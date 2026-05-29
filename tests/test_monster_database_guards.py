from types import SimpleNamespace

from spirecomm.ai.heuristics.monster_database import evaluate_monster_threat
from spirecomm.spire.character import Intent


def test_monster_database_threat_ignores_non_attack_stale_damage():
    monster = SimpleNamespace(
        monster_id="Louse",
        intent=Intent.DEBUFF,
        move_adjusted_damage=20,
    )
    context = SimpleNamespace(player_hp_pct=1.0)

    assert evaluate_monster_threat(monster, context) == 1


def test_monster_database_threat_scales_live_gremlin_nob_id():
    monster = SimpleNamespace(
        name="Gremlin Nob",
        monster_id="GremlinNob",
        intent=Intent.ATTACK,
        move_adjusted_damage=14,
    )
    context = SimpleNamespace(player_hp_pct=1.0, turn=4)

    assert evaluate_monster_threat(monster, context) == 11
