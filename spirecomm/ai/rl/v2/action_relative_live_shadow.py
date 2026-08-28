"""Behavior-neutral deferred live shadow for an action-relative residual."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Mapping, Optional
import uuid

import numpy as np
import torch

from analysis_scripts.combat_rl_action_relative_advantage_residual_fit import (
    FIXED_RECIPE as FIXED_FIT_RECIPE,
)
from spirecomm.ai.rl.checkpoint_io import load_torch_checkpoint

from .action_relative_advantage_residual import (
    ActionRelativeAdvantageResidual,
    load_development_artifact,
)
from .latent_gated_adapter import state_dict_sha256
from .latent_gated_live_shadow import (
    _require_committed_registration,
    _require_registered_file,
    _require_source_binding,
    _resolve_path,
    _safe_int,
    _state_sha256,
    _validate_sha256,
)


REGISTRATION_ENV = "STS_COMBAT_RL_ACTION_RELATIVE_SHADOW_REGISTRATION"
LEGACY_REGISTRATION_SCHEMA_VERSION = 1
REGISTRATION_SCHEMA_VERSION = 2
TRACE_SCHEMA_VERSION = 1
END_TURN_ACTION_INDEX = 90
SOURCE_BOUND_PATHS = (
    "analysis_scripts/combat_rl_action_relative_live_shadow_summary.py",
    "analysis_scripts/combat_rl_action_relative_advantage_residual_fit.py",
    "scripts/run_training_batch.py",
    "spirecomm/ai/rl/checkpoint_io.py",
    "spirecomm/ai/rl/v2/action_encoder.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/action_relative_live_shadow.py",
    "spirecomm/ai/rl/v2/agent.py",
    "spirecomm/ai/rl/v2/id_mapping.py",
    "spirecomm/ai/rl/v2/network.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
)


@dataclass(frozen=True)
class ActionRelativeShadowRegistration:
    schema_version: int
    inference_device: str
    experiment_id: str
    source_commit: str
    registration_path: Path
    registration_sha256: str
    candidate_artifact_path: Path
    candidate_artifact_sha256: str
    candidate_parent_checkpoint_sha256: str
    train_corpus_sha256: str
    evaluation_corpus_sha256: str
    production_parent_checkpoint_path: Path
    production_parent_checkpoint_sha256: str
    parent_state_dict_sha256: str
    trace_path: Path
    maximum_decision_count: int
    minimum_eligible_count: int
    maximum_p95_latency_ms: float


@dataclass
class _PendingDecision:
    game_identity: int
    event: dict[str, Any]
    continuous: np.ndarray
    card_ids: np.ndarray
    potion_ids: np.ndarray
    relic_ids: np.ndarray
    action_mask: np.ndarray


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"action-relative shadow {label} keys differ")
    return value


def load_live_shadow_registration(
    registration_path: str | Path,
    *,
    repo_root: str | Path,
    require_committed: bool = True,
) -> ActionRelativeShadowRegistration:
    root = Path(repo_root).resolve()
    path = Path(registration_path).resolve()
    if not path.is_file():
        raise ValueError(f"action-relative shadow registration is missing: {path}")
    data = path.read_bytes()
    if require_committed:
        _require_committed_registration(path, root)
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("action-relative shadow registration is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("action-relative shadow registration keys differ")
    schema_version = payload.get("schema_version")
    if schema_version not in {
        LEGACY_REGISTRATION_SCHEMA_VERSION,
        REGISTRATION_SCHEMA_VERSION,
    }:
        raise ValueError("action-relative shadow registration schema differs")
    expected_keys = {
        "schema_version",
        "experiment_id",
        "mode",
        "source_commit",
        "candidate_artifact",
        "production_parent_checkpoint",
        "parent_state_dict_sha256",
        "trace_path",
        "maximum_decision_count",
        "readiness_gates",
    }
    if schema_version == REGISTRATION_SCHEMA_VERSION:
        expected_keys.add("inference_device")
    payload = _exact_keys(payload, expected_keys, "registration")
    inference_device = (
        "parent"
        if schema_version == LEGACY_REGISTRATION_SCHEMA_VERSION
        else payload["inference_device"]
    )
    if schema_version == REGISTRATION_SCHEMA_VERSION and inference_device != "cpu":
        raise ValueError("action-relative shadow inference device must be cpu")
    if payload["mode"] != "shadow":
        raise ValueError("action-relative shadow registration mode differs")
    experiment_id = payload["experiment_id"]
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("action-relative shadow experiment identity is missing")
    source_commit = payload["source_commit"]
    if not isinstance(source_commit, str):
        raise ValueError("action-relative shadow source commit is missing")
    source_commit = source_commit.lower()
    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise ValueError("action-relative shadow source commit is invalid")
    candidate = _exact_keys(
        payload["candidate_artifact"],
        {
            "path",
            "sha256",
            "parent_checkpoint_sha256",
            "train_corpus_sha256",
            "evaluation_corpus_sha256",
        },
        "candidate binding",
    )
    production = _exact_keys(
        payload["production_parent_checkpoint"],
        {"path", "sha256"},
        "production parent binding",
    )
    gates = _exact_keys(
        payload["readiness_gates"],
        {"minimum_eligible_count", "maximum_p95_latency_ms"},
        "readiness gates",
    )
    maximum = payload["maximum_decision_count"]
    minimum = gates["minimum_eligible_count"]
    for value, label in (
        (maximum, "maximum decision count"),
        (minimum, "minimum eligible count"),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"action-relative shadow {label} must be positive")
    if minimum > maximum:
        raise ValueError("action-relative shadow minimum eligible count exceeds budget")
    latency = gates["maximum_p95_latency_ms"]
    if not isinstance(latency, (int, float)) or isinstance(latency, bool):
        raise ValueError("action-relative shadow latency ceiling is invalid")
    if not math.isfinite(float(latency)) or float(latency) <= 0:
        raise ValueError("action-relative shadow latency ceiling must be positive")
    trace_path = _resolve_path(payload["trace_path"], label="trace")
    try:
        trace_path.relative_to((root / "reports").resolve())
    except ValueError as exc:
        raise ValueError("action-relative shadow trace must be inside reports") from exc
    if trace_path.suffix.lower() != ".jsonl":
        raise ValueError("action-relative shadow trace must be JSONL")
    return ActionRelativeShadowRegistration(
        schema_version=int(schema_version),
        inference_device=str(inference_device),
        experiment_id=experiment_id.strip(),
        source_commit=source_commit,
        registration_path=path,
        registration_sha256=hashlib.sha256(data).hexdigest(),
        candidate_artifact_path=_resolve_path(candidate["path"], label="candidate artifact"),
        candidate_artifact_sha256=_validate_sha256(candidate["sha256"], "candidate artifact"),
        candidate_parent_checkpoint_sha256=_validate_sha256(
            candidate["parent_checkpoint_sha256"], "candidate parent checkpoint"
        ),
        train_corpus_sha256=_validate_sha256(
            candidate["train_corpus_sha256"], "train corpus"
        ),
        evaluation_corpus_sha256=_validate_sha256(
            candidate["evaluation_corpus_sha256"], "evaluation corpus"
        ),
        production_parent_checkpoint_path=_resolve_path(
            production["path"], label="production parent checkpoint"
        ),
        production_parent_checkpoint_sha256=_validate_sha256(
            production["sha256"], "production parent checkpoint"
        ),
        parent_state_dict_sha256=_validate_sha256(
            payload["parent_state_dict_sha256"], "parent state"
        ),
        trace_path=trace_path,
        maximum_decision_count=maximum,
        minimum_eligible_count=minimum,
        maximum_p95_latency_ms=float(latency),
    )


def _existing_decision_count(registration: ActionRelativeShadowRegistration) -> int:
    path = registration.trace_path
    if not path.exists():
        return 0
    if not path.is_file():
        raise ValueError("action-relative shadow existing trace is not a file")
    count = 0
    sessions: dict[str, int] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"action-relative shadow existing trace line {line_number} is invalid"
                ) from exc
            if not isinstance(event, Mapping):
                raise ValueError("action-relative shadow existing trace event is invalid")
            if event.get("experiment_id") != registration.experiment_id or event.get(
                "registration_sha256"
            ) != registration.registration_sha256:
                raise ValueError("action-relative shadow existing trace identity differs")
            if event.get("event_type") != "decision":
                continue
            session = event.get("session_id")
            sequence = event.get("decision_sequence")
            if not isinstance(session, str) or not isinstance(sequence, int):
                raise ValueError("action-relative shadow existing trace sequence is invalid")
            expected = sessions.get(session, 0) + 1
            if sequence != expected:
                raise ValueError("action-relative shadow decision sequence is not contiguous")
            sessions[session] = sequence
            count += 1
    if count > registration.maximum_decision_count:
        raise ValueError("action-relative shadow existing trace exceeds budget")
    return count


class ActionRelativeLiveShadow:
    """Cache proposals, then evaluate after the final guard action is known."""

    def __init__(
        self,
        *,
        residual: ActionRelativeAdvantageResidual,
        registration: ActionRelativeShadowRegistration,
        device: str,
        initial_decision_count: int = 0,
    ) -> None:
        self.residual = residual
        self.residual.eval()
        self.registration = registration
        self.device = torch.device(device)
        self.session_id = str(uuid.uuid4())
        self.enabled = True
        self.decision_count = int(initial_decision_count)
        self.session_decision_count = 0
        self.event_sequence = 0
        self.pending: Optional[_PendingDecision] = None

    @property
    def budget_exhausted(self) -> bool:
        return self.decision_count >= self.registration.maximum_decision_count

    def observe_proposal(
        self,
        *,
        game: Any,
        continuous: np.ndarray,
        card_ids: np.ndarray,
        potion_ids: np.ndarray,
        relic_ids: np.ndarray,
        action_mask: np.ndarray,
        parent_action_index: int,
    ) -> bool:
        if not self.enabled or self.budget_exhausted:
            return False
        if self.pending is not None:
            self.record_runtime_error(
                stage="proposal",
                error=RuntimeError("previous action-relative proposal was not committed"),
                game=game,
            )
            return False
        mask = np.asarray(action_mask, dtype=bool)
        if mask.ndim != 1 or not mask.any():
            raise ValueError("action-relative shadow mask must contain a legal action")
        player = getattr(game, "player", None)
        event = {
            "trace_schema_version": TRACE_SCHEMA_VERSION,
            "event_type": "decision",
            "experiment_id": self.registration.experiment_id,
            "session_id": self.session_id,
            "source_commit": self.registration.source_commit,
            "registration_sha256": self.registration.registration_sha256,
            "candidate_artifact_sha256": self.registration.candidate_artifact_sha256,
            "production_parent_checkpoint_sha256": (
                self.registration.production_parent_checkpoint_sha256
            ),
            "parent_state_dict_sha256": self.registration.parent_state_dict_sha256,
            "state_sha256": _state_sha256(
                np.asarray(continuous),
                np.asarray(card_ids),
                np.asarray(potion_ids),
                np.asarray(relic_ids),
                mask,
            ),
            "floor": _safe_int(getattr(game, "floor", None)),
            "turn": _safe_int(getattr(game, "turn", None)),
            "act": _safe_int(getattr(game, "act", None)),
            "room_type": str(getattr(game, "room_type", "") or ""),
            "screen_type": str(getattr(game, "screen_type", "") or ""),
            "player_energy": _safe_int(getattr(player, "energy", None)),
            "monster_names": [
                str(getattr(monster, "name", "") or "")
                for monster in (getattr(game, "monsters", None) or [])
            ],
            "parent_action_index": int(parent_action_index),
            "legal_action_indices": np.flatnonzero(mask).astype(int).tolist(),
        }
        self.pending = _PendingDecision(
            game_identity=id(game),
            event=event,
            continuous=np.asarray(continuous).copy(),
            card_ids=np.asarray(card_ids).copy(),
            potion_ids=np.asarray(potion_ids).copy(),
            relic_ids=np.asarray(relic_ids).copy(),
            action_mask=mask.copy(),
        )
        return True

    def commit_executed_action(
        self, *, game: Any, executed_action_index: Optional[int]
    ) -> bool:
        if self.pending is None:
            return False
        if self.pending.game_identity != id(game):
            self.record_runtime_error(
                stage="commit",
                error=RuntimeError("action-relative proposal game identity differs"),
                game=game,
            )
            return False
        pending = self.pending
        self.pending = None
        event = pending.event
        executed = None if executed_action_index is None else int(executed_action_index)
        encodable = executed is not None
        legal = bool(
            encodable
            and 0 <= executed < pending.action_mask.size
            and pending.action_mask[executed]
        )
        parent = int(event["parent_action_index"])
        if parent != END_TURN_ACTION_INDEX:
            reason = "parent_not_end_turn"
        elif not encodable:
            reason = "executed_action_unencodable"
        elif not legal:
            reason = "executed_action_illegal"
        elif executed == END_TURN_ACTION_INDEX:
            reason = "guard_not_replaced"
        else:
            reason = ""
        eligible = not reason
        event.update(
            {
                "executed_action_index": executed,
                "executed_action_encodable": encodable,
                "executed_action_legal": legal,
                "guard_action_index": executed if eligible else None,
                "eligible": eligible,
                "support_reason": reason,
                "candidate_action_index": None,
                "candidate_action_legal": None,
                "candidate_action_forbidden": None,
                "candidate_would_intervene": False,
                "candidate_matches_executed": None,
                "candidate_has_authority": False,
                "predicted_advantage": None,
                "advantage_threshold": float(
                    self.residual.config.advantage_threshold
                ),
                "forbidden_action_indices": [END_TURN_ACTION_INDEX],
                "shadow_latency_ms": 0.0,
                "runtime_error_type": "",
                "runtime_error_message": "",
            }
        )
        disable = False
        if eligible:
            try:
                alternative_mask = pending.action_mask.copy()
                alternative_mask[executed] = False
                alternative_mask[END_TURN_ACTION_INDEX] = False
                started = time.perf_counter()
                with torch.no_grad():
                    selection = self.residual.select_actions(
                        torch.as_tensor(pending.continuous, device=self.device).unsqueeze(0),
                        torch.as_tensor(pending.card_ids, device=self.device).unsqueeze(0),
                        torch.as_tensor(pending.potion_ids, device=self.device).unsqueeze(0),
                        torch.as_tensor(pending.relic_ids, device=self.device).unsqueeze(0),
                        torch.as_tensor(pending.action_mask, device=self.device).unsqueeze(0),
                        torch.tensor([executed], device=self.device),
                        torch.as_tensor(alternative_mask, device=self.device).unsqueeze(0),
                        forbidden_action_indices=frozenset({END_TURN_ACTION_INDEX}),
                    )
                latency_ms = (time.perf_counter() - started) * 1000.0
                gate_open = bool(selection.gate_open.item())
                candidate = int(selection.actions.item()) if gate_open else None
                prediction = float(selection.predicted_advantages.item())
                if not math.isfinite(prediction):
                    prediction_value: Optional[float] = None
                else:
                    prediction_value = prediction
                candidate_legal = (
                    bool(pending.action_mask[candidate]) if candidate is not None else None
                )
                candidate_forbidden = (
                    candidate == END_TURN_ACTION_INDEX if candidate is not None else None
                )
                event.update(
                    {
                        "candidate_action_index": candidate,
                        "candidate_action_legal": candidate_legal,
                        "candidate_action_forbidden": candidate_forbidden,
                        "candidate_would_intervene": gate_open,
                        "candidate_matches_executed": (
                            candidate == executed if candidate is not None else None
                        ),
                        "predicted_advantage": prediction_value,
                        "shadow_latency_ms": latency_ms,
                    }
                )
                if candidate is not None and (
                    candidate_legal is not True or candidate_forbidden is not False
                ):
                    disable = True
            except Exception as exc:
                event["runtime_error_type"] = type(exc).__name__
                event["runtime_error_message"] = str(exc)
                disable = True
        self.decision_count += 1
        self.session_decision_count += 1
        event["decision_sequence"] = self.session_decision_count
        try:
            self._append_event(event)
        except Exception:
            self.enabled = False
            return False
        if disable:
            self.enabled = False
        return True

    def discard_transient_action(self, *, reason: str) -> bool:
        if self.pending is None:
            return False
        pending = self.pending
        self.pending = None
        event = dict(pending.event)
        event["event_type"] = "transient_discard"
        event["discard_reason"] = str(reason)
        self._append_event(event)
        return True

    def discard_pending(self) -> None:
        if self.pending is None:
            return
        self.record_runtime_error(
            stage="discard_pending",
            error=RuntimeError("pending action-relative proposal was discarded"),
            game=None,
        )

    def record_runtime_error(self, *, stage: str, error: Exception, game: Any) -> None:
        pending = self.pending.event if self.pending is not None else {}
        self.pending = None
        self.enabled = False
        event = {
            "trace_schema_version": TRACE_SCHEMA_VERSION,
            "event_type": "error",
            "experiment_id": self.registration.experiment_id,
            "session_id": self.session_id,
            "source_commit": self.registration.source_commit,
            "registration_sha256": self.registration.registration_sha256,
            "candidate_artifact_sha256": self.registration.candidate_artifact_sha256,
            "production_parent_checkpoint_sha256": (
                self.registration.production_parent_checkpoint_sha256
            ),
            "parent_state_dict_sha256": self.registration.parent_state_dict_sha256,
            "stage": str(stage),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "floor": _safe_int(
                getattr(game, "floor", pending.get("floor"))
                if game is not None
                else pending.get("floor")
            ),
            "turn": _safe_int(
                getattr(game, "turn", pending.get("turn"))
                if game is not None
                else pending.get("turn")
            ),
        }
        try:
            self._append_event(event)
        except Exception:
            pass

    def _append_event(self, event: Mapping[str, Any]) -> None:
        self.event_sequence += 1
        payload = dict(event)
        payload["event_sequence"] = self.event_sequence
        payload["timestamp"] = datetime.now(timezone.utc).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")
        target = self.registration.trace_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def initialize_action_relative_live_shadow(
    *,
    parent: torch.nn.Module,
    metadata: Mapping[str, Any],
    model_path: Optional[str],
    training: bool,
    epsilon: float,
    expert_mix_enabled: bool,
    repo_root: str | Path,
    device: str,
    registration_path: Optional[str] = None,
    require_committed_registration: bool = True,
) -> Optional[ActionRelativeLiveShadow]:
    configured = registration_path
    if configured is None:
        configured = os.environ.get(REGISTRATION_ENV)
    if configured is None or not configured.strip():
        return None
    if training:
        raise ValueError("action-relative live shadow cannot run during training")
    if not math.isclose(float(epsilon), 0.0, abs_tol=0.0):
        raise ValueError("action-relative live shadow requires epsilon zero")
    if expert_mix_enabled:
        raise ValueError("action-relative live shadow requires expert mix disabled")
    if not model_path:
        raise ValueError("action-relative live shadow requires a parent checkpoint")
    registration = load_live_shadow_registration(
        configured,
        repo_root=repo_root,
        require_committed=require_committed_registration,
    )
    if require_committed_registration:
        _require_source_binding(
            registration.source_commit,
            Path(repo_root).resolve(),
            source_bound_paths=SOURCE_BOUND_PATHS,
        )
    initial_decision_count = _existing_decision_count(registration)
    active_model = Path(model_path).resolve()
    if active_model != registration.production_parent_checkpoint_path:
        raise ValueError("action-relative shadow production parent path differs")
    _require_registered_file(
        active_model,
        registration.production_parent_checkpoint_sha256,
        "production parent checkpoint",
    )
    production_parent_state = state_dict_sha256(parent.state_dict())
    if production_parent_state != registration.parent_state_dict_sha256:
        raise ValueError("action-relative shadow parent state differs")
    _require_registered_file(
        registration.candidate_artifact_path,
        registration.candidate_artifact_sha256,
        "candidate artifact",
    )
    if registration.inference_device == "cpu":
        residual_parent = copy.deepcopy(parent).to("cpu")
        residual_device = "cpu"
    else:
        residual_parent = parent
        residual_device = device
    artifact = load_torch_checkpoint(
        str(registration.candidate_artifact_path), map_location=residual_device
    )
    residual = load_development_artifact(
        residual_parent,
        metadata,
        artifact,
        expected_parent_checkpoint_sha256=(
            registration.candidate_parent_checkpoint_sha256
        ),
        expected_corpus_sha256={
            "train": registration.train_corpus_sha256,
            "evaluation": registration.evaluation_corpus_sha256,
        },
        expected_recipe=FIXED_FIT_RECIPE,
    )
    if state_dict_sha256(parent.state_dict()) != production_parent_state:
        raise RuntimeError("action-relative shadow mutated production parent state")
    if registration.inference_device == "cpu" and any(
        parameter.device.type != "cpu" for parameter in residual.parameters()
    ):
        raise RuntimeError("action-relative shadow CPU residual device differs")
    return ActionRelativeLiveShadow(
        residual=residual,
        registration=registration,
        device=residual_device,
        initial_decision_count=initial_decision_count,
    )
