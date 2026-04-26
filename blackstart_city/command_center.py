from __future__ import annotations

from blackstart_city.models import (
    ActionType,
    BlackstartAction,
    BlackstartState,
    CommandCenterState,
    CommandRecommendation,
    CommandRole,
    CoordinationMessage,
    CriticalNodeType,
    DifficultyLevel,
    ResourceState,
    StatusUpdate,
)


RESOURCE_TOTALS = {
    DifficultyLevel.EASY: {"repair_crews": 2, "telecom_units": 1},
    DifficultyLevel.MEDIUM: {"repair_crews": 3, "telecom_units": 1},
    DifficultyLevel.HARD: {"repair_crews": 4, "telecom_units": 2},
    DifficultyLevel.EXTREME: {"repair_crews": 5, "telecom_units": 2},
}


def initial_command_center(state: BlackstartState) -> CommandCenterState:
    unresolved = _unresolved_services(state)
    trust = (
        0.62 if state.difficulty == DifficultyLevel.EASY
        else 0.58 if state.difficulty == DifficultyLevel.MEDIUM
        else 0.54 if state.difficulty == DifficultyLevel.HARD
        else 0.50  # EXTREME — public starts with even less trust
    )
    snapshot = CommandCenterState(
        public_trust=trust,
        coordination_score=0.56,
        command_phase="critical triage" if unresolved else "load restoration",
        unresolved_services=unresolved,
    )
    snapshot.resource_state = build_resource_state(state)
    snapshot.role_recommendations = build_role_recommendations(state)
    snapshot.coordination_messages = build_coordination_messages(state, snapshot)
    return snapshot


def build_resource_state(state: BlackstartState) -> ResourceState:
    totals = RESOURCE_TOTALS[state.difficulty]
    pending_repairs = sum(1 for line in state.lines if line.damaged and not line.inspected) + sum(1 for line in state.lines if line.tripped)
    mobile_batteries_total = max(1, sum(1 for generator in state.generators if not generator.blackstart_capable))
    mobile_batteries_available = max(0, mobile_batteries_total - sum(1 for generator in state.generators if not generator.blackstart_capable and generator.online))
    telecom_nodes = [node for node in state.critical_nodes if node.type == CriticalNodeType.TELECOM]
    telecom_support_total = totals["telecom_units"]
    telecom_support_available = telecom_support_total if any(node.powered for node in telecom_nodes) else max(0, telecom_support_total - 1)
    unresolved_critical = sum(1 for node in state.critical_nodes if not node.powered)
    pressure = min(1.0, (unresolved_critical + pending_repairs) / max(1, len(state.critical_nodes) + totals["repair_crews"]))
    return ResourceState(
        repair_crews_total=totals["repair_crews"],
        repair_crews_available=max(0, totals["repair_crews"] - min(totals["repair_crews"], pending_repairs)),
        mobile_battery_units_total=mobile_batteries_total,
        mobile_battery_units_available=mobile_batteries_available,
        telecom_support_units_total=telecom_support_total,
        telecom_support_units_available=telecom_support_available,
        dispatch_pressure=round(pressure, 2),
    )


def derive_command_phase(state: BlackstartState) -> str:
    if state.catastrophe_triggered:
        return "catastrophe containment"
    if any(not generator.online for generator in state.generators if generator.blackstart_capable):
        return "blackstart sequencing"
    unresolved = sum(1 for node in state.critical_nodes if not node.powered)
    if unresolved:
        return "critical service triage"
    if state.reserve_margin_mw < 10 or state.frequency_hz < 59.8:
        return "stability preservation"
    if _zone_restored_ratio(state) < 0.60:
        return "corridor load restoration"
    return "city stabilization"


def build_role_recommendations(state: BlackstartState) -> list[CommandRecommendation]:
    recommendations = [
        _grid_operator_recommendation(state),
        _emergency_recommendation(state),
        _public_information_recommendation(state),
        _resource_dispatch_recommendation(state),
    ]
    return [item for item in recommendations if item is not None]


