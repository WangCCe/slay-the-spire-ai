from types import SimpleNamespace

from spirecomm.ai.heuristics import card as card_module
from spirecomm.ai.heuristics.card import SynergyCardEvaluator
from spirecomm.spire.card import Card, CardRarity, CardType


class _FakeCardDataLoader:
    def __init__(self, cards):
        self.cards = cards

    def get_card_data(self, card_name):
        return self.cards.get(card_name.lower())


def test_defensive_detection_uses_base_name_for_upgraded_cards(monkeypatch):
    monkeypatch.setattr(
        card_module,
        "game_data_loader",
        _FakeCardDataLoader(
            {
                "shrug it off": {
                    "name": "Shrug It Off",
                    "type": "SKILL",
                    "rarity": "COMMON",
                    "cost": "1",
                    "description": "Gain 8 Block. Draw 1 card.",
                },
            }
        ),
    )
    shrug_plus = Card(
        "Shrug It Off",
        "Shrug It Off+",
        CardType.SKILL,
        CardRarity.COMMON,
        upgrades=1,
        cost=1,
    )

    assert SynergyCardEvaluator(player_class="IRONCLAD")._is_defensive_card(shrug_plus) is True


def test_hand_of_greed_is_not_classified_as_defensive():
    hand_of_greed = Card(
        "HandOfGreed",
        "Hand of Greed",
        CardType.ATTACK,
        CardRarity.RARE,
        cost=2,
    )
    evaluator = SynergyCardEvaluator(player_class="IRONCLAD")

    assert evaluator._is_offensive_card(hand_of_greed) is True
    assert evaluator._is_defensive_card(hand_of_greed) is False


def test_defensive_detection_accepts_string_card_type(monkeypatch):
    monkeypatch.setattr(
        card_module,
        "game_data_loader",
        _FakeCardDataLoader(
            {
                "shrug it off": {
                    "name": "Shrug It Off",
                    "type": "SKILL",
                    "rarity": "COMMON",
                    "cost": "1",
                    "description": "Gain 8 Block. Draw 1 card.",
                },
            }
        ),
    )
    shrug = Card(
        "Shrug It Off",
        "Shrug It Off",
        CardType.SKILL,
        CardRarity.COMMON,
        cost=1,
    )
    shrug.type = "SKILL"

    assert SynergyCardEvaluator(player_class="IRONCLAD")._is_defensive_card(shrug) is True


def test_offensive_detection_accepts_string_card_type(monkeypatch):
    monkeypatch.setattr(card_module, "game_data_loader", _FakeCardDataLoader({}))
    strike = Card(
        "Strike_R",
        "Strike",
        CardType.ATTACK,
        CardRarity.BASIC,
        cost=1,
    )
    strike.type = "ATTACK"

    assert SynergyCardEvaluator(player_class="IRONCLAD")._is_offensive_card(strike) is True


def test_baseline_score_uses_base_name_for_upgraded_cards():
    evaluator = SynergyCardEvaluator(player_class="IRONCLAD")
    base_card = Card(
        "Pommel Strike",
        "Pommel Strike",
        CardType.ATTACK,
        CardRarity.COMMON,
        cost=1,
    )
    upgraded_card = Card(
        "Pommel Strike+1",
        "Pommel Strike+1",
        CardType.ATTACK,
        CardRarity.COMMON,
        upgrades=1,
        cost=1,
    )

    assert (
        evaluator._calculate_baseline_score(upgraded_card, None)
        == evaluator._calculate_baseline_score(base_card, None)
    )


def test_baseline_score_counts_repeated_hit_damage_for_efficiency():
    evaluator = SynergyCardEvaluator(player_class="IRONCLAD")
    pummel = Card(
        "Pummel",
        "Pummel",
        CardType.ATTACK,
        CardRarity.UNCOMMON,
        cost=1,
    )
    base_score = evaluator._calculate_baseline_score(pummel, None)

    scored = evaluator._calculate_baseline_score(
        pummel,
        {
            "name": "Pummel",
            "type": "ATTACK",
            "rarity": "UNCOMMON",
            "cost": "1",
            "description": "Deal 2 damage 4 times. Exhaust.",
        },
    )

    assert scored >= base_score + 20


