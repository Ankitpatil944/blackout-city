from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from blackstart_city.baseline import choose_greedy_action, choose_heuristic_action
from blackstart_city.models import BlackstartAction


class Policy(Protocol):
    def choose(
        self,
        observation,
        *,
        published_status: bool,
        seen_signatures: set[str],
    ) -> BlackstartAction | None:
        ...


class HeuristicPolicy:
    def choose(self, observation, *, published_status: bool, seen_signatures: set[str]) -> BlackstartAction | None:
        return choose_heuristic_action(
            observation,
            published_status=published_status,
            seen_signatures=seen_signatures,
        )


class GreedyPolicy:
    def choose(self, observation, *, published_status: bool, seen_signatures: set[str]) -> BlackstartAction | None:
        return choose_greedy_action(
            observation,
            published_status=published_status,
            seen_signatures=seen_signatures,
        )


@dataclass
class JsonPolicy:
    dataset_path: Path

    def __post_init__(self) -> None:
        self._mapping: dict[str, dict] = {}
        with self.dataset_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                self._mapping[record["prompt"]] = json.loads(record["completion"])

    def choose(self, observation, *, published_status: bool, seen_signatures: set[str]) -> BlackstartAction | None:
        from blackstart_city.training.build_dataset import observation_to_prompt

        prompt = observation_to_prompt(observation)
        payload = self._mapping.get(prompt)
        if payload is None:
            return None
        action = BlackstartAction.model_validate(payload)
        signature = f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}"
        if signature in seen_signatures:
            return None
        return action


def load_policy(policy_name: str, policy_path: str | None = None) -> Policy:
    name = policy_name.lower()
    if name == "heuristic":
        return HeuristicPolicy()
    if name == "greedy":
        return GreedyPolicy()
    if name == "json":
        if policy_path is None:
            raise ValueError("policy_path is required for json policy")
        return JsonPolicy(Path(policy_path))
    raise ValueError(f"Unknown policy: {policy_name}")
