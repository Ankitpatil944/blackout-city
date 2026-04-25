from __future__ import annotations

import json
from pathlib import Path

from blackstart_city.baseline import choose_heuristic_action
from blackstart_city.env import BlackstartCityEnv
from blackstart_city.models import ActionType, BlackstartAction
from blackstart_city.tasks.catalog import TASK_ORDER

# Phrases that appear in last_action_result when the env rejects or no-ops an
# action. last_action_error is only set for constraint violations / collapses;
# ordinary bad actions only show up here.
_FAILURE_RESULT_SIGNALS = (
    "not found",
    "already online",
    "already energized",
    "cannot start",
    "no energized path",
    "already closed",
    "already open",
    "already restored",
    "already powered",
    "already active",
    "already inspected",
    "unsupported action",
)


def _is_error_result(result: str | None) -> bool:
    """Return True when last_action_result describes a rejected or no-op action."""
    if not result:
        return False
    lower = result.lower()
    return any(sig in lower for sig in _FAILURE_RESULT_SIGNALS)


def _make_bad_action() -> BlackstartAction:
    """Return an action guaranteed to fail (non-existent generator target)."""
    return BlackstartAction(action_type=ActionType.START_GENERATOR, target_id="NONEXISTENT_GEN")


def observation_to_prompt(observation, failed_actions: list[dict] | None = None) -> str:
    """Serialise a BlackstartObservation to a JSON string.

    Includes ALL fields the reward functions inspect:
    - generators, substations, lines          (action_quality, format rewards)
    - command_center.role_recommendations      (alignment reward)
    - active_constraints                       (constraint reward)
    - news_feed                                (constraint reward bonus)
    - failure_context                          (failure_context reward)

    Previously these were omitted, causing three reward functions to always
    return the same value -> std=0 -> zero gradient -> no learning.
    """
    data = {
        "task_id": observation.task_id,
        "step": observation.step,
        "steps_remaining": observation.steps_remaining,
        "available_generation_mw": observation.available_generation_mw,
        "served_load_mw": observation.served_load_mw,
        "reserve_margin_mw": observation.reserve_margin_mw,
        "frequency_hz": observation.frequency_hz,
        # ── asset state (needed by action_quality_reward_func) ───────────────
        "generators": [g.model_dump(mode="json") for g in observation.generators],
        "substations": [s.model_dump(mode="json") for s in observation.substations],
        "lines": [l.model_dump(mode="json") for l in observation.lines],
        "critical_nodes": [node.model_dump(mode="json") for node in observation.critical_nodes],
        "zones": [zone.model_dump(mode="json") for zone in observation.zones],
        "warnings": observation.warnings,
        "allowed_actions": [a.value for a in observation.allowed_actions],
        "last_action_result": observation.last_action_result,
        "last_action_error": observation.last_action_error,
        # ── command center (needed by alignment_reward_func) ─────────────────
        "command_center": observation.command_center.model_dump(mode="json"),
        # ── constraints & news (needed by constraint_reward_func) ─────────────
        "active_constraints": [c.model_dump(mode="json") for c in observation.active_constraints],
        "news_feed": [n.model_dump(mode="json") for n in observation.news_feed],
    }
    # ── failure history (needed by failure_context_reward_func) ──────────────
    if failed_actions:
        data["failure_context"] = [{"tier": "previous", "failed_actions": failed_actions}]
    return json.dumps(data, separators=(",", ":"))


def build_dataset(output_path: str = "dataset.jsonl", episodes_per_task: int = 20) -> Path:
    path = Path(output_path)
    with path.open("w", encoding="utf-8") as handle:
        for task_id in TASK_ORDER:
            for seed in range(episodes_per_task):
                env = BlackstartCityEnv()
                observation = env.reset(task_id=task_id, seed=seed)
                published = False
                seen_signatures: set[str] = set()
                # Accumulate actions that the env rejected so we can expose a
                # non-empty failure_context to the reward function from step 2+.
                failed_actions: list[dict] = []

                # Every 3rd episode: inject one deliberate bad action first so
                # failure_context is populated from step 1 onward. We step the
                # env but skip writing a training record for the bad action so
                # the model never learns to imitate it.
                if seed % 3 == 1:
                    bad = _make_bad_action()
                    observation, _, _, _ = env.step(bad)
                    if observation.last_action_error or _is_error_result(observation.last_action_result):
                        failed_actions.append(
                            {"action_type": bad.action_type.value, "target_id": bad.target_id}
                        )

                while not observation.done:
                    action = choose_heuristic_action(
                        observation,
                        published_status=published,
                        seen_signatures=seen_signatures,
                    )
                    if action is None:
                        break
                    sig = (
                        f"{action.action_type.value}|"
                        f"{action.target_id or ''}|"
                        f"{action.requested_mw or 0}"
                    )
                    seen_signatures.add(sig)

                    record = {
                        "prompt": observation_to_prompt(observation, failed_actions),
                        "completion": json.dumps(
                            action.model_dump(mode="json", exclude_none=True),
                            separators=(",", ":"),
                        ),
                    }
                    handle.write(json.dumps(record) + "\n")

                    observation, _, done, _ = env.step(action)

                    # Detect both hard errors (constraint violations) and soft
                    # errors (bad target, already-online asset, etc.).
                    if observation.last_action_error or _is_error_result(observation.last_action_result):
                        failed_actions.append(
                            {
                                "action_type": action.action_type.value,
                                "target_id": action.target_id,
                            }
                        )

                    if action.action_type.value == "publish_status":
                        published = True
                    if done:
                        break
    return path


if __name__ == "__main__":
    dataset = build_dataset()
    print(f"Wrote dataset to {dataset}")
