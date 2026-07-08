#!/usr/bin/env python3
"""Offline Bottled policy oracle adapter.

This module reads a local bottled_ai checkout as an offline reference. It never
launches gameplay and does not modify the checkout.
"""

from __future__ import annotations

import importlib
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_BOTTLED_REPO = Path(r"C:\Users\20571\Documents\bottled_ai")
BOTTLED_REPO_ENV = "BOTTLED_AI_PATH"


@dataclass(frozen=True)
class BottledOracleResult:
    label: str
    confidence: str
    reason: str
    status: str = "ok"
    raw: Dict[str, Any] = field(default_factory=dict)
    source: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)


def resolve_bottled_repo_path(explicit: Optional[Path | str] = None) -> Path:
    if explicit:
        return Path(explicit)
    env_path = os.environ.get(BOTTLED_REPO_ENV)
    if env_path:
        return Path(env_path)
    return DEFAULT_BOTTLED_REPO


class BottledPolicyOracle:
    def __init__(self, bottled_repo_path: Optional[Path | str] = None):
        self.repo_path = resolve_bottled_repo_path(bottled_repo_path)

    def evaluate(self, sample: Any) -> BottledOracleResult:
        source = self.source_metadata()
        if not self.repo_path.exists():
            return BottledOracleResult(
                label="unknown",
                confidence="low",
                reason="Bottled checkout is missing; native oracle unavailable.",
                status="unsupported",
                source=source,
                limitations=[f"missing Bottled checkout: {self.repo_path}"],
            )
        if not (self.repo_path / "rs").exists():
            return BottledOracleResult(
                label="unknown",
                confidence="low",
                reason="Bottled checkout does not contain the expected rs package.",
                status="unsupported",
                source=source,
                limitations=[f"incompatible Bottled checkout: {self.repo_path}"],
            )

        category = str(getattr(sample, "category", "") or "")
        if category == "card_reward":
            return self._evaluate_card_reward(sample, source)
        if category == "shop":
            return self._evaluate_shop(sample, source)
        if category == "event":
            return self._evaluate_event(sample, source)
        if category == "route":
            return self._evaluate_route(sample, source)
        if category == "combat":
            return BottledOracleResult(
                label="unknown",
                confidence="low",
                reason="Combat Bottled oracle is feasibility-only for this change.",
                status="unsupported",
                source=source,
                limitations=["combat feasibility only; current combat policy is not replaced"],
            )
        return BottledOracleResult(
            label="unknown",
            confidence="low",
            reason=f"Unsupported Bottled oracle category: {category or 'unknown'}.",
            status="unsupported",
            source=source,
            limitations=[f"unsupported category: {category or 'unknown'}"],
        )

    def source_metadata(self) -> Dict[str, Any]:
        return {
            "mode": "native_bottled",
            "strategy": "REQUESTED_STRIKE",
            "path": str(self.repo_path),
            "commit": _git_output(self.repo_path, ["rev-parse", "--short", "HEAD"]),
            "dirty": bool(_git_output(self.repo_path, ["status", "--short"])),
        }

    def _evaluate_card_reward(self, sample: Any, source: Dict[str, Any]) -> BottledOracleResult:
        ctx = _context(sample)
        offered = [str(card) for card in _as_list(ctx.get("offered"))]
        if not offered:
            return _result(
                "skip",
                "low",
                "No offered cards are available for Bottled card-reward evaluation.",
                source,
                raw={"category": "card_reward"},
            )

        try:
            config = self._import("rs.ai.requested_strike.config")
        except Exception as exc:
            return _error_result("card_reward", exc, source)

        desired = dict(getattr(config, "DESIRED_CARDS_FOR_DECK", {}) or {})
        desired_by_normalized = {_normalize_name(key): value for key, value in desired.items()}
        desired_by_compact = {_compact_key(key): value for key, value in desired.items()}
        deck_counts = _deck_counts(_as_list(ctx.get("deck")))

        for card in offered:
            normalized = _normalize_name(card)
            desired_limit = desired_by_normalized.get(normalized)
            if desired_limit is None:
                desired_limit = desired_by_compact.get(_compact_key(card))
            if desired_limit is None:
                continue
            if deck_counts.get(normalized, 0) < int(desired_limit):
                return _result(
                    card,
                    _complete_confidence(sample, "high", "medium"),
                    f"Native Bottled REQUESTED_STRIKE desired-card config wants up to {desired_limit} copy/copies of {card}.",
                    source,
                    raw={"category": "card_reward", "desired_limit": desired_limit},
                )

        if ctx.get("can_bowl"):
            return _result(
                "bowl",
                "medium",
                "Native Bottled card-reward fallback would use Singing Bowl.",
                source,
                raw={"category": "card_reward"},
            )
        return _result(
            "skip",
            "medium",
            "Native Bottled card-reward fallback skips when no desired card is offered.",
            source,
            raw={"category": "card_reward"},
        )

    def _evaluate_shop(self, sample: Any, source: Dict[str, Any]) -> BottledOracleResult:
        if getattr(sample, "evidence_quality", "") != "complete":
            return _partial_result("shop", "full shop offer and prices are required", source)
        ctx = _context(sample)
        try:
            config = self._import("rs.ai.requested_strike.config")
            shop_module = self._import("rs.ai.requested_strike.handlers.shop_purchase_handler")
        except Exception as exc:
            return _error_result("shop", exc, source)

        handler = shop_module.ShopPurchaseHandler()
        removal_priority = [
            _normalize_name(card)
            for card in getattr(config, "CARD_REMOVAL_PRIORITY_LIST", []) or []
        ]
        relic_priority = [_normalize_name(relic) for relic in getattr(handler, "relics", []) or []]
        card_priority = [_normalize_name(card) for card in getattr(handler, "cards", []) or []]

        gold = _to_int(ctx.get("gold"), 0) or 0
        purge_cost = _to_int(ctx.get("purge_cost"), 10**9) or 10**9
        can_purge = bool(ctx.get("purge_available")) and gold >= purge_cost
        deck = [_normalize_name(card) for card in _as_list(ctx.get("deck"))]
        cards = [card for card in _as_list(ctx.get("cards")) if isinstance(card, dict)]
        relics = [relic for relic in _as_list(ctx.get("relics")) if isinstance(relic, dict)]
        potions = [potion for potion in _as_list(ctx.get("potions")) if isinstance(potion, dict)]

        label = ""
        reason = ""
        if can_purge and any(_is_curse(card) for card in deck):
            label = "purge"
            reason = "Native Bottled shop priority removes curses first."
        if not label:
            for card in cards:
                if _normalize_name(card.get("id") or card.get("name")) == "perfected strike" and gold >= (_to_int(card.get("price"), 10**9) or 10**9):
                    label = str(card.get("name") or card.get("id") or "Perfected Strike")
                    reason = "Native Bottled shop priority buys affordable Perfected Strike before general purge."
                    break
        if not label:
            for relic in relics:
                if _normalize_name(relic.get("name")) == "membership card" and gold >= (_to_int(relic.get("price"), 10**9) or 10**9):
                    label = str(relic.get("name") or "Membership Card")
                    reason = "Native Bottled shop priority buys affordable Membership Card."
                    break
        if not label and can_purge and any(card in set(removal_priority) for card in deck):
            label = "purge"
            reason = "Native Bottled shop priority prefers starter removal before optional purchases."
        if not label:
            for desired in relic_priority:
                for relic in relics:
                    if _normalize_name(relic.get("name")) == desired and gold >= (_to_int(relic.get("price"), 10**9) or 10**9):
                        label = str(relic.get("name") or desired)
                        reason = f"Native Bottled shop relic priority ranks {label} as buyable."
                        break
                if label:
                    break
        if not label:
            deck_set = set(deck)
            for desired in card_priority:
                for card in cards:
                    if _normalize_name(card.get("id") or card.get("name")) == desired and gold >= (_to_int(card.get("price"), 10**9) or 10**9):
                        if desired not in deck_set:
                            label = str(card.get("name") or card.get("id") or desired)
                            reason = f"Native Bottled shop card priority ranks {label} as buyable."
                            break
                if label:
                    break
        if not label:
            label = "leave"
            reason = "Native Bottled shop handler leaves when no priority purchase is affordable."

        command = _shop_command_for_label(label, cards, relics, potions, bool(ctx.get("purge_available")))
        return _result(
            label,
            "high",
            reason,
            source,
            raw={"category": "shop", "command": command},
        )

    def _evaluate_event(self, sample: Any, source: Dict[str, Any]) -> BottledOracleResult:
        if getattr(sample, "evidence_quality", "") != "complete":
            return _partial_result("event", "event option labels and HP are required", source)
        ctx = _context(sample)
        choices = [str(choice) for choice in _as_list(ctx.get("choices"))]
        if not choices:
            return _partial_result("event", "event choices are missing", source)
        if len(choices) == 1:
            return _result(
                f"choose 0: {choices[0]}",
                "low",
                "Native Bottled event handling has only one available option.",
                source,
                raw={"category": "event", "command": "choose 0"},
            )

        try:
            config = self._import("rs.ai.requested_strike.config")
            event_module = self._import("rs.ai.requested_strike.handlers.event_handler")
        except Exception as exc:
            return _error_result("event", exc, source)

        handler = event_module.EventHandler(
            removal_priority_list=getattr(config, "CARD_REMOVAL_PRIORITY_LIST", []) or [],
            cards_desired_for_deck=getattr(config, "DESIRED_CARDS_FOR_DECK", {}) or {},
        )
        state = _BottledStateShim(ctx, sample, event_enum=getattr(event_module, "Event", None))
        command = handler.find_event_choice(state)
        if not command:
            return BottledOracleResult(
                label="unknown",
                confidence="low",
                reason="Native Bottled event handler did not produce a choice for this event.",
                status="unsupported",
                source=source,
                raw={"category": "event"},
                limitations=["event handler returned no choice"],
            )
        label = _event_label_from_command(str(command), choices)
        return _result(
            label,
            "high",
            "Native Bottled REQUESTED_STRIKE event handler selected this option.",
            source,
            raw={"category": "event", "command": str(command)},
        )

    def _evaluate_route(self, sample: Any, source: Dict[str, Any]) -> BottledOracleResult:
        ctx = _context(sample)
        paths = [path for path in _as_list(ctx.get("paths")) if isinstance(path, dict)]
        if not paths:
            return _partial_result("route", "candidate route paths are missing", source)
        try:
            map_module = self._import("rs.common.handlers.common_map_handler")
        except Exception as exc:
            return _error_result("route", exc, source)

        config = getattr(map_module, "default_config", None)
        if config is None:
            return BottledOracleResult(
                label="unknown",
                confidence="low",
                reason="Native Bottled route config is unavailable.",
                status="unsupported",
                source=source,
                limitations=["missing common_map_handler.default_config"],
            )

        state = _BottledStateShim(ctx, sample, event_enum=None)
        scored = []
        for path in paths:
            score, detail = _score_route_path(path, state, config)
            scored.append((score, path, detail))
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_path, detail = scored[0]
        return _result(
            f"choice {best_path.get('choice')}",
            "high",
            f"Native Bottled route reward-to-survivability score {best_score:.2f}: {detail}",
            source,
            raw={"category": "route", "score": best_score, "path": dict(best_path)},
        )

    def _event_enum(self) -> Any:
        try:
            return self._import("rs.game.event").Event
        except Exception:
            return None

    def _import(self, module_name: str):
        with _bottled_import_path(self.repo_path):
            return importlib.import_module(module_name)


