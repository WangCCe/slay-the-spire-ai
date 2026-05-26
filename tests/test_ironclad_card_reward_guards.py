from types import SimpleNamespace

from spirecomm.ai.agent import OptimizedAgent
from spirecomm.ai.heuristics.ironclad_deck import IroncladDeckStrategy
from spirecomm.ai.heuristics.ironclad_evaluator import IroncladCardEvaluator
from spirecomm.ai.priorities import IroncladPriority
from spirecomm.communication.action import CancelAction, CardRewardAction


def _card(card_id, cost=1, upgrades=0):
    return SimpleNamespace(
        card_id=card_id,
        name=card_id,
        cost=cost,
        upgrades=upgrades,
        is_playable=True,
    )


def _agent_for_reward(
    reward_cards,
    deck,
    floor=10,
    hp=70,
    max_hp=80,
    act=1,
    act_boss=None,
):
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.card_evaluator = IroncladCardEvaluator()
    agent.deck_strategy = IroncladDeckStrategy()
    agent.priorities = IroncladPriority()
    agent.game_tracker = None
    agent.decision_history = []
    agent.skipped_cards = False
    agent.game = SimpleNamespace(
        screen=SimpleNamespace(cards=reward_cards, can_skip=True, can_bowl=False),
        in_combat=False,
        deck=deck,
        current_hp=hp,
        max_hp=max_hp,
        floor=floor,
        act=act,
        act_boss=act_boss,
        turn=1,
        hand=[],
        monsters=[],
        relics=[SimpleNamespace(relic_id="Burning Blood")],
        player=SimpleNamespace(energy=3, powers=[]),
    )
    return agent


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
