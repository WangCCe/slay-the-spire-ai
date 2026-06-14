"""Small JSONL decision traces for live gameplay diagnosis."""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


TRACE_ENV = "STS_DECISION_TRACE_FILE"
DISABLED_VALUES = {"", "0", "false", "off", "none", "disabled"}

logger = logging.getLogger(__name__)


def decision_trace_path(path: Optional[Path] = None) -> Optional[Path]:
    if path is not None:
        return Path(path)
    value = os.environ.get(TRACE_ENV)
    if value is None or value.strip().lower() in DISABLED_VALUES:
        return None
    return Path(value)


def build_decision_trace_event(
    action,
    game,
    source: str,
    decision_path: str = "",
) -> Dict[str, Any]:
    player = getattr(game, "player", None)
    return {
        "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        "unix_time": round(time.time(), 3),
        "source": str(source),
        "decision_path": str(decision_path or ""),
        "floor": _to_int(getattr(game, "floor", None)),
        "turn": _to_int(getattr(game, "turn", None)),
        "act": _to_int(getattr(game, "act", None)),
        "room_type": _safe_str(getattr(game, "room_type", "")),
        "screen_type": _safe_str(getattr(game, "screen_type", "")),
        "in_combat": bool(getattr(game, "in_combat", False)),
        "gold": _to_int(getattr(game, "gold", None)),
        "player": _player_summary(game, player),
        "deck": [_card_summary(card) for card in _safe_iterable(getattr(game, "deck", []))],
        "relics": [
            _relic_summary(relic)
            for relic in _safe_iterable(getattr(game, "relics", []))
        ],
        "hand": [_card_summary(card) for card in _safe_iterable(getattr(game, "hand", []))],
        "monsters": [
            _monster_summary(monster)
            for monster in _safe_iterable(getattr(game, "monsters", []))
        ],
        "potions": [
            _potion_summary(potion)
            for potion in _safe_iterable(getattr(game, "potions", []))
        ],
        "available_commands": [
            _safe_str(command)
            for command in _safe_iterable(getattr(game, "available_commands", []))
        ],
        "screen": _screen_summary(game),
        "action": _action_summary(action, game),
    }


def write_decision_trace_event(
    action,
    game,
    source: str = "combat_rl",
    decision_path: str = "",
    path: Optional[Path] = None,
) -> bool:
    target = decision_trace_path(path)
    if target is None:
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        event = build_decision_trace_event(
            action,
            game,
            source=source,
            decision_path=decision_path,
        )
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return True
    except Exception as exc:
        logger.debug("decision trace write failed: %s", exc)
        return False


def _player_summary(game, player) -> Dict[str, Any]:
    return {
        "current_hp": _to_int(
            getattr(player, "current_hp", getattr(game, "current_hp", None))
        ),
        "max_hp": _to_int(getattr(player, "max_hp", getattr(game, "max_hp", None))),
        "block": _to_int(getattr(player, "block", getattr(game, "block", None))),
        "energy": _to_int(getattr(player, "energy", getattr(game, "energy", None))),
    }


def _card_summary(card) -> Dict[str, Any]:
    return {
        "name": _safe_str(getattr(card, "name", "")),
        "id": _safe_str(getattr(card, "card_id", getattr(card, "id", ""))),
        "cost": _to_int(
            getattr(card, "cost_for_turn", getattr(card, "cost", None)),
            default=None,
        ),
        "playable": _safe_bool(getattr(card, "is_playable", None)),
        "type": _safe_str(getattr(card, "card_type", "")),
        "price": _to_int(getattr(card, "price", None), default=0),
    }


def _relic_summary(relic) -> Dict[str, Any]:
    return {
        "name": _safe_str(getattr(relic, "name", "")),
        "id": _safe_str(getattr(relic, "relic_id", getattr(relic, "id", ""))),
        "counter": _to_int(getattr(relic, "counter", None), default=0),
        "price": _to_int(getattr(relic, "price", None), default=0),
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
        "move_hits": _to_int(getattr(monster, "move_hits", None)),
        "gone": bool(getattr(monster, "is_gone", False)),
        "half_dead": bool(getattr(monster, "half_dead", False)),
    }


