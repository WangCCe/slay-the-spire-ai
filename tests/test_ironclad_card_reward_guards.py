from types import SimpleNamespace

from spirecomm.ai.agent import OptimizedAgent
from spirecomm.ai.decision.base import DecisionContext
from spirecomm.ai.heuristics.ironclad_deck import IroncladDeckStrategy
from spirecomm.ai.heuristics.ironclad_evaluator import IroncladCardEvaluator
from spirecomm.ai.priorities import IroncladPriority
from spirecomm.communication.action import CancelAction, CardRewardAction


class _FakeTracker:
    def __init__(self):
        self.cards_obtained = []
        self.cards_skipped = 0
        self.card_choice_calls = []
        self.decision_calls = []

    def record_card_choice(self, **kwargs):
        self.card_choice_calls.append(kwargs)
        chosen = kwargs.get("chosen")
        if chosen:
            self.cards_obtained.append(chosen)
        else:
            self.cards_skipped += kwargs.get("skipped", 0)

    def record_decision(self, **kwargs):
        self.decision_calls.append(kwargs)


def _card(card_id, cost=1, upgrades=0):
    return SimpleNamespace(
        card_id=card_id,
        name=card_id,
        cost=cost,
        upgrades=upgrades,
        is_playable=True,
    )


def _relic(relic_id):
    return SimpleNamespace(relic_id=relic_id, name=relic_id)


def _agent_for_reward(
    reward_cards,
    deck,
    floor=10,
    hp=70,
    max_hp=80,
    act=1,
    act_boss=None,
    can_skip=True,
    can_bowl=False,
    in_combat=False,
    room_type="MonsterRoom",
    monsters=None,
    game_tracker=None,
):
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.card_evaluator = IroncladCardEvaluator()
    agent.deck_strategy = IroncladDeckStrategy()
    agent.priorities = IroncladPriority()
    agent.game_tracker = game_tracker
    agent.decision_history = []
    agent.skipped_cards = False
    agent.use_optimized_card_selection = True
    agent.game = SimpleNamespace(
        screen=SimpleNamespace(cards=reward_cards, can_skip=can_skip, can_bowl=can_bowl),
        in_combat=in_combat,
        deck=deck,
        current_hp=hp,
        max_hp=max_hp,
        floor=floor,
        act=act,
        act_boss=act_boss,
        room_type=room_type,
        turn=1,
        hand=[],
        monsters=monsters if monsters is not None else [],
        relics=[SimpleNamespace(relic_id="Burning Blood")],
        player=SimpleNamespace(energy=3, powers=[]),
    )
    return agent


def test_ironclad_boss_relic_selection_avoids_runic_dome_when_safe_options_exist():
    relics = [
        _relic("Runic Dome"),
        _relic("Empty Cage"),
        _relic("Pandora's Box"),
    ]

    best_relic = IroncladPriority().get_best_boss_relic(relics)

    assert best_relic.relic_id == "Empty Cage"


def test_ironclad_boss_relic_selection_avoids_crown_and_dripper_for_low_risk_option():
    relics = [
        _relic("Busted Crown"),
        _relic("Coffee Dripper"),
        _relic("Black Star"),
    ]

    best_relic = IroncladPriority().get_best_boss_relic(relics)

    assert best_relic.relic_id == "Black Star"


def test_ironclad_deck_quality_treats_none_upgrades_as_base_card():
    strategy = IroncladDeckStrategy()
    context = DecisionContext(
        SimpleNamespace(
            deck=[
                _card("Pommel Strike", upgrades=None),
                _card("Bash", upgrades=1),
            ]
        )
    )

    assert 0.0 <= strategy.get_deck_health_score(context) <= 1.0


def test_ironclad_strategy_rejects_hp_cost_card_at_string_low_hp():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
    ]
    agent = _agent_for_reward([], deck, hp=28, max_hp=80)
    context = DecisionContext(agent.game)
    context.player_hp_pct = "0.35"

    should_pick, reason = IroncladDeckStrategy().should_pick_card(
        _card("Offering", cost=0),
        context,
    )

    assert not should_pick
    assert "35% HP" in reason


def test_ironclad_strategy_can_take_carnage_despite_legacy_zero_copy_cap():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Pommel Strike"),
        _card("Headbutt"),
    ]
    reward_cards = [_card("Juggernaut", cost=2), _card("Carnage", cost=2), _card("Pommel Strike")]

    action = _agent_for_reward(reward_cards, deck, floor=10)._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Carnage"


