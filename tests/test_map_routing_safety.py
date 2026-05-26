from types import SimpleNamespace

from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter
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


def test_map_router_pre_boss_rest_overrides_high_value_smith():
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

    assert option == RestOption.REST
