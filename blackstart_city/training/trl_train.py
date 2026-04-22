from __future__ import annotations

"""
Minimal training scaffold for the hackathon requirement.

This script intentionally stays lightweight:
- builds/loads a JSONL dataset from environment rollouts
- demonstrates how to load it with Hugging Face datasets
- outlines a TRL SFT pipeline

It is designed to be adapted in Colab or on provided Hugging Face compute.
"""

from pathlib import Path
import argparse
import json


def _build_messages(prompt: str, completion: str) -> str:
    return (
        "<|system|>You are a power-grid restoration policy. Return only JSON.\n"
        f"<|user|>{prompt}\n"
        f"<|assistant|>{completion}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal TRL SFT entrypoint for Blackstart City.")
    parser.add_argument("--dataset-path", default="dataset.jsonl")
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--output-dir", default="artifacts/blackstart-city-sft")
    parser.add_argument("--export-policy-json", default="artifacts/blackstart-city-policy.jsonl")
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--episodes-per-task", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dataset_path = Path(args.dataset_path)
    if not dataset_path.exists():
        from blackstart_city.training.build_dataset import build_dataset

        build_dataset(str(dataset_path), episodes_per_task=args.episodes_per_task)

    if args.dry_run:
        with dataset_path.open("r", encoding="utf-8") as handle:
            sample = json.loads(handle.readline())
        print("Dataset ready at", dataset_path)
        print("Sample formatted record:")
        print(_build_messages(sample["prompt"], sample["completion"])[:800])
        return

    try:
        from datasets import load_dataset
        from peft import LoraConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        print("Missing training dependencies. Install with: pip install -e .[train]")
        raise SystemExit(1) from exc

    dataset = load_dataset("json", data_files=str(dataset_path), split="train")

    def format_record(example: dict[str, str]) -> dict[str, str]:
        return {"text": _build_messages(example["prompt"], example["completion"])}

    train_dataset = dataset.map(format_record)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForCausalLM.from_pretrained(args.model_name, device_map="auto")
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        args=SFTConfig(
            output_dir=args.output_dir,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            learning_rate=2e-4,
            max_steps=args.max_steps,
            logging_steps=5,
            save_steps=max(10, args.max_steps // 2),
            report_to=[],
        ),
        peft_config=peft_config,
        formatting_func=lambda batch: batch["text"],
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Saved adapter and tokenizer to {args.output_dir}")

    export_path = Path(args.export_policy_json)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(dataset_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Exported rollout policy dataset to {export_path}")


if __name__ == "__main__":
    main()
