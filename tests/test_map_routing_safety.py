from types import SimpleNamespace

import pytest

from analysis_scripts import benchmark_adaptive_route_candidates as benchmark
from spirecomm.ai.agent import SimpleAgent
from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter
from spirecomm.communication.action import ChooseMapNodeAction, RestAction
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.map import Map, Node
from spirecomm.spire.screen import RestOption


def _card(card_id, upgrades=0):
    return SimpleNamespace(card_id=card_id, name=card_id, upgrades=upgrades)


def _context(deck=None, act=1, floor=5, hp_pct=1.0):
    return SimpleNamespace(
        game=SimpleNamespace(deck=deck or [], potions=[], relics=["Burning Blood"]),
        act=act,
        floor=floor,
        player_hp_pct=hp_pct,
        deck_archetype="unknown",
        archetype_score=0.0,
    )


def test_conservative_act2_route_prefers_safe_event_over_elite_when_healthy():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(act=2, floor=19, hp_pct=0.9)

    elite_priority = router.calculate_node_priority(SimpleNamespace(symbol="E"), context)
    event_priority = router.calculate_node_priority(SimpleNamespace(symbol="?"), context)

    assert elite_priority < event_priority


def test_conservative_act1_elite_penalty_blocks_future_reward_bait():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(act=1, floor=6, hp_pct=1.0)

    elite_priority = router.calculate_node_priority(SimpleNamespace(symbol="E"), context)

    assert elite_priority <= -1000


def test_conservative_act1_underprepared_deck_prefers_monster_over_early_event():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(
        act=1,
        floor=4,
        hp_pct=0.9,
        deck=[
            _card("Strike_R"),
            _card("Strike_R"),
            _card("Strike_R"),
            _card("Strike_R"),
            _card("Defend_R"),
            _card("Defend_R"),
            _card("Defend_R"),
            _card("Defend_R"),
            _card("Bash"),
        ],
    )

    monster_priority = router.calculate_node_priority(SimpleNamespace(symbol="M"), context)
    event_priority = router.calculate_node_priority(SimpleNamespace(symbol="?"), context)

    assert monster_priority > event_priority


def test_conservative_act1_underprepared_low_gold_deck_prefers_monster_over_early_shop():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(
        act=1,
        floor=3,
        hp_pct=0.9,
        deck=[
            _card("Strike_R"),
            _card("Strike_R"),
            _card("Strike_R"),
            _card("Strike_R"),
            _card("Defend_R"),
            _card("Defend_R"),
            _card("Defend_R"),
            _card("Defend_R"),
            _card("Bash"),
        ],
    )
    context.game.gold = 99

    monster_priority = router.calculate_node_priority(SimpleNamespace(symbol="M"), context)
    shop_priority = router.calculate_node_priority(SimpleNamespace(symbol="$"), context)

    assert monster_priority > shop_priority


def test_conservative_act2_elite_penalty_blocks_future_reward_bait():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(act=2, floor=22, hp_pct=1.0)

    elite_priority = router.calculate_node_priority(SimpleNamespace(symbol="E"), context)

    assert elite_priority <= -1000


def test_map_router_node_priority_accepts_string_hp_pct():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="aggressive")
    enum_context = _context(act=2, floor=22, hp_pct=0.9)
    string_context = _context(act=2, floor=22, hp_pct="0.9")

    enum_priority = router.calculate_node_priority(SimpleNamespace(symbol="E"), enum_context)
    string_priority = router.calculate_node_priority(SimpleNamespace(symbol="E"), string_context)

    assert string_priority == enum_priority


def test_map_router_node_priority_accepts_string_act_and_floor():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    enum_context = _context(act=1, floor=6, hp_pct=1.0)
    string_context = _context(act="1", floor="6", hp_pct=1.0)

    enum_priority = router.calculate_node_priority(SimpleNamespace(symbol="E"), enum_context)
    try:
        string_priority = router.calculate_node_priority(SimpleNamespace(symbol="E"), string_context)
    except TypeError:
        string_priority = "type-error"

    assert string_priority == enum_priority


def test_map_router_pre_boss_high_hp_allows_high_value_smith():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(
        floor=15,
        hp_pct=0.9,
        deck=[
            _card("Bash"),
            _card("Shockwave"),
            _card("Pommel Strike"),
            _card("Shrug It Off"),
            _card("Battle Trance"),
            _card("Headbutt"),
            _card("Inflame"),
            _card("Anger"),
        ],
    )

    option = router.choose_campfire_option(
        [RestOption.REST, RestOption.SMITH],
        context,
    )

    assert option == RestOption.SMITH


