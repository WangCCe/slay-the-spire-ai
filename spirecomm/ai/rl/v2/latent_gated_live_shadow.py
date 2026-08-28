"""Behavior-neutral live shadow runtime for a latent-gated RL v2 candidate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping, Optional
import uuid

import numpy as np
import torch

from spirecomm.ai.rl.checkpoint_io import load_torch_checkpoint

from .latent_gated_adapter import (
    LatentGatedActionAdapter,
    load_development_artifact,
    state_dict_sha256,
)


REGISTRATION_ENV = "STS_COMBAT_RL_LATENT_SHADOW_REGISTRATION"
REGISTRATION_SCHEMA_VERSION = 1
TRACE_SCHEMA_VERSION = 1
SOURCE_BOUND_PATHS = (
    "analysis_scripts/combat_rl_latent_gated_live_shadow_summary.py",
    "scripts/run_training_batch.py",
    "spirecomm/ai/rl/checkpoint_io.py",
    "spirecomm/ai/rl/v2/action_encoder.py",
    "spirecomm/ai/rl/v2/agent.py",
    "spirecomm/ai/rl/v2/id_mapping.py",
    "spirecomm/ai/rl/v2/latent_gated_adapter.py",
    "spirecomm/ai/rl/v2/latent_gated_live_shadow.py",
    "spirecomm/ai/rl/v2/network.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
)


@dataclass(frozen=True)
class LiveShadowRegistration:
    experiment_id: str
    source_commit: str
    registration_path: Path
    registration_sha256: str
    candidate_artifact_path: Path
    candidate_artifact_sha256: str
    candidate_parent_checkpoint_sha256: str
    production_parent_checkpoint_path: Path
    production_parent_checkpoint_sha256: str
    parent_state_dict_sha256: str
    trace_path: Path
    maximum_decision_count: int
    minimum_decision_count: int
    maximum_p95_latency_ms: float


@dataclass
class _PendingShadowDecision:
    game_identity: int
    event: dict[str, Any]
    disable_after_commit: bool = False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"live shadow {label} SHA-256 is missing")
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"live shadow {label} SHA-256 is invalid")
    return normalized


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"live shadow {label} keys differ")
    return value


def _resolve_path(value: Any, *, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"live shadow {label} path is missing")
    path = Path(value).expanduser().resolve()
    if not path.is_absolute():
        raise ValueError(f"live shadow {label} path must be absolute")
    return path


def _require_registered_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"live shadow {label} file is missing: {path}")
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"live shadow {label} SHA-256 differs")


def _require_committed_registration(path: Path, repo_root: Path) -> None:
    try:
        relative = path.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError("live shadow registration must be inside the repository") from exc
    common = {
        "cwd": str(repo_root),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "check": False,
    }
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", str(relative)], **common
    )
    if tracked.returncode != 0:
        raise ValueError("live shadow registration must be tracked")
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", str(relative)], **common
    )
    if unchanged.returncode != 0:
        raise ValueError("live shadow registration must match committed HEAD")


def _require_source_binding(
    source_commit: str,
    repo_root: Path,
    *,
    source_bound_paths: Optional[tuple[str, ...]] = None,
) -> None:
    bound_paths = SOURCE_BOUND_PATHS if source_bound_paths is None else source_bound_paths
    common = {
        "cwd": str(repo_root),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "check": False,
    }
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"], **common
    )
    if ancestor.returncode != 0:
        raise ValueError("live shadow source commit is not an ancestor of HEAD")
    for relative in bound_paths:
        present = subprocess.run(
            ["git", "cat-file", "-e", f"{source_commit}:{relative}"], **common
        )
        if present.returncode != 0:
            raise ValueError(f"live shadow source file is absent: {relative}")
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", source_commit, "--", *bound_paths],
        **common,
    )
    if unchanged.returncode != 0:
        raise ValueError("live shadow source files differ from the registered commit")


def load_live_registration(
    registration_path: str | Path,
    *,
    repo_root: str | Path,
    expected_mode: str,
    require_committed: bool = True,
) -> LiveShadowRegistration:
    root = Path(repo_root).resolve()
    path = Path(registration_path).resolve()
    if not path.is_file():
        raise ValueError(f"live shadow registration is missing: {path}")
    registration_bytes = path.read_bytes()
    if require_committed:
        _require_committed_registration(path, root)
    try:
        payload = json.loads(registration_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("live shadow registration is not valid JSON") from exc
    payload = _exact_keys(
        payload,
        {
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
        },
        "registration",
    )
    if payload["schema_version"] != REGISTRATION_SCHEMA_VERSION:
        raise ValueError("live shadow registration schema differs")
    if payload["mode"] != expected_mode:
        raise ValueError("live shadow registration mode differs")
    experiment_id = payload["experiment_id"]
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("live shadow experiment identity is missing")
    source_commit = payload["source_commit"]
    if not isinstance(source_commit, str):
        raise ValueError("live shadow source commit is missing")
    source_commit = source_commit.lower()
    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise ValueError("live shadow source commit is invalid")

    candidate = _exact_keys(
        payload["candidate_artifact"],
        {"path", "sha256", "parent_checkpoint_sha256"},
        "candidate artifact binding",
    )
    production = _exact_keys(
        payload["production_parent_checkpoint"],
        {"path", "sha256"},
        "production parent checkpoint binding",
    )
    gates = _exact_keys(
        payload["readiness_gates"],
        {"minimum_decision_count", "maximum_p95_latency_ms"},
        "readiness gates",
    )
    maximum_decisions = payload["maximum_decision_count"]
    minimum_decisions = gates["minimum_decision_count"]
    latency_ceiling = gates["maximum_p95_latency_ms"]
    for value, label in (
        (maximum_decisions, "maximum decision count"),
        (minimum_decisions, "minimum decision count"),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"live shadow {label} must be a positive integer")
    if minimum_decisions > maximum_decisions:
        raise ValueError("live shadow minimum decision count exceeds the budget")
    if not isinstance(latency_ceiling, (int, float)) or isinstance(
        latency_ceiling, bool
    ) or not math.isfinite(float(latency_ceiling)) or float(latency_ceiling) <= 0:
        raise ValueError("live shadow latency ceiling must be finite and positive")

    trace_path = _resolve_path(payload["trace_path"], label="trace")
    reports_root = (root / "reports").resolve()
    try:
        trace_path.relative_to(reports_root)
    except ValueError as exc:
        raise ValueError("live shadow trace must be inside repository reports") from exc
    if trace_path.suffix.lower() != ".jsonl":
        raise ValueError("live shadow trace must be JSONL")

    return LiveShadowRegistration(
        experiment_id=experiment_id.strip(),
        source_commit=source_commit,
        registration_path=path,
        registration_sha256=hashlib.sha256(registration_bytes).hexdigest(),
        candidate_artifact_path=_resolve_path(
            candidate["path"], label="candidate artifact"
        ),
        candidate_artifact_sha256=_validate_sha256(
            candidate["sha256"], "candidate artifact"
        ),
        candidate_parent_checkpoint_sha256=_validate_sha256(
            candidate["parent_checkpoint_sha256"],
            "candidate parent checkpoint",
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
        maximum_decision_count=maximum_decisions,
        minimum_decision_count=minimum_decisions,
        maximum_p95_latency_ms=float(latency_ceiling),
    )


def load_live_shadow_registration(
    registration_path: str | Path,
    *,
    repo_root: str | Path,
    require_committed: bool = True,
) -> LiveShadowRegistration:
    return load_live_registration(
        registration_path,
        repo_root=repo_root,
        expected_mode="shadow",
        require_committed=require_committed,
    )


def _state_sha256(
    continuous: np.ndarray,
    card_ids: np.ndarray,
    potion_ids: np.ndarray,
    relic_ids: np.ndarray,
    action_mask: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    for value in (continuous, card_ids, potion_ids, relic_ids, action_mask):
        array = np.ascontiguousarray(value)
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def _existing_trace_decision_count(
    registration: LiveShadowRegistration,
) -> int:
    path = registration.trace_path
    if not path.exists():
        return 0
    if not path.is_file():
        raise ValueError("live shadow existing trace path is not a file")
    expected_identity = {
        "trace_schema_version": TRACE_SCHEMA_VERSION,
        "experiment_id": registration.experiment_id,
        "source_commit": registration.source_commit,
        "registration_sha256": registration.registration_sha256,
        "candidate_artifact_sha256": registration.candidate_artifact_sha256,
        "production_parent_checkpoint_sha256": (
            registration.production_parent_checkpoint_sha256
        ),
        "parent_state_dict_sha256": registration.parent_state_dict_sha256,
    }
    event_sequences: dict[str, int] = {}
    decision_sequences: dict[str, int] = {}
    decision_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"live shadow existing trace line {line_number} is invalid JSON"
                ) from exc
            if not isinstance(event, Mapping):
                raise ValueError(
                    f"live shadow existing trace line {line_number} is not an object"
                )
            if event.get("event_type") not in {
                "decision",
                "transient_discard",
                "error",
            }:
                raise ValueError(
                    f"live shadow existing trace line {line_number} type differs"
                )
            for field, expected in expected_identity.items():
                if event.get(field) != expected:
                    raise ValueError(
                        f"live shadow existing trace line {line_number} {field} differs"
                    )
            session_id = event.get("session_id")
            if not isinstance(session_id, str) or not session_id:
                raise ValueError(
                    f"live shadow existing trace line {line_number} session is missing"
                )
            event_sequences[session_id] = event_sequences.get(session_id, 0) + 1
            if event.get("event_sequence") != event_sequences[session_id]:
                raise ValueError(
                    f"live shadow existing trace session {session_id} is not contiguous"
                )
            if event["event_type"] == "decision":
                decision_sequences[session_id] = (
                    decision_sequences.get(session_id, 0) + 1
                )
                if event.get("decision_sequence") != decision_sequences[session_id]:
                    raise ValueError(
                        "live shadow existing trace decision sequence is not contiguous"
                    )
                decision_count += 1
    if decision_count > registration.maximum_decision_count:
        raise ValueError("live shadow existing trace exceeds the decision budget")
    return decision_count


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


class LatentGatedLiveShadow:
    """Evaluate a candidate and bind it to the final action without control authority."""

    def __init__(
        self,
        *,
        adapter: LatentGatedActionAdapter,
        registration: LiveShadowRegistration,
        source_commit: str,
        device: str,
        initial_decision_count: int = 0,
    ) -> None:
        self.adapter = adapter
        self.adapter.eval()
        self.registration = registration
        self.source_commit = source_commit
        self.device = torch.device(device)
        self.session_id = str(uuid.uuid4())
        self.enabled = True
        self.decision_count = int(initial_decision_count)
        self.session_decision_count = 0
        self.event_sequence = 0
        self.pending: Optional[_PendingShadowDecision] = None

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
                error=RuntimeError("previous shadow proposal was not committed"),
                game=game,
            )
            return False
        mask = np.asarray(action_mask, dtype=bool)
        if mask.ndim != 1 or not mask.any():
            raise ValueError("live shadow action mask must contain one legal action")
        started = time.perf_counter()
        selected = self.adapter.select_actions(
            torch.as_tensor(continuous, device=self.device).unsqueeze(0),
            torch.as_tensor(card_ids, device=self.device).unsqueeze(0),
            torch.as_tensor(potion_ids, device=self.device).unsqueeze(0),
            torch.as_tensor(relic_ids, device=self.device).unsqueeze(0),
            torch.as_tensor(mask, device=self.device).unsqueeze(0),
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        shadow_parent = int(selected.parent_actions.item())
        correction = int(selected.correction_actions.item())
        candidate = int(selected.actions.item())
        parent_action_index = int(parent_action_index)
        candidate_legal = 0 <= candidate < mask.size and bool(mask[candidate])
        parent_parity = shadow_parent == parent_action_index
        player = getattr(game, "player", None)
        event = {
            "trace_schema_version": TRACE_SCHEMA_VERSION,
            "event_type": "decision",
            "experiment_id": self.registration.experiment_id,
            "session_id": self.session_id,
            "source_commit": self.source_commit,
            "registration_sha256": self.registration.registration_sha256,
            "candidate_artifact_sha256": (
                self.registration.candidate_artifact_sha256
            ),
            "production_parent_checkpoint_sha256": (
                self.registration.production_parent_checkpoint_sha256
            ),
            "parent_state_dict_sha256": (
                self.registration.parent_state_dict_sha256
            ),
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
            "parent_action_index": parent_action_index,
            "shadow_parent_action_index": shadow_parent,
            "correction_action_index": correction,
            "candidate_action_index": candidate,
            "legal_action_indices": np.flatnonzero(mask).astype(int).tolist(),
            "gate_probability": float(selected.gate_probabilities.item()),
            "gate_threshold": float(self.adapter.config.gate_threshold),
            "gate_open": bool(selected.gate_open.item()),
            "candidate_action_legal": candidate_legal,
            "parent_parity": parent_parity,
            "shadow_latency_ms": latency_ms,
            "_action_mask": mask.copy(),
        }
        self.pending = _PendingShadowDecision(
            game_identity=id(game),
            event=event,
            disable_after_commit=not parent_parity or not candidate_legal,
        )
        return True

    def commit_executed_action(
        self,
        *,
        game: Any,
        executed_action_index: Optional[int],
    ) -> bool:
        if self.pending is None:
            return False
        if self.pending.game_identity != id(game):
            self.record_runtime_error(
                stage="commit",
                error=RuntimeError("shadow proposal game identity differs"),
                game=game,
            )
            return False
        pending = self.pending
        self.pending = None
        event = pending.event
        executed = None if executed_action_index is None else int(executed_action_index)
        action_mask = event.pop("_action_mask")
        executed_encodable = executed is not None
        executed_legal = bool(
            executed_encodable
            and 0 <= executed < action_mask.size
            and action_mask[executed]
        )
        event.update(
            {
                "executed_action_index": executed,
                "executed_action_encodable": executed_encodable,
                "executed_action_legal": executed_legal,
                "proposal_changed": executed != event["parent_action_index"],
                "candidate_matches_executed": (
                    executed == event["candidate_action_index"]
                ),
                "correction_matches_executed": (
                    executed == event["correction_action_index"]
                ),
            }
        )
        if "selected_action_index" in event:
            event["selected_matches_executed"] = (
                executed == event["selected_action_index"]
            )
        self.decision_count += 1
        self.session_decision_count += 1
        event["decision_sequence"] = self.session_decision_count
        self._append_event(event)
        if pending.disable_after_commit:
            self.enabled = False
        return True

    def discard_pending(self) -> None:
        if self.pending is None:
            return
        self.record_runtime_error(
            stage="discard_pending",
            error=RuntimeError("pending shadow proposal was discarded"),
            game=None,
        )

    def discard_transient_action(self, *, reason: str) -> bool:
        """Publish a non-gameplay control action without consuming decision budget."""
        if self.pending is None:
            return False
        pending = self.pending
        self.pending = None
        event = pending.event
        event.pop("_action_mask")
        event["event_type"] = "transient_discard"
        event["discard_reason"] = str(reason)
        self._append_event(event)
        if pending.disable_after_commit:
            self.enabled = False
        return True

    def record_runtime_error(self, *, stage: str, error: Exception, game: Any) -> None:
        pending_event = self.pending.event if self.pending is not None else {}
        self.enabled = False
        self.pending = None
        event = {
            "trace_schema_version": TRACE_SCHEMA_VERSION,
            "event_type": "error",
            "experiment_id": self.registration.experiment_id,
            "session_id": self.session_id,
            "source_commit": self.source_commit,
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
                getattr(game, "floor", pending_event.get("floor"))
                if game is not None
                else pending_event.get("floor")
            ),
            "turn": _safe_int(
                getattr(game, "turn", pending_event.get("turn"))
                if game is not None
                else pending_event.get("turn")
            ),
        }
        try:
            self._append_event(event)
        except Exception:
            pass

    def _append_event(self, event: dict[str, Any]) -> None:
        self.event_sequence += 1
        event = dict(event)
        event["event_sequence"] = self.event_sequence
        event["timestamp"] = datetime.now(timezone.utc).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")
        target = self.registration.trace_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def initialize_latent_gated_live_shadow(
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
) -> Optional[LatentGatedLiveShadow]:
    configured = registration_path
    if configured is None:
        configured = os.environ.get(REGISTRATION_ENV)
    if configured is None or not configured.strip():
        return None
    if training:
        raise ValueError("latent-gated live shadow cannot run during training")
    if not math.isclose(float(epsilon), 0.0, abs_tol=0.0):
        raise ValueError("latent-gated live shadow requires epsilon zero")
    if expert_mix_enabled:
        raise ValueError("latent-gated live shadow requires expert mix disabled")
    if not model_path:
        raise ValueError("latent-gated live shadow requires a parent checkpoint")

    registration = load_live_shadow_registration(
        configured,
        repo_root=repo_root,
        require_committed=require_committed_registration,
    )
    if require_committed_registration:
        _require_source_binding(registration.source_commit, Path(repo_root).resolve())
    initial_decision_count = _existing_trace_decision_count(registration)
    active_model_path = Path(model_path).resolve()
    if active_model_path != registration.production_parent_checkpoint_path:
        raise ValueError("live shadow production parent checkpoint path differs")
    _require_registered_file(
        active_model_path,
        registration.production_parent_checkpoint_sha256,
        "production parent checkpoint",
    )
    observed_parent_state = state_dict_sha256(parent.state_dict())
    if observed_parent_state != registration.parent_state_dict_sha256:
        raise ValueError("live shadow parent state identity differs")
    _require_registered_file(
        registration.candidate_artifact_path,
        registration.candidate_artifact_sha256,
        "candidate artifact",
    )
    artifact = load_torch_checkpoint(
        str(registration.candidate_artifact_path), map_location=device
    )
    adapter = load_development_artifact(
        parent,
        metadata,
        artifact,
        expected_parent_checkpoint_sha256=(
            registration.candidate_parent_checkpoint_sha256
        ),
    )
    return LatentGatedLiveShadow(
        adapter=adapter,
        registration=registration,
        source_commit=registration.source_commit,
        device=device,
        initial_decision_count=initial_decision_count,
    )
