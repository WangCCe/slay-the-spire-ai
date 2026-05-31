from types import SimpleNamespace

from spirecomm.ai.agent import TurnPlanSignature
from spirecomm.spire.character import Intent


def _card(card_id, name, uuid=None):
    return SimpleNamespace(card_id=card_id, name=name, uuid=uuid)


def _monster(name="Cultist", monster_id="Cultist", move_adjusted_damage=12, move_hits=1):
    return SimpleNamespace(
        name=name,
        monster_id=monster_id,
        current_hp=40,
        block=0,
        intent=Intent.ATTACK,
        move_adjusted_damage=move_adjusted_damage,
        move_hits=move_hits,
        is_gone=False,
        half_dead=False,
    )


def _game(hand, monster=None, current_hp=70, block=0):
    return SimpleNamespace(
        hand=hand,
        current_hp=current_hp,
        player=SimpleNamespace(energy=3, block=block),
        monsters=[monster or _monster()],
    )


def test_turn_plan_signature_distinguishes_cards_when_uuid_is_missing():
    strike_signature = TurnPlanSignature(_game([_card("Strike_R", "Strike")]))
    defend_signature = TurnPlanSignature(_game([_card("Defend_R", "Defend")]))

    assert strike_signature.hand_cards != defend_signature.hand_cards
    assert strike_signature != defend_signature


def test_turn_plan_signature_distinguishes_live_monster_damage_changes():
    weaker_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], monster=_monster(move_adjusted_damage=8))
    )
    stronger_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], monster=_monster(move_adjusted_damage=18))
    )
    multi_hit_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], monster=_monster(move_adjusted_damage=8, move_hits=2))
    )

    assert weaker_signature.monster_signature != stronger_signature.monster_signature
    assert weaker_signature.monster_signature != multi_hit_signature.monster_signature
    assert weaker_signature != stronger_signature
    assert weaker_signature != multi_hit_signature


def test_turn_plan_signature_distinguishes_live_monster_identity_changes():
    cultist_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], monster=_monster(name="Cultist", monster_id="Cultist"))
    )
    louse_signature = TurnPlanSignature(
        _game(
            [_card("Strike_R", "Strike")],
            monster=_monster(name="Louse", monster_id="FuzzyLouseNormal"),
        )
    )

    assert cultist_signature.monster_signature != louse_signature.monster_signature
    assert cultist_signature != louse_signature


def test_turn_plan_signature_distinguishes_player_hp_and_block_changes():
    healthy_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=70, block=0)
    )
    wounded_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=12, block=0)
    )
    blocked_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=70, block=18)
    )

    assert healthy_signature != wounded_signature
    assert healthy_signature != blocked_signature
