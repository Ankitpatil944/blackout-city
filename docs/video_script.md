# 2-Minute Video Script

## 0:00 - 0:12

Black screen to city map.

Voiceover:

> This city is dark. Hospitals are on backup power. Telecom towers are failing. Water pressure is dropping. One unsafe reconnection can trigger a second collapse.

## 0:12 - 0:28

Show the `Blackstart City` UI.

Voiceover:

> Blackstart City is an OpenEnv benchmark where an AI agent acts as a restoration commander after a cascading blackout.

## 0:28 - 0:45

Highlight observations and actions.

Voiceover:

> The agent sees structured grid state, critical-service timers, line risk, and reserve margin. It takes discrete actions like starting generators, energizing substations, inspecting lines, restoring hospitals, and synchronizing islands.

## 0:45 - 1:05

Show a weak policy or comparison panel.

Voiceover:

> A weak policy restores load greedily and underperforms. It misses the importance of inspection and critical-service prioritization.

## 1:05 - 1:25

Show heuristic or improved rollout.

Voiceover:

> A stronger policy restores hospitals and telecom early, preserves reserve margin, inspects damaged lines, and avoids a second blackout.

## 1:25 - 1:42

Show score / reward improvement.

Voiceover:

> The reward is fully deterministic and decomposed into critical-service restoration, safe load recovery, stability, inspection quality, and catastrophe penalties.

## 1:42 - 2:00

Close on city map recovering.

Voiceover:

> Blackstart City is a benchmark for whether AI agents can safely restore civilization-scale systems under pressure. That is the capability we want to train, and that is what this environment measures.