class _DeckShim:
    def __init__(self, cards: Iterable[Any]):
        self.names = [_normalize_name(card) for card in cards]

    def contains_cards(self, cards: Iterable[Any]) -> bool:
        wanted = {_normalize_name(card) for card in cards}
        return any(name in wanted for name in self.names)

    def contains_card_amount(self, card_name: str) -> int:
        target = _normalize_name(card_name)
        return sum(1 for name in self.names if name == target)

    def contains_curses_we_can_remove(self) -> bool:
        return any(_is_curse(name) for name in self.names)


class _BottledStateShim:
    def __init__(self, ctx: Dict[str, Any], sample: Any, event_enum: Any = None):
        self.ctx = ctx
        self.sample = sample
        self.event_enum = event_enum
        self.deck = _DeckShim(_as_list(ctx.get("deck")))

    def game_state(self) -> Dict[str, Any]:
        choices = [str(choice).lower() for choice in _as_list(self.ctx.get("choices"))]
        return {
            "act": _to_int(getattr(self.sample, "act", None), _to_int(self.ctx.get("act"), 1) or 1) or 1,
            "floor": _to_int(getattr(self.sample, "floor", None), _to_int(self.ctx.get("floor"), 0) or 0) or 0,
            "gold": _to_int(self.ctx.get("gold"), 0) or 0,
            "current_hp": _to_int(self.ctx.get("current_hp"), 80) or 80,
            "max_hp": _to_int(self.ctx.get("max_hp"), 80) or 80,
            "relics": self._relics(),
            "potions": [],
            "deck": [{"name": str(card)} for card in _as_list(self.ctx.get("deck"))],
            "choice_list": choices,
            "screen_state": {
                "event_name": str(self.ctx.get("event_name") or ""),
                "options": [{"label": choice, "disabled": False, "text": choice} for choice in choices],
            },
            "screen_type": str(self.ctx.get("screen_type") or ""),
        }

    def get_player_health_percentage(self) -> float:
        game_state = self.game_state()
        maximum = game_state["max_hp"]
        return game_state["current_hp"] / maximum if maximum else 1.0

    def get_event(self):
        event_name = str(self.ctx.get("event_name") or "")
        if self.event_enum is None:
            return event_name
        try:
            return self.event_enum(event_name)
        except Exception:
            return event_name

    def has_relic(self, relic_name: str) -> bool:
        target = _normalize_name(relic_name)
        return any(_normalize_name(relic.get("name")) == target for relic in self._relics())

    def get_relic_counter(self, relic_name: str) -> int:
        target = _normalize_name(relic_name)
        for relic in self._relics():
            if _normalize_name(relic.get("name")) == target:
                return _to_int(relic.get("counter"), 0) or 0
        return 0

    def get_choice_list(self) -> List[str]:
        return list(self.game_state()["choice_list"])

    def floor(self) -> int:
        return self.game_state()["floor"]

    def get_deck_card_list_by_id(self) -> Dict[str, int]:
        return _deck_counts(_as_list(self.ctx.get("deck")))

    def _relics(self) -> List[Dict[str, Any]]:
        relics = []
        for relic in _as_list(self.ctx.get("relics")):
            if isinstance(relic, dict):
                relics.append(dict(relic))
            else:
                relics.append({"name": str(relic), "counter": 0})
        return relics


