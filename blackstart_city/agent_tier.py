"""
blackstart_city/agent_tier.py
─────────────────────────────
Minimal AgentTier system for Blackstart City.

Rules
-----
• Run Greedy → Heuristic → LLM in order.
• First success wins — no further tiers run.
• On failure, inject the failure context into the env before the next tier.
• Return an EpisodeResult with tier_used, score, escalation_count, history.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

# ── local imports ──────────────────────────────────────────────────────────────
from blackstart_city.baseline import choose_greedy_action, choose_heuristic_action
from blackstart_city.models import ActionType, BlackstartAction, BlackstartObservation


# ─────────────────────────────────────────────────────────────────────────────
# Thin policy wrappers around the baseline functions
# ─────────────────────────────────────────────────────────────────────────────

class GreedyPolicy:
    """Wraps choose_greedy_action into a Policy-compatible .act() interface."""

    name: str = "GreedyPolicy"

    def __init__(self):
        self._published = False
        self._seen_signatures: set[str] = set()

    def act(self, observation) -> BlackstartAction:
        obs = _to_observation(observation)
        action = choose_greedy_action(
            obs, published_status=self._published, seen_signatures=self._seen_signatures,
        )
        if action is None:
            # Fallback: no-op status publish
            action = BlackstartAction(action_type=ActionType.PUBLISH_STATUS, status_update=_fallback_status())
        if action.action_type == ActionType.PUBLISH_STATUS:
            self._published = True
        return action


class HeuristicPolicy:
    """Wraps choose_heuristic_action into a Policy-compatible .act() interface."""

    name: str = "HeuristicPolicy"

    def __init__(self):
        self._published = False
        self._seen_signatures: set[str] = set()

    def act(self, observation) -> BlackstartAction:
        obs = _to_observation(observation)
        action = choose_heuristic_action(
            obs, published_status=self._published, seen_signatures=self._seen_signatures,
        )
        if action is None:
            action = BlackstartAction(action_type=ActionType.PUBLISH_STATUS, status_update=_fallback_status())
        if action.action_type == ActionType.PUBLISH_STATUS:
            self._published = True
        return action


def _to_observation(observation) -> BlackstartObservation:
    """Convert dict or model to BlackstartObservation, stripping unknown keys."""
    if isinstance(observation, BlackstartObservation):
        return observation
    if isinstance(observation, dict):
        valid_fields = BlackstartObservation.model_fields.keys()
        clean = {k: v for k, v in observation.items() if k in valid_fields}
        return BlackstartObservation.model_validate(clean)
    return observation


def _fallback_status():
    """Return a minimal status update for when no other action is available."""
    from blackstart_city.models import StatusUpdate
    return StatusUpdate(
        summary="Recovery operations are in progress across the grid.",
        critical_services="Teams are working to restore critical services.",
        next_action="Continue coordinated restoration efforts.",
        owner="city restoration commander",
    )


class LLMPolicy:
    """
    GRPO-trained LLM policy (Tier 2).

    Loads the trained Qwen + LoRA adapter via `ModelPolicy` and uses real
    generation to choose actions. Resolution order for the model path:

      1. explicit `model_path` arg passed to the constructor, or
      2. `BLACKSTART_LLM_MODEL_PATH` environment variable, or
      3. `artifacts/blackstart-city-grpo` if it exists locally.

    If none resolve, the policy logs a warning and degrades to the
    `HeuristicPolicy` so the cascade still completes — but a flag is set
    so callers can detect that the LLM tier was skipped.
    """

    name: str = "LLMPolicy"

    def __init__(self, model_path: str | None = None, base_model: str | None = None):
        import os
        from pathlib import Path

        self._published = False
        self._seen_signatures: set[str] = set()
        self._inner = None
        self._fallback_reason: str | None = None

        resolved_path = (
            model_path
            or os.getenv("BLACKSTART_LLM_MODEL_PATH")
            or ("artifacts/blackstart-city-grpo"
                if Path("artifacts/blackstart-city-grpo").exists() else None)
        )
        resolved_base = base_model or os.getenv("BLACKSTART_LLM_BASE_MODEL")

        if resolved_path is None:
            self._fallback_reason = (
                "no LLM checkpoint configured (set BLACKSTART_LLM_MODEL_PATH "
                "or pass model_path=)"
            )
            return

        try:
            from blackstart_city.training.policy import ModelPolicy
            self._inner = ModelPolicy(
                model_name_or_path=resolved_path,
                base_model_name=resolved_base,
            )
        except Exception as exc:
            self._fallback_reason = f"failed to load LLM ({type(exc).__name__}: {exc})"
            self._inner = None

    @property
    def used_fallback(self) -> bool:
        return self._inner is None

    def act(self, observation) -> BlackstartAction:
        obs = _to_observation(observation)

        if self._inner is None:
            action = choose_heuristic_action(
                obs,
                published_status=self._published,
                seen_signatures=self._seen_signatures,
            )
        else:
            action = self._inner.choose(
                obs,
                published_status=self._published,
                seen_signatures=self._seen_signatures,
            )

        if action is None:
            action = BlackstartAction(
                action_type=ActionType.PUBLISH_STATUS,
                status_update=_fallback_status(),
            )

        sig = f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}"
        self._seen_signatures.add(sig)
        if action.action_type == ActionType.PUBLISH_STATUS:
            self._published = True
        return action


# ─────────────────────────────────────────────────────────────────────────────
# EpisodeResult
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EpisodeResult:
    """Returned by AgentTier.run()."""

    tier_used: int                          # 0 = Greedy, 1 = Heuristic, 2 = LLM
    tier_name: str
    success: bool
    score: float
    escalation_count: int
    action_history: List[Dict[str, Any]] = field(default_factory=list)
    failure_contexts: List[Dict[str, Any]] = field(default_factory=list)
    last_warning: Optional[str] = None
    wall_seconds: float = 0.0

    # Convenience alias so callers can do result.tier_used_name
    def __str__(self) -> str:
        status = "✅ SUCCESS" if self.success else "❌ FAILED"
        return (
            f"[AgentTier] {status} | tier={self.tier_name}({self.tier_used}) "
            f"| score={self.score:.3f} | escalations={self.escalation_count}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# AgentTier
# ─────────────────────────────────────────────────────────────────────────────

class AgentTier:
    """
    Runs a cascade of policies (Greedy → Heuristic → LLM).
    Stops at the first success; otherwise escalates and injects failure context.
    """

    TIER_CLASSES: List[Type] = [GreedyPolicy, HeuristicPolicy, LLMPolicy]
    TIER_NAMES: List[str]    = ["GreedyPolicy", "HeuristicPolicy", "LLMPolicy"]

    # ── public entry point ────────────────────────────────────────────────────

    def run(
        self,
        env,                          # BlackstartCityEnv instance
        task_id: str = "city_cascade_recovery",
        seed: int = 1,
    ) -> EpisodeResult:
        """
        Run tiers in order.  Return an EpisodeResult from the first success
        (or the best attempt if all tiers fail).
        """
        t0 = time.perf_counter()
        failure_contexts: List[Dict[str, Any]] = []
        last_result: Optional[EpisodeResult] = None

        for tier_num, (PolicyCls, tier_name) in enumerate(
            zip(self.TIER_CLASSES, self.TIER_NAMES)
        ):
            agent = PolicyCls()
            result = self._run_episode(
                env=env,
                agent=agent,
                task_id=task_id,
                seed=seed,
                tier_num=tier_num,
                tier_name=tier_name,
                failure_contexts=list(failure_contexts),  # snapshot
            )
            last_result = result

            if result.success:
                result.escalation_count = tier_num
                result.failure_contexts = failure_contexts
                result.wall_seconds = time.perf_counter() - t0
                return result

            # Build failure context for the next tier
            context = {
                "failed_tier": tier_num,
                "failed_tier_name": tier_name,
                "failed_actions": result.action_history,
                "failure_reason": result.last_warning or "unknown",
                "score_at_failure": result.score,
            }
            failure_contexts.append(context)

            # Inject into env so the next tier's observations carry the history
            env.inject_failure_context(context)

        # All tiers failed — return the last result
        last_result.escalation_count = len(self.TIER_CLASSES) - 1
        last_result.failure_contexts = failure_contexts
        last_result.wall_seconds = time.perf_counter() - t0
        return last_result

    # ── episode runner ────────────────────────────────────────────────────────

    def _run_episode(
        self,
        env,
        agent,
        task_id: str,
        seed: int,
        tier_num: int,
        tier_name: str,
        failure_contexts: List[Dict[str, Any]],
    ) -> EpisodeResult:
        """
        Roll out one full episode.  Returns an EpisodeResult.
        Does NOT call inject_failure_context — that is the caller's job.
        """
        obs = env.reset(task_id=task_id, seed=seed)
        done = False
        action_history: List[Dict[str, Any]] = []
        last_warning: Optional[str] = None
        total_reward: float = 0.0

        while not done:
            # obs may be an object or a dict depending on env version
            obs_dict = obs if isinstance(obs, dict) else obs.model_dump()

            # Expose failure contexts accumulated so far inside the observation
            # (env.inject_failure_context handles this for the *next* reset;
            #  here we patch the live obs_dict so the current agent also sees
            #  any context that was injected before this tier started).
            if failure_contexts:
                obs_dict["failure_context"] = failure_contexts

            action = agent.act(obs_dict)
            obs, reward, done, info = env.step(action)
            total_reward += reward

            # Record compact action log
            action_dict = action if isinstance(action, dict) else action.model_dump()
            action_history.append(
                {
                    "step": len(action_history),
                    "action_type": action_dict.get("action_type"),
                    "target_id": action_dict.get("target_id"),
                    "reward": round(reward, 4),
                }
            )

            # Track the most recent warning
            obs_dict2 = obs if isinstance(obs, dict) else obs.model_dump()
            warnings = obs_dict2.get("warnings") or obs_dict2.get("active_warnings") or []
            if warnings:
                last_warning = warnings[-1]

        # Determine success: use info["success"] if available, else score >= 0.6
        final_obs_dict = obs if isinstance(obs, dict) else obs.model_dump()
        score = float(
            info.get("score")
            or final_obs_dict.get("reward_breakdown", {}).get("total", total_reward)
            or total_reward
        )
        success = bool(info.get("success", score >= 0.6))

        return EpisodeResult(
            tier_used=tier_num,
            tier_name=tier_name,
            success=success,
            score=score,
            escalation_count=0,          # filled in by caller
            action_history=action_history,
            last_warning=last_warning,
        )
