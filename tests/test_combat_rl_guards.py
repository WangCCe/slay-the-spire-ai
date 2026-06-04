from types import SimpleNamespace

from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.communication.action import (
    CancelAction,
    CardRewardAction,
    EndTurnAction,
    PlayCardAction,
    PotionAction,
    WaitAction,
)
from spirecomm.spire.card import CardType
from spirecomm.spire.character import Intent
from spirecomm.spire.screen import ScreenType


def _agent():
    agent = CombatRLAgent.__new__(CombatRLAgent)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=lambda game: EndTurnAction())
    return agent


def _monster(hp=40, damage=12, index=0, name="Cultist", monster_id="Cultist"):
    return SimpleNamespace(
        name=name,
        monster_id=monster_id,
        current_hp=hp,
        move_adjusted_damage=damage,
        move_hits=1,
        is_gone=False,
        half_dead=False,
        monster_index=index,
    )


def _game(**kwargs):
    defaults = dict(
        screen_type=None,
        in_combat=True,
        potion_available=True,
        play_available=True,
        end_available=True,
        potions=[],
        monsters=[_monster()],
        current_hp=30,
        max_hp=80,
        room_type="Monster",
        player=SimpleNamespace(energy=2),
        hand=[],
        floor=5,
        turn=2,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_potion_guard_uses_damage_potion_in_danger():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    game = _game(potions=[potion], monsters=[_monster(hp=50, damage=20, index=0)])

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_accepts_missing_can_use_on_damage_potion():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        requires_target=True,
        effect_type="damage",
    )
    game = _game(potions=[potion], monsters=[_monster(hp=50, damage=20, index=0)])

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_infers_missing_potion_available_from_usable_potion():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    game = _game(potions=[potion], monsters=[_monster(hp=50, damage=20, index=0)])
    del game.potion_available

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_uses_get_real_potions_when_raw_potions_are_missing():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    game = _game(potions=[], monsters=[_monster(hp=50, damage=20, index=0)])
    del game.potions
    game.get_real_potions = lambda: [potion]

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_preserves_target_index_when_dead_monster_precedes_target():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    dead = _monster(hp=0, damage=0, index=0)
    live = _monster(hp=50, damage=20, index=1)
    del dead.monster_index
    del live.monster_index
    game = _game(potions=[potion], monsters=[dead, live])

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.target_index == 1


def test_potion_guard_skips_name_only_empty_potion_slot():
    empty_slot = SimpleNamespace(
        name="Potion Slot",
        can_use=True,
        requires_target=False,
    )
    game = _game(
        potions=[empty_slot],
        monsters=[_monster(hp=50, damage=25, index=0)],
    )

    assert _agent()._maybe_use_potion_guard(game) is None


def test_potion_guard_skips_safe_combat():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    game = _game(potions=[potion], monsters=[_monster(hp=20, damage=0, index=0)], current_hp=70)

    assert _agent()._maybe_use_potion_guard(game) is None


def test_potion_guard_accepts_decimal_string_player_hp():
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        name="Fire Potion",
        can_use=True,
        requires_target=True,
        effect_type="damage",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=50, damage=20, index=0)],
        current_hp="30.0",
        max_hp="80.0",
    )

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion
    assert action.target_index == 0


def test_potion_guard_saves_healing_potion_when_hp_is_high():
    potion = SimpleNamespace(
        potion_id="BloodPotion",
        name="Blood Potion",
        can_use=True,
        requires_target=False,
        effect_type="heal_percent",
    )
    game = _game(
        potions=[potion],
        monsters=[
            _monster(hp=25, damage=6, index=0),
            _monster(hp=20, damage=5, index=1),
            _monster(hp=18, damage=5, index=2),
        ],
        current_hp=73,
        max_hp=80,
        room_type="MonsterRoom",
    )

    assert _agent()._maybe_use_potion_guard(game) is None


def test_potion_guard_uses_healing_potion_to_survive_lethal_turn():
    potion = SimpleNamespace(
        potion_id="BloodPotion",
        name="Blood Potion",
        can_use=True,
        requires_target=False,
        effect_type="heal_percent",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=180, damage=24, index=0)],
        current_hp=9,
        max_hp=80,
        room_type="MonsterRoomBoss",
    )

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_potion_guard_saves_energy_potion_on_safe_boss_turn():
    potion = SimpleNamespace(
        potion_id="EnergyPotion",
        name="Energy Potion",
        can_use=True,
        requires_target=False,
        effect_type="energy",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=250, damage=0, index=0, name="The Guardian")],
        current_hp=68,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        turn=1,
    )

    assert _agent()._maybe_use_potion_guard(game) is None


