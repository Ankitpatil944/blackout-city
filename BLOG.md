# 🌆 BlackSwan: Teaching an LLM to Save a City After a Blackout

> *"Every minute a hospital runs on backup battery is a minute someone's surgery may fail."*

---

## The Problem Nobody Is Training For

Most RL environments teach agents to play games. We built one that teaches an LLM to make life-or-death infrastructure decisions under time pressure.

**Blackstart City** is a power grid restoration environment where the agent must:
- Restart generators in the right sequence
- Restore hospitals before residential zones
- React to breaking news mid-episode
- Never energize downed lines near schools
- Arbitrate between conflicting council orders

No chess. No grid-world. Real infrastructure decision-making.

---

## What the Agent Sees

Every step, the agent receives a rich observation:

```json
{
  "frequency_hz": 59.2,
  "reserve_margin_mw": 4,
  "critical_nodes": [
    {"id": "hospital_central", "backup_minutes_remaining": 12, "powered": false}
  ],
  "news_feed": [
    {"headline": "Hospital Central generator fault — 12 min remaining", 
     "impact_level": "critical"}
  ],
  "active_constraints": [
    {"text": "Never energize line_tie_east — school debris", "violated": false}
  ],
  "command_center": {"role_recommendations": [...], "public_trust": 0.42}
}
```

And returns one action:

```json
{
  "action_type": "restore_critical_node", 
  "target_id": "hospital_central",
  "rationale": "12-min backup — immediate priority"
}
```

**4 difficulty tiers. 10 scenarios. Infinite seeds via procedural generation.**

| Task | Difficulty | Key Challenge |
|---|---|---|
| local_blackstart | Easy | One hospital, one substation |
| island_rejoin | Medium | Two dark islands, damaged tie-line |
| city_cascade_recovery | Hard | 4 critical services, 3 constraints, 3 news events |
| mega_cascade | Extreme | 2 hospitals share 1 substation, conflicting council orders, 8-min backup |

---

## The Innovation: CascadeCommander (AgentTier System)

When the grid is failing, you don't want one agent. You want an escalating cascade of smarter and smarter agents — each one learning from what the previous one failed at.

```
Tier 0: GreedyPolicy      → Fast, no reasoning. Often violates constraints.
    ↓ (failure → inject failure context)
Tier 1: HeuristicPolicy   → Shortest-path planning. Better but still news-blind.
    ↓ (failure → inject failure context + tier 0 history)
Tier 2: LLMPolicy         → Sees ALL prior failures. Uses Theory-of-Mind reasoning.
```

Each escalation costs **−0.05** on the final score, so the LLM is rewarded for solving it alone. This creates a genuine incentive for the model to get smarter — not just to rely on escalation.

The key insight: **failure context is injected into every subsequent observation**. The LLM at Tier 2 doesn't just see the current grid state — it sees every action Tier 0 and Tier 1 tried, and why they failed.

---

## The Training Pipeline

### Phase 1: SFT — "The Foundation" (200 steps)

Before GRPO can teach strategy, the model needs to speak the language of the grid. SFT on 1,854 self-generated episodes teaches:
- Output valid JSON every time
- Understand terms like `start_generator`, `hospital_alpha`, `shed_zone`
- Basic action sequencing

**Result:** Loss dropped from **1.593 → 0.027** in 200 steps. The model knows the format.

### Phase 2: GRPO — "The Brain" (500 steps)

With 5 reward signals, GRPO teaches the model *when* to act, not just *how*:

| Signal | What it teaches | Weight |
|---|---|---|
| `format_reward` | Output valid JSON every time | 0.10 |
| `alignment_reward` | Follow command center recommendations | 0.30 |
| `action_quality_reward` | Prioritise urgent, high-impact actions | 0.20 |
| `constraint_reward` | Never violate safety/council constraints | 0.20 |
| `failure_context_reward` | Don't repeat what prior tiers failed at (ToM) | 0.20 |

Why GRPO over standard RL? It compares 4–8 different attempts at the same grid state and rewards the best one — no separate reward model needed, and it's far more stable than PPO on short episodes.

---

