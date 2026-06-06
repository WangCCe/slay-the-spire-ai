"""Single-step simulation divergence traces for live combat diagnosis."""

import copy
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from spirecomm.ai.heuristics.card_upgrades import (
    card_upgrade_count,
    heavy_blade_strength_multiplier,
    known_block_upgrade_bonus,
    known_damage_upgrade_bonus,
)


TRACE_ENV = "STS_SIM_DIVERGENCE_TRACE_FILE"
DISABLED_VALUES = {"", "0", "false", "off", "none", "disabled"}

BASE_ATTACK_DAMAGE = {
    "Anger": 6,
    "Bash": 8,
    "Bludgeon": 32,
    "Blood for Blood": 18,
    "Carnage": 20,
    "Cleave": 8,
    "Clothesline": 12,
    "Dropkick": 5,
    "Headbutt": 9,
    "Heavy Blade": 14,
    "Hemokinesis": 15,
    "Immolate": 21,
    "Iron Wave": 5,
    "Pommel Strike": 9,
    "Pummel": 8,
    "Rampage": 8,
    "Reckless Charge": 7,
    "Reaper": 4,
    "Sever Soul": 16,
    "Strike": 6,
    "Swift Strike": 7,
    "Sword Boomerang": 9,
    "Thunderclap": 4,
    "Twin Strike": 10,
    "Uppercut": 13,
    "Whirlwind": 5,
}

MULTI_HIT_ATTACKS = {
    "Pummel": 4,
    "Sword Boomerang": 3,
    "Twin Strike": 2,
}

ALL_ENEMY_ATTACKS = {
    "Cleave": 0,
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
    "Power Through": 15,
    "Shrug It Off": 8,
    "True Grit": 7,
}

SECOND_WIND_BLOCK_PER_CARD = {
    "Second Wind": 5,
}

CARD_SELF_DAMAGE = {
    "Bloodletting": 3,
    "Hemokinesis": 2,
    "Offering": 6,
}

CARD_ENERGY_GAIN = {
    "Bloodletting": 2,
    "Offering": 2,
    "Seeing Red": 2,
}