def test_potion_guard_uses_energy_potion_under_current_turn_pressure():
    potion = SimpleNamespace(
        potion_id="EnergyPotion",
        name="Energy Potion",
        can_use=True,
        requires_target=False,
        effect_type="energy",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=120, damage=32, index=0, name="The Guardian")],
        current_hp=8,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        turn=19,
    )

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_potion_guard_saves_utility_choice_potion_on_safe_boss_turn():
    potion = SimpleNamespace(
        potion_id="AttackPotion",
        name="Attack Potion",
        can_use=True,
        requires_target=False,
        effect_type="card_choice_attack",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=250, damage=0, index=0, name="The Guardian")],
        current_hp=75,
        max_hp=80,
        room_type="MonsterRoomBoss",
        floor=16,
        turn=1,
    )

    assert _agent()._maybe_use_potion_guard(game) is None


def test_potion_guard_uses_utility_choice_potion_under_current_turn_pressure():
    potion = SimpleNamespace(
        potion_id="ColorlessPotion",
        name="Colorless Potion",
        can_use=True,
        requires_target=False,
        effect_type="card_choice_colorless",
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=120, damage=24, index=0, name="Cultist")],
        current_hp=34,
        max_hp=80,
        room_type="MonsterRoom",
        floor=25,
        turn=3,
    )

    action = _agent()._maybe_use_potion_guard(game)

    assert isinstance(action, PotionAction)
    assert action.potion is potion


def test_potion_guard_does_not_auto_use_elixir_hand_select_potion():
    potion = SimpleNamespace(
        potion_id="ElixirPotion",
        name="Elixir",
        can_use=True,
        requires_target=False,
        effect_type="exhaust_hand_select",
    )
    game = _game(
        potions=[potion],
        monsters=[
            _monster(hp=52, damage=10, index=0, name="Blue Slaver"),
            _monster(hp=48, damage=10, index=1, name="Red Slaver"),
        ],
        current_hp=46,
        max_hp=85,
        room_type="EventRoom",
        floor=27,
        turn=1,
    )

    assert _agent()._maybe_use_potion_guard(game) is None


def test_rl_potion_action_is_blocked_in_low_risk_act1_hallway_before_boss():
    potion = SimpleNamespace(
        potion_id="ExplosivePotion",
        name="Explosive Potion",
        can_use=True,
        requires_target=False,
        effect_type="damage",
    )
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        potions=[potion],
        monsters=[_monster(hp=34, damage=5, index=0, name="Louse")],
        current_hp=70,
        max_hp=80,
        room_type="MonsterRoom",
        floor=10,
        act=1,
        player=SimpleNamespace(energy=3),
        hand=[strike],
    )
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PotionAction(True, potion=potion)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=fallback_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert calls == {"rl": 1, "fallback": 1}


def test_rl_incoming_damage_clamps_negative_live_move_damage_to_zero():
    monster = _monster(hp=25, damage=-1)
    monster.move_hits = 3
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 0


def test_rl_alive_monsters_accepts_numeric_string_hp():
    dead = _monster(hp="0", index=0)
    live = _monster(hp="12", index=1)
    game = _game(monsters=[dead, live])

    assert CombatRLAgent._alive_monsters(game) == [live]


def test_rl_best_monster_index_accepts_numeric_string_hp():
    dead = _monster(hp="0", index=0)
    low = _monster(hp="3", index=1)
    high = _monster(hp="12", index=2)
    game = _game(monsters=[dead, low, high])

    assert CombatRLAgent._best_monster_index(game) == 2


def test_rl_potion_target_index_orders_numeric_string_hp_numerically():
    potion = SimpleNamespace(effect_type="damage")
    low = _monster(hp="9", index=0)
    high = _monster(hp="12", index=1)
    game = _game(monsters=[low, high])

    assert CombatRLAgent._potion_target_index(potion, [low, high], game) == 1


def test_rl_incoming_damage_clamps_negative_live_move_hits_to_one():
    monster = _monster(hp=25, damage=7)
    monster.move_hits = -2
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 7


def test_rl_incoming_damage_accepts_decimal_string_damage_and_hits():
    monster = _monster(hp=25, damage="7.0")
    monster.move_hits = "2.0"
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 14


def test_rl_incoming_damage_ignores_nonfinite_live_move_damage():
    monster = _monster(hp=25, damage=float("inf"))
    monster.move_hits = 2
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 0


def test_rl_incoming_damage_defaults_nonfinite_live_move_hits_to_one():
    monster = _monster(hp=25, damage=7)
    monster.move_hits = float("inf")
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 7


def test_rl_incoming_damage_ignores_non_attack_intents():
    monster = _monster(hp=25, damage=7)
    monster.intent = "Intent.DEBUFF"
    monster.move_hits = 2
    game = _game(monsters=[monster])

    assert CombatRLAgent._incoming_damage(game) == 0


