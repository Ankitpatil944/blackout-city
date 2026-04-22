from __future__ import annotations

import json
from pathlib import Path

from blackstart_city.baseline import choose_heuristic_action
from blackstart_city.env import BlackstartCityEnv
from blackstart_city.tasks.catalog import TASK_ORDER


def observation_to_prompt(observation) -> str:
    return json.dumps(
        {
            "task_id": observation.task_id,
            "step": observation.step,
            "available_generation_mw": observation.available_generation_mw,
            "reserve_margin_mw": observation.reserve_margin_mw,
            "frequency_hz": observation.frequency_hz,
            "critical_nodes": [node.model_dump(mode="json") for node in observation.critical_nodes],
            "zones": [zone.model_dump(mode="json") for zone in observation.zones],
            "warnings": observation.warnings,
        },
        separators=(",", ":"),
    )


def build_dataset(output_path: str = "dataset.jsonl", episodes_per_task: int = 2) -> Path:
    path = Path(output_path)
    with path.open("w", encoding="utf-8") as handle:
        for task_id in TASK_ORDER:
            for seed in range(episodes_per_task):
                env = BlackstartCityEnv()
                observation = env.reset(task_id=task_id, seed=seed)
                published = False
                seen_signatures: set[str] = set()
                while not observation.done:
                    action = choose_heuristic_action(
                        observation,
                        published_status=published,
                        seen_signatures=seen_signatures,
                    )
                    if action is None:
                        break
                    seen_signatures.add(f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}")
                    record = {
                        "prompt": observation_to_prompt(observation),
                        "completion": json.dumps(action.model_dump(mode="json", exclude_none=True), separators=(",", ":")),
                    }
                    handle.write(json.dumps(record) + "\n")
                    observation, _, done, _ = env.step(action)
                    if action.action_type.value == "publish_status":
                        published = True
                    if done:
                        break
    return path


if __name__ == "__main__":
    dataset = build_dataset()
    print(f"Wrote dataset to {dataset}")
