from dataclasses import FrozenInstanceError, replace
import logging
from types import SimpleNamespace

import pytest

from analysis_scripts import benchmark_adaptive_route_candidates as benchmark
import spirecomm.ai.agent as agent_module
from spirecomm.ai.agent import SimpleAgent
from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter, RouteCandidateFeatures
from spirecomm.communication.action import ChooseMapBossAction, ChooseMapNodeAction, RestAction
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.map import Map, Node
from spirecomm.spire.screen import RestOption


def _card(card_id, upgrades=0):
    return SimpleNamespace(card_id=card_id, name=card_id, upgrades=upgrades)


def _context(deck=None, act=1, floor=5, hp_pct=1.0):
    current_hp = int(80 * float(hp_pct))
    return SimpleNamespace(
        game=SimpleNamespace(
            deck=deck or [],
            potions=[],
            relics=["Burning Blood"],
            current_hp=current_hp,
            max_hp=80,
        ),
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


def _potion(name, *, potion_id=None, can_use=True):
    return SimpleNamespace(
        potion_id=potion_id or name,
        name=name,
        can_use=can_use,
    )


def _adaptive_state(router, *, act=1, current_hp=80, max_hp=80, deck=None,
                    potions=None, relics=None, elite_seen=False, last_rest_floor=None):
    context = _context(
        deck=_prepared_act1_deck() if deck is None else deck,
        act=act,
        hp_pct=current_hp / max_hp if max_hp else 0.0,
    )
    context.game.current_hp = current_hp
    context.game.max_hp = max_hp
    context.game.potions = list(potions if potions is not None else [_potion("Fire Potion")])
    context.game.relics = list(relics if relics is not None else ["Burning Blood"])
    return router.build_adaptive_state(
        context,
        elite_seen=elite_seen,
        last_rest_floor=last_rest_floor,
    )


def _adaptive_candidates(router, *, elite_symbols=None, start_y=0):
    aggressive_symbols = elite_symbols or ("M", "M", "M", "M", "M", "E", "R")
    default_safe_symbols = ("M", "M", "R", "M", "M", "M", "M")
    safe_symbols = (
        default_safe_symbols
        if len(aggressive_symbols) == len(default_safe_symbols)
        else ("M",) * len(aggressive_symbols)
    )
    safe = router.describe_candidate(
        "conservative",
        (0,) * len(safe_symbols),
        safe_symbols,
        start_y=start_y,
    )
    aggressive = router.describe_candidate(
        "aggressive",
        (1,) * len(aggressive_symbols),
        aggressive_symbols,
        start_y=start_y,
    )
    return safe, aggressive


def test_adaptive_deck_readiness_excludes_hp_potions_relics_and_floor():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    context = _context(
        deck=_prepared_act1_deck() + [_card("Flame Barrier")],
        floor=12,
        hp_pct=0.95,
    )
    context.game.potions = [_potion("Fire Potion")]
    context.game.relics = ["Burning Blood", "Preserved Insect"]

    assert router.adaptive_deck_readiness(context) == 7


def test_adaptive_potion_support_counts_only_usable_real_combat_potions_and_caps_at_two():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    context = _context()
    context.game.potions = [
        _potion("Potion Slot"),
        _potion("Fire Potion", can_use=False),
        _potion("Attack Potion"),
        _potion("Entropic Brew"),
        _potion("Questionable Potion"),
    ]

    assert router.adaptive_potion_support(context) == 2


def test_adaptive_relic_support_is_allowlisted_and_capped():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")

    assert router.adaptive_relic_support(["Burning Blood", "Preserved Insect", "Vajra"]) == 2
    assert router.adaptive_relic_support(["Burning Blood", "Question Card"]) == 0


def test_adaptive_state_and_candidate_features_are_frozen():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    state = _adaptive_state(router)
    candidate, _ = _adaptive_candidates(router)

    with pytest.raises(FrozenInstanceError):
        state.deck_readiness = 0
    with pytest.raises(FrozenInstanceError):
        candidate.mode = "aggressive"


def test_describe_candidate_is_deterministic_and_uses_only_provided_path_symbols():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    path = (3, 3, 3, 3, 3, 3, 3)
    symbols = ("M", "R", "M", "M", "M", "E", "R")

    first = router.describe_candidate("aggressive", path, symbols)
    second = router.describe_candidate("aggressive", path, symbols)

    assert first == second
    assert first.path == path
    assert first.symbols == symbols
    assert first.elite_floors == (6,)
    assert first.first_elite_index == 5
    assert first.rest_before_distance == 4
    assert first.rest_after_distance == 1


def test_adaptive_assessment_allows_only_prepared_zero_vs_one_candidate():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    prepared_state = _adaptive_state(router)
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)

    assessment = router.assess_optional_elite(
        prepared_state,
        safe_candidate,
        one_elite_candidate,
    )

    assert assessment.optional_elite_budget == 1
    assert assessment.allowed is True
    assert assessment.reasons == ("optional_elite_allowed",)


def test_adaptive_assessment_denies_low_absolute_hp_before_other_gates():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)

    assessment = router.assess_optional_elite(
        _adaptive_state(router, current_hp=47),
        safe_candidate,
        one_elite_candidate,
    )

    assert assessment.reasons == ("hp_below_absolute_floor",)


def test_adaptive_assessment_denies_low_relative_hp_after_absolute_gate():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)

    assessment = router.assess_optional_elite(
        _adaptive_state(router, current_hp=60, max_hp=81),
        safe_candidate,
        one_elite_candidate,
    )

    assert assessment.reasons == ("hp_below_relative_floor",)


def test_adaptive_assessment_denies_insufficient_deck_before_resource_support():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)

    assessment = router.assess_optional_elite(
        _adaptive_state(router, deck=[]),
        safe_candidate,
        one_elite_candidate,
    )

    assert assessment.reasons == ("deck_not_ready",)


def test_adaptive_assessment_allows_exceptional_deck_without_potion():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)

    ordinary_assessment = router.assess_optional_elite(
        _adaptive_state(router, potions=[]),
        safe_candidate,
        one_elite_candidate,
    )

    assessment = router.assess_optional_elite(
        _adaptive_state(
            router,
            deck=_prepared_act1_deck() + [_card("Flame Barrier")],
            potions=[],
        ),
        safe_candidate,
        one_elite_candidate,
    )

    assert ordinary_assessment.reasons == ("resource_support_missing",)
    assert assessment.reasons == ("optional_elite_allowed",)


def test_adaptive_assessment_allows_two_point_relic_support_without_potion():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)
    prepared_but_not_exceptional = _prepared_act1_deck()[:-1]

    assessment = router.assess_optional_elite(
        _adaptive_state(
            router,
            deck=prepared_but_not_exceptional,
            potions=[],
            relics=["Burning Blood", "Preserved Insect"],
        ),
        safe_candidate,
        one_elite_candidate,
    )

    assert assessment.reasons == ("optional_elite_allowed",)


