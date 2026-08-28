"""Eval-only live authority for a source-bound latent-gated candidate."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Mapping, Optional

import numpy as np
import torch

from spirecomm.ai.rl.checkpoint_io import load_torch_checkpoint

from .latent_gated_adapter import load_development_artifact, state_dict_sha256
from .latent_gated_live_shadow import (
    LatentGatedLiveShadow,
    _existing_trace_decision_count,
    _require_registered_file,
    _require_source_binding,
    load_live_registration,
)


REGISTRATION_ENV = "STS_COMBAT_RL_LATENT_CANDIDATE_REGISTRATION"
SOURCE_BOUND_PATHS = (
    "scripts/run_training_batch.py",
    "spirecomm/ai/rl/checkpoint_io.py",
    "spirecomm/ai/rl/v2/action_encoder.py",
    "spirecomm/ai/rl/v2/agent.py",
    "spirecomm/ai/rl/v2/id_mapping.py",
    "spirecomm/ai/rl/v2/latent_gated_adapter.py",
    "spirecomm/ai/rl/v2/latent_gated_live_candidate.py",
    "spirecomm/ai/rl/v2/latent_gated_live_shadow.py",
    "spirecomm/ai/rl/v2/network.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
)


class LatentGatedLiveCandidate(LatentGatedLiveShadow):
    """Select an adapter proposal while retaining final guard attribution."""

    def select_action(
        self,
        *,
        game: Any,
        continuous: np.ndarray,
        card_ids: np.ndarray,
        potion_ids: np.ndarray,
        relic_ids: np.ndarray,
        action_mask: np.ndarray,
        parent_action_index: int,
    ) -> int:
        parent_action_index = int(parent_action_index)
        if not self.enabled:
            return parent_action_index
        if self.budget_exhausted:
            self.record_runtime_error(
                stage="proposal",
                error=RuntimeError("candidate decision budget is exhausted"),
                game=game,
            )
            return parent_action_index
        observed = self.observe_proposal(
            game=game,
            continuous=continuous,
            card_ids=card_ids,
            potion_ids=potion_ids,
            relic_ids=relic_ids,
            action_mask=action_mask,
            parent_action_index=parent_action_index,
        )
        if not observed or self.pending is None:
            return parent_action_index

        event = self.pending.event
        candidate_eligible = bool(
            event["parent_parity"]
            and event["candidate_action_legal"]
            and event["gate_open"]
        )
        selected = (
            int(event["candidate_action_index"])
            if candidate_eligible
            else parent_action_index
        )
        event["selected_action_index"] = selected
        event["candidate_takeover_applied"] = selected != parent_action_index
        return selected


def initialize_latent_gated_live_candidate(
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
) -> Optional[LatentGatedLiveCandidate]:
    configured = registration_path
    if configured is None:
        configured = os.environ.get(REGISTRATION_ENV)
    if configured is None or not configured.strip():
        return None
    if training:
        raise ValueError("latent-gated live candidate cannot run during training")
    if not math.isclose(float(epsilon), 0.0, abs_tol=0.0):
        raise ValueError("latent-gated live candidate requires epsilon zero")
    if expert_mix_enabled:
        raise ValueError("latent-gated live candidate requires expert mix disabled")
    if not model_path:
        raise ValueError("latent-gated live candidate requires a parent checkpoint")

    registration = load_live_registration(
        configured,
        repo_root=repo_root,
        expected_mode="candidate",
        require_committed=require_committed_registration,
    )
    if require_committed_registration:
        _require_source_binding(
            registration.source_commit,
            Path(repo_root).resolve(),
            source_bound_paths=SOURCE_BOUND_PATHS,
        )
    initial_decision_count = _existing_trace_decision_count(registration)
    active_model_path = Path(model_path).resolve()
    if active_model_path != registration.production_parent_checkpoint_path:
        raise ValueError("live candidate production parent checkpoint path differs")
    _require_registered_file(
        active_model_path,
        registration.production_parent_checkpoint_sha256,
        "production parent checkpoint",
    )
    observed_parent_state = state_dict_sha256(parent.state_dict())
    if observed_parent_state != registration.parent_state_dict_sha256:
        raise ValueError("live candidate parent state identity differs")
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
    return LatentGatedLiveCandidate(
        adapter=adapter,
        registration=registration,
        source_commit=registration.source_commit,
        device=device,
        initial_decision_count=initial_decision_count,
    )
