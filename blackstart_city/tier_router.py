"""
server/tier_router.py
─────────────────────
FastAPI router that adds the /run_with_tiers endpoint.

Mount this in server/app.py with ONE line (no other changes):

    from server.tier_router import tier_router
    app.include_router(tier_router)

The endpoint:
  POST /run_with_tiers
  Body: { "task_id": "city_cascade_recovery", "seed": 1 }

Returns:
  {
    "tier_used":         int,
    "tier_name":         str,
    "success":           bool,
    "score":             float,
    "escalation_count":  int,
    "escalation_penalty":float,
    "adjusted_score":    float,
    "action_history":    [...],
    "failure_contexts":  [...],
    "last_warning":      str | null,
    "wall_seconds":      float
  }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# ── lazily imported to avoid circular imports at module load time ─────────────
# from blackstart_city.env import BlackstartCityEnv
# from blackstart_city.agent_tier import AgentTier
# from blackstart_city.env_tier_patch import patch_env

tier_router = APIRouter(tags=["AgentTier"])

ESCALATION_PENALTY_PER_TIER = 0.05   # mirrors grading.py addition


# ── request / response models ─────────────────────────────────────────────────

class TierRunRequest(BaseModel):
    task_id: str = Field("city_cascade_recovery", description="Task ID from the catalog")
    seed: int    = Field(1, ge=0, description="Random seed for the scenario")


class TierRunResponse(BaseModel):
    tier_used: int
    tier_name: str
    success: bool
    score: float
    escalation_count: int
    escalation_penalty: float
    adjusted_score: float
    action_history: List[Dict[str, Any]]
    failure_contexts: List[Dict[str, Any]]
    last_warning: Optional[str]
    wall_seconds: float


# ── endpoint ──────────────────────────────────────────────────────────────────

@tier_router.post("/run_with_tiers", response_model=TierRunResponse)
def run_with_tiers(req: TierRunRequest) -> TierRunResponse:
    """
    Run the AgentTier cascade (Greedy → Heuristic → LLM) for one episode.

    Returns which tier solved it, the full action history, failure contexts
    from each escalation, and the adjusted score (after escalation penalties).
    """
    try:
        # Import here to avoid circular-import issues at module load
        from blackstart_city.env import BlackstartCityEnv          # noqa: PLC0415
        from blackstart_city.agent_tier import AgentTier           # noqa: PLC0415
        from blackstart_city.env_tier_patch import patch_env       # noqa: PLC0415
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"Import error: {exc}") from exc

    # Patch env if not already done (idempotent)
    patch_env(BlackstartCityEnv)

    try:
        env = BlackstartCityEnv()
        result = AgentTier().run(env, task_id=req.task_id, seed=req.seed)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    escalation_penalty = round(result.escalation_count * ESCALATION_PENALTY_PER_TIER, 4)
    adjusted_score     = round(max(0.0, result.score - escalation_penalty), 4)

    return TierRunResponse(
        tier_used=result.tier_used,
        tier_name=result.tier_name,
        success=result.success,
        score=round(result.score, 4),
        escalation_count=result.escalation_count,
        escalation_penalty=escalation_penalty,
        adjusted_score=adjusted_score,
        action_history=result.action_history,
        failure_contexts=result.failure_contexts,
        last_warning=result.last_warning,
        wall_seconds=round(result.wall_seconds, 3),
    )
