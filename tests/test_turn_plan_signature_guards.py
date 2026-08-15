from types import SimpleNamespace

from spirecomm.ai.agent import OptimizedAgent, SimpleAgent, TurnPlanSignature
from spirecomm.communication.action import EndTurnAction, PlayCardAction
from spirecomm.spire.character import Intent


def _card(card_id, name, uuid=None, cost=1, cost_for_turn=None, upgrades=0, is_playable=True):
    return SimpleNamespace(
        card_id=card_id,
        name=name,
        uuid=uuid,
        cost=cost,
        cost_for_turn=cost if cost_for_turn is None else cost_for_turn,
        upgrades=upgrades,
        is_playable=is_playable,
    )


def _power(power_id, amount):
    return SimpleNamespace(power_id=power_id, power_name=power_id, name=power_id, amount=amount)


def _potion(
    potion_id="Strength Potion",
    name="Strength Potion",
    can_use=True,
    can_discard=True,
    requires_target=False,
    effect_type="buff_strength",
    effect_value=2,
    target_type="self",
):
    return SimpleNamespace(
        potion_id=potion_id,
        name=name,
        can_use=can_use,
        can_discard=can_discard,
        requires_target=requires_target,
        effect_type=effect_type,
        effect_value=effect_value,
        target_type=target_type,
    )


def _monster(
    name="Cultist",
    monster_id="Cultist",
    move_adjusted_damage=12,
    move_hits=1,
    powers=None,
):
    return SimpleNamespace(
        name=name,
        monster_id=monster_id,
        current_hp=40,
        block=0,
        intent=Intent.ATTACK,
        move_adjusted_damage=move_adjusted_damage,
        move_hits=move_hits,
        is_gone=False,
        half_dead=False,
        powers=powers or [],
    )


def _game(hand, monster=None, current_hp=70, block=0, powers=None, potions=None):
    return SimpleNamespace(
        hand=hand,
        current_hp=current_hp,
        player=SimpleNamespace(energy=3, block=block, powers=powers or []),
        monsters=[monster or _monster()],
        potions=potions or [],
    )


def test_turn_plan_signature_distinguishes_cards_when_uuid_is_missing():
    strike_signature = TurnPlanSignature(_game([_card("Strike_R", "Strike")]))
    defend_signature = TurnPlanSignature(_game([_card("Defend_R", "Defend")]))

    assert strike_signature.hand_cards != defend_signature.hand_cards
    assert strike_signature != defend_signature


def test_turn_plan_signature_distinguishes_live_monster_damage_changes():
    weaker_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], monster=_monster(move_adjusted_damage=8))
    )
    stronger_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], monster=_monster(move_adjusted_damage=18))
    )
    multi_hit_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], monster=_monster(move_adjusted_damage=8, move_hits=2))
    )

    assert weaker_signature.monster_signature != stronger_signature.monster_signature
    assert weaker_signature.monster_signature != multi_hit_signature.monster_signature
    assert weaker_signature != stronger_signature
    assert weaker_signature != multi_hit_signature


def test_turn_plan_signature_distinguishes_live_monster_identity_changes():
    cultist_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], monster=_monster(name="Cultist", monster_id="Cultist"))
    )
    louse_signature = TurnPlanSignature(
        _game(
            [_card("Strike_R", "Strike")],
            monster=_monster(name="Louse", monster_id="FuzzyLouseNormal"),
        )
    )

    assert cultist_signature.monster_signature != louse_signature.monster_signature
    assert cultist_signature != louse_signature


def test_turn_plan_signature_distinguishes_player_hp_and_block_changes():
    healthy_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=70, block=0)
    )
    wounded_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=12, block=0)
    )
    blocked_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=70, block=18)
    )

    assert healthy_signature != wounded_signature
    assert healthy_signature != blocked_signature


def test_should_replan_when_player_hp_or_block_changes():
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.current_plan_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=70, block=0)
    )

    wounded_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=12, block=0)
    )
    blocked_signature = TurnPlanSignature(
        _game([_card("Defend_R", "Defend")], current_hp=70, block=18)
    )

    assert agent.should_replan(wounded_signature)
    assert agent.should_replan(blocked_signature)


