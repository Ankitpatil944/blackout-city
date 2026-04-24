from __future__ import annotations

from blackstart_city.models import BlackstartState, CriticalNodeType, RewardBreakdown, Scenario, StatusUpdate


def clamp_score(value: float) -> float:
    return round(min(0.99, max(0.01, value)), 2)


def score_status_update(status: StatusUpdate | None, scenario: Scenario, state: BlackstartState) -> float:
    if status is None:
        return 0.0

    text = " ".join(
        [
            status.summary.lower(),
            status.critical_services.lower(),
            status.next_action.lower(),
            status.owner.lower(),
        ]
    )
    score = 0.0

    for keyword in scenario.status_keywords:
        if keyword.lower() in text:
            score += 0.02

    if any(node.powered for node in state.critical_nodes if node.type == CriticalNodeType.HOSPITAL) and "hospital" in text:
        score += 0.02
    if state.catastrophe_triggered and "stable" in text:
        score -= 0.03
    if "owner" in status.owner.lower() or "commander" in status.owner.lower():
        score += 0.01

    return round(max(0.0, min(0.12, score)), 2)


def compute_final_score(state: BlackstartState, scenario: Scenario) -> float:
    critical_total = sum(node.population_impact for node in state.critical_nodes)
    critical_restored = sum(node.population_impact for node in state.critical_nodes if node.powered)
    critical_ratio = (critical_restored / critical_total) if critical_total else 0.0

    total_zone_demand = sum(zone.demand_mw for zone in state.zones)
    restored_zone_demand = sum(zone.demand_mw * (zone.restored_pct / 100) for zone in state.zones)
    load_ratio = (restored_zone_demand / total_zone_demand) if total_zone_demand else 0.0

    stability = 1.0
    if state.frequency_hz < 59.7:
        stability -= 0.15
    if state.frequency_hz < 59.5:
        stability -= 0.20  # approaching cascade threshold
    if state.frequency_hz < 59.2:
        stability -= 0.30  # severe; near second collapse
    stability -= min(0.3, state.cumulative_penalty)
    if state.catastrophe_triggered:
        stability -= 0.45
    stability = max(0.0, stability)

    inspection_ratio = 0.0
    damaged = [line for line in state.lines if line.damaged]
    if damaged:
        inspected = sum(1 for line in damaged if line.inspected)
        inspection_ratio = inspected / len(damaged)

    # Step efficiency: finishing early is rewarded.
    efficiency_ratio = max(0.0, 1.0 - (state.step_count / state.max_steps))

    communication = score_status_update(state.published_status, scenario, state) / 0.12
    public_trust = state.command_center.public_trust
    coordination = state.command_center.coordination_score
    unresolved_critical_ratio = (
        sum(1 for node in state.critical_nodes if not node.powered) / len(state.critical_nodes)
        if state.critical_nodes
        else 0.0
    )
    failure_penalty = min(0.18, 0.03 * len(state.failed_critical_nodes))

    # Hospital speed bonus: reward saving hospitals while backup still has >50% remaining.
    # This incentivises the agent to triage hospitals first, not last.
    hospital_speed_bonus = 0.0
    for node in state.critical_nodes:
        if node.powered and node.type.value == "hospital":
            # Find original backup from scenario to compute ratio saved.
            original = next(
                (n.backup_minutes_remaining for n in scenario.critical_nodes if n.id == node.id),
                None,
            )
            if original and original > 0:
                ratio_remaining = node.backup_minutes_remaining / original
                hospital_speed_bonus += 0.04 * ratio_remaining  # up to +0.04 per hospital
    hospital_speed_bonus = min(0.08, hospital_speed_bonus)  # cap at 0.08 total

    raw = (
        0.28 * critical_ratio
        + 0.20 * load_ratio
        + 0.22 * stability
        + 0.10 * inspection_ratio
        + 0.08 * efficiency_ratio
        + 0.08 * communication
        + 0.04 * public_trust
        + 0.04 * coordination
        + hospital_speed_bonus
    )
    raw -= 0.03 * unresolved_critical_ratio
    raw -= failure_penalty
    return clamp_score(raw)


def build_reward_breakdown(
    *,
    critical_restore_reward: float,
    load_restore_reward: float,
    stability_reward: float,
    inspection_reward: float,
    communication_reward: float,
    action_penalty: float,
    catastrophe_penalty: float,
    current_score: float,
) -> RewardBreakdown:
    return RewardBreakdown(
        critical_restore_reward=round(critical_restore_reward, 2),
        load_restore_reward=round(load_restore_reward, 2),
        stability_reward=round(stability_reward, 2),
        inspection_reward=round(inspection_reward, 2),
        communication_reward=round(communication_reward, 2),
        action_penalty=round(action_penalty, 2),
        catastrophe_penalty=round(catastrophe_penalty, 2),
        current_score=clamp_score(current_score),
    )
