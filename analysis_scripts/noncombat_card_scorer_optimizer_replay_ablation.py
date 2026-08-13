"""One-step full-Adam versus scorer-only replay ablation."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_only_behavior_sensitivity_diagnostic as diagnostic
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_card_optimizer_replay as replay
from analysis_scripts import noncombat_card_scorer_optimizer as scorer


RETAINED_MEAN_JOINT_TV_THRESHOLD = 0.80
FALSE_AUTHORITY = {
    "causal_claim": False,
    "formal_rl": False,
    "fresh_evaluation": False,
    "gameplay": False,
    "policy_quality": False,
    "production_model_loading": False,
    "promotion": False,
    "qualification": False,
    "training": False,
}


class ScorerReplayAblationBlocked(RuntimeError):
    """Raised when the registered one-step replay comparison cannot complete."""


@dataclass(frozen=True)
class CompletedScorerReplayAblation:
    full_bootstrap: runtime.PairedBootstrap
    full_optimizer: torch.optim.Adam
    scorer_bootstrap: runtime.PairedBootstrap
    scorer_optimizer: torch.optim.Adam
    full_checkpoint: bytes
    scorer_checkpoint: bytes
    telemetry: dict[str, Any]


def _objective_summary(value: runtime.ArmCardRewardObjective) -> dict[str, Any]:
    return {
        "card_decision_count": value.card_decision_count,
        "conditional_entropy_loss": float(value.conditional_entropy_loss.detach()),
        "conditional_policy_loss": float(value.conditional_policy_loss.detach()),
        "family_entropy_loss": float(value.family_entropy_loss.detach()),
        "family_policy_loss": float(value.family_policy_loss.detach()),
        "total_loss": float(value.total_loss.detach()),
    }


def _step_summary(value: runtime.ArmOptimizerStepEvidence) -> dict[str, Any]:
    delta_squares = [
        float(
            torch.sum(
                (post.detach().to(torch.float64) - pre.detach().to(torch.float64)) ** 2
            ).item()
        )
        for pre, post in zip(value.pre_parameters, value.post_parameters, strict=True)
    ]
    return {
        "model_step_l2": math.sqrt(math.fsum(delta_squares)),
        "parameter_names": list(value.parameter_names),
        "postclip_global_norm": float(value.postclip_global_norm),
        "preclip_global_norm": float(value.preclip_global_norm),
    }


def _optimizer_step_count(optimizer: torch.optim.Optimizer) -> int:
    state = optimizer.state_dict()["state"]
    steps = {
        int(float(entry["step"].item()))
        for entry in state.values()
    }
    if len(steps) != 1:
        raise ScorerReplayAblationBlocked("optimizer step coordinate differs")
    return steps.pop()


def encode_branch_checkpoint(
    bootstrap: runtime.PairedBootstrap,
    optimizer: torch.optim.Adam,
    *,
    parameter_names: Sequence[str],
    branch: str,
) -> bytes:
    names = tuple(parameter_names)
    if branch not in ("full", "scorer") or not names or len(set(names)) != len(names):
        raise ScorerReplayAblationBlocked("branch checkpoint identity differs")
    value = {
        "bootstrap": json.loads(runtime.encode_paired_bootstrap(bootstrap)),
        "branch": branch,
        "optimizer": runtime.encode_optimizer_state(optimizer),
        "optimizer_step": _optimizer_step_count(optimizer),
        "parameter_names": list(names),
        "schema_version": "noncombat-card-scorer-optimizer-branch-v1",
    }
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise ScorerReplayAblationBlocked("branch checkpoint is not canonical") from exc


def classify_result(
    *,
    reproduction_exact: bool,
    hidden_exact: bool,
    guarded_exact: bool,
    branch_coverage: bool,
    full_summary: Mapping[str, Any],
    scorer_summary: Mapping[str, Any],
) -> dict[str, Any]:
    full_tv = float(full_summary["joint_total_variation"]["mean"])
    scorer_tv = float(scorer_summary["joint_total_variation"]["mean"])
    if not all(math.isfinite(value) and value >= 0.0 for value in (full_tv, scorer_tv)):
        raise ScorerReplayAblationBlocked("function-space movement is invalid")
    retained = None if full_tv == 0.0 else scorer_tv / full_tv
    checks = {
        "branch_coverage": bool(branch_coverage),
        "full_reproduction_exact": bool(reproduction_exact),
        "full_mean_joint_tv_positive": full_tv > 0.0,
        "scorer_guarded_models_exact": bool(guarded_exact),
        "scorer_hidden_exact": bool(hidden_exact),
        "scorer_retained_mean_joint_tv": retained is not None
        and retained >= RETAINED_MEAN_JOINT_TV_THRESHOLD,
    }
    ready = all(checks.values())
    if not reproduction_exact:
        verdict = "scorer_optimizer_ablation_reproduction_failed"
    elif not hidden_exact or not guarded_exact:
        verdict = "scorer_hidden_freeze_failed"
    elif not branch_coverage:
        verdict = "scorer_optimizer_ablation_branch_collapse"
    elif ready:
        verdict = "ready_to_propose_four_step_scorer_optimizer_ablation"
    else:
        verdict = "scorer_only_optimizer_not_ready"
    return {
        "checks": checks,
        "full_mean_joint_tv": full_tv,
        "retained_mean_joint_tv_ratio": retained,
        "scorer_mean_joint_tv": scorer_tv,
        "threshold": RETAINED_MEAN_JOINT_TV_THRESHOLD,
        "verdict": verdict,
    }


def apply_decoded_replay_ablation(
    *,
    full_bootstrap: runtime.PairedBootstrap,
    full_optimizer: torch.optim.Adam,
    scorer_bootstrap: runtime.PairedBootstrap,
    scorer_source_optimizer: torch.optim.Adam,
    decoded: replay.DecodedReplay,
    expected_full_bootstrap: bytes,
    expected_full_optimizer: Mapping[str, Any],
    probe_rows: Sequence[Any],
) -> CompletedScorerReplayAblation:
    """Prepare both branches from decoded replay, then commit one step each."""
    try:
        full_names_and_parameters = runtime._arm_named_trainable_parameters(
            full_bootstrap, arm="candidate"
        )
        scorer_names_and_parameters = runtime._arm_named_trainable_parameters(
            scorer_bootstrap, arm="candidate"
        )
        if tuple(name for name, _ in full_names_and_parameters) != tuple(
            name for name, _ in scorer_names_and_parameters
        ):
            raise ScorerReplayAblationBlocked("branch parameter identity differs")
        if pilot.encode_candidate_card_policy(full_bootstrap) != pilot.encode_candidate_card_policy(
            scorer_bootstrap
        ) or runtime.encode_optimizer_state(full_optimizer) != runtime.encode_optimizer_state(
            scorer_source_optimizer
        ):
            raise ScorerReplayAblationBlocked("branch entry state differs")
        if len(probe_rows) != 175:
            raise ScorerReplayAblationBlocked("fixed probe row count differs")

        entry_surface = diagnostic._policy_surface(full_bootstrap, probe_rows)
        replay.apply_generator_states(full_bootstrap, decoded.generator_states)
        replay.apply_generator_states(scorer_bootstrap, decoded.generator_states)
        selected = scorer.build_scorer_optimizer(
            scorer_bootstrap, scorer_source_optimizer
        )
        hidden_before = scorer.candidate_hidden_parameter_bytes(scorer_bootstrap)
        guarded_before = scorer.candidate_guarded_model_bytes(scorer_bootstrap)

        full_episodes = replay.rebuild_episode_terms(full_bootstrap, decoded.episodes)
        scorer_episodes = replay.rebuild_episode_terms(scorer_bootstrap, decoded.episodes)
        baseline = runtime.build_candidate_cross_fitted_baseline(full_episodes)
        full_rows = runtime.build_arm_card_reward_rows(
            full_episodes, arm="candidate", baseline=baseline
        )
        scorer_rows = runtime.build_arm_card_reward_rows(
            scorer_episodes, arm="candidate", baseline=baseline
        )
        if tuple(float(value) for _, value in full_rows) != tuple(
            float(value) for _, value in scorer_rows
        ) or tuple(row[0].selected_action_id for row in full_rows) != tuple(
            row[0].selected_action_id for row in scorer_rows
        ):
            raise ScorerReplayAblationBlocked("branch objective rows differ")
        full_objective = runtime.build_arm_card_reward_objective(full_rows)
        scorer_objective = runtime.build_arm_card_reward_objective(scorer_rows)

        full_prepared = runtime._prepare_arm_optimizer_step(
            full_optimizer,
            full_objective,
            parameters=tuple(parameter for _, parameter in full_names_and_parameters),
            parameter_names=tuple(name for name, _ in full_names_and_parameters),
            reconstruct_components=False,
        )
        scorer_prepared = runtime._prepare_arm_optimizer_step(
            selected.optimizer,
            scorer_objective,
            parameters=selected.parameters,
            parameter_names=selected.parameter_names,
            reconstruct_components=False,
        )
        full_step = runtime._commit_prepared_arm_step(full_optimizer, full_prepared)
        scorer_step = runtime._commit_prepared_arm_step(
            selected.optimizer, scorer_prepared
        )

        hidden_exact = scorer.candidate_hidden_parameter_bytes(scorer_bootstrap) == hidden_before
        guarded_exact = scorer.candidate_guarded_model_bytes(scorer_bootstrap) == guarded_before
        bootstrap_exact = runtime.encode_paired_bootstrap(full_bootstrap) == expected_full_bootstrap
        optimizer_exact = runtime.encode_optimizer_state(full_optimizer) == dict(
            expected_full_optimizer
        )
        reproduction_exact = bootstrap_exact and optimizer_exact
        full_surface = diagnostic._policy_surface(full_bootstrap, probe_rows)
        scorer_surface = diagnostic._policy_surface(scorer_bootstrap, probe_rows)
        full_function_rows = diagnostic._compare_surfaces(entry_surface, full_surface)
        scorer_function_rows = diagnostic._compare_surfaces(entry_surface, scorer_surface)
        full_summary = diagnostic._build_summary(full_function_rows)
        scorer_summary = diagnostic._build_summary(scorer_function_rows)
        full_probe = pilot.classify_card_probe(
            pilot.evaluate_card_warm_start(full_bootstrap, probe_rows)
        )
        scorer_probe = pilot.classify_card_probe(
            pilot.evaluate_card_warm_start(scorer_bootstrap, probe_rows)
        )
        branch_coverage = not bool(full_probe["stop"]) and not bool(
            scorer_probe["stop"]
        )
        classification = classify_result(
            reproduction_exact=reproduction_exact,
            hidden_exact=hidden_exact,
            guarded_exact=guarded_exact,
            branch_coverage=branch_coverage,
            full_summary=full_summary,
            scorer_summary=scorer_summary,
        )

        full_names = tuple(name for name, _ in full_names_and_parameters)
        full_checkpoint = encode_branch_checkpoint(
            full_bootstrap,
            full_optimizer,
            parameter_names=full_names,
            branch="full",
        )
        scorer_checkpoint = encode_branch_checkpoint(
            scorer_bootstrap,
            selected.optimizer,
            parameter_names=selected.parameter_names,
            branch="scorer",
        )
        telemetry = {
            "classification": classification,
            "downstream_authority": copy.deepcopy(FALSE_AUTHORITY),
            "function_space": {
                "full": {"rows": list(full_function_rows), "summary": full_summary},
                "scorer": {
                    "rows": list(scorer_function_rows),
                    "summary": scorer_summary,
                },
            },
            "probe_gate": {"full": full_probe, "scorer": scorer_probe},
            "objective": {
                "full": _objective_summary(full_objective),
                "scorer": _objective_summary(scorer_objective),
            },
            "reproduction": {
                "bootstrap_exact": bootstrap_exact,
                "exact": reproduction_exact,
                "optimizer_exact": optimizer_exact,
            },
            "steps": {
                "full": _step_summary(full_step),
                "scorer": _step_summary(scorer_step),
            },
            "scorer_hidden_exact": hidden_exact,
            "scorer_guarded_models_exact": guarded_exact,
        }
        return CompletedScorerReplayAblation(
            full_bootstrap=full_bootstrap,
            full_optimizer=full_optimizer,
            scorer_bootstrap=scorer_bootstrap,
            scorer_optimizer=selected.optimizer,
            full_checkpoint=full_checkpoint,
            scorer_checkpoint=scorer_checkpoint,
            telemetry=telemetry,
        )
    except (
        diagnostic.FunctionSpaceDiagnosticBlocked,
        pilot.CardOnlyPilotBlocked,
        replay.CardOptimizerReplayBlocked,
        runtime.SuccessorRuntimeError,
        scorer.ScorerOptimizerBlocked,
    ) as exc:
        raise ScorerReplayAblationBlocked(str(exc)) from exc


__all__ = [
    "CompletedScorerReplayAblation",
    "FALSE_AUTHORITY",
    "RETAINED_MEAN_JOINT_TV_THRESHOLD",
    "ScorerReplayAblationBlocked",
    "apply_decoded_replay_ablation",
    "classify_result",
    "encode_branch_checkpoint",
]
