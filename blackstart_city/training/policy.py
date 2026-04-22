from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from blackstart_city.baseline import choose_greedy_action, choose_heuristic_action
from blackstart_city.models import BlackstartAction
from blackstart_city.training.model_utils import build_policy_prompt, parse_action_text


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


@dataclass
class ModelPolicy:
    model_name_or_path: str
    base_model_name: str | None = None
    max_new_tokens: int = 96

    def __post_init__(self) -> None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from peft import PeftModel
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Model policy requires train dependencies to be installed.") from exc

        self._torch = torch
        self._AutoModelForCausalLM = AutoModelForCausalLM
        self._AutoTokenizer = AutoTokenizer
        self._PeftModel = PeftModel

        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name or self.model_name_or_path)
        self.tokenizer.pad_token = self.tokenizer.eos_token

        if self.base_model_name:
            base = AutoModelForCausalLM.from_pretrained(self.base_model_name, device_map="auto")
            self.model = PeftModel.from_pretrained(base, self.model_name_or_path)
        else:
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name_or_path, device_map="auto")
        self.model.eval()

    def choose(self, observation, *, published_status: bool, seen_signatures: set[str]) -> BlackstartAction | None:
        prompt = build_policy_prompt(observation)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with self._torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=self.max_new_tokens,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        generated = outputs[0][inputs["input_ids"].shape[1] :]
        text = self.tokenizer.decode(generated, skip_special_tokens=True)
        action = parse_action_text(text)
        if action is None:
            return None
        signature = f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}"
        if signature in seen_signatures:
            return None
        return action


def load_policy(policy_name: str, policy_path: str | None = None, base_model_name: str | None = None) -> Policy:
    name = policy_name.lower()
    if name == "heuristic":
        return HeuristicPolicy()
    if name == "greedy":
        return GreedyPolicy()
    if name == "json":
        if policy_path is None:
            raise ValueError("policy_path is required for json policy")
        return JsonPolicy(Path(policy_path))
    if name == "model":
        if policy_path is None:
            raise ValueError("policy_path is required for model policy")
        return ModelPolicy(policy_path, base_model_name=base_model_name)
    raise ValueError(f"Unknown policy: {policy_name}")