def test_rl_incoming_damage_estimates_unknown_intent_by_act():
    monster = _monster(hp=25, damage=None)
    monster.intent = Intent.UNKNOWN
    game = _game(monsters=[monster], act=2)

    assert CombatRLAgent._incoming_damage(game) == 10


def test_rl_incoming_damage_counts_known_unknown_damage_move():
    monster = _monster(
        hp=30,
        damage=0,
        name="Exploder",
        monster_id="Exploder",
    )
    monster.intent = Intent.UNKNOWN
    monster.move_id = 1
    game = _game(monsters=[monster], act=3)

    assert CombatRLAgent._incoming_damage(game) == 30


def test_rl_incoming_damage_ignores_known_no_damage_unknown_moves():
    preparing = _monster(
        hp=99,
        damage=0,
        name="Slime Boss",
        monster_id="Slime_Boss",
    )
    preparing.max_hp = 140
    preparing.intent = Intent.UNKNOWN
    preparing.move_id = 1

    splitting = _monster(
        hp=15,
        damage=0,
        name="Acid Slime (L)",
        monster_id="Acid_Slime_L",
    )
    splitting.max_hp = 65
    splitting.intent = Intent.UNKNOWN
    splitting.move_id = 3

    game = _game(monsters=[preparing, splitting], act=2)

    assert CombatRLAgent._incoming_damage(game) == 0


