from types import SimpleNamespace

from spirecomm.data import loader as data_loader
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
