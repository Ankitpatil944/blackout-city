from __future__ import annotations

from blackstart_city.models import CityTaskSpec, DifficultyLevel, Scenario
from blackstart_city.tasks.scenarios import SCENARIO_FAMILIES

TASK_ORDER = ["local_blackstart", "island_rejoin", "city_cascade_recovery"]

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
}


def get_scenario(task_id: str, seed: int | None = None, episode_index: int = 0) -> Scenario:
    if task_id not in SCENARIO_FAMILIES:
        raise KeyError(f"Unknown task_id: {task_id}")
    family = SCENARIO_FAMILIES[task_id]
    if seed is not None:
        idx = seed % len(family)
    else:
        idx = episode_index % len(family)
    return family[idx].model_copy(deep=True)