def test_adaptive_assessment_uses_local_elite_floor_not_current_floor():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, early_elite_candidate = _adaptive_candidates(
        router,
        elite_symbols=("M", "M", "R", "M", "E", "R", "M"),
    )

    assessment = router.assess_optional_elite(
        _adaptive_state(router),
        safe_candidate,
        early_elite_candidate,
    )

    assert early_elite_candidate.elite_floors == (5,)
    assert assessment.reasons == ("elite_before_local_floor",)


def test_adaptive_assessment_denies_later_act_optional_elite():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)

    unsupported_state = _adaptive_state(
        AdaptiveMapRouter("THE_SILENT", "adaptive"),
    )
    unsupported_assessment = router.assess_optional_elite(
        unsupported_state,
        safe_candidate,
        one_elite_candidate,
    )

    assessment = router.assess_optional_elite(
        _adaptive_state(router, act=2),
        safe_candidate,
        one_elite_candidate,
    )

    assert unsupported_assessment.reasons == ("unsupported_character",)
    assert assessment.reasons == ("later_act_optional_elite",)


def test_adaptive_assessment_fails_closed_for_malformed_state_and_candidate():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    state = _adaptive_state(router, max_hp=0)
    safe_candidate, _ = _adaptive_candidates(router)
    malformed_candidate = router.describe_candidate("aggressive", (1, 1), ("M",))

    assessment = router.assess_optional_elite(state, safe_candidate, malformed_candidate)
    malformed_candidate_assessment = router.assess_optional_elite(
        _adaptive_state(router),
        safe_candidate,
        malformed_candidate,
    )

    assert assessment.allowed is False
    assert assessment.optional_elite_budget == 0
    assert assessment.reasons == ("malformed_state",)
    assert malformed_candidate_assessment.reasons == ("malformed_state",)


def test_adaptive_assessment_denies_prior_elite_exposure():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)

    assessment = router.assess_optional_elite(
        _adaptive_state(router, elite_seen=True),
        safe_candidate,
        one_elite_candidate,
    )

    assert assessment.reasons == ("elite_already_seen",)


@pytest.mark.parametrize(
    "safe_symbols, aggressive_symbols",
    [
        (("M", "M", "M", "M", "M", "E", "R"), ("M", "M", "M", "M", "M", "E", "R")),
        (("M", "M", "M", "M", "M", "M", "R"), ("M", "M", "M", "M", "M", "E", "E")),
    ],
)
def test_adaptive_assessment_denies_non_zero_vs_one_candidate_counts(
        safe_symbols, aggressive_symbols):
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate = router.describe_candidate("conservative", (0,) * 7, safe_symbols)
    aggressive_candidate = router.describe_candidate("aggressive", (1,) * 7, aggressive_symbols)

    assessment = router.assess_optional_elite(
        _adaptive_state(router),
        safe_candidate,
        aggressive_candidate,
    )

    assert assessment.reasons == ("candidate_counts_not_zero_vs_one",)


def test_adaptive_assessment_denies_missing_recovery_window():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, no_recovery_candidate = _adaptive_candidates(
        router,
        elite_symbols=("M", "M", "M", "M", "M", "E", "M"),
    )

    assessment = router.assess_optional_elite(
        _adaptive_state(router, deck=_prepared_act1_deck()[:-1]),
        safe_candidate,
        no_recovery_candidate,
    )

    assert assessment.reasons == ("recovery_window_missing",)


def test_adaptive_assessment_allows_90_percent_readiness_7_potion_recovery_exception():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, no_recovery_candidate = _adaptive_candidates(
        router,
        elite_symbols=("M", "M", "M", "M", "M", "E", "M"),
    )

    assessment = router.assess_optional_elite(
        _adaptive_state(
            router,
            current_hp=90,
            max_hp=100,
            deck=_prepared_act1_deck() + [_card("Flame Barrier")],
        ),
        safe_candidate,
        no_recovery_candidate,
    )

    assert assessment.reasons == ("optional_elite_allowed",)


def test_adaptive_candidate_rejects_forged_recovery_and_mutable_fields():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)
    forged_recovery = replace(
        one_elite_candidate,
        symbols=("M", "M", "M", "M", "M", "E", "M"),
        rest_after_distance=1,
    )
    mutable_candidate = RouteCandidateFeatures(
        mode="aggressive",
        path=[1, 1, 1, 1, 1, 1, 1],
        symbols=["M", "M", "M", "M", "M", "E", "R"],
        elite_floors=[6],
        first_elite_index=5,
        rest_before_distance=None,
        rest_after_distance=1,
        start_y=0,
    )

    forged_assessment = router.assess_optional_elite(
        _adaptive_state(router),
        safe_candidate,
        forged_recovery,
    )
    mutable_assessment = router.assess_optional_elite(
        _adaptive_state(router),
        safe_candidate,
        mutable_candidate,
    )

    assert forged_assessment.reasons == ("malformed_state",)
    assert mutable_assessment.reasons == ("malformed_state",)


@pytest.mark.parametrize(
    "candidate_update",
    [
        {"mode": "adaptive"},
        {"path": (1, 1, 1, 1, 1, -1, 1)},
        {"path": (1, 1, 1, 1, 1, 1.0, 1)},
        {"path": (1, 1, 1, 1, 1, True, 1)},
        {"rest_after_distance": 0},
        {"rest_after_distance": -1},
        {"first_elite_index": 4},
    ],
)
def test_adaptive_candidate_rejects_noncanonical_mode_coordinates_and_distances(
        candidate_update):
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)
    malformed_candidate = replace(one_elite_candidate, **candidate_update)

    assessment = router.assess_optional_elite(
        _adaptive_state(router),
        safe_candidate,
        malformed_candidate,
    )

    assert assessment.reasons == ("malformed_state",)


@pytest.mark.parametrize("non_finite_hp_pct", (float("nan"), float("inf"), float("-inf")))
def test_adaptive_state_rejects_non_finite_hp_percentage(non_finite_hp_pct):
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)
    state = replace(_adaptive_state(router), hp_pct=non_finite_hp_pct)

    assessment = router.assess_optional_elite(
        state,
        safe_candidate,
        one_elite_candidate,
    )

    assert assessment.reasons == ("malformed_state",)


@pytest.mark.parametrize(
    "field, value",
    [
        ("act", 1.5),
        ("act", True),
        ("current_hp", 79.5),
        ("current_hp", True),
        ("max_hp", 80.5),
        ("max_hp", True),
        ("last_rest_floor", 5.5),
        ("last_rest_floor", True),
    ],
)
def test_adaptive_state_rejects_fractional_and_boolean_integer_inputs(field, value):
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)
    state_args = {field: value}

    assessment = router.assess_optional_elite(
        _adaptive_state(router, **state_args),
        safe_candidate,
        one_elite_candidate,
    )

    assert assessment.reasons == ("malformed_state",)