def test_turn_plan_signature_distinguishes_player_power_changes():
    no_strength_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], powers=[])
    )
    strength_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], powers=[_power("Strength", 2)])
    )

    assert no_strength_signature != strength_signature


def test_turn_plan_signature_prefers_protocol_power_id_over_display_name():
    localized_signature = TurnPlanSignature(
        _game(
            [_card("Strike_R", "Strike")],
            powers=[
                SimpleNamespace(
                    power_id="Strength",
                    power_name="Strength Display",
                    name="Localized Strength",
                    amount=2,
                )
            ],
        )
    )
    renamed_signature = TurnPlanSignature(
        _game(
            [_card("Strike_R", "Strike")],
            powers=[
                SimpleNamespace(
                    power_id="Strength",
                    power_name="Alternate Display",
                    name="Renamed Strength",
                    amount=2,
                )
            ],
        )
    )

    assert localized_signature.player_powers == (("Strength", 2),)
    assert localized_signature == renamed_signature


def test_turn_plan_signature_handles_power_without_identifier():
    signature = TurnPlanSignature(
        _game(
            [_card("Strike_R", "Strike")],
            powers=[SimpleNamespace(amount=1), _power("Strength", 2)],
        )
    )

    assert set(signature.player_powers) == {(None, 1), ("Strength", 2)}


def test_turn_plan_signature_distinguishes_monster_power_changes():
    normal_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], monster=_monster(powers=[]))
    )
    weak_signature = TurnPlanSignature(
        _game(
            [_card("Strike_R", "Strike")],
            monster=_monster(powers=[_power("Weak", 2)]),
        )
    )

    assert normal_signature != weak_signature


def test_turn_plan_signature_distinguishes_hand_card_cost_and_upgrade_changes():
    base_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", cost=1, cost_for_turn=1)])
    )
    discounted_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", cost=1, cost_for_turn=0)])
    )
    upgraded_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", cost=1, cost_for_turn=1, upgrades=1)])
    )

    assert base_signature != discounted_signature
    assert base_signature != upgraded_signature


def test_turn_plan_signature_infers_upgrade_changes_from_card_suffix():
    base_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", cost=1, cost_for_turn=1)])
    )
    suffix_upgraded_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike+1", uuid="strike-1", cost=1, cost_for_turn=1)])
    )

    assert base_signature != suffix_upgraded_signature


def test_turn_plan_signature_distinguishes_hand_card_playability_changes():
    playable_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", is_playable=True)])
    )
    unplayable_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike", uuid="strike-1", is_playable=False)])
    )

    assert playable_signature != unplayable_signature


def test_turn_plan_signature_distinguishes_potion_inventory_changes():
    available_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], potions=[_potion()])
    )
    empty_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], potions=[])
    )
    spent_signature = TurnPlanSignature(
        _game(
            [_card("Strike_R", "Strike")],
            potions=[_potion(potion_id="Potion Slot", name="Potion Slot", can_use=False)],
        )
    )

    assert available_signature != empty_signature
    assert available_signature != spent_signature


def test_turn_plan_signature_distinguishes_string_potion_inventory_changes():
    fire_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], potions=["Fire Potion"])
    )
    empty_slot_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], potions=["Potion Slot"])
    )

    assert fire_signature != empty_slot_signature


def test_turn_plan_signature_uses_get_real_potions_without_raw_potions():
    game_with_potion = _game([_card("Strike_R", "Strike")])
    del game_with_potion.potions
    game_with_potion.get_real_potions = lambda: [_potion()]

    available_signature = TurnPlanSignature(game_with_potion)
    empty_signature = TurnPlanSignature(_game([_card("Strike_R", "Strike")], potions=[]))

    assert available_signature != empty_signature


def test_should_replan_when_potion_inventory_changes():
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.current_plan_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], potions=[_potion()])
    )

    empty_signature = TurnPlanSignature(
        _game([_card("Strike_R", "Strike")], potions=[])
    )
    spent_signature = TurnPlanSignature(
        _game(
            [_card("Strike_R", "Strike")],
            potions=[_potion(potion_id="Potion Slot", name="Potion Slot", can_use=False)],
        )
    )

    assert agent.should_replan(empty_signature)
    assert agent.should_replan(spent_signature)


