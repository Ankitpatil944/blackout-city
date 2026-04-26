"""augment_dataset.py — inject synthetic failure_context into an existing dataset.

Generates an augmented .jsonl by:
  - Original rows with --coverage probability of getting failure_context injected.
  - A forced-failure duplicate for every row that has real failed IDs available.
  - Combines and shuffles both.

Usage (Colab):
    !python -m blackstart_city.training.augment_dataset \
        --input  /content/drive/MyDrive/blackstart_city_run/dataset.jsonl \
        --output /content/blackout-city/dataset_v2.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

FAILURE_REASONS = [
    "Frequency collapsed below 59.1Hz — cascade triggered",
    "Critical node lost backup power",
    "Reserve margin dropped below 10MW",
    "Attempted to energize damaged substation",
    "Generator start failed — fuel unavailable",
]


def extract_real_failed_ids(obs: dict) -> list[dict]:
    """Extract real asset IDs that a greedy policy would realistically try and fail."""
    failures: list[dict] = []

    # Offline generators — greedy might have tried to start them prematurely
    for g in obs.get("generators", []):
        if not g.get("online"):
            failures.append({"action_type": "start_generator", "target_id": g["id"]})

    # Damaged substations — greedy might have tried to energize them
    for s in obs.get("substations", []):
        if s.get("damaged"):
            failures.append({"action_type": "energize_substation", "target_id": s["id"]})

    # Uninspected lines — greedy might have tried to close before inspecting
    for l in obs.get("lines", []):
        if not l.get("inspected"):
            failures.append({"action_type": "close_line", "target_id": l["id"]})

    # Zones — greedy might have tried to restore before hospitals were powered
    for z in obs.get("zones", []):
        failures.append({"action_type": "restore_zone", "target_id": z["id"]})

    return failures


def make_failure_context(obs: dict, n_actions: int = 2) -> list[dict]:
    real_failures = extract_real_failed_ids(obs)
    if not real_failures:
        return []
    sampled = random.sample(real_failures, min(n_actions, len(real_failures)))
    return [
        {
            "tier": "previous",
            "failed_actions": sampled,
            "failure_reason": random.choice(FAILURE_REASONS),
            "score_at_failure": round(random.uniform(0.15, 0.40), 3),
        }
    ]


def augment(input_path: str, output_path: str, coverage: float = 0.75, seed: int = 42) -> None:
    random.seed(seed)

    rows: list[dict] = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            obs = json.loads(row["prompt"])

            # Original row — inject with `coverage` probability
            if random.random() < coverage:
                obs["failure_context"] = make_failure_context(obs)
            else:
                obs["failure_context"] = []
            row["prompt"] = json.dumps(obs, separators=(",", ":"))
            rows.append(row)

            # Forced-failure duplicate — only added when real IDs are available
            obs2 = json.loads(row["prompt"])
            obs2["failure_context"] = make_failure_context(obs2, n_actions=3)
            if obs2["failure_context"]:
                rows.append(
                    {
                        "prompt": json.dumps(obs2, separators=(",", ":")),
                        "completion": row["completion"],
                    }
                )

    random.shuffle(rows)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    with_ctx = sum(
        1 for r in rows if json.loads(r["prompt"]).get("failure_context")
    )
    total = len(rows)
    print(f"Augmented dataset saved to {output_path}")
    print(f"  Total rows:           {total}")
    print(f"  With failure_context: {with_ctx} ({100 * with_ctx // total}%)")
    print(f"  Without:              {total - with_ctx}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Augment dataset with synthetic failure_context")
    parser.add_argument("--input", required=True, help="Source dataset.jsonl")
    parser.add_argument("--output", required=True, help="Output path for augmented dataset")
    parser.add_argument("--coverage", type=float, default=0.75,
                        help="Fraction of original rows that get failure_context injected (default 0.75)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    augment(args.input, args.output, coverage=args.coverage, seed=args.seed)


if __name__ == "__main__":
    main()
