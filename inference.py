from __future__ import annotations

"""
inference.py — Blackstart City demonstration runner.

Runs the heuristic policy on all 3 task families and prints a structured
report showing agent decisions, hospital backup timers, grid stability,
and final scores.  This file is the primary "proof of life" for judges.
"""

import json

from blackstart_city.baseline import choose_heuristic_action
from blackstart_city.env import BlackstartCityEnv
from blackstart_city.grading import clamp_score
from blackstart_city.tasks.catalog import TASK_ORDER


_DIVIDER = "=" * 72
_ICONS = {
    "hospital": "[H]",
    "telecom": "[T]",
    "water": "[W]",
    "emergency": "[E]",
}


def action_to_log(action) -> str:
    return json.dumps(action.model_dump(mode="json", exclude_none=True), separators=(",", ":"))


def backup_bar(minutes: int, original: int = 40) -> str:
    filled = max(0, int((minutes / max(1, original)) * 10))
    char = "#" if minutes > 15 else ("+" if minutes > 10 else ".")
    return char * filled + " " * (10 - filled)


def main() -> None:
    all_scores: dict[str, float] = {}

    for task_id in TASK_ORDER:
        env = BlackstartCityEnv()
        observation = env.reset(task_id=task_id, seed=0)

        print(f"\n{_DIVIDER}")
        print(f"  TASK: {task_id.upper()}  [{observation.difficulty.value.upper()}]")
        print(f"  Scenario: {observation.title}")
        print(f"  Objective: {observation.objective}")
        print(_DIVIDER)

        # Print initial hospital situation
        hospitals = [n for n in observation.critical_nodes if n.type.value == "hospital"]
        if hospitals:
            print("  INITIAL HOSPITAL STATUS:")
            for h in hospitals:
                print(f"    {_ICONS['hospital']} {h.id}: {h.backup_minutes_remaining} min backup  "
                      f"[{backup_bar(h.backup_minutes_remaining)}]  demand={h.demand_mw} MW")
        print()

        rewards: list[float] = []
        step_count = 0
        resolved = False
        score = 0.01
        published = False
        seen_signatures: set[str] = set()
        info: dict = {}

        try:
            while not observation.done:
                action = choose_heuristic_action(
                    observation,
                    published_status=published,
                    seen_signatures=seen_signatures,
                )
                if action is None:
                    break
                seen_signatures.add(
                    f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}"
                )
                observation, reward, done, info = env.step(action)
                rewards.append(reward)
                step_count += 1
                score = float(info["score"])

                if action.action_type.value == "publish_status":
                    published = True

                # Print step with key context
                critical_summary = " | ".join(
                    f"{_ICONS.get(n.type.value, '?')}{n.id.split('_')[0]}:"
                    f"{'OK' if n.powered else str(n.backup_minutes_remaining) + 'm'}"
                    for n in observation.critical_nodes
                )
                print(
                    f"  [{step_count:2d}] {action.action_type.value:<28} "
                    f"R={reward:+.2f}  score={score:.2f}  "
                    f"freq={observation.frequency_hz:.2f}Hz  "
                    f"{critical_summary}"
                )
                if observation.last_action_error:
                    print(f"       ! {observation.last_action_error}")

                if done:
                    break

            resolved = bool(info.get("resolved", False))

        finally:
            env.close()

        all_scores[task_id] = score
        rewards_str = ", ".join(f"{r:+.2f}" for r in rewards)

        print()
        print(f"  {'RESOLVED' if resolved else 'PARTIAL'}  "
              f"steps={step_count}/{observation.step + observation.steps_remaining}  "
              f"score={score:.2f}  "
              f"hospital_failures={info.get('hospital_failures', '?')}  "
              f"catastrophe={'YES FAIL' if info.get('catastrophe_triggered') else 'No OK'}")
        print(f"  Rewards: [{rewards_str}]")

        # Print reward breakdown
        rb = observation.reward_breakdown
        print(f"  Breakdown -> critical={rb.critical_restore_reward:.2f}  "
              f"load={rb.load_restore_reward:.2f}  "
              f"stability={rb.stability_reward:.2f}  "
              f"inspect={rb.inspection_reward:.2f}  "
              f"comms={rb.communication_reward:.2f}  "
              f"penalty={rb.action_penalty:.2f}")

    print(f"\n{_DIVIDER}")
    print("  OVERALL RESULTS")
    print(_DIVIDER)
    for task_id, score in all_scores.items():
        bar = "#" * int(score * 20) + "." * (20 - int(score * 20))
        print(f"  {task_id:<32} [{bar}]  {score:.2f}")
    mean = sum(all_scores.values()) / len(all_scores)
    print(f"\n  Mean score across all tasks: {mean:.3f}")
    print(_DIVIDER)


if __name__ == "__main__":
    main()
