import argparse
import json
import os
import matplotlib.pyplot as plt
from datasets import load_dataset
from unsloth import FastLanguageModel, PatchFastRL, is_bfloat16_supported

# This makes the GRPO training logs look nice in the terminal/colab
PatchFastRL("GRPO", FastLanguageModel)

from trl import GRPOConfig, GRPOTrainer
from blackstart_city.training.model_utils import parse_action_text


def format_reward_func(completions, **kwargs) -> list[float]:
    """Gate reward — valid JSON action = 1.0, invalid = 0.0"""
    rewards = []
    for comp in completions:
        try:
            text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(text)
            rewards.append(1.0 if action is not None else 0.0)
        except Exception:
            rewards.append(0.0)
    return rewards


def alignment_reward_func(prompts, completions, **kwargs) -> list[float]:
    """Rewards alignment with command center agent recommendations"""
    rewards = []
    for prompt, comp in zip(prompts, completions):
        try:
            prompt_text = prompt[0]["content"] if isinstance(prompt, list) else prompt
            obs_json_str = prompt_text.split("Observation:\n")[-1]
            obs = json.loads(obs_json_str)
            comp_text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(comp_text)
            reward = 0.0
            if action:
                recs = obs.get("command_center", {}).get("role_recommendations", [])
                for rec in recs:
                    rec_action = rec.get("proposed_action")
                    if rec_action and rec_action.get("action_type") == action.action_type.value:
                        if rec_action.get("target_id") == action.target_id:
                            reward = 1.0
                            break
            rewards.append(reward)
        except Exception:
            rewards.append(0.0)
    return rewards


def action_quality_reward_func(prompts, completions, **kwargs) -> list[float]:
    """Graded reward from observation state — no env.step(), no temporal mismatch."""
    rewards = []
    for prompt, comp in zip(prompts, completions):
        try:
            prompt_text = prompt[0]["content"] if isinstance(prompt, list) else prompt
            obs_json_str = prompt_text.split("Observation:\n")[-1]
            obs_data = json.loads(obs_json_str)
            comp_text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(comp_text)

            if action is None:
                rewards.append(-0.5)
                continue

            score = 0.0
            critical_nodes = obs_data.get("critical_nodes", [])
            generators = obs_data.get("generators", [])
            freq = obs_data.get("frequency_hz", 60.0)
            unpowered_critical = [n for n in critical_nodes if not n.get("powered")]

            for node in critical_nodes:
                if not node.get("powered") and action.target_id == node.get("id"):
                    backup = node.get("backup_minutes_remaining", 999)
                    score += 1.0 if backup < 15 else 0.5 if backup < 30 else 0.2

            online_count = sum(1 for g in generators if g.get("online"))
            if online_count == 0 and action.action_type.value == "start_generator":
                score += 1.0

            if freq < 59.5 and action.action_type.value == "shed_zone":
                score += 0.8

            if unpowered_critical and action.action_type.value == "restore_zone":
                score -= 0.5

            rewards.append(max(-1.0, min(1.0, score)))
        except Exception:
            rewards.append(0.0)
    return rewards


def constraint_reward_func(prompts, completions, **kwargs) -> list[float]:
    """Penalizes actions that violate scenario constraints visible in the observation."""
    rewards = []
    for prompt, comp in zip(prompts, completions):
        try:
            prompt_text = prompt[0]["content"] if isinstance(prompt, list) else prompt
            obs_json_str = prompt_text.split("Observation:\n")[-1]
            obs_data = json.loads(obs_json_str)
            comp_text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(comp_text)

            if action is None:
                rewards.append(0.0)
                continue

            score = 0.5  # base: assume compliant

            constraints = obs_data.get("active_constraints", [])
            for c in constraints:
                if not c.get("active", True) or c.get("violated", False):
                    continue
                ct = c.get("constraint_type", "")

                # Forbidden target check
                if ct == "forbidden_target":
                    if (action.action_type.value == c.get("forbidden_action_type")
                            and action.target_id == c.get("forbidden_target_id")):
                        score -= 1.0

                # Conditional limit check
                if ct == "conditional_limit":
                    if (action.action_type.value == "restore_zone"
                            and action.target_id == c.get("limit_target_id")
                            and action.requested_mw is not None
                            and c.get("limit_mw") is not None
                            and action.requested_mw > c["limit_mw"]):
                        score -= 0.8

                # Priority order check
                if ct == "priority_order":
                    if (action.action_type.value == "restore_zone"
                            and action.target_id == c.get("before_restoring")):
                        first_id = c.get("must_restore_first")
                        nodes = obs_data.get("critical_nodes", [])
                        first_node = next((n for n in nodes if n.get("id") == first_id), None)
                        if first_node and not first_node.get("powered"):
                            score -= 0.7

            # Bonus: responding to news feed
            news = obs_data.get("news_feed", [])
            if news and any(n.get("impact_level") == "critical" for n in news):
                # Reward actions that address critical news (e.g. restoring the mentioned node)
                for n in news:
                    if n.get("reduces_backup_node") and action.target_id == n["reduces_backup_node"]:
                        score += 0.5

            rewards.append(max(-1.0, min(1.0, score)))
        except Exception:
            rewards.append(0.0)
    return rewards


