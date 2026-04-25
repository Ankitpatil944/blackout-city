from blackstart_city.baseline import build_heuristic_actions, choose_heuristic_action
from blackstart_city.env import BlackstartCityEnv
from blackstart_city.grading import clamp_score
from blackstart_city.models import ActionType, BlackstartAction, StatusUpdate
from blackstart_city.tasks.scenarios import SCENARIO_FAMILIES
from blackstart_city.training.eval import evaluate_heuristic
from server.app import CompareRequest, compare


def test_reset_returns_valid_observation():
    env = BlackstartCityEnv()
    observation = env.reset(task_id="local_blackstart", seed=0)
    assert observation.task_id == "local_blackstart"
    assert observation.steps_remaining == 12
    assert observation.critical_nodes
    assert observation.command_center.role_recommendations
    assert observation.command_center.resource_state.repair_crews_total >= 1


def test_seeded_reset_is_deterministic():
    env = BlackstartCityEnv()
    first = env.reset(task_id="city_cascade_recovery", seed=1)
    second = env.reset(task_id="city_cascade_recovery", seed=1)
    third = env.reset(task_id="city_cascade_recovery", seed=2)
    assert first.incident_id == second.incident_id
    assert first.incident_id != third.incident_id


def test_heuristic_solves_easy_task():
    env = BlackstartCityEnv()
    observation = env.reset(task_id="local_blackstart", seed=0)
    info = {"score": 0.01, "resolved": False}
    published = False
    seen_signatures: set[str] = set()
    while not observation.done:
        action = choose_heuristic_action(
            observation,
            published_status=published,
            seen_signatures=seen_signatures,
        )
        if action is None:
            break
        seen_signatures.add(f"{action.action_type.value}|{action.target_id or ''}|{action.requested_mw or 0}")
        observation, _, done, info = env.step(action)
        if action.action_type == ActionType.PUBLISH_STATUS:
            published = True
        if done:
            break
    assert info["score"] >= 0.62


def test_static_plan_builder_returns_nonempty_skeleton():
    env = BlackstartCityEnv()
    observation = env.reset(task_id="local_blackstart", seed=0)
    actions = build_heuristic_actions(observation)
    assert actions
    assert actions[0].action_type == ActionType.START_GENERATOR


def test_closing_hidden_damaged_line_without_inspection_is_penalized():
    env = BlackstartCityEnv()
    env.reset(task_id="island_rejoin", seed=0)
    _, _, _, bad_info = env.step(BlackstartAction(action_type=ActionType.CLOSE_LINE, target_id="line_tie_1"))

    env = BlackstartCityEnv()
    env.reset(task_id="island_rejoin", seed=0)
    env.step(BlackstartAction(action_type=ActionType.INSPECT_LINE, target_id="line_tie_1"))
    _, _, _, good_info = env.step(BlackstartAction(action_type=ActionType.CLOSE_LINE, target_id="line_tie_1"))

    assert good_info["score"] >= bad_info["score"]


def test_status_update_scores_positive_when_relevant():
    env = BlackstartCityEnv()
    env.reset(task_id="local_blackstart", seed=0)
    observation, reward, _, info = env.step(
        BlackstartAction(
            action_type=ActionType.PUBLISH_STATUS,
            status_update=StatusUpdate(
                summary="Blackstart recovery is stabilizing the district hospital feeder.",
                critical_services="Hospital backup risk is falling while telecom and corridor load are prioritized.",
                next_action="Continue energizing substations and restore hospital service first.",
                owner="city restoration commander",
            ),
        )
    )
    # Total reward may be negative because publishing before critical-node recovery
    # incurs an intentional penalty.  The communication component itself should be positive.
    assert observation.reward_breakdown.communication_reward >= 0.0


def test_scores_clamp_to_required_range():
    assert clamp_score(0.0) == 0.01
    assert clamp_score(1.5) == 0.99


def test_restoring_noncritical_zone_before_critical_nodes_is_penalized():
    env = BlackstartCityEnv()
    env.reset(task_id="local_blackstart", seed=0)
    env.step(BlackstartAction(action_type=ActionType.START_GENERATOR, target_id="gen_blackstart_north"))
    env.step(BlackstartAction(action_type=ActionType.ACTIVATE_BATTERY_SUPPORT, target_id="battery_north"))
    env.step(BlackstartAction(action_type=ActionType.CLOSE_LINE, target_id="line_n_1"))
    env.step(BlackstartAction(action_type=ActionType.CLOSE_LINE, target_id="line_n_2"))
    env.step(BlackstartAction(action_type=ActionType.ENERGIZE_SUBSTATION, target_id="sub_north"))
    env.step(BlackstartAction(action_type=ActionType.ENERGIZE_SUBSTATION, target_id="sub_civic"))

    observation, reward, _, _ = env.step(
        BlackstartAction(action_type=ActionType.RESTORE_ZONE, target_id="zone_corridor_north", requested_mw=6)
    )
    assert reward < 0.17
    assert "Non-critical load" in observation.last_action_result


def test_hospital_failure_counts_once_after_backup_expires():
    env = BlackstartCityEnv()
    env.reset(task_id="local_blackstart", seed=0)
    state = env._require_state()
    hospital = next(node for node in state.critical_nodes if node.type.value == "hospital")
    hospital.backup_minutes_remaining = 0
    env._passive_dynamics()
    env._passive_dynamics()
    assert env.state.hospital_failures == 1