@contextmanager
def _bottled_import_path(path: Path):
    path_text = str(path)
    previous = list(sys.path)
    _purge_rs_modules()
    sys.path.insert(0, path_text)
    importlib.invalidate_caches()
    try:
        yield
    finally:
        sys.path[:] = previous


def _purge_rs_modules() -> None:
    for name in list(sys.modules):
        if name == "rs" or name.startswith("rs."):
            sys.modules.pop(name, None)


def _git_output(path: Path, args: List[str]) -> Optional[str]:
    if not path.exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    return text or None


def _context(sample: Any) -> Dict[str, Any]:
    ctx = getattr(sample, "context", {}) or {}
    return ctx if isinstance(ctx, dict) else {}


def _result(
    label: str,
    confidence: str,
    reason: str,
    source: Dict[str, Any],
    raw: Optional[Dict[str, Any]] = None,
) -> BottledOracleResult:
    return BottledOracleResult(
        label=label,
        confidence=confidence,
        reason=reason,
        status="ok",
        raw=dict(raw or {}),
        source=dict(source),
    )


def _partial_result(category: str, limitation: str, source: Dict[str, Any]) -> BottledOracleResult:
    return BottledOracleResult(
        label="unknown",
        confidence="low",
        reason=f"Partial {category} evidence: {limitation}.",
        status="partial",
        source=source,
        raw={"category": category},
        limitations=[limitation],
    )


