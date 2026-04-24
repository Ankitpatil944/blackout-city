"""
blackstart_city/tier_grading.py
────────────────────────────────
Adds the tier_escalation_penalty to grading without touching grading.py.

Integration
-----------
Option A — call apply_tier_penalty() after your existing grader:

    from blackstart_city.grading import grade          # your existing function
    from blackstart_city.tier_grading import apply_tier_penalty

    raw_result   = grade(episode)
    final_result = apply_tier_penalty(raw_result, escalation_count=1)

Option B — use TierAwareGrader as a thin wrapper:

    from blackstart_city.tier_grading import TierAwareGrader
    grader = TierAwareGrader()
    final  = grader.grade(episode, escalation_count=tier_result.escalation_count)

Penalty rule
------------
  -0.05 per escalation (i.e. per tier switch)
  Tier 1 solve  → no penalty  (escalation_count = 0)
  Tier 2 solve  → −0.05       (escalation_count = 1)
  Tier 3 solve  → −0.10       (escalation_count = 2)

Score is clamped to [0.0, 1.0] after penalty.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

ESCALATION_PENALTY: float = 0.05   # per tier escalation


# ─────────────────────────────────────────────────────────────────────────────
# Data container — mirrors the dict that grading.py returns
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TierGradeResult:
    """Final grade including tier escalation penalty."""

    raw_score: float
    escalation_count: int
    escalation_penalty: float
    final_score: float
    breakdown: Dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# apply_tier_penalty — functional API
# ─────────────────────────────────────────────────────────────────────────────

def apply_tier_penalty(
    grade_result: Dict[str, Any],
    escalation_count: int,
) -> TierGradeResult:
    """
    Accept the dict returned by your existing grading.grade() and return
    a TierGradeResult with the escalation penalty applied.

    Parameters
    ----------
    grade_result     : dict   — output of blackstart_city.grading.grade()
                                Expected to have a numeric "score" or "total" key.
    escalation_count : int    — number of tier escalations (0 = solved at Tier 1)

    Returns
    -------
    TierGradeResult
    """
    # Locate the raw score — handles different grading.py dict shapes
    raw_score = _extract_score(grade_result)

    penalty     = round(escalation_count * ESCALATION_PENALTY, 4)
    final_score = round(max(0.0, min(1.0, raw_score - penalty)), 4)

    return TierGradeResult(
        raw_score=round(raw_score, 4),
        escalation_count=escalation_count,
        escalation_penalty=penalty,
        final_score=final_score,
        breakdown={
            **grade_result,
            "tier_escalation_penalty": -penalty,
            "tier_escalation_count": escalation_count,
            "tier_adjusted_score": final_score,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# TierAwareGrader — class API (wraps existing grader)
# ─────────────────────────────────────────────────────────────────────────────

class TierAwareGrader:
    """
    Wraps the existing BlackstartCityGrader (or any callable that returns a
    grade dict) and applies the tier escalation penalty on top.

    Usage
    -----
        grader = TierAwareGrader()
        result = grader.grade(episode, escalation_count=tier_result.escalation_count)
        print(result.final_score)
    """

    def __init__(self, base_grader=None):
        """
        Parameters
        ----------
        base_grader : optional
            Any object with a .grade(episode) → dict method.
            If None, a lazy import of BlackstartCityGrader is used.
        """
        self._base_grader = base_grader

    def _get_base_grader(self):
        if self._base_grader is not None:
            return self._base_grader
        # Lazy import so this file can be imported without the full env stack
        try:
            from blackstart_city.grading import BlackstartCityGrader  # noqa: PLC0415
            return BlackstartCityGrader()
        except ImportError:
            return _FallbackGrader()

    def grade(self, episode: Any, escalation_count: int = 0) -> TierGradeResult:
        """
        Grade one episode and apply the tier escalation penalty.

        Parameters
        ----------
        episode          : the episode object/dict accepted by your grader
        escalation_count : int — number of tier escalations
        """
        raw_result = self._get_base_grader().grade(episode)
        if not isinstance(raw_result, dict):
            # Pydantic model or dataclass → coerce to dict
            try:
                raw_result = raw_result.dict()
            except AttributeError:
                raw_result = vars(raw_result)

        return apply_tier_penalty(raw_result, escalation_count=escalation_count)

    def grade_from_result(
        self,
        raw_score: float,
        breakdown: Optional[Dict[str, Any]] = None,
        escalation_count: int = 0,
    ) -> TierGradeResult:
        """
        Convenience method: supply the score directly (skip re-running the grader).

        Useful when AgentTier.run() already returned a score and you just want
        to apply the penalty.
        """
        grade_result = {"score": raw_score, **(breakdown or {})}
        return apply_tier_penalty(grade_result, escalation_count=escalation_count)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_score(grade_result: Dict[str, Any]) -> float:
    """Try common key names used by different grading.py versions."""
    for key in ("score", "total", "final_score", "composite_score", "total_score"):
        val = grade_result.get(key)
        if val is not None:
            return float(val)
    # Last resort: sum all numeric values in a "breakdown" sub-dict
    breakdown = grade_result.get("breakdown") or grade_result.get("components") or {}
    if breakdown:
        return float(sum(v for v in breakdown.values() if isinstance(v, (int, float))))
    return 0.0


class _FallbackGrader:
    """Used when BlackstartCityGrader cannot be imported."""
    def grade(self, episode: Any) -> Dict[str, Any]:
        score = getattr(episode, "score", 0.0) if not isinstance(episode, dict) \
                else episode.get("score", 0.0)
        return {"score": float(score)}
