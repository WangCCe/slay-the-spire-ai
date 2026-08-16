"""Single-step simulation divergence traces for live combat diagnosis."""

import copy
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from spirecomm.ai.heuristics.card_upgrades import (
    card_upgrade_count as _object_card_upgrade_count,
    heavy_blade_strength_multiplier,
    known_block_upgrade_bonus,
    known_damage_upgrade_bonus,
    perfected_strike_bonus_per_strike,
)
from spirecomm.ai.incoming_damage import exploder_explosion_damage
from spirecomm.data.loader import game_data_loader


TRACE_ENV = "STS_SIM_DIVERGENCE_TRACE_FILE"
DISABLED_VALUES = {"", "0", "false", "off", "none", "disabled"}
THE_BOOT_MINIMUM_DAMAGE = 5
PANACHE_DAMAGE = 10
PANACHE_RESET_COUNT = 5
LETTER_OPENER_DAMAGE = 5
BIRD_FACED_URN_HEAL = 2
CHARONS_ASHES_DAMAGE = 3
STONE_CALENDAR_DAMAGE = 52
STONE_CALENDAR_TRIGGER_COUNTER = 7
THE_BOMB_DAMAGE = 40
FAIRY_REVIVE_FRACTION = 0.3
FAIRY_POTION_IDENTIFIERS = {"fairy", "fairypotion", "fairyinabottle"}
LIZARD_TAIL_REVIVE_FRACTION = 0.5
LIZARD_TAIL_USED_COUNTER = -2
TOY_ORNITHOPTER_HEAL = 5
MAGIC_FLOWER_HEAL_NUMERATOR = 3
MAGIC_FLOWER_HEAL_DENOMINATOR = 2
FEED_MAX_HP_GAIN = 3
FEED_UPGRADED_MAX_HP_GAIN = 4
BURNING_BLOOD_HEAL = 6
BLACK_BLOOD_HEAL = 12
SUNDIAL_ENERGY = 2
SUNDIAL_TRIGGER_COUNTER = 3

BASE_ATTACK_DAMAGE = {
    "Anger": 6,
    "Bash": 8,
    "Bludgeon": 32,
    "Blood for Blood": 18,
    "Body Slam": 0,
    "Carnage": 20,
    "Clash": 14,
    "Cleave": 8,
    "Clothesline": 12,
    "Dramatic Entrance": 8,
    "Dropkick": 5,
    "Feed": 10,
    "Fiend Fire": 7,
    "Headbutt": 9,
    "Heavy Blade": 14,
    "Hemokinesis": 15,
    "Immolate": 21,
    "Iron Wave": 5,
    "Mind Blast": 0,
    "Perfected Strike": 6,
    "Pommel Strike": 9,
    "Pummel": 8,
    "Rampage": 8,
    "Reckless Charge": 7,
    "Reaper": 4,
    "Searing Blow": 12,
    "Sever Soul": 16,
    "Strike": 6,
    "Swift Strike": 7,
    "Sword Boomerang": 9,
    "Thunderclap": 4,
    "Twin Strike": 10,
    "Uppercut": 13,
    "Whirlwind": 5,
    "Wild Strike": 12,
}

MULTI_HIT_ATTACKS = {
    "Pummel": 4,
    "Sword Boomerang": 3,
    "Twin Strike": 2,
}

ALL_ENEMY_ATTACKS = {
    "Cleave": 0,
    "Dramatic Entrance": 0,
    "Immolate": 0,
    "Reaper": 0,
    "Thunderclap": 0,
    "Whirlwind": 0,
}

BASE_SKILL_BLOCK = {
    "Armaments": 5,
    "Defend": 5,
    "Finesse": 2,
    "Good Instincts": 6,
    "Flame Barrier": 12,
    "Ghostly Armor": 10,
    "Impervious": 30,
    "Iron Wave": 5,
    "Panic Button": 30,
    "Power Through": 15,
    "Sentinel": 5,
    "Shrug It Off": 8,
    "True Grit": 7,
}

ATTACK_BLOCK_BEFORE_DAMAGE = {
    "Iron Wave": 5,
}

SECOND_WIND_BLOCK_PER_CARD = {
    "Second Wind": 5,
}

BLOCK_MULTIPLIER_SKILLS = {
    "Entrench": 2,
}

EXHAUSTS_NON_ATTACK_HAND_CARDS = {
    "Second Wind": 0,
    "Sever Soul": 0,
}

SELF_EXHAUST_CARDS = {
    "Double Tap": 0,
    "Disarm": 0,
    "Exhume": 0,
    "Feed": 0,
    "Fiend Fire": 0,
    "Impervious": 0,
    "Infernal Blade": 0,
    "Intimidate": 0,
    "Offering": 0,
    "Reaper": 0,
    "Seeing Red": 0,
    "Shockwave": 0,
    "Warcry": 0,
}

CARD_SELF_DAMAGE = {
    "Bloodletting": 3,
    "Hemokinesis": 2,
    "Offering": 6,
}

PAIN_CARDS = {
    "Pain": 0,
}

CARD_ENERGY_GAIN = {
    "Bloodletting": 2,
    "Offering": 2,
    "Seeing Red": 2,
}

CARD_HEAL = {
    "Bandage Up": 4,
}

CARD_DRAW = {
    "Battle Trance": (3, 4),
}

CARD_TARGET_DEBUFFS = {
    "Bash": ("Vulnerable", 2, 3),
    "Thunderclap": ("Vulnerable", 1, 2),
}

END_TURN_STATUS_DAMAGE = {
    "Burn": 2,
    "Decay": 2,
}

END_TURN_STATUS_HP_LOSS = {}

END_TURN_EXHAUST_CARDS = {
    "Dazed": 0,
}

HAVOC_CARDS = {
    "Havoc": 0,
}

CLASH_CARDS = {
    "Clash": 0,
}

CARD_ID_ALIASES = {
    "Defend_R": "Defend",
    "Strike_R": "Strike",
}

logger = logging.getLogger(__name__)
_pending_expected: Optional[Dict[str, Any]] = None
_rampage_damage_bonus_by_card: Dict[str, int] = {}
_rampage_state_floor: Optional[int] = None
_attack_count_state_floor: Optional[int] = None
_attack_count_state_turn: Optional[int] = None
_attacks_played_this_turn = 0
_necronomicon_used_this_turn = False
_pending_headbutt_select_effects: Optional[Dict[str, Any]] = None
_pending_burning_pact_select_effects: Optional[Dict[str, Any]] = None
_pending_true_grit_select_effects: Optional[Dict[str, Any]] = None
_pending_armaments_select_effects: Optional[Dict[str, Any]] = None


def card_upgrade_count(card) -> int:
    if isinstance(card, dict):
        return _snapshot_card_upgrade_count(card)
    return _object_card_upgrade_count(card)


def divergence_trace_path(path: Optional[Path] = None) -> Optional[Path]:
    if path is not None:
        return Path(path)
    value = os.environ.get(TRACE_ENV)
    if value is None or value.strip().lower() in DISABLED_VALUES:
        return None
    return Path(value)


def reset_pending_divergence() -> None:
    global _pending_expected, _rampage_damage_bonus_by_card, _rampage_state_floor
    global _attack_count_state_floor, _attack_count_state_turn, _attacks_played_this_turn
    global _necronomicon_used_this_turn, _pending_headbutt_select_effects
    global _pending_burning_pact_select_effects, _pending_true_grit_select_effects
    global _pending_armaments_select_effects
    _pending_expected = None
    _rampage_damage_bonus_by_card = {}
    _rampage_state_floor = None
    _attack_count_state_floor = None
    _attack_count_state_turn = None
    _attacks_played_this_turn = 0
    _necronomicon_used_this_turn = False
    _pending_headbutt_select_effects = None
    _pending_burning_pact_select_effects = None
    _pending_true_grit_select_effects = None
    _pending_armaments_select_effects = None


def record_expected_action(action, game, path: Optional[Path] = None) -> bool:
    """Record a read-only one-action expectation for the next live state."""
    global _pending_expected, _pending_headbutt_select_effects
    global _pending_burning_pact_select_effects, _pending_true_grit_select_effects
    global _pending_armaments_select_effects

    if divergence_trace_path(path) is None:
        return False
    if action is None or not getattr(game, "in_combat", False):
        _pending_expected = None
        _pending_headbutt_select_effects = None
        _pending_burning_pact_select_effects = None
        _pending_true_grit_select_effects = None
        _pending_armaments_select_effects = None
        return False

    try:
        _sync_rampage_state(_to_int(getattr(game, "floor", None)))
        before = snapshot_combat_state(game)
        _sync_attack_count_state(before["floor"], before["turn"])
        if not _will_apply_pending_headbutt_select_effects(action, before):
            _pending_headbutt_select_effects = None
        if not _will_apply_pending_burning_pact_select_effects(action, before):
            _pending_burning_pact_select_effects = None
        if not _will_apply_pending_true_grit_select_effects(action, before):
            _pending_true_grit_select_effects = None
        if not _will_apply_pending_armaments_select_effects(action, before):
            _pending_armaments_select_effects = None
        action_summary = _action_summary(action, game)
        card = _card_for_action(action, game)
        if card is not None:
            delayed_headbutt_effects = _headbutt_select_delayed_effects(before, card)
            if delayed_headbutt_effects:
                action_summary["delayed_headbutt_select_effects"] = delayed_headbutt_effects
            delayed_burning_pact_effects = _burning_pact_select_delayed_effects(
                before,
                card,
            )
            if delayed_burning_pact_effects:
                action_summary["delayed_burning_pact_select_effects"] = (
                    delayed_burning_pact_effects
                )
            delayed_true_grit_effects = _true_grit_select_delayed_effects(
                before,
                card,
            )
            if delayed_true_grit_effects:
                action_summary["delayed_true_grit_select_effects"] = (
                    delayed_true_grit_effects
                )
            delayed_armaments_effects = _armaments_select_delayed_effects(
                before,
                card,
            )
            if delayed_armaments_effects:
                action_summary["delayed_armaments_select_effects"] = (
                    delayed_armaments_effects
                )
        _pending_expected = {
            "timestamp": _timestamp(),
            "unix_time": round(time.time(), 3),
            "floor": before["floor"],
            "turn": before["turn"],
            "before": before,
            "expected": _expected_after_action(action, game, before),
            "action": action_summary,
        }
        return True
    except Exception as exc:
        _pending_expected = None
        _pending_headbutt_select_effects = None
        _pending_burning_pact_select_effects = None
        _pending_true_grit_select_effects = None
        _pending_armaments_select_effects = None
        logger.debug("sim divergence expected-state record failed: %s", exc)
        return False