def build_coordination_messages(state: BlackstartState, command_center: CommandCenterState) -> list[CoordinationMessage]:
    messages: list[CoordinationMessage] = []
    unresolved = command_center.unresolved_services

    # ── Standard coordination messages ────────────────────────────────────────
    if unresolved:
        messages.append(
            CoordinationMessage(
                role=CommandRole.EMERGENCY_COORDINATOR,
                recipient="grid_operator",
                urgency="critical" if any("hospital" in item for item in unresolved) else "high",
                summary=f"Prioritize {unresolved[0]} before non-critical load restoration.",
            )
        )
    if command_center.public_trust < 0.45:
        messages.append(
            CoordinationMessage(
                role=CommandRole.PUBLIC_INFORMATION_OFFICER,
                recipient="all_roles",
                urgency="high",
                summary="Public trust is slipping. Publish a concrete update tied to visible service restoration.",
            )
        )
    if command_center.resource_state.dispatch_pressure > 0.65:
        messages.append(
            CoordinationMessage(
                role=CommandRole.RESOURCE_DISPATCHER,
                recipient="emergency_coordinator",
                urgency="high",
                summary="Crew pressure is high. Sequence repairs and feeder work to avoid splitting scarce field teams.",
            )
        )

    # ── Multi-agent conflict detection ────────────────────────────────────────
    # Find what each role is proposing
    recs = {r.role: r for r in command_center.role_recommendations}
    grid_rec = recs.get(CommandRole.GRID_OPERATOR)
    emerg_rec = recs.get(CommandRole.EMERGENCY_COORDINATOR)
    dispatch_rec = recs.get(CommandRole.RESOURCE_DISPATCHER)
    pio_rec = recs.get(CommandRole.PUBLIC_INFORMATION_OFFICER)

    # Conflict 1: Grid Operator vs Emergency Coordinator (different targets)
    if (
        grid_rec and emerg_rec
        and grid_rec.proposed_action and emerg_rec.proposed_action
        and grid_rec.proposed_action.action_type != emerg_rec.proposed_action.action_type
    ):
        messages.append(
            CoordinationMessage(
                role=CommandRole.GRID_OPERATOR,
                recipient="emergency_coordinator",
                urgency="critical",
                is_conflict=True,
                summary=(
                    f"CONFLICT: Grid Operator recommends {grid_rec.proposed_action.action_type.value} "
                    f"on {grid_rec.proposed_action.target_id or 'grid'}, but Emergency Coordinator "
                    f"wants {emerg_rec.proposed_action.action_type.value} on "
                    f"{emerg_rec.proposed_action.target_id or 'critical service'}. "
                    f"Commander must arbitrate."
                ),
            )
        )

    # Conflict 2: Resource Dispatcher wants to shed load, but Emergency wants to restore
    if (
        dispatch_rec and emerg_rec
        and dispatch_rec.proposed_action and emerg_rec.proposed_action
        and dispatch_rec.proposed_action.action_type == ActionType.SHED_ZONE
        and emerg_rec.proposed_action.action_type in {ActionType.RESTORE_CRITICAL_NODE, ActionType.ENERGIZE_SUBSTATION}
    ):
        messages.append(
            CoordinationMessage(
                role=CommandRole.RESOURCE_DISPATCHER,
                recipient="emergency_coordinator",
                urgency="high",
                is_conflict=True,
                summary=(
                    f"CONFLICT: Resource Dispatcher wants to shed {dispatch_rec.proposed_action.target_id} "
                    f"to stabilize frequency, but Emergency Coordinator insists on restoring "
                    f"{emerg_rec.proposed_action.target_id}. These goals may be incompatible."
                ),
            )
        )

    # Conflict 3: PIO wants to publish now, Grid Operator says focus on restoration
    if (
        pio_rec and grid_rec
        and pio_rec.proposed_action
        and pio_rec.proposed_action.action_type == ActionType.PUBLISH_STATUS
        and grid_rec.proposed_action
        and grid_rec.proposed_action.action_type != ActionType.PUBLISH_STATUS
        and grid_rec.urgency == "critical"
    ):
        messages.append(
            CoordinationMessage(
                role=CommandRole.PUBLIC_INFORMATION_OFFICER,
                recipient="grid_operator",
                urgency="high",
                is_conflict=True,
                summary=(
                    f"CONFLICT: Public Information Officer urges immediate status publication "
                    f"(trust at {command_center.public_trust:.0%}), but Grid Operator has a "
                    f"critical {grid_rec.proposed_action.action_type.value} pending. "
                    f"Publishing now costs a step that could save a critical service."
                ),
            )
        )

    if not messages:
        messages.append(
            CoordinationMessage(
                role=CommandRole.GRID_OPERATOR,
                recipient="all_roles",
                urgency="normal",
                summary="Coordination is stable. Continue aligned restoration while preserving reserve margin.",
            )
        )
    return messages[:5]