def _error_result(category: str, exc: Exception, source: Dict[str, Any]) -> BottledOracleResult:
    return BottledOracleResult(
        label="unknown",
        confidence="low",
        reason=f"Native Bottled {category} oracle failed: {exc}",
        status="error",
        source=source,
        raw={"category": category},
        limitations=[str(exc)],
    )


def _complete_confidence(sample: Any, complete_value: str, partial_value: str) -> str:
    return complete_value if getattr(sample, "evidence_quality", "") == "complete" else partial_value


def _shop_command_for_label(
    label: str,
    cards: List[Dict[str, Any]],
    relics: List[Dict[str, Any]],
    potions: List[Dict[str, Any]],
    purge_available: bool,
) -> str:
    normalized = _normalize_name(label)
    if normalized == "leave":
        return "return"
    choice_list = []
    choice_list.extend(str(card.get("name") or card.get("id") or "").lower() for card in cards)
    choice_list.extend(str(relic.get("name") or "").lower() for relic in relics)
    choice_list.extend(str(potion.get("name") or "").lower() for potion in potions)
    if purge_available:
        choice_list.append("purge")
    for index, choice in enumerate(choice_list):
        if _normalize_name(choice) == normalized:
            return f"choose {index}"
    if normalized == "purge":
        return "choose purge"
    return "choose"


def _event_label_from_command(command: str, choices: List[str]) -> str:
    normalized = command.strip().lower()
    match = re.match(r"choose\s+(\d+)", normalized)
    if match:
        index = int(match.group(1))
        return f"choose {index}: {_choice_label(choices, index)}"
    if normalized.startswith("choose "):
        target = normalized.split(" ", 1)[1].strip()
        for index, choice in enumerate(choices):
            if target == str(choice).lower() or target in str(choice).lower():
                return f"choose {index}: {choice}"
    return command


def _choice_label(choices: List[str], index: int) -> str:
    if 0 <= index < len(choices):
        return str(choices[index])
    return str(index)


