from types import SimpleNamespace

from spirecomm.ai.agent import SimpleAgent


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