def test_describe_candidate_uses_start_y_for_mid_act_local_floor():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")

    candidate = router.describe_candidate(
        "aggressive",
        (3, 3, 3),
        ("M", "E", "R"),
        start_y=7,
    )

    assert candidate.start_y == 7
    assert candidate.elite_floors == (9,)
    assert candidate.rest_after_distance == 1


@pytest.mark.parametrize(
    "last_rest_floor, expected_reason",
    [
        (7, "optional_elite_allowed"),
        (8, "recovery_window_missing"),
        (6, "recovery_window_missing"),
        (9, "recovery_window_missing"),
        (10, "recovery_window_missing"),
        (-1, "malformed_state"),
        (True, "malformed_state"),
        (7.5, "malformed_state"),
    ],
)
def test_adaptive_assessment_uses_only_recent_prior_rest_for_recovery(
        last_rest_floor, expected_reason):
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(
        router,
        elite_symbols=("M", "E", "M"),
        start_y=7,
    )

    assessment = router.assess_optional_elite(
        _adaptive_state(router, last_rest_floor=last_rest_floor),
        safe_candidate,
        one_elite_candidate,
    )

    assert one_elite_candidate.elite_floors == (9,)
    assert assessment.reasons == (expected_reason,)


def test_adaptive_assessment_locks_fail_closed_reason_order_for_combined_failures():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, eligible_candidate = _adaptive_candidates(router)
    _, early_candidate = _adaptive_candidates(
        router,
        elite_symbols=("M", "M", "R", "M", "E", "R", "M"),
    )

    wrong_type = router.assess_optional_elite(object(), safe_candidate, eligible_candidate)
    unsupported = router.assess_optional_elite(
        _adaptive_state(AdaptiveMapRouter("THE_SILENT", "adaptive"), act=2),
        safe_candidate,
        eligible_candidate,
    )
    later_act = router.assess_optional_elite(
        _adaptive_state(router, act=2, current_hp=47, deck=[]),
        safe_candidate,
        eligible_candidate,
    )
    early_floor = router.assess_optional_elite(
        _adaptive_state(router, current_hp=47, deck=[]),
        safe_candidate,
        early_candidate,
    )
    absolute_hp = router.assess_optional_elite(
        _adaptive_state(router, current_hp=47, deck=[]),
        safe_candidate,
        eligible_candidate,
    )
    relative_hp = router.assess_optional_elite(
        _adaptive_state(router, current_hp=60, max_hp=81, deck=[]),
        safe_candidate,
        eligible_candidate,
    )
    deck = router.assess_optional_elite(
        _adaptive_state(router, deck=[], elite_seen=True),
        safe_candidate,
        eligible_candidate,
    )
    resource = router.assess_optional_elite(
        _adaptive_state(router, potions=[], elite_seen=True),
        safe_candidate,
        eligible_candidate,
    )
    seen = router.assess_optional_elite(
        _adaptive_state(router, elite_seen=True),
        safe_candidate,
        eligible_candidate,
    )
    count = router.assess_optional_elite(
        _adaptive_state(router),
        replace(eligible_candidate, mode="conservative"),
        eligible_candidate,
    )

    assert wrong_type.reasons == ("malformed_state",)
    assert unsupported.reasons == ("unsupported_character",)
    assert later_act.reasons == ("later_act_optional_elite",)
    assert early_floor.reasons == ("elite_before_local_floor",)
    assert absolute_hp.reasons == ("hp_below_absolute_floor",)
    assert relative_hp.reasons == ("hp_below_relative_floor",)
    assert deck.reasons == ("deck_not_ready",)
    assert resource.reasons == ("resource_support_missing",)
    assert seen.reasons == ("elite_already_seen",)
    assert count.reasons == ("candidate_counts_not_zero_vs_one",)


def test_adaptive_assessment_rejects_candidate_pair_with_boosted_start_y():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate = router.describe_candidate(
        "conservative",
        (0,) * 7,
        ("M", "M", "M", "M", "M", "M", "M"),
        start_y=0,
    )
    boosted_candidate = router.describe_candidate(
        "aggressive",
        (1,) * 7,
        ("M", "M", "M", "M", "E", "R", "M"),
        start_y=1,
    )

    assessment = router.assess_optional_elite(
        _adaptive_state(router),
        safe_candidate,
        boosted_candidate,
    )

    assert boosted_candidate.elite_floors == (6,)
    assert assessment.reasons == ("malformed_state",)


def test_adaptive_assessment_rejects_swapped_candidate_modes():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate, one_elite_candidate = _adaptive_candidates(router)

    assessment = router.assess_optional_elite(
        _adaptive_state(router),
        replace(safe_candidate, mode="aggressive"),
        replace(one_elite_candidate, mode="conservative"),
    )

    assert assessment.reasons == ("malformed_state",)


def test_adaptive_assessment_rejects_unequal_candidate_extents():
    router = AdaptiveMapRouter("IRONCLAD", "adaptive")
    safe_candidate = router.describe_candidate(
        "conservative",
        (0,) * 6,
        ("M", "M", "M", "M", "M", "M"),
    )
    one_elite_candidate = router.describe_candidate(
        "aggressive",
        (1,) * 7,
        ("M", "M", "M", "M", "M", "E", "R"),
    )

    assessment = router.assess_optional_elite(
        _adaptive_state(router),
        safe_candidate,
        one_elite_candidate,
    )

    assert assessment.reasons == ("malformed_state",)


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


def test_build_map_route_returns_legacy_candidates_without_committing_state():
    game_map, safe_start, elite_start = _optional_elite_route_map()
    agent = _route_agent("adaptive", game_map, deck=_prepared_act1_deck())
    _set_start_screen(agent, safe_start, elite_start)

    conservative = agent._build_map_route("conservative")
    aggressive = agent._build_map_route("aggressive")

    assert sum(game_map.get_node(x, y).symbol == "E" for y, x in enumerate(conservative)) == 0
    assert sum(game_map.get_node(x, y).symbol == "E" for y, x in enumerate(aggressive)) == 1
    assert agent.map_route == []
    assert agent._last_route_hp_pct is None
    assert agent._last_route_floor is None


@pytest.mark.parametrize("elite_mode", ("conservative", "aggressive"))
def test_build_map_route_preserves_exact_legacy_route(elite_mode):
    game_map, safe_start, elite_start = _optional_elite_route_map()
    agent = _route_agent(elite_mode, game_map, deck=_prepared_act1_deck())
    _set_start_screen(agent, safe_start, elite_start)

    expected = agent.generate_map_route()
    rebuilt = agent._build_map_route(elite_mode)

    assert rebuilt == expected


def test_adaptive_selector_chooses_aggressive_only_for_allowed_zero_vs_one():
    agent = _route_agent("adaptive", Map(), deck=_prepared_act1_deck())
    agent.game.potions = [_potion("Fire Potion")]
    conservative, aggressive = _adaptive_candidates(agent.map_router)

    route, assessment = agent._select_adaptive_route(
        conservative,
        aggressive,
        SimpleNamespace(
            game=agent.game,
            act=agent.game.act,
            floor=agent.game.floor,
            player_hp_pct=1.0,
        ),
    )

    assert route == list(aggressive.path)
    assert assessment.allowed is True
    assert assessment.optional_elite_budget == 1
    assert assessment.reasons == ("optional_elite_allowed",)