def test_map_router_campfire_accepts_string_hp_pct():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(
        floor=15,
        hp_pct="0.9",
        deck=[
            _card("Bash"),
            _card("Shockwave"),
            _card("Pommel Strike"),
            _card("Shrug It Off"),
            _card("Battle Trance"),
            _card("Headbutt"),
            _card("Inflame"),
            _card("Anger"),
        ],
    )

    option = router.choose_campfire_option(
        [RestOption.REST, RestOption.SMITH],
        context,
    )

    assert option == RestOption.SMITH


def test_map_router_campfire_accepts_string_floor_for_pre_boss_rest():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    enum_context = _context(floor=15, hp_pct=0.74, deck=[_card("Bash")])
    string_context = _context(floor="15", hp_pct=0.74, deck=[_card("Bash")])

    enum_option = router.choose_campfire_option(
        [RestOption.REST, RestOption.SMITH],
        enum_context,
    )
    try:
        string_option = router.choose_campfire_option(
            [RestOption.REST, RestOption.SMITH],
            string_context,
        )
    except TypeError:
        string_option = "type-error"

    assert string_option == enum_option


def test_map_router_pre_boss_moderate_hp_still_forces_rest():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(
        floor=15,
        hp_pct=0.74,
        deck=[
            _card("Bash"),
            _card("Shockwave"),
            _card("Pommel Strike"),
            _card("Shrug It Off"),
            _card("Battle Trance"),
            _card("Headbutt"),
            _card("Inflame"),
            _card("Anger"),
        ],
    )

    option = router.choose_campfire_option(
        [RestOption.REST, RestOption.SMITH],
        context,
    )

    assert option == RestOption.REST


def test_map_router_early_act1_low_margin_campfire_forces_rest():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(
        floor=6,
        hp_pct=41 / 80,
        deck=[
            _card("Pommel Strike"),
            _card("Whirlwind"),
            _card("Disarm"),
            _card("Bash"),
        ],
    )

    option = router.choose_campfire_option(
        [RestOption.REST, RestOption.SMITH],
        context,
    )

    assert option == RestOption.REST


def test_simple_agent_early_act1_low_margin_campfire_rests():
    agent = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode="conservative")
    agent.game.current_hp = 41
    agent.game.max_hp = 80
    agent.game.floor = 6
    agent.game.act = 1
    agent.game.deck = [
        _card("Pommel Strike"),
        _card("Whirlwind"),
        _card("Disarm"),
        _card("Bash"),
    ]
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = []
    agent.game.relics = ["Burning Blood"]
    agent.game.screen = SimpleNamespace(
        rest_options=[RestOption.REST, RestOption.SMITH],
        has_rested=False,
    )

    action = agent.choose_rest_option()

    assert isinstance(action, RestAction)
    assert action.name == RestOption.REST.name


def test_act1_elite_readiness_accepts_string_floor():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="aggressive")
    enum_context = _context(floor=9, hp_pct=0.9)
    string_context = _context(floor="9", hp_pct=0.9)

    try:
        string_readiness = router._act_1_elite_readiness_score(string_context)
    except TypeError:
        string_readiness = "type-error"

    assert string_readiness == router._act_1_elite_readiness_score(enum_context)


def test_map_router_counts_none_upgrades_as_upgradeable():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(deck=[_card("Pommel Strike", upgrades=None)])

    assert router._count_upgradeable_cards(context) == 1


def test_replanned_map_route_starts_from_current_node():
    agent = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode="conservative")
    game_map = Map()

    start = Node(0, 0, "M")
    unrelated_start = Node(5, 0, "?")
    current = Node(0, 1, "M")
    unrelated = Node(5, 1, "?")
    monster_child = Node(0, 2, "M")
    rest_child = Node(1, 2, "R")
    unreachable_shop = Node(5, 2, "$")

    start.children = [current]
    unrelated_start.children = [unrelated]
    current.children = [monster_child, rest_child]
    unrelated.children = [unreachable_shop]

    for node in [
        start,
        unrelated_start,
        current,
        unrelated,
        monster_child,
        rest_child,
        unreachable_shop,
    ]:
        game_map.add_node(node)

    agent.game.map = game_map
    agent.game.act = 3
    agent.game.floor = 42
    agent.game.current_hp = 16
    agent.game.max_hp = 80
    agent.game.deck = []
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = []
    agent.game.relics = []
    agent.game.screen = SimpleNamespace(
        current_node=current,
        next_nodes=[monster_child, rest_child],
        boss_available=False,
    )

    action = agent.make_map_choice()

    assert isinstance(action, ChooseMapNodeAction)
    assert action.node == rest_child