def refresh_command_center(state: BlackstartState) -> CommandCenterState:
    state.command_center.command_phase = derive_command_phase(state)
    state.command_center.unresolved_services = _unresolved_services(state)
    state.command_center.resource_state = build_resource_state(state)
    state.command_center.role_recommendations = build_role_recommendations(state)
    state.command_center.coordination_messages = build_coordination_messages(state, state.command_center)
    return state.command_center


def coordination_status_text(command_center: CommandCenterState) -> str:
    trust = command_center.public_trust
    coord = command_center.coordination_score
    if trust < 0.35 or coord < 0.35:
        return "fractured coordination"
    if trust < 0.55 or coord < 0.55:
        return "strained coordination"
    return "aligned coordination"


def _grid_operator_recommendation(state: BlackstartState) -> CommandRecommendation:
    if state.command_center.rl_proposed_action is not None:
        return CommandRecommendation(
            role=CommandRole.GRID_OPERATOR,
            objective="Execute external model policy",
            rationale="Action proposed by RL Brain / external policy.",
            urgency="high",
            proposed_action=state.command_center.rl_proposed_action,
        )

    action: BlackstartAction | None = None
    rationale = "Preserve grid stability while building the shortest safe energized path to unresolved critical load."

    offline_blackstart = next((generator for generator in state.generators if generator.blackstart_capable and not generator.online), None)
    if offline_blackstart is not None:
        action = BlackstartAction(action_type=ActionType.START_GENERATOR, target_id=offline_blackstart.id)
        rationale = "A blackstart-capable generator is still offline. Starting generation unlocks every downstream recovery option."
    else:
        pending_node = _most_urgent_node(state)
        if pending_node is not None:
            feeder_energized = any(sub.id == pending_node.feeder_bus and sub.energized for sub in state.substations)
            if feeder_energized:
                action = BlackstartAction(action_type=ActionType.RESTORE_CRITICAL_NODE, target_id=pending_node.id)
                rationale = f"{pending_node.id} is on an energized feeder and should be restored before more zone load is added."
            else:
                feeder_line = next(
                    (
                        line
                        for line in state.lines
                        if pending_node.feeder_bus in {line.from_bus, line.to_bus} and not line.tripped and not line.closed
                    ),
                    None,
                )
                if feeder_line is not None:
                    if feeder_line.damaged and not feeder_line.inspected:
                        action = BlackstartAction(action_type=ActionType.INSPECT_LINE, target_id=feeder_line.id)
                        rationale = f"{pending_node.id} depends on {feeder_line.id}; inspect it before attempting to energize the feeder."
                    else:
                        action_type = ActionType.SYNC_ISLANDS if feeder_line.damaged else ActionType.CLOSE_LINE
                        action = BlackstartAction(action_type=action_type, target_id=feeder_line.id)
                        rationale = f"Close the remaining feeder path to {pending_node.id} before public-facing load restoration."
                else:
                    feeder = next((sub for sub in state.substations if sub.id == pending_node.feeder_bus and not sub.energized), None)
                    if feeder is not None:
                        action = BlackstartAction(action_type=ActionType.ENERGIZE_SUBSTATION, target_id=feeder.id)
                        rationale = f"Energize {feeder.id} so {pending_node.id} can move from backup to grid power."

    if action is None:
        corridor = next((zone for zone in state.zones if zone.priority.value == "corridor" and zone.restored_pct < 100), None)
        if corridor is not None:
            action = BlackstartAction(
                action_type=ActionType.RESTORE_ZONE,
                target_id=corridor.id,
                requested_mw=max(1, min(6, corridor.demand_mw)),
            )
            rationale = "Critical services are online; restore corridor load in small increments to preserve reserve margin."

    return CommandRecommendation(
        role=CommandRole.GRID_OPERATOR,
        objective="Stabilize the grid and open a safe feeder path",
        rationale=rationale,
        urgency="critical" if _most_urgent_node(state) is not None else "high",
        proposed_action=action,
    )


