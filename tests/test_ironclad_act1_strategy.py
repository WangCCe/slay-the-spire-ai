from types import SimpleNamespace

from spirecomm.ai.heuristics.ironclad_deck import IroncladDeckStrategy
from spirecomm.ai.heuristics.ironclad_evaluator import IroncladCardEvaluator
from spirecomm.ai.heuristics.map_routing import AdaptiveMapRouter


def _card(card_id, cost=1, upgrades=0):
    return SimpleNamespace(card_id=card_id, name=card_id, cost=cost, upgrades=upgrades)


def _context(deck=None, floor=5, hp_pct=1.0):
    game = SimpleNamespace(
        deck=deck or [],
        potions=[],
        relics=["Burning Blood"],
    )
    return SimpleNamespace(
        game=game,
        act=1,
        floor=floor,
        player_hp_pct=hp_pct,
        deck_archetype="unknown",
        archetype_score=0.0,
    )


def test_act1_evaluator_prefers_frontload_over_unsupported_engine():
    evaluator = IroncladCardEvaluator()
    context = _context(
        deck=[
            _card("Strike_R"),
            _card("Strike_R"),
            _card("Defend_R"),
            _card("Defend_R"),
            _card("Bash"),
        ],
        floor=4,
    )

    pommel = evaluator.evaluate_card(_card("Pommel Strike"), context)
    body_slam = evaluator.evaluate_card(_card("Body Slam"), context)
    limit_break = evaluator.evaluate_card(_card("Limit Break"), context)

    assert pommel > body_slam
    assert pommel > limit_break


def test_act1_deck_strategy_rejects_unsupported_payoffs():
    strategy = IroncladDeckStrategy()
    context = _context(deck=[_card("Strike_R"), _card("Defend_R"), _card("Bash")])

    assert strategy.should_pick_card(_card("Limit Break"), context)[0] is False
    assert strategy.should_pick_card(_card("Body Slam"), context)[0] is False
    assert strategy.should_pick_card(_card("Pommel Strike"), context)[0] is True


def test_aggressive_elite_route_is_gated_until_deck_is_ready():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="aggressive")
    elite_node = SimpleNamespace(symbol="E")

    weak_context = _context(deck=[_card("Strike_R"), _card("Defend_R"), _card("Bash")], floor=5)
    ready_context = _context(
        deck=[
            _card("Bash", upgrades=1),
            _card("Pommel Strike"),
            _card("Anger"),
            _card("Cleave"),
            _card("Shrug It Off"),
        ],
        floor=9,
        hp_pct=0.9,
    )
    ready_context.game.potions = [SimpleNamespace(potion_id="Fire Potion", can_use=True)]
    ready_context.game.relics = ["Burning Blood", "Akabeko"]

    assert router.calculate_node_priority(elite_node, weak_context) < 0
    assert router.calculate_node_priority(elite_node, ready_context) > 0


def test_act1_elite_readiness_counts_upgraded_card_names():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="aggressive")
    context = _context(
        deck=[
            _card("Bash+1", upgrades=1),
            _card("Pommel Strike+1", upgrades=1),
            _card("Anger+1", upgrades=1),
            _card("Cleave+1", upgrades=1),
            _card("Shrug It Off+1", upgrades=1),
        ],
        floor=9,
        hp_pct=0.9,
    )
    context.game.potions = [SimpleNamespace(potion_id="Fire Potion", can_use=True)]
    context.game.relics = ["Burning Blood", "Akabeko"]

    assert router._act_1_elite_readiness_score(context) >= 5


def test_act1_elite_readiness_counts_compact_potion_ids_by_name():
    router = AdaptiveMapRouter(player_class="IRONCLAD", elite_mode="aggressive")
    context = _context(floor=9, hp_pct=0.9)
    context.game.potions = [
        SimpleNamespace(potion_id="FirePotion", name="Fire Potion", can_use=True)
    ]

    assert router._act_1_elite_readiness_score(context) == 2