def test_initial_map_route_still_considers_all_starting_nodes():
    agent = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode="conservative")
    game_map = Map()

    weak_start = Node(0, 0, "M")
    safe_start = Node(5, 0, "?")
    weak_child = Node(0, 1, "M")
    safe_child = Node(5, 1, "R")

    weak_start.children = [weak_child]
    safe_start.children = [safe_child]

    for node in [weak_start, safe_start, weak_child, safe_child]:
        game_map.add_node(node)

    agent.game.map = game_map
    agent.game.act = 3
    agent.game.floor = 34
    agent.game.current_hp = 16
    agent.game.max_hp = 80
    agent.game.deck = []
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = []
    agent.game.relics = []
    agent.game.screen = SimpleNamespace(
        current_node=weak_start,
        next_nodes=[weak_start, safe_start],
        boss_available=False,
    )

    action = agent.make_map_choice()

    assert isinstance(action, ChooseMapNodeAction)
    assert action.node == safe_start


def test_conservative_route_prefers_complete_zero_elite_path_over_reward_bait():
    agent = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode="conservative")
    game_map = Map()

    safe_start = Node(0, 0, "M")
    elite_start = Node(1, 0, "M")
    safe_mid = Node(0, 1, "M")
    elite_mid = Node(1, 1, "E")
    safe_end = Node(0, 2, "M")
    elite_reward = Node(1, 2, "T")

    safe_start.children = [safe_mid]
    elite_start.children = [elite_mid]
    safe_mid.children = [safe_end]
    elite_mid.children = [elite_reward]

    for node in [
        safe_start,
        elite_start,
        safe_mid,
        elite_mid,
        safe_end,
        elite_reward,
    ]:
        game_map.add_node(node)

    agent.game.map = game_map
    agent.game.act = 1
    agent.game.floor = 0
    agent.game.current_hp = 80
    agent.game.max_hp = 80
    agent.game.deck = []
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = []
    agent.game.relics = []
    agent.game.screen = SimpleNamespace(
        current_node=safe_start,
        next_nodes=[safe_start, elite_start],
        boss_available=False,
    )

    def reward_bait_priority(node, context):
        return 10000 if node is elite_reward else 0

    agent._calculate_map_node_priority = reward_bait_priority

    action = agent.make_map_choice()

    assert isinstance(action, ChooseMapNodeAction)
    assert action.node == safe_start


def test_conservative_act1_route_prefers_early_fights_over_event_chain_when_underprepared():
    agent = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode="conservative")
    game_map = Map()

    event_start = Node(0, 0, "M")
    event_1 = Node(0, 1, "?")
    event_2 = Node(0, 2, "?")
    event_3 = Node(0, 3, "?")
    event_rest = Node(0, 4, "R")

    fight_start = Node(1, 0, "M")
    fight_1 = Node(1, 1, "M")
    fight_2 = Node(1, 2, "M")
    fight_3 = Node(1, 3, "M")
    fight_rest = Node(1, 4, "R")

    event_start.children = [event_1]
    event_1.children = [event_2]
    event_2.children = [event_3]
    event_3.children = [event_rest]

    fight_start.children = [fight_1]
    fight_1.children = [fight_2]
    fight_2.children = [fight_3]
    fight_3.children = [fight_rest]

    for node in [
        event_start,
        event_1,
        event_2,
        event_3,
        event_rest,
        fight_start,
        fight_1,
        fight_2,
        fight_3,
        fight_rest,
    ]:
        game_map.add_node(node)

    agent.game.map = game_map
    agent.game.act = 1
    agent.game.floor = 0
    agent.game.current_hp = 75
    agent.game.max_hp = 80
    agent.game.deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash"),
    ]
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = []
    agent.game.relics = ["Burning Blood"]
    agent.game.screen = SimpleNamespace(
        current_node=event_start,
        next_nodes=[event_start, fight_start],
        boss_available=False,
    )

    def event_bait_priority(node, context):
        return 100 if node.symbol == "?" else 0

    agent._calculate_map_node_priority = event_bait_priority

    action = agent.make_map_choice()

    assert isinstance(action, ChooseMapNodeAction)
    assert action.node == fight_start


