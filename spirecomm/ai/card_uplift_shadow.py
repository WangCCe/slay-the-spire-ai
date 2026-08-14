"""Opt-in live shadow scoring for the frozen card-uplift candidate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any


CONFIG_ENV = "STS_CARD_UPLIFT_SHADOW_CONFIG"
CANARY_CONFIG_ENV = "STS_CARD_UPLIFT_CANARY_CONFIG"
EVALUATION_CONFIG_ENV = "STS_CARD_UPLIFT_EVALUATION_CONFIG"
CONFIG_SCHEMA_VERSION = "noncombat-card-uplift-live-shadow-config-v1"
CANARY_CONFIG_SCHEMA_VERSION = "noncombat-card-uplift-live-canary-config-v1"
EVALUATION_CONFIG_SCHEMA_VERSION = "noncombat-card-uplift-live-evaluation-config-v1"
ROW_SCHEMA_VERSION = "noncombat-card-uplift-live-shadow-row-v1"
CANARY_ROW_SCHEMA_VERSION = "noncombat-card-uplift-live-canary-row-v1"
EVALUATION_ROW_SCHEMA_VERSION = "noncombat-card-uplift-live-evaluation-row-v1"
PROJECTION_VERSION = "live-best-effort-v1"
CANARY_TORCH_THREAD_LIMIT = 2
SOURCE_PATHS = (
    "analysis_scripts/noncombat_card_acceptance_empirical_successor_runtime.py",
    "analysis_scripts/noncombat_card_acceptance_objective.py",
    "analysis_scripts/noncombat_card_acceptance_policy.py",
    "analysis_scripts/noncombat_card_counterfactual_ranking_training.py",
    "analysis_scripts/noncombat_card_counterfactual_uplift_residual_crossfit.py",
    "analysis_scripts/noncombat_formal_reward_contract.py",
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_rl_experiment.py",
    "analysis_scripts/noncombat_state_conditioned_policy_input.py",
    "analysis_scripts/noncombat_state_conditioned_ranker.py",
    "main.py",
    "scripts/run_training_batch.py",
    "spirecomm/ai/card_uplift_shadow.py",
    "spirecomm/communication/action.py",
    "spirecomm/spire/card.py",
    "spirecomm/spire/game.py",
    "spirecomm/spire/map.py",
    "spirecomm/spire/potion.py",
    "spirecomm/spire/relic.py",
    "spirecomm/spire/screen.py",
)
AUTHORITY = {
    name: False
    for name in (
        "action_selection",
        "causal_claim",
        "exploration",
        "formal_rl",
        "model_fitting",
        "policy_quality",
        "promotion",
        "qualification",
        "training",
    )
}
CANARY_AUTHORITY = {**AUTHORITY, "action_selection": True}
KNOWN_PROJECTION_SHIFTS = (
    "baseline_history_unavailable",
    "burning_elite_metadata_estimated",
    "current_map_node_tracked_from_live_actions",
    "encounter_enum_best_effort",
    "native_enum_ids_derived_from_live_names",
    "reward_index_assumed_zero",
)


logger = logging.getLogger(__name__)
_UPGRADE_SUFFIX_RE = re.compile(r"\+\d*$")


class CardUpliftShadowError(ValueError):
    """Raised when explicitly configured shadow mode is invalid."""


def _configure_canary_torch_threads() -> int:
    """Bound small-model inference threads before the canary starts scoring."""
    import torch

    current = int(torch.get_num_threads())
    if current > CANARY_TORCH_THREAD_LIMIT:
        torch.set_num_threads(CANARY_TORCH_THREAD_LIMIT)
    active = int(torch.get_num_threads())
    if active > CANARY_TORCH_THREAD_LIMIT:
        raise CardUpliftShadowError("canary torch thread limit was not applied")
    return active


def _canonical_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise CardUpliftShadowError("shadow artifact is not canonical") from exc


def _read_canonical(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
        value = json.loads(payload.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CardUpliftShadowError(f"invalid shadow JSON: {source}") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise CardUpliftShadowError(f"noncanonical shadow JSON: {source}")
    return value


def _binding(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
    except OSError as exc:
        raise CardUpliftShadowError(f"shadow input is unavailable: {source}") from exc
    return {
        "path": source.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _source_bindings(repo_root: Path, source_commit: str) -> dict[str, Any]:
    bindings: dict[str, Any] = {}
    for relative in SOURCE_PATHS:
        actual = _binding(repo_root / relative)
        try:
            committed = subprocess.run(
                ["git", "show", f"{source_commit}:{relative}"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise CardUpliftShadowError(
                f"shadow source path unavailable at commit: {relative}"
            ) from exc
        if hashlib.sha256(committed).hexdigest() != actual["sha256"]:
            raise CardUpliftShadowError(f"shadow source bytes differ: {relative}")
        bindings[relative] = actual
    return bindings


def build_configuration(
    *,
    repo_root: Path | str,
    source_commit: str,
    entry_checkpoint: Path | str,
    residual_model: Path | str,
    output_path: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    try:
        commit_type = subprocess.run(
            ["git", "cat-file", "-t", source_commit],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CardUpliftShadowError("shadow source commit is unavailable") from exc
    if commit_type != "commit":
        raise CardUpliftShadowError("shadow source commit is unavailable")
    return validate_configuration(
        {
            "authority": copy.deepcopy(AUTHORITY),
            "entry_checkpoint": _binding(entry_checkpoint),
            "maximum_games": 5,
            "output_path": Path(output_path).resolve().as_posix(),
            "projection_version": PROJECTION_VERSION,
            "residual_model": _binding(residual_model),
            "schema_version": CONFIG_SCHEMA_VERSION,
            "source": {
                "bindings": _source_bindings(root, source_commit),
                "commit": source_commit,
                "repo_root": root.as_posix(),
            },
        }
    )


def _build_intervention_configuration(
    *,
    repo_root: Path | str,
    source_commit: str,
    entry_checkpoint: Path | str,
    residual_model: Path | str,
    output_path: Path | str,
    maximum_games: int,
    label: str,
    schema_version: str,
    validator: Callable[[Mapping[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    try:
        commit_type = subprocess.run(
            ["git", "cat-file", "-t", source_commit],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CardUpliftShadowError(
            f"{label} source commit is unavailable"
        ) from exc
    if commit_type != "commit":
        raise CardUpliftShadowError(f"{label} source commit is unavailable")
    return validator(
        {
            "authority": copy.deepcopy(CANARY_AUTHORITY),
            "entry_checkpoint": _binding(entry_checkpoint),
            "maximum_games": maximum_games,
            "output_path": Path(output_path).resolve().as_posix(),
            "projection_version": PROJECTION_VERSION,
            "residual_model": _binding(residual_model),
            "schema_version": schema_version,
            "source": {
                "bindings": _source_bindings(root, source_commit),
                "commit": source_commit,
                "repo_root": root.as_posix(),
            },
        }
    )


def build_canary_configuration(
    *,
    repo_root: Path | str,
    source_commit: str,
    entry_checkpoint: Path | str,
    residual_model: Path | str,
    output_path: Path | str,
) -> dict[str, Any]:
    return _build_intervention_configuration(
        repo_root=repo_root,
        source_commit=source_commit,
        entry_checkpoint=entry_checkpoint,
        residual_model=residual_model,
        output_path=output_path,
        maximum_games=3,
        label="canary",
        schema_version=CANARY_CONFIG_SCHEMA_VERSION,
        validator=validate_canary_configuration,
    )


def build_evaluation_configuration(
    *,
    repo_root: Path | str,
    source_commit: str,
    entry_checkpoint: Path | str,
    residual_model: Path | str,
    output_path: Path | str,
    maximum_games: int,
) -> dict[str, Any]:
    return _build_intervention_configuration(
        repo_root=repo_root,
        source_commit=source_commit,
        entry_checkpoint=entry_checkpoint,
        residual_model=residual_model,
        output_path=output_path,
        maximum_games=maximum_games,
        label="evaluation",
        schema_version=EVALUATION_CONFIG_SCHEMA_VERSION,
        validator=validate_evaluation_configuration,
    )


def validate_configuration(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CardUpliftShadowError("shadow config must be an object")
    config = copy.deepcopy(dict(value))
    if set(config) != {
        "authority",
        "entry_checkpoint",
        "maximum_games",
        "output_path",
        "projection_version",
        "residual_model",
        "schema_version",
        "source",
    } or config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise CardUpliftShadowError("shadow config fields differ")
    if config["authority"] != AUTHORITY:
        raise CardUpliftShadowError("shadow authority differs")
    if config["projection_version"] != PROJECTION_VERSION:
        raise CardUpliftShadowError("shadow projection version differs")
    if config["maximum_games"] != 5:
        raise CardUpliftShadowError("shadow game ceiling differs")
    for name in ("entry_checkpoint", "residual_model"):
        binding = config.get(name)
        if not isinstance(binding, dict) or set(binding) != {
            "path",
            "sha256",
            "size_bytes",
        }:
            raise CardUpliftShadowError(f"shadow {name} binding differs")
    source = config.get("source")
    if (
        not isinstance(source, dict)
        or set(source) != {"bindings", "commit", "repo_root"}
        or set(source.get("bindings", {})) != set(SOURCE_PATHS)
        or not isinstance(source.get("commit"), str)
        or len(source["commit"]) != 40
    ):
        raise CardUpliftShadowError("shadow source differs")
    if not isinstance(config.get("output_path"), str) or not config["output_path"]:
        raise CardUpliftShadowError("shadow output path differs")
    output = Path(config["output_path"]).resolve()
    checkpoint_root = Path(source["repo_root"]).resolve() / "checkpoints"
    if output == checkpoint_root or checkpoint_root in output.parents:
        raise CardUpliftShadowError("shadow output overlaps checkpoints")
    return config


def _validate_intervention_configuration(
    value: Mapping[str, Any],
    *,
    label: str,
    schema_version: str,
    valid_game_ceiling: Callable[[Any], bool],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CardUpliftShadowError(f"{label} config must be an object")
    config = copy.deepcopy(dict(value))
    if set(config) != {
        "authority",
        "entry_checkpoint",
        "maximum_games",
        "output_path",
        "projection_version",
        "residual_model",
        "schema_version",
        "source",
    } or config.get("schema_version") != schema_version:
        raise CardUpliftShadowError(f"{label} config fields differ")
    if config["authority"] != CANARY_AUTHORITY:
        raise CardUpliftShadowError(f"{label} authority differs")
    if config["projection_version"] != PROJECTION_VERSION:
        raise CardUpliftShadowError(f"{label} projection version differs")
    if not valid_game_ceiling(config["maximum_games"]):
        raise CardUpliftShadowError(f"{label} game ceiling differs")
    for name in ("entry_checkpoint", "residual_model"):
        binding = config.get(name)
        if not isinstance(binding, dict) or set(binding) != {
            "path",
            "sha256",
            "size_bytes",
        }:
            raise CardUpliftShadowError(f"{label} {name} binding differs")
    source = config.get("source")
    if (
        not isinstance(source, dict)
        or set(source) != {"bindings", "commit", "repo_root"}
        or set(source.get("bindings", {})) != set(SOURCE_PATHS)
        or not isinstance(source.get("commit"), str)
        or len(source["commit"]) != 40
    ):
        raise CardUpliftShadowError(f"{label} source differs")
    if not isinstance(config.get("output_path"), str) or not config["output_path"]:
        raise CardUpliftShadowError(f"{label} output path differs")
    output = Path(config["output_path"]).resolve()
    checkpoint_root = Path(source["repo_root"]).resolve() / "checkpoints"
    if output == checkpoint_root or checkpoint_root in output.parents:
        raise CardUpliftShadowError(f"{label} output overlaps checkpoints")
    return config


def validate_canary_configuration(value: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_intervention_configuration(
        value,
        label="canary",
        schema_version=CANARY_CONFIG_SCHEMA_VERSION,
        valid_game_ceiling=lambda maximum: maximum == 3,
    )


def validate_evaluation_configuration(value: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_intervention_configuration(
        value,
        label="evaluation",
        schema_version=EVALUATION_CONFIG_SCHEMA_VERSION,
        valid_game_ceiling=lambda maximum: (
            not isinstance(maximum, bool)
            and isinstance(maximum, int)
            and 1 <= maximum <= 25
        ),
    )


def _verify_configuration(config: Mapping[str, Any]) -> None:
    root = Path(config["source"]["repo_root"]).resolve()
    try:
        subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                config["source"]["commit"],
                "HEAD",
            ],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CardUpliftShadowError("shadow source commit is not an ancestor") from exc
    if _source_bindings(root, config["source"]["commit"]) != config["source"][
        "bindings"
    ]:
        raise CardUpliftShadowError("shadow source binding differs")
    for name in ("entry_checkpoint", "residual_model"):
        if _binding(config[name]["path"]) != config[name]:
            raise CardUpliftShadowError(f"shadow {name} bytes differ")
    output = Path(config["output_path"]).resolve()
    if output.exists():
        raise CardUpliftShadowError("shadow output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)


def _base_name(value: object) -> str:
    return _UPGRADE_SUFFIX_RE.sub("", str(value or "")).strip()


def _enum_id(value: object) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", _base_name(value)).strip("_")
    return normalized.upper() or "INVALID"


def _int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _card_json(card: Any, slot: int) -> dict[str, Any]:
    name = _base_name(getattr(card, "name", ""))
    upgrades = max(0, _int(getattr(card, "upgrades", 0)))
    return {
        "id": _enum_id(name or getattr(card, "card_id", "")),
        "misc": _int(getattr(card, "misc", 0)),
        "name": name,
        "slot": slot,
        "upgrade_count": upgrades,
        "upgraded": upgrades > 0,
    }


def _relic_json(relic: Any) -> dict[str, Any]:
    name = _base_name(getattr(relic, "name", ""))
    return {
        "data": _int(getattr(relic, "counter", 0)),
        "id": _enum_id(name or getattr(relic, "relic_id", "")),
        "name": name,
    }


def _potion_json(potion: Any, slot: int) -> dict[str, Any]:
    name = _base_name(getattr(potion, "name", ""))
    potion_id = str(getattr(potion, "potion_id", "") or "")
    if potion_id == "Potion Slot" or name == "Potion Slot":
        identifier = "EMPTY_POTION_SLOT"
        name = identifier
    else:
        identifier = _enum_id(name or potion_id)
    return {"id": identifier, "name": name, "slot": slot}


_ROOM_BY_SYMBOL = {
    "?": "EVENT",
    "$": "SHOP",
    "B": "BOSS",
    "E": "ELITE",
    "M": "MONSTER",
    "R": "REST",
    "T": "TREASURE",
}


def _room_name(value: object, symbol: str | None) -> str:
    if symbol in _ROOM_BY_SYMBOL:
        return _ROOM_BY_SYMBOL[symbol]
    text = str(value or "").upper()
    for needle, result in (
        ("BOSS", "BOSS"),
        ("ELITE", "ELITE"),
        ("MONSTER", "MONSTER"),
        ("SHOP", "SHOP"),
        ("REST", "REST"),
        ("TREASURE", "TREASURE"),
        ("EVENT", "EVENT"),
    ):
        if needle in text:
            return result
    return "NONE"


def _map_json(game_map: Any) -> dict[str, Any] | None:
    nodes_by_y = getattr(game_map, "nodes", None)
    if not isinstance(nodes_by_y, dict):
        return None
    nodes = []
    for y in sorted(nodes_by_y):
        row = nodes_by_y[y]
        if not isinstance(row, dict):
            continue
        for x in sorted(row):
            node = row[x]
            symbol = str(getattr(node, "symbol", "") or "")
            nodes.append(
                {
                    "edges": [
                        {
                            "x": _int(getattr(child, "x", -1), -1),
                            "y": _int(getattr(child, "y", -1), -1),
                        }
                        for child in (getattr(node, "children", None) or [])
                    ],
                    "room": _room_name(getattr(node, "room", None), symbol),
                    "symbol": symbol,
                    "x": _int(getattr(node, "x", x), x),
                    "y": _int(getattr(node, "y", y), y),
                }
            )
    return {
        "burning_elite": {"buff": 0, "x": -1, "y": -1},
        "nodes": nodes,
    }


def _screen_name(value: object) -> str:
    return str(getattr(value, "name", value or ""))


def _category(game: Any) -> str | None:
    name = _screen_name(getattr(game, "screen_type", None))
    return {
        "CARD_REWARD": "card_reward",
        "EVENT": "event",
        "MAP": "route",
        "SHOP_SCREEN": "shop",
    }.get(name)


def _offer_hash(cards: Sequence[Any]) -> str:
    return hashlib.sha256(
        _canonical_bytes([_card_json(card, index) for index, card in enumerate(cards)])
    ).hexdigest()


def _action_id(action: Any, candidates: Sequence[Mapping[str, Any]]) -> str:
    class_name = type(action).__name__
    if class_name == "CancelAction":
        matches = [row["action_id"] for row in candidates if row["kind"] == "skip"]
    elif class_name == "CardRewardAction" and getattr(action, "name", None) != "bowl":
        target = _base_name(getattr(action, "name", "")).casefold()
        matches = [
            row["action_id"]
            for row in candidates
            if row["kind"] == "take"
            and _base_name(row["label"]).casefold() == target
        ]
    else:
        matches = []
    if len(matches) != 1:
        raise CardUpliftShadowError("Current card action mapping is not unique")
    return str(matches[0])


def _live_action_for_id(
    game: Any,
    candidates: Sequence[Mapping[str, Any]],
    action_id: str,
) -> Any:
    matches = [candidate for candidate in candidates if candidate["action_id"] == action_id]
    if len(matches) != 1:
        raise CardUpliftShadowError("candidate card action mapping is not unique")
    candidate = matches[0]
    if candidate["kind"] == "skip":
        from spirecomm.communication.action import CancelAction

        return CancelAction()
    if candidate["kind"] != "take":
        raise CardUpliftShadowError("candidate card action kind is unsupported")
    slot = candidate.get("raw", {}).get("slot")
    cards = list(getattr(getattr(game, "screen", None), "cards", None) or [])
    if isinstance(slot, bool) or not isinstance(slot, int) or not 0 <= slot < len(cards):
        raise CardUpliftShadowError("candidate card slot is invalid")
    if _base_name(getattr(cards[slot], "name", "")) != _base_name(candidate["label"]):
        raise CardUpliftShadowError("candidate card offer mapping differs")
    from spirecomm.communication.action import CardRewardAction

    return CardRewardAction(cards[slot])


def project_live_card_reward(
    game: Any,
    *,
    decision_count: int,
    current_map_node: tuple[int, int, str] | None,
    encounter: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], tuple[str, ...]]:
    screen = getattr(game, "screen", None)
    cards = list(getattr(screen, "cards", None) or [])
    if bool(getattr(game, "in_combat", False)):
        raise CardUpliftShadowError("generated_combat_card_choice")
    if len(cards) != 3:
        raise CardUpliftShadowError("card_count_not_three")
    if bool(getattr(screen, "can_bowl", False)):
        raise CardUpliftShadowError("singing_bowl_present")
    if not bool(getattr(screen, "can_skip", False)):
        raise CardUpliftShadowError("card_reward_cannot_skip")
    card_values = [_card_json(card, index) for index, card in enumerate(cards)]
    candidates = [
        {
            "action_id": f"card_reward:take:0:{index}:{_enum_id(card['name']).lower()}",
            "available": True,
            "category": "card_reward",
            "kind": "take",
            "label": card["name"],
            "raw": {**card, "reward_index": 0},
        }
        for index, card in enumerate(card_values)
    ]
    candidates.append(
        {
            "action_id": "card_reward:skip:0",
            "available": True,
            "category": "card_reward",
            "kind": "skip",
            "label": "skip",
            "raw": {"reward_index": 0},
        }
    )
    node_x, node_y, node_symbol = current_map_node or (-1, -1, "")
    state = {
        "act": _int(getattr(game, "act", 0)),
        "ascension": _int(getattr(game, "ascension_level", 0)),
        "blue_key": bool(getattr(game, "has_sapphire_key", False)),
        "boss": _enum_id(getattr(game, "act_boss", "INVALID")),
        "cur_hp": _int(getattr(game, "current_hp", 0)),
        "cur_map_node": {"x": node_x, "y": node_y},
        "cur_room": _room_name(getattr(game, "room_type", None), node_symbol),
        "decision_context": {
            "cards": card_values,
            "has_singing_bowl": False,
            "reward_index": 0,
        },
        "deck": [
            _card_json(card, index)
            for index, card in enumerate(getattr(game, "deck", None) or [])
        ],
        "encounter": encounter,
        "floor": _int(getattr(game, "floor", 0)),
        "gold": _int(getattr(game, "gold", 0)),
        "green_key": bool(getattr(game, "has_emerald_key", False)),
        "map": _map_json(getattr(game, "map", None)),
        "max_hp": _int(getattr(game, "max_hp", 0)),
        "outcome": "UNDECIDED",
        "potions": [
            _potion_json(potion, index)
            for index, potion in enumerate(getattr(game, "potions", None) or [])
        ],
        "red_key": bool(getattr(game, "has_ruby_key", False)),
        "relics": [
            _relic_json(relic) for relic in (getattr(game, "relics", None) or [])
        ],
        "screen_state": "REWARDS",
        "seed": str(getattr(game, "seed", 0)),
    }
    snapshot = {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
        "baseline_control": {
            "history": [],
            "policy_id": "sts_lightspeed_simple_agent_target_v1",
        },
        "category": "card_reward",
        "decision_count": decision_count,
        "schema_version": "sts-lightspeed-state-v1",
        "source_type": "sts_lightspeed_simulation",
        "state": state,
        "terminal": False,
    }
    return snapshot, candidates, KNOWN_PROJECTION_SHIFTS


class CardUpliftShadowRuntime:
    def __init__(self, config: Mapping[str, Any]):
        self._initialize(validate_configuration(config), ROW_SCHEMA_VERSION)

    def _initialize(
        self,
        config: Mapping[str, Any],
        row_schema_version: str,
    ) -> None:
        self.config = dict(config)
        _verify_configuration(self.config)
        intervention_schema = row_schema_version in {
            CANARY_ROW_SCHEMA_VERSION,
            EVALUATION_ROW_SCHEMA_VERSION,
        }
        self.torch_threads = (
            _configure_canary_torch_threads() if intervention_schema else None
        )
        from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
        from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as uplift

        entry_bytes = Path(self.config["entry_checkpoint"]["path"]).read_bytes()
        model_bytes = Path(self.config["residual_model"]["path"]).read_bytes()
        self.bootstrap = ranking.restore_entry_bootstrap(entry_bytes)
        self.model, self.residual_configuration = uplift.restore_uplift_model(
            model_bytes
        )
        if self.residual_configuration.as_dict() != {
            "shrinkage": 1,
            "strength": 128,
        }:
            raise CardUpliftShadowError("shadow residual configuration differs")
        self._ranking = ranking
        self._uplift = uplift
        self.output_path = Path(self.config["output_path"]).resolve()
        self.config_sha256 = hashlib.sha256(_canonical_bytes(self.config)).hexdigest()
        self.row_schema_version = row_schema_version
        self.run_key: tuple[str, int] | None = None
        self.run_count = 0
        self.last_floor = -1
        self.disabled = False
        self.decision_count = 0
        self.current_map_node: tuple[int, int, str] | None = None
        self.encounter = "INVALID"
        self.seen: set[str] = set()

    def wrap_state_callback(self, current_callback: Callable[[Any], Any]):
        def wrapped(game: Any) -> Any:
            action = current_callback(game)
            try:
                self.observe(game, action)
            except Exception as exc:
                logger.error("[CARD_UPLIFT_SHADOW] observation failed: %s", exc)
            return action

        return wrapped

    def _reset_if_needed(self, game: Any) -> None:
        key = (
            str(getattr(game, "seed", 0)),
            _int(getattr(game, "ascension_level", 0)),
        )
        floor = _int(getattr(game, "floor", 0))
        if key == self.run_key and floor >= self.last_floor:
            self.last_floor = floor
            return
        self.run_count += 1
        self.disabled = self.disabled or self.run_count > self.config["maximum_games"]
        self.run_key = key
        self.last_floor = floor
        self.decision_count = 0
        self.current_map_node = None
        self.encounter = "INVALID"
        self.seen.clear()

    def _update_context(self, game: Any, action: Any, category: str | None) -> None:
        monsters = getattr(game, "monsters", None) or []
        if bool(getattr(game, "in_combat", False)) and monsters:
            names = sorted(
                _enum_id(
                    getattr(monster, "name", "")
                    or getattr(monster, "monster_id", "")
                )
                for monster in monsters
            )
            self.encounter = "_".join(names) or "INVALID"
        if category == "route":
            node = getattr(action, "node", None)
            if node is not None:
                self.current_map_node = (
                    _int(getattr(node, "x", -1), -1),
                    _int(getattr(node, "y", -1), -1),
                    str(getattr(node, "symbol", "") or ""),
                )

    def _decision_key(self, game: Any, action: Any, category: str) -> str:
        screen = getattr(game, "screen", None)
        if category == "card_reward":
            screen_value = [
                _card_json(card, index)
                for index, card in enumerate(getattr(screen, "cards", None) or [])
            ]
        else:
            screen_value = {
                "action": type(action).__name__,
                "floor": _int(getattr(game, "floor", 0)),
                "screen": _screen_name(getattr(game, "screen_type", None)),
            }
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "action": {
                        "choice_index": getattr(action, "choice_index", None),
                        "name": getattr(action, "name", None),
                        "type": type(action).__name__,
                    },
                    "category": category,
                    "run": self.run_key,
                    "screen": screen_value,
                }
            )
        ).hexdigest()

    def observe(self, game: Any, action: Any) -> None:
        self._process(game, action, allow_substitution=False)

    def _process(self, game: Any, action: Any, *, allow_substitution: bool) -> Any:
        self._reset_if_needed(game)
        if self.disabled:
            return action
        category = _category(game)
        self._update_context(game, action, category)
        if category is None:
            return action
        key = self._decision_key(game, action, category)
        if key in self.seen:
            return action
        self.seen.add(key)
        ordinal = self.decision_count
        self.decision_count += 1
        if category != "card_reward":
            return action
        started = time.perf_counter()
        screen = getattr(game, "screen", None)
        cards = list(getattr(screen, "cards", None) or [])
        base = {
            "action_substituted": False,
            "act": _int(getattr(game, "act", 0)),
            "agreement": None,
            "base_scores": None,
            "candidate_action_ids": None,
            "composed_scores": None,
            "config_sha256": self.config_sha256,
            "current_action_id": None,
            "decision_ordinal": ordinal,
            "error": None,
            "floor": _int(getattr(game, "floor", 0)),
            "ineligibility_reason": None,
            "model_sha256": self.config["residual_model"]["sha256"],
            "offer_sha256": _offer_hash(cards),
            "projection_version": PROJECTION_VERSION,
            "run_key": list(self.run_key or ("0", 0)),
            "schema_version": self.row_schema_version,
            "shadow_action_id": None,
            "source_commit": self.config["source"]["commit"],
            "source_sha256": None,
            "unseen_take_actions": None,
        }
        try:
            snapshot, candidates, shifts = project_live_card_reward(
                game,
                decision_count=ordinal,
                current_map_node=self.current_map_node,
                encounter=self.encounter,
            )
        except CardUpliftShadowError as exc:
            row = {
                **base,
                "error": None,
                "ineligibility_reason": str(exc),
                "known_projection_shifts": list(KNOWN_PROJECTION_SHIFTS),
                "latency_ms": (time.perf_counter() - started) * 1000.0,
                "status": "ineligible",
            }
            self._append(row)
            return action
        selected_action = action
        try:
            current_action_id = _action_id(action, candidates)
            result = self._score(snapshot, candidates)
            if allow_substitution and current_action_id != result["shadow_action_id"]:
                selected_action = _live_action_for_id(
                    game,
                    candidates,
                    str(result["shadow_action_id"]),
                )
            row = {
                **base,
                **result,
                "action_substituted": selected_action is not action,
                "agreement": current_action_id == result["shadow_action_id"],
                "current_action_id": current_action_id,
                "known_projection_shifts": list(shifts),
                "latency_ms": (time.perf_counter() - started) * 1000.0,
                "status": "complete",
            }
        except Exception as exc:
            if allow_substitution:
                self.disabled = True
            row = {
                **base,
                "error": f"{type(exc).__name__}: {exc}",
                "ineligibility_reason": None,
                "known_projection_shifts": list(shifts),
                "latency_ms": (time.perf_counter() - started) * 1000.0,
                "status": "error",
            }
        self._append(row)
        return selected_action

    def _score(
        self,
        snapshot: Mapping[str, Any],
        candidates: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        import torch
        from analysis_scripts.noncombat_state_conditioned_policy_input import (
            PolicyInputError,
            project_state_conditioned_policy_input,
        )

        try:
            policy_input = project_state_conditioned_policy_input(snapshot, candidates)
        except PolicyInputError as exc:
            raise CardUpliftShadowError(str(exc)) from exc
        source_sha256 = hashlib.sha256(
            _canonical_bytes(
                {"candidate_actions": list(candidates), "snapshot": dict(snapshot)}
            )
        ).hexdigest()
        row = self._ranking.CounterfactualRankingRow(
            seed=0,
            decision_index=0,
            source_sha256=source_sha256,
            state_features=policy_input.state_features.detach().clone(),
            candidate_features=policy_input.candidate_features.detach().clone(),
            candidates=tuple(copy.deepcopy(candidates)),
            action_returns=(0.0, 0.0, 0.0, 0.0),
        )
        with torch.inference_mode():
            base_scores = tuple(
                float(value)
                for value in self._ranking._joint_log_probabilities(
                    self.bootstrap, row
                )
                .detach()
                .tolist()
            )
        scores, unseen = self._uplift.compose_scores(
            row,
            base_scores,
            self.model,
            strength=self.residual_configuration.strength,
        )
        maximum = max(scores)
        selected_index = min(
            (index for index, value in enumerate(scores) if value == maximum),
            key=lambda index: str(candidates[index]["action_id"]),
        )
        if any(not math.isfinite(value) for value in (*base_scores, *scores)):
            raise CardUpliftShadowError("shadow score is nonfinite")
        return {
            "base_scores": list(base_scores),
            "candidate_action_ids": [row["action_id"] for row in candidates],
            "composed_scores": list(scores),
            "shadow_action_id": str(candidates[selected_index]["action_id"]),
            "source_sha256": source_sha256,
            "unseen_take_actions": unseen,
        }

    def _append(self, row: Mapping[str, Any]) -> None:
        payload = _canonical_bytes(dict(row))
        with self.output_path.open("ab") as handle:
            handle.write(payload)


class CardUpliftCanaryRuntime(CardUpliftShadowRuntime):
    def __init__(self, config: Mapping[str, Any]):
        self._initialize(
            validate_canary_configuration(config),
            CANARY_ROW_SCHEMA_VERSION,
        )

    def wrap_state_callback(self, current_callback: Callable[[Any], Any]):
        def wrapped(game: Any) -> Any:
            action = current_callback(game)
            try:
                return self._process(game, action, allow_substitution=True)
            except Exception as exc:
                self.disabled = True
                logger.error("[CARD_UPLIFT_CANARY] intervention failed: %s", exc)
                return action

        return wrapped


class CardUpliftEvaluationRuntime(CardUpliftCanaryRuntime):
    def __init__(self, config: Mapping[str, Any]):
        self._initialize(
            validate_evaluation_configuration(config),
            EVALUATION_ROW_SCHEMA_VERSION,
        )


def initialize_card_uplift_shadow_runtime(
    *, environ: Mapping[str, str] | None = None
) -> CardUpliftShadowRuntime | None:
    environment = os.environ if environ is None else environ
    path = environment.get(CONFIG_ENV)
    if path is None or not str(path).strip():
        return None
    return CardUpliftShadowRuntime(_read_canonical(path))


def initialize_card_uplift_canary_runtime(
    *, environ: Mapping[str, str] | None = None
) -> CardUpliftCanaryRuntime | None:
    environment = os.environ if environ is None else environ
    path = environment.get(CANARY_CONFIG_ENV)
    if path is None or not str(path).strip():
        return None
    return CardUpliftCanaryRuntime(_read_canonical(path))


def initialize_card_uplift_evaluation_runtime(
    *, environ: Mapping[str, str] | None = None
) -> CardUpliftEvaluationRuntime | None:
    environment = os.environ if environ is None else environ
    path = environment.get(EVALUATION_CONFIG_ENV)
    if path is None or not str(path).strip():
        return None
    return CardUpliftEvaluationRuntime(_read_canonical(path))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("register", "register-canary", "register-evaluation")
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--entry-checkpoint", required=True)
    parser.add_argument("--residual-model", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--maximum-games", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        common = {
            "repo_root": args.repo_root,
            "source_commit": args.source_commit,
            "entry_checkpoint": args.entry_checkpoint,
            "residual_model": args.residual_model,
            "output_path": args.output_path,
        }
        if args.command == "register-evaluation":
            if args.maximum_games is None:
                raise CardUpliftShadowError("evaluation maximum games is required")
            config = build_evaluation_configuration(
                **common, maximum_games=args.maximum_games
            )
        else:
            if args.maximum_games is not None:
                raise CardUpliftShadowError(
                    "maximum games is only valid for evaluation"
                )
            builder = (
                build_canary_configuration
                if args.command == "register-canary"
                else build_configuration
            )
            config = builder(**common)
        target = Path(args.config).resolve()
        target.write_bytes(_canonical_bytes(config))
        print(_canonical_bytes(_binding(target)).decode("ascii"), end="")
        return 0
    except (CardUpliftShadowError, OSError) as exc:
        print(str(exc), file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
