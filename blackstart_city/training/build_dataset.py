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
            "steps_remaining": observation.steps_remaining,
            "available_generation_mw": observation.available_generation_mw,
            "served_load_mw": observation.served_load_mw,
            "reserve_margin_mw": observation.reserve_margin_mw,
            "frequency_hz": observation.frequency_hz,
            "generators": [g.model_dump(mode="json") for g in observation.generators],
            "substations": [s.model_dump(mode="json") for s in observation.substations],
            "lines": [l.model_dump(mode="json") for l in observation.lines],
            "critical_nodes": [node.model_dump(mode="json") for node in observation.critical_nodes],
            "zones": [zone.model_dump(mode="json") for zone in observation.zones],
            "warnings": observation.warnings,
            "allowed_actions": [a.value for a in observation.allowed_actions],
            "last_action_result": observation.last_action_result,
            "last_action_error": observation.last_action_error,
            "command_center": observation.command_center.model_dump(mode="json"),
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
                    # Collect role recommendations from the command center agents
                    role_recs = []
                    if hasattr(env, "command_center"):
                        state = env.command_center.get_state()
                        role_recs = state.role_recommendations

                    record = {
                        "prompt": observation_to_prompt(observation),
                        "completion": json.dumps(action.model_dump(mode="json", exclude_none=True), separators=(",", ":")),
                        "role_recommendations": json.dumps([r.model_dump(mode="json") for r in role_recs])
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
