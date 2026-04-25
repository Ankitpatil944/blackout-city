# AgentTier Integration Guide

## Files Added (no existing files modified)

```
blackstart_city/
  agent_tier.py       ← AgentTier, EpisodeResult, LLMPolicy stub
  env_tier_patch.py   ← FailureContextMixin + patch_env()
  tier_grading.py     ← apply_tier_penalty(), TierAwareGrader

server/
  tier_router.py      ← FastAPI router with /run_with_tiers endpoint
```

---

## Step 1 — Wire inject_failure_context into env.py

Choose **Option A** (one-line mixin) or **Option B** (zero-edit monkey-patch).

### Option A — preferred (one import + one base class change in env.py)

```python
# env.py  — add at top
from blackstart_city.env_tier_patch import FailureContextMixin

# Change your class line from:
class BlackstartCityEnv(OpenEnvEnvironment):
# to:
class BlackstartCityEnv(FailureContextMixin, OpenEnvEnvironment):
```

That's it. `inject_failure_context()`, the patched `reset()`, and the
patched `step()` are all inherited.  Your existing `reset()` / `step()`
bodies are **completely untouched** — the mixin calls `super()`.

### Option B — zero edits to env.py (monkey-patch at startup)

```python
# In server/app.py or inference.py — before the env is first instantiated:
from blackstart_city.env import BlackstartCityEnv
from blackstart_city.env_tier_patch import patch_env
patch_env(BlackstartCityEnv)   # idempotent, safe to call multiple times
```

---

## Step 2 — Mount the /run_with_tiers endpoint in server/app.py

```python
# server/app.py  — add these two lines anywhere after `app = FastAPI(...)`
from server.tier_router import tier_router
app.include_router(tier_router)
```

---

## Step 3 — Wire the tier penalty into grading.py

No edits to grading.py required.  Use the wrapper:

```python
from blackstart_city.tier_grading import TierAwareGrader

grader = TierAwareGrader()

# After AgentTier.run():
result = tier.run(env, task_id="city_cascade_recovery", seed=1)
grade  = grader.grade_from_result(
    raw_score=result.score,
    escalation_count=result.escalation_count,
)
print(f"Raw score:          {grade.raw_score:.3f}")
print(f"Escalation penalty: {grade.escalation_penalty:.3f}")
print(f"Final score:        {grade.final_score:.3f}")
```

---

## Quick-start (full example)

```python
from blackstart_city.env import BlackstartCityEnv
from blackstart_city.env_tier_patch import patch_env
from blackstart_city.agent_tier import AgentTier
from blackstart_city.tier_grading import TierAwareGrader

# Option B patch — zero changes to env.py
patch_env(BlackstartCityEnv)

env    = BlackstartCityEnv()
tier   = AgentTier()
grader = TierAwareGrader()

result = tier.run(env, task_id="city_cascade_recovery", seed=1)
grade  = grader.grade_from_result(result.score, escalation_count=result.escalation_count)

print(f"Solved at tier:    {result.tier_name} (tier {result.tier_used})")
print(f"Final score:       {grade.final_score:.3f}")
print(f"Escalations:       {result.escalation_count}")
print(f"Penalty applied:   -{grade.escalation_penalty:.3f}")
print(result)
```

Expected output (Greedy solves it):
```
Solved at tier:    GreedyPolicy (tier 0)
Final score:       0.810
Escalations:       0
Penalty applied:   -0.000
[AgentTier] ✅ SUCCESS | tier=GreedyPolicy(0) | score=0.810 | escalations=0
```

Expected output (needs Heuristic):
```
Solved at tier:    HeuristicPolicy (tier 1)
Final score:       0.723
Escalations:       1
Penalty applied:   -0.050
[AgentTier] ✅ SUCCESS | tier=HeuristicPolicy(1) | score=0.773 | escalations=1
```

---

## REST API

```
POST /run_with_tiers
Content-Type: application/json

{ "task_id": "city_cascade_recovery", "seed": 1 }
```

Response:
```json
{
  "tier_used": 1,
  "tier_name": "HeuristicPolicy",
  "success": true,
  "score": 0.773,
  "escalation_count": 1,
  "escalation_penalty": 0.05,
  "adjusted_score": 0.723,
  "action_history": [ ... ],
  "failure_contexts": [
    {
      "failed_tier": 0,
      "failed_tier_name": "GreedyPolicy",
      "failed_actions": [ ... ],
      "failure_reason": "Frequency below 59.1 Hz — catastrophe triggered",
      "score_at_failure": 0.31
    }
  ],
  "last_warning": null,
  "wall_seconds": 0.412
}
```

---

## Escalation Penalty Table

| Tier that solved it | Escalations | Penalty | Adjustment |
|---|---|---|---|
| Greedy (Tier 0)    | 0 | 0.000 | none |
| Heuristic (Tier 1) | 1 | −0.050 | −0.050 |
| LLM (Tier 2)       | 2 | −0.100 | −0.100 |
| All failed         | 2 | −0.100 | applied to best attempt |

---

## Replacing the LLMPolicy stub

In `blackstart_city/agent_tier.py`, replace the body of `LLMPolicy.act()`:

```python
def act(self, observation: dict) -> BlackstartAction:
    # Failure context from previous tiers (if any):
    failure_ctx = observation.get("failure_context", [])

    # Build your prompt — failure_ctx is already structured
    from blackstart_city.training.policy import call_llm
    return call_llm(observation)
```

The `failure_context` key is automatically present in every observation
once `inject_failure_context()` has been called — the LLM receives a full
list of what each previous tier tried and why it failed.
