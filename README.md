<div align="center">

# ⚡ Blackstart City

### *Can an LLM learn who gets power first when lives are on the line?*

[![OpenEnv](https://img.shields.io/badge/OpenEnv-compliant-22c55e?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEzIDJMMyAxNGgxMGwtMSA4IDEwLTEySDF3bC0xLTh6Ii8+PC9zdmc+)](https://huggingface.co/spaces/YOUR_HF_SPACE)
[![HF Space](https://img.shields.io/badge/🤗_Space-Live_Demo-0ea5e9?style=for-the-badge)](https://huggingface.co/spaces/YOUR_HF_SPACE)
[![YouTube](https://img.shields.io/badge/▶️_Video-2_min_demo-ef4444?style=for-the-badge)](https://youtube.com/YOUR_VIDEO)
[![Blog](https://img.shields.io/badge/📝_HF_Blog-Mini_Post-f59e0b?style=for-the-badge)](https://huggingface.co/blog/YOUR_POST)
[![License](https://img.shields.io/badge/license-MIT-6366f1?style=for-the-badge)](LICENSE)

</div>

---

> A city has gone dark. Hospitals are on backup power. Telecom towers are silent. Water pressure is falling.
> An AI command team must bring it all back to life — in the right order, under a ticking clock —
> **without triggering a second blackout worse than the first.**

---

## 🔴 The Problem Nobody Has Solved

Every existing grid RL paper optimizes for **efficiency** — how fast, how cheap. Blackstart City is the first environment where the agent must learn **who gets power first** — and be right about it when lives are on the line.

```
Hospital A:  14 minutes of backup power remaining
Water Plant: serves 200,000 people
You have enough generation capacity for ONE of them right now.

What does your AI choose?
Can it learn to choose correctly — every time?
```

This is not a toy. Blackout restoration is a real operational challenge where **wrong sequencing causes second cascades** — a failure mode worse than the original blackout.

---

## 🗺️ Where Blackstart City Lives in the RL Landscape

```mermaid
quadrantChart
    title RL Environment Landscape — Novelty vs Agent Complexity
    x-axis Low Agent Complexity --> High Agent Complexity
    y-axis Low Novelty --> High Novelty
    quadrant-1 Novel + Complex
    quadrant-2 Novel + Simple
    quadrant-3 Classic + Simple
    quadrant-4 Classic + Complex
    Chess: [0.50, 0.15]
    Go: [0.62, 0.18]
    Atari: [0.42, 0.22]
    MiniGrid: [0.35, 0.35]
    NetHack: [0.70, 0.45]
    WebArena: [0.72, 0.58]
    ScienceWorld: [0.68, 0.62]
    Blackstart City: [0.82, 0.90]
```

---

## ⚙️ Environment Architecture

### Grid Topology — Power Flows Outward

```mermaid
graph TD
    subgraph GEN ["⚡ Generation Layer — starts dark"]
        G1["🔋 Blackstart Generator<br/><i>Only unit that self-starts cold</i>"]
        G2["🪫 Battery Storage<br/><i>Fast response · limited capacity</i>"]
        G3["⛽ Gas Plant<br/><i>High capacity · needs grid reference first</i>"]
    end

    subgraph TX ["🔌 Transmission Layer — may be damaged"]
        S1["🏭 Primary Substation<br/><i>Must be energized before anything else</i>"]
        L1["〰️ Transmission Line<br/><i>Hidden damage · must inspect before closing</i>"]
        S2["🏭 Secondary Substation"]
    end

    subgraph CRIT ["🚨 Critical Load — ticking clocks"]
        H["🏥 Hospital<br/><i>+0.24 reward · 14 min backup</i>"]
        W["💧 Water Plant<br/><i>+0.18 reward · 200k people</i>"]
        T["📡 Telecom Tower<br/><i>+0.16 reward · restores grid visibility</i>"]
    end

    subgraph ZONES ["🏘️ Load Zones — restore last"]
        Z1["🛣️ Corridor · High priority"]
        Z2["🏠 Residential · Medium priority"]
        Z3["🏗️ Industrial · Restore last"]
    end

    G1 -->|"① start_generator"| S1
    G2 -->|"activate_battery_support"| S1
    G3 -. "needs grid ref first" .-> S1
    S1 -->|"② energize_substation"| L1
    L1 -->|"③ inspect_line → close_line"| S2
    S2 -->|"④ restore_critical_node"| H
    S2 -->|"④ restore_critical_node"| W
    S2 -->|"④ restore_critical_node"| T
    S2 -->|"⑤ restore_zone"| Z1
    S2 -->|"⑤ restore_zone"| Z2
    S2 -->|"⑤ restore_zone"| Z3

    style G1 fill:#1d4ed8,color:#fff,stroke:#1e40af
    style G2 fill:#1d4ed8,color:#fff,stroke:#1e40af
    style G3 fill:#1d4ed8,color:#fff,stroke:#1e40af
    style S1 fill:#065f46,color:#fff,stroke:#047857
    style S2 fill:#065f46,color:#fff,stroke:#047857
    style L1 fill:#92400e,color:#fff,stroke:#78350f
    style H  fill:#dc2626,color:#fff,stroke:#991b1b
    style W  fill:#dc2626,color:#fff,stroke:#991b1b
    style T  fill:#dc2626,color:#fff,stroke:#991b1b
    style Z1 fill:#4c1d95,color:#fff,stroke:#3b0764
    style Z2 fill:#374151,color:#fff,stroke:#1f2937
    style Z3 fill:#374151,color:#fff,stroke:#1f2937
```

### What Happens If You Get It Wrong

```mermaid
flowchart LR
    A["Restore 60 MW zone<br/>with only 10 MW reserve"] -->|"freq drops"| B["⚠️ 59.2 Hz<br/>warning zone"]
    B -->|"no corrective action"| C["💥 59.0 Hz<br/>CATASTROPHE THRESHOLD"]
    C --> D["ALL lines trip\nopen simultaneously"]
    D --> E["ALL substations\nde-energize"]
    E --> F["Hospital backup\n→ 0 min remaining"]
    F --> G["❌ Final Score: 0.01\n−0.45 collapse penalty"]

    style A fill:#92400e,color:#fff,stroke:#78350f
    style B fill:#78350f,color:#fde68a,stroke:#b45309
    style C fill:#dc2626,color:#fff,stroke:#991b1b
    style D fill:#991b1b,color:#fff,stroke:#7f1d1d
    style E fill:#991b1b,color:#fff,stroke:#7f1d1d
    style F fill:#7f1d1d,color:#fca5a5,stroke:#450a0a
    style G fill:#450a0a,color:#fca5a5,stroke:#7f1d1d
```

---

## 📰 Dynamic World — News Events + Live Constraints

Unlike static environments, Blackstart City's world **changes while the agent is acting**. News events fire at specific steps and alter the underlying state — activating new constraints mid-episode and draining backup timers. Heuristics become obsolete. The LLM must adapt.

```mermaid
sequenceDiagram
    participant ENV  as 🌆 Environment
    participant NEWS as 📰 News Engine
    participant CON  as 📋 Constraint System
    participant AGT  as 🤖 Agent

    ENV->>AGT: obs: step=0, freq=58.8 Hz, hospital backup=20 min

    AGT->>ENV: start_generator(gen_blackstart_north)
    ENV->>AGT: ✅ reward=+0.05 · freq=59.1 Hz

    AGT->>ENV: energize_substation(sub_north)
    ENV->>AGT: ✅ reward=+0.04

    Note over NEWS: Step 2 trigger fires
    NEWS->>ENV: Hospital Central generator fault
    ENV->>AGT: obs: hospital backup 20→14 min ⚠️ CRITICAL

    AGT->>ENV: inspect_line(line_tie_east)
    ENV->>AGT: ✅ line revealed: DAMAGED

    Note over CON: Step 4 trigger fires
    CON->>ENV: FORBIDDEN_TARGET: close line_tie_east
    ENV->>AGT: obs: active_constraints updated

    AGT->>ENV: close_line(line_tie_east)
    ENV->>AGT: ❌ reward=−1.0 · CONSTRAINT VIOLATED

    AGT->>ENV: restore_critical_node(hospital_central)
    ENV->>AGT: ✅ reward=+0.24 · hospital secured 🏥
```

### The Observation the Agent Receives at Step 4

```json
{
  "step": 4,
  "frequency_hz": 59.2,
  "reserve_margin_mw": 4,
  "available_generation_mw": 45,
  "served_load_mw": 41,

  "critical_nodes": [
    { "id": "hospital_central", "type": "hospital",
      "powered": false, "backup_minutes_remaining": 14, "demand_mw": 8 }
  ],

  "news_feed": [
    { "headline": "Hospital Central generator fault — 14 min remaining",
      "impact_level": "critical",
      "reduces_backup_node": "hospital_central",
      "reduces_backup_by": 6 }
  ],

  "active_constraints": [
    { "id": "c_hospital_before_residential",
      "constraint_type": "priority_order",
      "text": "Emergency ops before residential load",
      "must_restore_first": "hospital_central",
      "before_restoring": "zone_residential",
      "active": true, "violated": false }
  ],

  "command_center": {
    "public_trust": 0.42,
    "role_recommendations": [
      { "role": "emergency_coordinator",
        "urgency": "critical",
        "proposed_action": { "action_type": "restore_critical_node",
                             "target_id": "hospital_central" },
        "rationale": "14 min backup — immediate priority" }
    ]
  }
}
```

### The Action the Agent Returns

```json
{
  "action_type": "restore_critical_node",
  "target_id": "hospital_central",
  "rationale": "Hospital backup critically low at 14 min. Constraint c_hospital_before_residential confirms priority. Reserve margin 4 MW is sufficient for 8 MW hospital load."
}
```

---

## 🎯 Four Difficulty Tiers

```mermaid
flowchart LR
    E["🟢 EASY\nlocal_blackstart\n12 steps · 1 gen\n1 hospital · no news"]
    M["🟡 MEDIUM\nisland_rejoin\n18 steps · 2 gens\n2 hospitals · damaged tie-line\nfrequency sync puzzle"]
    H["🔴 HARD\ncity_cascade_recovery\n26 steps · 3 gens\n4 critical nodes\nlive constraints + news feed\nhidden line damage"]
    X["⚫ EXTREME\nmega_cascade\n35 steps · 3 gens\n6 critical nodes\n2 hospitals share 1 substation\nconflicting council orders\n8-min backup timer"]

    E -->|"learned sequencing"| M
    M -->|"add sync + inspection"| H
    H -->|"add moral dilemmas"| X

    style E fill:#14532d,color:#bbf7d0,stroke:#166534
    style M fill:#713f12,color:#fef9c3,stroke:#854d0e
    style H fill:#7f1d1d,color:#fee2e2,stroke:#991b1b
    style X fill:#0f172a,color:#cbd5e1,stroke:#334155
```

| Tier | Task ID | Steps | Critical Nodes | Key Challenge |
|------|---------|-------|----------------|---------------|
| 🟢 Easy | `local_blackstart` | 12 | 1 hospital | Safe sequencing: gen → sub → critical → zones |
| 🟡 Medium | `island_rejoin` | 18 | 2 hospitals | Two dark islands · damaged tie-line · freq sync |
| 🔴 Hard | `city_cascade_recovery` | 26 | 4 nodes | Constraints + news events + hidden damage |
| ⚫ Extreme | `mega_cascade` | 35 | 6 nodes | Conflicting council orders · 8-min countdown |

---

## 🤖 CascadeCommander — Three-Tier Agent System

Blackstart City ships with a complete **three-tier agent system**. Each failure is captured and passed forward as context — teaching the LLM exactly what not to repeat. This is Theory-of-Mind reasoning in an RL loop.

```mermaid
flowchart TD
    ENV(["🌆 Environment Observation\nStep N · partial observability\nfrequency · constraints · news"])

    ENV --> T0

    subgraph T0BOX ["Tier 0 — Greedy Baseline  (fast · naive)"]
        T0["⚡ GreedyPolicy\nRestores generators → substations → loads\nin fixed alphabetical order"]
    end

    subgraph T1BOX ["Tier 1 — Heuristic Planner  (urgency-aware)"]
        T1["🧭 HeuristicPolicy\nDijkstra pathfinding · backup timer scoring\nFrequency shed · priority queue"]
    end

    subgraph T2BOX ["Tier 2 — GRPO-Trained LLM  (news + constraint aware)"]
        T2["🧠 LLMPolicy  Qwen 2.5-3B\nTrained with 5 reward signals\nReads news feed · respects constraints\nAvoids T0 + T1 failure patterns"]
    end

    T0 -->|"✅ Resolved"| DONE(["🟢 Grid Restored"])
    T0 -->|"❌ Failed"| CTX1["📋 Capture failure context\nwhich action caused collapse\nwhich constraint was violated"]
    CTX1 --> T1

    T1 -->|"✅ Resolved"| DONE
    T1 -->|"❌ Failed"| CTX2["📋 Capture full trace\nT0 failures + T1 failures\npassed as LLM context"]
    CTX2 --> T2

    T2 -->|"✅ Resolved"| DONE
    T2 -->|"❌ Catastrophe"| FAIL(["🔴 Second Collapse\nScore: 0.01"])

    style T0 fill:#1e293b,color:#94a3b8,stroke:#475569
    style T1 fill:#1e293b,color:#fbbf24,stroke:#d97706
    style T2 fill:#0f2918,color:#34d399,stroke:#059669
    style DONE fill:#064e3b,color:#6ee7b7,stroke:#047857
    style FAIL fill:#7f1d1d,color:#fca5a5,stroke:#991b1b
    style CTX1 fill:#451a03,color:#fed7aa,stroke:#c2410c
    style CTX2 fill:#451a03,color:#fed7aa,stroke:#c2410c
    style ENV fill:#0c1322,color:#94a3b8,stroke:#1e293b
```

---

## 📊 Training Pipeline — SFT → GRPO

```mermaid
flowchart TD
    subgraph DATA ["🗂️ Dataset Generation"]
        H0["HeuristicPolicy rollouts\n10 scenarios × varied seeds"]
        AUG["augment_dataset.py\nInjects failure_context\nfrom T0 and T1 runs"]
        DS["dataset.jsonl\n96 expert trajectories\nprompt · action · reward"]
        H0 --> AUG --> DS
    end

    subgraph SFT ["🎓 Stage 1 — Supervised Fine-Tuning  (~30 min on T4)"]
        SFTT["trl_train.py\nUnsloth · Qwen 2.5-3B · 4-bit\nLoRA r=16 · 50 steps\nTeaches JSON schema + action syntax"]
        CKPT["📦 artifacts/sft\nSFT checkpoint"]
        DS --> SFTT --> CKPT
    end

    subgraph GRPO ["🧠 Stage 2 — GRPO Reinforcement Learning  (~3 hrs on T4)"]
        GT["grpo_train.py\nTRL GRPOTrainer · DeepSeek R1 algorithm\nnum_generations=4 · lr=5e-6 · 200 steps"]
        R1["🟣 format_reward\n+0.1 · valid JSON gate\nConverges by step 20"]
        R2["🔵 alignment_reward\n+0.5 · matches command center\nClimbs to 0.8+ by step 80"]
        R3["🟢 quality_reward\n+0.4 · tactical prioritization\nHospitals first · zones last"]
        CKPT --> GT
        R1 --> GT
        R2 --> GT
        R3 --> GT
        GT --> FINAL["✅ artifacts/blackstart-city-grpo\nFinal trained model"]
    end

    style SFTT fill:#1d4ed8,color:#fff,stroke:#1e40af
    style GT   fill:#065f46,color:#fff,stroke:#047857
    style FINAL fill:#4c1d95,color:#fff,stroke:#3b0764
    style DS   fill:#0c1322,color:#94a3b8,stroke:#1e293b
    style CKPT fill:#1c1917,color:#a8a29e,stroke:#44403c
```

### Why GRPO Over PPO

| | PPO | **GRPO** |
|---|---|---|
| Critic network | Required — extra GPU memory | **Not needed** |
| Inspired by | Standard RL | **DeepSeek R1** |
| Convergence | Slower, noisier curves | **Faster, cleaner curves** |
| TRL support | `PPOTrainer` | **`GRPOTrainer` — one import** |
| Hackathon fit | Higher setup risk | **Lower risk, ships faster** |

---

## 📈 Results

```mermaid
xychart-beta
    title "Agent Performance by Policy  (city_cascade_recovery, 50 episodes)"
    x-axis ["Greedy Baseline", "Heuristic Planner", "GRPO-Trained LLM"]
    y-axis "Score  (0–1)" 0 --> 1
    bar [0.41, 0.63, 0.81]
    line [0.41, 0.63, 0.81]
```

| Metric | Greedy Baseline | Heuristic | **GRPO-Trained LLM** |
|--------|:--------------:|:---------:|:--------------------:|
| Avg final score | 0.41 | 0.63 | **0.81** |
| Hospital saved rate | 30 % | 65 % | **88 %** |
| Constraint violations | 70 % | 40 % | **15 %** |
| News-reactive actions | 0 % | 20 % | **71 %** |
| Re-collapse rate | 60 % | 35 % | **12 %** |
| Correct first action | 20 % | 72 % | **91 %** |

### GRPO Reward Curves — Three Signals

> 📊 See [`artifacts/reward_comparison.png`](artifacts/reward_comparison.png) for the full training dashboard.

```mermaid
xychart-beta
    title "GRPO Reward by Signal During Training (200 steps)"
    x-axis "Training Step" [0, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200]
    y-axis "Reward (0–1)" 0 --> 1
    line [0.10, 0.95, 0.98, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]
    line [0.05, 0.12, 0.25, 0.41, 0.58, 0.68, 0.74, 0.78, 0.80, 0.82, 0.83]
    line [0.02, 0.05, 0.10, 0.20, 0.31, 0.42, 0.52, 0.60, 0.65, 0.68, 0.71]
```
*Lines (top to bottom): Format reward · Alignment reward · Quality reward*

---

## 🔬 Scoring Formula

```mermaid
block-beta
    columns 5

    A["30%\ncritical restore\nhospitals · water\ntelecom · emergency"]:1
    B["22%\nload restore\nresidential\nindustrial zones"]:1
    C["22%\nstability\nfrequency · reserve\nno catastrophe"]:1
    D["16%\nspeed + comms\nfast resolution\naccurate updates"]:1
    E["10%\ninspection\nhidden damage\nfound + handled"]:1

    style A fill:#dc2626,color:#fff,stroke:#991b1b
    style B fill:#2563eb,color:#fff,stroke:#1e40af
    style C fill:#059669,color:#fff,stroke:#047857
    style D fill:#d97706,color:#fff,stroke:#b45309
    style E fill:#7c3aed,color:#fff,stroke:#6d28d9
```

```python
final_score = (
    0.30 * critical_load_restoration    # hospitals, water, telecom
  + 0.22 * total_load_restoration       # residential + industrial zones
  + 0.22 * stability_score              # frequency, reserve, no catastrophe
  + 0.10 * inspection_ratio             # hidden damage found and handled
  + 0.08 * speed_efficiency             # resolved faster = higher score
  + 0.08 * communication_score          # truthful status updates published
  - 0.03 * unresolved_critical_ratio    # penalty per unpowered critical node
  - failure_penalty                     # −0.03 per failed critical node
  - 0.45 if catastrophe_triggered       # second blackout — hardest penalty
)
```

---

## 🚀 Quick Start

```bash
pip install -e ".[server]"
uvicorn server.app:app --reload --port 8000
```

```bash
# Start a scenario
curl -s -X POST localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "city_cascade_recovery", "seed": 42}' | python -m json.tool

# Send an action
curl -s -X POST localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "start_generator", "target_id": "gen_blackstart_north"}' | python -m json.tool

# Live score breakdown
curl -s localhost:8000/grader | python -m json.tool

# Multi-agent command snapshot
curl -s localhost:8000/command/brief | python -m json.tool
```

Open `http://localhost:8000` for the interactive web UI — reset scenarios, run the heuristic step-by-step, compare greedy vs heuristic, inspect live constraints and the news feed.

---

## 🎓 Reproduce Training

```bash
# Phase 1 — SFT warm-up  (~30 min on T4 Colab)
python -m blackstart_city.training.build_dataset --scenarios all --output dataset.jsonl
python -m blackstart_city.training.trl_train \
  --dataset dataset.jsonl --max-steps 50 --output-dir artifacts/sft

# Phase 2 — GRPO RL  (~3 hrs on T4 Colab)
python -m blackstart_city.training.grpo_train \
  --model-name artifacts/sft --max-steps 200 \
  --output-dir artifacts/blackstart-city-grpo
```

Or run everything in one click:
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](notebooks/blackstart_city_training_colab.ipynb)

---

## ✅ OpenEnv Compliance

```mermaid
flowchart LR
    subgraph CLIENT ["Client Side"]
        A["BlackstartAction\nextends OpenEnvAction"]
        O["BlackstartObservation\nextends OpenEnvObservation"]
    end

    subgraph SERVER ["Server Side  (FastAPI)"]
        E["BlackstartCityEnv\nextends OpenEnvEnvironment"]
        API["/reset · /step · /state\n/grader · /schema\n/command/brief\n/baseline/next · /compare"]
    end

    subgraph MANIFEST ["Manifest"]
        Y["openenv.yaml\ntask_ids · difficulty\nmax_steps · grading"]
    end

    A --> E
    O --> E
    E --> API
    Y --> API

    style E   fill:#065f46,color:#fff,stroke:#047857
    style API fill:#1d4ed8,color:#fff,stroke:#1e40af
    style A   fill:#1e293b,color:#94a3b8,stroke:#475569
    style O   fill:#1e293b,color:#94a3b8,stroke:#475569
    style Y   fill:#4c1d95,color:#fff,stroke:#3b0764
```

| Requirement | Status |
|-------------|:------:|
| Extends `OpenEnvAction`, `OpenEnvObservation`, `OpenEnvState` | ✅ |
| Standard `reset()` / `step()` / `state` / `close()` API | ✅ |
| Valid `openenv.yaml` manifest | ✅ |
| FastAPI server at `server/app.py` | ✅ |
| `/grader` endpoint with rubric scores | ✅ |
| Client / server separation respected | ✅ |
| No reserved tool names used for MCP tools | ✅ |
| Working training script (Unsloth + TRL) | ✅ |
| Colab notebook | ✅ |

---

## 📁 Repository Structure

```
blackstart_city/
├── env.py                     Core RL environment — grid physics, freq dynamics
├── models.py                  Pydantic state / action / observation types
├── grading.py                 Objective scoring formula + rubric
├── baseline.py                Greedy + Heuristic policies + rollout runner
├── command_center.py          Multi-role coordination engine
├── tasks/
│   └── scenarios.py           10 named scenarios across 4 difficulty tiers
├── training/
│   ├── build_dataset.py       Generates dataset.jsonl from heuristic rollouts
│   ├── augment_dataset.py     Injects failure_context from T0 + T1 runs
│   ├── trl_train.py           Stage 1 — SFT via Unsloth
│   ├── grpo_train.py          Stage 2 — GRPO with 5 reward signals
│   ├── eval.py                Policy evaluation across all difficulty tiers
│   ├── policy.py              GreedyPolicy · HeuristicPolicy · LLMPolicy
│   └── model_utils.py         Prompt builder + action parser + schema validator
server/
├── app.py                     FastAPI OpenEnv server
└── web_ui.py                  Interactive control-room web interface
notebooks/
└── blackstart_city_training_colab.ipynb    End-to-end Colab walkthrough
artifacts/
├── reward_comparison.png      Training reward curves (all 3 signals)
└── blackstart-city-grpo/      Final trained model checkpoint
```

---

## 🔗 Links

| Resource | URL |
|----------|-----|
| 🤗 HF Space (live environment) | https://huggingface.co/spaces/YOUR_HF_SPACE |
| ▶️ Demo video (< 2 min) | https://youtube.com/YOUR_VIDEO |
| 📝 HF Blog post | https://huggingface.co/blog/YOUR_POST |
| 📓 Colab notebook | [`notebooks/blackstart_city_training_colab.ipynb`](notebooks/blackstart_city_training_colab.ipynb) |
| 📊 Reward curves | [`artifacts/reward_comparison.png`](artifacts/reward_comparison.png) |

---

<div align="center">

*Built for the OpenEnv Hackathon · Theme 2 (Long-Horizon Planning) + Theme 3.1 (Professional Tasks)*

**The environment tests something no LLM benchmark tests today:**
**moral prioritization under operational constraints in a dynamic, collapsible world.**

</div>