def _potion_summary(potion) -> Dict[str, Any]:
    return {
        "name": _safe_str(getattr(potion, "name", "")),
        "id": _safe_str(getattr(potion, "potion_id", getattr(potion, "id", ""))),
        "can_use": _safe_bool(getattr(potion, "can_use", None)),
        "price": _to_int(getattr(potion, "price", None), default=0),
    }


def _screen_summary(game) -> Dict[str, Any]:
    screen = getattr(game, "screen", None)
    screen_type = _safe_str(getattr(game, "screen_type", ""))
    if screen is None:
        return {}

    summary: Dict[str, Any] = {"type": screen_type}
    if "CARD_REWARD" in screen_type:
        summary.update(
            {
                "cards": [
                    _card_summary(card)
                    for card in _safe_iterable(getattr(screen, "cards", []))
                ],
                "can_bowl": _safe_bool(getattr(screen, "can_bowl", None)),
                "can_skip": _safe_bool(getattr(screen, "can_skip", None)),
            }
        )
    elif "SHOP_SCREEN" in screen_type:
        summary.update(
            {
                "cards": [
                    _card_summary(card)
                    for card in _safe_iterable(getattr(screen, "cards", []))
                ],
                "relics": [
                    _relic_summary(relic)
                    for relic in _safe_iterable(getattr(screen, "relics", []))
                ],
                "potions": [
                    _potion_summary(potion)
                    for potion in _safe_iterable(getattr(screen, "potions", []))
                ],
                "purge_available": _safe_bool(getattr(screen, "purge_available", None)),
                "purge_cost": _to_int(getattr(screen, "purge_cost", None), default=None),
            }
        )
    elif "EVENT" in screen_type:
        summary.update(
            {
                "event_name": _safe_str(getattr(screen, "event_name", "")),
                "event_id": _safe_str(getattr(screen, "event_id", "")),
                "options": [
                    _event_option_summary(option)
                    for option in _safe_iterable(getattr(screen, "options", []))
                ],
            }
        )
    elif "MAP" in screen_type:
        summary.update(
            {
                "current_node": _node_summary(getattr(screen, "current_node", None)),
                "next_nodes": [
                    _node_summary(node)
                    for node in _safe_iterable(getattr(screen, "next_nodes", []))
                ],
                "boss_available": _safe_bool(getattr(screen, "boss_available", None)),
                "map": _map_summary(getattr(game, "map", None)),
                "paths": _map_paths_summary(screen, getattr(game, "map", None)),
            }
        )
    return summary


def _event_option_summary(option) -> Dict[str, Any]:
    return {
        "text": _safe_str(getattr(option, "text", "")),
        "label": _safe_str(getattr(option, "label", "")),
        "disabled": _safe_bool(getattr(option, "disabled", None)),
        "choice_index": _to_int(getattr(option, "choice_index", None), default=None),
    }


def _node_summary(node) -> Optional[Dict[str, Any]]:
    if node is None:
        return None
    return {
        "x": _to_int(getattr(node, "x", None), default=None),
        "y": _to_int(getattr(node, "y", None), default=None),
        "symbol": _safe_str(getattr(node, "symbol", "")),
    }


def _map_summary(dungeon_map) -> Dict[str, Any]:
    nodes_by_y = getattr(dungeon_map, "nodes", None)
    if not isinstance(nodes_by_y, dict):
        return {"nodes": []}

    nodes = []
    for y in sorted(nodes_by_y):
        row = nodes_by_y.get(y)
        if not isinstance(row, dict):
            continue
        for x in sorted(row):
            node = row.get(x)
            node_summary = _node_summary(node)
            if node_summary is None:
                continue
            node_summary["children"] = [
                {
                    "x": _to_int(getattr(child, "x", None), default=None),
                    "y": _to_int(getattr(child, "y", None), default=None),
                }
                for child in _safe_iterable(getattr(node, "children", []))
            ]
            nodes.append(node_summary)
    return {"nodes": nodes}


