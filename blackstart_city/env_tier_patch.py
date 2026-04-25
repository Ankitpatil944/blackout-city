"""
blackstart_city/env_tier_patch.py
──────────────────────────────────
Drop-in mixin that adds inject_failure_context() to BlackstartCityEnv
WITHOUT touching the existing env.py file.

Usage (in env.py, add one import + inherit from the mixin):

    from blackstart_city.env_tier_patch import FailureContextMixin

    class BlackstartCityEnv(FailureContextMixin, ...existing bases...):
        ...

No other changes required.  All existing reset/step/state/close logic is
untouched.

──────────────────────────────────
If you prefer a monkey-patch approach (zero edits to env.py), do this
instead in your entry point:

    from blackstart_city.env import BlackstartCityEnv
    from blackstart_city.env_tier_patch import patch_env
    patch_env(BlackstartCityEnv)

──────────────────────────────────
"""

from __future__ import annotations

from typing import Any, Dict, List


# ─────────────────────────────────────────────────────────────────────────────
# Mixin
# ─────────────────────────────────────────────────────────────────────────────

class FailureContextMixin:
    """
    Adds failure-context injection to an OpenEnv-style environment.

    inject_failure_context(context)
        Stores context in self._failure_history.
        The next call to reset() clears the history (fresh episode).
        Every observation returned by step() has failure_context appended.

    _wrap_obs_with_failure_context(obs)
        Internal helper: patches an observation dict/object in place.

    Important: this mixin assumes the host class calls
        self._failure_history = []
    somewhere in __init__ (handled safely here via property).
    """

    # ── storage (lazy-init so we don't break __init__ of host class) ──────────

    @property
    def _failure_history(self) -> List[Dict[str, Any]]:
        if not hasattr(self, "_failure_history_store"):
            self._failure_history_store: List[Dict[str, Any]] = []
        return self._failure_history_store

    @_failure_history.setter
    def _failure_history(self, value: List[Dict[str, Any]]) -> None:
        self._failure_history_store = value

    # ── public API ────────────────────────────────────────────────────────────

    def inject_failure_context(self, context: Dict[str, Any]) -> None:
        """
        Store one tier's failure context.

        Parameters
        ----------
        context : dict with keys
            failed_tier        int   — tier index (0 = Greedy, 1 = Heuristic, 2 = LLM)
            failed_tier_name   str   — human-readable policy name
            failed_actions     list  — list of action dicts from that episode
            failure_reason     str   — last warning / reason for failure
            score_at_failure   float — final score of the failed attempt
        """
        self._failure_history.append(context)

    # ── hook: clear on reset ──────────────────────────────────────────────────

    def reset(self, *args, **kwargs):
        """
        Wraps the host's reset() to clear failure history on each new episode
        and patch the initial observation.
        """
        self._failure_history = []           # fresh episode → clear history
        obs = super().reset(*args, **kwargs)
        return self._wrap_obs_with_failure_context(obs)

    # ── hook: patch every step observation ───────────────────────────────────

    def step(self, action):
        """
        Wraps the host's step() to append failure_context to every observation.
        """
        obs, reward, done, info = super().step(action)
        return self._wrap_obs_with_failure_context(obs), reward, done, info

    # ── internal helper ───────────────────────────────────────────────────────

    def _wrap_obs_with_failure_context(self, obs):
        """
        Attach failure_context to an observation.

        Supports three obs types:
          • dict           — patch in place, return same dict
          • Pydantic model — patch model.__dict__ / .failure_context attr
          • other          — return unchanged (graceful degradation)
        """
        if not self._failure_history:
            return obs                       # nothing to inject

        history_snapshot = list(self._failure_history)

        if isinstance(obs, dict):
            obs["failure_context"] = history_snapshot
            return obs

        # Pydantic v1 / v2 model
        try:
            object.__setattr__(obs, "failure_context", history_snapshot)
            return obs
        except (AttributeError, TypeError):
            pass

        # Fallback: return a dict merge if obs has .dict()
        try:
            obs_dict = obs.model_dump()
            obs_dict["failure_context"] = history_snapshot
            return obs_dict
        except AttributeError:
            pass

        return obs  # graceful no-op


# ─────────────────────────────────────────────────────────────────────────────
# Monkey-patch helper (zero edits to env.py)
# ─────────────────────────────────────────────────────────────────────────────

def patch_env(env_cls) -> None:
    """
    Dynamically inject FailureContextMixin into an existing env class.

    Usage:
        from blackstart_city.env import BlackstartCityEnv
        from blackstart_city.env_tier_patch import patch_env
        patch_env(BlackstartCityEnv)

    After this call, BlackstartCityEnv has inject_failure_context() and
    all observations include failure_context when tiers have failed.

    This is idempotent — safe to call multiple times.
    """
    if FailureContextMixin in env_cls.__mro__:
        return  # already patched

    env_cls.__bases__ = (FailureContextMixin,) + env_cls.__bases__