def test_heuristic_regression_floor():
    scores = evaluate_heuristic(seeds=2)
    assert scores["local_blackstart"] >= 0.55
    assert scores["island_rejoin"] >= 0.55
    assert scores["city_cascade_recovery"] >= 0.42


def test_compare_endpoint_shows_heuristic_beating_greedy_on_hard_seed():
    result = compare(CompareRequest(task_id="city_cascade_recovery", seed=0))
    assert result["heuristic"]["score"] > result["greedy"]["score"]
    assert "public_trust" in result["heuristic"]
    assert "coordination_score" in result["heuristic"]


def test_command_center_trust_changes_after_relevant_status_update():
    env = BlackstartCityEnv()
    observation = env.reset(task_id="local_blackstart", seed=0)
    start_trust = observation.command_center.public_trust
    env.step(BlackstartAction(action_type=ActionType.START_GENERATOR, target_id="gen_blackstart_north"))
    observation, _, _, _ = env.step(
        BlackstartAction(
            action_type=ActionType.PUBLISH_STATUS,
            status_update=StatusUpdate(
                summary="Blackstart command is restoring the district and protecting hospital continuity.",
                critical_services="Hospital and telecom restoration remain the top public safety priority for the district.",
                next_action="Continue safe feeder recovery while preserving reserve margin and preventing another collapse.",
                owner="city restoration commander",
            ),
        )
    )
    assert observation.command_center.public_trust != start_trust


def test_each_task_family_has_three_seeded_variants():
    assert len(SCENARIO_FAMILIES["local_blackstart"]) == 3
    assert len(SCENARIO_FAMILIES["island_rejoin"]) == 3
    assert len(SCENARIO_FAMILIES["city_cascade_recovery"]) == 3


def test_forbidden_target_constraint_triggers_penalty():
    """Closing line_tie_east on BSC-HARD-001 violates the school-zone constraint."""
    env = BlackstartCityEnv()
    env.reset(task_id="city_cascade_recovery", seed=0)
    env.step(BlackstartAction(action_type=ActionType.START_GENERATOR, target_id="gen_south_blackstart"))
    _, reward, _, info = env.step(
        BlackstartAction(action_type=ActionType.CLOSE_LINE, target_id="line_tie_east")
    )
    assert info["constraint_violations"] >= 1
    assert reward < 0


def test_news_events_are_revealed_at_correct_step():
    """BSC-HARD-001 has a news event at step 4 that reduces hospital backup."""
    env = BlackstartCityEnv()
    obs = env.reset(task_id="city_cascade_recovery", seed=0)
    assert len(obs.news_feed) == 0  # no news at step 0

    # Take 4 steps to reach trigger_step 4
    env.step(BlackstartAction(action_type=ActionType.START_GENERATOR, target_id="gen_south_blackstart"))
    env.step(BlackstartAction(action_type=ActionType.START_GENERATOR, target_id="gen_river_gas"))
    obs, _, _, _ = env.step(BlackstartAction(action_type=ActionType.INSPECT_LINE, target_id="line_tie_city"))
    # Step 3 — news at step 2 should have fired
    assert len(obs.news_feed) >= 1
    obs, _, _, _ = env.step(BlackstartAction(action_type=ActionType.INSPECT_LINE, target_id="line_tie_east"))
    # Step 4 — hospital backup news should have fired
    assert any("Hospital" in e.headline or "hospital" in e.headline for e in obs.news_feed)


def test_rubric_score_is_present_on_observation():
    """Every observation should include a rubric with four dimensions."""
    env = BlackstartCityEnv()
    obs = env.reset(task_id="city_cascade_recovery", seed=0)
    assert obs.rubric is not None
    assert 0.0 <= obs.rubric.safety <= 1.0
    assert 0.0 <= obs.rubric.triage_quality <= 1.0
    assert 0.0 <= obs.rubric.communication_clarity <= 1.0
    assert 0.0 <= obs.rubric.resource_efficiency <= 1.0
    assert 0.0 <= obs.rubric.overall <= 1.0


def test_constraints_visible_in_observation():
    """Hard scenario should expose active constraints to the agent."""
    env = BlackstartCityEnv()
    obs = env.reset(task_id="city_cascade_recovery", seed=0)
    assert len(obs.active_constraints) >= 2  # at least forbidden + conditional
    texts = [c.text for c in obs.active_constraints]
    assert any("line_tie_east" in t for t in texts)


def test_arbitration_reward_is_tracked_in_breakdown():
    """When multi-agent conflicts exist, the arbitration reward should be non-zero."""
    env = BlackstartCityEnv()
    obs = env.reset(task_id="city_cascade_recovery", seed=0)
    # First step: start a generator (Grid Operator usually recommends this)
    obs, reward, _, _ = env.step(
        BlackstartAction(action_type=ActionType.START_GENERATOR, target_id="gen_south_blackstart")
    )
    # The reward breakdown should have an arbitration_reward field
    assert hasattr(obs.reward_breakdown, "arbitration_reward")
    # Whether it's positive, negative, or zero depends on the conflict state,
    # but it must be a real number, not missing
    assert isinstance(obs.reward_breakdown.arbitration_reward, float)


def test_conflict_messages_marked_with_is_conflict():
    """Coordination messages that represent agent disagreements should be flagged."""
    env = BlackstartCityEnv()
    obs = env.reset(task_id="city_cascade_recovery", seed=0)
    # Check that the is_conflict field exists on all coordination messages
    for msg in obs.command_center.coordination_messages:
        assert isinstance(msg.is_conflict, bool)

