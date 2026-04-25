from __future__ import annotations

import random

from blackstart_city.models import CityTaskSpec, DifficultyLevel, Scenario
from blackstart_city.tasks.scenarios import SCENARIO_FAMILIES

TASK_ORDER = ["local_blackstart", "island_rejoin", "city_cascade_recovery", "mega_cascade"]

TASK_SPECS = {
    "local_blackstart": CityTaskSpec(
        task_id="local_blackstart",
        difficulty=DifficultyLevel.EASY,
        description="Restart a dark district and restore one hospital before backup expires.",
        max_steps=12,
    ),
    "island_rejoin": CityTaskSpec(
        task_id="island_rejoin",
        difficulty=DifficultyLevel.MEDIUM,
        description="Recover multiple energized islands and reconnect safe transmission paths.",
        max_steps=18,
    ),
    "city_cascade_recovery": CityTaskSpec(
        task_id="city_cascade_recovery",
        difficulty=DifficultyLevel.HARD,
        description="Recover the city while critical services degrade and unsafe reconnection can cause a second blackout.",
        max_steps=26,
    ),
    "mega_cascade": CityTaskSpec(
        task_id="mega_cascade",
        difficulty=DifficultyLevel.HARD,
        description=(
            "Extreme: two hospitals share one substation, conflicting council orders, "
            "8-minute backup start, school-zone downed line forbidden."
        ),
        max_steps=35,
    ),
}


def _jitter(rng: random.Random, base: int, pct: float, minimum: int = 1) -> int:
    """Return *base* varied by up to ±pct, floored at *minimum*."""
    return max(minimum, int(base * rng.uniform(1.0 - pct, 1.0 + pct)))


def _randomize_scenario(scenario: Scenario, seed: int) -> Scenario:
    """Apply deep procedural variation so no two seeds produce the same challenge.

    Varies:
      - Critical node backup timers (±20%) and demand (±15%)
      - Zone demand (±15%)
      - Line capacity (±12%) and randomly shifts hidden damage
      - Generator capacity (±12%)
      - News event trigger timing (±1 step)
      - Initial frequency jitter (59.8–60.2 Hz)
    """
    rng = random.Random(seed)

    # ── Backup timers and demand ──────────────────────────────────────────────
    for node in scenario.critical_nodes:
        node.backup_minutes_remaining = _jitter(rng, node.backup_minutes_remaining, 0.20, minimum=8)
        node.demand_mw = _jitter(rng, node.demand_mw, 0.15, minimum=2)

    # ── Zone demand ───────────────────────────────────────────────────────────
    for zone in scenario.zones:
        zone.demand_mw = _jitter(rng, zone.demand_mw, 0.15, minimum=2)

    # ── Line capacity + topology variation ────────────────────────────────────
    non_damaged_lines = [
        line for line in scenario.lines
        if not line.damaged and line.id not in scenario.hidden_damaged_lines
    ]
    for line in scenario.lines:
        line.capacity_mw = _jitter(rng, line.capacity_mw, 0.12, minimum=6)

    # Randomly add hidden damage to one previously-safe line (30% chance)
    if non_damaged_lines and rng.random() < 0.30:
        victim = rng.choice(non_damaged_lines)
        if victim.id not in scenario.hidden_damaged_lines:
            scenario.hidden_damaged_lines.append(victim.id)

    # ── Generator capacity ────────────────────────────────────────────────────
    for gen in scenario.generators:
        gen.capacity_mw = _jitter(rng, gen.capacity_mw, 0.12, minimum=4)

    # ── News event timing jitter (±1 step, minimum 1) ────────────────────────
    for event in scenario.news_events:
        event.trigger_step = max(1, event.trigger_step + rng.randint(-1, 1))

    # ── Initial frequency variation ───────────────────────────────────────────
    scenario.initial_frequency_hz = round(rng.uniform(59.8, 60.2), 2)

    return scenario


def get_scenario(task_id: str, seed: int | None = None, episode_index: int = 0) -> Scenario:
    if task_id not in SCENARIO_FAMILIES:
        raise KeyError(f"Unknown task_id: {task_id}")
    family = SCENARIO_FAMILIES[task_id]
    if seed is not None:
        idx = seed % len(family)
    else:
        idx = episode_index % len(family)
    scenario = family[idx].model_copy(deep=True)
    # Apply procedural variation so the agent cannot memorise fixed layouts.
    variation_seed = seed if seed is not None else episode_index
    return _randomize_scenario(scenario, variation_seed)
