from __future__ import annotations

import heapq
from typing import Callable

from blackstart_city.models import (
    ActionType,
    BlackstartAction,
    BlackstartObservation,
    CriticalNodeState,
    CriticalNodeType,
    GeneratorState,
    LineState,
    StatusUpdate,
    ZonePriority,
    ZoneState,
)

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

REPEATABLE_ACTIONS = {
    ActionType.RESTORE_ZONE,
    ActionType.SHED_ZONE,
    ActionType.PUBLISH_STATUS,
}

NODE_TYPE_WEIGHT = {
    CriticalNodeType.HOSPITAL: 0,
    CriticalNodeType.TELECOM: 1,
    CriticalNodeType.WATER: 2,
    CriticalNodeType.EMERGENCY: 3,
}

ZONE_PRIORITY_WEIGHT = {
    ZonePriority.CORRIDOR: 0,
    ZonePriority.RESIDENTIAL: 1,
    ZonePriority.INDUSTRIAL: 2,
}


def build_heuristic_actions(observation: BlackstartObservation) -> list[BlackstartAction]:
    actions: list[BlackstartAction] = []
    published = False
    seen_signatures: set[str] = set()
    current = observation.model_copy(deep=True)

    while True:
        action = choose_heuristic_action(
            current,
            published_status=published,
            seen_signatures=seen_signatures,
        )
        if action is None:
            break
        actions.append(action)
        seen_signatures.add(_signature(action))
        if action.action_type == ActionType.PUBLISH_STATUS:
            published = True
        if len(actions) >= 24:
            break

    return actions


