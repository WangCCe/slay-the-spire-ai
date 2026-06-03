from types import SimpleNamespace

from spirecomm.data import loader as data_loader
from spirecomm.ai.heuristics.timing.balance_strategy import CombatBalanceStrategy
from spirecomm.ai.heuristics.timing.models import BalanceWeights, TurnTiming


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


def test_balance_strategy_current_damage_handles_numeric_string_monster_hp():
    stale_monster = SimpleNamespace(
        current_hp="0",
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=99,
        move_hits=1,
    )
    attacking_monster = SimpleNamespace(
        current_hp="12",
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=6,
        move_hits=2,
    )
    context = SimpleNamespace(monsters_alive=[stale_monster, attacking_monster])

    assert CombatBalanceStrategy()._estimate_current_damage(context) == 12


def test_balance_strategy_current_damage_rejects_nonfinite_monster_hp():
    invalid_hp = SimpleNamespace(
        current_hp=float("inf"),
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=99,
        move_hits=1,
    )
    attacking_monster = SimpleNamespace(
        current_hp=12,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=6,
        move_hits=1,
    )
    context = SimpleNamespace(monsters_alive=[invalid_hp, attacking_monster])

    assert CombatBalanceStrategy()._estimate_current_damage(context) == 6


def test_balance_strategy_current_damage_defaults_nonfinite_hits_without_aborting():
    invalid_hits = SimpleNamespace(
        current_hp=20,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=7,
        move_hits=float("inf"),
    )
    attacking_monster = SimpleNamespace(
        current_hp=12,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=6,
        move_hits=1,
    )
    context = SimpleNamespace(monsters_alive=[invalid_hits, attacking_monster])

    assert CombatBalanceStrategy()._estimate_current_damage(context) == 13


def test_balance_strategy_current_damage_accepts_decimal_string_damage_and_hits():
    monster = SimpleNamespace(
        current_hp=20,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage="7.0",
        move_hits="2.0",
    )
    context = SimpleNamespace(monsters_alive=[monster])

    assert CombatBalanceStrategy()._estimate_current_damage(context) == 14


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


def test_balance_strategy_uses_numeric_string_player_hp_for_defensive_adjustment():
    context = SimpleNamespace(
        player=SimpleNamespace(current_hp="20", max_hp="80"),
        monsters_alive=[],
    )
    weights = CombatBalanceStrategy().get_balance_weights(TurnTiming.BALANCED, context)
    baseline = BalanceWeights.balanced_weights()

    assert weights.block_weight > baseline.block_weight
    assert weights.damage_weight < baseline.damage_weight


def test_balance_strategy_uses_game_hp_for_defensive_adjustment():
    context = SimpleNamespace(
        game=SimpleNamespace(current_hp="20", max_hp="80"),
        monsters_alive=[],
    )
    weights = CombatBalanceStrategy().get_balance_weights(TurnTiming.BALANCED, context)
    baseline = BalanceWeights.balanced_weights()

    assert weights.block_weight > baseline.block_weight
    assert weights.damage_weight < baseline.damage_weight


def test_balance_strategy_prefers_valid_game_hp_over_stale_context_hp():
    context = SimpleNamespace(
        game=SimpleNamespace(current_hp="20", max_hp="80"),
        player=SimpleNamespace(current_hp="80", max_hp="80"),
        player_hp="80",
        player_max_hp="80",
        monsters_alive=[],
    )
    weights = CombatBalanceStrategy().get_balance_weights(TurnTiming.BALANCED, context)
    baseline = BalanceWeights.balanced_weights()

    assert weights.block_weight > baseline.block_weight
    assert weights.damage_weight < baseline.damage_weight


def test_low_scaling_encounter_uses_live_monster_id_for_summoners(monkeypatch):
    class CanonicalOnlyMonsterLoader:
        def __init__(self):
            self.summoner_names = []

        def is_monster_summoner(self, monster_name):
            self.summoner_names.append(monster_name)
            return monster_name == "Bronze Automaton"

        def does_monster_have_phase_change(self, _monster_name):
            return False

        def get_monster_threat_profile(self, _monster_name):
            return {"scaling_threat": 0}

    monster_loader = CanonicalOnlyMonsterLoader()
    monkeypatch.setattr(data_loader, "game_data_loader", monster_loader)
    live_automaton = SimpleNamespace(
        name="Automaton",
        monster_id="BronzeAutomaton",
    )
    context = SimpleNamespace(monsters_alive=[live_automaton])

    assert CombatBalanceStrategy()._is_low_scaling_encounter(context) is False
    assert monster_loader.summoner_names == ["Bronze Automaton"]


def test_low_scaling_encounter_uses_live_monster_id_for_threat_profile(monkeypatch):
    class CanonicalOnlyMonsterLoader:
        def __init__(self):
            self.profile_names = []

        def is_monster_summoner(self, _monster_name):
            return False

        def does_monster_have_phase_change(self, _monster_name):
            return False

        def get_monster_threat_profile(self, monster_name):
            self.profile_names.append(monster_name)
            if monster_name == "Red Slaver":
                return {"scaling_threat": 5}
            return {"scaling_threat": 0}

    monster_loader = CanonicalOnlyMonsterLoader()
    monkeypatch.setattr(data_loader, "game_data_loader", monster_loader)
    live_slaver = SimpleNamespace(
        name="Slaver",
        monster_id="SlaverRed",
    )
    context = SimpleNamespace(monsters_alive=[live_slaver])

    assert CombatBalanceStrategy()._is_low_scaling_encounter(context) is False
    assert monster_loader.profile_names == ["Red Slaver"]