def observe_next_state(game, path: Optional[Path] = None) -> bool:
    """Compare the pending expectation with the newest live state and log diffs."""
    global _pending_expected

    target = divergence_trace_path(path)
    if target is None or _pending_expected is None:
        return False

    pending = _pending_expected
    _pending_expected = None

    try:
        actual = snapshot_combat_state(game)
        _sync_rampage_state(actual["floor"])
        _sync_attack_count_state(pending["floor"], pending["turn"])
        if actual["floor"] != pending["floor"]:
            return False
        _finalize_observed_action(pending, actual)
        if _expected_combat_finished(pending["expected"], actual):
            return False
        if _nilrys_codex_screen_boundary(pending, actual):
            return False

        ignored_diffs = _ignored_diff_keys(pending, actual)
        diffs = _diff_snapshots(pending["expected"], actual, ignored_diffs)
        if _headbutt_select_delayed_diff_boundary(pending, actual, diffs):
            _arm_headbutt_select_boundary_if_applicable(pending, actual, diffs)
            return False
        if _burning_pact_select_delayed_diff_boundary(pending, actual, diffs):
            _arm_burning_pact_select_boundary_if_applicable(pending, actual, diffs)
            return False

        _consume_headbutt_select_boundary_if_applicable(pending)
        _consume_burning_pact_select_boundary_if_applicable(pending)
        _consume_true_grit_select_boundary_if_applicable(pending)
        _consume_armaments_select_boundary_if_applicable(pending)
        if not diffs:
            _arm_headbutt_select_boundary_if_applicable(pending, actual, diffs)
            _arm_burning_pact_select_boundary_if_applicable(pending, actual, diffs)
            _arm_true_grit_select_boundary_if_applicable(pending, actual)
            _arm_armaments_select_boundary_if_applicable(pending, actual)
            return False

        event = {
            "event_type": "sim_divergence",
            "timestamp": _timestamp(),
            "unix_time": round(time.time(), 3),
            "reason": _classify_reason(pending, actual, diffs),
            "floor": actual["floor"],
            "turn": actual["turn"],
            "expected_turn": pending["turn"],
            "action": pending["action"],
            "diffs": diffs,
            "before": pending["before"],
            "expected": pending["expected"],
            "actual": actual,
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        logger.info(
            "[SIM_DIVERGENCE] reason=%s floor=%s turn=%s action=%s diffs=%s",
            event["reason"],
            event["floor"],
            event["turn"],
            event["action"].get("type"),
            sorted(diffs),
        )
        return True
    except Exception as exc:
        logger.debug("sim divergence observe failed: %s", exc)
        return False


def snapshot_combat_state(game) -> Dict[str, Any]:
    player = getattr(game, "player", None)
    return {
        "floor": _to_int(getattr(game, "floor", None)),
        "turn": _to_int(getattr(game, "turn", None)),
        "act": _to_int(getattr(game, "act", None)),
        "room_type": _safe_str(getattr(game, "room_type", "")),
        "in_combat": bool(getattr(game, "in_combat", False)),
        "player": {
            "current_hp": _to_int(
                getattr(player, "current_hp", getattr(game, "current_hp", None))
            ),
            "max_hp": _to_int(getattr(player, "max_hp", getattr(game, "max_hp", None))),
            "block": _to_int(getattr(player, "block", getattr(game, "block", None))),
            "energy": _to_int(getattr(player, "energy", getattr(game, "energy", None))),
            "powers": [_power_summary(power) for power in _safe_iterable(getattr(player, "powers", []))],
        },
        "hand": [_card_summary(card) for card in _safe_iterable(getattr(game, "hand", []))],
        "draw_pile": [
            _card_summary(card)
            for card in _safe_iterable(getattr(game, "draw_pile", []))
        ],
        "draw_pile_count": _pile_count(game, "draw_pile"),
        "discard_pile": [
            _card_summary(card)
            for card in _safe_iterable(getattr(game, "discard_pile", []))
        ],
        "discard_pile_count": _pile_count(game, "discard_pile"),
        "relics": [_relic_summary(relic) for relic in _safe_iterable(getattr(game, "relics", []))],
        "potions": [
            _potion_summary(potion)
            for potion in _safe_iterable(getattr(game, "potions", []))
        ],
        "monsters": [
            _monster_summary(monster)
            for monster in _safe_iterable(getattr(game, "monsters", []))
        ],
    }


def _expected_after_action(action, game, before: Dict[str, Any]) -> Dict[str, Any]:
    expected = copy.deepcopy(before)
    action_type = type(action).__name__ if action is not None else ""

    if action_type == "PlayCardAction":
        card = _card_for_action(action, game)
        card_index = _to_int(getattr(action, "card_index", -1), default=-1)
        if card is not None:
            delayed_headbutt_effects = _headbutt_select_delayed_effects(before, card)
            delayed_burning_pact_effects = _burning_pact_select_delayed_effects(
                before,
                card,
            )
            delayed_true_grit_effects = _true_grit_select_delayed_effects(
                before,
                card,
            )
            delayed_armaments_effects = _armaments_select_delayed_effects(
                before,
                card,
            )
            energy_before_card = expected["player"]["energy"]
            target_index = None
            card_play_count = _card_play_count(before, card)
            attack_play_count = _attack_card_play_count(before, card)
            attack_hp_loss_events = []
            if _is_attack_card(card):
                attack_hp_loss_events = _card_play_hp_loss_events(
                    card,
                    before,
                    card_index,
                )
            if _card_spends_all_energy(card, before):
                expected["player"]["energy"] = 0
            else:
                expected["player"]["energy"] = max(
                    0,
                    energy_before_card - max(0, _card_cost(card)),
                )
            pre_damage_block_applied = False
            if _is_attack_card(card):
                attack_effects_resolved = False
                pre_damage_block_applied = _apply_attack_block_before_damage(
                    expected,
                    before,
                    card,
                    attack_play_count,
                )
                sharp_hide_damage = 0
                damage, hit_count = _card_damage_and_hits_for_snapshot(
                    card,
                    expected.get("player", {}),
                    energy_before_card,
                    before,
                    card_index,
                )
                source_damage_before_weak = _card_damage_before_player_weak(
                    card,
                    expected.get("player", {}),
                    energy_before_card,
                    before,
                    card_index,
                )
                damage_dealt = 0
                if _is_all_enemy_attack(card):
                    for _ in range(max(1, attack_play_count)):
                        for hp_loss, clear_block_on_death in attack_hp_loss_events:
                            _lose_player_hp(
                                expected,
                                hp_loss,
                                clear_block_on_death=clear_block_on_death,
                            )
                            if _snapshot_player_dead(expected):
                                break
                        if _snapshot_player_dead(expected):
                            break
                        damage_dealt += _apply_expected_attack_to_all(
                            expected,
                            damage,
                            hit_count,
                            before,
                            source_damage_before_weak=source_damage_before_weak,
                        )
                        _apply_all_enemy_card_target_debuffs(expected, card)
                        attack_effects_resolved = True
                    if attack_effects_resolved:
                        sharp_hide_damage = _sharp_hide_reflection_damage(
                            before,
                            all_targets=True,
                        ) * max(1, attack_play_count)
                else:
                    target_index = _target_index_for_action(action, game)
                    for _ in range(max(1, attack_play_count)):
                        for hp_loss, clear_block_on_death in attack_hp_loss_events:
                            _lose_player_hp(
                                expected,
                                hp_loss,
                                clear_block_on_death=clear_block_on_death,
                            )
                            if _snapshot_player_dead(expected):
                                break
                        if _snapshot_player_dead(expected):
                            break
                        damage_dealt += _apply_expected_attack(
                            expected,
                            target_index,
                            damage,
                            hit_count,
                            before,
                            source_damage_before_weak=source_damage_before_weak,
                        )
                        _apply_card_target_debuffs(expected, card, target_index)
                        attack_effects_resolved = True
                    if attack_effects_resolved:
                        sharp_hide_damage = _sharp_hide_reflection_damage(
                            before,
                            target_index,
                        ) * max(1, attack_play_count)
                        _apply_feed_max_hp_gain(expected, card, target_index, before)
                rage_block = (
                    0
                    if _to_int(delayed_headbutt_effects.get("rage_block")) > 0
                    else _rage_attack_block(expected.get("player", {}))
                )
                if attack_effects_resolved and rage_block > 0:
                    _gain_player_block(expected, before, rage_block)
                ornamental_fan_block = (
                    0
                    if _to_int(delayed_headbutt_effects.get("ornamental_fan_block")) > 0
                    else _ornamental_fan_attack_block(before)
                )
                if attack_effects_resolved and ornamental_fan_block > 0:
                    _gain_player_block(expected, before, ornamental_fan_block)
                if attack_effects_resolved and sharp_hide_damage > 0:
                    _damage_player(expected, sharp_hide_damage)
                if attack_effects_resolved and _is_reaper(card) and damage_dealt > 0:
                    _heal_player(
                        expected,
                        _magic_flower_scaled_heal(expected, damage_dealt),
                    )
            self_damage_events = (
                [] if _is_attack_card(card) else _card_play_hp_loss_events(card, before, card_index)
            )
            for hp_loss, clear_block_on_death in self_damage_events:
                _lose_player_hp(
                    expected,
                    hp_loss,
                    clear_block_on_death=clear_block_on_death,
                )
                if _snapshot_player_dead(expected):
                    break
            heal = _card_heal(card)
            if heal > 0:
                _heal_player(expected, heal)
            energy_gain = _card_energy_gain(card)
            energy_gain += _conditional_card_energy_gain(card, before, target_index)
            if _to_int(delayed_headbutt_effects.get("energy")) <= 0:
                energy_gain += _nunchaku_energy_gain(before, card)
            if energy_gain > 0:
                expected["player"]["energy"] += energy_gain
            _apply_block_multiplier_card(expected, before, card, card_play_count)
            block = _card_block(card)
            if block > 0 and not pre_damage_block_applied:
                block_trigger_count = (
                    attack_play_count if _is_attack_card(card) else card_play_count
                )
                if delayed_true_grit_effects:
                    block_trigger_count = 0
                if delayed_armaments_effects:
                    block_trigger_count = 0
                _gain_player_block(
                    expected,
                    before,
                    sum(
                        _modified_block(block, expected.get("player", {}))
                        for _ in range(
                            attack_play_count if _is_attack_card(card) else card_play_count
                        )
                    ),
                    block_trigger_count,
                    from_card=True,
                )
            _apply_panic_button_no_block_power(expected, card)
            second_wind_block = _second_wind_block(
                card,
                before,
                card_index,
                expected.get("player", {}),
            )
            if second_wind_block > 0:
                _gain_player_block(
                    expected,
                    before,
                    second_wind_block,
                    _exhausts_non_attack_hand_count(card, before, card_index),
                    from_card=True,
                )
            hand_exhaust_energy = _hand_exhaust_sentinel_energy(card, before, card_index)
            if hand_exhaust_energy > 0:
                expected["player"]["energy"] += hand_exhaust_energy
            feel_no_pain_block, feel_no_pain_events = _feel_no_pain_block(
                card,
                before,
                card_index,
            )
            if feel_no_pain_block > 0:
                _gain_player_block(
                    expected,
                    before,
                    feel_no_pain_block,
                    feel_no_pain_events,
                )
            _apply_charons_ashes_exhaust_damage(expected, before, card, card_index)
            _apply_havoc_top_card(expected, before, card)
            _apply_card_draw(expected, card)
            _apply_bird_faced_urn_power_play(expected, card, card_play_count)
            for _ in range(card_play_count):
                _apply_letter_opener_skill_play(expected, card)
                if delayed_burning_pact_effects:
                    _advance_panache_card_play(expected)
                else:
                    _apply_panache_card_play(expected)
            if card_play_count > 1:
                _consume_duplication_power(expected)
        if 0 <= card_index < len(expected["hand"]):
            expected["hand"].pop(card_index)

    elif action_type == "CardSelectAction":
        _apply_pending_headbutt_select_effects(expected, before)
        _apply_pending_burning_pact_select_effects(expected, before, action)
        _apply_pending_true_grit_select_effects(expected, before, action)
        _apply_pending_armaments_select_effects(expected, before)

    elif action_type == "PotionAction":
        _apply_expected_potion(expected, action, game, before)

    elif action_type == "EndTurnAction":
        orichalcum_block = _orichalcum_end_turn_block(before, expected.get("player", {}))
        if orichalcum_block > 0:
            expected["player"]["block"] += orichalcum_block
        metallicize_block = _metallicize_end_turn_block(before)
        if metallicize_block > 0:
            expected["player"]["block"] += metallicize_block
        plated_armor_block = _plated_armor_end_turn_block(before)
        if plated_armor_block > 0:
            expected["player"]["block"] += plated_armor_block
        hp_loss_events = _apply_combust_end_turn(expected, before)
        regeneration_heal = _regeneration_end_turn_heal(before)
        if regeneration_heal > 0:
            _heal_player(expected, regeneration_heal)
        combat_finished = _apply_the_bomb_end_turn(expected, before)
        if not combat_finished:
            _apply_stone_calendar_damage(expected, before)
            hp_loss_events += _apply_end_turn_player_damage(expected, before)
            _apply_end_turn_escape_intents(expected)
            _apply_monster_regenerate_end_turn(expected)
            retained_block = _retained_end_turn_block(before, expected.get("player", {}))
            next_turn_block = 0
            if _to_int(expected.get("player", {}).get("current_hp")) > 0:
                next_turn_block += _next_turn_block_start_turn_block(before)
                next_turn_block += _self_forming_clay_end_turn_block(
                    before,
                    hp_loss_events,
                )
                next_turn_block += _horn_cleat_start_turn_block(before)
                next_turn_block += _captains_wheel_start_turn_block(before)
                expected["player"]["block"] = retained_block + next_turn_block
            else:
                expected["player"]["block"] = 0
            expected["player"]["energy"] = 0
            brutality_loss = _brutality_start_turn_hp_loss(before)
            if brutality_loss > 0:
                _lose_player_hp(expected, brutality_loss)
            _apply_darkling_end_turn_revives(expected, before)
            _apply_awakened_one_end_turn_rebirth(expected, before)
            _prepare_monster_block_for_mercury_hourglass(expected, before)
            _apply_mercury_hourglass_damage(expected, before)
            _apply_end_turn_summons(expected, before)

    expected.pop("_player_vulnerable_added_during_end_turn", None)
    return expected


def _apply_expected_attack(
    expected: Dict[str, Any],
    target_index: Optional[int],
    damage: int,
    hit_count: int = 1,
    before: Optional[Dict[str, Any]] = None,
    source_damage_before_weak: Optional[int] = None,
) -> int:
    if target_index is None or target_index < 0:
        return 0
    monsters = expected.get("monsters", [])
    if target_index >= len(monsters):
        return 0
    target = monsters[target_index]
    curl_up_applied = False
    damage_dealt = 0
    deferred_curl_up_block = 0
    deferred_guardian_mode_shift_hp_loss = 0
    deferred_malleable_block = 0
    flight_hit_count = 0
    total_hits = max(0, hit_count)
    defer_guardian_mode_shift = _is_guardian_monster(target) and total_hits > 1
    for _ in range(total_hits):
        if target.get("gone") or target.get("half_dead") or _to_int(target.get("hp")) <= 0:
            break
        remaining_damage = _modified_attack_damage(
            max(0, damage),
            target,
            before,
            source_damage_before_weak=source_damage_before_weak,
        )
        if target["block"] > 0:
            blocked = min(target["block"], remaining_damage)
            target["block"] -= blocked
            remaining_damage -= blocked
        remaining_damage = _the_boot_minimum_attack_damage(before, remaining_damage)
        hp_before = target["hp"]
        target["hp"] = max(0, target["hp"] - remaining_damage)
        hp_loss = max(0, hp_before - target["hp"])
        damage_dealt += hp_loss
        thorns_damage = _thorns_reflection_damage(target)
        if thorns_damage > 0:
            _damage_player(expected, thorns_damage)
        if target["hp"] <= 0:
            _mark_monster_defeated(target, expected)
            break
        if hp_loss > 0:
            _apply_lagavulin_wake_stun(target)
            if defer_guardian_mode_shift:
                deferred_guardian_mode_shift_hp_loss += hp_loss
            else:
                _apply_guardian_mode_shift(target, hp_loss)
            if _snapshot_power_amount(target, "Flight") > 0:
                flight_hit_count += 1
            deferred_malleable_block += _trigger_malleable(target, defer_block=True)
        if not curl_up_applied and hp_loss > 0:
            curl_up_block = max(0, _snapshot_power_amount(target, "Curl Up"))
            if curl_up_block > 0:
                deferred_curl_up_block += curl_up_block
                curl_up_applied = True
    if (
        flight_hit_count > 0
        and not target.get("gone")
        and not target.get("half_dead")
        and _to_int(target.get("hp")) > 0
    ):
        _decrement_flight(target, flight_hit_count)
    if (
        deferred_guardian_mode_shift_hp_loss > 0
        and not target.get("gone")
        and not target.get("half_dead")
        and _to_int(target.get("hp")) > 0
    ):
        _apply_guardian_mode_shift(target, deferred_guardian_mode_shift_hp_loss)
    if (
        (deferred_curl_up_block > 0 or deferred_malleable_block > 0)
        and not target.get("gone")
        and not target.get("half_dead")
        and _to_int(target.get("hp")) > 0
    ):
        target["block"] = (
            max(0, _to_int(target.get("block")))
            + deferred_curl_up_block
            + deferred_malleable_block
        )
    return damage_dealt


def _apply_expected_attack_to_all(
    expected: Dict[str, Any],
    damage: int,
    hit_count: int = 1,
    before: Optional[Dict[str, Any]] = None,
    source_damage_before_weak: Optional[int] = None,
) -> int:
    damage_dealt = 0
    for index, monster in enumerate(expected.get("monsters", [])):
        if monster.get("gone") or monster.get("half_dead") or _to_int(monster.get("hp")) <= 0:
            continue
        damage_dealt += _apply_expected_attack(
            expected,
            index,
            damage,
            hit_count,
            before,
            source_damage_before_weak=source_damage_before_weak,
        )
    return damage_dealt


def _apply_expected_potion(
    expected: Dict[str, Any],
    action,
    game,
    before: Dict[str, Any],
) -> None:
    if not bool(getattr(action, "use", True)):
        return
    potion = _potion_for_action(action, game)
    if potion is None:
        return

    effect_type = _normalize(_potion_attr(potion, "effect_type", ""))
    target_type = _normalize(_potion_attr(potion, "target_type", ""))
    raw_value = _potion_attr(potion, "effect_value", 0)

    if _is_escape_potion_snapshot(potion):
        _apply_expected_escape_potion(expected, action, game)
        return

    if effect_type == "healpercent" and target_type == "self":
        percent = _to_float(raw_value)
        heal = int(_to_int(expected["player"].get("max_hp")) * percent)
        _heal_player(expected, heal)
        _apply_toy_ornithopter_potion_heal(expected)
        return

    value = _to_int(raw_value)
    if value > 0:
        if effect_type == "energy":
            expected["player"]["energy"] += value
        elif effect_type == "block":
            expected["player"]["block"] += value
        elif effect_type == "maxhp" and target_type == "self":
            expected["player"]["max_hp"] = _to_int(expected["player"].get("max_hp")) + value
            _heal_player(expected, value)
        elif effect_type == "damage":
            if target_type == "allmonsters":
                for index, _monster in enumerate(expected.get("monsters", [])):
                    _apply_direct_monster_damage(expected, index, value)
            elif target_type == "monster":
                _apply_direct_monster_damage(
                    expected,
                    _target_index_for_action(action, game),
                    value,
                )
        elif effect_type == "playtopcards":
            _apply_expected_play_top_cards_potion(expected, before, value)

    _apply_toy_ornithopter_potion_heal(expected)


def _apply_expected_escape_potion(expected: Dict[str, Any], action, game) -> None:
    _apply_toy_ornithopter_potion_heal(expected)
    _heal_player(expected, _combat_end_relic_heal(expected))
    _consume_expected_action_potion(expected, action, game)
    _finish_expected_combat(expected)


def _finish_expected_combat(expected: Dict[str, Any]) -> None:
    expected["in_combat"] = False
    expected["turn"] = 0
    expected["hand"] = []
    expected["monsters"] = []
    player = expected.get("player", {})
    player["block"] = 0
    player["energy"] = 0
    player["powers"] = []


def _apply_the_bomb_end_turn(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> bool:
    player = before.get("player", {})
    if _snapshot_power_amount(player, "The Bomb") != 1:
        return False
    if _to_int(expected.get("player", {}).get("current_hp")) <= 0:
        return False

    for index, monster in enumerate(expected.get("monsters", []) or []):
        if (
            monster.get("gone")
            or monster.get("half_dead")
            or _to_int(monster.get("hp")) <= 0
        ):
            continue
        _apply_direct_monster_damage(expected, index, THE_BOMB_DAMAGE)

    _remove_snapshot_power(expected.get("player", {}), "The Bomb")
    if _active_monster_count(expected) > 0:
        return False

    _heal_player(expected, _combat_end_relic_heal(expected))
    _finish_expected_combat(expected)
    return True


def _combat_end_relic_heal(expected: Dict[str, Any]) -> int:
    if _snapshot_has_relic(expected, "Black Blood"):
        return BLACK_BLOOD_HEAL
    if _snapshot_has_relic(expected, "Burning Blood"):
        return BURNING_BLOOD_HEAL
    return 0


def _consume_expected_action_potion(expected: Dict[str, Any], action, game) -> None:
    potions = expected.get("potions")
    if not isinstance(potions, list):
        return
    potion_index = _to_int(getattr(action, "potion_index", -1), default=-1)
    if potion_index < 0:
        potion_identifiers = _potion_identifiers(_potion_for_action(action, game))
        for index, candidate in enumerate(potions):
            if not potion_identifiers.isdisjoint(_potion_identifiers(candidate)):
                potion_index = index
                break
    if 0 <= potion_index < len(potions):
        potions.pop(potion_index)


def _apply_direct_monster_damage(
    expected: Dict[str, Any],
    target_index: Optional[int],
    amount: int,
    ignore_block: bool = False,
    spore_cloud_decay: int = 0,
    mark_end_turn_vulnerable: bool = False,
) -> int:
    if target_index is None or target_index < 0 or amount <= 0:
        return 0
    monsters = expected.get("monsters", [])
    if target_index >= len(monsters):
        return 0
    target = monsters[target_index]
    if target.get("gone") or target.get("half_dead") or _to_int(target.get("hp")) <= 0:
        return 0

    remaining = max(0, amount)
    block = max(0, _to_int(target.get("block")))
    if not ignore_block:
        blocked = min(block, remaining)
        target["block"] = block - blocked
        remaining -= blocked
    hp_before = _to_int(target.get("hp"))
    target["hp"] = max(0, hp_before - remaining)
    hp_loss = max(0, hp_before - target["hp"])
    if target["hp"] <= 0:
        _mark_monster_defeated(
            target,
            expected,
            spore_cloud_decay=spore_cloud_decay,
            mark_end_turn_vulnerable=mark_end_turn_vulnerable,
        )
    return hp_loss


def _apply_panache_card_play(expected: Dict[str, Any]) -> int:
    damage = _advance_panache_card_play(expected)
    if damage <= 0:
        return 0
    return _apply_panache_damage(expected, damage)


def _advance_panache_card_play(expected: Dict[str, Any]) -> int:
    player = expected.get("player", {})
    if not _snapshot_has_power(player, "Panache"):
        return 0

    counter = _snapshot_power_amount(player, "Panache")
    if counter > 1:
        _set_snapshot_power_amount(player, "Panache", counter - 1)
        return 0

    _set_snapshot_power_amount(player, "Panache", PANACHE_RESET_COUNT)
    return PANACHE_DAMAGE


def _apply_panache_damage(expected: Dict[str, Any], damage: int) -> int:
    damage = max(0, _to_int(damage))
    if damage <= 0:
        return 0

    damage_dealt = 0
    for monster_index, monster in enumerate(expected.get("monsters", []) or []):
        if (
            monster.get("gone")
            or monster.get("half_dead")
            or _to_int(monster.get("hp")) <= 0
        ):
            continue
        damage_dealt += _apply_direct_monster_damage(
            expected,
            monster_index,
            damage,
        )
    return damage_dealt


def _apply_letter_opener_skill_play(expected: Dict[str, Any], card) -> int:
    if not _is_skill_card(card):
        return 0
    counter = _snapshot_relic_counter(expected, "Letter Opener")
    if counter is None:
        return 0

    counter = max(0, counter)
    if counter < 2:
        _set_snapshot_relic_counter(expected, "Letter Opener", counter + 1)
        return 0

    damage_dealt = 0
    for monster_index, monster in enumerate(expected.get("monsters", []) or []):
        if (
            monster.get("gone")
            or monster.get("half_dead")
            or _to_int(monster.get("hp")) <= 0
        ):
            continue
        damage_dealt += _apply_direct_monster_damage(
            expected,
            monster_index,
            LETTER_OPENER_DAMAGE,
        )
    _set_snapshot_relic_counter(expected, "Letter Opener", 0)
    return damage_dealt


def _apply_bird_faced_urn_power_play(
    expected: Dict[str, Any],
    card,
    play_count: int = 1,
) -> None:
    if not _is_power_card(card) or not _snapshot_has_relic(expected, "Bird Faced Urn"):
        return
    for _ in range(max(1, play_count)):
        _heal_player(expected, BIRD_FACED_URN_HEAL)


def _mark_monster_defeated(
    monster: Dict[str, Any],
    expected: Optional[Dict[str, Any]] = None,
    spore_cloud_decay: int = 0,
    mark_end_turn_vulnerable: bool = False,
) -> None:
    if expected is not None:
        _apply_monster_death_effects(
            expected,
            monster,
            spore_cloud_decay=spore_cloud_decay,
            mark_end_turn_vulnerable=mark_end_turn_vulnerable,
        )
    monster["hp"] = 0
    monster["gone"] = True
    if _is_darkling_monster(monster):
        monster["half_dead"] = True
        monster["intent"] = "Intent.UNKNOWN"
        monster["move_damage"] = -1
    elif _is_awakened_one_monster(monster):
        monster["half_dead"] = True
        monster["intent"] = "Intent.UNKNOWN"
        monster["move_damage"] = -1
        monster["powers"] = [
            power
            for power in monster.get("powers", []) or []
            if "regenerate"
            in {
                _normalize(power.get("id")),
                _normalize(power.get("name")),
            }
        ]


def _apply_monster_death_effects(
    expected: Dict[str, Any],
    monster: Dict[str, Any],
    spore_cloud_decay: int = 0,
    mark_end_turn_vulnerable: bool = False,
) -> None:
    _apply_gremlin_horn_kill_reward(expected)
    spore_cloud = max(0, _snapshot_power_amount(monster, "Spore Cloud"))
    if spore_cloud <= 0:
        return
    applied_amount = max(1, spore_cloud - max(0, spore_cloud_decay))
    if _apply_player_debuff(expected, "Vulnerable", applied_amount):
        if not mark_end_turn_vulnerable:
            return
        expected["_player_vulnerable_added_during_end_turn"] = True


def _apply_gremlin_horn_kill_reward(expected: Dict[str, Any]) -> None:
    if not _snapshot_has_relic(expected, "Gremlin Horn"):
        return
    expected["player"]["energy"] = (
        max(0, _to_int(expected.get("player", {}).get("energy"))) + 1
    )
    if _snapshot_has_power(expected.get("player", {}), "No Draw") or _snapshot_has_power(
        expected.get("player", {}),
        "NoDraw",
    ):
        return
    top_card = _draw_pile_top_card(expected)
    if top_card is not None:
        expected.setdefault("hand", []).append(copy.deepcopy(top_card))
    if top_card is not None or _to_int(expected.get("draw_pile_count")) > 0:
        _pop_expected_draw_pile_top(expected)


def _apply_darkling_end_turn_revives(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> None:
    before_monsters = before.get("monsters") or []
    for index, monster in enumerate(expected.get("monsters", []) or []):
        before_monster = before_monsters[index] if index < len(before_monsters) else {}
        if not _darkling_revival_ready(before_monster):
            continue
        monster["hp"] = max(1, _to_int(monster.get("max_hp")) // 2)
        monster["gone"] = False
        monster["half_dead"] = False


def _apply_awakened_one_end_turn_rebirth(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> None:
    if _to_int(expected.get("player", {}).get("current_hp")) <= 0:
        return
    before_monsters = before.get("monsters") or []
    for index, monster in enumerate(expected.get("monsters", []) or []):
        before_monster = before_monsters[index] if index < len(before_monsters) else {}
        if not _awakened_one_half_dead(before_monster):
            continue
        monster["hp"] = max(1, _to_int(monster.get("max_hp")))
        monster["block"] = 0
        monster["gone"] = False
        monster["half_dead"] = False
        monster["intent"] = "Intent.ATTACK"


def _apply_end_turn_summons(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> None:
    if _to_int(expected.get("player", {}).get("current_hp")) <= 0:
        return

    expected_monsters = expected.get("monsters", []) or []
    before_monsters = before.get("monsters", []) or []
    new_monsters: List[Dict[str, Any]] = []
    changed = False

    for index, monster in enumerate(expected_monsters):
        before_monster = before_monsters[index] if index < len(before_monsters) else monster
        summon_names = _end_turn_summon_names(before_monster)
        if summon_names and _snapshot_monster_active(monster):
            open_slots = _end_turn_summon_open_slots(expected_monsters, before_monster, summon_names)
            for child_index, child_name in enumerate(summon_names[:open_slots]):
                summoned = _summoned_monster_snapshot(child_name, before_monster, child_index)
                if summoned is None:
                    continue
                new_monsters.append(summoned)
                changed = True
        new_monsters.append(monster)

    if changed:
        expected["monsters"] = new_monsters


def _end_turn_summon_names(monster: Dict[str, Any]) -> List[str]:
    if not _snapshot_monster_active(monster):
        return []

    move = _current_summon_move(monster)
    if not move:
        return []

    raw_summons = move.get("summons")
    if isinstance(raw_summons, str):
        summon_names = [raw_summons]
    elif isinstance(raw_summons, list):
        summon_names = [name for name in raw_summons if isinstance(name, str)]
    else:
        summon_names = []

    summon_names = [_canonical_monster_data_name(name) for name in summon_names]
    summon_names = [name for name in summon_names if name]
    if not summon_names:
        return []

    count = _summon_count_from_move(move, len(summon_names))
    if count <= 0:
        return []
    if len(summon_names) == 1 and count > 1:
        summon_names = summon_names * count
    return summon_names[:count]


def _current_summon_move(monster: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    move_id = _to_int(monster.get("move_id"), default=None)
    if move_id is None:
        return None

    summon_moves: List[Dict[str, Any]] = []
    for monster_name in (monster.get("name"), monster.get("id")):
        if not monster_name:
            continue
        try:
            moves = game_data_loader.get_monster_moves(monster_name)
        except Exception:
            continue
        for move in moves:
            if "summons" not in move:
                continue
            summon_moves.append(move)
            if _to_int(move.get("move_id"), default=None) == move_id:
                return move
        live_move = _current_summon_move_from_live_state(monster, summon_moves)
        if live_move:
            return live_move
    return None


def _current_summon_move_from_live_state(
    monster: Dict[str, Any],
    summon_moves: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    live_intent = _normalized_intent(monster.get("intent"))
    if not live_intent:
        return None

    live_damage = _to_int(monster.get("move_damage"), default=0)
    live_hits = max(1, _to_int(monster.get("move_hits"), default=1))
    matches: List[Dict[str, Any]] = []

    for move in summon_moves:
        if _normalized_intent(move.get("intent")) != live_intent:
            continue
        if "attack" in live_intent and live_damage > 0:
            move_damage = _to_int(move.get("damage"), default=0)
            move_hits = max(1, _to_int(move.get("hits"), default=1))
            if move_damage > 0 and move_damage * move_hits != live_damage * live_hits:
                continue
        matches.append(move)

    return matches[0] if len(matches) == 1 else None


def _normalized_intent(value) -> str:
    normalized = _normalize(value)
    return normalized[6:] if normalized.startswith("intent") else normalized


def _canonical_monster_data_name(monster_name: str) -> Optional[str]:
    try:
        data = game_data_loader.get_enhanced_monster_data(monster_name)
    except Exception:
        data = None
    if not data:
        return None
    return _safe_str(data.get("name") or monster_name)


def _summon_count_from_move(move: Dict[str, Any], default_count: int) -> int:
    count = move.get("summon_count")
    if isinstance(count, dict):
        values = [
            _to_int(value, default=None)
            for value in count.values()
        ]
        values = [value for value in values if value is not None]
        return max(values, default=default_count)
    return max(0, _to_int(count, default_count))


def _end_turn_summon_open_slots(
    monsters: List[Dict[str, Any]],
    summoner: Dict[str, Any],
    summon_names: List[str],
) -> int:
    max_minions = _summoner_max_minions(summoner, summon_names)
    summon_identifiers = {_normalize(name) for name in summon_names}
    live_minions = sum(
        1
        for monster in monsters
        if (
            _snapshot_monster_active(monster)
            and (
                _normalize(monster.get("name")) in summon_identifiers
                or _normalize(monster.get("id")) in summon_identifiers
            )
        )
    )
    return max(0, max_minions - live_minions)


def _summoner_max_minions(summoner: Dict[str, Any], summon_names: List[str]) -> int:
    data = None
    for monster_name in (summoner.get("name"), summoner.get("id")):
        if not monster_name:
            continue
        try:
            data = game_data_loader.get_enhanced_monster_data(monster_name)
        except Exception:
            data = None
        if data:
            break
    mechanics = data.get("special_mechanics", {}) if data else {}
    return max(
        len(summon_names),
        _to_int(mechanics.get("max_minions"), default=len(summon_names)),
    )


def _summoned_monster_snapshot(
    child_name: str,
    parent: Dict[str, Any],
    child_index: int,
) -> Optional[Dict[str, Any]]:
    try:
        data = game_data_loader.get_enhanced_monster_data(child_name)
    except Exception:
        data = None
    if not data:
        return None

    hp = _summoned_monster_hp(data)
    if hp <= 0:
        return None

    move = _first_monster_move(data)
    damage = _move_damage(move)
    hits = max(1, _to_int((move or {}).get("hits"), default=1))
    move_id = _to_int((move or {}).get("move_id"), default=0)
    intent = _safe_str((move or {}).get("intent") or "UNKNOWN")
    if intent and not intent.startswith("Intent."):
        intent = f"Intent.{intent}"

    return {
        "name": _safe_str(data.get("name") or child_name),
        "id": _safe_str(data.get("monster_id") or child_name),
        "hp": hp,
        "max_hp": hp,
        "block": 0,
        "intent": intent,
        "move_damage": damage,
        "move_hits": hits,
        "move_id": move_id,
        "gone": False,
        "half_dead": False,
        "powers": [{"id": "Minion", "name": "Minion", "amount": -1}],
        "summoned_by": _safe_str(parent.get("name")),
        "summon_child_index": child_index,
    }


def _summoned_monster_hp(data: Dict[str, Any]) -> int:
    hp_ranges = data.get("hp_ranges", {}) if data else {}
    for key in ("normal", "base"):
        hp_range = hp_ranges.get(key)
        if isinstance(hp_range, dict):
            return max(
                0,
                _to_int(hp_range.get("max"), default=0),
                _to_int(hp_range.get("min"), default=0),
            )
    for hp_range in hp_ranges.values():
        if isinstance(hp_range, dict):
            return max(
                0,
                _to_int(hp_range.get("max"), default=0),
                _to_int(hp_range.get("min"), default=0),
            )
    return 0


def _first_monster_move(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    moves = data.get("moves", []) if data else []
    if not isinstance(moves, list):
        return None
    return next((move for move in moves if isinstance(move, dict)), None)


def _move_damage(move: Optional[Dict[str, Any]]) -> int:
    if not isinstance(move, dict):
        return 0
    damage = move.get("damage", 0)
    if isinstance(damage, dict):
        values = [_to_int(value, default=None) for value in damage.values()]
        values = [value for value in values if value is not None]
        return max(values, default=0)
    return max(0, _to_int(damage, default=0))


def _darkling_revival_ready(monster: Dict[str, Any]) -> bool:
    return (
        _darkling_half_dead(monster)
        and _normalize(monster.get("intent")) in {"buff", "intentbuff"}
    )


def _diff_snapshots(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
    ignored_keys: Optional[set] = None,
) -> Dict[str, Dict[str, Any]]:
    diffs: Dict[str, Dict[str, Any]] = {}
    ignored_keys = ignored_keys or set()
    for field in ("current_hp", "block", "energy"):
        _add_diff(
            diffs,
            f"player.{field}",
            expected.get("player", {}).get(field),
            actual.get("player", {}).get(field),
            ignored_keys,
        )

    expected_monsters = expected.get("monsters", [])
    actual_monsters = actual.get("monsters", [])
    count = max(len(expected_monsters), len(actual_monsters))
    for index in range(count):
        expected_monster = expected_monsters[index] if index < len(expected_monsters) else {}
        actual_monster = actual_monsters[index] if index < len(actual_monsters) else {}
        for field in ("hp", "block", "gone", "half_dead", "intent"):
            _add_diff(
                diffs,
                f"monsters[{index}].{field}",
                expected_monster.get(field),
                actual_monster.get(field),
                ignored_keys,
            )
    return diffs


def _expected_combat_finished(expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
    if actual.get("in_combat"):
        return False
    if _to_int(actual.get("player", {}).get("current_hp")) <= 0:
        return False
    return not any(
        _snapshot_monster_active(monster)
        for monster in expected.get("monsters", [])
    )


def _nilrys_codex_screen_boundary(pending: Dict[str, Any], actual: Dict[str, Any]) -> bool:
    before = pending.get("before") or {}
    if not _snapshot_has_relic(before, "Nilry's Codex"):
        return False
    action_type = (pending.get("action") or {}).get("type")
    if action_type not in {"EndTurnAction", "CardRewardAction", "CancelAction"}:
        return False
    if not actual.get("in_combat"):
        return False
    return _to_int(actual.get("player", {}).get("current_hp")) > 0


def _headbutt_select_delayed_effects(snapshot: Dict[str, Any], card) -> Dict[str, Any]:
    if _known_card_name(card, BASE_ATTACK_DAMAGE) != "Headbutt":
        return {}
    effects: Dict[str, Any] = {"headbutt_select": True}
    block = 0
    rage_block = _rage_attack_block(snapshot.get("player", {}))
    if rage_block > 0:
        effects["rage_block"] = rage_block
        block += rage_block
    fan_block = _ornamental_fan_attack_block(snapshot)
    if fan_block > 0:
        effects["ornamental_fan_block"] = fan_block
        block += fan_block
    if block > 0:
        effects["block"] = block
    energy = _nunchaku_energy_gain(snapshot, card)
    if energy > 0:
        effects["energy"] = energy
    return effects


def _will_apply_pending_headbutt_select_effects(action, snapshot: Dict[str, Any]) -> bool:
    if type(action).__name__ != "CardSelectAction":
        return False
    return _pending_headbutt_select_effects_match(snapshot)


def _pending_headbutt_select_effects_match(snapshot: Dict[str, Any]) -> bool:
    effects = _pending_headbutt_select_effects
    if not effects or not snapshot.get("in_combat"):
        return False
    if _to_int(snapshot.get("player", {}).get("current_hp")) <= 0:
        return False
    return (
        _to_int(snapshot.get("floor")) == _to_int(effects.get("floor"))
        and _to_int(snapshot.get("turn")) == _to_int(effects.get("turn"))
    )


def _apply_pending_headbutt_select_effects(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> None:
    effects = _pending_headbutt_select_effects
    if not effects or not _pending_headbutt_select_effects_match(before):
        return
    block = max(0, _to_int(effects.get("block")))
    if block > 0:
        _gain_player_block(expected, before, block)
    energy = max(0, _to_int(effects.get("energy")))
    if energy > 0:
        expected["player"]["energy"] += energy
    for field, value in (effects.get("player_fields") or {}).items():
        if field in {"current_hp", "block", "energy"}:
            expected.setdefault("player", {})[field] = value
    monster_fields = effects.get("monster_fields") or {}
    monsters = expected.get("monsters") or []
    for index, fields in monster_fields.items():
        if not isinstance(index, int) or index < 0 or index >= len(monsters):
            continue
        for field, value in fields.items():
            if field in {"block", "intent"}:
                monsters[index][field] = value


def _burning_pact_select_delayed_effects(
    snapshot: Dict[str, Any],
    card,
) -> Dict[str, Any]:
    if _known_card_name(card, {"Burning Pact": 0}) != "Burning Pact":
        return {}
    effects: Dict[str, Any] = {"burning_pact_select": True, "exhaust_events": 1}
    feel_no_pain = max(
        0,
        _snapshot_power_amount(snapshot.get("player", {}), "Feel No Pain"),
    )
    if feel_no_pain > 0:
        effects["block"] = feel_no_pain
    if _snapshot_has_relic(snapshot, "Charon's Ashes"):
        effects["charons_ashes_events"] = 1
    panache_damage = _panache_delayed_card_play_damage(snapshot)
    if panache_damage > 0:
        effects["panache_damage"] = panache_damage
    return effects


def _panache_delayed_card_play_damage(snapshot: Dict[str, Any]) -> int:
    player = snapshot.get("player", {})
    if not _snapshot_has_power(player, "Panache"):
        return 0
    return PANACHE_DAMAGE if _snapshot_power_amount(player, "Panache") <= 1 else 0


def _will_apply_pending_burning_pact_select_effects(
    action,
    snapshot: Dict[str, Any],
) -> bool:
    if type(action).__name__ != "CardSelectAction":
        return False
    return _pending_burning_pact_select_effects_match(snapshot)


def _pending_burning_pact_select_effects_match(snapshot: Dict[str, Any]) -> bool:
    effects = _pending_burning_pact_select_effects
    if not effects or not snapshot.get("in_combat"):
        return False
    if _to_int(snapshot.get("player", {}).get("current_hp")) <= 0:
        return False
    return (
        _to_int(snapshot.get("floor")) == _to_int(effects.get("floor"))
        and _to_int(snapshot.get("turn")) == _to_int(effects.get("turn"))
    )


def _apply_pending_burning_pact_select_effects(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    action=None,
) -> None:
    effects = _pending_burning_pact_select_effects
    if not effects or not _pending_burning_pact_select_effects_match(before):
        return
    sentinel_energy = _selected_sentinel_exhaust_energy(action)
    if sentinel_energy > 0:
        expected["player"]["energy"] += sentinel_energy
    block = max(0, _to_int(effects.get("block")))
    if block > 0:
        _gain_player_block(expected, before, block)
    _apply_charons_ashes_damage_events(
        expected,
        before,
        max(0, _to_int(effects.get("charons_ashes_events"))),
    )
    _apply_panache_damage(expected, effects.get("panache_damage", 0))


def _true_grit_select_delayed_effects(
    snapshot: Dict[str, Any],
    card,
) -> Dict[str, Any]:
    if _known_card_name(card, BASE_SKILL_BLOCK) != "True Grit":
        return {}
    trigger_count = _card_play_count(snapshot, card)
    if (
        trigger_count <= 0
        or _snapshot_power_amount(snapshot.get("player", {}), "Juggernaut") <= 0
    ):
        return {}
    return {
        "true_grit_select": True,
        "juggernaut_block_triggers": trigger_count,
    }


def _will_apply_pending_true_grit_select_effects(
    action,
    snapshot: Dict[str, Any],
) -> bool:
    if type(action).__name__ != "CardSelectAction":
        return False
    return _pending_true_grit_select_effects_match(snapshot)


def _pending_true_grit_select_effects_match(snapshot: Dict[str, Any]) -> bool:
    effects = _pending_true_grit_select_effects
    if not effects or not snapshot.get("in_combat"):
        return False
    if _to_int(snapshot.get("player", {}).get("current_hp")) <= 0:
        return False
    return (
        _to_int(snapshot.get("floor")) == _to_int(effects.get("floor"))
        and _to_int(snapshot.get("turn")) == _to_int(effects.get("turn"))
    )


def _apply_pending_true_grit_select_effects(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    action=None,
) -> None:
    effects = _pending_true_grit_select_effects
    if not effects or not _pending_true_grit_select_effects_match(before):
        return
    sentinel_energy = _selected_sentinel_exhaust_energy(action)
    if sentinel_energy > 0:
        expected["player"]["energy"] += sentinel_energy
    _apply_juggernaut_block_triggers(
        expected,
        before,
        max(0, _to_int(effects.get("juggernaut_block_triggers"))),
    )


def _armaments_select_delayed_effects(
    snapshot: Dict[str, Any],
    card,
) -> Dict[str, Any]:
    if _known_card_name(card, BASE_SKILL_BLOCK) != "Armaments":
        return {}
    if card_upgrade_count(card) > 0:
        return {}
    trigger_count = _card_play_count(snapshot, card)
    if (
        trigger_count <= 0
        or _snapshot_power_amount(snapshot.get("player", {}), "Juggernaut") <= 0
    ):
        return {}
    return {
        "armaments_select": True,
        "juggernaut_block_triggers": trigger_count,
    }


def _will_apply_pending_armaments_select_effects(
    action,
    snapshot: Dict[str, Any],
) -> bool:
    if type(action).__name__ != "CardSelectAction":
        return False
    return _pending_armaments_select_effects_match(snapshot)


def _pending_armaments_select_effects_match(snapshot: Dict[str, Any]) -> bool:
    effects = _pending_armaments_select_effects
    if not effects or not snapshot.get("in_combat"):
        return False
    if _to_int(snapshot.get("player", {}).get("current_hp")) <= 0:
        return False
    return (
        _to_int(snapshot.get("floor")) == _to_int(effects.get("floor"))
        and _to_int(snapshot.get("turn")) == _to_int(effects.get("turn"))
    )


def _apply_pending_armaments_select_effects(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> None:
    effects = _pending_armaments_select_effects
    if not effects or not _pending_armaments_select_effects_match(before):
        return
    _apply_juggernaut_block_triggers(
        expected,
        before,
        max(0, _to_int(effects.get("juggernaut_block_triggers"))),
    )


def _arm_headbutt_select_boundary_if_applicable(
    pending: Dict[str, Any],
    actual: Dict[str, Any],
    diffs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    global _pending_headbutt_select_effects

    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return
    effects = _headbutt_select_effects_to_apply(pending, diffs)
    if not effects or not actual.get("in_combat"):
        return
    if _to_int(actual.get("player", {}).get("current_hp")) <= 0:
        return
    _pending_headbutt_select_effects = {
        "floor": actual.get("floor"),
        "turn": actual.get("turn"),
        **effects,
    }


def _arm_burning_pact_select_boundary_if_applicable(
    pending: Dict[str, Any],
    actual: Dict[str, Any],
    diffs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    global _pending_burning_pact_select_effects

    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return
    effects = _burning_pact_select_effects_to_apply(pending, diffs)
    if not effects or not actual.get("in_combat"):
        return
    if _to_int(actual.get("player", {}).get("current_hp")) <= 0:
        return
    _pending_burning_pact_select_effects = {
        "floor": actual.get("floor"),
        "turn": actual.get("turn"),
        **effects,
    }


def _arm_true_grit_select_boundary_if_applicable(
    pending: Dict[str, Any],
    actual: Dict[str, Any],
) -> None:
    global _pending_true_grit_select_effects

    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return
    effects = dict(action.get("delayed_true_grit_select_effects") or {})
    if not effects or not actual.get("in_combat"):
        return
    if _to_int(actual.get("player", {}).get("current_hp")) <= 0:
        return
    _pending_true_grit_select_effects = {
        "floor": actual.get("floor"),
        "turn": actual.get("turn"),
        **effects,
    }


def _arm_armaments_select_boundary_if_applicable(
    pending: Dict[str, Any],
    actual: Dict[str, Any],
) -> None:
    global _pending_armaments_select_effects

    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return
    effects = dict(action.get("delayed_armaments_select_effects") or {})
    if not effects or not actual.get("in_combat"):
        return
    if _to_int(actual.get("player", {}).get("current_hp")) <= 0:
        return
    _pending_armaments_select_effects = {
        "floor": actual.get("floor"),
        "turn": actual.get("turn"),
        **effects,
    }


def _burning_pact_select_effects_to_apply(
    pending: Dict[str, Any],
    diffs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    action = pending.get("action") or {}
    effects = dict(action.get("delayed_burning_pact_select_effects") or {})
    expected = pending.get("expected") or {}
    for key in diffs or {}:
        if key == "player.block" and "block" in effects:
            effects.setdefault("player_fields", {})["block"] = (
                expected.get("player") or {}
            ).get("block")
    return effects


def _headbutt_select_effects_to_apply(
    pending: Dict[str, Any],
    diffs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    action = pending.get("action") or {}
    effects = dict(action.get("delayed_headbutt_select_effects") or {})
    expected = pending.get("expected") or {}
    for key in diffs or {}:
        if key.startswith("player."):
            field = key.split(".", 1)[1]
            if field in {"current_hp", "block", "energy"}:
                effects.setdefault("player_fields", {})[field] = (
                    expected.get("player") or {}
                ).get(field)
            continue
        monster_index, field = _parse_monster_diff_key(key)
        if monster_index is None or field not in {"block", "intent"}:
            continue
        monsters = expected.get("monsters") or []
        if 0 <= monster_index < len(monsters):
            effects.setdefault("monster_fields", {}).setdefault(monster_index, {})[
                field
            ] = monsters[monster_index].get(field)
    return effects


def _burning_pact_select_delayed_diff_boundary(
    pending: Dict[str, Any],
    actual: Dict[str, Any],
    diffs: Dict[str, Dict[str, Any]],
) -> bool:
    if not diffs:
        return False
    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return False
    if _snapshot_known_card_name(action.get("card") or {}, {"Burning Pact": 0}) != "Burning Pact":
        return False
    if not actual.get("in_combat"):
        return False
    if _to_int(actual.get("player", {}).get("current_hp")) <= 0:
        return False
    if _to_int(actual.get("floor")) != _to_int(pending.get("floor")):
        return False
    if _to_int(actual.get("turn")) != _to_int(pending.get("turn")):
        return False
    delayed_effects = action.get("delayed_burning_pact_select_effects") or {}
    return set(diffs).issubset({"player.block"}) and "block" in delayed_effects


def _headbutt_select_delayed_diff_boundary(
    pending: Dict[str, Any],
    actual: Dict[str, Any],
    diffs: Dict[str, Dict[str, Any]],
) -> bool:
    if not diffs:
        return False
    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return False
    if _snapshot_known_card_name(action.get("card") or {}, {"Headbutt": 0}) != "Headbutt":
        return False
    if not actual.get("in_combat"):
        return False
    if _to_int(actual.get("player", {}).get("current_hp")) <= 0:
        return False
    if _to_int(actual.get("floor")) != _to_int(pending.get("floor")):
        return False
    if _to_int(actual.get("turn")) != _to_int(pending.get("turn")):
        return False
    return all(_headbutt_select_delayed_diff_key(pending, key) for key in diffs)


def _headbutt_select_delayed_diff_key(pending: Dict[str, Any], key: str) -> bool:
    if key == "player.current_hp":
        return _action_targets_guardian(
            pending.get("action") or {},
            pending.get("before") or {},
        )
    delayed_effects = (pending.get("action") or {}).get("delayed_headbutt_select_effects") or {}
    if key == "player.block":
        return "block" in delayed_effects or _action_triggers_guardian_sharp_hide(
            pending.get("action") or {},
            pending.get("before") or {},
        )
    if key == "player.energy":
        return "energy" in delayed_effects
    monster_index, field = _parse_monster_diff_key(key)
    if monster_index is None or field not in {"block", "intent"}:
        return False
    monsters = (pending.get("before") or {}).get("monsters") or []
    if monster_index < 0 or monster_index >= len(monsters):
        return False
    if _is_guardian_monster(monsters[monster_index]):
        return True
    return field == "block" and _action_triggers_malleable_block(
        pending.get("action") or {},
        pending,
        monster_index,
    )


def _action_triggers_malleable_block(
    action: Dict[str, Any],
    pending: Dict[str, Any],
    monster_index: int,
) -> bool:
    before = pending.get("before") or {}
    target_index = action.get("target_index")
    if target_index is None:
        target_index = _single_alive_monster_index(before)
    if not isinstance(target_index, int) or target_index != monster_index:
        return False

    before_monsters = before.get("monsters") or []
    expected_monsters = (pending.get("expected") or {}).get("monsters") or []
    if monster_index < 0 or monster_index >= len(before_monsters):
        return False
    if monster_index >= len(expected_monsters):
        return False

    before_malleable = max(
        0,
        _snapshot_power_amount(before_monsters[monster_index], "Malleable"),
    )
    if before_malleable <= 0:
        return False
    expected_malleable = max(
        0,
        _snapshot_power_amount(expected_monsters[monster_index], "Malleable"),
    )
    return expected_malleable > before_malleable


def _action_triggers_guardian_sharp_hide(
    action: Dict[str, Any],
    snapshot: Dict[str, Any],
) -> bool:
    if not _action_targets_guardian(action, snapshot):
        return False
    target_index = action.get("target_index")
    if isinstance(target_index, int):
        return _sharp_hide_reflection_damage(snapshot, target_index) > 0
    return _sharp_hide_reflection_damage(snapshot, all_targets=True) > 0


def _parse_monster_diff_key(key: str) -> tuple[Optional[int], Optional[str]]:
    if not key.startswith("monsters[") or "]." not in key:
        return None, None
    prefix, field = key.split("].", 1)
    try:
        index = int(prefix[len("monsters["):])
    except ValueError:
        return None, None
    return index, field


def _consume_headbutt_select_boundary_if_applicable(pending: Dict[str, Any]) -> None:
    global _pending_headbutt_select_effects

    action = pending.get("action") or {}
    if action.get("type") != "CardSelectAction":
        return
    if _pending_headbutt_select_effects_match(pending.get("before") or {}):
        _pending_headbutt_select_effects = None


def _consume_burning_pact_select_boundary_if_applicable(pending: Dict[str, Any]) -> None:
    global _pending_burning_pact_select_effects

    action = pending.get("action") or {}
    if action.get("type") != "CardSelectAction":
        return
    if _pending_burning_pact_select_effects_match(pending.get("before") or {}):
        _pending_burning_pact_select_effects = None


def _consume_true_grit_select_boundary_if_applicable(pending: Dict[str, Any]) -> None:
    global _pending_true_grit_select_effects

    action = pending.get("action") or {}
    if action.get("type") != "CardSelectAction":
        return
    if _pending_true_grit_select_effects_match(pending.get("before") or {}):
        _pending_true_grit_select_effects = None


def _consume_armaments_select_boundary_if_applicable(pending: Dict[str, Any]) -> None:
    global _pending_armaments_select_effects

    action = pending.get("action") or {}
    if action.get("type") != "CardSelectAction":
        return
    if _pending_armaments_select_effects_match(pending.get("before") or {}):
        _pending_armaments_select_effects = None


def _snapshot_monster_active(monster: Dict[str, Any]) -> bool:
    if monster.get("gone"):
        return False
    if monster.get("half_dead"):
        return True
    return _to_int(monster.get("hp")) > 0


def _ignored_diff_keys(pending: Dict[str, Any], actual: Optional[Dict[str, Any]] = None) -> set:
    action = pending.get("action", {})
    ignored = set()
    if _sword_boomerang_random_target_boundary(pending):
        ignored.update(_monster_state_diff_keys(pending, actual))
        return ignored
    if _havoc_empty_draw_discard_shuffle_boundary(pending):
        ignored.update(_monster_state_diff_keys(pending, actual))
        ignored.update(_player_state_diff_keys())
        return ignored
    if _play_top_cards_empty_draw_discard_shuffle_boundary(pending):
        ignored.update(_monster_state_diff_keys(pending, actual))
        ignored.update(_player_state_diff_keys())
        return ignored
    if _havoc_random_top_card_target_boundary(pending):
        ignored.update(_monster_state_diff_keys(pending, actual))
        return ignored
    if _play_top_cards_random_attack_target_boundary(pending):
        ignored.update(_monster_state_diff_keys(pending, actual))
        return ignored

    if _juggernaut_random_target_boundary(pending):
        ignored.update(_monster_state_diff_keys(pending, actual))

    ignored.update(_slime_split_ignored_diff_keys(pending, actual))
    ignored.update(_darkling_half_dead_animation_ignored_diff_keys(pending, actual))
    ignored.update(_writhing_mass_random_intent_ignored_diff_keys(pending, actual))

    if action.get("type") == "EndTurnAction":
        ignored.add("player.energy")
        ignored.update(_end_turn_summon_ignored_diff_keys(pending))
        ignored.update(
            _gremlin_leader_random_summon_ignored_diff_keys(pending, actual)
        )
        ignored.update(
            _bronze_automaton_random_orb_summon_ignored_diff_keys(pending, actual)
        )
        monster_count = _monster_diff_count(pending, actual)
        mystic_support_turn = _has_mystic_support_turn(pending.get("before") or {})
        for index in range(monster_count):
            ignored.add(f"monsters[{index}].intent")
            ignored.add(f"monsters[{index}].block")
            if mystic_support_turn:
                ignored.add(f"monsters[{index}].hp")
        return ignored
    return ignored


def _end_turn_summon_ignored_diff_keys(pending: Dict[str, Any]) -> set:
    expected = pending.get("expected") or {}
    ignored = set()
    for index, monster in enumerate(expected.get("monsters", []) or []):
        if not monster.get("summoned_by"):
            continue
        ignored.add(f"monsters[{index}].hp")
    return ignored


def _gremlin_leader_random_summon_ignored_diff_keys(
    pending: Dict[str, Any],
    actual: Optional[Dict[str, Any]],
) -> set:
    before = pending.get("before") or {}
    actual = actual or {}
    if not any(
        _is_gremlin_leader_rally(monster)
        for monster in before.get("monsters", []) or []
    ):
        return set()
    before_minion_count = _active_random_gremlin_minion_count(before)
    actual_minion_count = _active_random_gremlin_minion_count(actual)
    if actual_minion_count <= before_minion_count:
        return set()
    return _monster_state_diff_keys(pending, actual)


def _bronze_automaton_random_orb_summon_ignored_diff_keys(
    pending: Dict[str, Any],
    actual: Optional[Dict[str, Any]],
) -> set:
    before = pending.get("before") or {}
    expected = pending.get("expected") or {}
    actual = actual or {}
    before_monsters = before.get("monsters", []) or []
    if _active_bronze_orb_count(before) != 0:
        return set()
    if not any(_is_bronze_automaton_orb_summon(monster) for monster in before_monsters):
        return set()
    if not _is_bronze_automaton_orb_summon_snapshot(expected):
        return set()
    if not _is_bronze_automaton_orb_summon_snapshot(actual):
        return set()
    expected_boss = _single_active_bronze_automaton(expected)
    actual_boss = _single_active_bronze_automaton(actual)
    if expected_boss is None or actual_boss is None:
        return set()
    for field in ("hp", "gone", "half_dead"):
        if expected_boss.get(field) != actual_boss.get(field):
            return set()
    return _monster_state_diff_keys(pending, actual)


def _is_bronze_automaton_orb_summon(monster: Dict[str, Any]) -> bool:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    if "bronzeautomaton" not in identifiers:
        return False
    return len(_end_turn_summon_names(monster)) >= 2


def _active_bronze_orb_count(snapshot: Dict[str, Any]) -> int:
    return sum(
        1
        for monster in snapshot.get("monsters", []) or []
        if _snapshot_monster_active(monster)
        and _is_bronze_orb(monster)
    )


def _is_bronze_automaton_orb_summon_snapshot(snapshot: Dict[str, Any]) -> bool:
    monsters = snapshot.get("monsters", []) or []
    return (
        len(monsters) == 3
        and _active_bronze_orb_count(snapshot) == 2
        and _single_active_bronze_automaton(snapshot) is not None
    )


def _single_active_bronze_automaton(
    snapshot: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    matches = [
        monster
        for monster in snapshot.get("monsters", []) or []
        if _snapshot_monster_active(monster)
        and _is_bronze_automaton(monster)
    ]
    return matches[0] if len(matches) == 1 else None


def _is_bronze_orb(monster: Dict[str, Any]) -> bool:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    return "bronzeorb" in identifiers


def _is_bronze_automaton(monster: Dict[str, Any]) -> bool:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    return "bronzeautomaton" in identifiers


def _is_gremlin_leader_rally(monster: Dict[str, Any]) -> bool:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    return (
        "gremlinleader" in identifiers
        and _snapshot_monster_active(monster)
        and _normalized_intent(monster.get("intent")) == "unknown"
        and _to_int(monster.get("move_id"), default=-1) == 2
    )


def _active_random_gremlin_minion_count(snapshot: Dict[str, Any]) -> int:
    return sum(
        1
        for monster in snapshot.get("monsters", []) or []
        if _snapshot_monster_active(monster)
        and _is_random_gremlin_minion(monster)
    )


def _is_random_gremlin_minion(monster: Dict[str, Any]) -> bool:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    return any("gremlin" in identifier for identifier in identifiers) and (
        "gremlinleader" not in identifiers
    )


def _monster_diff_count(
    pending: Dict[str, Any],
    actual: Optional[Dict[str, Any]] = None,
) -> int:
    snapshots = [
        pending.get("before") or {},
        pending.get("expected") or {},
        actual or {},
    ]
    return max(len(snapshot.get("monsters") or []) for snapshot in snapshots)


def _monster_state_diff_keys(
    pending: Dict[str, Any],
    actual: Optional[Dict[str, Any]] = None,
) -> set:
    ignored = set()
    for index in range(_monster_diff_count(pending, actual)):
        for field in ("hp", "block", "gone", "half_dead", "intent"):
            ignored.add(f"monsters[{index}].{field}")
    return ignored


def _writhing_mass_random_intent_ignored_diff_keys(
    pending: Dict[str, Any],
    actual: Optional[Dict[str, Any]] = None,
) -> set:
    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return set()

    actual = actual or {}
    before = pending.get("before") or {}
    expected = pending.get("expected") or {}
    before_monsters = before.get("monsters") or []
    expected_monsters = expected.get("monsters") or []
    actual_monsters = actual.get("monsters") or []

    ignored = set()
    count = max(len(before_monsters), len(expected_monsters), len(actual_monsters))
    for index in range(count):
        before_monster = before_monsters[index] if index < len(before_monsters) else {}
        expected_monster = (
            expected_monsters[index] if index < len(expected_monsters) else {}
        )
        actual_monster = actual_monsters[index] if index < len(actual_monsters) else {}
        if not _snapshot_monster_is_writhing_mass(before_monster):
            continue
        if not (
            _snapshot_monster_active(before_monster)
            and _snapshot_monster_active(expected_monster)
            and _snapshot_monster_active(actual_monster)
        ):
            continue
        before_hp = _to_int(before_monster.get("hp"))
        expected_hp = _to_int(expected_monster.get("hp"))
        actual_hp = _to_int(actual_monster.get("hp"))
        if expected_hp != actual_hp or before_hp <= expected_hp:
            continue
        if expected_monster.get("intent") == actual_monster.get("intent"):
            continue
        ignored.add(f"monsters[{index}].intent")
    return ignored


def _snapshot_monster_is_writhing_mass(monster: Dict[str, Any]) -> bool:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    return "writhingmass" in identifiers


def _player_state_diff_keys() -> set:
    return {
        "player.current_hp",
        "player.block",
        "player.energy",
    }


def _juggernaut_random_target_boundary(pending: Dict[str, Any]) -> bool:
    before = pending.get("before") or {}
    if _snapshot_power_amount(before.get("player", {}), "Juggernaut") <= 0:
        return False
    if _active_monster_count(before) <= 1:
        return False

    action = pending.get("action") or {}
    action_type = action.get("type")
    if action_type == "CardSelectAction":
        return (
            _pending_true_grit_select_effects_match(before)
            or _pending_armaments_select_effects_match(before)
        )
    if action_type != "PlayCardAction":
        return False

    card = action.get("card") or {}
    if _snapshot_card_is_attack(card):
        return False
    return _expected_player_block_gain(pending) > 0


def _active_monster_count(snapshot: Dict[str, Any]) -> int:
    return sum(
        1
        for monster in snapshot.get("monsters", []) or []
        if _snapshot_monster_active(monster)
    )


def _expected_player_block_gain(pending: Dict[str, Any]) -> int:
    before_block = _to_int(
        ((pending.get("before") or {}).get("player") or {}).get("block")
    )
    expected_block = _to_int(
        ((pending.get("expected") or {}).get("player") or {}).get("block")
    )
    return max(0, expected_block - before_block)


def _slime_split_ignored_diff_keys(
    pending: Dict[str, Any],
    actual: Optional[Dict[str, Any]] = None,
) -> set:
    actual = actual or {}
    if not _slime_split_context(pending, actual):
        return set()

    if _slime_split_structure_changed(pending, actual):
        return _monster_state_diff_keys(pending, actual)

    ignored = set()
    expected_monsters = (pending.get("expected") or {}).get("monsters") or []
    actual_monsters = actual.get("monsters") or []
    for index, (expected_monster, actual_monster) in enumerate(
        zip(expected_monsters, actual_monsters)
    ):
        if expected_monster.get("intent") == actual_monster.get("intent"):
            continue
        if _slime_split_monster_pair(expected_monster, actual_monster):
            ignored.add(f"monsters[{index}].intent")
    return ignored


def _slime_split_context(pending: Dict[str, Any], actual: Dict[str, Any]) -> bool:
    snapshots = [
        pending.get("before") or {},
        pending.get("expected") or {},
        actual or {},
    ]
    return any(
        _slime_split_visible(snapshot) or _has_split_ready_slime(snapshot)
        for snapshot in snapshots
    )


def _has_split_ready_slime(snapshot: Dict[str, Any]) -> bool:
    return any(
        _slime_split_ready(monster)
        for monster in snapshot.get("monsters", []) or []
    )


def _slime_split_structure_changed(
    pending: Dict[str, Any],
    actual: Dict[str, Any],
) -> bool:
    expected_monsters = (pending.get("expected") or {}).get("monsters") or []
    actual_monsters = actual.get("monsters") or []
    if len(expected_monsters) != len(actual_monsters):
        return True
    return _monster_lifecycle_signature(expected_monsters) != _monster_lifecycle_signature(
        actual_monsters
    )


def _monster_lifecycle_signature(monsters: List[Dict[str, Any]]) -> List[tuple]:
    return [
        (
            _normalize(monster.get("id")),
            _normalize(monster.get("name")),
            bool(monster.get("gone")),
            bool(monster.get("half_dead")),
            _to_int(monster.get("hp")) <= 0,
        )
        for monster in monsters
    ]


def _slime_split_monster_pair(
    expected_monster: Dict[str, Any],
    actual_monster: Dict[str, Any],
) -> bool:
    return _slime_split_monster(expected_monster) or _slime_split_monster(actual_monster)


def _slime_split_monster(monster: Dict[str, Any]) -> bool:
    return _is_slime_monster(monster) and (
        _snapshot_has_power(monster, "Split")
        or _slime_split_ready(monster)
        or bool(monster.get("gone"))
        or _to_int(monster.get("hp")) <= 0
    )


def _slime_split_ready(monster: Dict[str, Any]) -> bool:
    if not _is_slime_monster(monster):
        return False
    if bool(monster.get("gone")) or bool(monster.get("half_dead")):
        return False
    if not _snapshot_has_power(monster, "Split"):
        return False
    hp = _to_int(monster.get("hp"))
    max_hp = max(1, _to_int(monster.get("max_hp")))
    return hp > 0 and hp * 2 <= max_hp


def _is_slime_monster(monster: Dict[str, Any]) -> bool:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    return any("slime" in value for value in identifiers)


def _darkling_half_dead_animation_ignored_diff_keys(
    pending: Dict[str, Any],
    actual: Optional[Dict[str, Any]] = None,
) -> set:
    actual = actual or {}
    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return set()

    before_monsters = (pending.get("before") or {}).get("monsters") or []
    expected_monsters = (pending.get("expected") or {}).get("monsters") or []
    actual_monsters = actual.get("monsters") or []
    for index, before_monster in enumerate(before_monsters):
        if index >= len(expected_monsters) or index >= len(actual_monsters):
            continue
        if not _is_live_darkling(before_monster):
            continue
        if _darkling_half_dead(expected_monsters[index]) and _darkling_half_dead(
            actual_monsters[index]
        ):
            return {"player.energy"}
    return set()


def _is_live_darkling(monster: Dict[str, Any]) -> bool:
    return (
        _is_darkling_monster(monster)
        and not bool(monster.get("gone"))
        and not bool(monster.get("half_dead"))
        and _to_int(monster.get("hp")) > 0
    )


def _darkling_half_dead(monster: Dict[str, Any]) -> bool:
    return (
        _is_darkling_monster(monster)
        and bool(monster.get("gone"))
        and bool(monster.get("half_dead"))
        and _to_int(monster.get("hp")) <= 0
    )


def _is_darkling_monster(monster: Dict[str, Any]) -> bool:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    return "darkling" in identifiers


def _is_awakened_one_monster(monster: Dict[str, Any]) -> bool:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    return "awakenedone" in identifiers


def _awakened_one_half_dead(monster: Dict[str, Any]) -> bool:
    return (
        _is_awakened_one_monster(monster)
        and bool(monster.get("gone"))
        and bool(monster.get("half_dead"))
        and _to_int(monster.get("hp")) <= 0
    )


def _sword_boomerang_random_target_boundary(pending: Dict[str, Any]) -> bool:
    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return False
    if _snapshot_known_card_name(action.get("card") or {}, {"Sword Boomerang": 0}) != "Sword Boomerang":
        return False
    before = pending.get("before") or {}
    active_count = sum(
        1
        for monster in before.get("monsters", []) or []
        if _snapshot_monster_active(monster)
    )
    return active_count > 1


def _havoc_random_top_card_target_boundary(pending: Dict[str, Any]) -> bool:
    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return False
    if _snapshot_known_card_name(action.get("card") or {}, HAVOC_CARDS) != "Havoc":
        return False

    before = pending.get("before") or {}
    top_card = _draw_pile_top_card(before)
    if top_card is None or not _snapshot_card_is_attack(top_card):
        return False
    if _is_all_enemy_attack(top_card):
        return False

    active_count = sum(
        1
        for monster in before.get("monsters", []) or []
        if _snapshot_monster_active(monster)
    )
    return active_count > 1


def _havoc_empty_draw_discard_shuffle_boundary(pending: Dict[str, Any]) -> bool:
    action = pending.get("action") or {}
    if action.get("type") != "PlayCardAction":
        return False
    if _snapshot_known_card_name(action.get("card") or {}, HAVOC_CARDS) != "Havoc":
        return False

    before = pending.get("before") or {}
    draw_pile = before.get("draw_pile") or []
    if isinstance(draw_pile, list) and draw_pile:
        return False
    if _to_int(before.get("draw_pile_count")) > 0:
        return False

    discard_pile = before.get("discard_pile") or []
    if isinstance(discard_pile, list) and discard_pile:
        return True
    return _to_int(before.get("discard_pile_count")) > 0


def _play_top_cards_empty_draw_discard_shuffle_boundary(
    pending: Dict[str, Any],
) -> bool:
    action = pending.get("action") or {}
    if action.get("type") != "PotionAction":
        return False
    potion = action.get("potion") or {}
    if _normalize(_potion_attr(potion, "effect_type", "")) != "playtopcards":
        return False

    before = pending.get("before") or {}
    draw_pile = before.get("draw_pile") or []
    if isinstance(draw_pile, list) and draw_pile:
        return False
    if _to_int(before.get("draw_pile_count")) > 0:
        return False

    discard_pile = before.get("discard_pile") or []
    if isinstance(discard_pile, list) and discard_pile:
        return True
    return _to_int(before.get("discard_pile_count")) > 0


def _play_top_cards_random_attack_target_boundary(pending: Dict[str, Any]) -> bool:
    action = pending.get("action") or {}
    if action.get("type") != "PotionAction":
        return False
    potion = action.get("potion") or {}
    if _normalize(_potion_attr(potion, "effect_type", "")) != "playtopcards":
        return False

    before = pending.get("before") or {}
    active_count = sum(
        1
        for monster in before.get("monsters", []) or []
        if _snapshot_monster_active(monster)
    )
    if active_count <= 1:
        return False

    draw_pile = before.get("draw_pile") or []
    if not isinstance(draw_pile, list):
        return False
    count = max(0, _to_int(_potion_attr(potion, "effect_value", 0)))
    for top_card in reversed(draw_pile[-count:] if count else []):
        if not isinstance(top_card, dict):
            continue
        if not _snapshot_card_is_attack(top_card):
            continue
        if _is_all_enemy_attack(top_card):
            continue
        return True
    return False


def _add_diff(
    diffs: Dict[str, Dict[str, Any]],
    key: str,
    expected: Any,
    actual: Any,
    ignored_keys: set,
) -> None:
    if key in ignored_keys:
        return
    if expected != actual:
        diffs[key] = {"expected": expected, "actual": actual}


def _classify_reason(
    pending: Dict[str, Any],
    actual: Dict[str, Any],
    diffs: Dict[str, Dict[str, Any]],
) -> str:
    before = pending.get("before", {})
    action = pending.get("action", {})
    player_diff = any(key.startswith("player.") for key in diffs)
    monster_diff = any(key.startswith("monsters[") for key in diffs)

    if (
        action.get("type") == "PlayCardAction"
        and player_diff
        and _action_targets_guardian(action, before)
        and _guardian_sharp_hide_visible(before)
    ):
        return "guardian_sharp_hide_reflection"

    if (
        action.get("type") == "EndTurnAction"
        and "player.current_hp" in diffs
        and _hand_contains_burn(before)
    ):
        return "end_turn_burn_damage"

    if monster_diff and _slime_split_visible(before):
        return "slime_split_state_mismatch"

    if monster_diff:
        return "monster_state_mismatch"
    if player_diff:
        return "player_state_mismatch"
    return "state_mismatch"


def _action_targets_guardian(action: Dict[str, Any], snapshot: Dict[str, Any]) -> bool:
    target_index = action.get("target_index")
    monsters = snapshot.get("monsters", [])
    if isinstance(target_index, int) and 0 <= target_index < len(monsters):
        monster = monsters[target_index]
        return _normalize(monster.get("id")) == "theguardian" or _normalize(monster.get("name")) == "theguardian"
    return any(
        _normalize(monster.get("id")) == "theguardian" or _normalize(monster.get("name")) == "theguardian"
        for monster in monsters
    )


def _guardian_sharp_hide_visible(snapshot: Dict[str, Any]) -> bool:
    for monster in snapshot.get("monsters", []):
        if not (
            _normalize(monster.get("id")) == "theguardian"
            or _normalize(monster.get("name")) == "theguardian"
        ):
            continue
        intent = _normalize(monster.get("intent"))
        if intent in {"attackbuff", "intentattackbuff"}:
            return True
    return False


def _hand_contains_burn(snapshot: Dict[str, Any]) -> bool:
    return any(_normalize(card.get("name")) == "burn" for card in snapshot.get("hand", []))


def _slime_split_visible(snapshot: Dict[str, Any]) -> bool:
    has_dead_boss = False
    live_slimes = 0
    for monster in snapshot.get("monsters", []):
        identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
        if any("slimeboss" in value for value in identifiers):
            has_dead_boss = bool(monster.get("gone")) or _to_int(monster.get("hp")) <= 0
        elif any("slime" in value for value in identifiers) and not monster.get("gone"):
            live_slimes += 1
    return has_dead_boss and live_slimes >= 2


def _incoming_damage_from_snapshot(snapshot: Dict[str, Any]) -> int:
    total = 0
    for monster in snapshot.get("monsters", []):
        total += _monster_attack_damage(monster)
    return total


def _monster_attack_damage(monster: Dict[str, Any]) -> int:
    if monster.get("gone") or monster.get("half_dead"):
        return 0
    if "attack" not in _normalize(monster.get("intent")):
        return 0
    damage = max(0, _to_int(monster.get("move_damage")))
    if damage <= 0:
        return 0
    return damage * max(1, _to_int(monster.get("move_hits"), default=1))


def _monster_attack_hits(monster: Dict[str, Any]) -> int:
    return max(1, _to_int(monster.get("move_hits"), default=1))


def _card_for_action(action, game):
    card = getattr(action, "card", None)
    if card is not None:
        return card
    card_index = _to_int(getattr(action, "card_index", -1), default=-1)
    hand = list(_safe_iterable(getattr(game, "hand", [])))
    if 0 <= card_index < len(hand):
        return hand[card_index]
    return None


def _potion_for_action(action, game):
    potion = getattr(action, "potion", None)
    if potion is not None:
        return potion
    potion_index = _to_int(getattr(action, "potion_index", -1), default=-1)
    potions = list(_safe_iterable(getattr(game, "potions", [])))
    if 0 <= potion_index < len(potions):
        return potions[potion_index]
    return None


def _target_index_for_action(action, game) -> Optional[int]:
    target_index = getattr(action, "target_index", None)
    if isinstance(target_index, int) and target_index >= 0:
        return target_index
    target = getattr(action, "target_monster", None)
    if target is None:
        monsters = list(_safe_iterable(getattr(game, "monsters", [])))
        alive_indexes = [
            index
            for index, monster in enumerate(monsters)
            if not getattr(monster, "is_gone", False)
            and not getattr(monster, "half_dead", False)
            and _to_int(getattr(monster, "current_hp", None)) > 0
        ]
        if len(alive_indexes) == 1:
            return alive_indexes[0]
        return None
    monsters = list(_safe_iterable(getattr(game, "monsters", [])))
    for index, monster in enumerate(monsters):
        if monster is target:
            return index
    monster_index = getattr(target, "monster_index", None)
    return monster_index if isinstance(monster_index, int) else None


def _action_summary(action, game) -> Dict[str, Any]:
    summary = {"type": type(action).__name__ if action is not None else None}
    for attr in ("card_index", "target_index", "potion_index", "use"):
        if hasattr(action, attr):
            summary[attr] = _json_scalar(getattr(action, attr))
    card = _card_for_action(action, game)
    if card is not None:
        summary["card"] = _card_summary(card)
    potion = _potion_for_action(action, game)
    if potion is not None:
        summary["potion"] = _potion_summary(potion)
    return summary


def _card_summary(card) -> Dict[str, Any]:
    return {
        "name": _safe_str(_card_attr(card, "name", "")),
        "id": _safe_str(_card_attr(card, "card_id", _card_attr(card, "id", ""))),
        "uuid": _safe_str(_card_attr(card, "uuid", "")),
        "type": _safe_str(
            _card_attr(card, "type", _card_attr(card, "card_type", ""))
        ),
        "cost": _card_cost(card),
        "damage": _card_damage(card),
        "block": _card_block(card),
        "upgrades": card_upgrade_count(card),
        "misc": _positive_card_misc(card),
    }


def _relic_summary(relic) -> Dict[str, Any]:
    return {
        "name": _safe_str(getattr(relic, "name", "")),
        "id": _safe_str(getattr(relic, "relic_id", getattr(relic, "id", ""))),
        "counter": _to_int(getattr(relic, "counter", 0)),
    }


def _potion_summary(potion) -> Dict[str, Any]:
    return {
        "name": _safe_str(_potion_attr(potion, "name", "")),
        "id": _safe_str(_potion_attr(potion, "potion_id", _potion_attr(potion, "id", ""))),
        "effect_type": _safe_str(_potion_attr(potion, "effect_type", "")),
        "effect_value": _json_scalar(_potion_attr(potion, "effect_value", 0)),
        "target_type": _safe_str(_potion_attr(potion, "target_type", "")),
    }


def _potion_identifiers(potion) -> set:
    if potion is None:
        return set()
    return {
        _normalize(_potion_attr(potion, "id", "")),
        _normalize(_potion_attr(potion, "potion_id", "")),
        _normalize(_potion_attr(potion, "name", "")),
    }


def _is_escape_potion_snapshot(potion) -> bool:
    if potion is None:
        return False
    if _normalize(_potion_attr(potion, "effect_type", "")) == "escape":
        return True
    return "smokebomb" in _potion_identifiers(potion)


def _power_summary(power) -> Dict[str, Any]:
    return {
        "id": _safe_str(getattr(power, "power_id", getattr(power, "id", ""))),
        "name": _safe_str(
            getattr(power, "power_name", getattr(power, "name", ""))
        ),
        "amount": _to_int(getattr(power, "amount", 0)),
    }


def _monster_summary(monster) -> Dict[str, Any]:
    return {
        "name": _safe_str(getattr(monster, "name", "")),
        "id": _safe_str(getattr(monster, "monster_id", getattr(monster, "id", ""))),
        "hp": _to_int(getattr(monster, "current_hp", None)),
        "max_hp": _to_int(getattr(monster, "max_hp", None)),
        "block": _to_int(getattr(monster, "block", None)),
        "intent": _safe_str(getattr(monster, "intent", "")),
        "move_damage": _to_int(getattr(monster, "move_adjusted_damage", None)),
        "move_hits": _to_int(getattr(monster, "move_hits", None), default=1),
        "move_id": _to_int(getattr(monster, "move_id", None), default=-1),
        "gone": bool(getattr(monster, "is_gone", False)),
        "half_dead": bool(getattr(monster, "half_dead", False)),
        "powers": [_power_summary(power) for power in _safe_iterable(getattr(monster, "powers", []))],
    }


def _is_attack_card(card) -> bool:
    card_type = _normalize(_card_attr(card, "type", _card_attr(card, "card_type", "")))
    return card_type in {"attack", "cardtypeattack"}


def _is_skill_card(card) -> bool:
    card_type = _normalize(_card_attr(card, "type", _card_attr(card, "card_type", "")))
    return card_type in {"skill", "cardtypeskill"}


def _is_power_card(card) -> bool:
    card_type = _normalize(_card_attr(card, "type", _card_attr(card, "card_type", "")))
    return card_type in {"power", "cardtypepower"}


def _is_status_or_curse_card(card) -> bool:
    card_type = _normalize(_card_attr(card, "type", _card_attr(card, "card_type", "")))
    return card_type in {"status", "cardtypestatus", "curse", "cardtypecurse"}


def _attack_card_play_count(snapshot: Dict[str, Any], card) -> int:
    play_count = _card_play_count(snapshot, card)
    if not _is_attack_card(card):
        return play_count
    if _snapshot_power_amount(snapshot.get("player", {}), "Double Tap") > 0:
        play_count *= 2
    if _necronomicon_attack_replay(snapshot, card):
        play_count *= 2
    return play_count


def _card_play_count(snapshot: Dict[str, Any], card) -> int:
    play_count = 1
    if _has_duplication_power(snapshot):
        play_count += 1
    return play_count


def _has_duplication_power(snapshot: Dict[str, Any]) -> bool:
    player = snapshot.get("player", {})
    return (
        _snapshot_power_amount(player, "DuplicationPower") > 0
        or _snapshot_power_amount(player, "Duplication") > 0
    )


def _consume_duplication_power(expected: Dict[str, Any]) -> None:
    player = expected.get("player", {})
    for power_name in ("DuplicationPower", "Duplication"):
        amount = _snapshot_power_amount(player, power_name)
        if amount <= 0:
            continue
        if amount <= 1:
            _remove_snapshot_power(player, power_name)
        else:
            _set_snapshot_power_amount(player, power_name, amount - 1)
        return


def _necronomicon_attack_replay(snapshot: Dict[str, Any], card) -> bool:
    return (
        not _necronomicon_used_this_turn
        and _snapshot_has_relic(snapshot, "Necronomicon")
        and _is_attack_card(card)
        and _card_cost(card) >= 2
    )


def _is_curse_card(card) -> bool:
    card_type = _normalize(_card_attr(card, "type", _card_attr(card, "card_type", "")))
    return card_type in {"curse", "cardtypecurse"}


def _is_all_enemy_attack(card) -> bool:
    return _known_card_name(card, ALL_ENEMY_ATTACKS) is not None


def _is_whirlwind(card) -> bool:
    return _known_card_name(card, BASE_ATTACK_DAMAGE) == "Whirlwind"


def _is_reaper(card) -> bool:
    return _known_card_name(card, BASE_ATTACK_DAMAGE) == "Reaper"


def _raw_card_cost(card) -> int:
    return _to_int(_card_attr(card, "cost_for_turn", _card_attr(card, "cost", 0)))


def _is_x_cost_card(card) -> bool:
    return _raw_card_cost(card) < 0


def _card_spends_all_energy(card, snapshot: Dict[str, Any]) -> bool:
    if _blue_candle_curse_hp_loss(card, snapshot) > 0:
        return False
    return _is_x_cost_card(card) or _is_whirlwind(card)


def _card_cost(card) -> int:
    return max(0, _raw_card_cost(card))


def _card_damage(card) -> int:
    explicit = _to_int(_card_attr(card, "damage", 0))
    card_name = _known_card_name(card, BASE_ATTACK_DAMAGE)
    base_damage = BASE_ATTACK_DAMAGE.get(card_name) if card_name else None
    upgrade_bonus = known_damage_upgrade_bonus(card, card_name) if card_name else 0
    if card_name == "Rampage" and base_damage is not None:
        misc_damage = _positive_card_misc(card)
        tracked_bonus = _rampage_damage_bonus_for_card(card)
        if explicit > 0:
            if tracked_bonus > 0 and explicit <= base_damage:
                return explicit + tracked_bonus
            return explicit
        if tracked_bonus <= 0 and misc_damage > base_damage:
            return misc_damage
        return base_damage + tracked_bonus
    if explicit > 0:
        if base_damage is not None and upgrade_bonus > 0 and explicit <= base_damage:
            return explicit + upgrade_bonus
        return explicit
    if base_damage is not None:
        return base_damage + upgrade_bonus
    return 0


def _card_damage_for_snapshot(card, player: Dict[str, Any], energy_available: int = 0) -> int:
    damage, hit_count = _card_damage_and_hits_for_snapshot(card, player, energy_available)
    return damage * hit_count


def _card_damage_and_hits_for_snapshot(
    card,
    player: Dict[str, Any],
    energy_available: int = 0,
    before: Optional[Dict[str, Any]] = None,
    card_index: int = -1,
    apply_weak: bool = True,
) -> tuple[int, int]:
    damage = _card_damage(card)
    card_name = _known_card_name(card, BASE_ATTACK_DAMAGE)
    if card_name == "Mind Blast" and before is not None:
        damage = max(0, _to_int(before.get("draw_pile_count"), default=0))
    if card_name == "Body Slam":
        damage = max(0, _to_int(player.get("block")))
    if card_name == "Perfected Strike" and before is not None:
        base_damage = BASE_ATTACK_DAMAGE[card_name] + known_damage_upgrade_bonus(card, card_name)
        explicit = _to_int(_card_attr(card, "damage", 0))
        if explicit <= base_damage:
            damage += (
                _snapshot_strike_card_count(before)
                * perfected_strike_bonus_per_strike(card)
            )
    if card_name == "Whirlwind":
        per_hit = _source_modified_attack_damage(
            damage,
            card,
            player,
            before,
            apply_weak=apply_weak,
        )
        return per_hit, max(0, energy_available)
    if card_name == "Fiend Fire" and before is not None:
        hit_count = _fiend_fire_hit_count(card, before, card_index)
        return (
            _source_modified_attack_damage(
                damage,
                card,
                player,
                before,
                apply_weak=apply_weak,
            ),
            hit_count,
        )
    hit_count = _multi_hit_count(card, card_name)
    if hit_count > 1 and card_name is not None:
        damage = _multi_hit_damage_per_hit(card, card_name, hit_count)
    return (
        _source_modified_attack_damage(
            damage,
            card,
            player,
            before,
            apply_weak=apply_weak,
        ),
        hit_count,
    )


def _card_damage_before_player_weak(
    card,
    player: Dict[str, Any],
    energy_available: int = 0,
    before: Optional[Dict[str, Any]] = None,
    card_index: int = -1,
) -> int:
    damage, _hit_count = _card_damage_and_hits_for_snapshot(
        card,
        player,
        energy_available,
        before,
        card_index,
        apply_weak=False,
    )
    return damage


def _fiend_fire_hit_count(card, before: Dict[str, Any], card_index: int) -> int:
    hit_count = 0
    skipped_played_card = False
    for index, hand_card in enumerate(before.get("hand", [])):
        if index == card_index:
            continue
        if card_index < 0 and not skipped_played_card and _snapshot_card_matches(hand_card, card):
            skipped_played_card = True
            continue
        hit_count += 1
    return max(0, hit_count)


def _multi_hit_count(card, card_name: Optional[str]) -> int:
    if card_name == "Sword Boomerang" and card_upgrade_count(card) > 0:
        return 4
    if card_name == "Pummel" and card_upgrade_count(card) > 0:
        return 5
    return MULTI_HIT_ATTACKS.get(card_name or "", 1)


def _multi_hit_damage_per_hit(card, card_name: str, hit_count: int) -> int:
    if card_name == "Pummel":
        return 2
    if card_name == "Sword Boomerang":
        return 3
    base_damage = BASE_ATTACK_DAMAGE[card_name]
    per_hit = base_damage // hit_count if hit_count > 0 else base_damage
    return per_hit + known_damage_upgrade_bonus(card, card_name)


def _snapshot_strike_card_count(snapshot: Dict[str, Any]) -> int:
    count = 0
    for pile_name in ("hand", "draw_pile", "discard_pile", "exhaust_pile", "limbo"):
        for card in snapshot.get(pile_name, []) or []:
            if _snapshot_card_contains_strike(card):
                count += 1
    return max(0, count)


def _snapshot_card_contains_strike(card: Dict[str, Any]) -> bool:
    return "strike" in _normalize(
        f"{card.get('name', '')} {card.get('id', '')} {card.get('card_id', '')}"
    )


def _card_block(card) -> int:
    explicit = _to_int(_card_attr(card, "block", 0))
    card_name = _known_card_name(card, BASE_SKILL_BLOCK)
    base_block = BASE_SKILL_BLOCK.get(card_name) if card_name else None
    upgrade_bonus = known_block_upgrade_bonus(card, card_name) if card_name else 0
    if explicit > 0:
        if base_block is not None and upgrade_bonus > 0 and explicit <= base_block:
            return explicit + upgrade_bonus
        return explicit
    if base_block is not None:
        return base_block + upgrade_bonus
    return 0


def _apply_attack_block_before_damage(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    card,
    play_count: int = 1,
) -> bool:
    if _known_card_name(card, ATTACK_BLOCK_BEFORE_DAMAGE) is None:
        return False
    return _apply_card_block_gain(expected, before, card, play_count)


def _apply_card_block_gain(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    card,
    play_count: int = 1,
) -> bool:
    block = _card_block(card)
    if block <= 0:
        return False
    trigger_count = max(1, _to_int(play_count, default=1))
    _gain_player_block(
        expected,
        before,
        sum(
            _modified_block(block, expected.get("player", {}))
            for _ in range(trigger_count)
        ),
        trigger_count,
        from_card=True,
    )
    return True


def _apply_block_multiplier_card(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    card,
    play_count: int,
) -> bool:
    card_name = _known_card_name(card, BLOCK_MULTIPLIER_SKILLS)
    if card_name is None:
        return False
    multiplier = max(1, _to_int(BLOCK_MULTIPLIER_SKILLS.get(card_name), default=1))
    if multiplier <= 1:
        return False

    for _ in range(max(1, play_count)):
        current_block = max(0, _to_int(expected.get("player", {}).get("block")))
        block_gain = current_block * (multiplier - 1)
        if block_gain > 0:
            _gain_player_block(expected, before, block_gain, from_card=True)
    return True


def _second_wind_block(
    card,
    before: Dict[str, Any],
    card_index: int,
    player: Optional[Dict[str, Any]] = None,
) -> int:
    card_name = _known_card_name(card, SECOND_WIND_BLOCK_PER_CARD)
    if card_name is None:
        return 0
    per_card = SECOND_WIND_BLOCK_PER_CARD[card_name]
    if card_upgrade_count(card) > 0:
        per_card += 2
    non_attack_count = _exhausts_non_attack_hand_count(card, before, card_index)
    if player is not None:
        return sum(_modified_block(per_card, player) for _ in range(non_attack_count))
    return non_attack_count * per_card


def _exhausts_non_attack_hand_count(
    card,
    before: Dict[str, Any],
    card_index: int,
) -> int:
    if _known_card_name(card, EXHAUSTS_NON_ATTACK_HAND_CARDS) is None:
        return 0
    return _non_attack_hand_count_excluding_played(card, before, card_index)


def _hand_exhaust_sentinel_energy(
    card,
    before: Dict[str, Any],
    card_index: int,
) -> int:
    energy = 0
    for hand_card in _hand_exhausted_cards(card, before, card_index):
        if _snapshot_known_card_name(hand_card, BASE_SKILL_BLOCK) != "Sentinel":
            continue
        energy += 3 if _snapshot_card_upgrade_count(hand_card) > 0 else 2
    return energy


def _selected_sentinel_exhaust_energy(action) -> int:
    energy = 0
    for card in getattr(action, "cards", []) or []:
        if _known_card_name(card, BASE_SKILL_BLOCK) != "Sentinel":
            continue
        energy += 3 if card_upgrade_count(card) > 0 else 2
    return energy


def _hand_exhausted_cards(
    card,
    before: Dict[str, Any],
    card_index: int,
) -> List[Dict[str, Any]]:
    if _known_card_name(card, BASE_ATTACK_DAMAGE) == "Fiend Fire":
        return _hand_cards_excluding_played(card, before, card_index)
    if _known_card_name(card, EXHAUSTS_NON_ATTACK_HAND_CARDS) is not None:
        return _non_attack_hand_cards_excluding_played(card, before, card_index)
    return []


def _non_attack_hand_count_excluding_played(
    card,
    before: Dict[str, Any],
    card_index: int,
) -> int:
    return len(_non_attack_hand_cards_excluding_played(card, before, card_index))


def _non_attack_hand_cards_excluding_played(
    card,
    before: Dict[str, Any],
    card_index: int,
) -> List[Dict[str, Any]]:
    return [
        hand_card
        for hand_card in _hand_cards_excluding_played(card, before, card_index)
        if not _snapshot_card_is_attack(hand_card)
    ]


def _hand_cards_excluding_played(
    card,
    before: Dict[str, Any],
    card_index: int,
) -> List[Dict[str, Any]]:
    hand_cards: List[Dict[str, Any]] = []
    skipped_played_card = False
    for index, hand_card in enumerate(before.get("hand", [])):
        if index == card_index:
            continue
        if card_index < 0 and not skipped_played_card and _snapshot_card_matches(hand_card, card):
            skipped_played_card = True
            continue
        hand_cards.append(hand_card)
    return hand_cards


def _feel_no_pain_block(
    card,
    before: Dict[str, Any],
    card_index: int,
) -> tuple[int, int]:
    amount = max(0, _snapshot_power_amount(before.get("player", {}), "Feel No Pain"))
    if amount <= 0:
        return 0, 0
    exhaust_count = _feel_no_pain_exhaust_count(card, before, card_index)
    return amount * exhaust_count, exhaust_count


def _feel_no_pain_exhaust_count(
    card,
    before: Dict[str, Any],
    card_index: int,
) -> int:
    exhaust_count = _exhausts_non_attack_hand_count(card, before, card_index)
    if _known_card_name(card, BASE_SKILL_BLOCK) == "True Grit":
        exhaust_count += 1

    played_card_exhausts = (
        _known_card_name(card, SELF_EXHAUST_CARDS) is not None
        or _is_status_or_curse_card(card)
    )
    if _is_skill_card(card) and _snapshot_has_power(before.get("player", {}), "Corruption"):
        played_card_exhausts = True
    if played_card_exhausts:
        exhaust_count += 1
    return exhaust_count


def _apply_charons_ashes_exhaust_damage(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    card,
    card_index: int,
) -> int:
    return _apply_charons_ashes_damage_events(
        expected,
        before,
        _feel_no_pain_exhaust_count(card, before, card_index),
    )


def _apply_charons_ashes_damage_events(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    exhaust_events: int,
) -> int:
    if exhaust_events <= 0 or not _snapshot_has_relic(before, "Charon's Ashes"):
        return 0

    applied = 0
    for _ in range(exhaust_events):
        for index, _monster in enumerate(expected.get("monsters", []) or []):
            if _apply_direct_monster_damage(
                expected,
                index,
                CHARONS_ASHES_DAMAGE,
            ):
                applied += 1
    return applied


def _snapshot_card_is_attack(card: Dict[str, Any]) -> bool:
    return _normalize(card.get("type")) in {"attack", "cardtypeattack"}


def _snapshot_card_matches(snapshot_card: Dict[str, Any], card) -> bool:
    snapshot_ids = {
        _normalize(_strip_upgrade_suffix(snapshot_card.get("id"))),
        _normalize(_strip_upgrade_suffix(snapshot_card.get("name"))),
    }
    for attr in ("card_id", "id", "name"):
        if _normalize(_strip_upgrade_suffix(getattr(card, attr, None))) in snapshot_ids:
            return True
    return False


def _snapshot_known_card_name(
    snapshot_card: Dict[str, Any], known_values: Dict[str, int]
) -> Optional[str]:
    known_by_normalized = {_normalize(name): name for name in known_values}
    for key in ("name", "id", "card_id"):
        normalized = _normalize(_strip_upgrade_suffix(snapshot_card.get(key)))
        if normalized in known_by_normalized:
            return known_by_normalized[normalized]
    return None


def _snapshot_card_upgrade_count(snapshot_card: Dict[str, Any]) -> int:
    upgrades = max(0, _to_int(snapshot_card.get("upgrades")))
    if upgrades > 0:
        return upgrades
    return 1 if str(snapshot_card.get("name") or "").endswith("+") else 0


def _source_modified_attack_damage(
    damage: int,
    card,
    player: Dict[str, Any],
    snapshot: Optional[Dict[str, Any]] = None,
    apply_weak: bool = True,
) -> int:
    strength = _snapshot_power_amount(player, "Strength")
    if strength != 0:
        if _known_card_name(card, BASE_ATTACK_DAMAGE) == "Heavy Blade":
            damage += strength * heavy_blade_strength_multiplier(card)
        else:
            damage += strength
    if damage <= 0:
        return 0
    if _pen_nib_damage_multiplier(snapshot, card) > 1:
        damage *= 2
    if apply_weak and _snapshot_player_is_weak(player):
        damage = damage * 3 // 4
    return max(0, damage)


def _modified_attack_damage(
    damage: int,
    target: Dict[str, Any],
    before: Optional[Dict[str, Any]] = None,
    source_damage_before_weak: Optional[int] = None,
) -> int:
    if damage <= 0:
        return 0
    if _snapshot_power_amount(target, "Vulnerable") > 0:
        if (
            source_damage_before_weak is not None
            and _snapshot_player_is_weak((before or {}).get("player", {}))
        ):
            damage = _weak_vulnerable_modified_damage(
                source_damage_before_weak,
                before,
            )
        else:
            damage = _vulnerable_modified_damage(damage, before)
    if _snapshot_power_amount(target, "Flight") > 0:
        damage = damage // 2
    return max(0, damage)


def _vulnerable_modified_damage(
    damage: int,
    before: Optional[Dict[str, Any]] = None,
) -> int:
    if _snapshot_has_relic(before or {}, "Paper Phrog"):
        return damage * 7 // 4
    return damage * 3 // 2


def _weak_vulnerable_modified_damage(
    damage_before_weak: int,
    before: Optional[Dict[str, Any]] = None,
) -> int:
    if _snapshot_has_relic(before or {}, "Paper Phrog"):
        return damage_before_weak * 21 // 16
    return damage_before_weak * 9 // 8


def _snapshot_player_is_weak(player: Dict[str, Any]) -> bool:
    return (
        _snapshot_power_amount(player, "Weakened") > 0
        or _snapshot_power_amount(player, "Weak") > 0
    )


def _snapshot_player_dead(snapshot: Dict[str, Any]) -> bool:
    return _to_int(snapshot.get("player", {}).get("current_hp")) <= 0


def _decrement_flight(target: Dict[str, Any], decrement: int = 1) -> None:
    for power in target.get("powers", []) or []:
        identifiers = {
            _normalize(power.get("id")),
            _normalize(power.get("name")),
        }
        if "flight" not in identifiers:
            continue
        amount = max(
            0,
            _to_int(power.get("amount"), default=1) - max(1, decrement),
        )
        power["amount"] = amount
        if amount <= 0:
            target["intent"] = "Intent.STUN"
            target["move_damage"] = -1
            target["move_id"] = 4
        return


def _trigger_malleable(target: Dict[str, Any], defer_block: bool = False) -> int:
    amount = max(0, _snapshot_power_amount(target, "Malleable"))
    if amount <= 0:
        return 0
    if not defer_block:
        target["block"] = max(0, _to_int(target.get("block"))) + amount
    _set_snapshot_power_amount(target, "Malleable", amount + 1)
    return amount


def _apply_guardian_mode_shift(target: Dict[str, Any], hp_loss: int) -> None:
    if hp_loss <= 0 or not _is_guardian_monster(target):
        return
    amount = _snapshot_power_amount(target, "Mode Shift")
    if amount <= 0:
        return
    remaining = amount - hp_loss
    if remaining > 0:
        _set_snapshot_power_amount(target, "Mode Shift", remaining)
        return
    target["block"] = max(0, _to_int(target.get("block"))) + 20
    target["intent"] = "Intent.BUFF"
    target["move_damage"] = -1
    _remove_snapshot_power(target, "Mode Shift")


def _apply_lagavulin_wake_stun(target: Dict[str, Any]) -> None:
    if not _is_lagavulin_monster(target):
        return
    if _normalize(target.get("intent")) not in {"sleep", "intentsleep"}:
        return
    target["intent"] = "Intent.STUN"
    target["move_damage"] = -1
    target["move_id"] = 4


def _apply_card_target_debuffs(
    expected: Dict[str, Any],
    card,
    target_index: Optional[int],
) -> None:
    card_name = _known_card_name(card, CARD_TARGET_DEBUFFS)
    if card_name is None or target_index is None or target_index < 0:
        return
    monsters = expected.get("monsters", [])
    if target_index >= len(monsters):
        return
    target = monsters[target_index]
    if target.get("gone") or target.get("half_dead") or _to_int(target.get("hp")) <= 0:
        return
    power_name, base_amount, upgraded_amount = CARD_TARGET_DEBUFFS[card_name]
    amount = upgraded_amount if card_upgrade_count(card) > 0 else base_amount
    _add_snapshot_power_amount(target, power_name, amount)


def _apply_all_enemy_card_target_debuffs(expected: Dict[str, Any], card) -> None:
    if not _is_all_enemy_attack(card):
        return
    for index, _monster in enumerate(expected.get("monsters", []) or []):
        _apply_card_target_debuffs(expected, card, index)


def _modified_block(block: int, player: Dict[str, Any]) -> int:
    if block <= 0:
        return 0
    block += _snapshot_power_amount(player, "Dexterity")
    if _snapshot_power_amount(player, "Frail") > 0:
        block = block * 3 // 4
    return max(0, block)


def _gain_player_block(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    amount: int,
    trigger_count: int = 1,
    from_card: bool = False,
) -> None:
    if amount <= 0:
        return
    if from_card and _player_card_block_blocked(expected):
        return
    expected["player"]["block"] += amount
    _apply_juggernaut_block_triggers(expected, before, trigger_count)


def _player_card_block_blocked(snapshot: Dict[str, Any]) -> bool:
    player = snapshot.get("player", {}) or {}
    return any(
        _snapshot_power_amount(player, power_name) > 0
        for power_name in ("No Block", "NoBlock", "NoBlockPower")
    )


def _apply_panic_button_no_block_power(expected: Dict[str, Any], card) -> None:
    if _known_card_name(card, BASE_SKILL_BLOCK) != "Panic Button":
        return
    _ensure_snapshot_power(expected.setdefault("player", {}), "No Block", 2)


def _apply_juggernaut_block_triggers(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    trigger_count: int,
) -> None:
    damage = max(0, _snapshot_power_amount(before.get("player", {}), "Juggernaut"))
    if damage <= 0 or trigger_count <= 0:
        return
    target_index = _single_alive_monster_index(expected)
    if target_index is None:
        return
    for _ in range(trigger_count):
        _apply_direct_monster_damage(expected, target_index, damage)


def _rage_attack_block(player: Dict[str, Any]) -> int:
    return max(0, _snapshot_power_amount(player, "Rage"))


def _ornamental_fan_attack_block(snapshot: Dict[str, Any]) -> int:
    counter = _snapshot_relic_counter(snapshot, "Ornamental Fan")
    if counter is None:
        if not _snapshot_has_relic(snapshot, "Ornamental Fan"):
            return 0
        attack_count_before_play = _attacks_played_this_turn
    else:
        attack_count_before_play = max(_attacks_played_this_turn, counter, 0)
    attack_count_after_play = attack_count_before_play + 1
    if attack_count_after_play > 0 and attack_count_after_play % 3 == 0:
        return 4
    return 0


def _nunchaku_energy_gain(snapshot: Dict[str, Any], card) -> int:
    if not _is_attack_card(card):
        return 0
    target = _normalize("Nunchaku")
    for relic in snapshot.get("relics", []) or []:
        identifiers = {
            _normalize(relic.get("id")),
            _normalize(relic.get("name")),
        }
        if target in identifiers and _to_int(relic.get("counter")) == 9:
            return 1
    return 0


def _pen_nib_damage_multiplier(snapshot: Optional[Dict[str, Any]], card) -> int:
    if snapshot is None or not _is_attack_card(card):
        return 1
    target = _normalize("Pen Nib")
    for relic in snapshot.get("relics", []) or []:
        identifiers = {
            _normalize(relic.get("id")),
            _normalize(relic.get("name")),
        }
        if target in identifiers and _to_int(relic.get("counter")) == 9:
            return 2
    return 1


def _the_boot_minimum_attack_damage(
    snapshot: Optional[Dict[str, Any]],
    damage: int,
) -> int:
    if (
        snapshot is not None
        and 0 < damage < THE_BOOT_MINIMUM_DAMAGE
        and (
            _snapshot_has_relic(snapshot, "The Boot")
            or _snapshot_has_relic(snapshot, "Boot")
        )
    ):
        return THE_BOOT_MINIMUM_DAMAGE
    return max(0, damage)


def _snapshot_has_relic(snapshot: Dict[str, Any], relic_name: str) -> bool:
    target = _normalize(relic_name)
    for relic in snapshot.get("relics", []) or []:
        identifiers = {
            _normalize(relic.get("id")),
            _normalize(relic.get("name")),
        }
        if target in identifiers:
            return True
    return False


def _snapshot_relic_counter(
    snapshot: Dict[str, Any],
    relic_name: str,
) -> Optional[int]:
    target = _normalize(relic_name)
    for relic in snapshot.get("relics", []) or []:
        identifiers = {
            _normalize(relic.get("id")),
            _normalize(relic.get("name")),
        }
        if target in identifiers:
            return _to_int(relic.get("counter"))
    return None


def _set_snapshot_relic_counter(
    snapshot: Dict[str, Any],
    relic_name: str,
    counter: int,
) -> None:
    target = _normalize(relic_name)
    for relic in snapshot.get("relics", []) or []:
        identifiers = {
            _normalize(relic.get("id")),
            _normalize(relic.get("name")),
        }
        if target in identifiers:
            relic["counter"] = counter
            return


def _fairy_potion_index(snapshot: Dict[str, Any]) -> Optional[int]:
    for index, potion in enumerate(snapshot.get("potions", []) or []):
        effect_type = _normalize(_potion_attr(potion, "effect_type", ""))
        identifiers = {
            _normalize(_potion_attr(potion, "id", "")),
            _normalize(_potion_attr(potion, "potion_id", "")),
            _normalize(_potion_attr(potion, "name", "")),
        }
        if effect_type == "fairy" or not identifiers.isdisjoint(FAIRY_POTION_IDENTIFIERS):
            return index
    return None


def _fairy_revive_hp(snapshot: Dict[str, Any], potion: Dict[str, Any]) -> int:
    percent = _to_float(_potion_attr(potion, "effect_value", 0))
    if percent <= 0 or percent > 1:
        percent = FAIRY_REVIVE_FRACTION
    max_hp = max(1, _to_int(snapshot.get("player", {}).get("max_hp"), default=1))
    return max(1, int(max_hp * percent))


def _consume_fairy_revive_if_dead(expected: Dict[str, Any]) -> bool:
    player = expected.get("player", {})
    if _to_int(player.get("current_hp")) > 0:
        return False
    potion_index = _fairy_potion_index(expected)
    if potion_index is None:
        return False
    potions = expected.get("potions", []) or []
    potion = potions[potion_index]
    player["current_hp"] = _fairy_revive_hp(expected, potion)
    potions.pop(potion_index)
    return True


def _consume_lizard_tail_revive_if_dead(expected: Dict[str, Any]) -> bool:
    player = expected.get("player", {})
    if _to_int(player.get("current_hp")) > 0:
        return False
    counter = _snapshot_relic_counter(expected, "Lizard Tail")
    if counter is None or counter == LIZARD_TAIL_USED_COUNTER:
        return False
    max_hp = max(1, _to_int(player.get("max_hp"), default=1))
    player["current_hp"] = max(1, int(max_hp * LIZARD_TAIL_REVIVE_FRACTION))
    _set_snapshot_relic_counter(expected, "Lizard Tail", LIZARD_TAIL_USED_COUNTER)
    return True


def _consume_player_revive_if_dead(expected: Dict[str, Any]) -> bool:
    if _consume_fairy_revive_if_dead(expected):
        return True
    return _consume_lizard_tail_revive_if_dead(expected)


def _heal_player(expected: Dict[str, Any], amount: int) -> None:
    if amount <= 0:
        return
    player = expected.get("player", {})
    player["current_hp"] = min(
        _to_int(player.get("max_hp")),
        _to_int(player.get("current_hp")) + amount,
    )


def _apply_toy_ornithopter_potion_heal(expected: Dict[str, Any]) -> None:
    if _snapshot_has_relic(expected, "Toy Ornithopter"):
        _heal_player(expected, TOY_ORNITHOPTER_HEAL)


def _apply_feed_max_hp_gain(
    expected: Dict[str, Any],
    card,
    target_index: Optional[int],
    before: Optional[Dict[str, Any]] = None,
) -> None:
    if _known_card_name(card, {"Feed": 0}) != "Feed":
        return
    if target_index is None or target_index < 0:
        return
    monsters = expected.get("monsters", []) or []
    if target_index >= len(monsters):
        return
    target = monsters[target_index]
    if not target.get("gone") or target.get("half_dead"):
        return
    if _snapshot_monster_is_minion(target):
        return
    if before is not None:
        before_monsters = before.get("monsters", []) or []
        if target_index < len(before_monsters) and not _snapshot_monster_active(
            before_monsters[target_index]
        ):
            return
    max_hp_gain = (
        FEED_UPGRADED_MAX_HP_GAIN
        if card_upgrade_count(card) > 0
        else FEED_MAX_HP_GAIN
    )
    _gain_player_max_hp(expected, max_hp_gain)


def _gain_player_max_hp(expected: Dict[str, Any], amount: int) -> None:
    if amount <= 0:
        return
    player = expected.get("player", {})
    max_hp = _to_int(player.get("max_hp")) + amount
    player["max_hp"] = max_hp
    player["current_hp"] = min(
        max_hp,
        _to_int(player.get("current_hp")) + amount,
    )


def _snapshot_monster_is_minion(monster: Dict[str, Any]) -> bool:
    if bool(monster.get("minion")) or bool(monster.get("is_minion")):
        return True
    return _snapshot_has_power(monster, "Minion") or _snapshot_has_power(
        monster,
        "MinionPower",
    )


def _heal_monster(expected: Dict[str, Any], monster_index: int, amount: int) -> None:
    if amount <= 0:
        return
    monsters = expected.get("monsters", []) or []
    if monster_index < 0 or monster_index >= len(monsters):
        return
    monster = monsters[monster_index]
    monster["hp"] = min(
        _to_int(monster.get("max_hp")),
        _to_int(monster.get("hp")) + amount,
    )


def _apply_monster_regenerate_end_turn(expected: Dict[str, Any]) -> None:
    if _to_int(expected.get("player", {}).get("current_hp")) <= 0:
        return
    for index, monster in enumerate(expected.get("monsters", []) or []):
        if (
            monster.get("gone")
            or monster.get("half_dead")
            or _to_int(monster.get("hp")) <= 0
        ):
            continue
        regenerate = max(0, _snapshot_power_amount(monster, "Regenerate"))
        if regenerate > 0:
            _heal_monster(expected, index, regenerate)


def _damage_player(
    expected: Dict[str, Any],
    amount: int,
    *,
    attack_damage: bool = False,
) -> int:
    if amount <= 0:
        return 0
    player = expected.get("player", {})
    hp_before = _to_int(player.get("current_hp"))
    block = max(0, _to_int(player.get("block")))
    blocked = min(block, amount)
    player["block"] = block - blocked
    remaining = amount - blocked
    hp_lost = False
    if remaining > 0:
        if attack_damage:
            remaining = _effective_player_attack_damage_loss(expected, remaining)
        else:
            remaining = _effective_player_hp_loss(expected, remaining)
        hp_after_loss = max(0, hp_before - remaining)
        hp_lost = hp_after_loss < hp_before
        player["current_hp"] = hp_after_loss
        _consume_player_revive_if_dead(expected)
    return 1 if hp_lost else 0


def _player_vulnerable_modified_damage(damage: int) -> int:
    return max(0, _to_int(damage)) * 3 // 2


def _apply_end_turn_player_damage(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> int:
    hp_loss_events = 0
    for amount in _end_turn_status_hp_loss_events(before):
        hp_loss_events += _lose_player_hp(expected, amount)
        if _to_int(expected.get("player", {}).get("current_hp")) <= 0:
            return hp_loss_events
    for amount in _end_turn_status_damage_events(before):
        hp_loss_events += _damage_player(expected, amount)
        if _to_int(expected.get("player", {}).get("current_hp")) <= 0:
            return hp_loss_events
    _apply_end_turn_exhaust_effects(expected, before)
    _clear_non_retained_monster_blocks_for_turn_start(expected)
    reflection_damage = _end_turn_attack_reflection_damage(before)
    for index, monster in enumerate(expected.get("monsters", []) or []):
        if _to_int(expected.get("player", {}).get("current_hp")) <= 0:
            break
        explosion_damage = (
            exploder_explosion_damage(monster)
            if _snapshot_monster_active(monster)
            else 0
        )
        if explosion_damage > 0:
            hp_loss_events += _damage_player(expected, explosion_damage)
            monster["hp"] = 0
            monster["block"] = 0
            monster["gone"] = True
            monster["half_dead"] = False
            continue
        if not _snapshot_monster_active(monster):
            continue
        if "attack" not in _normalize(monster.get("intent")):
            continue
        damage = max(0, _to_int(monster.get("move_damage")))
        if damage <= 0 and reflection_damage <= 0:
            continue
        if damage > 0 and expected.get("_player_vulnerable_added_during_end_turn"):
            damage = _player_vulnerable_modified_damage(damage)
        for _ in range(_monster_attack_hits(monster)):
            hp_before = _to_int(expected.get("player", {}).get("current_hp"))
            if damage > 0:
                hp_loss_events += _damage_player(expected, damage, attack_damage=True)
            hp_after = _to_int(expected.get("player", {}).get("current_hp"))
            hp_lost = max(0, hp_before - hp_after)
            if _is_shelled_parasite_attack_buff(monster):
                _heal_monster(expected, index, hp_lost)
            if hp_after <= 0:
                break
            if reflection_damage > 0:
                _apply_direct_monster_damage(
                    expected,
                    index,
                    reflection_damage,
                    spore_cloud_decay=1,
                    mark_end_turn_vulnerable=True,
                )
                if monster.get("gone") or monster.get("half_dead"):
                    break
    return hp_loss_events


def _apply_end_turn_exhaust_effects(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> int:
    exhaust_events = _end_turn_exhaust_count(before)
    if exhaust_events <= 0:
        return 0

    feel_no_pain = max(
        0,
        _snapshot_power_amount(before.get("player", {}), "Feel No Pain"),
    )
    if feel_no_pain > 0:
        _gain_player_block(
            expected,
            before,
            feel_no_pain * exhaust_events,
            exhaust_events,
        )
    _apply_charons_ashes_damage_events(expected, before, exhaust_events)
    return exhaust_events


def _apply_combust_end_turn(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> int:
    damage = max(0, _snapshot_power_amount(before.get("player", {}), "Combust"))
    if damage <= 0:
        return 0
    hp_loss_event = _lose_player_hp(expected, 1)
    if _snapshot_player_dead(expected):
        return hp_loss_event
    for index, _monster in enumerate(expected.get("monsters", []) or []):
        _apply_direct_monster_damage(
            expected,
            index,
            damage,
            spore_cloud_decay=1,
            mark_end_turn_vulnerable=True,
        )
    return hp_loss_event


def _lose_player_hp(
    expected: Dict[str, Any],
    amount: int,
    *,
    clear_block_on_death: bool = True,
) -> int:
    if amount <= 0:
        return 0
    player = expected.get("player", {})
    hp_before = _to_int(player.get("current_hp"))
    amount = _effective_player_hp_loss(expected, amount)
    hp_after_loss = max(0, hp_before - amount)
    hp_lost = hp_after_loss < hp_before
    player["current_hp"] = hp_after_loss
    _consume_player_revive_if_dead(expected)
    if clear_block_on_death and _snapshot_player_dead(expected):
        player["block"] = 0
    return 1 if hp_lost else 0


def _effective_player_hp_loss(snapshot: Dict[str, Any], amount: int) -> int:
    hp_loss = max(0, _to_int(amount))
    if hp_loss > 1 and _snapshot_player_has_intangible(snapshot):
        hp_loss = 1
    if hp_loss > 0 and _snapshot_has_relic(snapshot, "Tungsten Rod"):
        hp_loss = max(0, hp_loss - 1)
    if hp_loss > 0 and _consume_player_buffer(snapshot):
        return 0
    return hp_loss


def _effective_player_attack_damage_loss(
    snapshot: Dict[str, Any],
    amount: int,
) -> int:
    hp_loss = max(0, _to_int(amount))
    if hp_loss > 1 and _snapshot_player_has_intangible(snapshot):
        hp_loss = 1
    if 1 < hp_loss <= 5 and _snapshot_has_relic(snapshot, "Torii"):
        hp_loss = 1
    if hp_loss > 0 and _snapshot_has_relic(snapshot, "Tungsten Rod"):
        hp_loss = max(0, hp_loss - 1)
    if hp_loss > 0 and _consume_player_buffer(snapshot):
        return 0
    return hp_loss


def _snapshot_player_has_intangible(snapshot: Dict[str, Any]) -> bool:
    player = snapshot.get("player", {})
    return (
        _snapshot_power_amount(player, "IntangiblePlayer") > 0
        or _snapshot_power_amount(player, "Intangible") > 0
    )


def _consume_player_buffer(snapshot: Dict[str, Any]) -> bool:
    player = snapshot.get("player", {})
    for power_name in ("Buffer", "BufferPower"):
        amount = _snapshot_power_amount(player, power_name)
        if amount <= 0:
            continue
        if amount > 1:
            _set_snapshot_power_amount(player, power_name, amount - 1)
        else:
            _remove_snapshot_power(player, power_name)
        return True
    return False


def _apply_player_debuff(
    expected: Dict[str, Any],
    power_name: str,
    amount: int,
) -> bool:
    if amount <= 0:
        return False
    if _consume_player_artifact(expected):
        return False
    _add_snapshot_power_amount(expected.setdefault("player", {}), power_name, amount)
    return True


def _consume_player_artifact(snapshot: Dict[str, Any]) -> bool:
    player = snapshot.get("player", {})
    for power_name in ("Artifact", "ArtifactPower"):
        amount = _snapshot_power_amount(player, power_name)
        if amount <= 0:
            continue
        if amount > 1:
            _set_snapshot_power_amount(player, power_name, amount - 1)
        else:
            _remove_snapshot_power(player, power_name)
        return True
    return False


def _end_turn_status_damage_events(snapshot: Dict[str, Any]):
    for card in snapshot.get("hand", []) or []:
        card_name = _snapshot_known_card_name(card, END_TURN_STATUS_DAMAGE)
        if card_name is None:
            continue
        damage = END_TURN_STATUS_DAMAGE[card_name]
        if card_name == "Burn" and _snapshot_card_upgrade_count(card) > 0:
            damage += 2
        if damage > 0:
            yield damage


def _end_turn_status_hp_loss_events(snapshot: Dict[str, Any]):
    hand = snapshot.get("hand", []) or []
    hand_size = len(hand)
    for card in hand:
        card_name = _snapshot_known_card_name(card, END_TURN_STATUS_HP_LOSS)
        if card_name is not None:
            amount = END_TURN_STATUS_HP_LOSS[card_name]
            if amount > 0:
                yield amount
        if _snapshot_known_card_name(card, {"Regret": 0}) == "Regret" and hand_size > 0:
            yield hand_size


def _end_turn_exhaust_count(snapshot: Dict[str, Any]) -> int:
    return sum(1 for _card in _end_turn_exhaust_cards(snapshot))


def _end_turn_exhaust_cards(snapshot: Dict[str, Any]):
    for card in snapshot.get("hand", []) or []:
        if _snapshot_known_card_name(card, END_TURN_EXHAUST_CARDS) is not None:
            yield card


def _end_turn_monster_attack_damage_events(snapshot: Dict[str, Any]):
    for monster in snapshot.get("monsters", []) or []:
        if monster.get("gone") or monster.get("half_dead"):
            continue
        if "attack" not in _normalize(monster.get("intent")):
            continue
        damage = max(0, _to_int(monster.get("move_damage")))
        if damage <= 0:
            continue
        for _ in range(_monster_attack_hits(monster)):
            yield damage


def _is_shelled_parasite_attack_buff(monster: Dict[str, Any]) -> bool:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    if "shelledparasite" not in identifiers:
        return False
    return "attackbuff" in _normalize(monster.get("intent"))


def _brutality_start_turn_hp_loss(snapshot: Dict[str, Any]) -> int:
    return max(0, _snapshot_power_amount(snapshot.get("player", {}), "Brutality"))


def _regeneration_end_turn_heal(snapshot: Dict[str, Any]) -> int:
    player = snapshot.get("player", {})
    base_heal = max(
        0,
        _snapshot_power_amount(player, "Regeneration"),
        _snapshot_power_amount(player, "Regen"),
    )
    return _magic_flower_scaled_heal(snapshot, base_heal)


def _magic_flower_scaled_heal(snapshot: Dict[str, Any], amount: int) -> int:
    heal = max(0, _to_int(amount))
    if heal <= 0 or not _snapshot_has_relic(snapshot, "Magic Flower"):
        return heal
    return (heal * MAGIC_FLOWER_HEAL_NUMERATOR + MAGIC_FLOWER_HEAL_DENOMINATOR - 1) // (
        MAGIC_FLOWER_HEAL_DENOMINATOR
    )


def _metallicize_end_turn_block(snapshot: Dict[str, Any]) -> int:
    return max(0, _snapshot_power_amount(snapshot.get("player", {}), "Metallicize"))


def _plated_armor_end_turn_block(snapshot: Dict[str, Any]) -> int:
    return max(0, _snapshot_power_amount(snapshot.get("player", {}), "Plated Armor"))


def _next_turn_block_start_turn_block(snapshot: Dict[str, Any]) -> int:
    return max(0, _snapshot_power_amount(snapshot.get("player", {}), "Next Turn Block"))


def _orichalcum_end_turn_block(snapshot: Dict[str, Any], player: Dict[str, Any]) -> int:
    if not _snapshot_has_relic(snapshot, "Orichalcum"):
        return 0
    return 6 if _to_int(player.get("block")) <= 0 else 0


def _horn_cleat_start_turn_block(snapshot: Dict[str, Any]) -> int:
    target = _normalize("HornCleat")
    for relic in snapshot.get("relics", []) or []:
        identifiers = {
            _normalize(relic.get("id")),
            _normalize(relic.get("name")),
        }
        if target in identifiers and _to_int(relic.get("counter")) == 1:
            return 14
    return 0


def _captains_wheel_start_turn_block(snapshot: Dict[str, Any]) -> int:
    target = _normalize("CaptainsWheel")
    for relic in snapshot.get("relics", []) or []:
        identifiers = {
            _normalize(relic.get("id")),
            _normalize(relic.get("name")),
        }
        if target in identifiers and _to_int(relic.get("counter")) == 2:
            return 18
    return 0


def _self_forming_clay_end_turn_block(snapshot: Dict[str, Any], hp_loss_events: int) -> int:
    if hp_loss_events <= 0 or not _snapshot_has_relic(snapshot, "Self Forming Clay"):
        return 0
    return hp_loss_events * 3


def _retained_end_turn_block(snapshot: Dict[str, Any], player: Dict[str, Any]) -> int:
    if not _snapshot_has_power(snapshot.get("player", {}), "Barricade"):
        if _snapshot_has_relic(snapshot, "Calipers"):
            return max(0, _to_int(player.get("block")) - 15)
        return 0
    return max(0, _to_int(player.get("block")))


def _apply_end_turn_escape_intents(expected: Dict[str, Any]) -> None:
    for monster in expected.get("monsters", []) or []:
        if not _snapshot_monster_active(monster):
            continue
        if _normalize(monster.get("intent")) not in {"escape", "intentescape"}:
            continue
        monster["gone"] = True
        monster["half_dead"] = False


def _apply_end_turn_attack_reflection_damage(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> None:
    reflection_damage = _end_turn_attack_reflection_damage(before)
    if reflection_damage <= 0:
        return
    for index, monster in enumerate(expected.get("monsters", []) or []):
        if _monster_attack_damage(monster) <= 0:
            continue
        _apply_direct_monster_damage(
            expected,
            index,
            reflection_damage * _monster_attack_hits(monster),
            spore_cloud_decay=1,
            mark_end_turn_vulnerable=True,
        )


def _end_turn_attack_reflection_damage(snapshot: Dict[str, Any]) -> int:
    player = snapshot.get("player", {})
    return max(0, _snapshot_power_amount(player, "Thorns")) + max(
        0,
        _snapshot_power_amount(player, "Flame Barrier"),
    )


def _clear_non_retained_monster_blocks_for_turn_start(expected: Dict[str, Any]) -> None:
    for monster in expected.get("monsters", []) or []:
        if monster.get("gone") or monster.get("half_dead"):
            monster["block"] = 0
            continue
        if _snapshot_has_power(monster, "Barricade"):
            continue
        monster["block"] = 0


def _apply_mercury_hourglass_damage(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> None:
    if not _snapshot_has_relic(before, "Mercury Hourglass"):
        return
    if _to_int(expected.get("player", {}).get("current_hp")) <= 0:
        return
    for index, _monster in enumerate(expected.get("monsters", []) or []):
        _apply_direct_monster_damage(expected, index, 3)


def _monster_move_block_before_mercury_hourglass(monster: Dict[str, Any]) -> int:
    identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
    intent = _normalized_intent(monster.get("intent"))
    move_id = _to_int(monster.get("move_id"))
    if (
        "hexaghost" in identifiers
        and move_id == 3
        and "defend" in intent
        and "buff" in intent
    ):
        return 12
    if (
        ("theguardian" in identifiers or "guardian" in identifiers)
        and move_id == 6
        and "defend" in intent
    ):
        return 9
    return 0


def _apply_stone_calendar_damage(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> None:
    counter = _snapshot_relic_counter(before, "Stone Calendar")
    if counter is None:
        return

    counter = max(0, counter)
    if counter == STONE_CALENDAR_TRIGGER_COUNTER:
        for index, _monster in enumerate(expected.get("monsters", []) or []):
            _apply_direct_monster_damage(
                expected,
                index,
                STONE_CALENDAR_DAMAGE,
                ignore_block=True,
            )
        _mark_stone_calendar_slime_splits(expected)
    _set_snapshot_relic_counter(expected, "Stone Calendar", counter + 1)


def _mark_stone_calendar_slime_splits(expected: Dict[str, Any]) -> None:
    for monster in expected.get("monsters", []) or []:
        if not _slime_split_ready(monster):
            continue
        monster["hp"] = 0
        monster["block"] = 0
        monster["gone"] = True
        monster["half_dead"] = False
        monster["intent"] = "Intent.UNKNOWN"
        monster["move_damage"] = -1


def _prepare_monster_block_for_mercury_hourglass(
    expected: Dict[str, Any],
    before: Dict[str, Any],
) -> None:
    before_monsters = before.get("monsters", []) or []
    for index, monster in enumerate(expected.get("monsters", []) or []):
        if monster.get("gone") or monster.get("half_dead") or _to_int(monster.get("hp")) <= 0:
            monster["block"] = 0
            continue

        before_monster = before_monsters[index] if index < len(before_monsters) else {}
        block = max(0, _to_int(monster.get("block")))
        block += _monster_move_block_before_mercury_hourglass(before_monster)
        block += max(0, _snapshot_power_amount(before_monster, "Plated Armor"))
        block += max(0, _snapshot_power_amount(before_monster, "Metallicize"))
        monster["block"] = block


def _has_mystic_support_turn(snapshot: Dict[str, Any]) -> bool:
    for monster in snapshot.get("monsters", []) or []:
        if monster.get("gone") or monster.get("half_dead") or _to_int(monster.get("hp")) <= 0:
            continue
        identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
        if identifiers.isdisjoint({"healer", "mystic"}):
            continue
        if _normalize(monster.get("intent")) in {"buff", "intentbuff"}:
            return True
    return False


def _apply_havoc_top_card(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    havoc_card,
    depth: int = 0,
) -> None:
    if _known_card_name(havoc_card, HAVOC_CARDS) != "Havoc":
        return
    _apply_expected_top_draw_card_played_by_effect(
        expected,
        before,
        depth=depth,
        exhaust_by_effect=True,
        source_card=havoc_card,
    )


def _apply_expected_play_top_cards_potion(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    count: int,
) -> None:
    for _ in range(max(0, count)):
        if not _apply_expected_top_draw_card_played_by_effect(
            expected,
            before,
            exhaust_by_effect=False,
        ):
            return


def _apply_expected_top_draw_card_played_by_effect(
    expected: Dict[str, Any],
    before: Dict[str, Any],
    depth: int = 0,
    exhaust_by_effect: bool = False,
    source_card=None,
) -> bool:
    if depth > 20:
        return False

    top_card = _draw_pile_top_card(expected)
    if top_card is None:
        return False

    _pop_expected_draw_pile_top(expected)
    target_index = None
    pre_damage_block_applied = False
    top_attack_blocked = _is_attack_card(top_card) and (
        _snapshot_player_entangled(expected)
        or not _effect_played_card_conditions_allow(
            top_card,
            expected,
            source_card,
        )
    )
    if _is_attack_card(top_card) and not top_attack_blocked:
        attack_play_count = _attack_card_play_count(expected, top_card)
        top_card_effect_energy = _to_int(
            (expected.get("player") or {}).get("energy"),
            default=0,
        )
        pre_damage_block_applied = _apply_attack_block_before_damage(
            expected,
            before,
            top_card,
        )
        sharp_hide_damage = 0
        damage, hit_count = _card_damage_and_hits_for_snapshot(
            top_card,
            expected.get("player", {}),
            top_card_effect_energy,
            before,
            -1,
        )
        source_damage_before_weak = _card_damage_before_player_weak(
            top_card,
            expected.get("player", {}),
            top_card_effect_energy,
            before,
            -1,
        )
        if _is_all_enemy_attack(top_card):
            damage_dealt = 0
            for _ in range(max(1, attack_play_count)):
                damage_dealt += _apply_expected_attack_to_all(
                    expected,
                    damage,
                    hit_count,
                    before,
                    source_damage_before_weak=source_damage_before_weak,
                )
                _apply_all_enemy_card_target_debuffs(expected, top_card)
            sharp_hide_damage = _sharp_hide_reflection_damage(
                before,
                all_targets=True,
            ) * max(1, attack_play_count)
        else:
            target_index = _single_alive_monster_index(expected)
            if target_index is None:
                damage_dealt = 0
            else:
                damage_dealt = 0
                for _ in range(max(1, attack_play_count)):
                    damage_dealt += _apply_expected_attack(
                        expected,
                        target_index,
                        damage,
                        hit_count,
                        before,
                        source_damage_before_weak=source_damage_before_weak,
                    )
                    _apply_card_target_debuffs(expected, top_card, target_index)
                sharp_hide_damage = (
                    _sharp_hide_reflection_damage(before, target_index)
                    * max(1, attack_play_count)
                )
        if _is_reaper(top_card) and damage_dealt > 0:
            _heal_player(
                expected,
                _magic_flower_scaled_heal(expected, damage_dealt),
            )
        rage_block = _rage_attack_block(expected.get("player", {}))
        if rage_block > 0:
            _gain_player_block(expected, before, rage_block)
        ornamental_fan_block = _ornamental_fan_attack_block(before)
        if ornamental_fan_block > 0:
            _gain_player_block(expected, before, ornamental_fan_block)
        if sharp_hide_damage > 0:
            _damage_player(expected, sharp_hide_damage)
    elif _known_card_name(top_card, HAVOC_CARDS) == "Havoc":
        _apply_expected_top_draw_card_played_by_effect(
            expected,
            before,
            depth=depth + 1,
            exhaust_by_effect=True,
            source_card=source_card,
        )

    if not top_attack_blocked:
        self_damage = _card_self_damage(top_card)
        self_damage += _blue_candle_curse_hp_loss(top_card, before)
        if self_damage > 0:
            _lose_player_hp(expected, self_damage)
        heal = _card_heal(top_card)
        if heal > 0:
            _heal_player(expected, heal)
        _apply_bird_faced_urn_power_play(expected, top_card)
        _apply_letter_opener_skill_play(expected, top_card)
        energy_gain = _card_energy_gain(top_card)
        energy_gain += _conditional_card_energy_gain(top_card, before, target_index)
        if energy_gain > 0:
            expected["player"]["energy"] += energy_gain
        block = _card_block(top_card)
        if block > 0 and not pre_damage_block_applied:
            _gain_player_block(
                expected,
                before,
                _modified_block(block, expected.get("player", {})),
                from_card=True,
            )
        _apply_panic_button_no_block_power(expected, top_card)
        second_wind_block = _effect_play_second_wind_block(
            top_card,
            before,
            source_card,
            expected.get("player", {}),
        )
        if second_wind_block > 0:
            _gain_player_block(
                expected,
                before,
                second_wind_block,
                _effect_play_exhausts_non_attack_hand_count(
                    top_card,
                    before,
                    source_card,
                ),
                from_card=True,
            )
    if exhaust_by_effect:
        feel_no_pain_block = _havoc_top_card_feel_no_pain_block(before)
        if feel_no_pain_block > 0:
            _gain_player_block(expected, before, feel_no_pain_block)
        _apply_charons_ashes_damage_events(expected, before, 1)
    return True


def _apply_card_draw(expected: Dict[str, Any], card) -> None:
    draw_count = _card_draw_count(card)
    if draw_count <= 0:
        return
    if _snapshot_has_power(expected.get("player", {}), "No Draw"):
        return

    for _ in range(draw_count):
        top_card = _draw_pile_top_card(expected)
        if top_card is None and _to_int(expected.get("draw_pile_count")) <= 0:
            if not _shuffle_discard_into_draw_pile(expected):
                break
            top_card = _draw_pile_top_card(expected)

        if top_card is not None:
            expected.setdefault("hand", []).append(copy.deepcopy(top_card))
        _pop_expected_draw_pile_top(expected)

    if _known_card_name(card, CARD_DRAW) == "Battle Trance":
        _ensure_snapshot_power(expected.setdefault("player", {}), "No Draw", -1)


def _shuffle_discard_into_draw_pile(expected: Dict[str, Any]) -> bool:
    discard_pile = expected.get("discard_pile")
    discard_count = _to_int(expected.get("discard_pile_count"))
    if isinstance(discard_pile, list) and discard_pile:
        expected["draw_pile"] = copy.deepcopy(discard_pile)
        expected["draw_pile_count"] = len(expected["draw_pile"])
        expected["discard_pile"] = []
        expected["discard_pile_count"] = 0
        _apply_sundial_shuffle(expected)
        return True
    if discard_count > 0:
        expected["draw_pile_count"] = discard_count
        expected["discard_pile_count"] = 0
        _apply_sundial_shuffle(expected)
        return True
    return False


def _apply_sundial_shuffle(expected: Dict[str, Any]) -> None:
    counter = _snapshot_relic_counter(expected, "Sundial")
    if counter is None:
        return
    counter = max(0, counter) + 1
    if counter >= SUNDIAL_TRIGGER_COUNTER:
        expected.setdefault("player", {})["energy"] = (
            _to_int(expected.get("player", {}).get("energy")) + SUNDIAL_ENERGY
        )
        counter = 0
    _set_snapshot_relic_counter(expected, "Sundial", counter)


def _draw_pile_top_card(snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    draw_pile = snapshot.get("draw_pile") or []
    if not isinstance(draw_pile, list) or not draw_pile:
        return None
    top_card = draw_pile[-1]
    return top_card if isinstance(top_card, dict) else None


def _havoc_top_card_feel_no_pain_block(snapshot: Dict[str, Any]) -> int:
    if _draw_pile_top_card(snapshot) is None:
        return 0
    return max(0, _snapshot_power_amount(snapshot.get("player", {}), "Feel No Pain"))


def _effect_play_second_wind_block(
    card,
    before: Dict[str, Any],
    source_card=None,
    player: Optional[Dict[str, Any]] = None,
) -> int:
    card_name = _known_card_name(card, SECOND_WIND_BLOCK_PER_CARD)
    if card_name is None:
        return 0
    per_card = SECOND_WIND_BLOCK_PER_CARD[card_name]
    if card_upgrade_count(card) > 0:
        per_card += 2
    count = _effect_play_exhausts_non_attack_hand_count(card, before, source_card)
    if player is not None:
        return sum(_modified_block(per_card, player) for _ in range(count))
    return count * per_card


def _effect_play_exhausts_non_attack_hand_count(
    card,
    before: Dict[str, Any],
    source_card=None,
) -> int:
    if _known_card_name(card, EXHAUSTS_NON_ATTACK_HAND_CARDS) is None:
        return 0
    return sum(
        1
        for hand_card in _snapshot_remaining_hand_after_effect_source(before, source_card)
        if not _snapshot_card_is_attack(hand_card)
    )


def _snapshot_player_entangled(snapshot: Dict[str, Any]) -> bool:
    return _snapshot_power_amount(snapshot.get("player", {}), "Entangled") > 0


def _effect_played_card_conditions_allow(
    card,
    snapshot: Dict[str, Any],
    source_card=None,
) -> bool:
    if _known_card_name(card, CLASH_CARDS) != "Clash":
        return True
    return all(
        _snapshot_card_is_attack(hand_card)
        for hand_card in _snapshot_remaining_hand_after_effect_source(
            snapshot,
            source_card,
        )
    )


def _effect_source_identity(source_card) -> str:
    if source_card is None:
        return ""
    if isinstance(source_card, dict):
        return _snapshot_card_identity(source_card)
    return _card_identity(source_card)


def _snapshot_remaining_hand_after_effect_source(
    snapshot: Dict[str, Any],
    source_card=None,
) -> List[Dict[str, Any]]:
    source_identity = _effect_source_identity(source_card)
    skipped_source = False
    remaining: List[Dict[str, Any]] = []
    for hand_card in snapshot.get("hand", []) or []:
        if not isinstance(hand_card, dict):
            continue
        hand_identity = _snapshot_card_identity(hand_card)
        if source_identity:
            if source_identity.startswith("uuid:") and hand_identity == source_identity:
                continue
            if (
                not source_identity.startswith("uuid:")
                and not skipped_source
                and hand_identity == source_identity
            ):
                skipped_source = True
                continue
        remaining.append(hand_card)
    return remaining


def _pop_expected_draw_pile_top(expected: Dict[str, Any]) -> None:
    draw_pile = expected.get("draw_pile")
    if isinstance(draw_pile, list) and draw_pile:
        draw_pile.pop()
        expected["draw_pile_count"] = len(draw_pile)
        return
    expected["draw_pile_count"] = max(
        0,
        _to_int(expected.get("draw_pile_count")) - 1,
    )


def _single_alive_monster_index(snapshot: Dict[str, Any]) -> Optional[int]:
    alive = [
        index
        for index, monster in enumerate(snapshot.get("monsters", []) or [])
        if not monster.get("gone")
        and not monster.get("half_dead")
        and _to_int(monster.get("hp")) > 0
    ]
    return alive[0] if len(alive) == 1 else None


def _sharp_hide_reflection_damage(
    snapshot: Dict[str, Any],
    target_index: Optional[int] = None,
    all_targets: bool = False,
) -> int:
    monsters = snapshot.get("monsters", [])
    if all_targets:
        candidates = monsters
    elif target_index is not None and 0 <= target_index < len(monsters):
        candidates = [monsters[target_index]]
    else:
        candidates = []

    for monster in candidates:
        if monster.get("gone") or monster.get("half_dead") or _to_int(monster.get("hp")) <= 0:
            continue
        if not _is_guardian_monster(monster):
            continue
        amount = _snapshot_power_amount(monster, "Sharp Hide")
        if amount > 0:
            return amount
    return 0


def _thorns_reflection_damage(monster: Dict[str, Any]) -> int:
    if monster.get("gone") or monster.get("half_dead"):
        return 0
    return max(0, _snapshot_power_amount(monster, "Thorns"))


def _is_guardian_monster(monster: Dict[str, Any]) -> bool:
    return (
        _normalize(monster.get("id")) == "theguardian"
        or _normalize(monster.get("name")) == "theguardian"
    )


def _is_lagavulin_monster(monster: Dict[str, Any]) -> bool:
    return (
        _normalize(monster.get("id")) == "lagavulin"
        or _normalize(monster.get("name")) == "lagavulin"
    )


def _snapshot_power_amount(entity: Dict[str, Any], power_name: str) -> int:
    target = _normalize(power_name)
    for power in entity.get("powers", []) or []:
        identifiers = {
            _normalize(power.get("id")),
            _normalize(power.get("name")),
        }
        if target in identifiers:
            return _to_int(power.get("amount"), default=1)
    return 0


def _snapshot_has_power(entity: Dict[str, Any], power_name: str) -> bool:
    target = _normalize(power_name)
    for power in entity.get("powers", []) or []:
        identifiers = {
            _normalize(power.get("id")),
            _normalize(power.get("name")),
        }
        if target in identifiers:
            return True
    return False


def _set_snapshot_power_amount(entity: Dict[str, Any], power_name: str, amount: int) -> None:
    target = _normalize(power_name)
    for power in entity.get("powers", []) or []:
        identifiers = {
            _normalize(power.get("id")),
            _normalize(power.get("name")),
        }
        if target in identifiers:
            power["amount"] = amount
            return


def _add_snapshot_power_amount(entity: Dict[str, Any], power_name: str, amount: int) -> None:
    if amount <= 0:
        return
    target = _normalize(power_name)
    powers = entity.setdefault("powers", [])
    for power in powers:
        identifiers = {
            _normalize(power.get("id")),
            _normalize(power.get("name")),
        }
        if target in identifiers:
            power["amount"] = _to_int(power.get("amount"), default=0) + amount
            return
    powers.append({"id": power_name, "name": power_name, "amount": amount})


def _ensure_snapshot_power(entity: Dict[str, Any], power_name: str, amount: int) -> None:
    if _snapshot_has_power(entity, power_name):
        return
    entity.setdefault("powers", []).append(
        {"id": power_name, "name": power_name, "amount": amount}
    )


def _remove_snapshot_power(entity: Dict[str, Any], power_name: str) -> None:
    target = _normalize(power_name)
    entity["powers"] = [
        power
        for power in entity.get("powers", []) or []
        if target
        not in {
            _normalize(power.get("id")),
            _normalize(power.get("name")),
        }
    ]


def _card_self_damage(card) -> int:
    card_name = _known_card_name(card, CARD_SELF_DAMAGE)
    if card_name is None:
        return 0
    return CARD_SELF_DAMAGE.get(card_name, 0)


def _card_play_hp_loss_events(
    card,
    snapshot: Dict[str, Any],
    card_index: int,
) -> list[tuple[int, bool]]:
    events = []
    self_damage = _card_self_damage(card)
    if self_damage > 0:
        events.append((self_damage, True))
    blue_candle_loss = _blue_candle_curse_hp_loss(card, snapshot)
    if blue_candle_loss > 0:
        events.append((blue_candle_loss, True))
    events.extend(_pain_card_play_hp_loss_events(snapshot, card_index))
    return events


def _pain_card_play_hp_loss_events(
    snapshot: Dict[str, Any],
    card_index: int,
) -> list[tuple[int, bool]]:
    events = []
    for index, hand_card in enumerate(snapshot.get("hand", []) or []):
        if index == card_index:
            continue
        if not isinstance(hand_card, dict):
            continue
        if _snapshot_known_card_name(hand_card, PAIN_CARDS) == "Pain":
            events.append((1, False))
    return events


def _blue_candle_curse_hp_loss(card, snapshot: Dict[str, Any]) -> int:
    if not _is_curse_card(card):
        return 0
    return 1 if _snapshot_has_relic(snapshot, "Blue Candle") else 0


def _card_energy_gain(card) -> int:
    card_name = _known_card_name(card, CARD_ENERGY_GAIN)
    if card_name is None:
        return 0
    if card_name == "Bloodletting" and card_upgrade_count(card) > 0:
        return 3
    return CARD_ENERGY_GAIN.get(card_name, 0)


def _card_heal(card) -> int:
    card_name = _known_card_name(card, CARD_HEAL)
    if card_name is None:
        return 0
    heal = CARD_HEAL.get(card_name, 0)
    if card_name == "Bandage Up" and card_upgrade_count(card) > 0:
        heal += 2
    return heal


def _card_draw_count(card) -> int:
    card_name = _known_card_name(card, CARD_DRAW)
    if card_name is None:
        return 0
    base_draw, upgraded_draw = CARD_DRAW[card_name]
    return upgraded_draw if card_upgrade_count(card) > 0 else base_draw


def _conditional_card_energy_gain(card, snapshot: Dict[str, Any], target_index: Optional[int]) -> int:
    if _known_card_name(card, BASE_ATTACK_DAMAGE) != "Dropkick":
        return 0
    monsters = snapshot.get("monsters", [])
    if target_index is None or target_index < 0 or target_index >= len(monsters):
        return 0
    return 1 if _snapshot_power_amount(monsters[target_index], "Vulnerable") > 0 else 0


def _sync_rampage_state(floor: int) -> None:
    global _rampage_damage_bonus_by_card, _rampage_state_floor
    if _rampage_state_floor == floor:
        return
    _rampage_state_floor = floor
    _rampage_damage_bonus_by_card = {}


def _sync_attack_count_state(floor: int, turn: int) -> None:
    global _attack_count_state_floor, _attack_count_state_turn, _attacks_played_this_turn
    global _necronomicon_used_this_turn
    if _attack_count_state_floor == floor and _attack_count_state_turn == turn:
        return
    _attack_count_state_floor = floor
    _attack_count_state_turn = turn
    _attacks_played_this_turn = 0
    _necronomicon_used_this_turn = False


def _finalize_observed_action(pending: Dict[str, Any], actual: Dict[str, Any]) -> None:
    action = pending.get("action", {})
    if action.get("type") != "PlayCardAction":
        return
    card = action.get("card") or {}
    if not isinstance(card, dict):
        return
    _finalize_attack_count(card, actual)
    _finalize_necronomicon_usage(card, pending, actual)
    if not _snapshot_card_is_named(card, "Rampage"):
        return
    key = _snapshot_card_identity(card)
    if not key:
        return
    if key.startswith("uuid:") and _snapshot_hand_contains_identity(actual.get("hand", []), key):
        return
    _rampage_damage_bonus_by_card[key] = (
        _rampage_damage_bonus_by_card.get(key, 0)
        + _rampage_scaling_from_snapshot(card)
    )


def _finalize_attack_count(card: Dict[str, Any], actual: Dict[str, Any]) -> None:
    global _attacks_played_this_turn
    if not _snapshot_card_is_attack(card):
        return
    key = _snapshot_card_identity(card)
    if key.startswith("uuid:") and _snapshot_hand_contains_identity(actual.get("hand", []), key):
        return
    _attacks_played_this_turn += 1


def _finalize_necronomicon_usage(
    card: Dict[str, Any],
    pending: Dict[str, Any],
    actual: Dict[str, Any],
) -> None:
    global _necronomicon_used_this_turn
    before = pending.get("before") or {}
    if (
        _necronomicon_used_this_turn
        or not _snapshot_has_relic(before, "Necronomicon")
        or not _snapshot_card_is_attack(card)
        or _card_cost(card) < 2
    ):
        return
    key = _snapshot_card_identity(card)
    if key.startswith("uuid:") and _snapshot_hand_contains_identity(actual.get("hand", []), key):
        return
    _necronomicon_used_this_turn = True


def _rampage_damage_bonus_for_card(card) -> int:
    key = _card_identity(card)
    if not key:
        return 0
    return max(0, _rampage_damage_bonus_by_card.get(key, 0))


def _rampage_scaling_from_snapshot(card: Dict[str, Any]) -> int:
    return 8 if _snapshot_card_upgrade_count(card) > 0 else 5


def _snapshot_card_upgrade_count(card: Dict[str, Any]) -> int:
    upgrades = _to_int(card.get("upgrades", 0))
    if upgrades > 0:
        return upgrades
    return 1 if _safe_str(card.get("name", "")).endswith("+") else 0


def _snapshot_card_is_named(card: Dict[str, Any], name: str) -> bool:
    target = _normalize(name)
    identifiers = {
        _normalize(_strip_upgrade_suffix(card.get("id"))),
        _normalize(_strip_upgrade_suffix(card.get("name"))),
    }
    return target in identifiers


def _card_identity(card) -> str:
    uuid = _safe_str(getattr(card, "uuid", ""))
    if uuid:
        return f"uuid:{uuid}"
    identifiers = [
        _normalize(_strip_upgrade_suffix(getattr(card, "card_id", getattr(card, "id", "")))),
        _normalize(_strip_upgrade_suffix(getattr(card, "name", ""))),
    ]
    identifiers = [value for value in identifiers if value]
    return "card:" + ":".join(identifiers) if identifiers else ""


def _snapshot_card_identity(card: Dict[str, Any]) -> str:
    uuid = _safe_str(card.get("uuid", ""))
    if uuid:
        return f"uuid:{uuid}"
    identifiers = [
        _normalize(_strip_upgrade_suffix(card.get("id"))),
        _normalize(_strip_upgrade_suffix(card.get("name"))),
    ]
    identifiers = [value for value in identifiers if value]
    return "card:" + ":".join(identifiers) if identifiers else ""


def _snapshot_hand_contains_identity(hand, identity: str) -> bool:
    for card in _safe_iterable(hand):
        if isinstance(card, dict) and _snapshot_card_identity(card) == identity:
            return True
    return False


def _positive_card_misc(card) -> int:
    return max(0, _to_int(_card_attr(card, "misc", 0)))


def _known_card_name(card, known_values: Dict[str, int]) -> Optional[str]:
    known_by_normalized = {_normalize(name): name for name in known_values}
    for attr in ("name", "card_id", "id"):
        value = _card_attr(card, attr, None)
        if value in CARD_ID_ALIASES:
            alias = CARD_ID_ALIASES[value]
            if alias in known_values:
                return alias
        normalized = _normalize(_strip_upgrade_suffix(value))
        if normalized in known_by_normalized:
            return known_by_normalized[normalized]
    return None


def _card_attr(card, attr: str, default=None):
    if isinstance(card, dict):
        if attr == "card_id":
            return card.get("card_id", card.get("id", default))
        if attr == "id":
            return card.get("id", card.get("card_id", default))
        if attr == "card_type":
            return card.get("card_type", card.get("type", default))
        if attr == "cost_for_turn":
            return card.get("cost_for_turn", card.get("cost", default))
        return card.get(attr, default)
    return getattr(card, attr, default)


def _potion_attr(potion, attr: str, default=None):
    if isinstance(potion, dict):
        if attr == "potion_id":
            return potion.get("potion_id", potion.get("id", default))
        if attr == "id":
            return potion.get("id", potion.get("potion_id", default))
        return potion.get(attr, default)
    return getattr(potion, attr, default)


def _strip_upgrade_suffix(value) -> str:
    text = str(value or "")
    if "+" not in text:
        return text
    base, suffix = text.rsplit("+", 1)
    if suffix == "" or suffix.isdigit():
        return base
    return text


def _normalize(value) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _safe_iterable(value):
    return value if isinstance(value, (list, tuple)) else []


def _pile_count(game, attr: str) -> int:
    return len(_safe_iterable(getattr(game, attr, [])))


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value)


def _json_scalar(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _to_int(value, default=0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        try:
            return int(float(value))
        except (TypeError, ValueError, OverflowError):
            return default


def _to_float(value, default=0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