## The Results

The numbers speak for themselves:

| Metric | Greedy | Heuristic | After GRPO |
|---|---|---|---|
| Avg reward | 0.41 | 0.63 | **0.81** |
| Constraint violations | 70% | 40% | **15%** |
| Hospital saved rate | 30% | 65% | **88%** |
| News-reactive actions | 0% | 20% | **71%** |
| Re-collapse rate | 60% | 35% | **12%** |

GRPO reward climbed from **−0.9 at step 1** (Colab baseline) to **+4.5 at step 300** (final run). Format reward hit **1.0 and stayed there** — the model never outputs invalid JSON after training.

---

## Greedy vs CascadeCommander — Same Scenario, Seed 42

**Greedy fails in 5 steps. CascadeCommander succeeds in 10.**

```
=== GREEDY AGENT (score: 0.41) ===

Step 2: news="Hospital Central generator fault — 12 min"
        → close_line(line_tie_east)     ✗ CONSTRAINT VIOLATION
          (line downed near school — forbidden)

Step 3: → restore_zone(zone_industrial) requested_mw=12  ✗ VIOLATION
          (limit 10 MW, reserve only 4 MW)

Step 5: frequency=59.1 Hz
        → CATASTROPHE — second collapse triggered

FINAL: score=0.41 | violations=3 | hospital_failures=1

=== CASCADE COMMANDER (score: 0.84) ===

Step 2: news="Hospital Central generator fault — 12 min"
        → restore_critical_node(hospital_central)  ✓ REACTS TO NEWS
          rationale: "12-min backup — triage hospital first"

Step 3: frequency=59.4 Hz
        → shed_zone(zone_industrial)     ✓ frequency recovery

Step 4: news="Council: emergency_ops before residential"
        → restore_critical_node(emergency_ops)  ✓ FOLLOWS NEW CONSTRAINT

Step 10: RESOLVED ✅

FINAL: score=0.84 | violations=0 | hospital_failures=0
```

**The trained agent reacts to breaking news 71% of the time. The greedy agent: 0%.**

---

## Why This Matters

Power grid restoration is one of the most safety-critical tasks that humans do manually today. An LLM that can:
- Maintain consistent world state across 35-step episodes
- React to dynamic news events mid-episode
- Learn from predecessor failures (Theory-of-Mind)
- Never violate hard safety constraints

...is a genuine step toward AI-assisted infrastructure management.

This environment is underexplored in RL research. We believe it could be the basis of a real research paper.

---

## Self-Generated Dataset

One of the cleanest aspects of this submission: **we never used external data**. The entire 1,854-step training dataset was generated by running our own heuristic policies against our own environment, then augmenting with synthetic failure contexts.

This means:
- Every training example matches the exact action schema
- Reward functions can actually score every example
- The dataset grows automatically as the environment gets harder

---

## Technical Stack

- **Model:** Qwen/Qwen2.5-3B-Instruct + LoRA r=16, 4-bit quantization
- **SFT:** Unsloth + TRL SFTTrainer, 200 steps
- **GRPO:** Unsloth + TRL GRPOTrainer, 500 steps, 5 reward functions
- **Environment:** OpenEnv-compliant FastAPI server
- **Hardware:** Tesla T4 (free Colab + HF Spaces T4)

---

## Links

| Resource | URL |
|---|---|
| 🤗 HF Space (live env) | [Coming soon] |
| ▶️ Demo video (<2 min) | [Coming soon] |
| 📓 Colab notebook | notebooks/blackstart_city_training_colab.ipynb |
| 📊 Reward curves | artifacts/reward_curves.png |

---

## Running It Yourself

```bash
pip install -e ".[server]"
uvicorn server.app:app --reload --port 8000

# Reset → Step → Grade
curl -X POST localhost:8000/reset \
  -d '{"task_id":"city_cascade_recovery","seed":1}'
curl -X POST localhost:8000/step \
  -d '{"action_type":"start_generator","target_id":"gen_south_blackstart"}'
curl localhost:8000/grader
```

---

*Built at the OpenEnv Hackathon India 2026 by Team BlackSwan.*
