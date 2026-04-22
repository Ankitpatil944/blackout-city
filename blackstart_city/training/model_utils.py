from __future__ import annotations

import json

from blackstart_city.models import ActionType, BlackstartAction, StatusUpdate
from blackstart_city.training.build_dataset import observation_to_prompt


def build_policy_prompt(observation) -> str:
    return (
        "You are a city blackout restoration policy.\n"
        "Return exactly one valid JSON action object and nothing else.\n"
        "Observation:\n"
        f"{observation_to_prompt(observation)}"
    )


def parse_action_text(text: str) -> BlackstartAction | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
        return BlackstartAction.model_validate(payload)
    except Exception:
        return None


def invalid_action_penalty(observation) -> tuple[BlackstartAction, float, bool, str]:
    action = BlackstartAction(
        action_type=ActionType.PUBLISH_STATUS,
        status_update=StatusUpdate(
            summary="Recovery status unavailable because the policy produced malformed output.",
            critical_services="Critical services remain at risk until a valid action is generated.",
            next_action="Generate a valid structured JSON action for the next step.",
            owner="autonomous restoration policy",
        ),
    )
    emergency = any((not node.powered) and node.backup_minutes_remaining <= 12 for node in observation.critical_nodes)
    penalty = -0.18 if emergency else -0.10
    terminate = emergency
    reason = "Model output was not parseable JSON action."
    return action, penalty, terminate, reason
