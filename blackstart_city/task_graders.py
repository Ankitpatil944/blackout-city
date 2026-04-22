from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from blackstart_city.grading import clamp_score


@dataclass
class BaseBlackstartGrader:
    task_id: str

    def grade(self, **kwargs: Any) -> float:
        score = kwargs.get("score")
        if isinstance(score, (int, float)):
            return clamp_score(float(score))

        info = kwargs.get("info")
        if isinstance(info, dict) and isinstance(info.get("score"), (int, float)):
            return clamp_score(float(info["score"]))

        return 0.01

    def __call__(self, **kwargs: Any) -> float:
        return self.grade(**kwargs)


class LocalBlackstartGrader(BaseBlackstartGrader):
    def __init__(self) -> None:
        super().__init__(task_id="local_blackstart")


class IslandRejoinGrader(BaseBlackstartGrader):
    def __init__(self) -> None:
        super().__init__(task_id="island_rejoin")


class CityCascadeRecoveryGrader(BaseBlackstartGrader):
    def __init__(self) -> None:
        super().__init__(task_id="city_cascade_recovery")
