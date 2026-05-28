from types import SimpleNamespace

from spirecomm.ai.heuristics.timing.balance_strategy import CombatBalanceStrategy


def test_balance_strategy_current_damage_ignores_zero_hp_stale_monsters():
    monster = SimpleNamespace(
        current_hp=0,
        is_gone=False,
        half_dead=False,
        move_adjusted_damage=12,
        move_hits=1,
    )
    context = SimpleNamespace(monsters_alive=[monster])

    assert CombatBalanceStrategy()._estimate_current_damage(context) == 0


def test_balance_strategy_current_damage_clamps_negative_damage_and_hits():
    negative_damage = SimpleNamespace(
        current_hp=20,
        is_gone=False,
        half_dead=False,
        move_adjusted_damage=-3,
        move_hits=2,
    )
    negative_hits = SimpleNamespace(
        current_hp=20,
        is_gone=False,
        half_dead=False,
        move_adjusted_damage=7,
        move_hits=-2,
    )
    context = SimpleNamespace(monsters_alive=[negative_damage, negative_hits])

    assert CombatBalanceStrategy()._estimate_current_damage(context) == 7


def test_balance_strategy_current_damage_ignores_non_attack_intents():
    buffing = SimpleNamespace(
        current_hp=20,
        is_gone=False,
        half_dead=False,
        intent="Intent.BUFF",
        move_adjusted_damage=12,
        move_hits=1,
    )
    attacking = SimpleNamespace(
        current_hp=20,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK_DEBUFF",
        move_adjusted_damage=5,
        move_hits=2,
    )
    context = SimpleNamespace(monsters_alive=[buffing, attacking])

    assert CombatBalanceStrategy()._estimate_current_damage(context) == 10
