from __future__ import annotations

from typing import Callable

from blackstart_city.models import ActionType, BlackstartAction, BlackstartObservation, StatusUpdate


def build_heuristic_actions(observation: BlackstartObservation) -> list[BlackstartAction]:
    actions: list[BlackstartAction] = []
    published = False
    seen_signatures: set[str] = set()

    while True:
        action = choose_heuristic_action(observation, published_status=published, seen_signatures=seen_signatures)
        if action is None:
            break
        actions.append(action)
        seen_signatures.add(_signature(action))
        if action.action_type == ActionType.PUBLISH_STATUS:
            published = True

        # This function is also used to build offline imitation data from a single observation.
        # We stop after composing the best next-step plan skeleton rather than trying to simulate forward here.
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
            if _signature(action) not in seen_signatures:
                return action

    for line in observation.lines:
        if not line.closed and not line.tripped:
            action = BlackstartAction(action_type=ActionType.CLOSE_LINE, target_id=line.id)
            if _signature(action) not in seen_signatures:
                return action

    for substation in observation.substations:
        if not substation.energized and not substation.id.startswith("gen_"):
            action = BlackstartAction(action_type=ActionType.ENERGIZE_SUBSTATION, target_id=substation.id)
            if _signature(action) not in seen_signatures:
                return action

    for zone in observation.zones:
        if zone.restored_pct < 100:
            action = BlackstartAction(
                action_type=ActionType.RESTORE_ZONE,
                target_id=zone.id,
                requested_mw=max(4, zone.demand_mw // 2),
            )
            if _signature(action) not in seen_signatures:
                return action

    for node in observation.critical_nodes:
        if not node.powered:
            action = BlackstartAction(action_type=ActionType.RESTORE_CRITICAL_NODE, target_id=node.id)
            if _signature(action) not in seen_signatures:
                return action

    if not published_status:
        action = _status_action()
        if _signature(action) not in seen_signatures:
            return action

    return None


def choose_heuristic_action(
    observation: BlackstartObservation,
    *,
    published_status: bool,
    seen_signatures: set[str] | None = None,
) -> BlackstartAction | None:
    seen_signatures = seen_signatures or set()

    for generator in observation.generators:
        if generator.blackstart_capable and not generator.online:
            action = BlackstartAction(action_type=ActionType.START_GENERATOR, target_id=generator.id)
            if _signature(action) not in seen_signatures:
                return action

    for generator in observation.generators:
        if not generator.blackstart_capable and not generator.online:
            action = BlackstartAction(action_type=ActionType.ACTIVATE_BATTERY_SUPPORT, target_id=generator.id)
            if _signature(action) not in seen_signatures:
                return action

    for line in observation.lines:
        if line.damaged and not line.inspected:
            action = BlackstartAction(action_type=ActionType.INSPECT_LINE, target_id=line.id)
            if _signature(action) not in seen_signatures:
                return action

    for line in observation.lines:
        if line.inspected and line.damaged and not line.closed and not line.tripped:
            if observation.reserve_margin_mw >= 6 and observation.frequency_hz >= 59.7:
                action = BlackstartAction(action_type=ActionType.SYNC_ISLANDS, target_id=line.id)
                if _signature(action) not in seen_signatures:
                    return action

    for line in observation.lines:
        if not line.closed and not line.tripped and not line.damaged:
            action = BlackstartAction(action_type=ActionType.CLOSE_LINE, target_id=line.id)
            if _signature(action) not in seen_signatures:
                return action

    for substation in observation.substations:
        if not substation.energized and not substation.id.startswith("gen_"):
            action = BlackstartAction(action_type=ActionType.ENERGIZE_SUBSTATION, target_id=substation.id)
            if _signature(action) not in seen_signatures:
                return action

    for node in sorted(
        observation.critical_nodes,
        key=lambda item: (item.backup_minutes_remaining, item.population_impact * -1),
    ):
        if not node.powered:
            if observation.reserve_margin_mw >= node.demand_mw:
                action = BlackstartAction(action_type=ActionType.RESTORE_CRITICAL_NODE, target_id=node.id)
                if _signature(action) not in seen_signatures:
                    return action
            shed_candidate = _best_shed_candidate(observation)
            if shed_candidate is not None:
                if _signature(shed_candidate) not in seen_signatures:
                    return shed_candidate

    for zone in observation.zones:
        if zone.priority.value == "corridor" and zone.restored_pct < 100:
            requested = min(6, zone.demand_mw)
            if observation.reserve_margin_mw >= requested:
                action = BlackstartAction(action_type=ActionType.RESTORE_ZONE, target_id=zone.id, requested_mw=requested)
                if _signature(action) not in seen_signatures:
                    return action

    if not published_status and any(node.powered for node in observation.critical_nodes):
        action = _status_action()
        if _signature(action) not in seen_signatures:
            return action

    for zone in observation.zones:
        if zone.priority.value == "corridor":
            continue
        if zone.restored_pct < 100:
            requested = max(4, zone.demand_mw // 2)
            if observation.reserve_margin_mw >= requested:
                action = BlackstartAction(action_type=ActionType.RESTORE_ZONE, target_id=zone.id, requested_mw=requested)
                if _signature(action) not in seen_signatures:
                    return action

    if observation.frequency_hz < 59.5:
        shed_candidate = _best_shed_candidate(observation)
        if shed_candidate is not None:
            if _signature(shed_candidate) not in seen_signatures:
                return shed_candidate

    if not published_status:
        action = _status_action()
        if _signature(action) not in seen_signatures:
            return action

    return None


def _best_shed_candidate(observation: BlackstartObservation) -> BlackstartAction | None:
    for zone in sorted(observation.zones, key=lambda item: (item.priority.value != "industrial", -item.restored_pct)):
        if zone.restored_pct > 0:
            requested = max(4, zone.demand_mw // 2)
            return BlackstartAction(action_type=ActionType.SHED_ZONE, target_id=zone.id, requested_mw=requested)
    return None


def _status_action() -> BlackstartAction:
    return BlackstartAction(
        action_type=ActionType.PUBLISH_STATUS,
        status_update=StatusUpdate(
            summary="Blackstart recovery is underway and critical services are being restored in priority order.",
            critical_services="Hospitals, telecom, water, and emergency nodes are being restored before general load.",
            next_action="Continue safe feeder restoration while maintaining reserve margin and avoiding a second collapse.",
            owner="city restoration commander",
        ),
    )
def _signature(action: BlackstartAction) -> str:
    return f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}"


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
