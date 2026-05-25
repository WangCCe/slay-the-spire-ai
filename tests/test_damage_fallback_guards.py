from types import SimpleNamespace

import spirecomm.ai.heuristics.ironclad_combat as ironclad_combat
import spirecomm.ai.heuristics.simulation as simulation
from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner
from spirecomm.ai.heuristics.simulation import FastCombatSimulator
from spirecomm.spire.card import Card, CardRarity, CardType


def _unknown_attack():
    card = Card(
        card_id="UnknownAttack",
        name="Unknown Attack",
        card_type=CardType.ATTACK,
        rarity=CardRarity.COMMON,
        has_target=True,
        cost=1,
    )
    card.damage = None
    return card


def test_fast_simulator_falls_back_when_card_damage_parse_returns_none(monkeypatch):
    monkeypatch.setattr(
        simulation.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal unknown damage."},
    )
    monkeypatch.setattr(
        simulation.game_data_loader,
        "_parse_card_damage",
        lambda card_data: None,
    )
    state = SimpleNamespace(
        monsters=[
            {
                "hp": 20,
                "block": 0,
                "is_gone": False,
                "vulnerable": 0,
                "weak": 0,
                "thorns": 0,
            }
        ],
        player_strength=0,
        player_hp=80,
        total_damage_dealt=0,
        monsters_killed=0,
        damage_instances=0,
    )

    FastCombatSimulator(None)._apply_attack(
        state,
        _unknown_attack(),
        target=None,
        target_index=0,
        context=None,
    )

    assert state.total_damage_dealt == 6


def test_ironclad_prune_targets_falls_back_when_damage_parse_returns_none(monkeypatch):
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "get_card_data",
        lambda card_name: {"description": "Deal unknown damage."},
    )
    monkeypatch.setattr(
        ironclad_combat.game_data_loader,
        "_parse_card_damage",
        lambda card_data: None,
    )
    monster = SimpleNamespace(current_hp=20, block=0)
    context = SimpleNamespace(strength=0, monsters_alive=[monster])
    state = SimpleNamespace(monsters=[{"hp": 20, "block": 0, "is_gone": False}])

    pruned = IroncladCombatPlanner()._prune_targets(
        _unknown_attack(),
        [(monster, 0, 10)],
        context,
        state,
    )

    assert pruned == [(monster, 0, 10)]
