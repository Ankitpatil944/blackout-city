from __future__ import annotations

from blackstart_city.models import (
    ActionType,
    CityTaskSpec,
    Constraint,
    ConstraintType,
    CriticalNodeState,
    CriticalNodeType,
    DifficultyLevel,
    GeneratorState,
    LineState,
    NewsEvent,
    Scenario,
    SubstationState,
    ZonePriority,
    ZoneState,
)


def task(task_id: str, difficulty: DifficultyLevel, description: str, max_steps: int) -> CityTaskSpec:
    return CityTaskSpec(task_id=task_id, difficulty=difficulty, description=description, max_steps=max_steps)


LOCAL_TASK = task(
    "local_blackstart",
    DifficultyLevel.EASY,
    "Restore a district hospital and nearby city load after a substation trip.",
    12,
)
ISLAND_TASK = task(
    "island_rejoin",
    DifficultyLevel.MEDIUM,
    "Recover two dark grid islands and safely reconnect them.",
    18,
)
CITY_TASK = task(
    "city_cascade_recovery",
    DifficultyLevel.HARD,
    "Recover a city-scale blackout while hospitals, telecom, and water systems degrade.",
    26,
)


SCENARIO_FAMILIES = {
    "local_blackstart": [
        Scenario(
            incident_id="BSC-EASY-001",
            title="District Blackstart North",
            task=LOCAL_TASK,
            objective="Start local generation, energize the district substation, and restore St. Anne Hospital before backup power expires.",
            generators=[
                GeneratorState(id="gen_blackstart_north", bus="gen_bus_n", blackstart_capable=True, capacity_mw=30),
                GeneratorState(id="battery_north", bus="sub_north", blackstart_capable=False, capacity_mw=8),
            ],
            substations=[
                SubstationState(id="gen_bus_n", energized=False, island_id="north"),
                SubstationState(id="sub_north", energized=False, island_id="north"),
                SubstationState(id="sub_civic", energized=False, island_id="north"),
            ],
            lines=[
                LineState(id="line_n_1", from_bus="gen_bus_n", to_bus="sub_north", capacity_mw=40, closed=False),
                LineState(id="line_n_2", from_bus="sub_north", to_bus="sub_civic", capacity_mw=25, closed=False),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="hospital_st_anne",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_civic",
                    demand_mw=12,
                    powered=False,
                    backup_minutes_remaining=24,
                    population_impact=1800,
                ),
                CriticalNodeState(
                    id="telecom_north_1",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_north",
                    demand_mw=4,
                    powered=False,
                    backup_minutes_remaining=40,
                    population_impact=32000,
                ),
            ],
            zones=[
                ZoneState(id="zone_res_north", feeder_bus="sub_north", priority=ZonePriority.RESIDENTIAL, demand_mw=10),
                ZoneState(id="zone_corridor_north", feeder_bus="sub_civic", priority=ZonePriority.CORRIDOR, demand_mw=6),
            ],
            hidden_damaged_lines=[],
            warnings=["Hospital backup estimated under 30 minutes.", "All district feeders are currently dark."],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_blackstart_north"},
                {"action_type": "close_line", "target_id": "line_n_1"},
                {"action_type": "energize_substation", "target_id": "sub_north"},
                {"action_type": "restore_critical_node", "target_id": "telecom_north_1"},
                {"action_type": "close_line", "target_id": "line_n_2"},
                {"action_type": "energize_substation", "target_id": "sub_civic"},
                {"action_type": "restore_critical_node", "target_id": "hospital_st_anne"},
            ],
            status_keywords=["hospital", "blackstart", "stabilized", "backup"],
            constraints=[
                Constraint(
                    id="c_hospital_first",
                    text="Restore St. Anne Hospital before any corridor zone load is reconnected.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="hospital_st_anne",
                    before_restoring="zone_corridor_north",
                    active=True,
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_backup_warning",
                    trigger_step=3,
                    headline="Hospital St. Anne reports backup generator overheating.",
                    detail="Hospital maintenance reports the backup generator is running hot. Effective backup time may be shorter than estimated.",
                    impact_level="warning",
                    reduces_backup_node="hospital_st_anne",
                    reduces_backup_by=4,
                    public_trust_delta=-0.04,
                ),
            ],
        ),
        Scenario(
            incident_id="BSC-EASY-002",
            title="District Blackstart West",
            task=LOCAL_TASK,
            objective="Restore Mercy Clinic and a telecom repeater using west-side blackstart generation.",
            generators=[
                GeneratorState(id="gen_blackstart_west", bus="gen_bus_w", blackstart_capable=True, capacity_mw=24),
                GeneratorState(id="battery_west", bus="sub_west", blackstart_capable=False, capacity_mw=6),
            ],
            substations=[
                SubstationState(id="gen_bus_w", energized=False, island_id="west"),
                SubstationState(id="sub_west", energized=False, island_id="west"),
                SubstationState(id="sub_medical_w", energized=False, island_id="west"),
            ],
            lines=[
                LineState(id="line_w_1", from_bus="gen_bus_w", to_bus="sub_west", capacity_mw=30, closed=False),
                LineState(id="line_w_2", from_bus="sub_west", to_bus="sub_medical_w", capacity_mw=20, closed=False),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="clinic_mercy",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_medical_w",
                    demand_mw=10,
                    powered=False,
                    backup_minutes_remaining=20,
                    population_impact=1200,
                ),
                CriticalNodeState(
                    id="telecom_west_1",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_west",
                    demand_mw=3,
                    powered=False,
                    backup_minutes_remaining=28,
                    population_impact=21000,
                ),
            ],
            zones=[
                ZoneState(id="zone_res_west", feeder_bus="sub_west", priority=ZonePriority.RESIDENTIAL, demand_mw=8),
                ZoneState(id="zone_industry_west", feeder_bus="sub_medical_w", priority=ZonePriority.INDUSTRIAL, demand_mw=9),
            ],
            hidden_damaged_lines=[],
            warnings=["Medical feeder offline in west district."],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_blackstart_west"},
                {"action_type": "close_line", "target_id": "line_w_1"},
                {"action_type": "energize_substation", "target_id": "sub_west"},
                {"action_type": "restore_critical_node", "target_id": "telecom_west_1"},
                {"action_type": "close_line", "target_id": "line_w_2"},
                {"action_type": "energize_substation", "target_id": "sub_medical_w"},
                {"action_type": "restore_critical_node", "target_id": "clinic_mercy"},
            ],
            status_keywords=["medical", "west district", "restoration"],
            constraints=[
                Constraint(
                    id="c_clinic_first",
                    text="Restore Mercy Clinic before industrial zone load is reconnected.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="clinic_mercy",
                    before_restoring="zone_industry_west",
                    active=True,
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_clinic_surge",
                    trigger_step=4,
                    headline="Mercy Clinic reports incoming patient surge from west district.",
                    detail="Emergency services are routing patients to Mercy Clinic. Restore clinic power immediately to avoid critical care failures.",
                    impact_level="critical",
                    public_trust_delta=-0.05,
                ),
            ],
        ),
        Scenario(
            incident_id="BSC-EASY-003",
            title="District Blackstart South",
            task=LOCAL_TASK,
            objective="Restore Southside ER and the dispatch repeater before commuter corridor load is brought back.",
            generators=[
                GeneratorState(id="gen_blackstart_south", bus="gen_bus_s", blackstart_capable=True, capacity_mw=28),
                GeneratorState(id="battery_south", bus="sub_south", blackstart_capable=False, capacity_mw=7),
            ],
            substations=[
                SubstationState(id="gen_bus_s", energized=False, island_id="south"),
                SubstationState(id="sub_south", energized=False, island_id="south"),
                SubstationState(id="sub_dispatch", energized=False, island_id="south"),
            ],
            lines=[
                LineState(id="line_s_easy_1", from_bus="gen_bus_s", to_bus="sub_south", capacity_mw=34, closed=False),
                LineState(id="line_s_easy_2", from_bus="sub_south", to_bus="sub_dispatch", capacity_mw=18, closed=False),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="er_southside",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_dispatch",
                    demand_mw=11,
                    powered=False,
                    backup_minutes_remaining=22,
                    population_impact=1600,
                ),
                CriticalNodeState(
                    id="telecom_dispatch_s",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_south",
                    demand_mw=3,
                    powered=False,
                    backup_minutes_remaining=26,
                    population_impact=27000,
                ),
            ],
            zones=[
                ZoneState(id="zone_south_res", feeder_bus="sub_south", priority=ZonePriority.RESIDENTIAL, demand_mw=9),
                ZoneState(id="zone_dispatch_corridor", feeder_bus="sub_dispatch", priority=ZonePriority.CORRIDOR, demand_mw=7),
            ],
            hidden_damaged_lines=[],
            warnings=["Southside ER is running on a fragile backup circuit.", "Dispatch corridor remains dark."],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_blackstart_south"},
                {"action_type": "close_line", "target_id": "line_s_easy_1"},
                {"action_type": "energize_substation", "target_id": "sub_south"},
                {"action_type": "restore_critical_node", "target_id": "telecom_dispatch_s"},
                {"action_type": "close_line", "target_id": "line_s_easy_2"},
                {"action_type": "energize_substation", "target_id": "sub_dispatch"},
                {"action_type": "restore_critical_node", "target_id": "er_southside"},
            ],
            status_keywords=["southside", "dispatch", "hospital", "backup"],
            constraints=[
                Constraint(
                    id="c_er_first",
                    text="Restore Southside ER before any residential zone receives load.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="er_southside",
                    before_restoring="zone_south_res",
                    active=True,
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_dispatch_outage",
                    trigger_step=3,
                    headline="Emergency dispatch radio reports intermittent coverage in south district.",
                    detail="Telecom dispatch tower backup batteries are draining faster than expected. Prioritize telecom restoration.",
                    impact_level="warning",
                    reduces_backup_node="telecom_dispatch_s",
                    reduces_backup_by=5,
                    public_trust_delta=-0.03,
                ),
            ],
        ),
    ],
    "island_rejoin": [
        Scenario(
            incident_id="BSC-MED-001",
            title="Twin Island Restoration",
            task=ISLAND_TASK,
            objective="Recover east and civic islands, restore the water plant, and safely sync the transmission corridor.",
            generators=[
                GeneratorState(id="gen_east_blackstart", bus="gen_east", blackstart_capable=True, capacity_mw=35),
                GeneratorState(id="gen_civic_gas", bus="gen_civic", blackstart_capable=True, capacity_mw=28),
                GeneratorState(id="battery_east", bus="sub_east", blackstart_capable=False, capacity_mw=10),
            ],
            substations=[
                SubstationState(id="gen_east", energized=False, island_id="east"),
                SubstationState(id="sub_east", energized=False, island_id="east"),
                SubstationState(id="gen_civic", energized=False, island_id="civic"),
                SubstationState(id="sub_civic", energized=False, island_id="civic"),
                SubstationState(id="sub_water", energized=False, island_id="civic"),
            ],
            lines=[
                LineState(id="line_e_1", from_bus="gen_east", to_bus="sub_east", capacity_mw=35, closed=False),
                LineState(id="line_c_1", from_bus="gen_civic", to_bus="sub_civic", capacity_mw=30, closed=False),
                LineState(id="line_c_2", from_bus="sub_civic", to_bus="sub_water", capacity_mw=22, closed=False),
                LineState(id="line_tie_1", from_bus="sub_east", to_bus="sub_civic", capacity_mw=28, closed=False, damaged=True),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="hospital_east",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_east",
                    demand_mw=14,
                    powered=False,
                    backup_minutes_remaining=32,
                    population_impact=2500,
                ),
                CriticalNodeState(
                    id="water_plant_central",
                    type=CriticalNodeType.WATER,
                    feeder_bus="sub_water",
                    demand_mw=11,
                    powered=False,
                    backup_minutes_remaining=38,
                    population_impact=145000,
                ),
            ],
            zones=[
                ZoneState(id="zone_east_res", feeder_bus="sub_east", priority=ZonePriority.RESIDENTIAL, demand_mw=12),
                ZoneState(id="zone_civic_corridor", feeder_bus="sub_civic", priority=ZonePriority.CORRIDOR, demand_mw=8),
                ZoneState(id="zone_water_industry", feeder_bus="sub_water", priority=ZonePriority.INDUSTRIAL, demand_mw=7),
            ],
            hidden_damaged_lines=["line_tie_1"],
            warnings=["Tie-line condition unknown after the cascade.", "Water pressure reserve estimated under one hour."],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_east_blackstart"},
                {"action_type": "close_line", "target_id": "line_e_1"},
                {"action_type": "energize_substation", "target_id": "sub_east"},
                {"action_type": "restore_critical_node", "target_id": "hospital_east"},
                {"action_type": "start_generator", "target_id": "gen_civic_gas"},
                {"action_type": "close_line", "target_id": "line_c_1"},
                {"action_type": "energize_substation", "target_id": "sub_civic"},
                {"action_type": "close_line", "target_id": "line_c_2"},
                {"action_type": "energize_substation", "target_id": "sub_water"},
                {"action_type": "restore_critical_node", "target_id": "water_plant_central"},
                {"action_type": "inspect_line", "target_id": "line_tie_1"},
                {"action_type": "sync_islands", "target_id": "line_tie_1"},
            ],
            status_keywords=["water", "tie-line", "synchronized"],
            constraints=[
                Constraint(
                    id="c_no_tie1_blind",
                    text="Never close line_tie_1 without inspecting it first — storm damage reports indicate possible structural failure.",
                    constraint_type=ConstraintType.FORBIDDEN_TARGET,
                    forbidden_action_type=ActionType.CLOSE_LINE,
                    forbidden_target_id="line_tie_1",
                    active=True,
                ),
                Constraint(
                    id="c_water_before_zones",
                    text="Restore the water treatment plant before any residential zone receives load.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="water_plant_central",
                    before_restoring="zone_east_res",
                    active=True,
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_tie1_damage",
                    trigger_step=3,
                    headline="Field crews report: line_tie_1 support tower leaning dangerously.",
                    detail="Structural assessment confirms the tie-line tower is compromised. Full inspection required before any reconnection attempt.",
                    impact_level="warning",
                    public_trust_delta=-0.04,
                ),
                NewsEvent(
                    id="news_water_pressure",
                    trigger_step=6,
                    headline="ALERT: Water pressure below minimum across east district.",
                    detail="Fire suppression systems are failing without water plant power. Hospitals and emergency services are at elevated risk.",
                    impact_level="critical",
                    public_trust_delta=-0.06,
                ),
            ],
        ),
        Scenario(
            incident_id="BSC-MED-002",
            title="Harbor and Core Rejoin",
            task=ISLAND_TASK,
            objective="Restore Harbor General and rejoin the harbor island after verifying the corridor line.",
            generators=[
                GeneratorState(id="gen_harbor_blackstart", bus="gen_harbor", blackstart_capable=True, capacity_mw=26),
                GeneratorState(id="gen_core_blackstart", bus="gen_core", blackstart_capable=True, capacity_mw=34),
            ],
            substations=[
                SubstationState(id="gen_harbor", energized=False, island_id="harbor"),
                SubstationState(id="sub_harbor", energized=False, island_id="harbor"),
                SubstationState(id="gen_core", energized=False, island_id="core"),
                SubstationState(id="sub_core", energized=False, island_id="core"),
            ],
            lines=[
                LineState(id="line_h_1", from_bus="gen_harbor", to_bus="sub_harbor", capacity_mw=28, closed=False),
                LineState(id="line_core_1", from_bus="gen_core", to_bus="sub_core", capacity_mw=35, closed=False),
                LineState(id="line_tie_hc", from_bus="sub_harbor", to_bus="sub_core", capacity_mw=24, closed=False, damaged=True),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="hospital_harbor",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_harbor",
                    demand_mw=13,
                    powered=False,
                    backup_minutes_remaining=26,
                    population_impact=2100,
                ),
                CriticalNodeState(
                    id="telecom_core",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_core",
                    demand_mw=5,
                    powered=False,
                    backup_minutes_remaining=24,
                    population_impact=87000,
                ),
            ],
            zones=[
                ZoneState(id="zone_harbor", feeder_bus="sub_harbor", priority=ZonePriority.CORRIDOR, demand_mw=9),
                ZoneState(id="zone_core_res", feeder_bus="sub_core", priority=ZonePriority.RESIDENTIAL, demand_mw=14),
            ],
            hidden_damaged_lines=["line_tie_hc"],
            warnings=["Harbor hospital running on backup.", "Tie corridor integrity unknown."],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_harbor_blackstart"},
                {"action_type": "close_line", "target_id": "line_h_1"},
                {"action_type": "energize_substation", "target_id": "sub_harbor"},
                {"action_type": "restore_critical_node", "target_id": "hospital_harbor"},
                {"action_type": "start_generator", "target_id": "gen_core_blackstart"},
                {"action_type": "close_line", "target_id": "line_core_1"},
                {"action_type": "energize_substation", "target_id": "sub_core"},
                {"action_type": "restore_critical_node", "target_id": "telecom_core"},
                {"action_type": "inspect_line", "target_id": "line_tie_hc"},
                {"action_type": "sync_islands", "target_id": "line_tie_hc"},
            ],
            status_keywords=["harbor", "corridor", "core"],
            constraints=[
                Constraint(
                    id="c_hospital_harbor_first",
                    text="Restore Harbor General Hospital before reconnecting any corridor zone load.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="hospital_harbor",
                    before_restoring="zone_harbor",
                    active=True,
                ),
                Constraint(
                    id="c_no_harbor_tie_blind",
                    text="Do not close the harbor tie-line without inspection — underwater cable may be compromised.",
                    constraint_type=ConstraintType.FORBIDDEN_TARGET,
                    forbidden_action_type=ActionType.CLOSE_LINE,
                    forbidden_target_id="line_tie_hc",
                    active=True,
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_harbor_flooding",
                    trigger_step=4,
                    headline="Harbor district reports localized flooding near substation sub_harbor.",
                    detail="Flooding may delay crew access to harbor substation. Plan alternative restoration paths if possible.",
                    impact_level="warning",
                    public_trust_delta=-0.04,
                ),
                NewsEvent(
                    id="news_harbor_hospital_urgency",
                    trigger_step=7,
                    headline="Harbor General ICU running on last battery reserves.",
                    detail="Hospital administration reports ICU backup will fail within minutes. Immediate power restoration critical.",
                    impact_level="critical",
                    reduces_backup_node="hospital_harbor",
                    reduces_backup_by=5,
                    public_trust_delta=-0.07,
                ),
            ],
        ),
        Scenario(
            incident_id="BSC-MED-003",
            title="North and River Rejoin",
            task=ISLAND_TASK,
            objective="Restore the north clinic and central telecom while verifying a degraded river tie before synchronization.",
            generators=[
                GeneratorState(id="gen_north_island", bus="gen_north_i", blackstart_capable=True, capacity_mw=30),
                GeneratorState(id="gen_river_island", bus="gen_river_i", blackstart_capable=True, capacity_mw=32),
                GeneratorState(id="battery_river", bus="sub_river", blackstart_capable=False, capacity_mw=8),
            ],
            substations=[
                SubstationState(id="gen_north_i", energized=False, island_id="north"),
                SubstationState(id="sub_north_i", energized=False, island_id="north"),
                SubstationState(id="gen_river_i", energized=False, island_id="river"),
                SubstationState(id="sub_river", energized=False, island_id="river"),
                SubstationState(id="sub_telecom_r", energized=False, island_id="river"),
            ],
            lines=[
                LineState(id="line_nr_1", from_bus="gen_north_i", to_bus="sub_north_i", capacity_mw=30, closed=False),
                LineState(id="line_rr_1", from_bus="gen_river_i", to_bus="sub_river", capacity_mw=32, closed=False),
                LineState(id="line_rr_2", from_bus="sub_river", to_bus="sub_telecom_r", capacity_mw=18, closed=False),
                LineState(id="line_tie_nr", from_bus="sub_north_i", to_bus="sub_river", capacity_mw=20, closed=False, damaged=True),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="clinic_north_i",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_north_i",
                    demand_mw=12,
                    powered=False,
                    backup_minutes_remaining=28,
                    population_impact=1750,
                ),
                CriticalNodeState(
                    id="telecom_river_core",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_telecom_r",
                    demand_mw=5,
                    powered=False,
                    backup_minutes_remaining=20,
                    population_impact=101000,
                ),
            ],
            zones=[
                ZoneState(id="zone_north_i_res", feeder_bus="sub_north_i", priority=ZonePriority.RESIDENTIAL, demand_mw=10),
                ZoneState(id="zone_river_corridor", feeder_bus="sub_river", priority=ZonePriority.CORRIDOR, demand_mw=7),
            ],
            hidden_damaged_lines=["line_tie_nr"],
            warnings=["River tie was stressed during the cascade and must be verified.", "North clinic backup is under 30 minutes."],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_north_island"},
                {"action_type": "close_line", "target_id": "line_nr_1"},
                {"action_type": "energize_substation", "target_id": "sub_north_i"},
                {"action_type": "restore_critical_node", "target_id": "clinic_north_i"},
                {"action_type": "start_generator", "target_id": "gen_river_island"},
                {"action_type": "close_line", "target_id": "line_rr_1"},
                {"action_type": "energize_substation", "target_id": "sub_river"},
                {"action_type": "close_line", "target_id": "line_rr_2"},
                {"action_type": "energize_substation", "target_id": "sub_telecom_r"},
                {"action_type": "restore_critical_node", "target_id": "telecom_river_core"},
                {"action_type": "inspect_line", "target_id": "line_tie_nr"},
                {"action_type": "sync_islands", "target_id": "line_tie_nr"},
            ],
            status_keywords=["north clinic", "river tie", "telecom", "sync"],
            constraints=[
                Constraint(
                    id="c_clinic_north_first",
                    text="Restore North Clinic before reconnecting any residential zone.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="clinic_north_i",
                    before_restoring="zone_north_i_res",
                    active=True,
                ),
                Constraint(
                    id="c_no_river_tie_blind",
                    text="Do not close line_river_tie without inspection — flash flooding may have weakened the river crossing.",
                    constraint_type=ConstraintType.FORBIDDEN_TARGET,
                    forbidden_action_type=ActionType.CLOSE_LINE,
                    forbidden_target_id="line_tie_nr",
                    active=True,
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_river_flooding",
                    trigger_step=4,
                    headline="Flash flood alert: river levels rising near line_river_tie crossing.",
                    detail="River monitoring stations report surging water levels. Do not attempt line closure until field crews confirm structural integrity.",
                    impact_level="warning",
                    public_trust_delta=-0.03,
                ),
                NewsEvent(
                    id="news_clinic_north_backup",
                    trigger_step=8,
                    headline="North Clinic backup generator fuel running low.",
                    detail="North Clinic maintenance confirms diesel reserves will be exhausted soon. Grid power restoration is now the only option.",
                    impact_level="critical",
                    reduces_backup_node="clinic_north_i",
                    reduces_backup_by=6,
                    public_trust_delta=-0.05,
                ),
            ],
        ),
    ],
    "city_cascade_recovery": [
        Scenario(
            incident_id="BSC-HARD-001",
            title="Metro Cascade Night One",
            task=CITY_TASK,
            objective="Restore hospitals, telecom, water, and emergency services before cascading failures trigger a second city-wide blackout.",
            generators=[
                GeneratorState(id="gen_south_blackstart", bus="gen_south", blackstart_capable=True, capacity_mw=42),
                GeneratorState(id="gen_river_gas", bus="gen_river", blackstart_capable=True, capacity_mw=38),
                GeneratorState(id="battery_core", bus="sub_core", blackstart_capable=False, capacity_mw=12),
            ],
            substations=[
                SubstationState(id="gen_south", energized=False, island_id="south"),
                SubstationState(id="sub_south", energized=False, island_id="south"),
                SubstationState(id="gen_river", energized=False, island_id="river"),
                SubstationState(id="sub_core", energized=False, island_id="core"),
                SubstationState(id="sub_medical", energized=False, island_id="core"),
                SubstationState(id="sub_water", energized=False, island_id="core"),
                SubstationState(id="sub_east", energized=False, island_id="east"),
            ],
            lines=[
                LineState(id="line_s_1", from_bus="gen_south", to_bus="sub_south", capacity_mw=45, closed=False),
                LineState(id="line_r_1", from_bus="gen_river", to_bus="sub_core", capacity_mw=40, closed=False),
                LineState(id="line_core_1", from_bus="sub_core", to_bus="sub_medical", capacity_mw=25, closed=False),
                LineState(id="line_core_2", from_bus="sub_core", to_bus="sub_water", capacity_mw=22, closed=False),
                LineState(id="line_tie_city", from_bus="sub_south", to_bus="sub_core", capacity_mw=24, closed=False, damaged=True),
                LineState(id="line_tie_east", from_bus="sub_core", to_bus="sub_east", capacity_mw=20, closed=False, damaged=True),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="hospital_central",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_medical",
                    demand_mw=16,
                    powered=False,
                    backup_minutes_remaining=18,
                    population_impact=4100,
                ),
                CriticalNodeState(
                    id="telecom_core_1",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_core",
                    demand_mw=6,
                    powered=False,
                    backup_minutes_remaining=15,
                    population_impact=240000,
                ),
                CriticalNodeState(
                    id="water_plant_main",
                    type=CriticalNodeType.WATER,
                    feeder_bus="sub_water",
                    demand_mw=12,
                    powered=False,
                    backup_minutes_remaining=22,
                    population_impact=320000,
                ),
                CriticalNodeState(
                    id="emergency_ops",
                    type=CriticalNodeType.EMERGENCY,
                    feeder_bus="sub_south",
                    demand_mw=9,
                    powered=False,
                    backup_minutes_remaining=20,
                    population_impact=120000,
                ),
            ],
            zones=[
                ZoneState(id="zone_south_res", feeder_bus="sub_south", priority=ZonePriority.RESIDENTIAL, demand_mw=14),
                ZoneState(id="zone_core_corridor", feeder_bus="sub_core", priority=ZonePriority.CORRIDOR, demand_mw=10),
                ZoneState(id="zone_east_res", feeder_bus="sub_east", priority=ZonePriority.RESIDENTIAL, demand_mw=11),
                ZoneState(id="zone_industrial", feeder_bus="sub_water", priority=ZonePriority.INDUSTRIAL, demand_mw=12),
            ],
            hidden_damaged_lines=["line_tie_city", "line_tie_east"],
            warnings=[
                "Central hospital backup under 20 minutes.",
                "Core telecom tower battery under 15 minutes.",
                "Water pressure reserve dropping as pumps remain offline.",
            ],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_river_gas"},
                {"action_type": "close_line", "target_id": "line_r_1"},
                {"action_type": "energize_substation", "target_id": "sub_core"},
                {"action_type": "restore_critical_node", "target_id": "telecom_core_1"},
                {"action_type": "close_line", "target_id": "line_core_1"},
                {"action_type": "energize_substation", "target_id": "sub_medical"},
                {"action_type": "restore_critical_node", "target_id": "hospital_central"},
                {"action_type": "close_line", "target_id": "line_core_2"},
                {"action_type": "energize_substation", "target_id": "sub_water"},
                {"action_type": "restore_critical_node", "target_id": "water_plant_main"},
                {"action_type": "start_generator", "target_id": "gen_south_blackstart"},
                {"action_type": "close_line", "target_id": "line_s_1"},
                {"action_type": "energize_substation", "target_id": "sub_south"},
                {"action_type": "restore_critical_node", "target_id": "emergency_ops"},
                {"action_type": "inspect_line", "target_id": "line_tie_city"},
                {"action_type": "sync_islands", "target_id": "line_tie_city"},
            ],
            status_keywords=["hospital", "telecom", "water", "city stabilization", "second blackout"],
            constraints=[
                # ── Forbidden: school-zone crossing must never be energized ──────────
                Constraint(
                    id="c_no_east_tie",
                    text=(
                        "Never energize line_tie_east — storm debris near Eastside Elementary School "
                        "makes this crossing a safety exclusion zone. Field safety orders prohibit any action on this line."
                    ),
                    constraint_type=ConstraintType.FORBIDDEN_TARGET,
                    forbidden_action_type=ActionType.CLOSE_LINE,
                    forbidden_target_id="line_tie_east",
                    active=True,
                ),
                # ── Conditional: industrial zone stays ≤ 10 MW until reserve > 20 MW
                Constraint(
                    id="c_industrial_limit",
                    text=(
                        "Industrial zone load must remain below 10 MW until the reserve margin exceeds 20 MW. "
                        "Premature heavy-load restoration risks a second cascade."
                    ),
                    constraint_type=ConstraintType.CONDITIONAL_LIMIT,
                    limit_target_id="zone_industrial",
                    limit_mw=10,
                    condition_field="reserve_margin_mw",
                    condition_threshold=20.0,
                    active=True,
                ),
                # ── Priority order: activated mid-episode by city council news ──────
                Constraint(
                    id="c_emergency_before_residential",
                    text=(
                        "City council emergency order: emergency operations must be restored "
                        "before any residential zone receives load."
                    ),
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="emergency_ops",
                    before_restoring="zone_south_res",
                    active=False,  # activated by news at step 6
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_line_damage_confirmed",
                    trigger_step=2,
                    headline="Field report: Structural damage confirmed at line_tie_city crossing.",
                    detail=(
                        "Repair crews have confirmed significant structural damage to the line_tie_city "
                        "support towers. Full inspection is mandatory before any closure attempt."
                    ),
                    impact_level="warning",
                    public_trust_delta=-0.03,
                ),
                NewsEvent(
                    id="news_hospital_generator_failure",
                    trigger_step=4,
                    headline="ALERT: Hospital Central internal generator degraded — backup revised to 12 min.",
                    detail=(
                        "Hospital Central reports an auxiliary generator fault. "
                        "Effective backup window is now critically short. Immediate grid restoration required."
                    ),
                    impact_level="critical",
                    reduces_backup_node="hospital_central",
                    reduces_backup_by=6,
                    public_trust_delta=-0.06,
                ),
                NewsEvent(
                    id="news_council_emergency_order",
                    trigger_step=6,
                    headline="City Council emergency order: emergency ops before residential zones.",
                    detail=(
                        "The city council has issued an emergency directive requiring that the Emergency "
                        "Operations Centre be restored before any residential zone load is reconnected."
                    ),
                    impact_level="warning",
                    activates_constraint_id="c_emergency_before_residential",
                    public_trust_delta=-0.05,
                ),
            ],
        ),
        Scenario(
            incident_id="BSC-HARD-002",
            title="Metro Cascade Dawn Shift",
            task=CITY_TASK,
            objective="Restore a dawn-shift blackout with fragile core transmission and limited reserve margin.",
            generators=[
                GeneratorState(id="gen_north_blackstart", bus="gen_north", blackstart_capable=True, capacity_mw=40),
                GeneratorState(id="gen_central_gas", bus="gen_central", blackstart_capable=True, capacity_mw=36),
                GeneratorState(id="battery_medical", bus="sub_medical", blackstart_capable=False, capacity_mw=10),
            ],
            substations=[
                SubstationState(id="gen_north", energized=False, island_id="north"),
                SubstationState(id="sub_north", energized=False, island_id="north"),
                SubstationState(id="gen_central", energized=False, island_id="central"),
                SubstationState(id="sub_core", energized=False, island_id="central"),
                SubstationState(id="sub_medical", energized=False, island_id="central"),
                SubstationState(id="sub_water", energized=False, island_id="central"),
            ],
            lines=[
                LineState(id="line_n_1", from_bus="gen_north", to_bus="sub_north", capacity_mw=42, closed=False),
                LineState(id="line_c_1", from_bus="gen_central", to_bus="sub_core", capacity_mw=38, closed=False),
                LineState(id="line_c_2", from_bus="sub_core", to_bus="sub_medical", capacity_mw=20, closed=False),
                LineState(id="line_c_3", from_bus="sub_core", to_bus="sub_water", capacity_mw=20, closed=False),
                LineState(id="line_tie_nc", from_bus="sub_north", to_bus="sub_core", capacity_mw=18, closed=False, damaged=True),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="hospital_north",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_medical",
                    demand_mw=14,
                    powered=False,
                    backup_minutes_remaining=19,
                    population_impact=3000,
                ),
                CriticalNodeState(
                    id="telecom_north",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_core",
                    demand_mw=5,
                    powered=False,
                    backup_minutes_remaining=16,
                    population_impact=180000,
                ),
                CriticalNodeState(
                    id="water_north",
                    type=CriticalNodeType.WATER,
                    feeder_bus="sub_water",
                    demand_mw=11,
                    powered=False,
                    backup_minutes_remaining=21,
                    population_impact=220000,
                ),
            ],
            zones=[
                ZoneState(id="zone_north_res", feeder_bus="sub_north", priority=ZonePriority.RESIDENTIAL, demand_mw=12),
                ZoneState(id="zone_core_res", feeder_bus="sub_core", priority=ZonePriority.RESIDENTIAL, demand_mw=12),
                ZoneState(id="zone_core_corridor", feeder_bus="sub_core", priority=ZonePriority.CORRIDOR, demand_mw=8),
            ],
            hidden_damaged_lines=["line_tie_nc"],
            warnings=["Reserve margin is expected to stay tight until both islands are synchronized."],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_central_gas"},
                {"action_type": "close_line", "target_id": "line_c_1"},
                {"action_type": "energize_substation", "target_id": "sub_core"},
                {"action_type": "restore_critical_node", "target_id": "telecom_north"},
                {"action_type": "close_line", "target_id": "line_c_2"},
                {"action_type": "energize_substation", "target_id": "sub_medical"},
                {"action_type": "restore_critical_node", "target_id": "hospital_north"},
                {"action_type": "close_line", "target_id": "line_c_3"},
                {"action_type": "energize_substation", "target_id": "sub_water"},
                {"action_type": "restore_critical_node", "target_id": "water_north"},
                {"action_type": "start_generator", "target_id": "gen_north_blackstart"},
                {"action_type": "close_line", "target_id": "line_n_1"},
                {"action_type": "energize_substation", "target_id": "sub_north"},
                {"action_type": "inspect_line", "target_id": "line_tie_nc"},
                {"action_type": "sync_islands", "target_id": "line_tie_nc"},
            ],
            status_keywords=["reserve margin", "north", "synchronized"],
            constraints=[
                Constraint(
                    id="c_no_nc_tie_blind",
                    text=(
                        "Do not close line_tie_nc without prior inspection — "
                        "dawn-shift crews reported suspected ice damage on the north-core corridor crossing."
                    ),
                    constraint_type=ConstraintType.FORBIDDEN_TARGET,
                    forbidden_action_type=ActionType.CLOSE_LINE,
                    forbidden_target_id="line_tie_nc",
                    active=True,
                ),
                Constraint(
                    id="c_hospital_north_before_north_res",
                    text="Restore North Hospital before any north residential zone receives load — medical triage order.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="hospital_north",
                    before_restoring="zone_north_res",
                    active=True,
                ),
                Constraint(
                    id="c_core_corridor_limit",
                    text=(
                        "Core corridor zone load must remain below 8 MW until reserve margin exceeds 18 MW. "
                        "Dawn-shift low-reserve conditions prohibit full corridor restoration early."
                    ),
                    constraint_type=ConstraintType.CONDITIONAL_LIMIT,
                    limit_target_id="zone_core_corridor",
                    limit_mw=8,
                    condition_field="reserve_margin_mw",
                    condition_threshold=18.0,
                    active=False,  # activated by city operations news at step 7
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_nc_tie_ice_damage",
                    trigger_step=2,
                    headline="Dawn maintenance report: ice loading suspected on line_tie_nc support towers.",
                    detail=(
                        "Overnight temperature dropped to -12°C. Inspection crews flag possible ice accumulation "
                        "on the north-core tie crossing. Full structural inspection required before any closure attempt."
                    ),
                    impact_level="warning",
                    public_trust_delta=-0.03,
                ),
                NewsEvent(
                    id="news_hospital_north_backup_drain",
                    trigger_step=4,
                    headline="ALERT: North Hospital backup generator fuel contaminated — revised to 14 min.",
                    detail=(
                        "Hospital North reports water contamination in backup fuel supply. "
                        "Effective backup window now critically short. Grid power is the only option."
                    ),
                    impact_level="critical",
                    reduces_backup_node="hospital_north",
                    reduces_backup_by=5,
                    public_trust_delta=-0.06,
                ),
                NewsEvent(
                    id="news_dawn_corridor_load_order",
                    trigger_step=7,
                    headline="City operations: core corridor load limited until reserve stabilises.",
                    detail=(
                        "Dawn-shift grid controller issues a load-limiting directive for the core corridor zone. "
                        "Restoration must not exceed 8 MW until reserve margin is confirmed above 18 MW."
                    ),
                    impact_level="warning",
                    activates_constraint_id="c_core_corridor_limit",
                    public_trust_delta=-0.04,
                ),
            ],
        ),
        Scenario(
            incident_id="BSC-HARD-003",
            title="Metro Cascade Harbor Storm",
            task=CITY_TASK,
            objective="Restore harbor emergency ops, medical load, telecom, and water during a storm-shift blackout with two fragile inter-island corridors.",
            generators=[
                GeneratorState(id="gen_harbor_blackstart_h", bus="gen_harbor_h", blackstart_capable=True, capacity_mw=39),
                GeneratorState(id="gen_core_blackstart_h", bus="gen_core_h", blackstart_capable=True, capacity_mw=37),
                GeneratorState(id="battery_harbor_h", bus="sub_harbor_h", blackstart_capable=False, capacity_mw=9),
            ],
            substations=[
                SubstationState(id="gen_harbor_h", energized=False, island_id="harbor"),
                SubstationState(id="sub_harbor_h", energized=False, island_id="harbor"),
                SubstationState(id="gen_core_h", energized=False, island_id="core"),
                SubstationState(id="sub_core_h", energized=False, island_id="core"),
                SubstationState(id="sub_medical_h", energized=False, island_id="core"),
                SubstationState(id="sub_water_h", energized=False, island_id="core"),
                SubstationState(id="sub_corridor_h", energized=False, island_id="east"),
            ],
            lines=[
                LineState(id="line_hh_1", from_bus="gen_harbor_h", to_bus="sub_harbor_h", capacity_mw=40, closed=False),
                LineState(id="line_ch_1", from_bus="gen_core_h", to_bus="sub_core_h", capacity_mw=38, closed=False),
                LineState(id="line_ch_2", from_bus="sub_core_h", to_bus="sub_medical_h", capacity_mw=20, closed=False),
                LineState(id="line_ch_3", from_bus="sub_core_h", to_bus="sub_water_h", capacity_mw=20, closed=False),
                LineState(id="line_tie_hstorm_1", from_bus="sub_harbor_h", to_bus="sub_core_h", capacity_mw=18, closed=False, damaged=True),
                LineState(id="line_tie_hstorm_2", from_bus="sub_core_h", to_bus="sub_corridor_h", capacity_mw=18, closed=False, damaged=True),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="hospital_harbor_emergency",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_medical_h",
                    demand_mw=15,
                    powered=False,
                    backup_minutes_remaining=17,
                    population_impact=3600,
                ),
                CriticalNodeState(
                    id="telecom_harbor_mesh",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_core_h",
                    demand_mw=6,
                    powered=False,
                    backup_minutes_remaining=14,
                    population_impact=210000,
                ),
                CriticalNodeState(
                    id="water_harbor_main",
                    type=CriticalNodeType.WATER,
                    feeder_bus="sub_water_h",
                    demand_mw=11,
                    powered=False,
                    backup_minutes_remaining=18,
                    population_impact=260000,
                ),
                CriticalNodeState(
                    id="emergency_harbor_ops",
                    type=CriticalNodeType.EMERGENCY,
                    feeder_bus="sub_harbor_h",
                    demand_mw=8,
                    powered=False,
                    backup_minutes_remaining=19,
                    population_impact=110000,
                ),
            ],
            zones=[
                ZoneState(id="zone_harbor_res_h", feeder_bus="sub_harbor_h", priority=ZonePriority.RESIDENTIAL, demand_mw=12),
                ZoneState(id="zone_core_corridor_h", feeder_bus="sub_core_h", priority=ZonePriority.CORRIDOR, demand_mw=9),
                ZoneState(id="zone_corridor_east_h", feeder_bus="sub_corridor_h", priority=ZonePriority.CORRIDOR, demand_mw=8),
                ZoneState(id="zone_industrial_h", feeder_bus="sub_water_h", priority=ZonePriority.INDUSTRIAL, demand_mw=13),
            ],
            hidden_damaged_lines=["line_tie_hstorm_1", "line_tie_hstorm_2"],
            warnings=[
                "Harbor storm damage has left both tie corridors in an unknown state.",
                "Telecom mesh backup is under 15 minutes.",
                "Water pressure reserve is falling across harbor districts.",
            ],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_core_blackstart_h"},
                {"action_type": "close_line", "target_id": "line_ch_1"},
                {"action_type": "energize_substation", "target_id": "sub_core_h"},
                {"action_type": "restore_critical_node", "target_id": "telecom_harbor_mesh"},
                {"action_type": "close_line", "target_id": "line_ch_2"},
                {"action_type": "energize_substation", "target_id": "sub_medical_h"},
                {"action_type": "restore_critical_node", "target_id": "hospital_harbor_emergency"},
                {"action_type": "close_line", "target_id": "line_ch_3"},
                {"action_type": "energize_substation", "target_id": "sub_water_h"},
                {"action_type": "restore_critical_node", "target_id": "water_harbor_main"},
                {"action_type": "start_generator", "target_id": "gen_harbor_blackstart_h"},
                {"action_type": "close_line", "target_id": "line_hh_1"},
                {"action_type": "energize_substation", "target_id": "sub_harbor_h"},
                {"action_type": "restore_critical_node", "target_id": "emergency_harbor_ops"},
                {"action_type": "inspect_line", "target_id": "line_tie_hstorm_1"},
                {"action_type": "sync_islands", "target_id": "line_tie_hstorm_1"},
            ],
            status_keywords=["harbor", "storm", "telecom", "water", "medical"],
            constraints=[
                Constraint(
                    id="c_no_hstorm1_blind",
                    text=(
                        "Do not close line_tie_hstorm_1 without prior inspection — "
                        "harbor storm crews reported structural damage on the harbor-core crossing."
                    ),
                    constraint_type=ConstraintType.FORBIDDEN_TARGET,
                    forbidden_action_type=ActionType.CLOSE_LINE,
                    forbidden_target_id="line_tie_hstorm_1",
                    active=True,
                ),
                Constraint(
                    id="c_harbor_hosp_first",
                    text="Restore harbor emergency hospital before any harbor residential zone — medical triage order.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="hospital_harbor_emergency",
                    before_restoring="zone_harbor_res_h",
                    active=True,
                ),
                Constraint(
                    id="c_harbor_industrial_limit",
                    text=(
                        "Harbor industrial zone must stay below 10 MW until reserve margin exceeds 20 MW. "
                        "Storm-degraded generation cannot safely support full industrial load."
                    ),
                    constraint_type=ConstraintType.CONDITIONAL_LIMIT,
                    limit_target_id="zone_industrial_h",
                    limit_mw=10,
                    condition_field="reserve_margin_mw",
                    condition_threshold=20.0,
                    active=False,  # activated by harbour authority news at step 6
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_hstorm_tie_damage",
                    trigger_step=2,
                    headline="Storm damage confirmed: line_tie_hstorm_1 support tower partially collapsed.",
                    detail=(
                        "Harbor patrol reports partial tower collapse on the harbor-core tie crossing. "
                        "Full structural inspection is mandatory before any reconnection attempt."
                    ),
                    impact_level="warning",
                    public_trust_delta=-0.04,
                ),
                NewsEvent(
                    id="news_hstorm_hospital_critical",
                    trigger_step=4,
                    headline="ALERT: Harbor Emergency Hospital backup systems failing — revised to 10 min.",
                    detail=(
                        "Storm flooding has compromised the hospital emergency backup system. "
                        "Effective backup window is now 10 minutes. Immediate grid restoration required."
                    ),
                    impact_level="critical",
                    reduces_backup_node="hospital_harbor_emergency",
                    reduces_backup_by=7,
                    public_trust_delta=-0.07,
                ),
                NewsEvent(
                    id="news_hstorm_industrial_order",
                    trigger_step=6,
                    headline="Harbor authority: industrial zone load limited to 10 MW until reserve margin recovers.",
                    detail=(
                        "Port authority issues emergency load-limiting directive for harbor industrial zone. "
                        "Full industrial restoration must wait until reserve margin exceeds 20 MW."
                    ),
                    impact_level="warning",
                    activates_constraint_id="c_harbor_industrial_limit",
                    public_trust_delta=-0.05,
                ),
            ],
        ),
    ],
    "mega_cascade": [
        Scenario(
            incident_id="BSC-EXTREME-001",
            title="Mega Cascade — Dual Hospital Crisis",
            task=CityTaskSpec(
                task_id="mega_cascade",
                difficulty=DifficultyLevel.HARD,
                description=(
                    "Two hospitals share one substation feeder. Conflicting city-council orders. "
                    "Battery backup starts at 8 minutes. A school-zone downed line must never be energized."
                ),
                max_steps=35,
            ),
            objective=(
                "Restore Hospital A and Hospital B which both draw from sub_medical_x. "
                "Respect conflicting council orders and never energize line_tie_school. "
                "Prevent a second collapse while industrial load stays below 10 MW until reserve > 20 MW."
            ),
            generators=[
                GeneratorState(id="gen_blackstart_x1", bus="gen_bus_x1", blackstart_capable=True, capacity_mw=50),
                GeneratorState(id="gen_blackstart_x2", bus="gen_bus_x2", blackstart_capable=True, capacity_mw=44),
                GeneratorState(id="battery_x_medical", bus="sub_medical_x", blackstart_capable=False, capacity_mw=14),
                GeneratorState(id="battery_x_south", bus="sub_south_x", blackstart_capable=False, capacity_mw=10),
            ],
            substations=[
                SubstationState(id="gen_bus_x1", energized=False, island_id="north_x"),
                SubstationState(id="gen_bus_x2", energized=False, island_id="south_x"),
                SubstationState(id="sub_north_x", energized=False, island_id="north_x"),
                SubstationState(id="sub_south_x", energized=False, island_id="south_x"),
                SubstationState(id="sub_medical_x", energized=False, island_id="core_x"),
                SubstationState(id="sub_water_x", energized=False, island_id="core_x"),
                SubstationState(id="sub_core_x", energized=False, island_id="core_x"),
                SubstationState(id="sub_school_x", energized=False, island_id="east_x"),
            ],
            lines=[
                LineState(id="line_x1_north", from_bus="gen_bus_x1", to_bus="sub_north_x", capacity_mw=52, closed=False),
                LineState(id="line_x2_south", from_bus="gen_bus_x2", to_bus="sub_south_x", capacity_mw=46, closed=False),
                LineState(id="line_north_core", from_bus="sub_north_x", to_bus="sub_core_x", capacity_mw=30, closed=False),
                LineState(id="line_south_core", from_bus="sub_south_x", to_bus="sub_core_x", capacity_mw=28, closed=False),
                LineState(id="line_core_medical", from_bus="sub_core_x", to_bus="sub_medical_x", capacity_mw=26, closed=False),
                LineState(id="line_core_water", from_bus="sub_core_x", to_bus="sub_water_x", capacity_mw=22, closed=False),
                LineState(id="line_tie_school", from_bus="sub_core_x", to_bus="sub_school_x", capacity_mw=18, closed=False, damaged=True),
                LineState(id="line_tie_backup", from_bus="sub_north_x", to_bus="sub_south_x", capacity_mw=20, closed=False, damaged=True),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="hospital_alpha",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_medical_x",
                    demand_mw=18,
                    powered=False,
                    backup_minutes_remaining=8,
                    population_impact=5200,
                ),
                CriticalNodeState(
                    id="hospital_beta",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_medical_x",
                    demand_mw=15,
                    powered=False,
                    backup_minutes_remaining=10,
                    population_impact=4100,
                ),
                CriticalNodeState(
                    id="telecom_core_x",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_core_x",
                    demand_mw=7,
                    powered=False,
                    backup_minutes_remaining=12,
                    population_impact=310000,
                ),
                CriticalNodeState(
                    id="water_plant_x",
                    type=CriticalNodeType.WATER,
                    feeder_bus="sub_water_x",
                    demand_mw=13,
                    powered=False,
                    backup_minutes_remaining=20,
                    population_impact=410000,
                ),
                CriticalNodeState(
                    id="emergency_x",
                    type=CriticalNodeType.EMERGENCY,
                    feeder_bus="sub_south_x",
                    demand_mw=10,
                    powered=False,
                    backup_minutes_remaining=15,
                    population_impact=160000,
                ),
            ],
            zones=[
                ZoneState(id="zone_north_x_res", feeder_bus="sub_north_x", priority=ZonePriority.RESIDENTIAL, demand_mw=16),
                ZoneState(id="zone_south_x_res", feeder_bus="sub_south_x", priority=ZonePriority.RESIDENTIAL, demand_mw=14),
                ZoneState(id="zone_core_x_corridor", feeder_bus="sub_core_x", priority=ZonePriority.CORRIDOR, demand_mw=11),
                ZoneState(id="zone_industrial_x", feeder_bus="sub_water_x", priority=ZonePriority.INDUSTRIAL, demand_mw=15),
            ],
            hidden_damaged_lines=["line_tie_school", "line_tie_backup"],
            warnings=[
                "Hospital Alpha backup: 8 MINUTES — CRITICAL.",
                "Hospital Beta backup: 10 minutes.",
                "line_tie_school is downed near Eastside School — DO NOT ENERGIZE.",
                "Both hospitals share sub_medical_x — substation must be energized before either can be restored.",
            ],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_blackstart_x1"},
                {"action_type": "close_line", "target_id": "line_x1_north"},
                {"action_type": "energize_substation", "target_id": "sub_north_x"},
                {"action_type": "close_line", "target_id": "line_north_core"},
                {"action_type": "energize_substation", "target_id": "sub_core_x"},
                {"action_type": "close_line", "target_id": "line_core_medical"},
                {"action_type": "energize_substation", "target_id": "sub_medical_x"},
                {"action_type": "restore_critical_node", "target_id": "hospital_alpha"},
                {"action_type": "restore_critical_node", "target_id": "hospital_beta"},
            ],
            status_keywords=["hospital", "dual", "school zone", "industrial limit", "conflict", "cascade"],
            constraints=[
                Constraint(
                    id="c_no_school_line",
                    text=(
                        "Never energize line_tie_school — it is downed near Eastside Elementary School. "
                        "Field safety orders permanently prohibit any action on this line."
                    ),
                    constraint_type=ConstraintType.FORBIDDEN_TARGET,
                    forbidden_action_type=ActionType.CLOSE_LINE,
                    forbidden_target_id="line_tie_school",
                    active=True,
                ),
                Constraint(
                    id="c_industrial_x_limit",
                    text=(
                        "Industrial zone must stay below 10 MW until reserve margin exceeds 20 MW. "
                        "Both generators must be online before industrial load is allowed."
                    ),
                    constraint_type=ConstraintType.CONDITIONAL_LIMIT,
                    limit_target_id="zone_industrial_x",
                    limit_mw=10,
                    condition_field="reserve_margin_mw",
                    condition_threshold=20.0,
                    active=True,
                ),
                Constraint(
                    id="c_hospital_alpha_first",
                    text="Restore Hospital A before any residential zone receives load — council direct order.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="hospital_alpha",
                    before_restoring="zone_north_x_res",
                    active=True,
                ),
                Constraint(
                    id="c_emergency_before_south_res",
                    text="Emergency operations must be restored before south residential zone — activated by council order.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="emergency_x",
                    before_restoring="zone_south_x_res",
                    active=False,  # activated by news at step 5
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_alpha_critical",
                    trigger_step=2,
                    headline="CRITICAL: Hospital Alpha internal backup degraded — now 6 minutes remaining.",
                    detail=(
                        "Hospital Alpha reports auxiliary generator fault. Effective backup is now 6 minutes. "
                        "Immediate grid power restoration is the only option. All other work must pause."
                    ),
                    impact_level="critical",
                    reduces_backup_node="hospital_alpha",
                    reduces_backup_by=2,
                    public_trust_delta=-0.08,
                ),
                NewsEvent(
                    id="news_school_confirmed",
                    trigger_step=3,
                    headline="Safety order confirmed: line_tie_school downed 10m from school playground.",
                    detail=(
                        "Emergency services confirm line_tie_school is lying on the ground 10 metres from "
                        "Eastside Elementary. All energization attempts on this line are prohibited by law."
                    ),
                    impact_level="warning",
                    public_trust_delta=-0.04,
                ),
                NewsEvent(
                    id="news_council_conflict",
                    trigger_step=5,
                    headline="City Council: conflicting order — Emergency Ops must come before south residential.",
                    detail=(
                        "A second council directive conflicts with earlier grid operator guidance. "
                        "Emergency Operations must be restored before any south residential zone load. "
                        "Agent must arbitrate between grid efficiency and council mandate."
                    ),
                    impact_level="warning",
                    activates_constraint_id="c_emergency_before_south_res",
                    public_trust_delta=-0.06,
                ),
                NewsEvent(
                    id="news_beta_urgency",
                    trigger_step=7,
                    headline="Hospital Beta ICU calling for immediate power — life-support systems failing.",
                    detail=(
                        "Hospital Beta ICU reports three ventilators on backup battery only. "
                        "Hospital Beta must be restored immediately — sub_medical_x must be energized first."
                    ),
                    impact_level="critical",
                    reduces_backup_node="hospital_beta",
                    reduces_backup_by=3,
                    public_trust_delta=-0.09,
                ),
            ],
        ),
        Scenario(
            incident_id="BSC-EXTREME-002",
            title="Mega Cascade — Chemical District Crisis",
            task=CityTaskSpec(
                task_id="mega_cascade",
                difficulty=DifficultyLevel.HARD,
                description=(
                    "Chemical district blackout with two hospitals on separate feeders. "
                    "Toxic-spill zone line permanently forbidden. Water plant must come before any residential load."
                ),
                max_steps=35,
            ),
            objective=(
                "Restore Hospital North and Hospital South from independent feeders. "
                "Never energize line_tie_chemical — it runs through an active toxic spill. "
                "Restore the water treatment hub before any residential zone. "
                "Keep industrial chemical load below 8 MW until reserve exceeds 18 MW."
            ),
            generators=[
                GeneratorState(id="gen_blackstart_cn1", bus="gen_bus_cn1", blackstart_capable=True, capacity_mw=48),
                GeneratorState(id="gen_blackstart_cn2", bus="gen_bus_cn2", blackstart_capable=True, capacity_mw=42),
                GeneratorState(id="battery_cn_north", bus="sub_hosp_cn_north", blackstart_capable=False, capacity_mw=12),
                GeneratorState(id="battery_cn_south", bus="sub_hosp_cn_south", blackstart_capable=False, capacity_mw=10),
            ],
            substations=[
                SubstationState(id="gen_bus_cn1", energized=False, island_id="cn_north"),
                SubstationState(id="gen_bus_cn2", energized=False, island_id="cn_south"),
                SubstationState(id="sub_cn_north", energized=False, island_id="cn_north"),
                SubstationState(id="sub_hosp_cn_north", energized=False, island_id="cn_north"),
                SubstationState(id="sub_cn_south", energized=False, island_id="cn_south"),
                SubstationState(id="sub_hosp_cn_south", energized=False, island_id="cn_south"),
                SubstationState(id="sub_water_cn", energized=False, island_id="cn_north"),
                SubstationState(id="sub_chemical", energized=False, island_id="cn_east"),
            ],
            lines=[
                LineState(id="line_cn1_north", from_bus="gen_bus_cn1", to_bus="sub_cn_north", capacity_mw=50, closed=False),
                LineState(id="line_cn2_south", from_bus="gen_bus_cn2", to_bus="sub_cn_south", capacity_mw=44, closed=False),
                LineState(id="line_north_hosp_cn", from_bus="sub_cn_north", to_bus="sub_hosp_cn_north", capacity_mw=28, closed=False),
                LineState(id="line_south_hosp_cn", from_bus="sub_cn_south", to_bus="sub_hosp_cn_south", capacity_mw=24, closed=False),
                LineState(id="line_north_water_cn", from_bus="sub_cn_north", to_bus="sub_water_cn", capacity_mw=22, closed=False),
                LineState(id="line_tie_cn", from_bus="sub_cn_north", to_bus="sub_cn_south", capacity_mw=20, closed=False, damaged=True),
                LineState(id="line_tie_chemical", from_bus="sub_cn_south", to_bus="sub_chemical", capacity_mw=16, closed=False, damaged=True),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="hospital_cn_north",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_hosp_cn_north",
                    demand_mw=16,
                    powered=False,
                    backup_minutes_remaining=14,
                    population_impact=4800,
                ),
                CriticalNodeState(
                    id="hospital_cn_south",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_hosp_cn_south",
                    demand_mw=14,
                    powered=False,
                    backup_minutes_remaining=18,
                    population_impact=3900,
                ),
                CriticalNodeState(
                    id="telecom_cn_core",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_cn_north",
                    demand_mw=6,
                    powered=False,
                    backup_minutes_remaining=16,
                    population_impact=290000,
                ),
                CriticalNodeState(
                    id="water_hub_cn",
                    type=CriticalNodeType.WATER,
                    feeder_bus="sub_water_cn",
                    demand_mw=12,
                    powered=False,
                    backup_minutes_remaining=24,
                    population_impact=380000,
                ),
                CriticalNodeState(
                    id="emergency_cn",
                    type=CriticalNodeType.EMERGENCY,
                    feeder_bus="sub_cn_south",
                    demand_mw=9,
                    powered=False,
                    backup_minutes_remaining=20,
                    population_impact=140000,
                ),
            ],
            zones=[
                ZoneState(id="zone_cn_north_res", feeder_bus="sub_cn_north", priority=ZonePriority.RESIDENTIAL, demand_mw=14),
                ZoneState(id="zone_cn_south_res", feeder_bus="sub_cn_south", priority=ZonePriority.RESIDENTIAL, demand_mw=13),
                ZoneState(id="zone_cn_corridor", feeder_bus="sub_cn_north", priority=ZonePriority.CORRIDOR, demand_mw=10),
                ZoneState(id="zone_chemical_ind", feeder_bus="sub_chemical", priority=ZonePriority.INDUSTRIAL, demand_mw=14),
            ],
            hidden_damaged_lines=["line_tie_cn", "line_tie_chemical"],
            warnings=[
                "Hospital North backup: 14 minutes — restore feeder immediately.",
                "line_tie_chemical runs through active toxic-spill exclusion zone — NEVER energize.",
                "Water hub must come before residential load per emergency health order.",
            ],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_blackstart_cn1"},
                {"action_type": "close_line", "target_id": "line_cn1_north"},
                {"action_type": "energize_substation", "target_id": "sub_cn_north"},
                {"action_type": "close_line", "target_id": "line_north_hosp_cn"},
                {"action_type": "energize_substation", "target_id": "sub_hosp_cn_north"},
                {"action_type": "restore_critical_node", "target_id": "hospital_cn_north"},
                {"action_type": "start_generator", "target_id": "gen_blackstart_cn2"},
                {"action_type": "close_line", "target_id": "line_cn2_south"},
                {"action_type": "energize_substation", "target_id": "sub_cn_south"},
                {"action_type": "close_line", "target_id": "line_south_hosp_cn"},
                {"action_type": "energize_substation", "target_id": "sub_hosp_cn_south"},
                {"action_type": "restore_critical_node", "target_id": "hospital_cn_south"},
                {"action_type": "close_line", "target_id": "line_north_water_cn"},
                {"action_type": "energize_substation", "target_id": "sub_water_cn"},
                {"action_type": "restore_critical_node", "target_id": "water_hub_cn"},
            ],
            status_keywords=["hospital north", "hospital south", "chemical", "water hub", "toxic", "cascade"],
            constraints=[
                Constraint(
                    id="c_no_chemical_line",
                    text=(
                        "Never energize line_tie_chemical — it passes through an active chemical spill zone. "
                        "Emergency services have issued a permanent safety exclusion order."
                    ),
                    constraint_type=ConstraintType.FORBIDDEN_TARGET,
                    forbidden_action_type=ActionType.CLOSE_LINE,
                    forbidden_target_id="line_tie_chemical",
                    active=True,
                ),
                Constraint(
                    id="c_chemical_ind_limit",
                    text=(
                        "Chemical industrial zone must stay below 8 MW until reserve margin exceeds 18 MW. "
                        "High industrial load before stability risks a secondary cascade."
                    ),
                    constraint_type=ConstraintType.CONDITIONAL_LIMIT,
                    limit_target_id="zone_chemical_ind",
                    limit_mw=8,
                    condition_field="reserve_margin_mw",
                    condition_threshold=18.0,
                    active=True,
                ),
                Constraint(
                    id="c_water_before_cn_res",
                    text="Restore water treatment hub before any residential zone — public health emergency order.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="water_hub_cn",
                    before_restoring="zone_cn_north_res",
                    active=True,
                ),
                Constraint(
                    id="c_hosp_north_before_south_res",
                    text="Hospital North must be restored before south residential zone receives any load.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="hospital_cn_north",
                    before_restoring="zone_cn_south_res",
                    active=False,
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_cn_hosp_north_critical",
                    trigger_step=2,
                    headline="CRITICAL: Hospital North backup degraded — now 10 minutes remaining.",
                    detail=(
                        "Hospital North reports auxiliary generator fuel contamination. "
                        "Effective backup is now 10 minutes. Grid power is the only option."
                    ),
                    impact_level="critical",
                    reduces_backup_node="hospital_cn_north",
                    reduces_backup_by=4,
                    public_trust_delta=-0.08,
                ),
                NewsEvent(
                    id="news_cn_chemical_spill",
                    trigger_step=3,
                    headline="Chemical spill confirmed near line_tie_chemical — exclusion zone enforced.",
                    detail=(
                        "Hazmat teams confirm a spill within 20 metres of line_tie_chemical. "
                        "No energization allowed until full decontamination."
                    ),
                    impact_level="warning",
                    public_trust_delta=-0.04,
                ),
                NewsEvent(
                    id="news_cn_water_pressure",
                    trigger_step=5,
                    headline="Water pressure failing across chemical district — fire suppression offline.",
                    detail=(
                        "Water hub must be restored before residential zones to prevent further risk."
                    ),
                    impact_level="critical",
                    public_trust_delta=-0.06,
                ),
                NewsEvent(
                    id="news_cn_council_order",
                    trigger_step=6,
                    headline="City council: Hospital North must be restored before south residential zone.",
                    detail=(
                        "Emergency council directive requires Hospital North as precondition for "
                        "any south residential load. Grid operator must comply."
                    ),
                    impact_level="warning",
                    activates_constraint_id="c_hosp_north_before_south_res",
                    public_trust_delta=-0.05,
                ),
            ],
        ),
        Scenario(
            incident_id="BSC-EXTREME-003",
            title="Mega Cascade — Coastal Storm Flooding",
            task=CityTaskSpec(
                task_id="mega_cascade",
                difficulty=DifficultyLevel.HARD,
                description=(
                    "Coastal storm with three hospitals across two islands. "
                    "Flooded substation crossing permanently forbidden. Tight reserve under storm-degraded generation."
                ),
                max_steps=35,
            ),
            objective=(
                "Restore three hospitals across the coastal and inland islands. "
                "Never energize line_tie_flood — storm surge has submerged the coastal crossing. "
                "Synchronize the inland tie-line only after inspection. "
                "Prevent a second collapse under degraded generation capacity."
            ),
            generators=[
                GeneratorState(id="gen_coastal_blackstart", bus="gen_bus_coastal", blackstart_capable=True, capacity_mw=46),
                GeneratorState(id="gen_inland_blackstart", bus="gen_bus_inland", blackstart_capable=True, capacity_mw=44),
                GeneratorState(id="gen_storm_backup", bus="sub_water_storm", blackstart_capable=True, capacity_mw=30),
                GeneratorState(id="battery_coastal_hosp", bus="sub_hosp_coastal", blackstart_capable=False, capacity_mw=11),
            ],
            substations=[
                SubstationState(id="gen_bus_coastal", energized=False, island_id="coastal"),
                SubstationState(id="gen_bus_inland", energized=False, island_id="inland"),
                SubstationState(id="sub_coastal", energized=False, island_id="coastal"),
                SubstationState(id="sub_hosp_coastal", energized=False, island_id="coastal"),
                SubstationState(id="sub_inland", energized=False, island_id="inland"),
                SubstationState(id="sub_hosp_inland_a", energized=False, island_id="inland"),
                SubstationState(id="sub_hosp_inland_b", energized=False, island_id="inland"),
                SubstationState(id="sub_water_storm", energized=False, island_id="storm"),
                SubstationState(id="sub_flood", energized=False, island_id="coastal"),
            ],
            lines=[
                LineState(id="line_coastal_cs1", from_bus="gen_bus_coastal", to_bus="sub_coastal", capacity_mw=48, closed=False),
                LineState(id="line_inland_cs1", from_bus="gen_bus_inland", to_bus="sub_inland", capacity_mw=46, closed=False),
                LineState(id="line_coastal_hosp_cs", from_bus="sub_coastal", to_bus="sub_hosp_coastal", capacity_mw=24, closed=False),
                LineState(id="line_inland_hosp_a_cs", from_bus="sub_inland", to_bus="sub_hosp_inland_a", capacity_mw=22, closed=False),
                LineState(id="line_inland_hosp_b_cs", from_bus="sub_inland", to_bus="sub_hosp_inland_b", capacity_mw=20, closed=False),
                LineState(id="line_tie_storm", from_bus="sub_inland", to_bus="sub_water_storm", capacity_mw=18, closed=False, damaged=True),
                LineState(id="line_tie_flood", from_bus="sub_coastal", to_bus="sub_flood", capacity_mw=16, closed=False, damaged=True),
            ],
            critical_nodes=[
                CriticalNodeState(
                    id="hospital_coastal_cs",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_hosp_coastal",
                    demand_mw=15,
                    powered=False,
                    backup_minutes_remaining=12,
                    population_impact=4400,
                ),
                CriticalNodeState(
                    id="hospital_inland_a",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_hosp_inland_a",
                    demand_mw=14,
                    powered=False,
                    backup_minutes_remaining=20,
                    population_impact=3700,
                ),
                CriticalNodeState(
                    id="hospital_inland_b",
                    type=CriticalNodeType.HOSPITAL,
                    feeder_bus="sub_hosp_inland_b",
                    demand_mw=13,
                    powered=False,
                    backup_minutes_remaining=24,
                    population_impact=3200,
                ),
                CriticalNodeState(
                    id="telecom_storm_cs",
                    type=CriticalNodeType.TELECOM,
                    feeder_bus="sub_water_storm",
                    demand_mw=7,
                    powered=False,
                    backup_minutes_remaining=15,
                    population_impact=270000,
                ),
                CriticalNodeState(
                    id="water_storm_plant",
                    type=CriticalNodeType.WATER,
                    feeder_bus="sub_water_storm",
                    demand_mw=11,
                    powered=False,
                    backup_minutes_remaining=22,
                    population_impact=350000,
                ),
            ],
            zones=[
                ZoneState(id="zone_coastal_res_cs", feeder_bus="sub_coastal", priority=ZonePriority.RESIDENTIAL, demand_mw=13),
                ZoneState(id="zone_inland_corridor_cs", feeder_bus="sub_inland", priority=ZonePriority.CORRIDOR, demand_mw=10),
                ZoneState(id="zone_storm_res_cs", feeder_bus="sub_water_storm", priority=ZonePriority.RESIDENTIAL, demand_mw=11),
                ZoneState(id="zone_coastal_ind_cs", feeder_bus="sub_coastal", priority=ZonePriority.INDUSTRIAL, demand_mw=12),
            ],
            hidden_damaged_lines=["line_tie_storm", "line_tie_flood"],
            warnings=[
                "Hospital Coastal backup: 12 MINUTES — CRITICAL. Restore immediately.",
                "line_tie_flood submerged by storm surge — DO NOT ENERGIZE under any circumstances.",
                "Two inland hospitals share sub_inland feeder — energize before both can be restored.",
            ],
            solution_actions=[
                {"action_type": "start_generator", "target_id": "gen_coastal_blackstart"},
                {"action_type": "close_line", "target_id": "line_coastal_cs1"},
                {"action_type": "energize_substation", "target_id": "sub_coastal"},
                {"action_type": "close_line", "target_id": "line_coastal_hosp_cs"},
                {"action_type": "energize_substation", "target_id": "sub_hosp_coastal"},
                {"action_type": "restore_critical_node", "target_id": "hospital_coastal_cs"},
                {"action_type": "start_generator", "target_id": "gen_inland_blackstart"},
                {"action_type": "close_line", "target_id": "line_inland_cs1"},
                {"action_type": "energize_substation", "target_id": "sub_inland"},
                {"action_type": "close_line", "target_id": "line_inland_hosp_a_cs"},
                {"action_type": "energize_substation", "target_id": "sub_hosp_inland_a"},
                {"action_type": "restore_critical_node", "target_id": "hospital_inland_a"},
                {"action_type": "close_line", "target_id": "line_inland_hosp_b_cs"},
                {"action_type": "energize_substation", "target_id": "sub_hosp_inland_b"},
                {"action_type": "restore_critical_node", "target_id": "hospital_inland_b"},
                {"action_type": "inspect_line", "target_id": "line_tie_storm"},
                {"action_type": "sync_islands", "target_id": "line_tie_storm"},
            ],
            status_keywords=["coastal hospital", "inland", "flood", "storm", "water plant", "cascade"],
            constraints=[
                Constraint(
                    id="c_no_flood_line",
                    text=(
                        "Never energize line_tie_flood — storm surge has submerged this coastal crossing. "
                        "Coast Guard prohibits all electrical activity on this line."
                    ),
                    constraint_type=ConstraintType.FORBIDDEN_TARGET,
                    forbidden_action_type=ActionType.CLOSE_LINE,
                    forbidden_target_id="line_tie_flood",
                    active=True,
                ),
                Constraint(
                    id="c_coastal_hospital_first",
                    text="Restore Coastal Hospital before any coastal residential zone — life-critical triage.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="hospital_coastal_cs",
                    before_restoring="zone_coastal_res_cs",
                    active=True,
                ),
                Constraint(
                    id="c_storm_industrial_limit",
                    text=(
                        "Coastal industrial zone must stay below 10 MW until reserve margin exceeds 20 MW. "
                        "Storm-degraded generation cannot support full industrial load safely."
                    ),
                    constraint_type=ConstraintType.CONDITIONAL_LIMIT,
                    limit_target_id="zone_coastal_ind_cs",
                    limit_mw=10,
                    condition_field="reserve_margin_mw",
                    condition_threshold=20.0,
                    active=True,
                ),
                Constraint(
                    id="c_inland_hospitals_before_storm_res",
                    text="Both inland hospitals must be restored before storm residential zone receives load.",
                    constraint_type=ConstraintType.PRIORITY_ORDER,
                    must_restore_first="hospital_inland_a",
                    before_restoring="zone_storm_res_cs",
                    active=False,
                ),
            ],
            news_events=[
                NewsEvent(
                    id="news_cs_coastal_critical",
                    trigger_step=2,
                    headline="CRITICAL: Coastal Hospital backup generator flooding — 8 minutes remaining.",
                    detail=(
                        "Storm surge reached the Coastal Hospital generator room. "
                        "Backup is now 8 minutes. Restore coastal feeder immediately — no alternatives."
                    ),
                    impact_level="critical",
                    reduces_backup_node="hospital_coastal_cs",
                    reduces_backup_by=4,
                    public_trust_delta=-0.09,
                ),
                NewsEvent(
                    id="news_cs_flood_confirmed",
                    trigger_step=3,
                    headline="Storm surge confirmed: line_tie_flood is submerged — energization prohibited.",
                    detail=(
                        "Coast Guard confirms line_tie_flood is under 1.5 metres of seawater. "
                        "Any energization attempt will be fatal. Line is permanently out of service."
                    ),
                    impact_level="warning",
                    public_trust_delta=-0.05,
                ),
                NewsEvent(
                    id="news_cs_inland_b_degraded",
                    trigger_step=6,
                    headline="Hospital Inland B backup degraded — now 16 minutes remaining.",
                    detail=(
                        "Storm interference has reduced Hospital Inland B backup output. "
                        "Accelerate inland feeder restoration immediately."
                    ),
                    impact_level="warning",
                    reduces_backup_node="hospital_inland_b",
                    reduces_backup_by=8,
                    public_trust_delta=-0.06,
                ),
                NewsEvent(
                    id="news_cs_inland_hospitals_priority",
                    trigger_step=8,
                    headline="Emergency order: inland hospitals must be restored before storm residential zone.",
                    detail=(
                        "City emergency management requires both inland hospitals fully restored "
                        "before any storm-district residential load is reconnected."
                    ),
                    impact_level="warning",
                    activates_constraint_id="c_inland_hospitals_before_storm_res",
                    public_trust_delta=-0.04,
                ),
            ],
        ),
    ],
}
