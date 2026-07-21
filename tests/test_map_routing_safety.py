from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from analysis_scripts import benchmark_adaptive_route_candidates as benchmark
from spirecomm.ai.agent import SimpleAgent
from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter, RouteCandidateFeatures
from spirecomm.communication.action import ChooseMapNodeAction, RestAction
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
    safe = router.describe_candidate(
        "conservative",
        (0, 0, 0, 0, 0, 0, 0),
        ("M", "M", "R", "M", "M", "M", "M"),
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
        eligible_candidate,
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