def test_adaptive_selector_chooses_conservative_for_zero_vs_two():
    agent = _route_agent("adaptive", Map(), deck=_prepared_act1_deck())
    agent.game.potions = [_potion("Fire Potion")]
    conservative = agent.map_router.describe_candidate(
        "conservative", (0,) * 7, ("M",) * 7,
    )
    aggressive = agent.map_router.describe_candidate(
        "aggressive", (1,) * 7, ("M", "M", "M", "M", "M", "E", "E"),
    )

    route, assessment = agent._select_adaptive_route(
        conservative,
        aggressive,
        SimpleNamespace(
            game=agent.game,
            act=agent.game.act,
            floor=agent.game.floor,
            player_hp_pct=1.0,
        ),
    )

    assert route == list(conservative.path)
    assert assessment.allowed is False
    assert assessment.optional_elite_budget == 0
    assert assessment.reasons == ("candidate_counts_not_zero_vs_one",)


@pytest.mark.parametrize("elite_count", (1, 2))
def test_adaptive_selector_keeps_conservative_for_forced_elites(elite_count):
    game_map, early_start, delayed_start = _forced_elite_route_map(elite_count)
    agent = _route_agent("adaptive", game_map, deck=_prepared_act1_deck())
    _set_start_screen(agent, early_start, delayed_start)

    conservative, aggressive = agent._adaptive_route_candidates()
    route, assessment = agent._select_adaptive_route(
        conservative,
        aggressive,
        SimpleNamespace(
            game=agent.game,
            act=agent.game.act,
            floor=agent.game.floor,
            player_hp_pct=1.0,
        ),
    )

    assert conservative.elite_floors == tuple(sorted(conservative.elite_floors))
    assert len(conservative.elite_floors) == elite_count
    assert route == list(conservative.path)
    assert assessment.allowed is False
    assert assessment.optional_elite_budget == 0
    assert assessment.reasons == ("forced_elite_route",)


def test_adaptive_selector_uses_conservative_route_for_unsupported_character():
    game_map, safe_start, elite_start = _optional_elite_route_map()
    agent = SimpleAgent(chosen_class=PlayerClass.THE_SILENT, elite_mode="adaptive")
    agent.game.map = game_map
    agent.game.act = 1
    agent.game.floor = 0
    agent.game.current_hp = 80
    agent.game.max_hp = 80
    agent.game.deck = _prepared_act1_deck()
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = [_potion("Fire Potion")]
    agent.game.relics = ["Burning Blood"]
    _set_start_screen(agent, safe_start, elite_start)

    conservative, aggressive = agent._adaptive_route_candidates()
    route, assessment = agent._select_adaptive_route(
        conservative,
        aggressive,
        SimpleNamespace(
            game=agent.game,
            act=agent.game.act,
            floor=agent.game.floor,
            player_hp_pct=1.0,
        ),
    )

    assert route == list(conservative.path)
    assert assessment.optional_elite_budget == 0
    assert assessment.reasons == ("unsupported_character",)