def test_conservative_act1_route_seeks_relief_after_early_reward_target():
    agent = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode="conservative")
    game_map = Map()

    overfight_start = Node(0, 0, "M")
    overfight_1 = Node(0, 1, "M")
    overfight_2 = Node(0, 2, "M")
    overfight_3 = Node(0, 3, "M")
    overfight_4 = Node(0, 4, "M")
    overfight_rest = Node(0, 5, "R")

    relief_start = Node(1, 0, "M")
    relief_1 = Node(1, 1, "M")
    relief_2 = Node(1, 2, "M")
    relief_shop = Node(1, 3, "$")
    relief_rest = Node(1, 4, "R")
    relief_followup = Node(1, 5, "M")

    overfight_start.children = [overfight_1]
    overfight_1.children = [overfight_2]
    overfight_2.children = [overfight_3]
    overfight_3.children = [overfight_4]
    overfight_4.children = [overfight_rest]

    relief_start.children = [relief_1]
    relief_1.children = [relief_2]
    relief_2.children = [relief_shop]
    relief_shop.children = [relief_rest]
    relief_rest.children = [relief_followup]

    for node in [
        overfight_start,
        overfight_1,
        overfight_2,
        overfight_3,
        overfight_4,
        overfight_rest,
        relief_start,
        relief_1,
        relief_2,
        relief_shop,
        relief_rest,
        relief_followup,
    ]:
        game_map.add_node(node)

    agent.game.map = game_map
    agent.game.act = 1
    agent.game.floor = 0
    agent.game.current_hp = 80
    agent.game.max_hp = 80
    agent.game.gold = 120
    agent.game.deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash"),
    ]
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = []
    agent.game.relics = ["Burning Blood"]
    agent.game.screen = SimpleNamespace(
        current_node=overfight_start,
        next_nodes=[overfight_start, relief_start],
        boss_available=False,
    )

    action = agent.make_map_choice()

    assert isinstance(action, ChooseMapNodeAction)
    assert action.node == relief_start


def test_conservative_route_delays_forced_act1_elite_until_after_rest():
    agent = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode="conservative")
    game_map = Map()

    early_start = Node(0, 0, "M")
    early_fight_1 = Node(0, 1, "M")
    early_fight_2 = Node(0, 2, "M")
    early_fight_3 = Node(0, 3, "M")
    early_event = Node(0, 4, "?")
    early_elite = Node(0, 5, "E")
    early_after_1 = Node(0, 6, "M")
    early_after_2 = Node(0, 7, "M")

    delayed_start = Node(1, 0, "M")
    delayed_event_1 = Node(1, 1, "?")
    delayed_event_2 = Node(1, 2, "?")
    delayed_event_3 = Node(1, 3, "?")
    delayed_rest = Node(1, 4, "R")
    delayed_fight_1 = Node(1, 5, "M")
    delayed_fight_2 = Node(1, 6, "M")
    delayed_elite = Node(1, 7, "E")

    early_start.children = [early_fight_1]
    early_fight_1.children = [early_fight_2]
    early_fight_2.children = [early_fight_3]
    early_fight_3.children = [early_event]
    early_event.children = [early_elite]
    early_elite.children = [early_after_1]
    early_after_1.children = [early_after_2]

    delayed_start.children = [delayed_event_1]
    delayed_event_1.children = [delayed_event_2]
    delayed_event_2.children = [delayed_event_3]
    delayed_event_3.children = [delayed_rest]
    delayed_rest.children = [delayed_fight_1]
    delayed_fight_1.children = [delayed_fight_2]
    delayed_fight_2.children = [delayed_elite]

    for node in [
        early_start,
        early_fight_1,
        early_fight_2,
        early_fight_3,
        early_event,
        early_elite,
        early_after_1,
        early_after_2,
        delayed_start,
        delayed_event_1,
        delayed_event_2,
        delayed_event_3,
        delayed_rest,
        delayed_fight_1,
        delayed_fight_2,
        delayed_elite,
    ]:
        game_map.add_node(node)

    agent.game.map = game_map
    agent.game.act = 1
    agent.game.floor = 0
    agent.game.current_hp = 80
    agent.game.max_hp = 80
    agent.game.deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash"),
    ]
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = []
    agent.game.relics = ["Burning Blood"]
    agent.game.screen = SimpleNamespace(
        current_node=early_start,
        next_nodes=[early_start, delayed_start],
        boss_available=False,
    )

    action = agent.make_map_choice()

    assert isinstance(action, ChooseMapNodeAction)
    assert action.node == delayed_start


def _route_agent(elite_mode, game_map, *, hp=80, max_hp=80, floor=0, deck=None):
    agent = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode=elite_mode)
    agent.game.map = game_map
    agent.game.act = 1
    agent.game.floor = floor
    agent.game.current_hp = hp
    agent.game.max_hp = max_hp
    agent.game.deck = list(deck or [])
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = []
    agent.game.relics = ["Burning Blood"]
    return agent