def _emergency_recommendation(state: BlackstartState) -> CommandRecommendation:
    urgent = _most_urgent_node(state)
    if urgent is not None:
        rationale = f"{urgent.id} has the tightest backup window and highest near-term human impact."
        if any(sub.id == urgent.feeder_bus and sub.energized for sub in state.substations):
            action = BlackstartAction(action_type=ActionType.RESTORE_CRITICAL_NODE, target_id=urgent.id)
        else:
            action = BlackstartAction(action_type=ActionType.ENERGIZE_SUBSTATION, target_id=urgent.feeder_bus)
        objective = f"Keep {urgent.type.value} services alive first"
        urgency = "critical" if urgent.backup_minutes_remaining <= 12 else "high"
    else:
        action = None
        objective = "Protect restored critical services from secondary instability"
        rationale = "All critical services are online. Emergency operations can now shift attention to corridor resilience and reserve preservation."
        urgency = "normal"

    return CommandRecommendation(
        role=CommandRole.EMERGENCY_COORDINATOR,
        objective=objective,
        rationale=rationale,
        urgency=urgency,
        proposed_action=action,
    )


def _public_information_recommendation(state: BlackstartState) -> CommandRecommendation:
    powered_services = [node.type.value for node in state.critical_nodes if node.powered]
    pending = [node.type.value for node in state.critical_nodes if not node.powered]
    should_publish = bool(powered_services) or state.command_center.public_trust < 0.45
    action = None
    rationale = "Hold public messaging until there is either visible progress or a trust deficit that requires an explanation."
    if should_publish:
        action = BlackstartAction(
            action_type=ActionType.PUBLISH_STATUS,
            status_update=StatusUpdate(
                summary=(
                    f"Blackstart City command has restored {', '.join(powered_services) if powered_services else 'stability operations'} "
                    f"and is coordinating safe recovery across the grid."
                ),
                critical_services=(
                    f"Current priorities remain hospital, telecom, water, emergency, and corridor coordination. "
                    f"Pending services: {', '.join(pending) if pending else 'none'}."
                ),
                next_action=(
                    "Continue synchronized feeder restoration, keep reserve margin healthy, and avoid a second collapse."
                ),
                owner="city restoration commander",
            ),
        )
        rationale = "A factual public update improves trust once there is visible critical-service progress or elevated public uncertainty."

    return CommandRecommendation(
        role=CommandRole.PUBLIC_INFORMATION_OFFICER,
        objective="Preserve public trust with truthful operational messaging",
        rationale=rationale,
        urgency="high" if state.command_center.public_trust < 0.45 else "normal",
        proposed_action=action,
    )


