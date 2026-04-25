#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Blackstart City — HF Space / GPU Terminal run script
# Run this inside an HF Space terminal (A10G or T4 hardware)
# or paste cell-by-cell into a JupyterLab / Colab notebook.
# ─────────────────────────────────────────────────────────────────────────────
set -e

# 1. Install deps (unsloth first — it pins torch/cuda; rest follows)
pip install "unsloth[colab-new]" --quiet
pip install "trl>=0.10.1" "datasets>=2.20.0" "accelerate>=0.34.0" \
            "transformers>=4.44.0" "peft>=0.11.0" \
            "matplotlib" "numpy" "rich" --quiet

# 2. Install the project package in editable mode
pip install -e . --quiet

# 3. Build / refresh the training dataset
#    Use episodes_per_task=5 for ~400 samples (better than the default 2 × 3 = 159)
python - <<'PYEOF'
from blackstart_city.training.build_dataset import build_dataset
path = build_dataset("dataset.jsonl", episodes_per_task=5)
print(f"Dataset built: {path}")
import subprocess, sys
result = subprocess.run(["wc", "-l", str(path)], capture_output=True, text=True)
print(result.stdout.strip() or f"(wc not available; file exists: {path.exists()})")
PYEOF

# 4. Run GRPO training
#    --max-steps 200  ≈ 45-60 min on A10G (~$2.50-$3.15)
#    --max-steps 400  ≈ 90-120 min on A10G (~$5-$7)   ← recommended for hackathon
python -m blackstart_city.training.grpo_train \
    --model-name  "Qwen/Qwen2.5-3B-Instruct" \
    --output-dir  "artifacts/blackstart-city-grpo" \
    --max-steps   300

# 5. Push the trained LoRA adapter to your HF Hub repo
#    Replace YOUR_HF_USERNAME with your actual username
python - <<'PYEOF'
import os
from huggingface_hub import HfApi

api = HfApi()
username = api.whoami()["name"]
repo_id  = f"{username}/blackstart-city-grpo"

# Create repo if it doesn't exist
api.create_repo(repo_id, exist_ok=True, private=False)

# Upload the adapter + tokenizer
api.upload_folder(
    folder_path="artifacts/blackstart-city-grpo",
    repo_id=repo_id,
    commit_message="GRPO-trained Qwen2.5-3B LoRA — Blackstart City hackathon",
)
print(f"Model pushed → https://huggingface.co/{repo_id}")
PYEOF

echo "Done. Check artifacts/blackstart-city-grpo/reward_curves.png for training curves."