def _map_paths_summary(
    screen,
    dungeon_map=None,
    max_depth: int = 6,
    max_paths_per_choice: int = 4,
) -> List[Dict[str, Any]]:
    paths: List[Dict[str, Any]] = []
    next_nodes = list(_safe_iterable(getattr(screen, "next_nodes", [])))
    for choice, node in enumerate(next_nodes):
        node = _resolve_map_node(dungeon_map, node) or node
        choice_paths: List[List[Any]] = []
        _collect_paths(node, [], choice_paths, max_depth=max_depth, max_paths=max_paths_per_choice)
        for path in choice_paths:
            node_labels = [_safe_str(getattr(path_node, "symbol", "")) for path_node in path]
            paths.append(
                {
                    "choice": choice,
                    "label": " -> ".join(
                        f"{getattr(path_node, 'symbol', '')}@{getattr(path_node, 'x', '?')},{getattr(path_node, 'y', '?')}"
                        for path_node in path
                    ),
                    "nodes": node_labels,
                }
            )
    return paths


def _resolve_map_node(dungeon_map, node):
    if node is None:
        return None
    nodes_by_y = getattr(dungeon_map, "nodes", None)
    if not isinstance(nodes_by_y, dict):
        return None
    y = getattr(node, "y", None)
    x = getattr(node, "x", None)
    row = nodes_by_y.get(y)
    if not isinstance(row, dict):
        return None
    return row.get(x)


def _collect_paths(node, prefix: List[Any], paths: List[List[Any]], max_depth: int, max_paths: int) -> None:
    if node is None or len(paths) >= max_paths:
        return
    current = prefix + [node]
    children = list(_safe_iterable(getattr(node, "children", [])))
    if not children or len(current) >= max_depth:
        paths.append(current)
        return
    for child in children:
        _collect_paths(child, current, paths, max_depth=max_depth, max_paths=max_paths)
        if len(paths) >= max_paths:
            break


def _action_summary(action, game) -> Dict[str, Any]:
    summary = {
        "type": type(action).__name__ if action is not None else None,
        "command": _safe_str(getattr(action, "command", "")),
    }
    for attr in ("card_index", "target_index", "choice_index", "name", "use"):
        if hasattr(action, attr):
            summary[attr] = _json_scalar(getattr(action, attr))

    card = getattr(action, "card", None)
    card_index = getattr(action, "card_index", None)
    if card is None and isinstance(card_index, int):
        hand = list(_safe_iterable(getattr(game, "hand", [])))
        if 0 <= card_index < len(hand):
            card = hand[card_index]
    if card is not None:
        summary["card"] = _card_summary(card)

    potion = getattr(action, "potion", None)
    potion_index = getattr(action, "potion_index", None)
    resolved_potion_index = _resolve_potion_index(game, potion, potion_index)
    if resolved_potion_index is not None:
        summary["potion_index"] = resolved_potion_index
        potion_index = resolved_potion_index
    elif hasattr(action, "potion_index"):
        summary["potion_index"] = _json_scalar(potion_index)

    if potion is None and isinstance(potion_index, int):
        potions = _game_potions(game)
        if 0 <= potion_index < len(potions):
            potion = potions[potion_index]
    if potion is not None:
        summary["potion"] = _potion_summary(potion)

    node = getattr(action, "node", None)
    if node is not None:
        summary["node"] = _node_summary(node)
        next_nodes = list(_safe_iterable(getattr(getattr(game, "screen", None), "next_nodes", [])))
        try:
            summary["choice_index"] = next_nodes.index(node)
        except ValueError:
            pass

    card_to_purge = getattr(action, "card_to_purge", None)
    if card_to_purge is not None:
        summary["card_to_purge"] = _card_summary(card_to_purge)

    return summary


def _resolve_potion_index(game, potion, potion_index) -> Optional[int]:
    if isinstance(potion_index, int) and potion_index >= 0:
        return potion_index
    if potion is None:
        return None
    potions = _game_potions(game)
    try:
        return potions.index(potion)
    except Exception:
        return None


def _game_potions(game):
    raw_potions = getattr(game, "potions", None)
    if raw_potions is not None:
        return list(_safe_iterable(raw_potions))
    get_real_potions = getattr(game, "get_real_potions", None)
    if callable(get_real_potions):
        return list(_safe_iterable(get_real_potions()))
    return []


def _safe_iterable(value):
    return value if isinstance(value, (list, tuple)) else []


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_bool(value):
    return None if value is None else bool(value)


def _json_scalar(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _to_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        try:
            return int(float(value))
        except (TypeError, ValueError, OverflowError):
            return default
