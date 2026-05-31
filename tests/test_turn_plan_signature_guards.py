from types import SimpleNamespace

from spirecomm.ai.agent import OptimizedAgent, TurnPlanSignature
from spirecomm.spire.character import Intent


def _card(card_id, name, uuid=None, cost=1, cost_for_turn=None, upgrades=0, is_playable=True):
    return SimpleNamespace(
        card_id=card_id,
        name=name,
        uuid=uuid,
        cost=cost,
        cost_for_turn=cost if cost_for_turn is None else cost_for_turn,
        upgrades=upgrades,
        is_playable=is_playable,
    )


def _power(power_id, amount):
    return SimpleNamespace(power_id=power_id, power_name=power_id, name=power_id, amount=amount)


def _monster(
    name="Cultist",
    monster_id="Cultist",
    move_adjusted_damage=12,
    move_hits=1,
    powers=None,
):
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
        powers=powers or [],
    )


def _game(hand, monster=None, current_hp=70, block=0, powers=None):
    return SimpleNamespace(
        hand=hand,
        current_hp=current_hp,
        player=SimpleNamespace(energy=3, block=block, powers=powers or []),
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


def test_should_replan_when_player_hp_or_block_changes():
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.current_plan_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=70, block=0)
    )

    wounded_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=12, block=0)
    )
    blocked_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=70, block=18)
    )

    assert agent.should_replan(wounded_signature)
    assert agent.should_replan(blocked_signature)


def test_turn_plan_signature_distinguishes_player_power_changes():
    no_strength_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], powers=[])
    )
    strength_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], powers=[_power("Strength", 2)])
    )

    assert no_strength_signature != strength_signature


def test_turn_plan_signature_distinguishes_monster_power_changes():
    normal_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], monster=_monster(powers=[]))
    )
    weak_signature = TurnPlanSignature(
        _game(
            [_card("Strike_R", "Strike")],
            monster=_monster(powers=[_power("Weak", 2)]),
        )
    )

    assert normal_signature != weak_signature


def test_turn_plan_signature_distinguishes_hand_card_cost_and_upgrade_changes():
    base_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", cost=1, cost_for_turn=1)])
    )
    discounted_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", cost=1, cost_for_turn=0)])
    )
    upgraded_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", cost=1, cost_for_turn=1, upgrades=1)])
    )

    assert base_signature != discounted_signature
    assert base_signature != upgraded_signature


def test_turn_plan_signature_distinguishes_hand_card_playability_changes():
    playable_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", is_playable=True)])
    )
    unplayable_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", is_playable=False)])
    )

    assert playable_signature != unplayable_signature
