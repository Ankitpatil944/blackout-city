from __future__ import annotations

from collections import deque
from typing import Any

from blackstart_city.grading import build_reward_breakdown, clamp_score, compute_final_score, score_status_update
from blackstart_city.models import (
    ActionType,
    AssetHealth,
    BlackstartAction,
    BlackstartObservation,
    BlackstartState,
    CriticalNodeState,
    CriticalNodeType,
    GeneratorState,
    LineState,
    RewardBreakdown,
    Scenario,
    SubstationState,
    ZoneState,
)
from blackstart_city.tasks.catalog import TASK_ORDER, get_scenario


class BlackstartCityEnv:
    def __init__(self, max_steps: int | None = None):
        self._scenario: Scenario | None = None
        self._state: BlackstartState | None = None
        self._max_steps_override = max_steps
        self._task_counters = {task_id: 0 for task_id in TASK_ORDER}

    def reset(self, task_id: str | None = None, seed: int | None = None) -> BlackstartObservation:
        selected = task_id or TASK_ORDER[0]
        episode_index = self._task_counters[selected]
        self._task_counters[selected] += 1
        self._scenario = get_scenario(selected, seed=seed, episode_index=episode_index)
        max_steps = self._max_steps_override or self._scenario.task.max_steps

        self._state = BlackstartState(
            incident_id=self._scenario.incident_id,
            task_id=self._scenario.task.task_id,
            title=self._scenario.title,
            difficulty=self._scenario.task.difficulty,
            objective=self._scenario.objective,
            step_count=0,
            max_steps=max_steps,
            done=False,
            generators=[generator.model_copy(deep=True) for generator in self._scenario.generators],
            substations=[sub.model_copy(deep=True) for sub in self._scenario.substations],
            lines=[line.model_copy(deep=True) for line in self._scenario.lines],
            critical_nodes=[node.model_copy(deep=True) for node in self._scenario.critical_nodes],
            zones=[zone.model_copy(deep=True) for zone in self._scenario.zones],
            available_generation_mw=self._scenario.initial_available_generation_mw,
            served_load_mw=self._scenario.initial_served_load_mw,
            reserve_margin_mw=0,
            frequency_hz=self._scenario.initial_frequency_hz,
            unstable_islands=self._count_unstable_islands(),
            failed_critical_nodes=[],
            reward_breakdown=RewardBreakdown(current_score=0.01),
            last_action_result="Blackout scenario initialized.",
        )
        self._recompute_state()
        self._state.score = compute_final_score(self._state, self._scenario)
        self._state.reward_breakdown.current_score = self._state.score
        return self._build_observation(0.0)

    def step(self, action: BlackstartAction) -> tuple[BlackstartObservation, float, bool, dict[str, Any]]:
        state = self._require_state()
        scenario = self._require_scenario()
        if state.done:
            state.last_action_error = "Episode already completed"
            return self._build_observation(0.0), 0.0, True, self._info()

        previous_score = state.score
        action_signature = self._signature(action)
        previous_signature_count = state.action_history.count(action_signature)
        state.step_count += 1
        state.last_action_error = None

        critical_reward = 0.0
        load_reward = 0.0
        stability_reward = 0.0
        inspection_reward = 0.0
        communication_reward = 0.0
        action_penalty = 0.0
        catastrophe_penalty = 0.0

        result = ""

        match action.action_type:
            case ActionType.START_GENERATOR:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._start_generator(action.target_id or "")
            case ActionType.ENERGIZE_SUBSTATION:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._energize_substation(action.target_id or "")
            case ActionType.INSPECT_LINE:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._inspect_line(action.target_id or "")
            case ActionType.CLOSE_LINE:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._close_line(action.target_id or "")
            case ActionType.OPEN_LINE:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._open_line(action.target_id or "")
            case ActionType.RESTORE_CRITICAL_NODE:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._restore_critical_node(action.target_id or "")
            case ActionType.RESTORE_ZONE:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._restore_zone(action.target_id or "", action.requested_mw or 0)
            case ActionType.SHED_ZONE:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._shed_zone(action.target_id or "", action.requested_mw or 0)
            case ActionType.SYNC_ISLANDS:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._sync_islands(action.target_id or "")
            case ActionType.ACTIVATE_BATTERY_SUPPORT:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._activate_battery(action.target_id or "")
            case ActionType.PUBLISH_STATUS:
                result, critical_reward, load_reward, stability_reward, inspection_reward, communication_reward, action_penalty = self._publish_status(action)
            case _:
                result = f"Unsupported action type: {action.action_type.value}"
                action_penalty = 0.08

        state.action_history.append(action_signature)
        state.last_action_result = result
        self._recompute_state()
        self._passive_dynamics()
        catastrophe_penalty = self._maybe_trigger_catastrophe()
        self._recompute_state()
        state.score = compute_final_score(state, scenario)

        shaped = critical_reward + load_reward + stability_reward + inspection_reward + communication_reward
        score_delta = state.score - previous_score
        if previous_signature_count > 0:
            action_penalty += min(0.08, 0.03 + previous_signature_count * 0.01)
        if load_reward > 0.0 and any(not node.powered for node in state.critical_nodes):
            action_penalty += 0.03
            state.last_action_result += " Non-critical load was restored before all critical services were online."
        if action.action_type == ActionType.PUBLISH_STATUS and not any(node.powered for node in state.critical_nodes):
            action_penalty += 0.04
            state.last_action_result += " Status was published before visible critical-service recovery."
        if shaped <= 0.02 and score_delta <= 0.0 and action.action_type not in {ActionType.INSPECT_LINE, ActionType.PUBLISH_STATUS}:
            action_penalty += 0.03
        reward = shaped + score_delta - action_penalty - catastrophe_penalty
        state.cumulative_reward = round(min(10.0, state.cumulative_reward + reward), 3)
        state.cumulative_penalty = round(min(2.0, state.cumulative_penalty + action_penalty + catastrophe_penalty), 3)
        state.reward_breakdown = build_reward_breakdown(
            critical_restore_reward=critical_reward,
            load_restore_reward=load_reward,
            stability_reward=stability_reward,
            inspection_reward=inspection_reward,
            communication_reward=communication_reward,
            action_penalty=action_penalty,
            catastrophe_penalty=catastrophe_penalty,
            current_score=state.score,
        )

        state.done = self._is_resolved() or state.step_count >= state.max_steps or state.catastrophe_triggered
        return self._build_observation(round(reward, 2)), round(reward, 2), state.done, self._info()

    @property
    def state(self) -> BlackstartState:
        return self._require_state().model_copy(deep=True)

    def close(self) -> None:
        return None

    def _start_generator(self, target_id: str) -> tuple[str, float, float, float, float, float, float]:
        generator = self._find_generator(target_id)
        if generator is None:
            return "Generator target not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if generator.online:
            return "Generator already online.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.03
        if not generator.blackstart_capable and not any(unit.online for unit in self._require_state().generators):
            return "Generator cannot start without an energized system reference.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        generator.online = True
        generator.current_output_mw = generator.capacity_mw
        bus = self._find_substation(generator.bus)
        if bus is not None:
            bus.energized = True
        return f"Generator {target_id} started and is contributing power.", 0.0, 0.0, 0.08, 0.0, 0.0, 0.0

    def _energize_substation(self, target_id: str) -> tuple[str, float, float, float, float, float, float]:
        substation = self._find_substation(target_id)
        if substation is None:
            return "Substation target not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if substation.energized:
            return "Substation already energized.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.03
        if substation.damaged:
            return "Substation remains damaged and cannot be energized safely.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if not self._has_energized_path(target_id):
            return "No energized path exists to the target substation.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.07
        substation.energized = True
        return f"Substation {target_id} energized.", 0.0, 0.0, 0.06, 0.0, 0.0, 0.0

    def _inspect_line(self, target_id: str) -> tuple[str, float, float, float, float, float, float]:
        line = self._find_line(target_id)
        if line is None:
            return "Line target not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if line.inspected:
            return "Line already inspected.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.02
        line.inspected = True
        if line.id in self._require_scenario().hidden_damaged_lines:
            line.damaged = True
            return f"Inspection found hidden damage on {target_id}.", 0.0, 0.0, 0.02, 0.08, 0.0, 0.0
        return f"Inspection cleared {target_id} for safe operation.", 0.0, 0.0, 0.01, 0.06, 0.0, 0.0

    def _close_line(self, target_id: str) -> tuple[str, float, float, float, float, float, float]:
        line = self._find_line(target_id)
        if line is None:
            return "Line target not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if line.closed and not line.tripped:
            return "Line already closed.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.02
        if line.damaged and not line.inspected:
            line.tripped = True
            line.closed = False
            self._destabilize(line.to_bus)
            return "Unsafe close attempt tripped a damaged line and destabilized the receiving bus.", 0.0, 0.0, -0.05, 0.0, 0.0, 0.12
        line.closed = True
        line.tripped = False
        return f"Line {target_id} closed.", 0.0, 0.0, 0.03, 0.0, 0.0, 0.0

    def _open_line(self, target_id: str) -> tuple[str, float, float, float, float, float, float]:
        line = self._find_line(target_id)
        if line is None:
            return "Line target not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        line.closed = False
        line.tripped = False
        return f"Line {target_id} opened to isolate risk.", 0.0, 0.0, 0.04, 0.0, 0.0, 0.0

    def _restore_critical_node(self, target_id: str) -> tuple[str, float, float, float, float, float, float]:
        node = self._find_critical_node(target_id)
        if node is None:
            return "Critical node target not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if node.powered:
            return "Critical node already restored.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.02
        feeder = self._find_substation(node.feeder_bus)
        if feeder is None or not feeder.energized:
            return "Cannot restore critical node before feeder is energized.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        state = self._require_state()
        if state.reserve_margin_mw < node.demand_mw:
            state.frequency_hz -= 0.25
            return "Critical load added without enough reserve margin, stressing the island.", 0.0, 0.0, -0.05, 0.0, 0.0, 0.1
        node.powered = True
        if node.type == CriticalNodeType.HOSPITAL:
            return f"Hospital {target_id} restored to grid power.", 0.24, 0.0, 0.06, 0.0, 0.0, 0.0
        if node.type == CriticalNodeType.WATER:
            return f"Water plant {target_id} restored.", 0.18, 0.0, 0.05, 0.0, 0.0, 0.0
        if node.type == CriticalNodeType.TELECOM:
            return f"Telecom node {target_id} restored.", 0.16, 0.0, 0.04, 0.0, 0.0, 0.0
        return f"Emergency services node {target_id} restored.", 0.18, 0.0, 0.04, 0.0, 0.0, 0.0

    def _restore_zone(self, target_id: str, requested_mw: int) -> tuple[str, float, float, float, float, float, float]:
        zone = self._find_zone(target_id)
        if zone is None:
            return "Zone target not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        feeder = self._find_substation(zone.feeder_bus)
        if feeder is None or not feeder.energized:
            return "Cannot restore zone before feeder is energized.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        state = self._require_state()
        restore_mw = min(requested_mw, zone.demand_mw * (100 - zone.restored_pct) // 100)
        if restore_mw <= 0:
            return "Zone already fully restored.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.02
        if state.reserve_margin_mw < restore_mw:
            state.frequency_hz -= 0.2
            return "Zone restoration attempted without adequate margin, causing instability.", 0.0, 0.0, -0.04, 0.0, 0.0, 0.1
        zone.restored_pct = min(100, zone.restored_pct + int((restore_mw / zone.demand_mw) * 100))
        weight = 0.08 if zone.priority.value == "corridor" else 0.05 if zone.priority.value == "residential" else 0.03
        return f"Zone {target_id} restored by {restore_mw} MW.", 0.0, weight, 0.02, 0.0, 0.0, 0.0

    def _shed_zone(self, target_id: str, requested_mw: int) -> tuple[str, float, float, float, float, float, float]:
        zone = self._find_zone(target_id)
        if zone is None:
            return "Zone target not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if zone.restored_pct == 0:
            return "Zone already fully shed.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.02
        shed_pct = min(zone.restored_pct, int((requested_mw / zone.demand_mw) * 100))
        zone.restored_pct = max(0, zone.restored_pct - max(5, shed_pct))
        state = self._require_state()
        state.frequency_hz = min(60.0, state.frequency_hz + 0.08)
        return f"Load shed from {target_id} to recover stability.", 0.0, 0.0, 0.08, 0.0, 0.0, 0.0

    def _sync_islands(self, target_id: str) -> tuple[str, float, float, float, float, float, float]:
        line = self._find_line(target_id)
        state = self._require_state()
        if line is None:
            return "Tie-line target not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if line.damaged and not line.inspected:
            return "Tie-line must be inspected before synchronization.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if state.frequency_hz < 59.7 or state.reserve_margin_mw < 6:
            state.frequency_hz -= 0.15
            return "Synchronization attempted under weak stability conditions.", 0.0, 0.0, -0.05, 0.0, 0.0, 0.12
        line.closed = True
        line.tripped = False
        if self._find_substation(line.from_bus):
            self._find_substation(line.from_bus).island_id = self._find_substation(line.to_bus).island_id
        return "Grid islands synchronized through the tie-line.", 0.0, 0.03, 0.12, 0.0, 0.0, 0.0

    def _activate_battery(self, target_id: str) -> tuple[str, float, float, float, float, float, float]:
        generator = self._find_generator(target_id)
        if generator is None:
            return "Battery asset not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        generator.online = True
        generator.current_output_mw = generator.capacity_mw
        return f"Battery support {target_id} activated.", 0.0, 0.0, 0.07, 0.0, 0.0, 0.0

    def _publish_status(self, action: BlackstartAction) -> tuple[str, float, float, float, float, float, float]:
        state = self._require_state()
        scenario = self._require_scenario()
        previous = score_status_update(state.published_status, scenario, state)
        current = score_status_update(action.status_update, scenario, state)
        state.published_status = action.status_update
        communication_reward = max(0.0, current - previous)
        penalty = 0.0 if current >= previous else 0.03
        return "Published public recovery status.", 0.0, 0.0, 0.0, 0.0, communication_reward, penalty

    def _passive_dynamics(self) -> None:
        state = self._require_state()
        newly_failed: list[str] = []
        for node in state.critical_nodes:
            if not node.powered and node.backup_minutes_remaining > 0:
                node.backup_minutes_remaining = max(0, node.backup_minutes_remaining - 3)
            if (
                not node.powered
                and node.backup_minutes_remaining == 0
                and node.id not in state.failed_critical_nodes
            ):
                state.failed_critical_nodes.append(node.id)
                newly_failed.append(node.id)
        for node_id in newly_failed:
            node = next(item for item in state.critical_nodes if item.id == node_id)
            if node.type == CriticalNodeType.HOSPITAL:
                state.hospital_failures += 1

        if not any(node.powered for node in state.critical_nodes if node.type == CriticalNodeType.TELECOM):
            state.frequency_hz = max(58.8, state.frequency_hz - 0.03)
        if not any(node.powered for node in state.critical_nodes if node.type == CriticalNodeType.WATER):
            state.cumulative_penalty += 0.01

        for generator in state.generators:
            if generator.online and generator.current_output_mw == 0:
                generator.current_output_mw = generator.capacity_mw

    def _maybe_trigger_catastrophe(self) -> float:
        state = self._require_state()
        if state.frequency_hz < 59.0:
            state.catastrophe_triggered = True
            for line in state.lines:
                line.closed = False
                line.tripped = True
            for substation in state.substations:
                if not substation.id.startswith("gen_"):
                    substation.energized = False
            for node in state.critical_nodes:
                node.powered = False
            for zone in state.zones:
                zone.restored_pct = max(0, zone.restored_pct - 60)
            state.last_action_error = "Second collapse triggered by unstable restoration sequence."
            return 0.25
        return 0.0

    def _recompute_state(self) -> None:
        state = self._require_state()
        energized_buses = {sub.id for sub in state.substations if sub.energized}
        online_generation = sum(generator.current_output_mw for generator in state.generators if generator.online)
        critical_load = sum(node.demand_mw for node in state.critical_nodes if node.powered)
        zone_load = sum(int(zone.demand_mw * (zone.restored_pct / 100)) for zone in state.zones)

        state.available_generation_mw = online_generation
        state.served_load_mw = critical_load + zone_load
        state.reserve_margin_mw = max(0, online_generation - state.served_load_mw)

        if online_generation == 0:
            state.frequency_hz = 58.8
        else:
            margin_ratio = state.reserve_margin_mw / max(1, online_generation)
            state.frequency_hz = round(min(60.02, max(58.8, 59.4 + margin_ratio * 1.1)), 2)

        for line in state.lines:
            line.current_flow_mw = 0
            if line.closed and not line.tripped:
                from_energized = line.from_bus in energized_buses or self._generator_bus_online(line.from_bus)
                to_energized = line.to_bus in energized_buses or self._generator_bus_online(line.to_bus)
                if from_energized or to_energized:
                    downstream = self._bus_connected_load(line.to_bus) + self._bus_connected_load(line.from_bus)
                    line.current_flow_mw = min(line.capacity_mw, downstream)
                    if downstream > line.capacity_mw:
                        line.tripped = True
                        line.closed = False
                        self._destabilize(line.to_bus)
                        state.frequency_hz = max(58.9, state.frequency_hz - 0.18)

        state.unstable_islands = self._count_unstable_islands()
        state.score = clamp_score(compute_final_score(state, self._require_scenario()))

    def _has_energized_path(self, target_bus: str) -> bool:
        state = self._require_state()
        sources = {sub.id for sub in state.substations if sub.energized}
        sources |= {generator.bus for generator in state.generators if generator.online}
        if target_bus in sources:
            return True
        queue = deque(sources)
        visited = set(sources)
        adjacency = {}
        for line in state.lines:
            if line.closed and not line.tripped:
                adjacency.setdefault(line.from_bus, []).append(line.to_bus)
                adjacency.setdefault(line.to_bus, []).append(line.from_bus)
        while queue:
            bus = queue.popleft()
            for neighbor in adjacency.get(bus, []):
                if neighbor == target_bus:
                    return True
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return False

    def _bus_connected_load(self, bus: str) -> int:
        state = self._require_state()
        total = sum(node.demand_mw for node in state.critical_nodes if node.feeder_bus == bus and node.powered)
        total += sum(int(zone.demand_mw * (zone.restored_pct / 100)) for zone in state.zones if zone.feeder_bus == bus)
        return total

    def _generator_bus_online(self, bus: str) -> bool:
        return any(generator.bus == bus and generator.online for generator in self._require_state().generators)

    def _destabilize(self, bus: str) -> None:
        substation = self._find_substation(bus)
        if substation is not None:
            substation.energized = False

    def _count_unstable_islands(self) -> int:
        state = self._state
        if state is None:
            return 0
        return sum(1 for sub in state.substations if sub.energized and any(line.tripped for line in state.lines if sub.id in {line.from_bus, line.to_bus}))

    def _is_resolved(self) -> bool:
        state = self._require_state()
        critical_ok = all(node.powered for node in state.critical_nodes)
        stable = state.frequency_hz >= 59.7 and not state.catastrophe_triggered
        zone_ok = sum(zone.restored_pct for zone in state.zones) >= 180
        communicated = score_status_update(state.published_status, self._require_scenario(), state) >= 0.06
        return critical_ok and stable and zone_ok and communicated

    def _build_observation(self, reward: float) -> BlackstartObservation:
        state = self._require_state()
        warnings = list(self._require_scenario().warnings)
        for node in state.critical_nodes:
            if not node.powered and node.backup_minutes_remaining <= 15:
                warnings.append(f"{node.id} backup below 15 minutes.")
        if state.frequency_hz < 59.6:
            warnings.append("Grid frequency below safe restoration threshold.")
        if any(line.tripped for line in state.lines):
            warnings.append("One or more lines are tripped.")

        return BlackstartObservation(
            incident_id=state.incident_id,
            task_id=state.task_id,
            title=state.title,
            objective=state.objective,
            difficulty=state.difficulty,
            step=state.step_count,
            steps_remaining=max(0, state.max_steps - state.step_count),
            available_generation_mw=state.available_generation_mw,
            served_load_mw=state.served_load_mw,
            reserve_margin_mw=state.reserve_margin_mw,
            frequency_hz=state.frequency_hz,
            unstable_islands=state.unstable_islands,
            generators=[item.model_copy(deep=True) for item in state.generators],
            substations=[item.model_copy(deep=True) for item in state.substations],
            lines=[item.model_copy(deep=True) for item in state.lines],
            critical_nodes=[item.model_copy(deep=True) for item in state.critical_nodes],
            zones=[item.model_copy(deep=True) for item in state.zones],
            warnings=warnings,
            allowed_actions=list(ActionType),
            last_action_result=state.last_action_result,
            last_action_error=state.last_action_error,
            reward_breakdown=state.reward_breakdown.model_copy(deep=True),
            reward=reward,
            done=state.done,
        )

    def _info(self) -> dict[str, Any]:
        state = self._require_state()
        return {
            "incident_id": state.incident_id,
            "task_id": state.task_id,
            "score": clamp_score(state.score),
            "resolved": self._is_resolved(),
            "catastrophe_triggered": state.catastrophe_triggered,
            "hospital_failures": state.hospital_failures,
            "failed_critical_nodes": list(state.failed_critical_nodes),
        }

    def _find_generator(self, target_id: str) -> GeneratorState | None:
        for generator in self._require_state().generators:
            if generator.id == target_id:
                return generator
        return None

    def _find_substation(self, target_id: str) -> SubstationState | None:
        for substation in self._require_state().substations:
            if substation.id == target_id:
                return substation
        return None

    def _find_line(self, target_id: str) -> LineState | None:
        for line in self._require_state().lines:
            if line.id == target_id:
                return line
        return None

    def _find_critical_node(self, target_id: str) -> CriticalNodeState | None:
        for node in self._require_state().critical_nodes:
            if node.id == target_id:
                return node
        return None

    def _find_zone(self, target_id: str) -> ZoneState | None:
        for zone in self._require_state().zones:
            if zone.id == target_id:
                return zone
        return None

    def _signature(self, action: BlackstartAction) -> str:
        return f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}"

    def _require_state(self) -> BlackstartState:
        if self._state is None:
            raise RuntimeError("Call reset() before using the environment.")
        return self._state

    def _require_scenario(self) -> Scenario:
        if self._scenario is None:
            raise RuntimeError("Scenario not initialized.")
        return self._scenario