CARD_HEAL = {
    "Bandage Up": 4,
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
    _pending_expected = None
    _rampage_damage_bonus_by_card = {}
    _rampage_state_floor = None
    _attack_count_state_floor = None
    _attack_count_state_turn = None
    _attacks_played_this_turn = 0


def record_expected_action(action, game, path: Optional[Path] = None) -> bool:
    """Record a read-only one-action expectation for the next live state."""
    global _pending_expected

    if divergence_trace_path(path) is None:
        return False
    if action is None or not getattr(game, "in_combat", False):
        _pending_expected = None
        return False

    try:
        _sync_rampage_state(_to_int(getattr(game, "floor", None)))
        before = snapshot_combat_state(game)
        _sync_attack_count_state(before["floor"], before["turn"])
        _pending_expected = {
            "timestamp": _timestamp(),
            "unix_time": round(time.time(), 3),
            "floor": before["floor"],
            "turn": before["turn"],
            "before": before,
            "expected": _expected_after_action(action, game, before),
            "action": _action_summary(action, game),
        }
        return True
    except Exception as exc:
        _pending_expected = None
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

        ignored_diffs = _ignored_diff_keys(pending)
        diffs = _diff_snapshots(pending["expected"], actual, ignored_diffs)
        if not diffs:
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
        "relics": [_relic_summary(relic) for relic in _safe_iterable(getattr(game, "relics", []))],
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
            energy_before_card = expected["player"]["energy"]
            target_index = None
            if _is_whirlwind(card):
                expected["player"]["energy"] = 0
            else:
                expected["player"]["energy"] = max(
                    0,
                    energy_before_card - max(0, _card_cost(card)),
                )
            if _is_attack_card(card):
                damage, hit_count = _card_damage_and_hits_for_snapshot(
                    card,
                    expected.get("player", {}),
                    energy_before_card,
                )
                if _is_all_enemy_attack(card):
                    damage_dealt = _apply_expected_attack_to_all(expected, damage, hit_count)
                else:
                    target_index = _target_index_for_action(action, game)
                    damage_dealt = _apply_expected_attack(expected, target_index, damage, hit_count)
                if _is_reaper(card) and damage_dealt > 0:
                    _heal_player(expected, damage_dealt)
                rage_block = _rage_attack_block(expected.get("player", {}))
                if rage_block > 0:
                    expected["player"]["block"] += rage_block
                ornamental_fan_block = _ornamental_fan_attack_block(before)
                if ornamental_fan_block > 0:
                    expected["player"]["block"] += ornamental_fan_block
            self_damage = _card_self_damage(card)
            if self_damage > 0:
                expected["player"]["current_hp"] = max(
                    0,
                    expected["player"]["current_hp"] - self_damage,
                )
            heal = _card_heal(card)
            if heal > 0:
                _heal_player(expected, heal)
            energy_gain = _card_energy_gain(card)
            energy_gain += _conditional_card_energy_gain(card, before, target_index)
            if energy_gain > 0:
                expected["player"]["energy"] += energy_gain
            block = _card_block(card)
            if block > 0:
                expected["player"]["block"] += _modified_block(block, expected.get("player", {}))
            second_wind_block = _second_wind_block(
                card,
                before,
                card_index,
                expected.get("player", {}),
            )
            if second_wind_block > 0:
                expected["player"]["block"] += second_wind_block
        if 0 <= card_index < len(expected["hand"]):
            expected["hand"].pop(card_index)

    elif action_type == "EndTurnAction":
        incoming = _incoming_damage_from_snapshot(before)
        current_block = expected["player"]["block"]
        expected["player"]["current_hp"] = max(
            0,
            expected["player"]["current_hp"] - max(0, incoming - current_block),
        )
        expected["player"]["block"] = 0
        expected["player"]["energy"] = 0

    return expected


def _apply_expected_attack(
    expected: Dict[str, Any],
    target_index: Optional[int],
    damage: int,
    hit_count: int = 1,
) -> int:
    if target_index is None or target_index < 0:
        return 0
    monsters = expected.get("monsters", [])
    if target_index >= len(monsters):
        return 0
    target = monsters[target_index]
    curl_up_applied = False
    damage_dealt = 0
    for _ in range(max(0, hit_count)):
        if target.get("gone") or target.get("half_dead") or _to_int(target.get("hp")) <= 0:
            break
        remaining_damage = _modified_attack_damage(max(0, damage), target)
        if target["block"] > 0:
            blocked = min(target["block"], remaining_damage)
            target["block"] -= blocked
            remaining_damage -= blocked
        hp_before = target["hp"]
        target["hp"] = max(0, target["hp"] - remaining_damage)
        hp_loss = max(0, hp_before - target["hp"])
        damage_dealt += hp_loss
        if target["hp"] <= 0:
            target["gone"] = True
            break
        if not curl_up_applied and hp_loss > 0:
            curl_up_block = max(0, _snapshot_power_amount(target, "Curl Up"))
            if curl_up_block > 0:
                target["block"] += curl_up_block
                curl_up_applied = True
    return damage_dealt


def _apply_expected_attack_to_all(
    expected: Dict[str, Any],
    damage: int,
    hit_count: int = 1,
) -> int:
    damage_dealt = 0
    for index, monster in enumerate(expected.get("monsters", [])):
        if monster.get("gone") or monster.get("half_dead") or _to_int(monster.get("hp")) <= 0:
            continue
        damage_dealt += _apply_expected_attack(expected, index, damage, hit_count)
    return damage_dealt


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


def _ignored_diff_keys(pending: Dict[str, Any]) -> set:
    action = pending.get("action", {})
    if action.get("type") == "EndTurnAction":
        return {"player.energy"}
    return set()


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
        if monster.get("gone") or monster.get("half_dead"):
            continue
        if "attack" not in _normalize(monster.get("intent")):
            continue
        total += max(0, _to_int(monster.get("move_damage"))) * max(
            1,
            _to_int(monster.get("move_hits"), default=1),
        )
    return total


def _card_for_action(action, game):
    card = getattr(action, "card", None)
    if card is not None:
        return card
    card_index = _to_int(getattr(action, "card_index", -1), default=-1)
    hand = list(_safe_iterable(getattr(game, "hand", [])))
    if 0 <= card_index < len(hand):
        return hand[card_index]
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
    return summary


def _card_summary(card) -> Dict[str, Any]:
    return {
        "name": _safe_str(getattr(card, "name", "")),
        "id": _safe_str(getattr(card, "card_id", getattr(card, "id", ""))),
        "uuid": _safe_str(getattr(card, "uuid", "")),
        "type": _safe_str(
            getattr(card, "type", getattr(card, "card_type", ""))
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
    }


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
        "gone": bool(getattr(monster, "is_gone", False)),
        "half_dead": bool(getattr(monster, "half_dead", False)),
        "powers": [_power_summary(power) for power in _safe_iterable(getattr(monster, "powers", []))],
    }


def _is_attack_card(card) -> bool:
    card_type = _normalize(getattr(card, "type", getattr(card, "card_type", "")))
    return card_type in {"attack", "cardtypeattack"}


def _is_all_enemy_attack(card) -> bool:
    return _known_card_name(card, ALL_ENEMY_ATTACKS) is not None


def _is_whirlwind(card) -> bool:
    return _known_card_name(card, BASE_ATTACK_DAMAGE) == "Whirlwind"


def _is_reaper(card) -> bool:
    return _known_card_name(card, BASE_ATTACK_DAMAGE) == "Reaper"


def _card_cost(card) -> int:
    return max(
        0,
        _to_int(getattr(card, "cost_for_turn", getattr(card, "cost", 0))),
    )


def _card_damage(card) -> int:
    explicit = _to_int(getattr(card, "damage", 0))
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
) -> tuple[int, int]:
    damage = _card_damage(card)
    card_name = _known_card_name(card, BASE_ATTACK_DAMAGE)
    if card_name == "Whirlwind":
        per_hit = _source_modified_attack_damage(damage, card, player)
        return max(0, energy_available) * per_hit, 1
    hit_count = _multi_hit_count(card, card_name)
    if hit_count > 1 and card_name is not None:
        damage = _multi_hit_damage_per_hit(card, card_name, hit_count)
    return _source_modified_attack_damage(damage, card, player), hit_count


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


