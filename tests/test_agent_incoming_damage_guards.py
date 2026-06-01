from types import SimpleNamespace

import spirecomm.ai.incoming_damage as incoming_damage
from spirecomm.ai.agent import OptimizedAgent, SimpleAgent
from spirecomm.ai.incoming_damage import known_unknown_move_has_no_immediate_damage
from spirecomm.communication.action import PotionAction
from spirecomm.spire.character import Intent
from spirecomm.spire.potion import Potion


def _agent_with_monsters(monsters):
    agent = SimpleAgent.__new__(SimpleAgent)
    agent.game = SimpleNamespace(monsters=monsters, act=1)
    return agent


def test_simple_agent_is_monster_attacking_accepts_string_intents():
    assert _agent_with_monsters([SimpleNamespace(intent="Intent.ATTACK")]).is_monster_attacking()
    assert _agent_with_monsters([SimpleNamespace(intent="Intent.NONE")]).is_monster_attacking()
    assert not _agent_with_monsters([SimpleNamespace(intent="NOT_ATTACK")]).is_monster_attacking()


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


def test_simple_agent_live_monster_accepts_numeric_string_hp():
    live = SimpleNamespace(current_hp="7", is_gone=False, half_dead=False)
    dead = SimpleNamespace(current_hp="0", is_gone=False, half_dead=False)

    assert SimpleAgent._is_live_monster(live)
    assert not SimpleAgent._is_live_monster(dead)


def test_simple_agent_target_helpers_accept_numeric_string_hp():
    dead = SimpleNamespace(current_hp="0", is_gone=False, half_dead=False)
    low = SimpleNamespace(current_hp="3", is_gone=False, half_dead=False)
    high = SimpleNamespace(current_hp="12", is_gone=False, half_dead=False)
    agent = _agent_with_monsters([dead, high, low])

    assert agent.many_monsters_alive()
    assert agent.get_low_hp_target() is low
    assert agent.get_high_hp_target() is high


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


def test_simple_agent_incoming_damage_estimates_unknown_intent_by_act():
    monster = SimpleNamespace(
        current_hp=20,
        is_gone=False,
        half_dead=False,
        intent=Intent.UNKNOWN,
        move_adjusted_damage=None,
        move_hits=1,
    )

    assert _agent_with_monsters([monster]).get_incoming_damage() == 5


def test_simple_agent_incoming_damage_counts_known_unknown_damage_move():
    monster = SimpleNamespace(
        name="Exploder",
        monster_id="Exploder",
        current_hp=30,
        is_gone=False,
        half_dead=False,
        intent=Intent.UNKNOWN,
        move_id=1,
        move_adjusted_damage=0,
        move_hits=1,
    )
    agent = _agent_with_monsters([monster])
    agent.game.act = 3

    assert agent.get_incoming_damage() == 30


def test_simple_agent_incoming_damage_ignores_known_no_damage_unknown_moves():
    monsters = [
        SimpleNamespace(
            name="Slime Boss",
            monster_id="Slime_Boss",
            current_hp=99,
            max_hp=140,
            is_gone=False,
            half_dead=False,
            intent=Intent.UNKNOWN,
            move_id=1,
            move_adjusted_damage=0,
            move_hits=1,
        ),
        SimpleNamespace(
            name="Acid Slime (L)",
            monster_id="Acid_Slime_L",
            current_hp=15,
            max_hp=65,
            is_gone=False,
            half_dead=False,
            intent=Intent.UNKNOWN,
            move_id=3,
            move_adjusted_damage=0,
            move_hits=1,
        ),
    ]

    assert _agent_with_monsters(monsters).get_incoming_damage() == 0


def test_known_unknown_move_guard_ignores_negated_attack_intent(monkeypatch):
    class FakeMonsterMoveLoader:
        def get_monster_moves(self, _monster_name):
            return [{"move_id": 9, "intent": "NOT_ATTACK", "damage": 0}]

    monkeypatch.setattr(incoming_damage, "game_data_loader", FakeMonsterMoveLoader())
    monster = SimpleNamespace(
        name="Training Dummy",
        current_hp=20,
        is_gone=False,
        half_dead=False,
        intent=Intent.UNKNOWN,
        move_id=9,
        move_adjusted_damage=0,
        move_hits=1,
    )

    assert known_unknown_move_has_no_immediate_damage(monster)


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


def test_optimized_agent_combat_danger_accepts_numeric_string_player_hp():
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = SimpleNamespace(
        monsters=[],
        current_hp="20",
        max_hp="80",
        act=1,
        room_type="Monster",
    )

    assert agent._evaluate_combat_danger(None) == 0.3


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