def test_energy_guard_replaces_wasteful_end_turn_with_play_card():
    card = SimpleNamespace(is_playable=True, cost=1, has_target=True)
    game = _game(hand=[card], monsters=[_monster(hp=30, damage=8, index=0)])
    agent = _agent()

    assert agent._should_override_wasteful_end_turn(EndTurnAction(), game)
    replacement = agent._get_non_end_turn_fallback(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_energy_guard_targets_name_only_attack_without_has_target():
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
    )
    game = _game(hand=[strike], monsters=[_monster(hp=30, damage=8, index=0)])
    agent = _agent()

    replacement = agent._get_non_end_turn_fallback(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index == 0


def test_energy_guard_does_not_target_name_only_aoe_with_misleading_flag():
    cleave = SimpleNamespace(
        name="Cleave",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        hand=[cleave],
        monsters=[
            _monster(hp=30, damage=8, index=0),
            _monster(hp=30, damage=8, index=1),
        ],
    )
    agent = _agent()

    replacement = agent._get_non_end_turn_fallback(game)

    assert isinstance(replacement, PlayCardAction)
    assert replacement.card_index == 0
    assert replacement.target_index is None


def test_rl_playable_cards_parse_string_turn_cost():
    card = SimpleNamespace(is_playable=True, cost=3, cost_for_turn="2", has_target=True)
    game = _game(hand=[card], player=SimpleNamespace(energy=1))

    assert CombatRLAgent._playable_cards(game, energy=1) == []


def test_wasteful_end_turn_hands_rest_of_turn_to_fallback():
    card = SimpleNamespace(is_playable=True, cost=1, has_target=True)
    game = _game(hand=[card], monsters=[_monster(hp=30, damage=8, index=0)])
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return EndTurnAction()

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=fallback_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    first = agent.get_next_action_in_game(game)
    second = agent.get_next_action_in_game(game)

    assert isinstance(first, PlayCardAction)
    assert isinstance(second, PlayCardAction)
    assert calls == {"rl": 1, "fallback": 2}


def test_awakened_one_power_guard_replaces_rl_power_with_non_power_card():
    demon_form = SimpleNamespace(
        name="Demon Form",
        card_id="Demon Form",
        type=CardType.POWER,
        is_playable=True,
        cost=3,
        has_target=False,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        floor=50,
        turn=3,
        player=SimpleNamespace(energy=3),
        hand=[demon_form, strike],
        monsters=[
            _monster(
                hp=300,
                damage=18,
                index=0,
                name="Awakened One",
                monster_id="AwakenedOne",
            )
        ],
        room_type="MonsterRoomBoss",
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0


def test_awakened_one_power_guard_accepts_decimal_string_card_index():
    demon_form = SimpleNamespace(
        name="Demon Form",
        card_id="Demon Form",
        type=CardType.POWER,
        is_playable=True,
        cost=3,
        has_target=False,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        floor=50,
        turn=3,
        player=SimpleNamespace(energy=3),
        hand=[demon_form, strike],
        monsters=[
            _monster(
                hp=300,
                damage=18,
                index=0,
                name="Awakened One",
                monster_id="AwakenedOne",
            )
        ],
        room_type="MonsterRoomBoss",
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda _game: PlayCardAction(card_index="0.0")
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0


def test_awakened_one_power_guard_accepts_decimal_string_energy():
    demon_form = SimpleNamespace(
        name="Demon Form",
        card_id="Demon Form",
        type=CardType.POWER,
        is_playable=True,
        cost=3,
        has_target=False,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        floor=50,
        turn=3,
        player=SimpleNamespace(energy="3.0"),
        hand=[demon_form, strike],
        monsters=[
            _monster(
                hp=300,
                damage=18,
                index=0,
                name="Awakened One",
                monster_id="AwakenedOne",
            )
        ],
        room_type="MonsterRoomBoss",
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0


def test_havoc_guard_replaces_rl_havoc_with_safer_card():
    havoc = SimpleNamespace(
        name="Havoc",
        card_id="Havoc",
        type=CardType.SKILL,
        is_playable=True,
        cost=1,
        has_target=False,
    )
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        player=SimpleNamespace(energy=2),
        hand=[havoc, strike],
        monsters=[
            _monster(
                hp=72,
                damage=12,
                index=0,
                name="Shelled Parasite",
                monster_id="ShelledParasite",
            )
        ],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 1
    assert action.target_index == 0
    assert agent._fallback_turn_key == (5, 2)


def test_rl_action_log_names_returned_card(caplog):
    strike = SimpleNamespace(
        name="Strike",
        card_id="Strike_R",
        type=CardType.ATTACK,
        is_playable=True,
        cost=1,
        has_target=True,
    )
    game = _game(
        player=SimpleNamespace(energy=2),
        hand=[strike],
        monsters=[_monster(hp=30, damage=8, index=0)],
    )

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: PlayCardAction(card_index=0, target_index=0))
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    with caplog.at_level("INFO", logger="spirecomm.ai.rl.agent"):
        action = agent.get_next_action_in_game(game)

    assert isinstance(action, PlayCardAction)
    assert "card=Strike" in caplog.text
    assert "card_index=0" in caplog.text
    assert "target_index=0" in caplog.text
    assert "hand=[Strike]" in caplog.text


def test_card_reward_uses_fallback_even_when_in_combat_flag_is_stale():
    card = SimpleNamespace(name="Pommel Strike")
    fallback_action = CardRewardAction(card)
    agent = _agent()
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=lambda game: fallback_action
    )
    agent.rl_agent = SimpleNamespace(
        get_next_action_in_game=lambda game: CancelAction()
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = (1, str(ScreenType.CARD_REWARD), 1)
    agent._reward_screen_waited = True
    agent.reward_screen_wait = 0
    game = _game(
        screen_type=ScreenType.CARD_REWARD,
        in_combat=True,
        choice_available=True,
        choice_list=["Pommel Strike", "skip"],
        screen=SimpleNamespace(cards=[card], can_skip=True),
    )

    assert agent.get_next_action_in_game(game) is fallback_action


def test_in_combat_grid_screen_uses_fallback_not_rl():
    fallback_action = PlayCardAction(card_index=0)
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return CancelAction()

    def fallback_decide(_game):
        calls["fallback"] += 1
        return fallback_action

    agent = _agent()
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=fallback_decide,
        _track_game_state=lambda game: None,
    )
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0
    game = _game(
        screen_type=ScreenType.GRID,
        in_combat=True,
        choice_available=True,
        choice_list=["card 1", "card 2", "card 3"],
        screen=SimpleNamespace(cards=[], confirm_up=False),
    )

    assert agent.get_next_action_in_game(game) is fallback_action
    assert calls == {"rl": 0, "fallback": 1}


def test_main_combat_still_uses_rl_context():
    game = _game(screen_type=None, in_combat=True)

    assert _agent()._is_rl_context(game)


def test_finished_combat_stale_state_waits_instead_of_playing_card():
    card = SimpleNamespace(is_playable=True, cost=1, has_target=True)
    dead_monsters = [
        _monster(hp=0, index=0, name="Fungi Beast", monster_id="FungiBeast"),
        _monster(hp=0, index=1, name="Fungi Beast", monster_id="FungiBeast"),
    ]
    calls = {"rl": 0, "fallback": 0}

    def rl_decide(_game):
        calls["rl"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    def fallback_decide(_game):
        calls["fallback"] += 1
        return PlayCardAction(card_index=0, target_index=0)

    agent = _agent()
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=rl_decide)
    agent.fallback_agent = SimpleNamespace(
        get_next_action_in_game=fallback_decide,
        _track_game_state=lambda game: None,
    )
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = (5, 1)
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0
    game = _game(
        screen_type=None,
        in_combat=True,
        play_available=True,
        hand=[card],
        monsters=dead_monsters,
        floor=5,
        turn=1,
    )

    action = agent.get_next_action_in_game(game)

    assert isinstance(action, WaitAction)
    assert agent._fallback_turn_key is None
    assert calls == {"rl": 0, "fallback": 0}