def _card_block(card) -> int:
    explicit = _to_int(getattr(card, "block", 0))
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
    non_attack_count = 0
    skipped_played_card = False
    for index, hand_card in enumerate(before.get("hand", [])):
        if index == card_index:
            continue
        if card_index < 0 and not skipped_played_card and _snapshot_card_matches(hand_card, card):
            skipped_played_card = True
            continue
        if not _snapshot_card_is_attack(hand_card):
            non_attack_count += 1
    if player is not None:
        return sum(_modified_block(per_card, player) for _ in range(non_attack_count))
    return non_attack_count * per_card


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


def _source_modified_attack_damage(damage: int, card, player: Dict[str, Any]) -> int:
    if damage <= 0:
        return 0
    strength = _snapshot_power_amount(player, "Strength")
    if strength != 0:
        if _known_card_name(card, BASE_ATTACK_DAMAGE) == "Heavy Blade":
            damage += strength * heavy_blade_strength_multiplier(card)
        else:
            damage += strength
    if _snapshot_power_amount(player, "Weakened") > 0 or _snapshot_power_amount(player, "Weak") > 0:
        damage = damage * 3 // 4
    return max(0, damage)


def _modified_attack_damage(damage: int, target: Dict[str, Any]) -> int:
    if damage <= 0:
        return 0
    if _snapshot_power_amount(target, "Vulnerable") > 0:
        damage = damage * 3 // 2
    return max(0, damage)


def _modified_block(block: int, player: Dict[str, Any]) -> int:
    if block <= 0:
        return 0
    block += _snapshot_power_amount(player, "Dexterity")
    if _snapshot_power_amount(player, "Frail") > 0:
        block = block * 3 // 4
    return max(0, block)


def _rage_attack_block(player: Dict[str, Any]) -> int:
    return max(0, _snapshot_power_amount(player, "Rage"))


def _ornamental_fan_attack_block(snapshot: Dict[str, Any]) -> int:
    if not _snapshot_has_relic(snapshot, "Ornamental Fan"):
        return 0
    attack_count_after_play = _attacks_played_this_turn + 1
    return 4 if attack_count_after_play > 0 and attack_count_after_play % 3 == 0 else 0


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


def _heal_player(expected: Dict[str, Any], amount: int) -> None:
    if amount <= 0:
        return
    player = expected.get("player", {})
    player["current_hp"] = min(
        _to_int(player.get("max_hp")),
        _to_int(player.get("current_hp")) + amount,
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


def _card_self_damage(card) -> int:
    card_name = _known_card_name(card, CARD_SELF_DAMAGE)
    if card_name is None:
        return 0
    return CARD_SELF_DAMAGE.get(card_name, 0)


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
    if _attack_count_state_floor == floor and _attack_count_state_turn == turn:
        return
    _attack_count_state_floor = floor
    _attack_count_state_turn = turn
    _attacks_played_this_turn = 0


def _finalize_observed_action(pending: Dict[str, Any], actual: Dict[str, Any]) -> None:
    action = pending.get("action", {})
    if action.get("type") != "PlayCardAction":
        return
    card = action.get("card") or {}
    if not isinstance(card, dict):
        return
    _finalize_attack_count(card, actual)
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
    return max(0, _to_int(getattr(card, "misc", 0)))


def _known_card_name(card, known_values: Dict[str, int]) -> Optional[str]:
    known_by_normalized = {_normalize(name): name for name in known_values}
    for attr in ("name", "card_id", "id"):
        value = getattr(card, attr, None)
        if value in CARD_ID_ALIASES:
            alias = CARD_ID_ALIASES[value]
            if alias in known_values:
                return alias
        normalized = _normalize(_strip_upgrade_suffix(value))
        if normalized in known_by_normalized:
            return known_by_normalized[normalized]
    return None


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


def _timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
