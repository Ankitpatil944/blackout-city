from __future__ import annotations

import requests

from blackstart_city.models import BlackstartAction, BlackstartObservation, BlackstartState


class BlackstartCityClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    def reset(self, task_id: str, seed: int | None = None) -> BlackstartObservation:
        response = requests.post(f"{self.base_url}/reset", json={"task_id": task_id, "seed": seed}, timeout=30)
        response.raise_for_status()
        return BlackstartObservation.model_validate(response.json())

    def step(self, action: BlackstartAction) -> BlackstartObservation:
        response = requests.post(f"{self.base_url}/step", json=action.model_dump(mode="json"), timeout=30)
        response.raise_for_status()
        return BlackstartObservation.model_validate(response.json())

    def state(self) -> BlackstartState:
        response = requests.get(f"{self.base_url}/state", timeout=30)
        response.raise_for_status()
        return BlackstartState.model_validate(response.json())