def test_defensive_potion_uses_player_block_not_monster_block():
    monster = SimpleNamespace(
        current_hp=40,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=30,
        move_hits=1,
        block=999,
    )
    potion = SimpleNamespace(
        name="Block Potion",
        can_use=True,
        requires_target=False,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game_tracker = None
    agent.game = SimpleNamespace(
        monsters=[monster],
        player=SimpleNamespace(block=0),
        current_hp=20,
        max_hp=80,
        act=1,
        room_type="Monster",
        get_real_potions=lambda: [potion],
    )

    action = agent.use_next_potion()

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_defensive_potion_accepts_numeric_string_player_hp_and_block():
    monster = SimpleNamespace(
        current_hp=40,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=30,
        move_hits=1,
        block=0,
    )
    potion = SimpleNamespace(
        name="Block Potion",
        can_use=True,
        requires_target=False,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game_tracker = None
    agent.game = SimpleNamespace(
        monsters=[monster],
        player=SimpleNamespace(block="0"),
        current_hp="20",
        max_hp="80",
        act=1,
        room_type="Monster",
        get_real_potions=lambda: [potion],
    )

    action = agent.use_next_potion()

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_defensive_potion_uses_effect_metadata_not_only_name():
    monster = SimpleNamespace(
        current_hp=40,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=30,
        move_hits=1,
        block=0,
    )
    potion = Potion(
        potion_id="EssenceOfSteel",
        name="Essence of Steel",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game_tracker = None
    agent.game = SimpleNamespace(
        monsters=[monster],
        player=SimpleNamespace(block=0),
        current_hp=40,
        max_hp=80,
        act=1,
        room_type="Monster",
        get_real_potions=lambda: [potion],
    )

    action = agent.use_next_potion()

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_healing_potion_uses_effect_metadata_not_only_name():
    monster = SimpleNamespace(
        current_hp=40,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=10,
        move_hits=1,
        block=0,
    )
    potion = Potion(
        potion_id="BloodPotion",
        name="Blood Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game_tracker = None
    agent.game = SimpleNamespace(
        monsters=[monster],
        player=SimpleNamespace(block=0),
        current_hp=20,
        max_hp=80,
        act=1,
        room_type="Monster",
        get_real_potions=lambda: [potion],
    )

    action = agent.use_next_potion()

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_damage_potion_uses_effect_metadata_not_only_name():
    monsters = [
        SimpleNamespace(
            current_hp=25,
            is_gone=False,
            half_dead=False,
            intent="Intent.ATTACK",
            move_adjusted_damage=12,
            move_hits=1,
            block=0,
        ),
        SimpleNamespace(
            current_hp=30,
            is_gone=False,
            half_dead=False,
            intent="Intent.ATTACK",
            move_adjusted_damage=12,
            move_hits=1,
            block=0,
        ),
    ]
    potion = Potion(
        potion_id="ExplosivePotion",
        name="Explosive Potion",
        can_use=True,
        can_discard=True,
        requires_target=False,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game_tracker = None
    agent.game = SimpleNamespace(
        monsters=monsters,
        player=SimpleNamespace(block=0),
        current_hp=80,
        max_hp=80,
        act=1,
        room_type="Monster",
        get_real_potions=lambda: [potion],
    )

    action = agent.use_next_potion()

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_damage_potion_usage_accepts_potion_id_only_object():
    monsters = [
        SimpleNamespace(
            current_hp=25,
            is_gone=False,
            half_dead=False,
            intent="Intent.ATTACK",
            move_adjusted_damage=12,
            move_hits=1,
            block=0,
        ),
        SimpleNamespace(
            current_hp=30,
            is_gone=False,
            half_dead=False,
            intent="Intent.ATTACK",
            move_adjusted_damage=12,
            move_hits=1,
            block=0,
        ),
    ]
    potion = SimpleNamespace(
        potion_id="FirePotion",
        can_use=True,
        requires_target=False,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game_tracker = None
    agent.game = SimpleNamespace(
        monsters=monsters,
        player=SimpleNamespace(block=0),
        current_hp=80,
        max_hp=80,
        act=1,
        room_type="Monster",
        get_real_potions=lambda: [potion],
    )

    action = agent.use_next_potion()

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_targeted_damage_potion_uses_effect_metadata_for_targeting():
    low_hp = SimpleNamespace(
        current_hp=10,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=12,
        move_hits=1,
        block=0,
    )
    high_hp = SimpleNamespace(
        current_hp=50,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=12,
        move_hits=1,
        block=0,
    )
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game_tracker = None
    agent.game = SimpleNamespace(
        monsters=[low_hp, high_hp],
        player=SimpleNamespace(block=0),
        current_hp=80,
        max_hp=80,
        act=1,
        room_type="Monster",
        get_real_potions=lambda: [potion],
    )

    action = agent.use_next_potion()

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_monster is high_hp


def test_targeted_damage_potion_orders_numeric_string_hp_numerically():
    lower_hp = SimpleNamespace(
        current_hp="9",
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=12,
        move_hits=1,
        block=0,
    )
    higher_hp = SimpleNamespace(
        current_hp="12",
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=12,
        move_hits=1,
        block=0,
    )
    potion = Potion(
        potion_id="FirePotion",
        name="Fire Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game_tracker = None
    agent.game = SimpleNamespace(
        monsters=[lower_hp, higher_hp],
        player=SimpleNamespace(block=0),
        current_hp=80,
        max_hp=80,
        act=1,
        room_type="Monster",
        get_real_potions=lambda: [potion],
    )

    action = agent.use_next_potion()

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_monster is higher_hp


def test_targeted_debuff_potion_uses_effect_metadata_for_targeting():
    low_hp = SimpleNamespace(
        current_hp=10,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=20,
        move_hits=1,
        block=0,
    )
    high_hp = SimpleNamespace(
        current_hp=50,
        is_gone=False,
        half_dead=False,
        intent="Intent.ATTACK",
        move_adjusted_damage=20,
        move_hits=1,
        block=0,
    )
    potion = Potion(
        potion_id="FearPotion",
        name="Fear Potion",
        can_use=True,
        can_discard=True,
        requires_target=True,
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game_tracker = None
    agent.game = SimpleNamespace(
        monsters=[low_hp, high_hp],
        player=SimpleNamespace(block=0),
        current_hp=20,
        max_hp=80,
        act=1,
        room_type="Monster",
        get_real_potions=lambda: [potion],
    )

    action = agent.use_next_potion()

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_monster is high_hp
