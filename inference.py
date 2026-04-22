from __future__ import annotations

import json

from blackstart_city.baseline import choose_heuristic_action
from blackstart_city.env import BlackstartCityEnv
from blackstart_city.tasks.catalog import TASK_ORDER


def action_to_log(action) -> str:
    return json.dumps(action.model_dump(mode="json", exclude_none=True), separators=(",", ":"))


def main() -> None:
    for task_id in TASK_ORDER:
        env = BlackstartCityEnv()
        observation = env.reset(task_id=task_id, seed=0)
        rewards: list[float] = []
        step_count = 0
        success = False
        score = 0.01
        published = False
        seen_signatures: set[str] = set()

        print(f"[START] task={task_id} env=blackstart_city model=heuristic")
        try:
            while not observation.done:
                action = choose_heuristic_action(
                    observation,
                    published_status=published,
                    seen_signatures=seen_signatures,
                )
                if action is None:
                    break
                seen_signatures.add(f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}")
                observation, reward, done, info = env.step(action)
                rewards.append(reward)
                step_count += 1
                score = float(info["score"])
                if action.action_type.value == "publish_status":
                    published = True
                print(
                    f"[STEP] step={step_count} action={action_to_log(action)} "
                    f"reward={reward:.2f} done={'true' if done else 'false'} "
                    f"error={observation.last_action_error or 'null'}"
                )
                if done:
                    break
            success = score >= 0.70 and bool(info["resolved"])
        finally:
            env.close()
            rewards_str = ",".join(f"{value:.2f}" for value in rewards)
            print(f"[END] success={'true' if success else 'false'} steps={step_count} score={score:.2f} rewards={rewards_str}")


if __name__ == "__main__":
    main()