def test_optimized_agent_continues_cached_sequence_after_played_card_leaves_hand(monkeypatch):
    first_card = _card("Heavy Blade", "Heavy Blade", uuid="heavy-blade", cost=2)
    second_card = _card("Offering", "Offering", uuid="offering", cost=0)
    first_action = PlayCardAction(card=first_card)
    second_action = PlayCardAction(card=second_card)
    planned_context = SimpleNamespace(act=1, threat_category=None, turn=3, floor=14)

    class FixedPlanner:
        last_plan_kind = "lethal"

        def __init__(self):
            self.calls = 0

        def plan_turn(self, _context):
            self.calls += 1
            return [first_action, second_action]

    monkeypatch.setattr("spirecomm.ai.agent.DecisionContext", lambda _game: planned_context)
    monkeypatch.setattr(
        "spirecomm.ai.heuristics.simulation.select_combat_mode_with_monster_data",
        lambda _context: "test-mode",
    )

    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = _game([first_card, second_card])
    agent.game.play_available = True
    agent.current_action_sequence = []
    agent.current_action_index = 0
    agent.current_plan_signature = None
    agent.current_plan_kind = None
    agent.replan_count_this_turn = 0
    agent._current_combat_mode = "test-mode"
    agent.combat_planner = FixedPlanner()
    agent.game_tracker = None
    agent.decision_history = []
    agent.player_class = "IRONCLAD"

    first = agent._get_optimized_play_card_action()
    assert first is first_action
    assert agent.current_plan_kind == "lethal"
    assert agent.is_active_lethal_plan_action(first) is True

    agent.game = _game([second_card])
    agent.game.play_available = True
    second = agent._get_optimized_play_card_action()

    assert second is second_action
    assert agent.is_active_lethal_plan_action(second) is True
    assert agent.combat_planner.calls == 1


def test_optimized_agent_replans_when_cached_card_is_no_longer_playable(monkeypatch):
    first_card = _card("Bloodletting", "Bloodletting", uuid="bloodletting", cost=0)
    planned_strike = _card("Strike_R", "Strike", uuid="strike", cost=1)
    fallback = _card("Defend_R", "Defend", uuid="defend", cost=1)
    first_action = PlayCardAction(card=first_card)
    stale_action = PlayCardAction(card=planned_strike)
    fallback_action = PlayCardAction(card=fallback)
    planned_context = SimpleNamespace(act=1, threat_category=None, turn=3, floor=14)

    class FixedPlanner:
        last_plan_kind = None

        def __init__(self):
            self.calls = 0

        def plan_turn(self, _context):
            self.calls += 1
            if self.calls == 1:
                return [first_action, stale_action]
            return [fallback_action]

    monkeypatch.setattr("spirecomm.ai.agent.DecisionContext", lambda _game: planned_context)
    monkeypatch.setattr(
        "spirecomm.ai.heuristics.simulation.select_combat_mode_with_monster_data",
        lambda _context: "test-mode",
    )

    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = _game([first_card, planned_strike])
    agent.game.play_available = True
    agent.current_action_sequence = []
    agent.current_action_index = 0
    agent.current_plan_signature = None
    agent.current_plan_kind = None
    agent.replan_count_this_turn = 0
    agent._current_combat_mode = "test-mode"
    agent.combat_planner = FixedPlanner()
    agent.game_tracker = None
    agent.decision_history = []
    agent.player_class = "IRONCLAD"

    assert agent._get_optimized_play_card_action() is first_action

    unplayable_strike = _card(
        "Strike_R", "Strike", uuid="strike", cost=1, is_playable=False
    )
    agent.game = _game([unplayable_strike, fallback])
    agent.game.play_available = True

    action = agent._get_optimized_play_card_action()

    assert action is fallback_action
    assert action is not stale_action
    assert agent.combat_planner.calls == 2