def failure_context_reward_func(prompts, completions, **kwargs) -> list[float]:
    """
    ToM Reward: Rewards the model for NOT repeating actions that failed in
    previous tiers (visible in the failure_context).
    """
    rewards = []
    for prompt, comp in zip(prompts, completions):
        try:
            prompt_text = prompt[0]["content"] if isinstance(prompt, list) else prompt
            obs_json_str = prompt_text.split("Observation:\n")[-1]
            obs_data = json.loads(obs_json_str)

            # Check for failure history
            failure_ctx = obs_data.get("failure_context", [])
            if not failure_ctx:
                rewards.append(0.0)  # No context to learn from
                continue

            comp_text = comp[0]["content"] if isinstance(comp, list) else comp
            action = parse_action_text(comp_text)
            if not action:
                rewards.append(-0.2)
                continue

            # Check if this specific action was tried and failed before
            was_failure = False
            for fail in failure_ctx:
                for failed_action in fail.get("failed_actions", []):
                    if (failed_action.get("action_type") == action.action_type.value and
                        failed_action.get("target_id") == action.target_id):
                        was_failure = True
                        break

            # Positive reward for pivoting away from failure, negative for repeating it
            rewards.append(-1.0 if was_failure else 0.5)
        except Exception:
            rewards.append(0.0)
    return rewards


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--output-dir", default="artifacts/blackstart-city-grpo")
    parser.add_argument("--max-steps", type=int, default=200)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model_name,
        max_seq_length=2048,
        load_in_4bit=True,
        fast_inference=True,
        max_lora_rank=16,
        gpu_memory_utilization=0.6,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj","k_proj","v_proj","o_proj",
                        "gate_proj","up_proj","down_proj"],
        lora_alpha=16,
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    dataset = load_dataset("json", data_files="dataset.jsonl", split="train")

    def format_for_grpo(example):
        return {"prompt": [
            {"role": "system", "content": "You are a city blackout restoration policy. "
                                          "Return exactly one valid JSON action object and nothing else."},
            {"role": "user", "content": "Observation:\n" + example["prompt"]}
        ]}
    dataset = dataset.map(format_for_grpo, remove_columns=dataset.column_names)

    training_args = GRPOConfig(
        output_dir=args.output_dir,
        learning_rate=5e-6,
        lr_scheduler_type="cosine",
        logging_steps=5,
        max_steps=args.max_steps,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_generations=4,
        max_prompt_length=1500,
        max_completion_length=150,
        bf16=is_bfloat16_supported(),
        fp16=not is_bfloat16_supported(),
        optim="adamw_8bit",
        report_to="none",
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[
            format_reward_func,
            alignment_reward_func,
            action_quality_reward_func,
            constraint_reward_func,
            failure_context_reward_func,
        ],
        reward_weights=[0.1, 0.3, 0.2, 0.2, 0.2],
        args=training_args,
        train_dataset=dataset,
    )

    trainer.train()
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # Show all 5 reward signals to the judges
    # --- PREMIUM DASHBOARD PLOTTING ---
    import matplotlib.pyplot as plt
    import numpy as np

    # Set dark theme aesthetics
    plt.style.use('dark_background')
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), facecolor='#121212')
    fig.suptitle('BLACKSTART CITY: GRPO TRAINING DASHBOARD', fontsize=20, fontweight='bold', color='#00FFCC', y=1.05)

    reward_keys_substrings = [
        "format_reward_func",
        "alignment_reward_func",
        "action_quality_reward_func",
    ]
    titles = ["FORMAT INTEGRITY", "AGENT ALIGNMENT", "TACTICAL QUALITY"]
    colors = ['#FF00FF', '#00CCFF', '#00FF66'] # Neon Pink, Blue, Green

    for ax, sub, title, color in zip(axes, reward_keys_substrings, titles, colors):
        actual_key = None
        for log in trainer.state.log_history:
            for k in log.keys():
                if sub in k:
                    actual_key = k
                    break
            if actual_key: break
            
        if actual_key:
            raw_values = [l[actual_key] for l in trainer.state.log_history if actual_key in l]
            
            # Calculate rolling average for smoothness
            window = max(1, len(raw_values) // 10)
            smooth_values = np.convolve(raw_values, np.ones(window)/window, mode='valid')
            
            # Plot raw data with transparency
            ax.plot(raw_values, color=color, alpha=0.2, linewidth=1)
            # Plot smooth trend line
            ax.plot(range(window-1, len(raw_values)), smooth_values, color=color, linewidth=3, label='Trend')
            
            # Styling
            ax.set_title(title, fontsize=14, fontweight='bold', color=color, pad=15)
            ax.set_facecolor('#1e1e1e')
            ax.grid(True, linestyle='--', alpha=0.1)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.set_xlabel("Training Step", alpha=0.7)
            if title == "TACTICAL QUALITY":
                ax.set_ylabel("Reward Value", alpha=0.7)
            
            # Add a subtle glow effect
            ax.fill_between(range(window-1, len(raw_values)), smooth_values, alpha=0.05, color=color)

    plt.tight_layout()
    plt.savefig(f"{args.output_dir}/reward_curves.png", dpi=150, bbox_inches='tight', facecolor='#121212')
    print(f"Premium Dashboard saved to {args.output_dir}/reward_curves.png")
    print("Done.")


if __name__ == "__main__":
    main()