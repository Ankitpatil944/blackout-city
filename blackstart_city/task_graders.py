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
    """Easy-tier: extra penalty if the hospital fails early (before step 8)."""

    def __init__(self) -> None:
        super().__init__(task_id="local_blackstart")

    def grade(self, **kwargs: Any) -> float:
        base = super().grade(**kwargs)
        info = kwargs.get("info")
        if isinstance(info, dict):
            hospital_failures = int(info.get("hospital_failures", 0))
            step_count = int(info.get("step_count", 0))
            if hospital_failures > 0 and step_count < 8:
                base -= 0.10  # harsh penalty for early hospital loss
            elif hospital_failures > 0:
                base -= 0.05
        return clamp_score(base)


class IslandRejoinGrader(BaseBlackstartGrader):
    """Medium-tier: bonus for successful island synchronization, penalty for catastrophe."""

    def __init__(self) -> None:
        super().__init__(task_id="island_rejoin")

    def grade(self, **kwargs: Any) -> float:
        base = super().grade(**kwargs)
        info = kwargs.get("info")
        if isinstance(info, dict):
            if info.get("resolved"):
                base += 0.08  # bonus for full resolution including sync
            if info.get("catastrophe_triggered"):
                base -= 0.12  # failed sync caused a collapse
        return clamp_score(base)


class CityCascadeRecoveryGrader(BaseBlackstartGrader):
    """Hard-tier: harshest penalties for hospital failures and cascading catastrophe."""

    def __init__(self) -> None:
        super().__init__(task_id="city_cascade_recovery")

    def grade(self, **kwargs: Any) -> float:
        base = super().grade(**kwargs)
        info = kwargs.get("info")
        if isinstance(info, dict):
            hospital_failures = int(info.get("hospital_failures", 0))
            base -= 0.06 * hospital_failures  # each hospital failure is costly
            failed_nodes = info.get("failed_critical_nodes", [])
            if isinstance(failed_nodes, list):
                base -= 0.03 * len(failed_nodes)  # penalty for every failed critical node
            if info.get("catastrophe_triggered"):
                base -= 0.15  # second blackout is unacceptable
            if info.get("resolved"):
                base += 0.10  # big bonus for saving the city
        return clamp_score(base)