def test_ironclad_strategy_can_take_power_through_despite_legacy_zero_copy_cap():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Pommel Strike"),
        _card("Headbutt"),
        _card("Bloodletting", cost=0),
        _card("Clothesline", cost=2),
    ]
    reward_cards = [_card("Wild Strike"), _card("Power Through")]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=14,
        hp=35,
        max_hp=80,
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Power Through"


def test_ironclad_strategy_prefers_shrug_when_act1_damage_is_already_covered():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Immolate", cost=2),
    ]
    reward_cards = [
        _card("Clothesline", cost=2),
        _card("Shrug It Off", cost=1),
        _card("Twin Strike", cost=1),
    ]

    action = _agent_for_reward(reward_cards, deck, floor=3)._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Shrug It Off"


def test_ironclad_strategy_prefers_flame_barrier_before_boss_when_block_is_thin():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Pommel Strike"),
        _card("Anger", cost=0),
        _card("Heavy Blade", cost=2),
    ]
    reward_cards = [
        _card("Heavy Blade", cost=2),
        _card("Flame Barrier", cost=2),
        _card("Cleave", cost=1),
    ]

    action = _agent_for_reward(reward_cards, deck, floor=10)._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Flame Barrier"


def test_ironclad_strategy_prefers_slime_boss_frontload_when_damage_is_thin():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R", upgrades=1),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Headbutt", upgrades=1),
        _card("Shrug It Off", upgrades=1),
        _card("Bloodletting", cost=0, upgrades=1),
    ]
    reward_cards = [
        _card("Flame Barrier", cost=2),
        _card("Heavy Blade", cost=2),
        _card("Metallicize", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=13,
        hp=74,
        max_hp=80,
        act_boss="Slime Boss",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Heavy Blade"


def test_ironclad_slime_boss_frontload_gap_counts_upgraded_damage_cards():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Pommel Strike+1", upgrades=1),
        _card("Anger+1", cost=0, upgrades=1),
        _card("Heavy Blade+1", cost=2, upgrades=1),
        _card("Cleave+1", upgrades=1),
    ]
    reward_cards = [
        _card("Heavy Blade", cost=2),
        _card("Flame Barrier", cost=2),
        _card("Metallicize", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=13,
        hp=74,
        max_hp=80,
        act_boss="Slime Boss",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Flame Barrier"


def test_ironclad_strategy_prefers_anger_over_unsupported_heavy_blade_for_slime_boss():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Anger", cost=0),
        _card("Armaments"),
    ]
    reward_cards = [
        _card("Heavy Blade", cost=2),
        _card("Anger", cost=0),
        _card("Dual Wield", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=3,
        hp=64,
        max_hp=80,
        act_boss="Slime Boss",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Anger"


def test_ironclad_strategy_prefers_spot_weakness_over_second_unsupported_heavy_blade():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Anger", cost=0),
        _card("Armaments"),
        _card("Heavy Blade", cost=2),
        _card("Sever Soul", cost=2),
    ]
    reward_cards = [
        _card("Heavy Blade", cost=2),
        _card("Spot Weakness", cost=1),
        _card("Warcry", cost=0),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=7,
        hp=64,
        max_hp=80,
        act_boss="Slime Boss",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Spot Weakness"


def test_ironclad_strategy_prefers_fiend_fire_over_unsupported_heavy_blade():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Heavy Blade", cost=2),
        _card("Thunderclap"),
        _card("Armaments"),
    ]
    reward_cards = [
        _card("Heavy Blade", cost=2),
        _card("Fiend Fire", cost=2),
        _card("Wild Strike"),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=4,
        hp=64,
        max_hp=80,
        act_boss="The Guardian",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Fiend Fire"


def test_ironclad_strategy_prefers_inflame_support_over_attack_with_heavy_blade():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Heavy Blade", cost=2),
    ]
    reward_cards = [
        _card("Thunderclap"),
        _card("Clash", cost=0),
        _card("Inflame", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=2,
        hp=64,
        max_hp=80,
        act_boss="The Guardian",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Inflame"


def test_ironclad_strategy_prefers_frontload_over_unsupported_havoc():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
    ]
    reward_cards = [
        _card("Havoc"),
        _card("Cleave"),
        _card("Wild Strike"),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=1,
        hp=73,
        max_hp=80,
        act_boss="Hexaghost",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Cleave"


def test_ironclad_strategy_prefers_foundation_block_over_neow_havoc():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
    ]
    reward_cards = [
        _card("Havoc"),
        _card("Iron Wave"),
        _card("Warcry", cost=0),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=0,
        hp=80,
        max_hp=80,
        act_boss="The Guardian",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Iron Wave"


def test_ironclad_strategy_prefers_combust_over_unsupported_havoc():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
    ]
    reward_cards = [
        _card("Combust", cost=1),
        _card("Havoc"),
        _card("Infernal Blade", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=1,
        hp=70,
        max_hp=80,
        act_boss="Slime Boss",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Combust"


def test_ironclad_strategy_skips_duplicate_havoc_in_large_act1_deck():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Good Instincts", cost=0, upgrades=1),
        _card("Intimidate", cost=0),
        _card("Hemokinesis", upgrades=1),
        _card("Whirlwind", cost=-1),
        _card("Havoc", upgrades=1),
        _card("Anger", cost=0),
        _card("Twin Strike"),
        _card("True Grit"),
        _card("Fiend Fire", cost=2, upgrades=1),
    ]
    reward_cards = [
        _card("Searing Blow", cost=2),
        _card("Havoc"),
        _card("Flex", cost=0),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=14,
        hp=48,
        max_hp=80,
        act_boss="Slime Boss",
    )._choose_card_reward_optimized()

    assert isinstance(action, CancelAction)


def test_ironclad_strategy_prefers_immolate_over_anger_before_guardian():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Swift Strike", cost=0, upgrades=1),
        _card("Clothesline", cost=2),
        _card("Whirlwind", cost=-1),
        _card("Shrug It Off", upgrades=1),
        _card("Uppercut", cost=2),
    ]
    reward_cards = [
        _card("Thunderclap"),
        _card("Immolate", cost=2),
        _card("Anger", cost=0),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=7,
        hp=58,
        max_hp=80,
        act_boss="The Guardian",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Immolate"


def test_ironclad_strategy_prefers_power_through_for_guardian_survival_gap():
    deck = [
        _card("Strike_R", upgrades=1),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Armaments"),
        _card("Shockwave", cost=2, upgrades=1),
        _card("Anger", cost=0),
        _card("Clothesline", cost=2),
        _card("Anger", cost=0, upgrades=1),
    ]
    reward_cards = [
        _card("Power Through", cost=1),
        _card("Intimidate", cost=0),
        _card("Sever Soul", cost=2),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=14,
        hp=57,
        max_hp=80,
        act_boss="The Guardian",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Power Through"


def test_ironclad_strategy_prefers_power_through_over_supported_havoc_before_guardian():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R", upgrades=1),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Anger", cost=0),
        _card("Second Wind", upgrades=1),
        _card("True Grit"),
        _card("Armaments"),
        _card("Headbutt"),
    ]
    reward_cards = [
        _card("Havoc"),
        _card("Power Through"),
        _card("Hemokinesis", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=8,
        hp=55,
        max_hp=94,
        act_boss="The Guardian",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Power Through"


def test_ironclad_strategy_prefers_power_through_over_duplicate_twin_strike_for_slime_boss():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Twin Strike"),
        _card("Shockwave", cost=2, upgrades=1),
        _card("Blood for Blood", cost=4),
        _card("Flex", cost=0),
        _card("Heavy Blade", cost=2),
    ]
    reward_cards = [
        _card("Armaments"),
        _card("Power Through"),
        _card("Twin Strike"),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=6,
        hp=54,
        max_hp=80,
        act_boss="Slime Boss",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Power Through"


def test_ironclad_strategy_rejects_perfected_strike_when_strike_density_is_low():
    deck = [
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Reaper", cost=2, upgrades=1),
        _card("Havoc", upgrades=1),
        _card("Whirlwind", cost=-1),
        _card("Cleave"),
        _card("Shrug It Off"),
    ]
    agent = _agent_for_reward([_card("Perfected Strike", cost=2)], deck, floor=11)
    context = DecisionContext(agent.game)

    should_pick, reason = IroncladDeckStrategy().should_pick_card(
        _card("Perfected Strike", cost=2),
        context,
    )

    assert not should_pick
    assert "Strike" in reason


def test_ironclad_strategy_rejects_counted_upgraded_perfected_strike():
    deck = [
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Reaper", cost=2, upgrades=1),
        _card("Whirlwind", cost=-1),
    ]
    agent = _agent_for_reward([_card("Perfected Strike+1", cost=2, upgrades=1)], deck, floor=11)
    context = DecisionContext(agent.game)

    should_pick, reason = IroncladDeckStrategy().should_pick_card(
        _card("Perfected Strike+1", cost=2, upgrades=1),
        context,
    )

    assert not should_pick
    assert "Perfected Strike" in reason


def test_ironclad_strategy_still_removes_starter_strikes_after_name_normalization():
    deck = [_card("Strike_R"), _card("Strike_R"), _card("Defend_R"), _card("Bash", cost=2)]
    agent = _agent_for_reward([], deck, floor=8)
    context = DecisionContext(agent.game)

    should_remove, reason = IroncladDeckStrategy().should_remove_card(_card("Strike_R"), context)

    assert should_remove
    assert "Strike" in reason


def test_ironclad_strategy_uses_basic_card_upgrade_priorities_after_name_normalization():
    deck = [_card("Strike_R"), _card("Defend_R"), _card("Bash", cost=2)]
    agent = _agent_for_reward([], deck, floor=8)
    context = DecisionContext(agent.game)
    strategy = IroncladDeckStrategy()

    assert strategy.get_upgrade_priority(_card("Strike_R"), context) == 3
    assert strategy.get_upgrade_priority(_card("Defend_R"), context) == 2


def test_ironclad_strategy_rejects_perfected_strike_even_with_starter_strikes():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Armaments"),
    ]
    agent = _agent_for_reward([_card("Perfected Strike", cost=2)], deck, floor=5)
    context = DecisionContext(agent.game)

    should_pick, reason = IroncladDeckStrategy().should_pick_card(
        _card("Perfected Strike", cost=2),
        context,
    )

    assert not should_pick
    assert "Perfected Strike" in reason


def test_ironclad_strategy_skips_duplicate_perfected_strike_when_alternatives_are_bad():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Headbutt"),
        _card("Perfected Strike", cost=2),
    ]
    reward_cards = [
        _card("Perfected Strike", cost=2),
        _card("Wild Strike"),
        _card("Clash", cost=0),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=8,
        hp=64,
        max_hp=80,
    )._choose_card_reward_optimized()

    assert isinstance(action, CancelAction)


def test_ironclad_strategy_takes_wild_strike_when_act1_frontload_is_empty():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Armaments"),
        _card("Spot Weakness"),
    ]
    reward_cards = [
        _card("Wild Strike"),
        _card("Clash", cost=0),
        _card("Rupture", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=5,
        hp=69,
        max_hp=80,
        act_boss="The Guardian",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Wild Strike"


def test_ironclad_strategy_skips_fire_breathing_without_status_support():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
    ]
    reward_cards = [
        _card("Fire Breathing", cost=1),
        _card("Entrench", cost=2),
        _card("Dark Embrace", cost=2),
    ]

    action = _agent_for_reward(reward_cards, deck, floor=1)._choose_card_reward_optimized()

    assert isinstance(action, CancelAction)


def test_power_potion_generated_choice_is_not_recorded_as_deck_reward():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Anger", cost=0),
        _card("Havoc"),
    ]
    reward_cards = [
        _card("Inflame", cost=1),
        _card("Rupture", cost=1),
        _card("Combust", cost=1),
    ]
    tracker = _FakeTracker()
    live_monsters = [
        SimpleNamespace(current_hp=20, is_gone=False, half_dead=False),
    ]
    agent = _agent_for_reward(
        reward_cards,
        deck,
        can_skip=False,
        in_combat=False,
        room_type="MonsterRoom",
        monsters=live_monsters,
        game_tracker=tracker,
    )

    action = agent.choose_card_reward()

    assert isinstance(action, CardRewardAction)
    assert tracker.card_choice_calls == []
    assert tracker.cards_obtained == []


def test_generated_combat_card_choice_cannot_skip_when_deck_is_large():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Shrug It Off"),
        _card("True Grit"),
        _card("Iron Wave"),
        _card("Thunderclap"),
        _card("Anger", cost=0),
        _card("Battle Trance", cost=0),
        _card("Flex", cost=0),
        _card("Headbutt"),
        _card("Clothesline", cost=2),
        _card("Cleave"),
        _card("Discovery", cost=1, upgrades=1),
        _card("Fiend Fire", cost=2, upgrades=1),
        _card("Swift Strike", cost=0),
    ]
    reward_cards = [
        _card("Rampage", cost=1),
        _card("Limit Break", cost=1),
        _card("Bludgeon", cost=3),
    ]
    tracker = _FakeTracker()
    live_monsters = [
        SimpleNamespace(current_hp=298, is_gone=False, half_dead=False),
    ]
    agent = _agent_for_reward(
        reward_cards,
        deck,
        floor=33,
        act=3,
        can_skip=False,
        in_combat=False,
        room_type="MonsterRoom",
        monsters=live_monsters,
        game_tracker=tracker,
    )

    action = agent.choose_card_reward()

    assert isinstance(action, CardRewardAction)
    assert action.name in {"Rampage", "Limit Break", "Bludgeon"}
    assert tracker.card_choice_calls == []


def test_ironclad_strategy_prefers_thunderclap_over_second_brutality_before_boss():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Brutality", cost=0, upgrades=1),
        _card("Whirlwind"),
        _card("True Grit", upgrades=1),
    ]
    reward_cards = [
        _card("Brutality", cost=0),
        _card("Thunderclap", cost=1),
        _card("Dual Wield", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=13,
        hp=55,
        max_hp=80,
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Thunderclap"


def test_ironclad_strategy_prefers_immolate_over_armaments_before_act1_boss():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Bandage Up", cost=0),
        _card("Havoc", cost=0, upgrades=1),
        _card("Thunderclap"),
        _card("Thunderclap"),
        _card("Ghostly Armor", cost=1),
        _card("Shrug It Off", upgrades=1),
        _card("Shrug It Off"),
    ]
    reward_cards = [
        _card("Immolate", cost=2),
        _card("Armaments", cost=1),
        _card("Anger", cost=0),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=14,
        hp=34,
        max_hp=80,
        act_boss="Hexaghost",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Immolate"


def test_ironclad_strategy_prefers_feed_over_duplicate_demon_form_after_act1_boss():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Intimidate", cost=0),
        _card("Anger", cost=0),
        _card("Clothesline", cost=2),
        _card("Demon Form", cost=3),
        _card("Carnage", cost=2),
        _card("Armaments"),
        _card("Rage", cost=0),
        _card("Uppercut", cost=2),
    ]
    reward_cards = [
        _card("Demon Form", cost=3),
        _card("Brutality", cost=0),
        _card("Feed", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=16,
        act=1,
        hp=24,
        max_hp=80,
        act_boss="Hexaghost",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Feed"


def test_ironclad_strategy_prefers_frontload_over_early_rage_before_act1_boss():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Intimidate", cost=0),
        _card("Anger", cost=0),
        _card("Clothesline", cost=2),
        _card("Demon Form", cost=3),
        _card("Carnage", cost=2),
        _card("Armaments"),
    ]
    reward_cards = [
        _card("Rage", cost=0),
        _card("Heavy Blade", cost=2),
        _card("Twin Strike", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=8,
        act=1,
        hp=54,
        max_hp=80,
        act_boss="Hexaghost",
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name in {"Heavy Blade", "Twin Strike"}


def test_ironclad_evaluator_treats_counted_upgraded_immolate_as_immolate():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
    ]
    agent = _agent_for_reward([], deck, floor=5)
    context = DecisionContext(agent.game)
    evaluator = IroncladCardEvaluator()

    immolate_score = evaluator.evaluate_card(_card("Immolate", cost=2), context)
    counted_score = evaluator.evaluate_card(_card("Immolate+1", cost=2, upgrades=1), context)

    assert counted_score == immolate_score


def test_ironclad_evaluator_hp_modifier_accepts_string_hp_pct():
    evaluator = IroncladCardEvaluator()
    context = SimpleNamespace(player_hp_pct="0.2")

    assert evaluator._calculate_hp_aware_modifier(_card("Offering", cost=0), context) == 0.1


def test_ironclad_evaluator_archetype_bonus_accepts_string_archetype_score():
    evaluator = IroncladCardEvaluator()
    card = _card("Cleave", cost=1)
    enum_context = SimpleNamespace(deck_archetype="strength", archetype_score=0.6)
    string_context = SimpleNamespace(deck_archetype="strength", archetype_score="0.6")

    try:
        string_bonus = evaluator._calculate_archetype_bonus(card, string_context)
    except TypeError:
        string_bonus = "type-error"

    assert string_bonus == evaluator._calculate_archetype_bonus(card, enum_context)


def test_ironclad_evaluator_act_1_bonus_accepts_string_act():
    evaluator = IroncladCardEvaluator()
    deck = [_card("Strike_R"), _card("Strike_R"), _card("Defend_R"), _card("Defend_R"), _card("Bash", cost=2)]
    enum_context = SimpleNamespace(game=SimpleNamespace(deck=deck), act=1, floor=5)
    string_context = SimpleNamespace(game=SimpleNamespace(deck=deck), act="1", floor=5)

    assert (
        evaluator._calculate_act_1_bonus(_card("Pommel Strike", cost=1), string_context)
        == evaluator._calculate_act_1_bonus(_card("Pommel Strike", cost=1), enum_context)
    )


def test_ironclad_evaluator_act_1_bonus_accepts_string_floor():
    evaluator = IroncladCardEvaluator()
    deck = [_card("Strike_R") for _ in range(14)]
    enum_context = SimpleNamespace(game=SimpleNamespace(deck=deck), act=1, floor=5)
    string_context = SimpleNamespace(game=SimpleNamespace(deck=deck), act=1, floor="5")

    try:
        string_bonus = evaluator._calculate_act_1_bonus(_card("Pommel Strike", cost=1), string_context)
    except TypeError:
        string_bonus = "type-error"

    assert string_bonus == evaluator._calculate_act_1_bonus(_card("Pommel Strike", cost=1), enum_context)


def test_ironclad_evaluator_survival_gap_accepts_string_act_and_floor():
    evaluator = IroncladCardEvaluator()
    deck = [_card("Strike_R"), _card("Strike_R"), _card("Defend_R"), _card("Defend_R"), _card("Bash", cost=2)]
    enum_context = SimpleNamespace(game=SimpleNamespace(deck=deck), act=1, floor=4)
    string_context = SimpleNamespace(game=SimpleNamespace(deck=deck), act="1", floor="4")

    assert evaluator._act_1_survival_gap(string_context) == evaluator._act_1_survival_gap(enum_context)


def test_ironclad_energy_curve_survival_floor_accepts_string_act():
    evaluator = IroncladCardEvaluator()
    deck = [_card("Pommel Strike", cost=1) for _ in range(10)]
    enum_context = SimpleNamespace(game=SimpleNamespace(deck=deck), act=1, floor=5)
    string_context = SimpleNamespace(game=SimpleNamespace(deck=deck), act="1", floor=5)

    assert (
        evaluator._evaluate_energy_curve(_card("Shrug It Off", cost=1), string_context)
        == evaluator._evaluate_energy_curve(_card("Shrug It Off", cost=1), enum_context)
    )


def test_ironclad_energy_curve_parses_string_card_costs():
    deck = [_card("Strike_R", cost=1) for _ in range(10)]
    context = DecisionContext(SimpleNamespace(deck=deck, act=1))
    evaluator = IroncladCardEvaluator()

    int_modifier = evaluator._evaluate_energy_curve(_card("Pommel Strike", cost=1), context)
    string_modifier = evaluator._evaluate_energy_curve(_card("Pommel Strike", cost="1"), context)

    assert string_modifier == int_modifier


def test_large_deck_reward_keeps_strategy_good_card_despite_energy_curve_penalty():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Shrug It Off"),
        _card("Shrug It Off"),
        _card("True Grit"),
        _card("Iron Wave"),
        _card("Thunderclap"),
        _card("Anger", cost=0),
        _card("Battle Trance", cost=0),
        _card("Flex", cost=0),
        _card("Headbutt"),
        _card("Clothesline", cost=2),
        _card("Cleave"),
    ]
    reward_cards = [
        _card("Entrench", cost=2),
        _card("Intimidate", cost=0),
        _card("Pommel Strike", cost=1),
    ]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=19,
        act=2,
        hp=50,
        max_hp=80,
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Pommel Strike"


def test_large_deck_reward_does_not_skip_strategy_good_card():
    deck = [
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Defend_R"),
        _card("Bash", cost=2),
        _card("Shrug It Off"),
        _card("True Grit"),
        _card("Iron Wave"),
        _card("Thunderclap"),
        _card("Anger", cost=0),
        _card("Battle Trance", cost=0),
        _card("Flex", cost=0),
        _card("Headbutt"),
        _card("Clothesline", cost=2),
        _card("Cleave"),
        _card("Armaments"),
    ]
    reward_cards = [_card("Pommel Strike", cost=1)]

    action = _agent_for_reward(
        reward_cards,
        deck,
        floor=19,
        act=2,
        hp=50,
        max_hp=80,
    )._choose_card_reward_optimized()

    assert isinstance(action, CardRewardAction)
    assert action.name == "Pommel Strike"
