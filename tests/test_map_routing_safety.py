from types import SimpleNamespace

from spirecomm.ai.agent import SimpleAgent
from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter
from spirecomm.communication.action import ChooseMapNodeAction
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


def test_conservative_act2_elite_penalty_blocks_future_reward_bait():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="conservative")
    context = _context(act=2, floor=22, hp_pct=1.0)

    elite_priority = router.calculate_node_priority(SimpleNamespace(symbol="E"), context)

    assert elite_priority <= -1000


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
