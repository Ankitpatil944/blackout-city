from __future__ import annotations

import argparse
import json
from statistics import mean

from blackstart_city.env import BlackstartCityEnv
from blackstart_city.tasks.catalog import TASK_ORDER
from blackstart_city.training.policy import load_policy


def evaluate_policy(policy_name: str, seeds: int = 3, policy_path: str | None = None) -> dict[str, float]:
    policy = load_policy(policy_name, policy_path)
    scores = {}
    for task_id in TASK_ORDER:
        task_scores = []
        for seed in range(seeds):
            env = BlackstartCityEnv()
            observation = env.reset(task_id=task_id, seed=seed)
            info = {"score": 0.01}
            published = False
            seen_signatures: set[str] = set()
            while not observation.done:
                action = policy.choose(
                    observation,
                    published_status=published,
                    seen_signatures=seen_signatures,
                )
                if action is None:
                    break
                seen_signatures.add(f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}")
                observation, _, done, info = env.step(action)
                if action.action_type.value == "publish_status":
                    published = True
                if done:
                    break
            task_scores.append(float(info["score"]))
        scores[task_id] = round(mean(task_scores), 3)
    return scores


def evaluate_with_details(policy_name: str, seeds: int = 3, policy_path: str | None = None) -> dict[str, object]:
    policy = load_policy(policy_name, policy_path)
    task_results: dict[str, dict[str, float]] = {}
    overall_scores: list[float] = []
    for task_id in TASK_ORDER:
        scores = []
        resolved = 0
        catastrophes = 0
        hospital_failures = 0
        for seed in range(seeds):
            env = BlackstartCityEnv()
            observation = env.reset(task_id=task_id, seed=seed)
            info = {"score": 0.01, "resolved": False, "catastrophe_triggered": False, "hospital_failures": 0}
            published = False
            seen_signatures: set[str] = set()
            while not observation.done:
                action = policy.choose(
                    observation,
                    published_status=published,
                    seen_signatures=seen_signatures,
                )
                if action is None:
                    break
                seen_signatures.add(f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}")
                observation, _, done, info = env.step(action)
                if action.action_type.value == "publish_status":
                    published = True
                if done:
                    break
            score = float(info["score"])
            scores.append(score)
            overall_scores.append(score)
            resolved += int(bool(info["resolved"]))
            catastrophes += int(bool(info["catastrophe_triggered"]))
            hospital_failures += int(info["hospital_failures"])

        task_results[task_id] = {
            "mean_score": round(mean(scores), 3),
            "resolved_rate": round(resolved / seeds, 3),
            "catastrophe_rate": round(catastrophes / seeds, 3),
            "mean_hospital_failures": round(hospital_failures / seeds, 3),
        }

    return {
        "policy": policy_name,
        "overall_mean_score": round(mean(overall_scores), 3),
        "tasks": task_results,
    }


def evaluate_heuristic(seeds: int = 3) -> dict[str, float]:
    return evaluate_policy("heuristic", seeds=seeds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a Blackstart City policy on fixed seeds.")
    parser.add_argument("--policy", default="heuristic", choices=["heuristic", "greedy", "json"])
    parser.add_argument("--policy-path", default=None)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = evaluate_with_details(args.policy, seeds=args.seeds, policy_path=args.policy_path)
    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