def _score_route_path(path: Dict[str, Any], state: _BottledStateShim, config: Any) -> tuple[float, str]:
    nodes = [str(node) for node in _as_list(path.get("nodes"))]
    game_state = state.game_state()
    act = max(1, _to_int(game_state.get("act"), 1) or 1)
    max_hp = max(1.0, float(_to_int(game_state.get("max_hp"), 80) or 80))
    hp = float(_to_int(game_state.get("current_hp"), int(max_hp)) or int(max_hp))
    gold = float(_to_int(game_state.get("gold"), 0) or 0)
    reward = 0.0
    survivability = 1.0

    for node in nodes:
        symbol = node.upper()
        if symbol == "M":
            reward += float(getattr(config, "hallway_fight_base_reward", 1))
            if state.has_relic("Prayer Wheel"):
                reward += float(getattr(config, "hallway_fight_prayer_wheel", 0))
            if state.has_relic("Question Card"):
                reward += float(getattr(config, "hallway_question_card_reward", 0))
            gold += float(getattr(config, "hallway_fight_gold", 15))
            hp -= float(config.hallway_fight_health_loss(state)) if hasattr(config, "hallway_fight_health_loss") else act * 5
            hp = _apply_post_combat_healing(hp, max_hp, state)
        elif symbol == "E":
            reward += float(getattr(config, "elite_base_reward", 1)) + float(getattr(config, "relic_reward", 1.5))
            if state.has_relic("Question Card"):
                reward += float(getattr(config, "elite_question_card_reward", 0))
            if state.has_relic("Black Star"):
                reward += float(getattr(config, "relic_reward", 1.5))
            gold += 30
            hp -= float(config.elite_fight_health_loss(state)) if hasattr(config, "elite_fight_health_loss") else (act + 1) * 15
            hp = _apply_post_combat_healing(hp, max_hp, state)
        elif symbol == "T":
            reward += float(getattr(config, "relic_reward", 1.5))
            if state.has_relic("Cursed Key"):
                reward -= float(getattr(config, "curse_reward_loss", 1.5))
        elif symbol == "?":
            reward += float(config.event_value_reward(state)) if hasattr(config, "event_value_reward") else (1 if act == 1 else 1.5)
        elif symbol == "R":
            if hp / max_hp >= 0.6 and not state.has_relic("Fusion Hammer"):
                reward += float(getattr(config, "upgrade_reward", 1.1))
            else:
                hp += max_hp * 0.3
        elif symbol == "$":
            if state.has_relic("Membership Card"):
                gold_to_spend = min(gold, 300)
                gold -= gold_to_spend
            else:
                gold_to_spend = min(gold, 200) * 2
                gold -= gold_to_spend / 2
            reward += float(config.gold_at_shop_reward(state, gold_to_spend)) if hasattr(config, "gold_at_shop_reward") else gold_to_spend / 100

        barrier = max_hp / 4
        if hp < barrier:
            survivability *= max((hp + barrier * 2) / (barrier * 3), 0)
        hp = min(max(hp, 0), max_hp)

    if act != 3:
        reward += float(config.gold_after_boss_reward(state)) if hasattr(config, "gold_after_boss_reward") else float(_to_int(game_state.get("gold"), 0) or 0) / 200
    if survivability != 0 and hasattr(config, "survivability_reward_calculation"):
        score = float(config.survivability_reward_calculation(reward, survivability))
    else:
        score = reward + (survivability - 1) * 15
    return score, f"{path.get('label') or nodes}: reward={reward:.2f}, survivability={survivability:.2f}"


def _apply_post_combat_healing(hp: float, max_hp: float, state: _BottledStateShim) -> float:
    if state.has_relic("Meat on the Bone") and hp / max_hp < 0.5:
        hp += 12
    if state.has_relic("Blood Vial"):
        hp += 2
    if state.has_relic("Black Blood"):
        hp += 12
    if state.has_relic("Burning Blood"):
        hp += 6
    return hp


def _deck_counts(cards: Iterable[Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for card in cards:
        key = _normalize_name(card)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _to_int(value: Any, default: Optional[int] = 0) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_name(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("name") or value.get("id") or ""
    text = str(value or "").strip()
    text = re.sub(r"\+\d*$", "", text)
    text = text.replace("_R", "").replace("_G", "").replace("_B", "").replace("_P", "")
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _compact_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _is_curse(name: str) -> bool:
    normalized = _normalize_name(name)
    return normalized in {
        "ascendersbane",
        "ascender's bane",
        "curse of the bell",
        "clumsy",
        "decay",
        "doubt",
        "injury",
        "normality",
        "pain",
        "parasite",
        "regret",
        "shame",
        "writhe",
    } or "curse" in normalized
