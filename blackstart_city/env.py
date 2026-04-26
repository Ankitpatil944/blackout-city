from __future__ import annotations

from collections import deque
from typing import Any

from blackstart_city.command_center import coordination_status_text, initial_command_center, refresh_command_center, score_arbitration
from blackstart_city.grading import build_reward_breakdown, clamp_score, compute_final_score, compute_rubric_score, score_status_update
from blackstart_city.models import (
    ActionType,
    BlackstartAction,
    BlackstartObservation,
    BlackstartState,
    Constraint,
    ConstraintType,
    CriticalNodeState,
    CriticalNodeType,
    GeneratorState,
    LineState,
    RewardBreakdown,
    RubricScore,
    Scenario,
    SubstationState,
    ZoneState,
)
from blackstart_city.tasks.catalog import TASK_ORDER, get_scenario

# Minutes consumed per action type — used for backup battery drain in _passive_dynamics.
ACTION_DURATION_MINUTES: dict[ActionType, int] = {
    ActionType.START_GENERATOR: 5,
    ActionType.ENERGIZE_SUBSTATION: 3,
    ActionType.INSPECT_LINE: 4,
    ActionType.CLOSE_LINE: 2,
    ActionType.OPEN_LINE: 1,
    ActionType.RESTORE_CRITICAL_NODE: 4,
    ActionType.RESTORE_ZONE: 4,
    ActionType.SHED_ZONE: 2,
    ActionType.SYNC_ISLANDS: 6,
    ActionType.ACTIVATE_BATTERY_SUPPORT: 3,
    ActionType.PUBLISH_STATUS: 2,
}


