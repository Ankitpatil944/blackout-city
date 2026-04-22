# Blackstart City: Training AI To Restore A City After A Cascading Blackout

Large language models are increasingly tested on planning and tool use, but most benchmarks still avoid the hardest part of real-world operations: acting inside a fragile system where one wrong move can make everything worse.

That is the motivation behind **Blackstart City**.

## The Problem

After a city-scale blackout, recovery is not just about turning power back on.

Hospitals may be running on backup batteries. Telecom towers may be degrading. Water plants may be losing pressure. The power grid itself may be split into unstable islands, with hidden damage on key transmission lines.

An intelligent recovery agent has to decide:

- which generator to start first
- which feeder to energize
- which line to inspect before closing
- which services to restore before general load
- when it is safe to reconnect the city

If it restores load too aggressively, it can trigger a second collapse.

## The Environment

Blackstart City is an **OpenEnv** benchmark built around that problem.

The agent sees a structured state containing:

- available generation
- served load
- reserve margin
- frequency
- substations
- lines
- critical nodes like hospitals, telecom, water, and emergency services
- warnings and reward breakdowns

It takes discrete actions such as:

- `start_generator`
- `energize_substation`
- `inspect_line`
- `close_line`
- `restore_critical_node`
- `restore_zone`
- `sync_islands`
- `publish_status`

Every step changes the environment.

## What Makes It Interesting

The environment is built to reward **safe recovery**, not just fast recovery.

Rewards increase when the agent:

- restores critical services
- stabilizes reserve margin
- avoids unsafe reconnections
- inspects risky lines before acting

Rewards decrease when the agent:

- overloads lines
- loses hospital backup
- destabilizes the grid
- triggers a second blackout

This makes the benchmark highly interpretable and suitable for lightweight RL or fine-tuning workflows.

## Why We Built It

We wanted an environment that reflects real operational reasoning pressure:

- order-sensitive actions
- delayed consequences
- partial observability
- infrastructure dependencies
- objective evaluation

That makes Blackstart City a good fit for training and evaluating agents that need to act inside real systems instead of simply generating plausible text.

## Training Story

The repository includes:

- a heuristic baseline
- a dataset builder from environment trajectories
- a lightweight TRL training scaffold
- a Colab notebook for hackathon-style fine-tuning

This means the environment is not just demoable. It is trainable.

## Closing

Blackstart City asks a simple question:

**Can an AI restore a city safely when every early mistake risks making the blackout worse?**

That is the behavior we believe future operational agents will need, and that is the behavior this benchmark is designed to measure.