def _set_start_screen(agent, *next_nodes):
    agent.game.screen = SimpleNamespace(
        current_node=Node(-1, -1, "M"),
        next_nodes=list(next_nodes),
        boss_available=False,
    )


def _prepared_act1_deck():
    return [
        _card("Bash", upgrades=1),
        _card("Pommel Strike"),
        _card("Headbutt"),
        _card("Anger"),
        _card("Shrug It Off"),
        _card("Iron Wave"),
    ]


def _add_nodes(game_map, *nodes):
    for node in nodes:
        game_map.add_node(node)


def _optional_elite_route_map():
    game_map = Map.from_json(benchmark.legacy_route_fixture("optional_elite")["nodes"])
    return game_map, game_map.get_node(0, 0), game_map.get_node(1, 0)


def _forced_elite_route_map(elite_count):
    case_name = "forced_one_elite" if elite_count == 1 else "forced_two_elite"
    game_map = Map.from_json(benchmark.legacy_route_fixture(case_name)["nodes"])
    return game_map, game_map.get_node(0, 0), game_map.get_node(1, 0)


def test_legacy_modes_lock_optional_elite_choice_on_identical_map():
    game_map, safe_start, elite_start = _optional_elite_route_map()
    conservative = _route_agent("conservative", game_map)
    aggressive = _route_agent("aggressive", game_map, deck=_prepared_act1_deck())
    _set_start_screen(conservative, safe_start, elite_start)
    _set_start_screen(aggressive, safe_start, elite_start)

    assert conservative.make_map_choice().node == safe_start
    assert aggressive.make_map_choice().node == elite_start


def test_legacy_node_priorities_remain_mode_specific():
    context = _context(deck=_prepared_act1_deck(), act=1, floor=8, hp_pct=1.0)
    elite = SimpleNamespace(symbol="E")

    conservative = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    aggressive = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="aggressive")

    assert conservative.calculate_node_priority(elite, context) == -4960
    assert aggressive.calculate_node_priority(elite, context) == 700


def test_legacy_conservative_tie_delays_first_forced_elite():
    game_map, early_start, delayed_start = _forced_elite_route_map(1)
    agent = _route_agent("conservative", game_map, deck=_prepared_act1_deck())
    _set_start_screen(agent, early_start, delayed_start)

    assert agent.make_map_choice().node == delayed_start


def test_legacy_modes_preserve_forced_single_elite_path():
    game_map, early_start, delayed_start = _forced_elite_route_map(1)
    conservative = _route_agent("conservative", game_map, deck=_prepared_act1_deck())
    aggressive = _route_agent("aggressive", game_map, deck=_prepared_act1_deck())
    _set_start_screen(conservative, early_start, delayed_start)
    _set_start_screen(aggressive, early_start, delayed_start)

    assert conservative.make_map_choice().node == delayed_start
    assert aggressive.make_map_choice().node == early_start


def test_legacy_modes_preserve_forced_two_elite_path():
    game_map, early_start, delayed_start = _forced_elite_route_map(2)
    conservative = _route_agent("conservative", game_map, deck=_prepared_act1_deck())
    aggressive = _route_agent("aggressive", game_map, deck=_prepared_act1_deck())
    _set_start_screen(conservative, early_start, delayed_start)
    _set_start_screen(aggressive, early_start, delayed_start)

    assert conservative.make_map_choice().node == delayed_start
    assert aggressive.make_map_choice().node == early_start


@pytest.mark.parametrize("elite_mode", ("conservative", "aggressive"))
def test_legacy_modes_only_replan_after_configured_hp_drop(monkeypatch, elite_mode):
    game_map = Map.from_json(benchmark.legacy_route_fixture("hp_drop_replan")["nodes"])
    current = game_map.get_node(0, 1)
    next_node = game_map.get_node(0, 2)
    agent = _route_agent(elite_mode, game_map, hp=80, max_hp=80)
    agent.map_route = [0, 0, 0]
    agent._last_route_hp_pct = 1.0
    agent.game.screen = SimpleNamespace(
        current_node=current,
        next_nodes=[next_node],
        boss_available=False,
    )
    calls = []
    monkeypatch.setattr(agent, "generate_map_route", lambda: calls.append(True))

    agent.game.current_hp = 73
    assert agent.make_map_choice().node == next_node
    assert calls == []

    agent.game.current_hp = 71
    assert agent.make_map_choice().node == next_node
    assert calls == [True]