class BlackstartCityEnv:
    def __init__(self, max_steps: int | None = None):
        self._scenario: Scenario | None = None
        self._state: BlackstartState | None = None
        self._max_steps_override = max_steps
        # Build from TASK_ORDER so any newly registered task_id works without a code change here.
        self._task_counters = {task_id: 0 for task_id in TASK_ORDER}
        # Also catch unknown task_ids at runtime by defaulting to 0.
        import collections
        self._task_counters = collections.defaultdict(int, self._task_counters)
        self._failure_history: list[dict] = []

    def inject_failure_context(self, context: dict) -> None:
        """Store one tier's failure context for the next tier to see."""
        self._failure_history.append(context)

    def get_failure_context(self) -> list[dict]:
        """Return accumulated failure contexts from previous tiers."""
        return list(self._failure_history)

    def reset(self, task_id: str | None = None, seed: int | None = None) -> BlackstartObservation:
        selected = task_id or TASK_ORDER[0]
        episode_index = self._task_counters[selected]
        self._task_counters[selected] += 1
        self._scenario = get_scenario(selected, seed=seed, episode_index=episode_index)
        max_steps = self._max_steps_override or self._scenario.task.max_steps
        # Failure contexts are episode-local — a fresh reset must not leak
        # the previous tier's failure history into the new scenario.
        self._failure_history = []

        self._state = BlackstartState.model_validate({
            "incident_id": self._scenario.incident_id,
            "task_id": self._scenario.task.task_id,
            "title": self._scenario.title,
            "difficulty": self._scenario.task.difficulty,
            "objective": self._scenario.objective,
            "step_count": 0,
            "max_steps": max_steps,
            "done": False,
            "generators": [generator.model_dump() for generator in self._scenario.generators],
            "substations": [sub.model_dump() for sub in self._scenario.substations],
            "lines": [line.model_dump() for line in self._scenario.lines],
            "critical_nodes": [node.model_dump() for node in self._scenario.critical_nodes],
            "zones": [zone.model_dump() for zone in self._scenario.zones],
            "available_generation_mw": self._scenario.initial_available_generation_mw,
            "served_load_mw": self._scenario.initial_served_load_mw,
            "reserve_margin_mw": 0,
            "frequency_hz": self._scenario.initial_frequency_hz,
            "unstable_islands": self._count_unstable_islands(),
            "failed_critical_nodes": [],
            "reward_breakdown": RewardBreakdown(current_score=0.01).model_dump(),
            "last_action_result": "Blackout scenario initialized.",
        })
        self._recompute_state()
        self._state.command_center = initial_command_center(self._state)
        self._state.active_constraints = list(self._scenario.constraints)
        self._state.news_feed = []
        self._state.constraint_violations = 0
        self._state.score = compute_final_score(self._state, self._scenario)
        self._state.reward_breakdown.current_score = self._state.score
        self._state.rubric = compute_rubric_score(self._state, self._scenario)
        return self._build_observation(0.0)

    def step(self, action: BlackstartAction) -> tuple[BlackstartObservation, float, bool, dict[str, Any]]:
        state = self._require_state()
        scenario = self._require_scenario()
        if state.done:
            state.last_action_error = "Episode already completed"
            return self._build_observation(0.0), 0.0, True, self._info()

        previous_score = state.score
        previous_hospital_failures = state.hospital_failures
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

        # --- Constraint check: penalise violations before applying the action ---
        # Saved separately because the match block below reassigns action_penalty
        # from the handler's return value — without saving here, constraint penalties
        # would be silently overwritten and never reach the reward calculation.
        constraint_penalty = self._check_constraints(action)

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

        # Add constraint penalty on top of handler penalty — must happen after match so
        # the handler cannot overwrite it.
        action_penalty += constraint_penalty

        state.action_history.append(action_signature)
        state.last_action_result = result
        self._recompute_state()
        self._passive_dynamics(action.action_type)
        catastrophe_penalty = self._maybe_trigger_catastrophe()
        self._recompute_state()
        # Decay frequency stress offset once per step (75% persistence → ~4-step half-life)
        state.frequency_offset = round(state.frequency_offset * 0.75, 3)
        self._update_command_center(
            action=action,
            critical_reward=critical_reward,
            load_reward=load_reward,
            inspection_reward=inspection_reward,
            communication_reward=communication_reward,
            action_penalty=action_penalty,
            catastrophe_penalty=catastrophe_penalty,
            previous_hospital_failures=previous_hospital_failures,
        )
        state.score = compute_final_score(state, scenario)

        # --- Arbitration reward: score conflict resolution BEFORE refresh ---
        arbitration_reward = score_arbitration(state, action)

        shaped = critical_reward + load_reward + stability_reward + inspection_reward + communication_reward + arbitration_reward
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
        # Scale shaped rewards by 0.5 to prevent double-counting with score_delta:
        # both signals capture the same progress events (e.g. hospital restore → shaped 0.24
        # AND score_delta ≈ +0.07 from critical_ratio jump). Halving shaped keeps dense
        # per-action guidance without overwhelming the holistic score signal.
        reward = 0.5 * shaped + score_delta - action_penalty - catastrophe_penalty
        state.cumulative_reward = round(max(-2.0, min(10.0, state.cumulative_reward + reward)), 3)
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
        state.reward_breakdown.arbitration_reward = arbitration_reward

        state.done = self._is_resolved() or state.step_count >= state.max_steps or state.catastrophe_triggered

        # --- Terminal reward shaping (#11) ---
        if state.done:
            if self._is_resolved():
                reward += 1.0
            if state.catastrophe_triggered:
                reward -= 0.5
            if state.hospital_failures > 0:
                reward -= 0.2 * state.hospital_failures

        # --- Rubric update every step ---
        state.rubric = compute_rubric_score(state, scenario)

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
        if generator.blackstart_capable:
            generator.current_output_mw = generator.capacity_mw
            generator.startup_steps_remaining = 0
        else:
            generator.current_output_mw = generator.capacity_mw // 2
            generator.startup_steps_remaining = 1
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
            state.frequency_offset -= 0.25
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
            state.frequency_offset -= 0.2
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
        return f"Load shed from {target_id} to recover stability.", 0.0, 0.0, 0.08, 0.0, 0.0, 0.0

    def _sync_islands(self, target_id: str) -> tuple[str, float, float, float, float, float, float]:
        line = self._find_line(target_id)
        state = self._require_state()
        if line is None:
            return "Tie-line target not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if line.damaged and not line.inspected:
            return "Tie-line must be inspected before synchronization.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if state.frequency_hz < 59.7 or state.reserve_margin_mw < 6:
            state.frequency_offset -= 0.15
            return "Synchronization attempted under weak stability conditions.", 0.0, 0.0, -0.05, 0.0, 0.0, 0.12
        line.closed = True
        line.tripped = False
        from_sub = self._find_substation(line.from_bus)
        to_sub = self._find_substation(line.to_bus)
        if from_sub is not None and to_sub is not None:
            old_island = from_sub.island_id
            new_island = to_sub.island_id
            for sub in self._require_state().substations:
                if sub.island_id == old_island:
                    sub.island_id = new_island
        return "Grid islands synchronized through the tie-line.", 0.0, 0.03, 0.12, 0.0, 0.0, 0.0

    def _activate_battery(self, target_id: str) -> tuple[str, float, float, float, float, float, float]:
        generator = self._find_generator(target_id)
        if generator is None:
            return "Battery asset not found.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        if generator.online:
            return "Battery support already active.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.03
        if not any(unit.online for unit in self._require_state().generators):
            return "Battery support cannot activate without an energized system reference.", 0.0, 0.0, 0.0, 0.0, 0.0, 0.08
        generator.online = True
        generator.current_output_mw = generator.capacity_mw
        return f"Battery support {target_id} activated.", 0.0, 0.0, 0.07, 0.0, 0.0, 0.0

    def _publish_status(self, action: BlackstartAction) -> tuple[str, float, float, float, float, float, float]:
        state = self._require_state()
        scenario = self._require_scenario()
        previous = score_status_update(state.published_status, scenario, state)
        current = score_status_update(action.status_update, scenario, state)
        state.published_status = action.status_update
        state.published_status_step = state.step_count
        communication_reward = max(0.0, current - previous)
        penalty = 0.0 if current >= previous else 0.03
        return "Published public recovery status.", 0.0, 0.0, 0.0, 0.0, communication_reward, penalty

    def _passive_dynamics(self, action_type: ActionType | None = None) -> None:
        state = self._require_state()
        scenario = self._require_scenario()
        drain_minutes = ACTION_DURATION_MINUTES.get(action_type, 3) if action_type else 3

        newly_failed: list[str] = []
        for node in state.critical_nodes:
            if not node.powered and node.backup_minutes_remaining > 0:
                node.backup_minutes_remaining = max(0, node.backup_minutes_remaining - drain_minutes)
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
            state.frequency_offset -= 0.03
        if not any(node.powered for node in state.critical_nodes if node.type == CriticalNodeType.WATER):
            state.cumulative_penalty += 0.01

        # Generator ramp-up: tick down startup_steps_remaining each step.
        for generator in state.generators:
            if generator.online and generator.startup_steps_remaining > 0:
                generator.startup_steps_remaining -= 1
                if generator.startup_steps_remaining == 0:
                    generator.current_output_mw = generator.capacity_mw
            elif generator.online and generator.current_output_mw == 0:
                generator.current_output_mw = generator.capacity_mw

        # --- News feed: reveal events scheduled for this step ---
        self._reveal_news_events()

    def _maybe_trigger_catastrophe(self) -> float:
        state = self._require_state()
        # Only fire when the grid was actually energized — a pre-blackstart state
        # with zero generation should never count as a "second collapse".
        if state.frequency_hz < 59.1 and state.available_generation_mw > 0:  # Realistic cascade threshold
            state.catastrophe_triggered = True
            state.frequency_offset = 0.0  # Clear transient stress; grid is fully collapsed
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

        # Base frequency from reserve margin ratio; frequency_offset captures transient stress
        # (unsafe actions, line trips, bad syncs) that persists and decays across steps.
        if online_generation == 0:
            base_freq = 58.8
        else:
            margin_ratio = state.reserve_margin_mw / max(1, online_generation)
            base_freq = 59.4 + margin_ratio * 1.1
        state.frequency_hz = round(min(60.02, max(58.8, base_freq + state.frequency_offset)), 2)

        for line in state.lines:
            line.current_flow_mw = 0
            if line.closed and not line.tripped:
                from_energized = line.from_bus in energized_buses or self._generator_bus_online(line.from_bus)
                to_energized = line.to_bus in energized_buses or self._generator_bus_online(line.to_bus)
                if from_energized or to_energized:
                    # Power flows from the energized side toward the load side.
                    # Use whichever end carries load — taking the SUM of both
                    # double-counts demand that crosses the line only once.
                    flow = max(
                        self._bus_connected_load(line.to_bus),
                        self._bus_connected_load(line.from_bus),
                    )
                    line.current_flow_mw = min(line.capacity_mw, flow)
                    if flow > line.capacity_mw:
                        line.tripped = True
                        line.closed = False
                        self._destabilize(line.to_bus)
                        state.frequency_offset -= 0.18

        state.unstable_islands = self._count_unstable_islands()
        state.score = clamp_score(compute_final_score(state, self._require_scenario()))

    def _update_command_center(
        self,
        *,
        action: BlackstartAction,
        critical_reward: float,
        load_reward: float,
        inspection_reward: float,
        communication_reward: float,
        action_penalty: float,
        catastrophe_penalty: float,
        previous_hospital_failures: int,
    ) -> None:
        state = self._require_state()
        center = state.command_center
        trust_delta = 0.0
        coordination_delta = 0.0

        if critical_reward > 0.0:
            trust_delta += 0.02
            coordination_delta += 0.05
        if inspection_reward > 0.0:
            coordination_delta += 0.04
        if communication_reward > 0.0:
            trust_delta += min(0.08, communication_reward + 0.01)
            coordination_delta += 0.03
        if load_reward > 0.0 and any(not node.powered for node in state.critical_nodes):
            trust_delta -= 0.02
            coordination_delta -= 0.05
        if action_penalty >= 0.08:
            coordination_delta -= 0.03
        if action.action_type == ActionType.PUBLISH_STATUS and not any(node.powered for node in state.critical_nodes):
            trust_delta -= 0.05
            coordination_delta -= 0.04
        if state.frequency_hz < 59.7:
            trust_delta -= 0.02
            coordination_delta -= 0.03
        if state.frequency_hz < 59.5:
            trust_delta -= 0.04
            coordination_delta -= 0.05
        if state.reserve_margin_mw < 6:
            coordination_delta -= 0.03
        if state.hospital_failures > previous_hospital_failures:
            delta = state.hospital_failures - previous_hospital_failures
            trust_delta -= 0.12 * delta
            coordination_delta -= 0.08 * delta
        if not any(node.powered for node in state.critical_nodes if node.type == CriticalNodeType.TELECOM):
            trust_delta -= 0.015
        if not any(node.powered for node in state.critical_nodes if node.type == CriticalNodeType.WATER):
            trust_delta -= 0.015
        if catastrophe_penalty > 0.0 or state.catastrophe_triggered:
            trust_delta -= 0.25
            coordination_delta -= 0.25
        if self._all_critical_restored():
            trust_delta += 0.015
            coordination_delta += 0.02

        center.public_trust = round(min(0.99, max(0.01, center.public_trust + trust_delta)), 2)
        center.coordination_score = round(min(0.99, max(0.01, center.coordination_score + coordination_delta)), 2)
        refresh_command_center(state)

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
        # Zone check: at least 60% of total zone demand must be restored.
        total_zone_demand = sum(zone.demand_mw for zone in state.zones)
        restored_zone_demand = sum(zone.demand_mw * (zone.restored_pct / 100) for zone in state.zones)
        zone_ok = (restored_zone_demand / total_zone_demand) >= 0.60 if total_zone_demand else True
        communicated = score_status_update(state.published_status, self._require_scenario(), state) >= 0.06
        return critical_ok and stable and zone_ok and communicated

    def _compute_allowed_actions(self) -> list[ActionType]:
        """Return only the action types that are currently valid given the state."""
        state = self._require_state()
        allowed: list[ActionType] = []
        has_online_gen = any(g.online for g in state.generators)
        if any(g.blackstart_capable and not g.online for g in state.generators):
            allowed.append(ActionType.START_GENERATOR)
        elif has_online_gen and any(not g.online for g in state.generators):
            allowed.append(ActionType.START_GENERATOR)
        if any(not s.energized and not s.damaged for s in state.substations):
            allowed.append(ActionType.ENERGIZE_SUBSTATION)
        if any(not line.inspected for line in state.lines):
            allowed.append(ActionType.INSPECT_LINE)
        if any(not line.closed and not line.tripped for line in state.lines):
            allowed.append(ActionType.CLOSE_LINE)
        if any(line.closed for line in state.lines):
            allowed.append(ActionType.OPEN_LINE)
        if any(not n.powered for n in state.critical_nodes):
            allowed.append(ActionType.RESTORE_CRITICAL_NODE)
        if any(z.restored_pct < 100 for z in state.zones):
            allowed.append(ActionType.RESTORE_ZONE)
        if any(z.restored_pct > 0 for z in state.zones):
            allowed.append(ActionType.SHED_ZONE)
        # SYNC_ISLANDS is only meaningful for an open tie-line whose two end
        # substations sit on different islands.
        island_by_sub = {s.id: s.island_id for s in state.substations}
        if any(
            (not line.closed and not line.tripped)
            and line.from_bus in island_by_sub
            and line.to_bus in island_by_sub
            and island_by_sub[line.from_bus] != island_by_sub[line.to_bus]
            for line in state.lines
        ):
            allowed.append(ActionType.SYNC_ISLANDS)
        if any(not g.online for g in state.generators if not g.blackstart_capable):
            allowed.append(ActionType.ACTIVATE_BATTERY_SUPPORT)
        allowed.append(ActionType.PUBLISH_STATUS)
        return allowed

    def _all_critical_restored(self) -> bool:
        return all(node.powered for node in self._require_state().critical_nodes)

    def _build_observation(self, reward: float) -> BlackstartObservation:
        state = self._require_state()
        warnings = list(self._require_scenario().warnings)
        for node in state.critical_nodes:
            if not node.powered:
                if node.backup_minutes_remaining <= 10:
                    warnings.append(f"{node.id} CRITICAL: backup under 10 minutes!")
                elif node.backup_minutes_remaining <= 15:
                    warnings.append(f"{node.id} backup below 15 minutes.")
        if state.frequency_hz < 59.6:
            warnings.append("Grid frequency below safe restoration threshold.")
        if state.frequency_hz < 59.2:
            warnings.append("ALERT: Frequency near second-collapse threshold.")
        if any(line.tripped for line in state.lines):
            warnings.append("One or more lines are tripped.")
        if state.reserve_margin_mw < 6:
            warnings.append("Reserve margin critically low — risk of overload.")

        return BlackstartObservation.model_validate({
            "incident_id": state.incident_id,
            "task_id": state.task_id,
            "title": state.title,
            "objective": state.objective,
            "difficulty": state.difficulty,
            "step": state.step_count,
            "steps_remaining": max(0, state.max_steps - state.step_count),
            "available_generation_mw": state.available_generation_mw,
            "served_load_mw": state.served_load_mw,
            "reserve_margin_mw": state.reserve_margin_mw,
            "frequency_hz": state.frequency_hz,
            "unstable_islands": state.unstable_islands,
            "generators": [item.model_dump() for item in state.generators],
            "substations": [item.model_dump() for item in state.substations],
            "lines": [item.model_dump() for item in state.lines],
            "critical_nodes": [item.model_dump() for item in state.critical_nodes],
            "zones": [item.model_dump() for item in state.zones],
            "warnings": warnings,
            "allowed_actions": self._compute_allowed_actions(),
            "last_action_result": state.last_action_result,
            "last_action_error": state.last_action_error,
            "reward_breakdown": state.reward_breakdown.model_dump(),
            "command_center": state.command_center.model_dump(),
            "active_constraints": [c.model_dump() for c in state.active_constraints],
            "news_feed": [e.model_dump() for e in state.news_feed],
            "rubric": state.rubric.model_dump(),
            "reward": reward,
            "done": state.done,
        })

    def _info(self) -> dict:
        state = self._require_state()
        return {
            "incident_id": state.incident_id,
            "task_id": state.task_id,
            "score": clamp_score(state.score),
            "resolved": self._is_resolved(),
            "done": state.done,
            "step_count": state.step_count,
            "max_steps": state.max_steps,
            "catastrophe_triggered": state.catastrophe_triggered,
            "hospital_failures": state.hospital_failures,
            "failed_critical_nodes": list(state.failed_critical_nodes),
            "public_trust": state.command_center.public_trust,
            "coordination_score": state.command_center.coordination_score,
            "coordination_status": coordination_status_text(state.command_center),
            "constraint_violations": state.constraint_violations,
            "rubric": state.rubric.model_dump(mode="json"),
            "news_count": len(state.news_feed),
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

    # ── Constraint enforcement ────────────────────────────────────────────────────

    def _check_constraints(self, action: BlackstartAction) -> float:
        """Return an extra penalty if the proposed action violates any active constraint."""
        state = self._require_state()
        penalty = 0.0

        for constraint in state.active_constraints:
            if not constraint.active:
                continue

            if constraint.constraint_type == ConstraintType.FORBIDDEN_TARGET:
                if (
                    action.action_type == constraint.forbidden_action_type
                    and action.target_id == constraint.forbidden_target_id
                ):
                    constraint.violated = True
                    state.constraint_violations += 1
                    msg = f"CONSTRAINT VIOLATION: {constraint.text}"
                    state.last_action_error = msg
                    penalty += 0.25

            elif constraint.constraint_type == ConstraintType.CONDITIONAL_LIMIT:
                if (
                    action.action_type == ActionType.RESTORE_ZONE
                    and action.target_id == constraint.limit_target_id
                    and action.requested_mw is not None
                    and constraint.limit_mw is not None
                    and action.requested_mw > constraint.limit_mw
                ):
                    condition_met = False
                    if constraint.condition_field == "reserve_margin_mw":
                        condition_met = state.reserve_margin_mw >= (constraint.condition_threshold or 0)
                    if not condition_met:
                        constraint.violated = True
                        state.constraint_violations += 1
                        state.last_action_error = f"CONSTRAINT VIOLATION: {constraint.text}"
                        penalty += 0.18

            elif constraint.constraint_type == ConstraintType.PRIORITY_ORDER:
                if (
                    action.action_type == ActionType.RESTORE_ZONE
                    and action.target_id == constraint.before_restoring
                    and constraint.must_restore_first is not None
                ):
                    first_node = self._find_critical_node(constraint.must_restore_first)
                    if first_node is not None and not first_node.powered:
                        constraint.violated = True
                        state.constraint_violations += 1
                        state.last_action_error = f"CONSTRAINT VIOLATION: {constraint.text}"
                        penalty += 0.15

        return penalty

    # ── Live news feed ─────────────────────────────────────────────────────────

    def _reveal_news_events(self) -> None:
        """Surface any news event whose trigger_step has been reached."""
        state = self._require_state()
        scenario = self._require_scenario()

        for event in scenario.news_events:
            if event.revealed:
                continue
            if state.step_count < event.trigger_step:
                continue

            event.revealed = True
            state.news_feed.append(event.model_copy(deep=True))

            # Apply world-state side-effects
            if event.reveals_damage_on_line:
                line = self._find_line(event.reveals_damage_on_line)
                if line is not None and not line.damaged:
                    line.damaged = True
                    line.inspected = True  # crews confirmed it; agent knows

            if event.reduces_backup_node and event.reduces_backup_by:
                node = self._find_critical_node(event.reduces_backup_node)
                if node is not None and not node.powered:
                    node.backup_minutes_remaining = max(
                        0, node.backup_minutes_remaining - event.reduces_backup_by
                    )

            if event.public_trust_delta:
                state.command_center.public_trust = round(
                    min(0.99, max(0.01, state.command_center.public_trust + event.public_trust_delta)),
                    2,
                )

            if event.activates_constraint_id:
                for constraint in state.active_constraints:
                    if constraint.id == event.activates_constraint_id:
                        constraint.active = True
                        break
