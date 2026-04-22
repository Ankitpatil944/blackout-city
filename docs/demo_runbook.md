# Demo Runbook

## Goal

Show that `Blackstart City` is:

- a real environment
- visually understandable
- reward-driven
- able to distinguish weak and strong policies

## Recommended Demo Flow

### 1. Open the Web UI

Open:

```text
http://127.0.0.1:8000/web
```

Say:

> This is a city-scale blackout recovery environment. The model must keep hospitals, telecom, water, and emergency services alive while restoring the grid safely.

### 2. Reset the Hard Scenario

Task:

- `city_cascade_recovery`
- seed `0`

Point out:

- hospital on backup
- telecom at risk
- damaged tie-lines
- reserve margin starts fragile

### 3. Run Policy Comparison

Click:

- `Run Greedy vs Heuristic`

Say:

> Here we compare a weaker greedy policy against a safer restoration policy on the exact same blackout seed.

Highlight:

- greedy score
- heuristic score
- catastrophe flag
- hospital failures

### 4. Live Heuristic Rollout

Click:

- `Reset Scenario`
- `Autoplay Heuristic`

While it runs, narrate:

- generator start
- feeder energization
- hospital restoration
- risky line inspection
- reserve margin preservation

### 5. Manual Intervention

Use:

- `Suggest Action`
- edit the JSON slightly if you want to show manual control
- `Submit Action`

Say:

> The environment is not a slideshow. Every action mutates the system state and changes the city outcome.

### 6. Close With Training

Mention:

- dataset builder
- TRL training scaffold
- Colab notebook
- before/after evaluation on fixed seeds

## Fallback Demo

If the UI is unavailable:

Run:

```powershell
python inference.py
python -m blackstart_city.training.eval
```

And narrate from the structured logs.

## Key Lines To Use

- “This benchmark punishes unsafe restoration, not just incomplete restoration.”
- “The same blackout seed produces different outcomes depending on policy quality.”
- “Our reward is deterministic, decomposed, and directly tied to critical infrastructure survival.”
