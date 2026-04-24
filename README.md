# 🏙️ Blackstart City

`Blackstart City` is an OpenEnv benchmark for **city-scale cascading blackout recovery**. 

An AI restoration commander operates inside a multi-role emergency command loop after a blackout. It must restart generation, energize substations, inspect risky lines, restore hospitals and critical services, coordinate scarce field resources, preserve public trust, and avoid a second collapse while the city degrades around it.

---

## 🏆 Hackathon Deliverables

> [!IMPORTANT]
> **Hugging Face Space:** [https://huggingface.co/spaces/YOUR-USERNAME/blackout-city](https://huggingface.co/spaces/YOUR-USERNAME/blackout-city) (Please ensure this is public and cloneable!)

* **Training Script:** [`blackstart_city/training/grpo_train.py`](./blackstart_city/training/grpo_train.py) (Unsloth + TRL GRPO)
* **Training Evidence:** See the embedded GRPO reward curves below.
* **Writeup / Blog:** [`docs/hf_mini_blog.md`](./docs/hf_mini_blog.md)
* **Pitch & Video:** [`docs/pitch_script.md`](./docs/pitch_script.md) & [`docs/video_script.md`](./docs/video_script.md)

---

## 🧠 Multi-Agent Architecture (Theme #1)

Instead of a single monolithic script, the environment explicitly surfaces recommendations from four specialized agents on every turn. This creates a deeply strategic planning loop (Theme #2) and tests world-modeling capabilities (Theme #3.1).

```mermaid
graph TD
    subgraph Env [OpenEnv Simulation]
        O[Observation State JSON]
    end

    subgraph Command Center [Multi-Agent Command Center Layer]
        O -->|Grid Stats and Frequencies| GO[Grid Operator]
        O -->|Hospital Backup Timers| EC[Emergency Coordinator]
        O -->|Damage and Crew Status| RD[Resource Dispatcher]
        O -->|Trust and Panic Levels| PIO[Public Info Officer]
        
        GO -->|Proposes Action| R((Role Recommendations))
        EC -->|Proposes Action| R
        RD -->|Proposes Action| R
        PIO -->|Proposes Action| R
    end

    subgraph AI [RL Policy]
        O --> M[Qwen 2.5 3B Model]
        R -.->|Strategic Context Injection| M
        M -->|Final JSON Action| A[BlackstartAction]
    end
    
    A -->|env.step| O
```

---

## 🚀 True RL Training: DeepSeek-Style GRPO

We moved past simple supervised fine-tuning and implemented **Group Relative Policy Optimization (GRPO)** using Unsloth and Hugging Face `TRL`. This removes the need for a VRAM-heavy Critic model and allows our Qwen-based policy to learn rapidly on a single GPU.

```mermaid
flowchart TD
    subgraph Generation [Rollout Phase]
        S[Dataset State JSON] --> LLM[Qwen 2.5 3B LoRA]
        LLM -->|Generate 4 Candidates| C1[Action Candidate 1-4]
    end

    subgraph Evaluation [Reward Engine Calculation]
        C1 --> R1[Format Reward: Valid JSON Schema]
        C1 --> R2[Alignment Reward: Matches Multi-Agent Consensus]
        C1 --> R3[Quality Reward: Tactical Proxy Logic]
        
        R3 -.->|Proxy Logic| T1[Shed load if freq < 59.5Hz]
        R3 -.->|Proxy Logic| T2[Rescue hospitals < 15m backup]
        R3 -.->|Proxy Logic| T3[Penalize greedy zone restoration]
    end

    subgraph Optimization [PPO / GRPO Update]
        R1 --> SUM[Sum Rewards per Action]
        R2 --> SUM
        R3 --> SUM
        SUM --> ADV[Compute Group Relative Advantage]
        ADV -->|Policy Gradient Update| LLM
    end
```

### GRPO Training Evidence

We track three independent multi-objective reward signals during training to ensure the model learns syntax, tactics, and overarching strategy simultaneously.

![GRPO Reward Curves](artifacts/blackstart-city-grpo/reward_curves.png)

---

## 🏗️ Environment Design

The environment uses typed, structured observations and actions.

### Task Families
| Task ID | Difficulty | What It Tests |
|---|---|---|
| `local_blackstart` | Easy | basic blackstart sequencing and restoring one hospital |
| `island_rejoin` | Medium | inspection, multi-island recovery, and safe synchronization |
| `city_cascade_recovery` | Hard | city-scale recovery under backup timers and cascading-failure risk |

### Action Space (`BlackstartAction`)
* `start_generator`, `energize_substation`, `inspect_line`, `close_line`, `open_line`
* `restore_critical_node`, `restore_zone`, `shed_zone`
* `sync_islands`, `activate_battery_support`, `publish_status`

### Observation Space (`BlackstartObservation`)
* **Physical Grid:** Generation, Load, Frequency, Reserve Margin.
* **Assets:** Generators, Substations, Lines, Population Zones.
* **Critical Nodes:** Hospitals, Telecom, Water, Emergency (with active countdown timers).
* **Command Center:** Coordination score, public trust, dispatch pressure, and multi-agent recommendations.

---

## ⚙️ Local Setup

```bash
python -m venv .venv
# On Windows: .venv\Scripts\Activate.ps1
source .venv/bin/activate

pip install --upgrade pip
pip install -e .[dev]
```

*(This project complies with the OpenEnv structure and utilizes `openenv-core`.)*

### Run Locally

Start the FastAPI server:
```bash
python -m server.app
```
Then navigate to: `http://127.0.0.1:8000/web`

### Validation & Testing
```bash
# Run unit tests
python -m pytest -q

# Run baseline inference
python inference.py

# Verify OpenEnv compliance
openenv validate
```

---
*Built for the OpenEnv Hackathon.*