def test_baseline_score_parses_numeric_card_data_costs():
    evaluator = SynergyCardEvaluator(player_class="IRONCLAD")
    pummel = Card(
        "Pummel",
        "Pummel",
        CardType.ATTACK,
        CardRarity.UNCOMMON,
        cost=1,
    )
    base_score = evaluator._calculate_baseline_score(pummel, None)

    scored = evaluator._calculate_baseline_score(
        pummel,
        {
            "name": "Pummel",
            "type": "ATTACK",
            "rarity": "UNCOMMON",
            "cost": 1,
            "description": "Deal 2 damage 4 times. Exhaust.",
        },
    )

    assert scored >= base_score + 20


def test_combo_detection_uses_base_names_for_upgraded_cards():
    evaluator = SynergyCardEvaluator(player_class="IRONCLAD")
    demon_form = Card(
        "Demon Form+1",
        "Demon Form+1",
        CardType.POWER,
        CardRarity.RARE,
        upgrades=1,
        cost=3,
    )
    limit_break = Card(
        "Limit Break+1",
        "Limit Break+1",
        CardType.SKILL,
        CardRarity.RARE,
        upgrades=1,
        cost=1,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(deck=[limit_break]),
        deck_archetype="strength",
    )

    assert evaluator._detect_combo_potential(demon_form, context, None) >= 25


def test_combo_detection_rewards_second_combo_piece_when_first_is_in_deck():
    evaluator = SynergyCardEvaluator(player_class="IRONCLAD")
    demon_form = Card(
        "Demon Form",
        "Demon Form",
        CardType.POWER,
        CardRarity.RARE,
        cost=3,
    )
    limit_break = Card(
        "Limit Break",
        "Limit Break",
        CardType.SKILL,
        CardRarity.RARE,
        cost=1,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(deck=[demon_form]),
        deck_archetype="strength",
    )

    assert evaluator._detect_combo_potential(limit_break, context, None) >= 25


def test_apotheosis_combo_counts_none_upgrades_as_unupgraded():
    evaluator = SynergyCardEvaluator(player_class="IRONCLAD")
    apotheosis = Card(
        "Apotheosis",
        "Apotheosis",
        CardType.SKILL,
        CardRarity.RARE,
        cost=2,
    )
    unknown_upgrade_card = Card(
        "Pommel Strike",
        "Pommel Strike",
        CardType.ATTACK,
        CardRarity.COMMON,
        upgrades=None,
        cost=1,
    )
    context = SimpleNamespace(
        game=SimpleNamespace(deck=[unknown_upgrade_card]),
        deck_archetype="unknown",
    )

    assert evaluator._detect_combo_potential(apotheosis, context, None) >= 1


def test_context_modifier_uses_turn_cost_for_energy_efficiency():
    evaluator = SynergyCardEvaluator(player_class="IRONCLAD")
    context = SimpleNamespace(
        energy_available=1,
        player_hp_pct=0.5,
        monsters_alive=[],
    )
    zero_for_turn = Card(
        "Shrug It Off",
        "Shrug It Off",
        CardType.SKILL,
        CardRarity.COMMON,
        cost=1,
        cost_for_turn=0,
    )

    assert evaluator._calculate_context_modifier(zero_for_turn, context, None) == 1.2


def test_context_modifier_handles_missing_card_cost_as_zero():
    evaluator = SynergyCardEvaluator(player_class="IRONCLAD")
    context = SimpleNamespace(
        energy_available=1,
        player_hp_pct=0.5,
        monsters_alive=[],
    )
    missing_cost = Card(
        "Discovery",
        "Discovery",
        CardType.SKILL,
        CardRarity.RARE,
        cost=None,
        cost_for_turn=None,
    )

    assert evaluator._calculate_context_modifier(missing_cost, context, None) == 1.2


def test_context_modifier_accepts_numeric_string_low_monster_hp():
    evaluator = SynergyCardEvaluator(player_class="IRONCLAD")
    context = SimpleNamespace(
        energy_available=1,
        player_hp_pct=0.5,
        incoming_damage=0,
        game=SimpleNamespace(current_hp=80),
        monsters_alive=[
            SimpleNamespace(current_hp="19"),
        ],
    )
    strike = Card(
        "Strike_R",
        "Strike",
        CardType.ATTACK,
        CardRarity.BASIC,
        cost=1,
        cost_for_turn=1,
    )

    assert evaluator._calculate_context_modifier(strike, context, None) == 1.3
