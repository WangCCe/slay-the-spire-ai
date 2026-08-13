"""Evaluate the frozen card-uplift residual on fresh paired simulator runs."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import types
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any


def _bootstrap_direct_script_imports() -> None:
    if __package__:
        return
    repo_root = Path(__file__).resolve().parents[1]
    package_root = repo_root / "analysis_scripts"
    package = types.ModuleType("analysis_scripts")
    package.__file__ = str(package_root / "__init__.py")
    package.__package__ = "analysis_scripts"
    package.__path__ = [str(package_root)]
    package.__spec__ = importlib.util.spec_from_loader(
        "analysis_scripts", loader=None, is_package=True
    )
    sys.modules["analysis_scripts"] = package
    sys.path.append(str(repo_root))


if __name__ == "__main__":
    _bootstrap_direct_script_imports()


REGISTRATION_SCHEMA_VERSION = (
    "noncombat-card-uplift-fresh-simulator-evaluation-registration-v1"
)
_EARLY_NATIVE_HANDLES: list[Any] = []


def _is_direct_worker_invocation() -> bool:
    return (
        len(sys.argv) >= 2
        and sys.argv[1] == "run-worker"
        and Path(sys.argv[0]).resolve() == Path(__file__).resolve()
    )


def _early_preload_native() -> None:
    if not _is_direct_worker_invocation():
        return
    try:
        registration_path = Path(
            sys.argv[sys.argv.index("--registration") + 1]
        ).resolve()
        registration = json.loads(registration_path.read_text(encoding="ascii"))
        if registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
            raise RuntimeError("fresh evaluation registration schema differs")
        native = registration["native"]["identity"]
        module_path = Path(native["module"]["path"]).resolve()
        dependencies = {
            Path(binding["path"]).name.casefold(): Path(binding["path"]).resolve()
            for binding in native["dependency_closure"]["dependencies"]
        }
        imports_by_path = {
            Path(row["path"]).resolve(): tuple(
                str(name).casefold() for name in row["imports"]
            )
            for row in native["dependency_closure"]["imports"]
        }
        order: list[Path] = []
        visiting: set[Path] = set()
        visited: set[Path] = set()

        def visit(path: Path) -> None:
            if path in visiting:
                raise RuntimeError("fresh evaluation dependency cycle differs")
            if path in visited:
                return
            visiting.add(path)
            for name in imports_by_path.get(path, ()):
                dependency = dependencies.get(name)
                if dependency is not None:
                    visit(dependency)
            visiting.remove(path)
            visited.add(path)
            if path != module_path:
                order.append(path)

        visit(module_path)
        if set(order) != set(dependencies.values()):
            raise RuntimeError("fresh evaluation dependency graph differs")
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        load_library = kernel32.LoadLibraryExW
        load_library.argtypes = (wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD)
        load_library.restype = wintypes.HMODULE
        for path in order:
            handle = load_library(str(path), None, 0x00000100 | 0x00000400)
            if not handle:
                raise OSError(
                    ctypes.get_last_error(), "LoadLibraryExW failed", str(path)
                )
            _EARLY_NATIVE_HANDLES.append(int(handle))
        for directory in native["dll_directories"]:
            _EARLY_NATIVE_HANDLES.append(os.add_dll_directory(directory))
        spec = importlib.util.spec_from_file_location(
            "sts_lightspeed_noncombat_adapter", module_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("fresh evaluation native spec is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.adapter_api_version() != "sts-lightspeed-noncombat-adapter-v3":
            raise RuntimeError("fresh evaluation native API differs")
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("fresh evaluation early native load failed") from exc


_early_preload_native()


from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_ranking_training_runner as base_runner
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as uplift
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner
from analysis_scripts import noncombat_large_corpus_card_uplift_residual_audit_runner as audit_runner
from analysis_scripts import noncombat_simulator_adapter as adapter
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    PolicyInputError,
    project_state_conditioned_policy_input,
)


PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-card-uplift-fresh-simulator-evaluation-preflight-v1"
)
TRAJECTORY_SCHEMA_VERSION = (
    "noncombat-card-uplift-fresh-simulator-evaluation-trajectories-v1"
)
METRICS_SCHEMA_VERSION = (
    "noncombat-card-uplift-fresh-simulator-evaluation-metrics-v1"
)
REPORT_SCHEMA_VERSION = (
    "noncombat-card-uplift-fresh-simulator-evaluation-report-v1"
)
TERMINAL_SCHEMA_VERSION = (
    "noncombat-card-uplift-fresh-simulator-evaluation-terminal-v1"
)
FRESH_SEEDS = tuple(range(90100, 90164))
EXCLUDED_SEED_RANGES = (
    {"end": 1031, "reason": "predecessor-card-fit-and-holdout", "start": 1000},
    {"end": 80383, "reason": "large-corpus-train-development-audit", "start": 80000},
    {"end": 90063, "reason": "failed-fresh-evaluation-r1", "start": 90000},
)
MAX_PAIRED_SEEDS = 64
MAX_EPISODE_ROLLOUTS = 128
MAX_DECISIONS_PER_EPISODE = 500
MAX_CENSORED_PAIRS = 8
MIN_COMPLETE_PAIRS = 56
MIN_CARD_INTERVENTIONS = 12
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20_260_813
MIN_BOOTSTRAP_LOWER_BOUND = -2.0
MAX_WALL_SECONDS = 7_200.0
MAX_TRAJECTORY_BYTES = 32 * 1024 * 1024
DEFAULT_AUDIT_ROOT = Path(
    "reports/noncombat_large_corpus_card_uplift_residual_audit_20260813_r1"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_uplift_fresh_simulator_evaluation_20260813_r2"
)
BOUND_SOURCE_PATHS = tuple(
    sorted(
        {
            *audit_runner.BOUND_SOURCE_PATHS,
            "analysis_scripts/noncombat_card_uplift_fresh_simulator_evaluation.py",
        }
    )
)
AUTHORITY = {
    name: False
    for name in (
        "causal_claim",
        "communication_mod",
        "formal_rl",
        "gameplay",
        "ope",
        "policy_quality",
        "production_model_loading",
        "promotion",
        "qualification",
        "training",
    )
}
OPERATIONS = {
    "communication_mod": False,
    "environment_construction": True,
    "fresh_simulator_evaluation": True,
    "gameplay": False,
    "model_fitting": False,
    "model_loading": True,
    "native_loading": True,
    "ope": False,
    "production_model_loading": False,
    "seed_access": True,
    "training": False,
}


class FreshSimulatorEvaluationBlocked(RuntimeError):
    """Raised when the registered fresh evaluation cannot proceed."""


def _configuration() -> dict[str, Any]:
    return {
        "bootstrap": {
            "lower_quantile": 0.025,
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
            "upper_quantile": 0.975,
        },
        "gates": {
            "candidate_victories_at_least_control": True,
            "maximum_censored_pairs": MAX_CENSORED_PAIRS,
            "minimum_bootstrap_lower_bound": MIN_BOOTSTRAP_LOWER_BOUND,
            "minimum_card_interventions": MIN_CARD_INTERVENTIONS,
            "minimum_complete_pairs": MIN_COMPLETE_PAIRS,
            "minimum_mean_paired_floor_difference": 0.0,
        },
        "maximum_decisions_per_episode": MAX_DECISIONS_PER_EPISODE,
        "maximum_episode_rollouts": MAX_EPISODE_ROLLOUTS,
        "maximum_paired_seeds": MAX_PAIRED_SEEDS,
        "maximum_trajectory_bytes": MAX_TRAJECTORY_BYTES,
        "maximum_wall_seconds": MAX_WALL_SECONDS,
        "residual_configuration": {"shrinkage": 1, "strength": 128},
    }


def _source_bindings(root: Path, source_commit: str) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    for relative in BOUND_SOURCE_PATHS:
        actual = pilot_runner._file_binding(root / relative)
        try:
            committed = subprocess.run(
                ["git", "show", f"{source_commit}:{relative}"],
                cwd=root,
                check=True,
                capture_output=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise FreshSimulatorEvaluationBlocked(
                f"source path is unavailable at commit: {relative}"
            ) from exc
        if hashlib.sha256(committed).hexdigest() != actual["sha256"]:
            raise FreshSimulatorEvaluationBlocked(f"source bytes differ: {relative}")
        bindings[relative] = actual
    return bindings


def _inputs(audit_root: Path, audit_registration: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "audit_dataset": pilot_runner._file_binding(
            audit_root / "audit_dataset_full.json"
        ),
        "audit_registration": pilot_runner._file_binding(
            audit_root / "registration.json"
        ),
        "audit_report": pilot_runner._file_binding(audit_root / "report.json"),
        "audit_terminal": pilot_runner._file_binding(audit_root / "terminal.json"),
        "corpus_report": copy.deepcopy(audit_registration["inputs"]["corpus_report"]),
        "entry_checkpoint": copy.deepcopy(
            audit_registration["inputs"]["entry_checkpoint"]
        ),
        "residual_model": pilot_runner._file_binding(
            audit_root / "residual_model.json"
        ),
    }


def build_registration(
    *,
    repo_root: Path | str,
    source_commit: str,
    audit_root: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    audit_path = Path(audit_root).resolve()
    audit_registration = base_runner._read_canonical(
        audit_path / "registration.json"
    )
    audit_report = base_runner._read_canonical(audit_path / "report.json")
    audit_terminal = base_runner._read_canonical(audit_path / "terminal.json")
    expected = (
        "large_corpus_card_uplift_residual_audit_ready_for_fresh_eval_proposal"
    )
    if audit_report.get("verdict") != expected or audit_terminal.get("verdict") != expected:
        raise FreshSimulatorEvaluationBlocked("predecessor audit verdict differs")
    try:
        if pilot_runner._git(root, "cat-file", "-t", source_commit) != "commit":
            raise FreshSimulatorEvaluationBlocked("source commit is unavailable")
    except pilot_runner.CardOnlyRunnerBlocked as exc:
        raise FreshSimulatorEvaluationBlocked("source commit is unavailable") from exc
    output = Path(output_dir).resolve()
    checkpoint_root = base_runner.PRODUCTION_CHECKPOINT_ROOT.resolve()
    if output == checkpoint_root or checkpoint_root in output.parents:
        raise FreshSimulatorEvaluationBlocked("output overlaps production checkpoints")
    return validate_registration(
        {
            "authority": copy.deepcopy(AUTHORITY),
            "configuration": _configuration(),
            "inputs": _inputs(audit_path, audit_registration),
            "native": copy.deepcopy(audit_registration["native"]),
            "operations": copy.deepcopy(OPERATIONS),
            "output_dir": output.as_posix(),
            "production_isolation": copy.deepcopy(
                audit_registration["production_isolation"]
            ),
            "schedule": {
                "excluded_seed_ranges": copy.deepcopy(list(EXCLUDED_SEED_RANGES)),
                "fresh_seeds": list(FRESH_SEEDS),
                "seed_status": "untouched-fresh-paired-evaluation",
            },
            "schema_version": REGISTRATION_SCHEMA_VERSION,
            "source": {
                "bindings": _source_bindings(root, source_commit),
                "commit": source_commit,
                "repo_root": root.as_posix(),
            },
        }
    )


def validate_registration(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise FreshSimulatorEvaluationBlocked("registration must be an object")
    registration = copy.deepcopy(dict(value))
    if set(registration) != {
        "authority",
        "configuration",
        "inputs",
        "native",
        "operations",
        "output_dir",
        "production_isolation",
        "schedule",
        "schema_version",
        "source",
    } or registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
        raise FreshSimulatorEvaluationBlocked("registration fields differ")
    if registration["authority"] != AUTHORITY:
        raise FreshSimulatorEvaluationBlocked("authority differs")
    if registration["configuration"] != _configuration():
        raise FreshSimulatorEvaluationBlocked("configuration differs")
    if registration["operations"] != OPERATIONS:
        raise FreshSimulatorEvaluationBlocked("operations differ")
    expected_schedule = {
        "excluded_seed_ranges": copy.deepcopy(list(EXCLUDED_SEED_RANGES)),
        "fresh_seeds": list(FRESH_SEEDS),
        "seed_status": "untouched-fresh-paired-evaluation",
    }
    if registration["schedule"] != expected_schedule:
        raise FreshSimulatorEvaluationBlocked("schedule differs")
    inputs = registration.get("inputs")
    expected_inputs = {
        "audit_dataset",
        "audit_registration",
        "audit_report",
        "audit_terminal",
        "corpus_report",
        "entry_checkpoint",
        "residual_model",
    }
    if not isinstance(inputs, dict) or set(inputs) != expected_inputs:
        raise FreshSimulatorEvaluationBlocked("inputs differ")
    source = registration.get("source")
    if (
        not isinstance(source, dict)
        or set(source) != {"bindings", "commit", "repo_root"}
        or set(source.get("bindings", {})) != set(BOUND_SOURCE_PATHS)
        or not isinstance(source.get("commit"), str)
        or len(source["commit"]) != 40
    ):
        raise FreshSimulatorEvaluationBlocked("source differs")
    bindings = [*inputs.values(), *source["bindings"].values()]
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in bindings
    ):
        raise FreshSimulatorEvaluationBlocked("file bindings differ")
    native = registration.get("native")
    identity = native.get("identity") if isinstance(native, dict) else None
    if not isinstance(identity, dict) or identity.get(
        "adapter_api_version"
    ) != adapter.ADAPTER_API_VERSION:
        raise FreshSimulatorEvaluationBlocked("native identity differs")
    if not isinstance(registration.get("output_dir"), str):
        raise FreshSimulatorEvaluationBlocked("output differs")
    return registration


def _binding_matches(binding: Mapping[str, Any]) -> bool:
    return pilot_runner._file_binding(binding["path"]) == dict(binding)


def _same_bytes(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return (
        left.get("sha256") == right.get("sha256")
        and left.get("size_bytes") == right.get("size_bytes")
    )


def _load_frozen_inputs(
    registration: Mapping[str, Any],
) -> tuple[Any, uplift.UpliftModel, uplift.ResidualConfiguration, bytes, bytes]:
    inputs = registration["inputs"]
    try:
        entry_bytes = Path(inputs["entry_checkpoint"]["path"]).read_bytes()
        bootstrap = ranking.restore_entry_bootstrap(entry_bytes)
        model_bytes = Path(inputs["residual_model"]["path"]).read_bytes()
        model, configuration = uplift.restore_uplift_model(model_bytes)
    except (OSError, ranking.CounterfactualRankingBlocked, uplift.UpliftCrossfitBlocked) as exc:
        raise FreshSimulatorEvaluationBlocked(str(exc)) from exc
    if configuration != uplift.ResidualConfiguration(shrinkage=1, strength=128):
        raise FreshSimulatorEvaluationBlocked("frozen configuration differs")
    return bootstrap, model, configuration, entry_bytes, model_bytes


def preflight_registration(
    value: Mapping[str, Any],
    *,
    process_observer: Callable[[], Sequence[Mapping[str, Any]]] = (
        pilot_runner._forbidden_processes
    ),
) -> dict[str, Any]:
    registration = validate_registration(value)
    source = registration["source"]
    root = Path(source["repo_root"]).resolve()
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source["commit"], "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FreshSimulatorEvaluationBlocked(
            "registered source is not an ancestor"
        ) from exc
    if _source_bindings(root, source["commit"]) != source["bindings"] or any(
        not _binding_matches(binding) for binding in registration["inputs"].values()
    ):
        raise FreshSimulatorEvaluationBlocked("registered source or input bytes differ")
    inputs = registration["inputs"]
    audit_registration = base_runner._read_canonical(
        inputs["audit_registration"]["path"]
    )
    audit_report = base_runner._read_canonical(inputs["audit_report"]["path"])
    audit_terminal = base_runner._read_canonical(inputs["audit_terminal"]["path"])
    corpus_report = base_runner._read_canonical(inputs["corpus_report"]["path"])
    expected = (
        "large_corpus_card_uplift_residual_audit_ready_for_fresh_eval_proposal"
    )
    used_seeds = {
        *corpus_report.get("schedule", {}).get("train_seeds", []),
        *corpus_report.get("schedule", {}).get("development_seeds", []),
        *corpus_report.get("schedule", {}).get("reserved_audit_seeds", []),
        *range(1000, 1032),
    }
    if (
        audit_registration.get("schema_version")
        != audit_runner.REGISTRATION_SCHEMA_VERSION
        or audit_report.get("verdict") != expected
        or audit_terminal.get("verdict") != expected
        or audit_terminal.get("report") != inputs["audit_report"]
        or audit_report.get("audit_dataset") != inputs["audit_dataset"]
        or audit_registration.get("inputs", {}).get("entry_checkpoint")
        != inputs["entry_checkpoint"]
        or audit_registration.get("inputs", {}).get("corpus_report")
        != inputs["corpus_report"]
        or not _same_bytes(
            audit_registration.get("inputs", {}).get("residual_model", {}),
            inputs["residual_model"],
        )
        or audit_registration.get("native") != registration["native"]
        or audit_registration.get("production_isolation")
        != registration["production_isolation"]
        or set(FRESH_SEEDS) & used_seeds
    ):
        raise FreshSimulatorEvaluationBlocked("audit or cohort lineage differs")
    _load_frozen_inputs(registration)
    native = registration["native"]["identity"]
    if any(
        not _binding_matches(binding)
        for binding in [
            native["module"],
            *native["dependency_closure"]["dependencies"],
        ]
    ):
        raise FreshSimulatorEvaluationBlocked("native bytes differ")
    if not base_runner.production_isolation_matches(registration):
        raise FreshSimulatorEvaluationBlocked("production isolation differs")
    if list(process_observer()):
        raise FreshSimulatorEvaluationBlocked("game or CommunicationMod is active")
    output = Path(registration["output_dir"]).resolve()
    staging = output.with_name(f".{output.name}.{source['commit']}.staging")
    checkpoint_root = Path(
        registration["production_isolation"]["production_checkpoints"]["path"]
    ).resolve()
    if (
        output.exists()
        or staging.exists()
        or output == checkpoint_root
        or checkpoint_root in output.parents
    ):
        raise FreshSimulatorEvaluationBlocked("output boundary differs")
    return {
        "checks": {
            "forbidden_processes_absent": True,
            "fresh_cohort_disjoint": True,
            "frozen_inputs_restorable_without_fitting": True,
            "native_bytes_bound_without_loading": True,
            "production_isolation_bound": True,
            "source_and_lineage_bound": True,
        },
        "registration_sha256": hashlib.sha256(
            base_runner._canonical_bytes(registration)
        ).hexdigest(),
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "verdict": "preflight_passed",
    }


def _source_sha256(
    snapshot: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> str:
    return hashlib.sha256(
        adapter.canonical_json_bytes(
            {"candidate_actions": list(candidates), "snapshot": dict(snapshot)}
        )
    ).hexdigest()


def _choose_index(
    scores: Sequence[float], candidates: Sequence[Mapping[str, Any]]
) -> int:
    normalized = tuple(float(value) for value in scores)
    if (
        not normalized
        or len(normalized) != len(candidates)
        or any(not math.isfinite(value) for value in normalized)
    ):
        raise FreshSimulatorEvaluationBlocked("candidate scores differ")
    maximum = max(normalized)
    return min(
        (index for index, value in enumerate(normalized) if value == maximum),
        key=lambda index: str(candidates[index]["action_id"]),
    )


def _candidate_card_step(
    environment: Any,
    *,
    bootstrap: Any,
    model: uplift.UpliftModel,
    configuration: uplift.ResidualConfiguration,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    snapshot, candidates = credit._environment_state(environment)
    if snapshot["category"] != "card_reward" or tuple(
        candidate.get("kind") for candidate in candidates
    ) != ("take", "take", "take", "skip"):
        raise FreshSimulatorEvaluationBlocked("card action boundary differs")
    try:
        policy_input = project_state_conditioned_policy_input(snapshot, candidates)
    except PolicyInputError as exc:
        raise FreshSimulatorEvaluationBlocked(str(exc)) from exc
    source_sha256 = _source_sha256(snapshot, candidates)
    row = ranking.CounterfactualRankingRow(
        seed=0,
        decision_index=0,
        source_sha256=source_sha256,
        state_features=policy_input.state_features.detach().clone(),
        candidate_features=policy_input.candidate_features.detach().clone(),
        candidates=tuple(copy.deepcopy(candidates)),
        action_returns=(0.0, 0.0, 0.0, 0.0),
    )
    with ranking.torch.no_grad():
        base_scores = tuple(
            float(value)
            for value in ranking._joint_log_probabilities(bootstrap, row)
            .detach()
            .tolist()
        )
    scores, unseen = uplift.compose_scores(
        row, base_scores, model, strength=configuration.strength
    )
    selected_index = _choose_index(scores, candidates)
    selected_action_id = str(candidates[selected_index]["action_id"])
    _, native_transition = credit._advance_native(environment)
    native_action_id = str(native_transition["selected_action_id"])
    successor, transition = credit._apply_forced_action(
        environment, selected_action_id
    )
    return successor, transition, {
        "base_scores": list(base_scores),
        "candidate_action_id": selected_action_id,
        "intervened": selected_action_id != native_action_id,
        "native_action_id": native_action_id,
        "scores": list(scores),
        "source_sha256": source_sha256,
        "unseen_take_actions": unseen,
    }


def _is_supported_card_reward(
    candidates: Sequence[Mapping[str, Any]],
) -> bool:
    return tuple(candidate.get("kind") for candidate in candidates) == (
        "take",
        "take",
        "take",
        "skip",
    )


def _check_deadline(deadline: float, clock: Callable[[], float]) -> None:
    if float(clock()) > deadline:
        raise FreshSimulatorEvaluationBlocked("wall-time bound exceeded")


def _rollout_episode(
    environment_factory: Callable[[int], Any],
    *,
    seed: int,
    arm: str,
    bootstrap: Any,
    model: uplift.UpliftModel,
    configuration: uplift.ResidualConfiguration,
    deadline: float,
    clock: Callable[[], float],
) -> dict[str, Any]:
    if arm not in {"control", "candidate"}:
        raise FreshSimulatorEvaluationBlocked("rollout arm differs")
    try:
        environment = environment_factory(seed)
    except Exception as exc:
        raise FreshSimulatorEvaluationBlocked(
            f"seed {seed} environment construction failed"
        ) from exc
    actions: list[dict[str, Any]] = []
    categories: Counter[str] = Counter()
    card_rows: list[dict[str, Any]] = []
    native_card_fallbacks = 0
    while True:
        _check_deadline(deadline, clock)
        snapshot, candidates = credit._environment_state(environment)
        if snapshot["terminal"]:
            break
        if len(actions) >= MAX_DECISIONS_PER_EPISODE:
            raise FreshSimulatorEvaluationBlocked(
                f"seed {seed} exceeded decision ceiling"
            )
        category = str(snapshot["category"])
        categories[category] += 1
        try:
            if (
                arm == "candidate"
                and category == "card_reward"
                and _is_supported_card_reward(candidates)
            ):
                environment, transition, card_row = _candidate_card_step(
                    environment,
                    bootstrap=bootstrap,
                    model=model,
                    configuration=configuration,
                )
                card_rows.append(card_row)
            else:
                native_card_fallbacks += int(
                    arm == "candidate" and category == "card_reward"
                )
                environment, transition = credit._advance_native(environment)
        except credit.CounterfactualCreditBlocked as exc:
            reason = ranking.registered_support_blocker(exc)
            if reason is None:
                raise FreshSimulatorEvaluationBlocked(str(exc)) from exc
            return {
                "action_sequence_sha256": hashlib.sha256(
                    adapter.canonical_json_bytes(actions)
                ).hexdigest(),
                "actions": actions,
                "arm": arm,
                "card_decisions": card_rows,
                "card_interventions": sum(row["intervened"] for row in card_rows),
                "categories": dict(sorted(categories.items())),
                "decisions": len(actions),
                "native_card_fallbacks": native_card_fallbacks,
                "outcome": None,
                "seed": seed,
                "status": "censored",
                "terminal_floor": None,
                "unsupported_reason": reason,
                "victory": False,
            }
        selected_action_id = str(transition["selected_action_id"])
        if selected_action_id not in {
            str(candidate["action_id"]) for candidate in candidates
        }:
            raise FreshSimulatorEvaluationBlocked("selected action is not legal")
        actions.append(
            {
                "action_id": selected_action_id,
                "category": category,
                "decision_index": len(actions),
                "source_sha256": _source_sha256(snapshot, candidates),
                "transition_sha256": hashlib.sha256(
                    adapter.canonical_json_bytes(transition)
                ).hexdigest(),
            }
        )
    state = snapshot.get("state")
    outcome = state.get("outcome") if isinstance(state, Mapping) else None
    floor_value = state.get("floor") if isinstance(state, Mapping) else None
    try:
        terminal_floor = float(floor_value)
    except (TypeError, ValueError) as exc:
        raise FreshSimulatorEvaluationBlocked("terminal floor differs") from exc
    if outcome not in {"player_loss", "player_victory"} or not math.isfinite(
        terminal_floor
    ):
        raise FreshSimulatorEvaluationBlocked("terminal outcome differs")
    return {
        "action_sequence_sha256": hashlib.sha256(
            adapter.canonical_json_bytes(actions)
        ).hexdigest(),
        "actions": actions,
        "arm": arm,
        "card_decisions": card_rows,
        "card_interventions": sum(row["intervened"] for row in card_rows),
        "categories": dict(sorted(categories.items())),
        "decisions": len(actions),
        "native_card_fallbacks": native_card_fallbacks,
        "outcome": str(outcome),
        "seed": seed,
        "status": "complete",
        "terminal_floor": terminal_floor,
        "unsupported_reason": None,
        "victory": outcome == "player_victory",
    }


def _percentile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered or not 0.0 <= quantile <= 1.0:
        raise FreshSimulatorEvaluationBlocked("percentile inputs differ")
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _bootstrap_interval(differences: Sequence[float]) -> dict[str, float]:
    values = tuple(float(value) for value in differences)
    if not values or any(not math.isfinite(value) for value in values):
        raise FreshSimulatorEvaluationBlocked("bootstrap differences differ")
    generator = random.Random(BOOTSTRAP_SEED)
    means = [
        math.fsum(values[generator.randrange(len(values))] for _ in values)
        / len(values)
        for _ in range(BOOTSTRAP_RESAMPLES)
    ]
    return {
        "lower": _percentile(means, 0.025),
        "upper": _percentile(means, 0.975),
    }


def evaluate_pairs(pairs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = tuple(copy.deepcopy(list(pairs)))
    if len(normalized) != len(FRESH_SEEDS) or [
        row.get("seed") for row in normalized
    ] != list(FRESH_SEEDS):
        raise FreshSimulatorEvaluationBlocked("pair schedule differs")
    complete: list[dict[str, Any]] = []
    censored: list[dict[str, Any]] = []
    for pair in normalized:
        control = pair.get("control")
        candidate = pair.get("candidate")
        if not isinstance(control, dict) or not isinstance(candidate, dict):
            raise FreshSimulatorEvaluationBlocked("pair arms differ")
        if control.get("seed") != pair["seed"] or candidate.get("seed") != pair["seed"]:
            raise FreshSimulatorEvaluationBlocked("pair seed differs")
        if control.get("status") == "complete" and candidate.get("status") == "complete":
            difference = float(candidate["terminal_floor"]) - float(
                control["terminal_floor"]
            )
            complete.append(
                {
                    "candidate_floor": candidate["terminal_floor"],
                    "candidate_victory": candidate["victory"],
                    "control_floor": control["terminal_floor"],
                    "control_victory": control["victory"],
                    "floor_difference": difference,
                    "seed": pair["seed"],
                }
            )
        else:
            censored.append(
                {
                    "candidate_reason": candidate.get("unsupported_reason"),
                    "control_reason": control.get("unsupported_reason"),
                    "seed": pair["seed"],
                }
            )
    differences = [float(row["floor_difference"]) for row in complete]
    interval = (
        _bootstrap_interval(differences)
        if differences
        else {"lower": None, "upper": None}
    )
    mean_difference = (
        math.fsum(differences) / len(differences) if differences else None
    )
    complete_seeds = {row["seed"] for row in complete}
    interventions = sum(
        int(pair["candidate"]["card_interventions"])
        for pair in normalized
        if pair["seed"] in complete_seeds
    )
    candidate_victories = sum(bool(row["candidate_victory"]) for row in complete)
    control_victories = sum(bool(row["control_victory"]) for row in complete)
    checks = {
        "actions_legal": all(
            action["action_id"]
            for pair in normalized
            for arm in (pair["control"], pair["candidate"])
            for action in arm["actions"]
        ),
        "bootstrap_noninferiority": interval["lower"] is not None
        and interval["lower"] >= MIN_BOOTSTRAP_LOWER_BOUND,
        "card_interventions_sufficient": interventions >= MIN_CARD_INTERVENTIONS,
        "complete_pairs_sufficient": len(complete) >= MIN_COMPLETE_PAIRS,
        "mean_floor_nonnegative": mean_difference is not None
        and mean_difference >= 0.0,
        "support_censors_within_limit": len(censored) <= MAX_CENSORED_PAIRS,
        "victories_noninferior": candidate_victories >= control_victories,
    }
    return {
        "bootstrap_95_percent": interval,
        "candidate_card_decisions": sum(
            len(pair["candidate"]["card_decisions"])
            for pair in normalized
            if pair["seed"] in complete_seeds
        ),
        "candidate_card_interventions": interventions,
        "candidate_victories": candidate_victories,
        "censored_pairs": censored,
        "checks": checks,
        "complete_pairs": complete,
        "control_victories": control_victories,
        "mean_paired_terminal_floor_difference": mean_difference,
    }


def _write_artifact(
    staging: Path, output: Path, name: str, payload: bytes
) -> dict[str, Any]:
    (staging / name).write_bytes(payload)
    return {
        "path": (output / name).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def execute(
    value: Mapping[str, Any],
    *,
    clock: Callable[[], float] = time.monotonic,
    process_observer: Callable[[], Sequence[Mapping[str, Any]]] = (
        pilot_runner._forbidden_processes
    ),
    environment_factory_loader: Callable[
        [Mapping[str, Any]], Callable[[int], Any]
    ] = pilot_runner._load_environment_factory,
) -> dict[str, Any]:
    registration = validate_registration(value)
    preflight = preflight_registration(registration, process_observer=process_observer)
    output = Path(registration["output_dir"]).resolve()
    staging = output.with_name(
        f".{output.name}.{registration['source']['commit']}.staging"
    )
    started = float(clock())
    if not math.isfinite(started):
        raise FreshSimulatorEvaluationBlocked("runner clock is invalid")
    deadline = started + MAX_WALL_SECONDS
    bootstrap, model, configuration, entry_bytes, model_bytes = _load_frozen_inputs(
        registration
    )
    entry_before = pilot.encode_candidate_card_policy(bootstrap)
    staging.mkdir(parents=False, exist_ok=False)
    model_binding = _write_artifact(
        staging, output, "residual_model.json", model_bytes
    )
    factory = environment_factory_loader(registration["native"]["identity"])
    pairs: list[dict[str, Any]] = []
    for seed in FRESH_SEEDS:
        control = _rollout_episode(
            factory,
            seed=seed,
            arm="control",
            bootstrap=bootstrap,
            model=model,
            configuration=configuration,
            deadline=deadline,
            clock=clock,
        )
        candidate = _rollout_episode(
            factory,
            seed=seed,
            arm="candidate",
            bootstrap=bootstrap,
            model=model,
            configuration=configuration,
            deadline=deadline,
            clock=clock,
        )
        pairs.append({"candidate": candidate, "control": control, "seed": seed})
    metrics = evaluate_pairs(pairs)
    if pilot.encode_candidate_card_policy(bootstrap) != entry_before:
        raise FreshSimulatorEvaluationBlocked("entry checkpoint changed during evaluation")
    if ranking.restore_entry_bootstrap(entry_bytes) is None:
        raise FreshSimulatorEvaluationBlocked("entry checkpoint no longer restores")
    if uplift.encode_uplift_model(model, configuration) != model_bytes:
        raise FreshSimulatorEvaluationBlocked("residual model changed during evaluation")
    if not base_runner.production_isolation_matches(registration):
        raise FreshSimulatorEvaluationBlocked("production isolation changed")
    if list(process_observer()):
        raise FreshSimulatorEvaluationBlocked("game or CommunicationMod started")
    if _source_bindings(
        Path(registration["source"]["repo_root"]),
        registration["source"]["commit"],
    ) != registration["source"]["bindings"]:
        raise FreshSimulatorEvaluationBlocked("source changed during evaluation")
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > MAX_WALL_SECONDS:
        raise FreshSimulatorEvaluationBlocked("wall time exceeds registration")
    trajectories = {
        "pairs": pairs,
        "schema_version": TRAJECTORY_SCHEMA_VERSION,
        "seeds": list(FRESH_SEEDS),
    }
    trajectory_payload = base_runner._canonical_bytes(trajectories)
    if len(trajectory_payload) > MAX_TRAJECTORY_BYTES:
        raise FreshSimulatorEvaluationBlocked("trajectory bytes exceed registration")
    ready = all(metrics["checks"].values())
    verdict = (
        "card_uplift_fresh_simulator_ready_for_live_shadow_adapter_proposal"
        if ready
        else "card_uplift_fresh_simulator_not_ready"
    )
    trajectory_binding = _write_artifact(
        staging, output, "trajectories.json", trajectory_payload
    )
    registration_binding = _write_artifact(
        staging,
        output,
        "registration.json",
        base_runner._canonical_bytes(registration),
    )
    preflight_binding = _write_artifact(
        staging, output, "preflight.json", base_runner._canonical_bytes(preflight)
    )
    metrics_payload = {
        **metrics,
        "schema_version": METRICS_SCHEMA_VERSION,
    }
    metrics_binding = _write_artifact(
        staging, output, "metrics.json", base_runner._canonical_bytes(metrics_payload)
    )
    report = {
        "authority": copy.deepcopy(AUTHORITY),
        "checks": metrics["checks"],
        "execution": {
            "completed_pairs": len(metrics["complete_pairs"]),
            "operations": copy.deepcopy(OPERATIONS),
            "paired_seeds": len(FRESH_SEEDS),
            "production_isolation_passed": True,
            "source_commit": registration["source"]["commit"],
            "wall_seconds": elapsed,
        },
        "metrics": metrics_binding,
        "model": model_binding,
        "preflight": preflight_binding,
        "registration": registration_binding,
        "schema_version": REPORT_SCHEMA_VERSION,
        "trajectories": trajectory_binding,
        "verdict": verdict,
    }
    report_binding = _write_artifact(
        staging, output, "report.json", base_runner._canonical_bytes(report)
    )
    terminal = {
        "completed_pairs": len(metrics["complete_pairs"]),
        "report": report_binding,
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "verdict": verdict,
    }
    _write_artifact(
        staging, output, "terminal.json", base_runner._canonical_bytes(terminal)
    )
    staging.rename(output)
    return terminal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("--repo-root", required=True)
    register.add_argument("--source-commit", required=True)
    register.add_argument("--audit-root", default=str(DEFAULT_AUDIT_ROOT))
    register.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    register.add_argument("--registration", required=True)
    for name in ("preflight", "run", "run-worker"):
        command = subparsers.add_parser(name)
        command.add_argument("--registration", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "register":
            registration = build_registration(
                repo_root=args.repo_root,
                source_commit=args.source_commit,
                audit_root=args.audit_root,
                output_dir=args.output_dir,
            )
            binding = base_runner._write_canonical(args.registration, registration)
            print(base_runner._canonical_bytes(binding).decode("ascii"))
            return 0
        registration = base_runner._read_canonical(args.registration)
        if args.command == "preflight":
            print(
                base_runner._canonical_bytes(
                    preflight_registration(registration)
                ).decode("ascii")
            )
            return 0
        if args.command == "run":
            preflight_registration(registration)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(Path(__file__).resolve()),
                    "run-worker",
                    "--registration",
                    str(Path(args.registration).resolve()),
                ],
                cwd=Path(registration["source"]["repo_root"]),
                check=False,
            )
            return completed.returncode
        terminal = execute(registration)
        print(base_runner._canonical_bytes(terminal).decode("ascii"))
        return 0
    except (
        FreshSimulatorEvaluationBlocked,
        OSError,
        base_runner.RankingRunnerBlocked,
        subprocess.SubprocessError,
        uplift.UpliftCrossfitBlocked,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