def choose_greedy_action(
    observation: BlackstartObservation,
    *,
    published_status: bool,
    seen_signatures: set[str] | None = None,
) -> BlackstartAction | None:
    seen_signatures = seen_signatures or set()

    for generator in observation.generators:
        if not generator.online:
            action_type = ActionType.START_GENERATOR if generator.blackstart_capable else ActionType.ACTIVATE_BATTERY_SUPPORT
            action = BlackstartAction(action_type=action_type, target_id=generator.id)
            if not _is_action_blocked(action, seen_signatures):
                return action

    for line in observation.lines:
        if not line.closed and not line.tripped:
            action = BlackstartAction(action_type=ActionType.CLOSE_LINE, target_id=line.id)
            if not _is_action_blocked(action, seen_signatures):
                return action

    for substation in observation.substations:
        if not substation.energized and not substation.id.startswith("gen_"):
            action = BlackstartAction(action_type=ActionType.ENERGIZE_SUBSTATION, target_id=substation.id)
            if not _is_action_blocked(action, seen_signatures):
                return action

    for zone in observation.zones:
        if zone.restored_pct < 100:
            remaining_mw = _zone_remaining_mw(zone)
            action = BlackstartAction(
                action_type=ActionType.RESTORE_ZONE,
                target_id=zone.id,
                requested_mw=max(1, min(remaining_mw, max(4, zone.demand_mw // 2))),
            )
            if not _is_action_blocked(action, seen_signatures):
                return action

    for node in observation.critical_nodes:
        if not node.powered:
            action = BlackstartAction(action_type=ActionType.RESTORE_CRITICAL_NODE, target_id=node.id)
            if not _is_action_blocked(action, seen_signatures):
                return action

    if not published_status:
        action = _status_action(observation)
        if not _is_action_blocked(action, seen_signatures):
            return action

    return None


def choose_heuristic_action(
    observation: BlackstartObservation,
    *,
    published_status: bool,
    seen_signatures: set[str] | None = None,
) -> BlackstartAction | None:
    seen_signatures = seen_signatures or set()

    if observation.frequency_hz < 59.5:
        shed_candidate = _best_shed_candidate(observation)
        if shed_candidate is not None and not _is_action_blocked(shed_candidate, seen_signatures):
            return shed_candidate

    rescue_action = _choose_critical_rescue_action(observation, seen_signatures)
    if rescue_action is not None:
        return rescue_action

    if not published_status and _can_resolve_via_publish(observation):
        action = _status_action(observation)
        if not _is_action_blocked(action, seen_signatures):
            return action

    zone_action = _choose_zone_resolution_action(observation, seen_signatures)
    if zone_action is not None:
        return zone_action

    zone_action = _best_zone_restore_candidate(observation, seen_signatures, target_resolution=False)
    if zone_action is not None:
        return zone_action

    inspect_action = _best_inspection_action(observation, seen_signatures)
    if inspect_action is not None:
        return inspect_action

    sync_action = _best_sync_action(observation, seen_signatures)
    if sync_action is not None:
        return sync_action

    if not published_status:
        action = _status_action(observation)
        if not _is_action_blocked(action, seen_signatures):
            return action

    return None


def _choose_critical_rescue_action(
    observation: BlackstartObservation,
    seen_signatures: set[str],
) -> BlackstartAction | None:
    best_plan: tuple[tuple[object, ...], dict[str, object]] | None = None

    for node in observation.critical_nodes:
        if node.powered:
            continue
        plan = _best_rescue_plan(observation, node)
        if plan is None:
            continue
        urgency = _critical_urgency_key(node, plan["minutes_to_restore"])
        if best_plan is None or urgency < best_plan[0]:
            best_plan = (urgency, plan)

    if best_plan is None:
        return _best_generation_boost(observation, seen_signatures)

    action = best_plan[1]["next_action"]
    if _is_action_blocked(action, seen_signatures):
        return None
    return action


def _best_rescue_plan(
    observation: BlackstartObservation,
    node: CriticalNodeState,
) -> dict[str, object] | None:
    best: tuple[tuple[int, int, int, int], dict[str, object]] | None = None

    for generator in observation.generators:
        activation_minutes = 0 if generator.online else _generator_action_minutes(generator)
        projected_generation = observation.available_generation_mw + (0 if generator.online else generator.capacity_mw)
        projected_reserve = projected_generation - observation.served_load_mw
        if projected_reserve < node.demand_mw:
            continue

        path, path_cost = _shortest_path(observation, generator.bus, node.feeder_bus)
        if path is None:
            continue

        minutes_to_restore = activation_minutes + path_cost
        if not _is_substation_energized(observation, node.feeder_bus):
            minutes_to_restore += ACTION_DURATION_MINUTES[ActionType.ENERGIZE_SUBSTATION]
        minutes_to_restore += ACTION_DURATION_MINUTES[ActionType.RESTORE_CRITICAL_NODE]

        next_action = _next_path_action(observation, generator, path)
        if next_action is None and not _is_substation_energized(observation, node.feeder_bus):
            next_action = BlackstartAction(
                action_type=ActionType.ENERGIZE_SUBSTATION,
                target_id=node.feeder_bus,
            )
        if next_action is None:
            if observation.reserve_margin_mw < node.demand_mw:
                extra_power = _best_generation_boost(observation, set())
                if extra_power is not None:
                    next_action = extra_power
            else:
                next_action = BlackstartAction(
                    action_type=ActionType.RESTORE_CRITICAL_NODE,
                    target_id=node.id,
                )
        if next_action is None:
            continue

        plan = {
            "generator": generator.id,
            "minutes_to_restore": minutes_to_restore,
            "next_action": next_action,
        }
        rank = (
            minutes_to_restore,
            0 if generator.online else 1,
            path_cost,
            -generator.capacity_mw,
        )
        if best is None or rank < best[0]:
            best = (rank, plan)

    return best[1] if best is not None else None


def _critical_urgency_key(node: CriticalNodeState, minutes_to_restore: int) -> tuple[object, ...]:
    backup_remaining = max(0, node.backup_minutes_remaining)
    deadline_miss = max(0, minutes_to_restore - backup_remaining)
    feasible = deadline_miss == 0 and backup_remaining > 0
    return (
        0 if feasible else 1,
        deadline_miss,
        NODE_TYPE_WEIGHT[node.type],
        backup_remaining,
        -node.population_impact,
        minutes_to_restore,
    )


def _can_resolve_via_publish(observation: BlackstartObservation) -> bool:
    critical_ok = all(node.powered for node in observation.critical_nodes)
    stable = observation.frequency_hz >= 59.7
    zone_ok = _zone_mw_needed_for_resolution(observation) <= 0
    return critical_ok and stable and zone_ok


def _choose_zone_resolution_action(
    observation: BlackstartObservation,
    seen_signatures: set[str],
) -> BlackstartAction | None:
    if not all(node.powered for node in observation.critical_nodes):
        return None

    needed_zone_mw = _zone_mw_needed_for_resolution(observation)
    if needed_zone_mw <= 0:
        return None

    best: tuple[tuple[object, ...], BlackstartAction] | None = None
    for zone in observation.zones:
        plan = _best_zone_plan(observation, zone, needed_zone_mw)
        if plan is None:
            continue
        action = plan["next_action"]
        if _is_action_blocked(action, seen_signatures):
            continue
        rank = (
            0 if plan["restore_mw"] >= needed_zone_mw else 1,
            abs(needed_zone_mw - plan["restore_mw"]),
            -plan["restore_mw"],
            plan["minutes_to_restore"],
            ZONE_PRIORITY_WEIGHT[zone.priority],
            zone.restored_pct,
        )
        if best is None or rank < best[0]:
            best = (rank, action)
    return best[1] if best is not None else None


def _best_zone_plan(
    observation: BlackstartObservation,
    zone: ZoneState,
    needed_zone_mw: float,
) -> dict[str, object] | None:
    remaining_restore_mw = _zone_restore_remaining_mw(zone)
    if remaining_restore_mw <= 0:
        return None

    requested_mw = max(1, min(remaining_restore_mw, max(4, zone.demand_mw // 2), int(needed_zone_mw + 0.9999)))
    best: tuple[tuple[object, ...], dict[str, object]] | None = None

    for generator in observation.generators:
        activation_minutes = 0 if generator.online else _generator_action_minutes(generator)
        projected_generation = observation.available_generation_mw + (0 if generator.online else generator.capacity_mw)
        projected_reserve = projected_generation - observation.served_load_mw
        if projected_reserve < requested_mw:
            continue

        path, path_cost = _shortest_path(observation, generator.bus, zone.feeder_bus)
        if path is None:
            continue

        minutes_to_restore = activation_minutes + path_cost
        if not _is_substation_energized(observation, zone.feeder_bus):
            minutes_to_restore += ACTION_DURATION_MINUTES[ActionType.ENERGIZE_SUBSTATION]
        minutes_to_restore += ACTION_DURATION_MINUTES[ActionType.RESTORE_ZONE]

        next_action = _next_path_action(observation, generator, path)
        if next_action is None and not _is_substation_energized(observation, zone.feeder_bus):
            next_action = BlackstartAction(
                action_type=ActionType.ENERGIZE_SUBSTATION,
                target_id=zone.feeder_bus,
            )
        if next_action is None:
            if observation.reserve_margin_mw < requested_mw:
                next_action = _best_generation_boost(observation, set())
            else:
                next_action = BlackstartAction(
                    action_type=ActionType.RESTORE_ZONE,
                    target_id=zone.id,
                    requested_mw=requested_mw,
                )
        if next_action is None:
            continue

        plan = {
            "minutes_to_restore": minutes_to_restore,
            "restore_mw": requested_mw,
            "next_action": next_action,
        }
        rank = (
            minutes_to_restore,
            0 if generator.online else 1,
            path_cost,
            ZONE_PRIORITY_WEIGHT[zone.priority],
        )
        if best is None or rank < best[0]:
            best = (rank, plan)

    return best[1] if best is not None else None


def _best_zone_restore_candidate(
    observation: BlackstartObservation,
    seen_signatures: set[str],
    *,
    target_resolution: bool,
) -> BlackstartAction | None:
    needed_zone_mw = _zone_mw_needed_for_resolution(observation)
    candidates: list[tuple[tuple[int, int, int], BlackstartAction]] = []

    for zone in observation.zones:
        if zone.restored_pct >= 100:
            continue
        if not _is_substation_energized(observation, zone.feeder_bus):
            continue
        remaining_mw = _zone_restore_remaining_mw(zone)
        if remaining_mw <= 0:
            continue
        requested_mw = min(remaining_mw, max(4, zone.demand_mw // 2))
        if observation.reserve_margin_mw < requested_mw:
            continue
        action = BlackstartAction(
            action_type=ActionType.RESTORE_ZONE,
            target_id=zone.id,
            requested_mw=max(1, requested_mw),
        )
        if _is_action_blocked(action, seen_signatures):
            continue
        completion_mw = min(requested_mw, remaining_mw)
        priority_bias = ZONE_PRIORITY_WEIGHT[zone.priority]
        if target_resolution:
            rank = (0 if zone.priority != ZonePriority.INDUSTRIAL else 1, priority_bias, -completion_mw)
        else:
            rank = (priority_bias, -completion_mw, zone.restored_pct)
        candidates.append((rank, action))

    if not candidates:
        return None

    if target_resolution and needed_zone_mw <= 0:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _best_shed_candidate(observation: BlackstartObservation) -> BlackstartAction | None:
    for zone in sorted(
        observation.zones,
        key=lambda item: (ZONE_PRIORITY_WEIGHT[item.priority] != ZONE_PRIORITY_WEIGHT[ZonePriority.INDUSTRIAL], -item.restored_pct),
    ):
        if zone.restored_pct > 0:
            requested = max(1, min(_zone_restored_mw(zone), max(4, zone.demand_mw // 2)))
            return BlackstartAction(action_type=ActionType.SHED_ZONE, target_id=zone.id, requested_mw=requested)
    return None


def _best_generation_boost(
    observation: BlackstartObservation,
    seen_signatures: set[str],
) -> BlackstartAction | None:
    offline = [generator for generator in observation.generators if not generator.online]
    if not offline:
        return None
    offline.sort(key=lambda item: (_generator_action_minutes(item), -item.capacity_mw, item.id))
    for generator in offline:
        action = _generator_action(generator)
        if not _is_action_blocked(action, seen_signatures):
            return action
    return None


def _best_inspection_action(
    observation: BlackstartObservation,
    seen_signatures: set[str],
) -> BlackstartAction | None:
    damaged_lines = [
        line
        for line in observation.lines
        if line.damaged and not line.inspected and not line.tripped
    ]
    for line in sorted(damaged_lines, key=lambda item: (item.capacity_mw, item.id)):
        action = BlackstartAction(action_type=ActionType.INSPECT_LINE, target_id=line.id)
        if not _is_action_blocked(action, seen_signatures):
            return action
    return None


def _best_sync_action(
    observation: BlackstartObservation,
    seen_signatures: set[str],
) -> BlackstartAction | None:
    if observation.reserve_margin_mw < 6 or observation.frequency_hz < 59.7:
        return None
    syncable = [
        line
        for line in observation.lines
        if line.damaged and line.inspected and not line.closed and not line.tripped
    ]
    for line in sorted(syncable, key=lambda item: (-item.capacity_mw, item.id)):
        action = BlackstartAction(action_type=ActionType.SYNC_ISLANDS, target_id=line.id)
        if not _is_action_blocked(action, seen_signatures):
            return action
    return None


def _status_action(observation: BlackstartObservation) -> BlackstartAction:
    powered = [node.type.value for node in observation.critical_nodes if node.powered]
    pending = [node.type.value for node in observation.critical_nodes if not node.powered]
    powered_text = ", ".join(powered) if powered else "no critical services yet"
    pending_text = ", ".join(pending[:3]) if pending else "all critical services"
    reserve_text = f"reserve margin {observation.reserve_margin_mw} MW and frequency {observation.frequency_hz:.2f} Hz"
    sync_text = "synchronized feeder recovery" if any(line.inspected for line in observation.lines) else "blackstart recovery sequencing"

    if pending:
        next_action = (
            f"Continue {sync_text} for {pending_text}, protect backup-limited services, "
            f"maintain {reserve_text}, and avoid a second blackout."
        )
    else:
        next_action = (
            f"Maintain synchronized city stabilization, expand corridor restoration, preserve backup resilience, "
            f"and hold {reserve_text} to avoid a second blackout."
        )

    return BlackstartAction(
        action_type=ActionType.PUBLISH_STATUS,
        status_update=StatusUpdate(
            summary=(
                f"Blackstart city stabilization has restored {powered_text} and is keeping hospital, telecom, water, "
                f"and emergency recovery synchronized."
            ),
            critical_services=(
                f"Priority remains on hospital, telecom, water, emergency, corridor, and backup-risk coordination; "
                f"pending focus is {pending_text}."
            ),
            next_action=next_action,
            owner="city restoration commander",
        ),
    )


def _is_action_blocked(action: BlackstartAction, seen_signatures: set[str]) -> bool:
    if action.action_type in REPEATABLE_ACTIONS:
        return False
    return _signature(action) in seen_signatures


def _signature(action: BlackstartAction) -> str:
    return f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}"


def _generator_action(generator: GeneratorState) -> BlackstartAction:
    action_type = ActionType.START_GENERATOR if generator.blackstart_capable else ActionType.ACTIVATE_BATTERY_SUPPORT
    return BlackstartAction(action_type=action_type, target_id=generator.id)


def _generator_action_minutes(generator: GeneratorState) -> int:
    return ACTION_DURATION_MINUTES[ActionType.START_GENERATOR if generator.blackstart_capable else ActionType.ACTIVATE_BATTERY_SUPPORT]


def _is_substation_energized(observation: BlackstartObservation, substation_id: str) -> bool:
    return any(sub.id == substation_id and sub.energized for sub in observation.substations)


def _line_action_cost(line: LineState) -> int | None:
    if line.tripped:
        return None
    if line.damaged:
        if line.closed:
            return 0
        if line.inspected:
            return ACTION_DURATION_MINUTES[ActionType.SYNC_ISLANDS]
        return ACTION_DURATION_MINUTES[ActionType.INSPECT_LINE] + ACTION_DURATION_MINUTES[ActionType.SYNC_ISLANDS]
    if line.closed:
        return 0
    return ACTION_DURATION_MINUTES[ActionType.CLOSE_LINE]


def _shortest_path(
    observation: BlackstartObservation,
    start_bus: str,
    target_bus: str,
) -> tuple[list[LineState] | None, int]:
    if start_bus == target_bus:
        return [], 0

    adjacency: dict[str, list[tuple[str, LineState]]] = {}
    line_lookup = {line.id: line for line in observation.lines}
    for line in observation.lines:
        if line.tripped:
            continue
        adjacency.setdefault(line.from_bus, []).append((line.to_bus, line))
        adjacency.setdefault(line.to_bus, []).append((line.from_bus, line))

    queue: list[tuple[int, int, str, list[str]]] = [(0, 0, start_bus, [])]
    best_cost: dict[str, int] = {start_bus: 0}
    counter = 0

    while queue:
        cost, _, bus, path_ids = heapq.heappop(queue)
        if bus == target_bus:
            return [line_lookup[line_id] for line_id in path_ids], cost
        if cost > best_cost.get(bus, cost):
            continue
        for neighbor, line in adjacency.get(bus, []):
            edge_cost = _line_action_cost(line)
            if edge_cost is None:
                continue
            new_cost = cost + edge_cost
            if new_cost < best_cost.get(neighbor, 1_000_000):
                best_cost[neighbor] = new_cost
                counter += 1
                heapq.heappush(queue, (new_cost, counter, neighbor, path_ids + [line.id]))

    return None, 0


def _next_path_action(
    observation: BlackstartObservation,
    generator: GeneratorState,
    path: list[LineState],
) -> BlackstartAction | None:
    if not generator.online:
        return _generator_action(generator)
    for line in path:
        if line.damaged and not line.inspected:
            return BlackstartAction(action_type=ActionType.INSPECT_LINE, target_id=line.id)
        if not line.closed and not line.tripped:
            action_type = ActionType.SYNC_ISLANDS if line.damaged else ActionType.CLOSE_LINE
            return BlackstartAction(action_type=action_type, target_id=line.id)
    return None


def _zone_restored_mw(zone: ZoneState) -> int:
    return int(zone.demand_mw * (zone.restored_pct / 100))


def _zone_remaining_mw(zone: ZoneState) -> int:
    return max(0, zone.demand_mw - _zone_restored_mw(zone))


def _zone_restore_remaining_mw(zone: ZoneState) -> int:
    return max(0, zone.demand_mw * (100 - zone.restored_pct) // 100)


def _zone_mw_needed_for_resolution(observation: BlackstartObservation) -> float:
    total_zone_demand = sum(zone.demand_mw for zone in observation.zones)
    restored_zone_demand = sum(_zone_restored_mw(zone) for zone in observation.zones)
    target = total_zone_demand * 0.60
    return max(0.0, target - restored_zone_demand)


def run_policy_rollout(
    env,
    observation: BlackstartObservation,
    chooser: Callable[..., BlackstartAction | None],
) -> dict[str, object]:
    published = False
    seen_signatures: set[str] = set()
    log: list[dict[str, object]] = []
    info: dict[str, object] = {"score": observation.reward_breakdown.current_score, "resolved": False}

    while not observation.done:
        action = chooser(
            observation,
            published_status=published,
            seen_signatures=seen_signatures,
        )
        if action is None:
            break
        seen_signatures.add(_signature(action))
        observation, reward, done, info = env.step(action)
        if action.action_type == ActionType.PUBLISH_STATUS:
            published = True
        log.append(
            {
                "step": observation.step,
                "action": action.model_dump(mode="json", exclude_none=True),
                "reward": reward,
                "score": float(info["score"]),
                "done": done,
            }
        )
        if done:
            break

    return {
        "final_observation": observation,
        "info": info,
        "log": log,
        "steps": len(log),
    }