def test_adaptive_selector_falls_back_when_candidate_generation_fails(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    game_map, safe_start, elite_start = _optional_elite_route_map()
    agent = _route_agent("adaptive", game_map, deck=_prepared_act1_deck())
    _set_start_screen(agent, safe_start, elite_start)
    original_builder = agent._build_map_route
    expected = original_builder("conservative")
    calls = []

    def malformed_aggressive_candidate(mode):
        calls.append(mode)
        if mode == "aggressive":
            return [99] * len(expected)
        return original_builder(mode)

    monkeypatch.setattr(agent, "_build_map_route", malformed_aggressive_candidate)

    route = agent.generate_map_route()

    assert calls == ["conservative", "aggressive", "conservative"]
    assert route == expected
    assert agent.map_route == expected
    assert "candidate_generation_failed" in caplog.text


@pytest.mark.parametrize("current_kind", ("absent", "sentinel"))
@pytest.mark.parametrize("stale_previous_route", (False, True))
def test_adaptive_act_start_fallback_uses_route_index_zero(
        monkeypatch, caplog, current_kind, stale_previous_route):
    caplog.set_level(logging.INFO)
    game_map, safe_start, elite_start = _optional_elite_route_map()
    agent = _route_agent("adaptive", game_map, deck=_prepared_act1_deck())
    agent.game.screen = SimpleNamespace(
        current_node=(
            None if current_kind == "absent" else Node(-1, -1, "M")
        ),
        next_nodes=[safe_start, elite_start],
        boss_available=False,
    )
    original_builder = agent._build_map_route
    expected = original_builder("conservative")
    if stale_previous_route:
        agent.map_route = [6] * len(expected)
    calls = []

    def candidate_failure():
        raise agent_module._AdaptiveRouteCandidateGenerationError("malformed candidate")

    def track_builder(mode):
        calls.append(mode)
        return original_builder(mode)

    monkeypatch.setattr(agent, "_adaptive_route_candidates", candidate_failure)
    monkeypatch.setattr(agent, "_build_map_route", track_builder)

    action = agent.make_map_choice()

    assert calls == ["conservative"]
    assert agent.map_route == expected
    assert isinstance(action, ChooseMapNodeAction)
    assert action.node == next(
        node for node in agent.game.screen.next_nodes if node.x == expected[0]
    )
    assert "candidate_generation_failed" in caplog.text


def test_adaptive_invalid_initial_origin_propagates_without_fallback(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    game_map, safe_start, _ = _optional_elite_route_map()
    agent = _route_agent("adaptive", game_map, deck=_prepared_act1_deck())
    agent.game.screen = SimpleNamespace(
        current_node=None,
        next_nodes=[safe_start.children[0]],
        boss_available=False,
    )
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    calls = []

    monkeypatch.setattr(
        agent,
        "_adaptive_route_candidates",
        lambda: (_ for _ in ()).throw(
            agent_module._AdaptiveRouteCandidateGenerationError("injected")
        ),
    )
    monkeypatch.setattr(
        agent,
        "_build_map_route",
        lambda mode: calls.append(mode),
    )

    with pytest.raises(ValueError, match="initial candidate origin is invalid"):
        agent.generate_map_route()

    assert calls == []
    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


@pytest.mark.parametrize("origin_kind", ("too_negative", "missing_y"))
def test_adaptive_malformed_negative_origin_propagates_before_builder(
        monkeypatch, caplog, origin_kind):
    caplog.set_level(logging.INFO)
    game_map, safe_start, elite_start = _optional_elite_route_map()
    agent = _route_agent("adaptive", game_map, deck=_prepared_act1_deck())
    agent.game.screen = SimpleNamespace(
        current_node=(
            SimpleNamespace(x=-1, y=-2)
            if origin_kind == "too_negative"
            else SimpleNamespace(x=-1)
        ),
        next_nodes=[safe_start, elite_start],
        boss_available=False,
    )
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    original_builder = agent._build_map_route
    calls = []

    def tracked_builder(mode):
        calls.append(mode)
        return original_builder(mode)

    monkeypatch.setattr(agent, "_build_map_route", tracked_builder)

    with pytest.raises(ValueError, match="candidate current node is invalid"):
        agent.make_map_choice()

    assert calls == []
    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


def test_legacy_route_does_not_normalize_absent_current_node():
    game_map, safe_start, _ = _optional_elite_route_map()
    agent = _route_agent("conservative", game_map, deck=_prepared_act1_deck())
    agent.map_route = agent._build_map_route("conservative")
    original_route = list(agent.map_route)
    agent._last_route_hp_pct = 1.0
    agent.game.screen = SimpleNamespace(
        current_node=None,
        next_nodes=[safe_start.children[0]],
        boss_available=False,
    )

    with pytest.raises(AttributeError):
        agent.make_map_choice()

    assert agent.map_route == original_route


def _mid_act_adaptive_route_agent():
    agent = _route_agent("adaptive", Map(), deck=_prepared_act1_deck())
    agent.game.deck.extend(_card("Strike") for _ in range(6))
    game_map = agent.game.map
    prefix = [Node(x, y, "M") for y, x in enumerate((0, 1, 1, 0))]
    current = Node(0, 4, "E")
    safe = Node(0, 5, "M")
    elite = Node(1, 5, "E")
    safe_rest = Node(0, 6, "R")
    elite_rest = Node(1, 6, "R")
    safe_end = Node(0, 7, "T")
    elite_end = Node(1, 7, "T")

    for parent, child in zip(prefix, prefix[1:] + [current]):
        parent.children = [child]
    current.children = [safe, elite]
    safe.children = [safe_rest]
    elite.children = [elite_rest]
    safe_rest.children = [safe_end]
    elite_rest.children = [elite_end]
    for node in prefix + [
            current, safe, elite, safe_rest, elite_rest, safe_end, elite_end]:
        game_map.add_node(node)

    agent.game.potions = [_potion("Fire Potion")]
    agent.game.screen = SimpleNamespace(
        current_node=current,
        next_nodes=[safe, elite],
        boss_available=False,
    )
    agent.map_route = [0, 1, 1, 0, current.x, 0, 0, 0]
    return agent, current, safe, elite


def test_adaptive_mid_act_generation_commits_legal_full_aggressive_route():
    agent, current, safe, elite = _mid_act_adaptive_route_agent()

    conservative, aggressive = agent._adaptive_route_candidates()
    route = agent.generate_map_route()
    action = agent.make_map_choice()

    assert conservative.start_y == current.y + 1
    assert aggressive.start_y == current.y + 1
    assert current.symbol == "E"
    assert conservative.elite_floors == ()
    assert aggressive.elite_floors == (elite.y + 1,)
    assert route[:current.y] == [0, 1, 1, 0]
    assert route[current.y] == current.x
    assert route[current.y + 1] == elite.x
    assert isinstance(action, ChooseMapNodeAction)
    assert action.node == safe
    assert action.node != elite


def test_adaptive_mid_act_fallback_merges_valid_history_with_conservative_suffix(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    agent, current, _, _ = _mid_act_adaptive_route_agent()
    original_builder = agent._build_map_route
    raw_conservative = original_builder("conservative")
    expected = list(raw_conservative)
    expected[:current.y + 1] = agent.map_route[:current.y + 1]
    calls = []

    def candidate_failure():
        raise agent_module._AdaptiveRouteCandidateGenerationError("malformed candidate")

    def track_builder(mode):
        calls.append(mode)
        return original_builder(mode)

    monkeypatch.setattr(agent, "_adaptive_route_candidates", candidate_failure)
    monkeypatch.setattr(agent, "_build_map_route", track_builder)

    route = agent.generate_map_route()

    assert calls == ["conservative"]
    assert route == expected
    assert agent.map_route == expected
    assert route[current.y] == current.x
    assert "candidate_generation_failed" in caplog.text


def test_adaptive_mid_act_fallback_invalid_history_propagates_without_mutation(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    agent, _, _, _ = _mid_act_adaptive_route_agent()
    agent.map_route = agent.map_route[:-1]
    invalid_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    calls = []

    def candidate_failure():
        raise agent_module._AdaptiveRouteCandidateGenerationError("malformed candidate")

    def track_builder(mode):
        calls.append(mode)
        return [0] * 8

    monkeypatch.setattr(agent, "_adaptive_route_candidates", candidate_failure)
    monkeypatch.setattr(agent, "_build_map_route", track_builder)

    with pytest.raises(RuntimeError, match="route history"):
        agent.generate_map_route()

    assert calls == []
    assert agent.map_route == invalid_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


def test_adaptive_mid_act_fallback_invalid_future_propagates_without_mutation(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    agent, _, _, _ = _mid_act_adaptive_route_agent()
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    calls = []

    def candidate_failure():
        raise agent_module._AdaptiveRouteCandidateGenerationError("malformed candidate")

    def truncated_builder(mode):
        calls.append(mode)
        return [0] * (len(original_route) - 1)

    monkeypatch.setattr(agent, "_adaptive_route_candidates", candidate_failure)
    monkeypatch.setattr(agent, "_build_map_route", truncated_builder)

    with pytest.raises(ValueError, match="candidate route is incomplete"):
        agent.generate_map_route()

    assert calls == ["conservative"]
    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


@pytest.mark.parametrize("failure_kind", ("truncated", "disconnected"))
def test_adaptive_candidate_shape_failures_trigger_conservative_fallback(
        monkeypatch, caplog, failure_kind):
    caplog.set_level(logging.INFO)
    agent, current, _, _ = _mid_act_adaptive_route_agent()
    original_builder = agent._build_map_route
    conservative_route = original_builder("conservative")
    expected = list(conservative_route)
    expected[:current.y + 1] = agent.map_route[:current.y + 1]
    calls = []

    def malformed_candidate_builder(mode):
        calls.append(mode)
        route = original_builder(mode)
        if mode != "aggressive":
            return route
        if failure_kind == "truncated":
            return route[:-1]
        route[6] = 0
        return route

    monkeypatch.setattr(agent, "_build_map_route", malformed_candidate_builder)

    route = agent.generate_map_route()

    assert calls == ["conservative", "aggressive", "conservative"]
    assert route == expected
    assert agent.map_route == expected
    assert "candidate_generation_failed" in caplog.text


def test_adaptive_malformed_unreachable_child_uses_one_conservative_fallback(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    agent, current, _, _ = _mid_act_adaptive_route_agent()
    original_builder = agent._build_map_route
    original_route = list(agent.map_route)
    expected = original_builder("conservative")
    expected[:current.y + 1] = original_route[:current.y + 1]
    calls = []
    orphan = Node(5, 0, "M")
    orphan.children = [Node(5, 1, "M")]
    agent.game.map.add_node(orphan)

    def track_builder(mode):
        calls.append(mode)
        return original_builder(mode)

    monkeypatch.setattr(agent, "_build_map_route", track_builder)

    route = agent.generate_map_route()

    assert calls == ["conservative"]
    assert route == expected
    assert agent.map_route == expected
    assert route[:current.y + 1] == original_route[:current.y + 1]
    assert "candidate_generation_failed" in caplog.text


def test_adaptive_active_origin_coordinate_identity_propagates_without_fallback(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    agent, current, _, _ = _mid_act_adaptive_route_agent()
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    original_get_node = agent.game.map.get_node
    malformed = Node(current.x + 7, current.y, current.symbol)
    malformed.children = list(current.children)
    calls = []

    def mismatched_origin(x, y):
        if (x, y) == (current.x, current.y):
            return malformed
        return original_get_node(x, y)

    monkeypatch.setattr(
        agent,
        "_adaptive_route_candidates",
        lambda: (_ for _ in ()).throw(
            agent_module._AdaptiveRouteCandidateGenerationError("injected")
        ),
    )
    monkeypatch.setattr(agent.game.map, "get_node", mismatched_origin)
    monkeypatch.setattr(
        agent,
        "_build_map_route",
        lambda mode: calls.append(mode),
    )

    with pytest.raises(ValueError, match="candidate map node coordinates are invalid"):
        agent.generate_map_route()

    assert calls == []
    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


def test_adaptive_history_coordinate_identity_propagates_without_fallback(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    agent, _, _, _ = _mid_act_adaptive_route_agent()
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    history_node = agent.game.map.get_node(1, 1)
    history_node.x = 7
    calls = []

    monkeypatch.setattr(
        agent,
        "_adaptive_route_candidates",
        lambda: (_ for _ in ()).throw(
            agent_module._AdaptiveRouteCandidateGenerationError("injected")
        ),
    )
    monkeypatch.setattr(
        agent,
        "_validate_adaptive_candidate_map",
        lambda *_args: pytest.fail("fallback repeated strict whole-map validation"),
    )
    monkeypatch.setattr(
        agent,
        "_build_map_route",
        lambda mode: calls.append(mode),
    )

    with pytest.raises(ValueError, match="candidate map node coordinates are invalid"):
        agent.generate_map_route()

    assert calls == []
    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


def test_adaptive_future_coordinate_identity_propagates_after_one_fallback(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    agent, current, _, _ = _mid_act_adaptive_route_agent()
    original_builder = agent._build_map_route
    fallback_route = original_builder("conservative")
    target_y = current.y + 2
    target_x = fallback_route[target_y]
    original_target = agent.game.map.get_node(target_x, target_y)
    malformed = Node(target_x + 7, target_y, original_target.symbol)
    malformed.children = list(original_target.children)
    original_get_node = agent.game.map.get_node
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    calls = []
    mismatch_enabled = False

    def candidate_failure():
        raise agent_module._AdaptiveRouteCandidateGenerationError("injected")

    def tracked_builder(mode):
        nonlocal mismatch_enabled
        calls.append(mode)
        route = original_builder(mode)
        mismatch_enabled = True
        return route

    def mismatched_future(x, y):
        if mismatch_enabled and (x, y) == (target_x, target_y):
            return malformed
        return original_get_node(x, y)

    monkeypatch.setattr(agent, "_adaptive_route_candidates", candidate_failure)
    monkeypatch.setattr(agent, "_build_map_route", tracked_builder)
    monkeypatch.setattr(agent.game.map, "get_node", mismatched_future)

    with pytest.raises(ValueError, match="candidate map node coordinates are invalid"):
        agent.generate_map_route()

    assert calls == ["conservative"]
    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


def test_adaptive_selector_key_error_propagates_without_conservative_fallback(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    agent, _, _, _ = _mid_act_adaptive_route_agent()
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    calls = []
    original_builder = agent._build_map_route

    def track_builder(mode):
        calls.append(mode)
        return original_builder(mode)

    def broken_selector(*args):
        raise KeyError("selector bug")

    monkeypatch.setattr(agent, "_build_map_route", track_builder)
    monkeypatch.setattr(agent, "_select_adaptive_route", broken_selector)

    with pytest.raises(KeyError, match="selector bug"):
        agent.generate_map_route()

    assert calls == ["conservative", "aggressive"]
    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


def test_non_ironclad_adaptive_generation_uses_one_conservative_pass_with_reason(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    game_map, safe_start, elite_start = _optional_elite_route_map()
    agent = SimpleAgent(chosen_class=PlayerClass.THE_SILENT, elite_mode="adaptive")
    agent.game.map = game_map
    agent.game.act = 1
    agent.game.floor = 0
    agent.game.current_hp = 80
    agent.game.max_hp = 80
    agent.game.deck = _prepared_act1_deck()
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = [_potion("Fire Potion")]
    agent.game.relics = ["Burning Blood"]
    _set_start_screen(agent, safe_start, elite_start)
    original_builder = agent._build_map_route
    expected = original_builder("conservative")
    calls = []

    def track_builder(mode):
        calls.append(mode)
        return original_builder(mode)

    monkeypatch.setattr(agent, "_build_map_route", track_builder)

    route = agent.generate_map_route()

    assert route == expected
    assert calls == ["conservative"]
    assert "unsupported_character" in caplog.text


def test_adaptive_success_logs_one_committed_chosen_path(caplog):
    caplog.set_level(logging.INFO)
    game_map, safe_start, elite_start = _optional_elite_route_map()
    agent = _route_agent("adaptive", game_map, deck=_prepared_act1_deck())
    agent.game.potions = [_potion("Fire Potion")]
    _set_start_screen(agent, safe_start, elite_start)

    agent.generate_map_route()

    assert caplog.text.count("[MAP_ROUTING] Chosen path:") == 1


def test_forged_adaptive_absolute_path_triggers_conservative_fallback(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    agent, current, _, _ = _mid_act_adaptive_route_agent()
    conservative, aggressive = agent._adaptive_route_candidates()
    expected = agent._build_map_route("conservative")
    expected[:current.y + 1] = agent.map_route[:current.y + 1]
    forged_path = list(aggressive.absolute_path)
    forged_path[aggressive.start_y] = conservative.path[0]
    forged_aggressive = type(aggressive)(aggressive.features, tuple(forged_path))

    monkeypatch.setattr(
        agent,
        "_adaptive_route_candidates",
        lambda: (conservative, forged_aggressive),
    )

    route = agent.generate_map_route()

    assert route == expected
    assert "candidate_generation_failed" in caplog.text


def _late_adaptive_route_agent(current_y, *, boss_available=False):
    agent = _route_agent("adaptive", Map(), deck=_prepared_act1_deck())
    game_map = agent.game.map
    nodes = [Node(0, y, "M") for y in range(15)]
    for parent, child in zip(nodes, nodes[1:]):
        parent.children = [child]
    for node in nodes:
        game_map.add_node(node)
    agent.game.screen = SimpleNamespace(
        current_node=nodes[current_y],
        next_nodes=[] if current_y == 14 else [nodes[current_y + 1]],
        boss_available=boss_available,
    )
    agent.map_route = [0] * 15
    agent._last_route_hp_pct = 1.0
    agent._last_route_floor = 13
    return agent, nodes


def test_adaptive_current_y13_uses_valid_complete_nonzero_history_prefix():
    agent, nodes = _late_adaptive_route_agent(13)
    alternate_1 = Node(1, 1, "M")
    alternate_2 = Node(1, 2, "M")
    nodes[0].children = [alternate_1]
    alternate_1.children = [alternate_2]
    alternate_2.children = [nodes[3]]
    agent.game.map.add_node(alternate_1)
    agent.game.map.add_node(alternate_2)
    agent.map_route[:4] = [0, 1, 1, 0]

    route = agent.generate_map_route()
    action = agent.make_map_choice()

    assert route[:4] == [0, 1, 1, 0]
    assert route[13] == nodes[13].x
    assert route[14] == nodes[14].x
    assert isinstance(action, ChooseMapNodeAction)
    assert action.node == nodes[14]


def test_adaptive_late_fallback_ignores_irrelevant_malformed_earlier_node(
        monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    agent, nodes = _late_adaptive_route_agent(13)
    original_builder = agent._build_map_route
    expected = original_builder("conservative")
    expected[:14] = agent.map_route[:14]
    orphan = Node(5, 0, "M")
    orphan.children = [Node(5, 1, "M")]
    agent.game.map.add_node(orphan)
    calls = []

    def tracked_builder(mode):
        calls.append(mode)
        return original_builder(mode)

    monkeypatch.setattr(agent, "_build_map_route", tracked_builder)

    action = agent.make_map_choice()

    assert calls == ["conservative"]
    assert agent.map_route == expected
    assert isinstance(action, ChooseMapNodeAction)
    assert action.node == nodes[14]
    assert "candidate_generation_failed" in caplog.text


@pytest.mark.parametrize("history_kind", ("short", "stale"))
def test_adaptive_invalid_history_prefix_propagates_without_route_mutation(
        monkeypatch, caplog, history_kind):
    caplog.set_level(logging.INFO)
    agent, nodes = _late_adaptive_route_agent(13)
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    if history_kind == "short":
        agent.map_route = agent.map_route[:14]
    else:
        agent.map_route[13] = 1
    invalid_history = list(agent.map_route)
    calls = []

    def track_builder(mode):
        calls.append(mode)
        return original_route

    monkeypatch.setattr(agent, "_build_map_route", track_builder)

    with pytest.raises(RuntimeError, match="route history"):
        agent.generate_map_route()

    assert calls == []
    assert agent.map_route == invalid_history
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


@pytest.mark.parametrize("error_type", (IndexError, KeyError))
def test_adaptive_builder_programming_errors_propagate_without_route_mutation(
        monkeypatch, caplog, error_type):
    caplog.set_level(logging.INFO)
    agent, _, _, _ = _mid_act_adaptive_route_agent()
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    calls = []

    def broken_builder(mode):
        calls.append(mode)
        raise error_type("injected builder failure")

    monkeypatch.setattr(agent, "_build_map_route", broken_builder)

    with pytest.raises(error_type, match="injected builder failure"):
        agent.generate_map_route()

    assert calls == ["conservative"]
    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


@pytest.mark.parametrize("error_type", (IndexError, KeyError))
def test_adaptive_fallback_builder_error_is_not_retried_or_committed(
        monkeypatch, caplog, error_type):
    caplog.set_level(logging.INFO)
    agent, _, _, _ = _mid_act_adaptive_route_agent()
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    calls = []

    def candidate_failure():
        raise agent_module._AdaptiveRouteCandidateGenerationError("injected")

    def broken_fallback(mode):
        calls.append(mode)
        raise error_type("injected fallback builder failure")

    monkeypatch.setattr(agent, "_adaptive_route_candidates", candidate_failure)
    monkeypatch.setattr(agent, "_build_map_route", broken_fallback)

    with pytest.raises(error_type, match="injected fallback builder failure"):
        agent.generate_map_route()

    assert calls == ["conservative"]
    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert "[ADAPTIVE_ROUTE]" not in caplog.text


def test_boss_choice_skips_replan_and_route_mutation_at_map_height(monkeypatch):
    agent, nodes = _late_adaptive_route_agent(14, boss_available=True)
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)
    calls = []

    monkeypatch.setattr(agent, "generate_map_route", lambda: calls.append(True))
    agent.game.current_hp = 1

    action = agent.make_map_choice()

    assert isinstance(action, ChooseMapBossAction)
    assert calls == []
    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata


def test_adaptive_constructor_initializes_isolated_tracking_state():
    ironclad = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode="adaptive")
    silent = SimpleAgent(chosen_class=PlayerClass.THE_SILENT, elite_mode="adaptive")

    for agent in (ironclad, silent):
        assert agent.elite_mode == "adaptive"
        assert agent._adaptive_route_act is None
        assert agent._adaptive_visited_nodes == set()
        assert agent._adaptive_elite_seen is False
        assert agent._adaptive_last_rest_floor is None


def test_adaptive_replans_on_every_map_choice(monkeypatch):
    agent, _ = _late_adaptive_route_agent(13)
    original_builder = agent._build_map_route
    calls = []

    def tracked_builder(mode):
        calls.append(mode)
        return original_builder(mode)

    monkeypatch.setattr(agent, "_build_map_route", tracked_builder)

    agent.make_map_choice()
    agent.make_map_choice()

    assert calls == ["conservative", "aggressive", "conservative", "aggressive"]


def test_legacy_mode_keeps_hp_drop_replan_trigger(monkeypatch):
    game_map = Map.from_json(benchmark.legacy_route_fixture("hp_drop_replan")["nodes"])
    current = game_map.get_node(0, 1)
    next_node = game_map.get_node(0, 2)
    agent = _route_agent("aggressive", game_map)
    agent.map_route = [0, 0, 0]
    agent._last_route_hp_pct = 1.0
    agent.game.screen = SimpleNamespace(
        current_node=current,
        next_nodes=[next_node],
        boss_available=False,
    )
    original_builder = agent._build_map_route
    calls = []

    def tracked_builder(mode):
        calls.append(mode)
        return original_builder(mode)

    monkeypatch.setattr(agent, "_build_map_route", tracked_builder)

    agent.game.current_hp = 73
    assert agent.make_map_choice().node == next_node
    agent.game.current_hp = 71
    assert agent.make_map_choice().node == next_node

    assert calls == ["aggressive"]


def test_adaptive_history_is_idempotent_for_repeated_coordinate():
    agent, current, _, _ = _mid_act_adaptive_route_agent()

    agent._update_adaptive_route_history()
    agent._update_adaptive_route_history()

    assert agent._adaptive_route_act == 1
    assert agent._adaptive_visited_nodes == {(current.x, current.y)}
    assert agent._adaptive_elite_seen is True
    assert agent._adaptive_last_rest_floor is None


def test_adaptive_history_resets_on_act_change():
    agent, current, _, _ = _mid_act_adaptive_route_agent()
    agent._update_adaptive_route_history()
    agent.game.act = 2
    next_act_node = Node(6, 2, "M")
    agent.game.map.add_node(next_act_node)
    agent.game.screen.current_node = next_act_node

    agent._update_adaptive_route_history()

    assert agent._adaptive_route_act == 2
    assert agent._adaptive_visited_nodes == {(6, 2)}
    assert agent._adaptive_elite_seen is False
    assert agent._adaptive_last_rest_floor is None
    assert (current.x, current.y) not in agent._adaptive_visited_nodes


def test_adaptive_history_records_latest_rest_and_elite():
    agent, _, _, _ = _mid_act_adaptive_route_agent()
    rest = Node(1, 3, "R")
    elite = Node(2, 5, "E")
    agent.game.map.add_node(rest)
    agent.game.map.add_node(elite)
    agent.game.screen.current_node = rest

    agent._update_adaptive_route_history()
    agent.game.screen.current_node = elite
    agent._update_adaptive_route_history()

    assert agent._adaptive_visited_nodes == {(1, 3), (2, 5)}
    assert agent._adaptive_elite_seen is True
    assert agent._adaptive_last_rest_floor == 4


@pytest.mark.parametrize("invalid_kind", ("missing", "mismatched"))
def test_adaptive_history_waits_for_a_valid_matching_map_node(
        monkeypatch, invalid_kind):
    agent, _, _, _ = _mid_act_adaptive_route_agent()
    current = Node(2, 5, "E")
    agent.game.screen.current_node = current

    if invalid_kind == "mismatched":
        original_get_node = agent.game.map.get_node
        monkeypatch.setattr(
            agent.game.map,
            "get_node",
            lambda _x, _y: Node(3, 5, "E"),
        )

    agent._update_adaptive_route_history()

    assert agent._adaptive_visited_nodes == set()
    assert agent._adaptive_elite_seen is False

    valid = Node(current.x, current.y, "E")
    agent.game.map.add_node(valid)
    if invalid_kind == "mismatched":
        monkeypatch.setattr(agent.game.map, "get_node", original_get_node)

    agent._update_adaptive_route_history()

    assert agent._adaptive_visited_nodes == {(current.x, current.y)}
    assert agent._adaptive_elite_seen is True


@pytest.mark.parametrize(
    ("invalid_symbol", "valid_symbol"),
    ((None, "E"), ("invalid", "R")),
)
def test_adaptive_history_waits_for_a_supported_map_symbol(
        monkeypatch, invalid_symbol, valid_symbol):
    agent, _, _, _ = _mid_act_adaptive_route_agent()
    current = Node(3, 5, "M")
    agent.game.screen.current_node = current
    original_get_node = agent.game.map.get_node
    monkeypatch.setattr(
        agent.game.map,
        "get_node",
        lambda _x, _y: Node(current.x, current.y, invalid_symbol),
    )

    agent._update_adaptive_route_history()

    assert agent._adaptive_visited_nodes == set()
    assert agent._adaptive_elite_seen is False
    assert agent._adaptive_last_rest_floor is None

    valid = Node(current.x, current.y, valid_symbol)
    agent.game.map.add_node(valid)
    monkeypatch.setattr(agent.game.map, "get_node", original_get_node)

    agent._update_adaptive_route_history()

    assert agent._adaptive_visited_nodes == {(current.x, current.y)}
    assert agent._adaptive_elite_seen is (valid_symbol == "E")
    assert agent._adaptive_last_rest_floor == (
        valid.y + 1 if valid_symbol == "R" else None
    )


def test_adaptive_route_summary_requires_chosen_route_commit(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    game_map, safe_start, elite_start = _optional_elite_route_map()
    agent = _route_agent("adaptive", game_map, deck=_prepared_act1_deck())
    agent.game.potions = [_potion("Fire Potion")]
    _set_start_screen(agent, safe_start, elite_start)
    original_route = list(agent.map_route)
    original_metadata = (agent._last_route_hp_pct, agent._last_route_floor)

    monkeypatch.setattr(
        agent,
        "_log_chosen_map_route",
        lambda _route: (_ for _ in ()).throw(RuntimeError("chosen route log failed")),
    )

    with pytest.raises(RuntimeError, match="chosen route log failed"):
        agent.generate_map_route()

    assert agent.map_route == original_route
    assert (agent._last_route_hp_pct, agent._last_route_floor) == original_metadata
    assert not any(
        record.getMessage().startswith("[ADAPTIVE_ROUTE]")
        for record in caplog.records
    )


@pytest.mark.parametrize("outcome", ("success", "forced", "fallback", "unsupported"))
def test_adaptive_decision_emits_one_structured_summary(monkeypatch, caplog, outcome):
    caplog.set_level(logging.INFO)
    if outcome == "unsupported":
        game_map, safe_start, elite_start = _optional_elite_route_map()
        agent = SimpleAgent(chosen_class=PlayerClass.THE_SILENT, elite_mode="adaptive")
        agent.game.map = game_map
        agent.game.act = 1
        agent.game.floor = 0
        agent.game.current_hp = 80
        agent.game.max_hp = 80
        agent.game.deck = _prepared_act1_deck()
        agent.game.hand = []
        agent.game.monsters = []
        agent.game.potions = [_potion("Fire Potion")]
        agent.game.relics = ["Burning Blood"]
        _set_start_screen(agent, safe_start, elite_start)
    elif outcome == "forced":
        game_map, early_start, delayed_start = _forced_elite_route_map(1)
        agent = _route_agent("adaptive", game_map, deck=_prepared_act1_deck())
        agent.game.potions = [_potion("Fire Potion")]
        _set_start_screen(agent, early_start, delayed_start)
    else:
        game_map, safe_start, elite_start = _optional_elite_route_map()
        agent = _route_agent("adaptive", game_map, deck=_prepared_act1_deck())
        agent.game.potions = [_potion("Fire Potion")]
        _set_start_screen(agent, safe_start, elite_start)
        if outcome == "fallback":
            monkeypatch.setattr(
                agent,
                "_adaptive_route_candidates",
                lambda: (_ for _ in ()).throw(
                    agent_module._AdaptiveRouteCandidateGenerationError("injected")
                ),
            )

    agent.make_map_choice()

    summaries = [
        record.getMessage()
        for record in caplog.records
        if record.getMessage().startswith("[ADAPTIVE_ROUTE]")
    ]
    assert len(summaries) == 1
    assert "conservative=" in summaries[0]
    assert "aggressive=" in summaries[0]
    assert "elite_counts=" in summaries[0]
    assert "recovery=" in summaries[0]
    assert "budget=" in summaries[0]
    assert "selected=" in summaries[0]
    assert "reasons=" in summaries[0]