def test_optimized_agent_clear_current_combat_plan_clears_provenance():
    action = PlayCardAction(card=_card("Strike_R", "Strike", uuid="strike"))
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.current_action_sequence = [action]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = "lethal"

    agent._clear_current_combat_plan()

    assert agent.current_action_sequence == []
    assert agent.current_action_index == 0
    assert agent.current_plan_signature is None
    assert agent.current_plan_kind is None
    assert agent.is_active_lethal_plan_action(action) is False


def test_optimized_agent_invalidates_only_emitted_active_lethal_action():
    emitted = PlayCardAction(card=_card("Strike_R", "Strike", uuid="emitted"))
    other = PlayCardAction(card=_card("Defend_R", "Defend", uuid="other"))
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.current_action_sequence = [emitted, other]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = "lethal"

    assert agent.invalidate_active_lethal_plan_action(other) is False
    assert agent.current_plan_kind == "lethal"
    assert agent.current_action_sequence == [emitted, other]

    assert agent.invalidate_active_lethal_plan_action(emitted) is True
    assert agent.current_action_sequence == []
    assert agent.current_action_index == 0
    assert agent.current_plan_signature is None
    assert agent.current_plan_kind is None


def test_optimized_agent_generic_active_plan_action_rejection():
    emitted = PlayCardAction(card=_card("Strike_R", "Strike", uuid="emitted"))
    followup = PlayCardAction(card=_card("Defend_R", "Defend", uuid="followup"))
    unrelated = PlayCardAction(card=_card("Bash", "Bash", uuid="unrelated"))
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.current_action_sequence = [emitted, followup]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = None

    assert agent.is_active_plan_action(emitted) is True
    assert agent.active_plan_kind_for_action(emitted) is None
    assert agent.reject_active_plan_action(unrelated) is False
    assert agent.current_action_sequence == [emitted, followup]

    assert agent.reject_active_plan_action(emitted) is True
    assert agent.current_action_sequence == []
    assert agent.current_action_index == 0
    assert agent.current_plan_signature is None
    assert agent.current_plan_kind is None


def test_optimized_agent_lethal_compatibility_wraps_generic_plan_contract():
    emitted = PlayCardAction(card=_card("Strike_R", "Strike", uuid="lethal"))
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.current_action_sequence = [emitted]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = "lethal"

    assert agent.active_plan_kind_for_action(emitted) == "lethal"
    assert agent.is_active_lethal_plan_action(emitted) is True
    assert agent.invalidate_active_lethal_plan_action(emitted) is True
    assert agent.current_action_sequence == []


