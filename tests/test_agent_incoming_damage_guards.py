from types import SimpleNamespace

from spirecomm.ai.agent import OptimizedAgent, SimpleAgent


def _agent_with_monsters(monsters):
    agent = SimpleAgent.__new__(SimpleAgent)
    agent.game = SimpleNamespace(monsters=monsters, act=1)
    return agent


def test_simple_agent_incoming_damage_ignores_zero_hp_stale_monsters():
    monster = SimpleNamespace(
        current_hp=0,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=12,
        move_hits=1,
    )

    assert _agent_with_monsters([monster]).get_incoming_damage() == 0


def test_simple_agent_incoming_damage_clamps_negative_live_move_damage_to_zero():
    monster = SimpleNamespace(
        current_hp=20,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=-3,
        move_hits=2,
    )

    assert _agent_with_monsters([monster]).get_incoming_damage() == 0


def test_simple_agent_incoming_damage_ignores_non_attack_intents():
    monster = SimpleNamespace(
        current_hp=20,
        is_gone=False,
        half_dead=False,
        intent="Intent.DEBUFF",
        move_adjusted_damage=10,
        move_hits=2,
    )

    assert _agent_with_monsters([monster]).get_incoming_damage() == 0


def test_optimized_agent_combat_danger_ignores_zero_hp_stale_monsters():
    monster = SimpleNamespace(
        current_hp=0,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=20,
        move_hits=1,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = SimpleNamespace(
        monsters=[monster],
        current_hp=80,
        max_hp=80,
        act=1,
        room_type="Monster",
    )

    assert agent._evaluate_combat_danger(None) == 0.0


def test_optimized_agent_potion_logic_ignores_stale_monsters_for_multi_monster_trigger():
    stale_monster = SimpleNamespace(
        current_hp=0,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=30,
        move_hits=1,
    )
    live_monster = SimpleNamespace(
        current_hp=40,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=30,
        move_hits=1,
        block=0,
    )
    potion = SimpleNamespace(
        name="Fire Potion",
        can_use=True,
        requires_target=False,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game_tracker = None
    agent.game = SimpleNamespace(
        monsters=[stale_monster, live_monster],
        current_hp=80,
        max_hp=80,
        act=1,
        room_type="Monster",
        get_real_potions=lambda: [potion],
    )

    assert agent.use_next_potion() is None
