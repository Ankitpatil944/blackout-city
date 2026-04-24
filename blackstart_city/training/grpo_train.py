import argparse
import json
import os

from unsloth import FastLanguageModel, is_bfloat16_supported
from datasets import load_dataset
from trl import GRPOConfig, GRPOTrainer
import matplotlib.pyplot as plt

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
    """
    1.0 for matching action type AND target_id
    0.3 for matching action type only
    0.0 for no match
    Fuzzy matching prevents permanent zero std.
    """
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
                    if not rec_action:
                        continue
                    if rec_action.get("action_type") == action.action_type.value:
                        if rec_action.get("target_id") == action.target_id:
                            reward = 1.0
                            break
                        else:
                            # Partial credit — right action type, wrong target
                            reward = max(reward, 0.3)
            rewards.append(reward)
        except Exception:
            rewards.append(0.0)
    return rewards


def action_quality_reward_func(prompts, completions, **kwargs) -> list[float]:
    """
    Graded reward from observation state.
    Base score 0.1 for any valid action ensures nonzero variance.
    No env.step() — no temporal mismatch.
    """
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

            # Base score for any valid action — ensures variance exists
            score = 0.1

            critical_nodes = obs_data.get("critical_nodes", [])
            generators = obs_data.get("generators", [])
            freq = obs_data.get("frequency_hz", 60.0)
            reserve = obs_data.get("reserve_margin_mw", 0)
            unpowered_critical = [n for n in critical_nodes if not n.get("powered")]
            powered_critical = [n for n in critical_nodes if n.get("powered")]

            # Reward rescuing critical nodes with low backup
            for node in critical_nodes:
                if not node.get("powered") and action.target_id == node.get("id"):
                    backup = node.get("backup_minutes_remaining", 999)
                    score += 1.0 if backup < 15 else 0.5 if backup < 30 else 0.2

            # Reward starting generator when none online
            online_count = sum(1 for g in generators if g.get("online"))
            if online_count == 0 and action.action_type.value == "start_generator":
                score += 1.0

            # Reward any generation boost when reserve is low
            if reserve < 10 and action.action_type.value in (
                "start_generator", "activate_battery_support"
            ):
                score += 0.5

            # Reward shedding load when frequency is critical
            if freq < 59.5 and action.action_type.value == "shed_zone":
                score += 0.8

            # Reward inspecting lines — always useful early game
            if action.action_type.value == "inspect_line":
                score += 0.2

            # Penalize restoring zones before critical nodes are powered
            if unpowered_critical and action.action_type.value == "restore_zone":
                score -= 0.5

            # Penalize publishing status before any critical node is powered
            if not powered_critical and action.action_type.value == "publish_status":
                score -= 0.3

            rewards.append(max(-1.0, min(1.0, score)))
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
        fast_inference=False,
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

    def generate_prompt(example):
        return {"prompt": [
            {"role": "system", "content": (
                "You are a Blackstart City grid commander. "
                "Output ONLY a valid JSON object matching the environment's action schema. "
                "Do not include markdown code blocks, explanations, or any other text. "
                "Example: {\"action_type\": \"start_generator\", \"target_id\": \"gen_1\"}"
            )},
            {"role": "user", "content": "Observation:\n" + example["prompt"]}
        ]}

    dataset = dataset.map(generate_prompt, remove_columns=dataset.column_names)

    training_args = GRPOConfig(
        output_dir=args.output_dir,
        learning_rate=5e-6,
        lr_scheduler_type="cosine",
        logging_steps=1,
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
        ],
        reward_weights=[0.0, 0.5, 0.5],  # format learned, dropped to 0
        args=training_args,
        train_dataset=dataset,
    )

    trainer.train()
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    reward_keys_substrings = [
        "format_reward_func",
        "alignment_reward_func",
        "action_quality_reward_func",
    ]
    titles = ["Format Reward", "Alignment Reward", "Quality Reward"]

    for ax, sub, title in zip(axes, reward_keys_substrings, titles):
        actual_key = None
        for log in trainer.state.log_history:
            for k in log.keys():
                if sub in k:
                    actual_key = k
                    break
            if actual_key:
                break
        if actual_key:
            values = [l[actual_key] for l in trainer.state.log_history if actual_key in l]
            ax.plot(values)
            ax.set_title(title)
            ax.set_xlabel("Step")
            ax.set_ylabel("Mean Reward")
            print(f"Plotted {len(values)} points for {title} (key: {actual_key})")
        else:
            print(f"Warning: Could not find log key for {title}")

    plt.tight_layout()
    plt.savefig(f"{args.output_dir}/reward_curves.png")
    print(f"Reward curves saved to {args.output_dir}/reward_curves.png")
    print("Done.")


if __name__ == "__main__":
    main()