def test_optimized_agent_clears_lethal_provenance_before_stale_replan(monkeypatch):
    stale_card = _card("Strike_R", "Strike", uuid="stale-strike")
    live_card = _card("Defend_R", "Defend", uuid="live-defend")
    stale_action = PlayCardAction(card=stale_card)
    live_action = PlayCardAction(card=live_card)
    planned_context = SimpleNamespace(act=1, threat_category=None, turn=3, floor=14)

    class FixedPlanner:
        last_plan_kind = None

        def plan_turn(self, _context):
            return [live_action]

    monkeypatch.setattr("spirecomm.ai.agent.DecisionContext", lambda _game: planned_context)
    monkeypatch.setattr(
        "spirecomm.ai.heuristics.simulation.select_combat_mode_with_monster_data",
        lambda _context: "test-mode",
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = _game([live_card])
    agent.game.play_available = True
    agent.current_action_sequence = [stale_action]
    agent.current_action_index = 0
    agent.current_plan_signature = None
    agent.current_plan_kind = "lethal"
    agent.replan_count_this_turn = 0
    agent._current_combat_mode = "test-mode"
    agent.combat_planner = FixedPlanner()
    agent.game_tracker = None
    agent.decision_history = []
    agent.player_class = "IRONCLAD"

    action = agent._get_optimized_play_card_action()

    assert action is live_action
    assert agent.current_plan_kind is None
    assert agent.is_active_lethal_plan_action(stale_action) is False


def test_optimized_agent_replans_when_cached_lethal_target_is_gone(monkeypatch):
    first_card = _card("Defend_R", "Defend", uuid="first-defend")
    strike = _card("Strike_R", "Strike", uuid="stale-strike")
    strike.has_target = True
    live_card = _card("Defend_R", "Defend", uuid="live-defend")
    planned_target = _monster(name="Spike Slime", monster_id="SpikeSlime_M")
    planned_target.monster_index = 0
    other_target = _monster(name="Acid Slime", monster_id="AcidSlime_M")
    other_target.monster_index = 1
    first_action = PlayCardAction(card=first_card)
    stale_action = PlayCardAction(card=strike, target_monster=planned_target)
    live_action = PlayCardAction(card=live_card)
    planned_context = SimpleNamespace(act=1, threat_category=None, turn=3, floor=14)

    class FixedPlanner:
        last_plan_kind = "lethal"

        def __init__(self):
            self.calls = 0

        def plan_turn(self, _context):
            self.calls += 1
            if self.calls == 1:
                return [first_action, stale_action]
            self.last_plan_kind = None
            return [live_action]

    monkeypatch.setattr("spirecomm.ai.agent.DecisionContext", lambda _game: planned_context)
    monkeypatch.setattr(
        "spirecomm.ai.heuristics.simulation.select_combat_mode_with_monster_data",
        lambda _context: "test-mode",
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = _game([first_card, strike])
    agent.game.monsters = [planned_target, other_target]
    agent.game.play_available = True
    agent.current_action_sequence = []
    agent.current_action_index = 0
    agent.current_plan_signature = None
    agent.current_plan_kind = None
    agent.replan_count_this_turn = 0
    agent._current_combat_mode = "test-mode"
    agent.combat_planner = FixedPlanner()
    agent.game_tracker = None
    agent.decision_history = []
    agent.player_class = "IRONCLAD"

    assert agent._get_optimized_play_card_action() is first_action
    assert agent.current_plan_kind == "lethal"

    gone_target = _monster(name="Spike Slime", monster_id="SpikeSlime_M")
    gone_target.monster_index = 0
    gone_target.current_hp = 0
    gone_target.is_gone = True
    live_other = _monster(name="Acid Slime", monster_id="AcidSlime_M")
    live_other.monster_index = 1
    agent.game = _game([strike, live_card])
    agent.game.monsters = [gone_target, live_other]
    agent.game.play_available = True

    action = agent._get_optimized_play_card_action()

    assert action is live_action
    assert action is not stale_action
    assert agent.current_plan_kind is None
    assert agent.is_active_lethal_plan_action(stale_action) is False
    assert agent.combat_planner.calls == 2


def test_optimized_agent_clears_lethal_plan_on_turn_change(monkeypatch):
    monkeypatch.setattr(
        SimpleAgent,
        "get_next_action_in_game",
        lambda _self, _game: EndTurnAction(),
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = SimpleNamespace(turn=3, in_combat=True)
    agent.game_tracker = None
    agent.current_action_sequence = [PlayCardAction(card_index=0, target_index=0)]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = "lethal"
    agent.replan_count_this_turn = 0

    agent.get_next_action_in_game(SimpleNamespace(turn=4, in_combat=True))

    assert agent.current_plan_kind is None
    assert agent.current_action_sequence == []


def test_optimized_agent_clears_lethal_plan_on_combat_exit(monkeypatch):
    monkeypatch.setattr(
        SimpleAgent,
        "get_next_action_in_game",
        lambda _self, _game: EndTurnAction(),
    )
    agent = OptimizedAgent.__new__(OptimizedAgent)
    agent.game = SimpleNamespace(turn=3, in_combat=True)
    agent.game_tracker = None
    agent.current_action_sequence = [PlayCardAction(card_index=0, target_index=0)]
    agent.current_action_index = 1
    agent.current_plan_signature = SimpleNamespace()
    agent.current_plan_kind = "lethal"
    agent.replan_count_this_turn = 0

    agent.get_next_action_in_game(SimpleNamespace(turn=3, in_combat=False))

    assert agent.current_plan_kind is None
    assert agent.current_action_sequence == []
