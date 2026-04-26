# Blackstart City Training Plan

This repository is designed to satisfy the hackathon requirement of showing a **minimal training script** using Hugging Face tooling.

## Recommended Training Setup

Use a **small open model + LoRA** rather than trying to train from scratch.

Suggested stack:

- `datasets`
- `transformers`
- `trl`
- optional `peft`

## Workflow

1. Run the heuristic policy over seeded scenarios and build `dataset.jsonl`
2. Use structured JSON observations as prompts
3. Use structured JSON actions as completions
4. Fine-tune with supervised SFT first
5. Evaluate on fixed seeds before and after

## Minimal Commands

```powershell
python -m blackstart_city.training.build_dataset
python -m blackstart_city.training.eval --policy heuristic --pretty
python -m blackstart_city.training.trl_train --dry-run
```

## Suggested Demo Metrics

- mean task score
- success rate by task family
- hospital survival rate
- second-collapse rate
- critical-node restoration rate

## Why This Works

The environment is intentionally structured:

- observation = compact JSON
- action = compact JSON
- reward = deterministic and decomposed

That makes it compatible with lightweight SFT / TRL workflows and easy to evaluate before vs after training.

## Before / After Evaluation

Suggested comparison commands:

```powershell
python -m blackstart_city.training.eval --policy greedy --pretty
python -m blackstart_city.training.eval --policy heuristic --pretty
python -m blackstart_city.training.eval --policy json --policy-path artifacts/blackstart-city-policy.jsonl --pretty
```

This gives you a clean story for the judges:

- weak baseline
- stronger heuristic baseline
- trained / exported policy
