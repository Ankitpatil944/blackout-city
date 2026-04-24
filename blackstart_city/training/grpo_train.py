import argparse
import json
import os
import matplotlib.pyplot as plt
from datasets import load_dataset
from trl import GRPOConfig, GRPOTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported
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
        ],
        reward_weights=[0.1, 0.5, 0.4],
        args=training_args,
        train_dataset=dataset,
    )

    trainer.train()
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # Three reward curves on one plot — show judges all three signals
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    reward_keys = [
        "rewards/format_reward_func",
        "rewards/alignment_reward_func",
        "rewards/action_quality_reward_func",
    ]
    titles = ["Format Reward", "Alignment Reward", "Quality Reward"]
    for ax, key, title in zip(axes, reward_keys, titles):
        values = [l[key] for l in trainer.state.log_history if key in l]
        if values:
            ax.plot(values)
            ax.set_title(title)
            ax.set_xlabel("Step")
            ax.set_ylabel("Mean Reward")
    plt.tight_layout()
    plt.savefig(f"{args.output_dir}/reward_curves.png")
    print(f"Reward curves saved to {args.output_dir}/reward_curves.png")
    print("Done.")


if __name__ == "__main__":
    main()