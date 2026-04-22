# Blackstart City Pitch Script

## Opening Hook

We built a city on the edge of collapse, and trained an AI to bring it back to life.

In `Blackstart City`, the model is not answering prompts. It is acting as a restoration commander after a cascading blackout. Hospitals are on backup power, telecom towers are degrading, water pressure is dropping, and one unsafe reconnection can trigger a second collapse.

## Problem

Most existing agent benchmarks are either:

- too static
- too toy-like
- or too narrow

Real critical-infrastructure recovery is not like that. It is sequential, partially observable, safety-critical, and full of delayed consequences.

An action that seems locally correct can destabilize the whole system.

## Environment

Our environment is fully structured and OpenEnv-compliant.

The agent observes:

- available generation
- reserve margin
- grid frequency
- substations
- transmission lines
- hospitals
- telecom nodes
- water plants
- restoration warnings

The agent takes discrete actions like:

- start generator
- energize substation
- inspect line
- close line
- restore hospital
- restore zone load
- sync islands
- publish status

Every action mutates the world.

## Why It Is Hard

The challenge is not just restoring power.

The challenge is restoring the city **in the right order**:

- hospitals before non-critical load
- inspections before risky reconnection
- enough reserve margin before restoration
- synchronization before tying islands together

If the model acts greedily, it can overload a line, trip a feeder, and restart the blackout.

## Reward

Our reward is deterministic and decomposed into:

- critical-service restoration
- load restoration
- stability and reserve margin
- inspection quality
- communication quality
- catastrophe penalties

This makes training and evaluation objective and easy to visualize.

## Demo Walkthrough

First, we show a weaker policy.

It restores load aggressively, ignores inspection, and underperforms.

Then we show the stronger heuristic baseline and the live environment:

- it restores hospitals early
- stabilizes the core grid
- avoids unsafe line closures
- reaches a higher score

The same seed, same city, same blackout, different policy quality.

## Training Story

We also include a lightweight HF TRL training path:

- roll out trajectories from the environment
- train on structured JSON observations and actions
- compare before vs after on fixed seeds

This gives us measurable improvement in score, service survival, and collapse avoidance.

## Closing

`Blackstart City` is not just a simulator. It is a benchmark for whether AI agents can safely restore civilization-scale systems under pressure.

That is the behavior we want to train, and that is what this environment measures.
