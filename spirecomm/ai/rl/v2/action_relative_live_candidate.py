"""Eval-only late authority for a source-bound action-relative residual."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Optional

import torch

from analysis_scripts.combat_rl_action_relative_advantage_residual_fit import (
    FIXED_RECIPE as FIXED_FIT_RECIPE,
)
from spirecomm.ai.rl.checkpoint_io import load_torch_checkpoint

from .action_relative_advantage_residual import load_development_artifact
from .action_relative_live_shadow import (
    ActionRelativeLiveShadow,
    _existing_decision_count,
)
from .latent_gated_adapter import state_dict_sha256
from .latent_gated_live_shadow import (
    _require_committed_registration,
    _require_registered_file,
    _require_source_binding,
    _resolve_path,
    _validate_sha256,
)


REGISTRATION_ENV = "STS_COMBAT_RL_ACTION_RELATIVE_CANDIDATE_REGISTRATION"
REGISTRATION_SCHEMA_VERSION = 1
SAFETY_POLICY_VERSION = "fixed-late-card-v1"
SOURCE_BOUND_PATHS = (
    "analysis_scripts/combat_rl_action_relative_advantage_residual_fit.py",
    "scripts/run_training_batch.py",
    "spirecomm/ai/rl/agent.py",
    "spirecomm/ai/rl/checkpoint_io.py",
    "spirecomm/ai/rl/v2/action_encoder.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/action_relative_live_candidate.py",
    "spirecomm/ai/rl/v2/action_relative_live_shadow.py",
    "spirecomm/ai/rl/v2/agent.py",
    "spirecomm/ai/rl/v2/id_mapping.py",
    "spirecomm/ai/rl/v2/network.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
)


@dataclass(frozen=True)
class ActionRelativeCandidateRegistration:
    schema_version: int
    inference_device: str
    safety_policy_version: str
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


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"action-relative candidate {label} keys differ")
    return value


def load_live_candidate_registration(
    registration_path: str | Path,
    *,
    repo_root: str | Path,
    require_committed: bool = True,
) -> ActionRelativeCandidateRegistration:
    root = Path(repo_root).resolve()
    path = Path(registration_path).resolve()
    if not path.is_file():
        raise ValueError(f"action-relative candidate registration is missing: {path}")
    data = path.read_bytes()
    if require_committed:
        _require_committed_registration(path, root)
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "action-relative candidate registration is not valid JSON"
        ) from exc
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
            "inference_device",
            "safety_policy_version",
            "trace_path",
            "maximum_decision_count",
        },
        "registration",
    )
    if payload["schema_version"] != REGISTRATION_SCHEMA_VERSION:
        raise ValueError("action-relative candidate registration schema differs")
    if payload["mode"] != "candidate":
        raise ValueError("action-relative candidate registration mode differs")
    if payload["inference_device"] != "cpu":
        raise ValueError("action-relative candidate inference device must be cpu")
    if payload["safety_policy_version"] != SAFETY_POLICY_VERSION:
        raise ValueError("action-relative candidate safety policy differs")
    experiment_id = payload["experiment_id"]
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("action-relative candidate experiment identity is missing")
    source_commit = payload["source_commit"]
    if not isinstance(source_commit, str):
        raise ValueError("action-relative candidate source commit is missing")
    source_commit = source_commit.lower()
    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise ValueError("action-relative candidate source commit is invalid")
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
    maximum = payload["maximum_decision_count"]
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0:
        raise ValueError(
            "action-relative candidate maximum decision count must be positive"
        )
    trace_path = _resolve_path(payload["trace_path"], label="trace")
    try:
        trace_path.relative_to((root / "reports").resolve())
    except ValueError as exc:
        raise ValueError(
            "action-relative candidate trace must be inside reports"
        ) from exc
    if trace_path.suffix.lower() != ".jsonl":
        raise ValueError("action-relative candidate trace must be JSONL")
    return ActionRelativeCandidateRegistration(
        schema_version=REGISTRATION_SCHEMA_VERSION,
        inference_device="cpu",
        safety_policy_version=SAFETY_POLICY_VERSION,
        experiment_id=experiment_id.strip(),
        source_commit=source_commit,
        registration_path=path,
        registration_sha256=hashlib.sha256(data).hexdigest(),
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
    )


class ActionRelativeLiveCandidate(ActionRelativeLiveShadow):
    """Evaluate after the guard, then await an explicit safety decision."""

    registration: ActionRelativeCandidateRegistration

    def prepare_candidate_action(
        self, *, game: Any, guard_action_index: Optional[int]
    ) -> Optional[int]:
        if not self.enabled:
            return None
        if self.budget_exhausted:
            self.record_runtime_error(
                stage="prepare_guard",
                error=RuntimeError("candidate decision budget is exhausted"),
                game=game,
            )
            return None
        event = self.prepare_guard_action(
            game=game,
            guard_action_index=guard_action_index,
            candidate_has_authority=True,
        )
        if event is None or self.pending is None:
            return None
        guard = None if guard_action_index is None else int(guard_action_index)
        candidate = event.get("candidate_action_index")
        would_intervene = bool(event.get("candidate_would_intervene"))
        event.update(
            {
                "safety_policy_version": SAFETY_POLICY_VERSION,
                "safety_veto_reason": (
                    "pending" if would_intervene else "candidate_abstained"
                ),
                "selected_action_index": guard,
                "candidate_takeover_applied": False,
            }
        )
        if event.get("runtime_error_type"):
            event["safety_veto_reason"] = "candidate_runtime_error"
            return None
        return int(candidate) if would_intervene and candidate is not None else None

    def resolve_safety_decision(
        self, *, selected_action_index: int, veto_reason: str
    ) -> bool:
        if self.pending is None or not self.pending.prepared:
            return False
        event = self.pending.event
        selected = int(selected_action_index)
        guard = event.get("guard_action_index")
        candidate = event.get("candidate_action_index")
        reason = str(veto_reason or "")
        valid = bool(
            (not reason and candidate is not None and selected == candidate)
            or (reason and guard is not None and selected == guard)
        )
        if not valid:
            event["runtime_error_type"] = "RuntimeError"
            event["runtime_error_message"] = "late safety resolution is inconsistent"
            self.pending.disable_after_commit = True
            selected = guard
            reason = "invalid_safety_resolution"
        event.update(
            {
                "safety_veto_reason": reason,
                "selected_action_index": selected,
                "candidate_takeover_applied": bool(
                    not reason and candidate is not None and selected == candidate
                ),
            }
        )
        if reason.startswith("safety_veto_error:"):
            event["runtime_error_type"] = "RuntimeError"
            event["runtime_error_message"] = "late safety veto raised"
            self.pending.disable_after_commit = True
        return valid

    def commit_executed_action(
        self, *, game: Any, executed_action_index: Optional[int]
    ) -> bool:
        if self.pending is None:
            return False
        if not self.pending.prepared:
            self.prepare_candidate_action(
                game=game,
                guard_action_index=executed_action_index,
            )
            if self.pending is None:
                return False
        event = self.pending.event
        if event.get("safety_veto_reason") == "pending":
            event["safety_veto_reason"] = "unresolved_safety_decision"
            event["selected_action_index"] = event.get("guard_action_index")
            event["candidate_takeover_applied"] = False
            event["runtime_error_type"] = "RuntimeError"
            event["runtime_error_message"] = "candidate safety decision was not resolved"
            self.pending.disable_after_commit = True
        selected = event.get("selected_action_index")
        executed = None if executed_action_index is None else int(executed_action_index)
        if selected != executed:
            event["runtime_error_type"] = "RuntimeError"
            event["runtime_error_message"] = "selected action differs from final action"
            self.pending.disable_after_commit = True
        return self._commit_prepared_action(
            game=game,
            executed_action_index=executed_action_index,
        )


def initialize_action_relative_live_candidate(
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
) -> Optional[ActionRelativeLiveCandidate]:
    configured = registration_path
    if configured is None:
        configured = os.environ.get(REGISTRATION_ENV)
    if configured is None or not configured.strip():
        return None
    if training:
        raise ValueError("action-relative live candidate cannot run during training")
    if not math.isclose(float(epsilon), 0.0, abs_tol=0.0):
        raise ValueError("action-relative live candidate requires epsilon zero")
    if expert_mix_enabled:
        raise ValueError("action-relative live candidate requires expert mix disabled")
    if not model_path:
        raise ValueError("action-relative live candidate requires a parent checkpoint")
    registration = load_live_candidate_registration(
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
        raise ValueError("action-relative candidate production parent path differs")
    _require_registered_file(
        active_model,
        registration.production_parent_checkpoint_sha256,
        "production parent checkpoint",
    )
    production_parent_state = state_dict_sha256(parent.state_dict())
    if production_parent_state != registration.parent_state_dict_sha256:
        raise ValueError("action-relative candidate parent state differs")
    _require_registered_file(
        registration.candidate_artifact_path,
        registration.candidate_artifact_sha256,
        "candidate artifact",
    )
    residual_parent = copy.deepcopy(parent).to("cpu")
    artifact = load_torch_checkpoint(
        str(registration.candidate_artifact_path), map_location="cpu"
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
        raise RuntimeError("action-relative candidate mutated production parent state")
    if any(parameter.device.type != "cpu" for parameter in residual.parameters()):
        raise RuntimeError("action-relative candidate residual device differs")
    return ActionRelativeLiveCandidate(
        residual=residual,
        registration=registration,
        device="cpu",
        initial_decision_count=initial_decision_count,
    )
