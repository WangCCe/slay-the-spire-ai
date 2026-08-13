"""Fixed-temperature replay gate for margin-controlled card training."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_only_behavior_sensitivity_diagnostic as diagnostic
from analysis_scripts import noncombat_card_only_behavior_sensitivity_runner as behavior_runner
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_card_optimizer_replay as replay
from analysis_scripts.noncombat_card_acceptance_policy import (
    CardAcceptancePolicy,
    CardAcceptancePolicyOutput,
    _acceptance_coordinate,
    build_family_features,
)


LOGIT_TEMPERATURE = 4.0
MINIMUM_MEAN_JOINT_TOTAL_VARIATION = 0.00482559
SCHEMA_VERSION = "noncombat-card-residual-replay-gate-v1"
DEFAULT_R7_CHECKPOINT = Path(
    "reports/noncombat_card_only_native_baseline_rl_pilot_20260813_r7/checkpoint_004.json"
)
DEFAULT_BEHAVIOR_REGISTRATION = Path(
    "reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1_registration.json"
)
DEFAULT_REPLAY = Path(
    "reports/noncombat_card_scorer_optimizer_replay_ablation_20260813_r1/candidate_replay.json.gz"
)
DEFAULT_REPLAY_BINDING = Path(
    "reports/noncombat_card_scorer_optimizer_replay_ablation_20260813_r1/replay_binding.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_margin_replay_gate_20260814_r1"
)


class MarginControlledTrainingBlocked(RuntimeError):
    """Raised when the fixed margin-controlled training contract differs."""


class MarginControlledCardPolicy(CardAcceptancePolicy):
    """Frozen card policy with compressed logits and trainable residual heads."""

    def __init__(self, input_dim: int, hidden_dim: int, *, temperature: float) -> None:
        super().__init__(input_dim, hidden_dim)
        if not math.isfinite(float(temperature)) or float(temperature) <= 0.0:
            raise MarginControlledTrainingBlocked("logit temperature must be positive")
        self.logit_temperature = float(temperature)
        self.family_residual = torch.nn.Linear(hidden_dim, 1, bias=False)
        self.conditional_residual = torch.nn.Linear(hidden_dim, 1, bias=False)
        torch.nn.init.zeros_(self.family_residual.weight)
        torch.nn.init.zeros_(self.conditional_residual.weight)

    def freeze_base(self) -> None:
        for module in (self.family_head, self.conditional_ranker):
            module.eval()
            for parameter in module.parameters():
                parameter.requires_grad_(False)

    def _ranker_output(
        self,
        ranker: torch.nn.Module,
        residual: torch.nn.Linear,
        state_features: torch.Tensor,
        candidate_features: torch.Tensor,
    ) -> torch.Tensor:
        base_logits = ranker(state_features, candidate_features)
        repeated_state = state_features.unsqueeze(0).expand(
            candidate_features.shape[0], -1
        )
        combined = torch.cat((repeated_state, candidate_features), dim=1)
        hidden = torch.relu(ranker.hidden(combined)).detach()
        residual_logits = residual(hidden).squeeze(-1)
        logits = base_logits / self.logit_temperature + residual_logits
        if not torch.isfinite(logits).all().item():
            raise MarginControlledTrainingBlocked("residual logits must be finite")
        return logits

    def forward(
        self,
        state_features: torch.Tensor,
        candidate_features: torch.Tensor,
        candidates: Sequence[Mapping[str, Any]],
        *,
        category: str,
    ) -> CardAcceptancePolicyOutput:
        family_batch = build_family_features(
            candidate_features, candidates, category=category
        )
        conditional_logits = self._ranker_output(
            self.conditional_ranker,
            self.conditional_residual,
            state_features,
            candidate_features,
        )
        family_logits = self._ranker_output(
            self.family_head,
            self.family_residual,
            state_features,
            family_batch.family_features,
        )
        active, coordinate = _acceptance_coordinate(
            family_logits, family_batch.family_order
        )
        return CardAcceptancePolicyOutput(
            family_batch=family_batch,
            conditional_logits=conditional_logits,
            family_logits=family_logits,
            acceptance_active=active,
            acceptance_coordinate=coordinate,
        )


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise MarginControlledTrainingBlocked("value is not canonical JSON") from exc


def _read_canonical(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    try:
        value = json.loads(payload.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarginControlledTrainingBlocked(f"cannot read canonical JSON: {path}") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise MarginControlledTrainingBlocked(f"JSON is not canonical: {path}")
    return value


def _file_binding(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    payload = resolved.read_bytes()
    return {
        "path": resolved.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def build_margin_controlled_bootstrap(
    bootstrap: runtime.PairedBootstrap,
    *,
    temperature: float = LOGIT_TEMPERATURE,
) -> runtime.PairedBootstrap:
    source = bootstrap.candidate.card_policy
    scaled = MarginControlledCardPolicy(
        source.input_dim, source.hidden_dim, temperature=temperature
    )
    try:
        for name in ("family_head", "conditional_ranker"):
            runtime._restore_model_state(
                getattr(scaled, name),
                runtime._encode_model_state(getattr(source, name)),
                f"margin-controlled {name}",
            )
    except runtime.SuccessorRuntimeError as exc:
        raise MarginControlledTrainingBlocked(str(exc)) from exc
    scaled.freeze_base()
    return replace(
        bootstrap,
        candidate=replace(bootstrap.candidate, card_policy=scaled),
        generators={name: generator for name, generator in bootstrap.generators.items()},
    )


def residual_named_parameters(
    bootstrap: runtime.PairedBootstrap,
) -> tuple[tuple[str, torch.nn.Parameter], ...]:
    policy = bootstrap.candidate.card_policy
    if not isinstance(policy, MarginControlledCardPolicy):
        raise MarginControlledTrainingBlocked("candidate policy is not residual")
    rows = (
        ("family_residual.weight", policy.family_residual.weight),
        ("conditional_residual.weight", policy.conditional_residual.weight),
    )
    if sum(parameter.numel() for _, parameter in rows) != 128:
        raise MarginControlledTrainingBlocked("residual parameter count differs")
    return rows


def build_residual_optimizer(
    bootstrap: runtime.PairedBootstrap,
) -> torch.optim.Adam:
    return torch.optim.Adam(
        tuple(parameter for _, parameter in residual_named_parameters(bootstrap)),
        **runtime._REGISTERED_ADAM_OPTIONS,
    )


def _base_model_bytes(bootstrap: runtime.PairedBootstrap) -> tuple[bytes, ...]:
    return tuple(
        runtime._model_state_bytes(model)
        for model in (
            bootstrap.candidate.card_policy.family_head,
            bootstrap.candidate.card_policy.conditional_ranker,
            bootstrap.candidate.frozen_noncard_ranker,
            bootstrap.control.shared_card_ranker,
            bootstrap.control.frozen_noncard_ranker,
        )
    )


def _residual_bytes(bootstrap: runtime.PairedBootstrap) -> bytes:
    return _canonical_bytes(
        {
            name: runtime._encode_tensor(parameter.detach())
            for name, parameter in residual_named_parameters(bootstrap)
        }
    )


def _surface_entry_gate(
    unscaled: Sequence[Mapping[str, Any]],
    scaled: Sequence[Mapping[str, Any]],
    *,
    ordering_preserved: bool,
    temperature: float,
) -> dict[str, Any]:
    if len(unscaled) != len(scaled) or not unscaled:
        raise MarginControlledTrainingBlocked("entry surface rows differ")
    action_preserved = all(
        left["action_id"] == right["action_id"]
        and left["family"] == right["family"]
        and (left["seed"], left["decision_index"])
        == (right["seed"], right["decision_index"])
        for left, right in zip(unscaled, scaled, strict=True)
    )
    margin_ratios = [
        float(left["two_stage_margin"]) / float(right["two_stage_margin"])
        for left, right in zip(unscaled, scaled, strict=True)
        if float(right["two_stage_margin"]) > 0.0
    ]
    margin_scaled_exact = len(margin_ratios) == len(unscaled) and all(
        math.isclose(value, temperature, rel_tol=1e-5, abs_tol=1e-5)
        for value in margin_ratios
    )
    unscaled_entropy = math.fsum(float(row["joint_entropy"]) for row in unscaled)
    scaled_entropy = math.fsum(float(row["joint_entropy"]) for row in scaled)
    finite_probabilities = all(
        all(math.isfinite(float(value)) and float(value) > 0.0 for value in values)
        and math.isclose(math.fsum(float(value) for value in values), 1.0, abs_tol=1e-9)
        for row in scaled
        for values in (row["family_probabilities"], row["joint_probabilities"])
    )
    checks = {
        "entry_greedy_actions_preserved": action_preserved,
        "entry_orderings_preserved": ordering_preserved,
        "entry_joint_entropy_increased": scaled_entropy > unscaled_entropy,
        "entry_margins_scaled_exactly": margin_scaled_exact,
        "entry_probabilities_finite": finite_probabilities,
    }
    return {
        "checks": checks,
        "scaled_joint_entropy_mean": scaled_entropy / len(scaled),
        "scaled_two_stage_margin_median": diagnostic._describe(
            [float(row["two_stage_margin"]) for row in scaled]
        )["median"],
        "unscaled_joint_entropy_mean": unscaled_entropy / len(unscaled),
        "unscaled_two_stage_margin_median": diagnostic._describe(
            [float(row["two_stage_margin"]) for row in unscaled]
        )["median"],
    }


def _ordering_signature(
    bootstrap: runtime.PairedBootstrap,
    rows: Sequence[Any],
) -> tuple[dict[str, Any], ...]:
    policy = bootstrap.candidate.card_policy
    values: list[dict[str, Any]] = []
    policy.eval()
    with torch.no_grad():
        for row in rows:
            output = policy(
                row.state_features,
                row.candidate_features,
                row.candidates,
                category="card_reward",
            )

            def order(logits: torch.Tensor, indices: Sequence[int]) -> tuple[int, ...]:
                return tuple(
                    sorted(
                        indices,
                        key=lambda index: (-float(logits[index].item()), index),
                    )
                )

            family_order = order(output.family_logits, range(len(output.family_logits)))
            conditional_orders = []
            for family, indices in zip(
                output.family_batch.family_order,
                output.family_batch.family_candidate_indices,
                strict=True,
            ):
                conditional_orders.append(
                    (
                        family,
                        tuple(
                            output.family_batch.action_ids[index]
                            for index in order(output.conditional_logits, indices)
                        ),
                    )
                )
            values.append(
                {
                    "conditional": conditional_orders,
                    "decision_index": row.decision_index,
                    "family": tuple(
                        output.family_batch.family_order[index]
                        for index in family_order
                    ),
                    "seed": row.seed,
                }
            )
    return tuple(values)


def apply_replay_gate_step(
    bootstrap: runtime.PairedBootstrap,
    optimizer: torch.optim.Adam,
    decoded: replay.DecodedReplay,
    probe_rows: Sequence[Any],
) -> dict[str, Any]:
    entry_surface = diagnostic._policy_surface(bootstrap, probe_rows)
    replay.apply_generator_states(bootstrap, decoded.generator_states)
    episodes = replay.rebuild_episode_terms(bootstrap, decoded.episodes)
    baseline = runtime.build_candidate_cross_fitted_baseline(episodes)
    rows = runtime.build_arm_card_reward_rows(
        episodes, arm="candidate", baseline=baseline
    )
    objective = runtime.build_arm_card_reward_objective(rows)
    named = residual_named_parameters(bootstrap)
    frozen_before = _base_model_bytes(bootstrap)
    residual_before = _residual_bytes(bootstrap)
    generators_before = {
        name: generator.get_state().clone()
        for name, generator in bootstrap.generators.items()
    }
    try:
        prepared = runtime._prepare_arm_optimizer_step(
            optimizer,
            objective,
            parameters=tuple(parameter for _, parameter in named),
            parameter_names=tuple(name for name, _ in named),
            reconstruct_components=False,
        )
        step = runtime._commit_prepared_arm_step(optimizer, prepared)
    except runtime.SuccessorRuntimeError as exc:
        raise MarginControlledTrainingBlocked(str(exc)) from exc
    if _base_model_bytes(bootstrap) != frozen_before:
        raise MarginControlledTrainingBlocked("residual step changed frozen model bytes")
    if any(
        not torch.equal(bootstrap.generators[name].get_state(), state)
        for name, state in generators_before.items()
    ):
        raise MarginControlledTrainingBlocked("residual step changed generator state")
    final_surface = diagnostic._policy_surface(bootstrap, probe_rows)
    comparison = diagnostic._build_summary(
        diagnostic._compare_surfaces(entry_surface, final_surface)
    )
    probe = pilot.classify_card_probe(
        pilot.evaluate_card_warm_start(bootstrap, probe_rows)
    )
    checks = {
        "coverage_preserved": not bool(probe["stop"]),
        "frozen_model_exact": _base_model_bytes(bootstrap) == frozen_before,
        "function_movement_material": float(
            comparison["joint_total_variation"]["mean"]
        )
        >= MINIMUM_MEAN_JOINT_TOTAL_VARIATION,
        "optimizer_step_complete": len(step.post_parameters) == len(named),
        "residual_parameters_updated": _residual_bytes(bootstrap) != residual_before,
    }
    return {
        "checks": checks,
        "function_space": comparison,
        "objective": {
            "card_decision_count": objective.card_decision_count,
            "total_loss": float(objective.total_loss.detach()),
        },
        "optimizer": {
            "parameter_count": sum(parameter.numel() for _, parameter in named),
            "parameter_names": list(step.parameter_names),
            "postclip_global_norm": step.postclip_global_norm,
            "preclip_global_norm": step.preclip_global_norm,
        },
        "probe": probe,
    }


def execute_replay_gate(
    *,
    r7_checkpoint: Path = DEFAULT_R7_CHECKPOINT,
    behavior_registration: Path = DEFAULT_BEHAVIOR_REGISTRATION,
    replay_path: Path = DEFAULT_REPLAY,
    replay_binding_path: Path = DEFAULT_REPLAY_BINDING,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    output = output_dir.resolve()
    if output.exists():
        raise MarginControlledTrainingBlocked("replay gate output already exists")
    registration = behavior_runner.validate_registration(
        _read_canonical(behavior_registration.resolve())
    )
    probe_rows, _entry = behavior_runner._load_probe_and_entry(registration)
    expected_checkpoint = Path(
        registration["inputs"]["r7_checkpoint"]["path"]
    ).resolve()
    if r7_checkpoint.resolve() != expected_checkpoint:
        raise MarginControlledTrainingBlocked("r7 checkpoint path differs")
    unscaled_runtime = pilot.restore_card_only_residual_checkpoint(
        r7_checkpoint.resolve().read_bytes(), probe_rows=probe_rows
    )
    if unscaled_runtime.candidate_optimizer_steps != 4:
        raise MarginControlledTrainingBlocked("r7 checkpoint coordinate differs")
    scaled_bootstrap = build_margin_controlled_bootstrap(unscaled_runtime.bootstrap)
    unscaled_surface = diagnostic._policy_surface(unscaled_runtime.bootstrap, probe_rows)
    scaled_surface = diagnostic._policy_surface(scaled_bootstrap, probe_rows)
    ordering_preserved = _ordering_signature(
        unscaled_runtime.bootstrap, probe_rows
    ) == _ordering_signature(scaled_bootstrap, probe_rows)
    entry = _surface_entry_gate(
        unscaled_surface,
        scaled_surface,
        ordering_preserved=ordering_preserved,
        temperature=LOGIT_TEMPERATURE,
    )
    residual_entry = _residual_bytes(scaled_bootstrap)
    zero_residuals = all(
        torch.count_nonzero(parameter.detach()).item() == 0
        for _, parameter in residual_named_parameters(scaled_bootstrap)
    )
    entry["checks"]["entry_residuals_zero"] = zero_residuals
    binding = _read_canonical(replay_binding_path.resolve())
    decoded = replay.decode_replay(replay_path.resolve().read_bytes(), binding)
    optimizer = build_residual_optimizer(scaled_bootstrap)
    step = apply_replay_gate_step(scaled_bootstrap, optimizer, decoded, probe_rows)
    checks = {**entry["checks"], **step["checks"]}
    verdict = (
        "card_margin_replay_gate_passed"
        if all(checks.values())
        else "card_margin_replay_gate_failed"
    )
    try:
        source_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            capture_output=True,
            text=True,
            encoding="ascii",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise MarginControlledTrainingBlocked("cannot resolve source commit") from exc
    report = {
        "authority": {
            "environment_access": False,
            "fresh_evaluation": False,
            "gameplay": False,
            "promotion": False,
            "training_continuation": verdict == "card_margin_replay_gate_passed",
        },
        "checks": checks,
        "entry": entry,
        "identity": {
            "behavior_registration": _file_binding(behavior_registration),
            "replay": _file_binding(replay_path),
            "replay_binding": _file_binding(replay_binding_path),
            "source": {
                "commit": source_commit,
                "script": _file_binding(Path(__file__)),
            },
            "r7_checkpoint": _file_binding(r7_checkpoint),
        },
        "operations": {
            "environment_construction": False,
            "model_fitting": True,
            "native_loading": False,
            "optimizer_steps": 1,
            "replay_access": True,
            "fresh_seed_access": False,
            "replay_seed_access": True,
        },
        "residual_entry_sha256": hashlib.sha256(residual_entry).hexdigest(),
        "schema_version": SCHEMA_VERSION,
        "step": step,
        "temperature": LOGIT_TEMPERATURE,
        "verdict": verdict,
    }
    output.mkdir(parents=False, exist_ok=False)
    (output / "report.json").write_bytes(_canonical_bytes(report))
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r7-checkpoint", default=str(DEFAULT_R7_CHECKPOINT))
    parser.add_argument(
        "--behavior-registration", default=str(DEFAULT_BEHAVIOR_REGISTRATION)
    )
    parser.add_argument("--replay", default=str(DEFAULT_REPLAY))
    parser.add_argument("--replay-binding", default=str(DEFAULT_REPLAY_BINDING))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = execute_replay_gate(
        r7_checkpoint=Path(args.r7_checkpoint),
        behavior_registration=Path(args.behavior_registration),
        replay_path=Path(args.replay),
        replay_binding_path=Path(args.replay_binding),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps({"verdict": report["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