def _resource_dispatch_recommendation(state: BlackstartState) -> CommandRecommendation:
    damaged_line = next((line for line in state.lines if line.damaged and not line.inspected), None)
    if damaged_line is not None:
        action = BlackstartAction(action_type=ActionType.INSPECT_LINE, target_id=damaged_line.id)
        rationale = f"Dispatch field crews to {damaged_line.id}; unseen line damage is the main coordination bottleneck."
        objective = "Commit scarce repair crews where they unlock the most recovery"
        urgency = "high"
    else:
        offline_support = next((generator for generator in state.generators if not generator.blackstart_capable and not generator.online), None)
        if offline_support is not None:
            action = BlackstartAction(action_type=ActionType.ACTIVATE_BATTERY_SUPPORT, target_id=offline_support.id)
            rationale = "A mobile battery support asset is still idle and can buy coordination time while feeders are restored."
            objective = "Allocate backup support assets to buy time"
            urgency = "high" if _most_urgent_node(state) is not None else "normal"
        else:
            zone = next((zone for zone in state.zones if zone.restored_pct > 0 and state.frequency_hz < 59.6), None)
            action = (
                BlackstartAction(action_type=ActionType.SHED_ZONE, target_id=zone.id, requested_mw=max(1, zone.demand_mw // 2))
                if zone is not None
                else None
            )
            rationale = "Resource dispatch is aligned; hold crews in reserve unless stability deteriorates or a damaged corridor appears."
            objective = "Keep dispatch resources in reserve for the next bottleneck"
            urgency = "normal"

    return CommandRecommendation(
        role=CommandRole.RESOURCE_DISPATCHER,
        objective=objective,
        rationale=rationale,
        urgency=urgency,
        proposed_action=action,
    )


def _most_urgent_node(state: BlackstartState):
    pending = [node for node in state.critical_nodes if not node.powered]
    if not pending:
        return None
    return min(
        pending,
        key=lambda node: (
            node.backup_minutes_remaining,
            0 if node.type == CriticalNodeType.HOSPITAL else 1,
            -node.population_impact,
        ),
    )


def _unresolved_services(state: BlackstartState) -> list[str]:
    return [node.id for node in state.critical_nodes if not node.powered]


def _zone_restored_ratio(state: BlackstartState) -> float:
    total = sum(zone.demand_mw for zone in state.zones)
    restored = sum(zone.demand_mw * (zone.restored_pct / 100) for zone in state.zones)
    return (restored / total) if total else 0.0


def score_arbitration(state: BlackstartState, action: BlackstartAction) -> float:
    """Score the agent's action against any active multi-agent conflicts.

    Design principles:
      - Feasibility is a hard gate (can't reward an impossible action)
      - Hysteresis: Emergency priority activates at ≤10 min, deactivates at >12 min
      - Intent credit decays: 1st infeasible-emergency=0.0, 2nd=−0.05, 3rd+=−0.12
      - Smooth ramp replaces hard cutoffs to prevent boundary oscillation
      - Per-step cap of ±0.25 prevents reward stacking exploits
    """
    cc = state.command_center
    conflicts = [m for m in cc.coordination_messages if m.is_conflict]
    if not conflicts:
        return 0.0

    recs = {r.role: r for r in cc.role_recommendations}
    grid_rec = recs.get(CommandRole.GRID_OPERATOR)
    emerg_rec = recs.get(CommandRole.EMERGENCY_COORDINATOR)
    dispatch_rec = recs.get(CommandRole.RESOURCE_DISPATCHER)

    total_bonus = 0.0
    conflict_handled = False  # only one main conflict bonus per step

    for conflict in conflicts:
        # ── Grid Operator vs Emergency Coordinator ────────────────────────
        if (
            conflict.role == CommandRole.GRID_OPERATOR
            and "Emergency Coordinator" in conflict.summary
            and grid_rec and emerg_rec
            and grid_rec.proposed_action and emerg_rec.proposed_action
            and not conflict_handled
        ):
            conflict_handled = True
            urgent_node = _most_urgent_node(state)
            emerg_action = emerg_rec.proposed_action
            backup = urgent_node.backup_minutes_remaining if urgent_node else 999

            # ── Feasibility check ────────────────────────────────────────
            emerg_executable = _is_action_executable(state, emerg_action)

            # ── Hysteresis for Emergency priority ────────────────────────
            # Activate at ≤10, deactivate only at >12
            if backup <= 10:
                state.emergency_priority_active = True
            elif backup > 12:
                state.emergency_priority_active = False
            # else: keep previous state (hysteresis band 10-12)

            # ── Decision logic (mutually exclusive, smooth) ──────────────
            # Bucket 1: Emergency NOT executable → Grid wins
            if not emerg_executable:
                correct_sides = {grid_rec.proposed_action.action_type}

                if action.action_type not in correct_sides:
                    # Intent credit with decay
                    streak = state.infeasible_emergency_streak + 1
                    state.infeasible_emergency_streak = streak
                    if state.emergency_priority_active and streak == 1:
                        total_bonus += 0.0    # 1st: understood urgency
                    elif state.emergency_priority_active and streak == 2:
                        total_bonus -= 0.05   # 2nd: should adapt
                    else:
                        total_bonus -= 0.12   # 3rd+: exploiting
                else:
                    state.infeasible_emergency_streak = 0  # reset on correct choice
                    total_bonus += 0.20

            # Bucket 2: Executable AND Emergency priority active → Emergency wins
            elif state.emergency_priority_active and emerg_executable:
                correct_sides = {emerg_action.action_type}
                state.infeasible_emergency_streak = 0

                if action.action_type in correct_sides:
                    # Smooth transition: if this JUST became executable,
                    # give 0.5x bonus to prevent spike
                    was_just_blocked = state.infeasible_emergency_streak > 0
                    total_bonus += 0.10 if was_just_blocked else 0.20
                else:
                    total_bonus -= 0.12

            # Bucket 3: Executable, backup in [10, 15] — smooth ramp
            elif urgent_node and 10 < backup <= 15:
                # Linear blend: at 10 min Emergency fully correct,
                # at 15 min Grid fully correct, between → both OK
                correct_sides = {grid_rec.proposed_action.action_type, emerg_action.action_type}
                state.infeasible_emergency_streak = 0

                if action.action_type in correct_sides:
                    # Scale bonus: closer to 10 → full bonus, closer to 15 → reduced
                    urgency_factor = (15 - backup) / 5.0  # 1.0 at 10, 0.0 at 15
                    total_bonus += 0.10 + 0.10 * urgency_factor
                else:
                    total_bonus -= 0.08  # softer penalty in ambiguous zone

            # Bucket 4: No urgency → Grid wins
            else:
                correct_sides = {grid_rec.proposed_action.action_type}
                state.infeasible_emergency_streak = 0

                if action.action_type in correct_sides:
                    total_bonus += 0.20
                else:
                    total_bonus -= 0.12

        # ── Resource Dispatcher (shed) vs Emergency (restore) ─────────────
        if (
            conflict.role == CommandRole.RESOURCE_DISPATCHER
            and "shed" in conflict.summary.lower()
            and dispatch_rec and emerg_rec
            and dispatch_rec.proposed_action and emerg_rec.proposed_action
            and not conflict_handled
        ):
            conflict_handled = True

            if state.frequency_hz < 59.4:
                correct_action_type = ActionType.SHED_ZONE
            else:
                urgent_node = _most_urgent_node(state)
                if urgent_node and urgent_node.backup_minutes_remaining <= 10:
                    correct_action_type = emerg_rec.proposed_action.action_type
                else:
                    correct_action_type = ActionType.SHED_ZONE

            if action.action_type == correct_action_type:
                total_bonus += 0.15
            else:
                total_bonus -= 0.10

        # ── PIO (publish) vs Grid (critical action) ──────────────────────
        # Only fires when no other conflict was handled this step
        if (
            conflict.role == CommandRole.PUBLIC_INFORMATION_OFFICER
            and "publication" in conflict.summary.lower()
            and grid_rec and grid_rec.proposed_action
            and not conflict_handled
        ):
            conflict_handled = True

            if cc.public_trust < 0.30:
                correct_action_type = ActionType.PUBLISH_STATUS
            else:
                correct_action_type = grid_rec.proposed_action.action_type

            if action.action_type == correct_action_type:
                total_bonus += 0.15
            else:
                total_bonus -= 0.10

    # Cap total to prevent stacking exploits
    return round(max(-0.25, min(0.25, total_bonus)), 3)


def _is_action_executable(state: BlackstartState, action: BlackstartAction) -> bool:
    """Check if a proposed action is physically executable in the current state."""
    if action.action_type == ActionType.RESTORE_CRITICAL_NODE:
        target_node = next(
            (n for n in state.critical_nodes if n.id == action.target_id), None,
        )
        if target_node:
            return any(
                s.id == target_node.feeder_bus and s.energized for s in state.substations
            )
    elif action.action_type == ActionType.ENERGIZE_SUBSTATION:
        target_sub = action.target_id
        return any(
            line.closed and (
                (line.to_bus == target_sub and any(s.id == line.from_bus and s.energized for s in state.substations))
                or (line.from_bus == target_sub and any(s.id == line.to_bus and s.energized for s in state.substations))
            )
            for line in state.lines
        )
    return True


