"""Collect outcome-backed route branches and train one bounded ranker."""

from __future__ import annotations

import argparse
import copy
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import logging
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import types
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any


DEFAULT_NATIVE_REGISTRATION = Path(
    "reports/noncombat_card_counterfactual_corpus_expansion_20260813_r1/registration.json"
)
DEFAULT_CURRENT_BRIDGE_INPUT = Path(
    "reports/noncombat_current_policy_simulator_bridge_20260802_r2_input.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_route_counterfactual_ranking_20260814_r1"
)
TRAIN_SEEDS = tuple(range(93000, 93128))
DEVELOPMENT_SEEDS = tuple(range(93128, 93160))
CHECKPOINT_EPOCHS = (1, 2, 4, 8, 16)
MODEL_SEED = 20260814
LEARNING_RATE = 1e-3
BATCH_SIZE = 32
MAX_ROUTE_STATES_PER_SEED = 3
MAX_TRAIN_SOURCE_STATES = 384
MAX_DEVELOPMENT_SOURCE_STATES = 96
MAX_TRAIN_BRANCHES = 2_048
MAX_DEVELOPMENT_BRANCHES = 512
MAX_TRAIN_CENSORED_SOURCES = 64
MAX_DEVELOPMENT_CENSORED_SOURCES = 16
MIN_TRAIN_SOURCE_STATES = 128
MIN_DEVELOPMENT_SOURCE_STATES = 32
MAX_DECISIONS_PER_CONTINUATION = 512
MAX_CHARGED_SECONDS = 14_400.0
SCHEMA_VERSION = "noncombat-route-counterfactual-ranking-v1"
DATASET_SCHEMA_VERSION = "noncombat-route-counterfactual-dataset-v1"
MODEL_SCHEMA_VERSION = "noncombat-route-counterfactual-model-v1"
BOUND_SOURCE_PATHS = (
    Path("analysis_scripts/noncombat_route_counterfactual_ranking.py"),
    Path("analysis_scripts/noncombat_card_action_counterfactual_credit.py"),
    Path("analysis_scripts/noncombat_current_policy_simulator_bridge.py"),
    Path("analysis_scripts/noncombat_state_conditioned_policy_input.py"),
    Path("analysis_scripts/noncombat_state_conditioned_ranker.py"),
)
_EARLY_NATIVE_HANDLES: list[Any] = []


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


def _early_preload_native() -> None:
    if not (
        __name__ == "__main__"
        and len(sys.argv) >= 2
        and sys.argv[1] == "run"
    ):
        return
    try:
        if "--native-registration" in sys.argv:
            registration_path = Path(
                sys.argv[sys.argv.index("--native-registration") + 1]
            ).resolve()
        else:
            registration_path = DEFAULT_NATIVE_REGISTRATION.resolve()
        registration = json.loads(registration_path.read_text(encoding="ascii"))
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
                raise RuntimeError("native dependency cycle differs")
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
            raise RuntimeError("native dependency graph differs")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        load_library = kernel32.LoadLibraryExW
        load_library.argtypes = (wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD)
        load_library.restype = wintypes.HMODULE
        for path in order:
            handle = load_library(str(path), None, 0x00000100 | 0x00000400)
            if not handle:
                raise OSError(ctypes.get_last_error(), "LoadLibraryExW failed", str(path))
            _EARLY_NATIVE_HANDLES.append(int(handle))
        for directory in native["dll_directories"]:
            _EARLY_NATIVE_HANDLES.append(os.add_dll_directory(directory))
        spec = importlib.util.spec_from_file_location(
            "sts_lightspeed_noncombat_adapter", module_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("native module spec is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("route experiment early native load failed") from exc


if __name__ == "__main__":
    _bootstrap_direct_script_imports()
    _early_preload_native()


import torch
import torch.nn.functional as F

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as model_codec
from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as native_runner
from analysis_scripts import noncombat_current_policy_simulator_bridge as current_bridge
from analysis_scripts import noncombat_simulator_adapter as adapter
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    StateConditionedPolicyInput,
    project_state_conditioned_policy_input,
)
from analysis_scripts.noncombat_state_conditioned_ranker import (
    DEFAULT_HIDDEN_DIM,
    StateConditionedCandidateRanker,
)


class RouteExperimentBlocked(RuntimeError):
    """Raised when the fixed route experiment cannot produce valid evidence."""


@dataclass(frozen=True)
class RouteRow:
    seed: int
    decision_index: int
    source_sha256: str
    state_features: torch.Tensor
    candidate_features: torch.Tensor
    candidates: tuple[dict[str, Any], ...]
    branch_outcomes: tuple[dict[str, Any], ...]
    current_action_id: str

    @property
    def action_returns(self) -> tuple[float, ...]:
        return tuple(float(row["total_return"]) for row in self.branch_outcomes)

    @property
    def informative(self) -> bool:
        return max(self.action_returns) > min(self.action_returns)


@dataclass(frozen=True)
class RoutePartition:
    name: str
    seeds: tuple[int, ...]
    rows: tuple[RouteRow, ...]
    action_branches: int
    root_native_transitions: int
    censored_sources: tuple[dict[str, Any], ...]
    budget_exhausted: bool


@dataclass(frozen=True)
class ExperimentResult:
    configuration: dict[str, Any]
    train: RoutePartition
    development: RoutePartition
    model: dict[str, Any]
    metrics: dict[str, Any]
    report: dict[str, Any]


def _canonical_bytes(value: Any) -> bytes:
    try:
        return adapter.canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise RouteExperimentBlocked("artifact is not canonical JSON") from exc


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _registered_support_blocker(exc: BaseException) -> str | None:
    current: BaseException | None = exc
    seen: set[int] = set()
    messages: list[str] = []
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        messages.append(str(current))
        current = current.__cause__ or current.__context__
    for blocker in model_codec.REGISTERED_SUPPORT_BLOCKERS:
        if any(blocker in message for message in messages):
            return blocker
    return None


def _encode_sparse_tensor(value: torch.Tensor) -> dict[str, Any]:
    if not isinstance(value, torch.Tensor):
        raise RouteExperimentBlocked("sparse encoding requires a tensor")
    tensor = value.detach().cpu().to(dtype=torch.float32).contiguous()
    if not torch.isfinite(tensor).all().item():
        raise RouteExperimentBlocked("sparse tensor must be finite")
    flat = tensor.reshape(-1)
    indices = torch.nonzero(flat, as_tuple=False).reshape(-1).tolist()
    return {
        "indices": indices,
        "shape": list(tensor.shape),
        "values": [float(flat[index].item()) for index in indices],
    }


def _decode_sparse_tensor(value: object, label: str) -> torch.Tensor:
    if not isinstance(value, Mapping) or set(value) != {"indices", "shape", "values"}:
        raise RouteExperimentBlocked(f"{label} sparse fields differ")
    shape = value["shape"]
    indices = value["indices"]
    values = value["values"]
    if (
        isinstance(shape, (str, bytes))
        or not isinstance(shape, Sequence)
        or isinstance(indices, (str, bytes))
        or not isinstance(indices, Sequence)
        or isinstance(values, (str, bytes))
        or not isinstance(values, Sequence)
        or len(indices) != len(values)
    ):
        raise RouteExperimentBlocked(f"{label} sparse payload is invalid")
    dimensions = tuple(int(item) for item in shape)
    if not dimensions or any(item <= 0 for item in dimensions):
        raise RouteExperimentBlocked(f"{label} sparse shape is invalid")
    size = math.prod(dimensions)
    if any(
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < size
        for index in indices
    ) or len(set(indices)) != len(indices):
        raise RouteExperimentBlocked(f"{label} sparse indices are invalid")
    tensor = torch.zeros(size, dtype=torch.float32)
    try:
        tensor[list(indices)] = torch.tensor(list(values), dtype=torch.float32)
    except (TypeError, ValueError, RuntimeError) as exc:
        raise RouteExperimentBlocked(f"{label} sparse values are invalid") from exc
    if not torch.isfinite(tensor).all().item():
        raise RouteExperimentBlocked(f"{label} sparse values must be finite")
    return tensor.reshape(dimensions)


def encode_partition(partition: RoutePartition) -> bytes:
    rows = [
        {
            "branch_outcomes": copy.deepcopy(list(row.branch_outcomes)),
            "candidate_features": _encode_sparse_tensor(row.candidate_features),
            "candidates": copy.deepcopy(list(row.candidates)),
            "current_action_id": row.current_action_id,
            "decision_index": row.decision_index,
            "seed": row.seed,
            "source_sha256": row.source_sha256,
            "state_features": _encode_sparse_tensor(row.state_features),
        }
        for row in partition.rows
    ]
    return _canonical_bytes(
        {
            "action_branches": partition.action_branches,
            "budget_exhausted": partition.budget_exhausted,
            "censored_sources": copy.deepcopy(list(partition.censored_sources)),
            "name": partition.name,
            "root_native_transitions": partition.root_native_transitions,
            "rows": rows,
            "schema_version": DATASET_SCHEMA_VERSION,
            "seeds": list(partition.seeds),
        }
    )


def restore_partition(payload: bytes) -> RoutePartition:
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RouteExperimentBlocked("dataset JSON is invalid") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise RouteExperimentBlocked("dataset is not canonical")
    if value.get("schema_version") != DATASET_SCHEMA_VERSION:
        raise RouteExperimentBlocked("dataset schema differs")
    rows: list[RouteRow] = []
    for index, raw in enumerate(value.get("rows", ())):
        try:
            candidates = tuple(copy.deepcopy(raw["candidates"]))
            outcomes = tuple(copy.deepcopy(raw["branch_outcomes"]))
            row = RouteRow(
                seed=int(raw["seed"]),
                decision_index=int(raw["decision_index"]),
                source_sha256=str(raw["source_sha256"]),
                state_features=_decode_sparse_tensor(
                    raw["state_features"], f"row {index} state"
                ),
                candidate_features=_decode_sparse_tensor(
                    raw["candidate_features"], f"row {index} candidates"
                ),
                candidates=candidates,
                branch_outcomes=outcomes,
                current_action_id=str(raw["current_action_id"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RouteExperimentBlocked(f"dataset row {index} is invalid") from exc
        if (
            row.state_features.ndim != 1
            or row.candidate_features.ndim != 2
            or row.candidate_features.shape[0] != len(candidates)
            or len(candidates) != len(outcomes)
            or row.current_action_id not in {
                candidate.get("action_id") for candidate in candidates
            }
            or any(
                outcome.get("action_id") != candidate.get("action_id")
                for outcome, candidate in zip(outcomes, candidates, strict=True)
            )
        ):
            raise RouteExperimentBlocked(f"dataset row {index} alignment differs")
        rows.append(row)
    partition = RoutePartition(
        name=str(value.get("name")),
        seeds=tuple(int(seed) for seed in value.get("seeds", ())),
        rows=tuple(rows),
        action_branches=int(value.get("action_branches", -1)),
        root_native_transitions=int(value.get("root_native_transitions", -1)),
        censored_sources=tuple(copy.deepcopy(value.get("censored_sources", ()))),
        budget_exhausted=bool(value.get("budget_exhausted")),
    )
    if partition.name not in {"train", "development"}:
        raise RouteExperimentBlocked("dataset partition name differs")
    if encode_partition(partition) != payload:
        raise RouteExperimentBlocked("dataset round trip differs")
    return partition


def _branch_outcome(trace: credit.BranchTrace, candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "action_id": trace.action_id,
        "action_sequence_sha256": hashlib.sha256(
            _canonical_bytes(list(trace.action_sequence))
        ).hexdigest(),
        "floor_progress": trace.floor_progress,
        "terminal_floor": trace.terminal_summary["floor"],
        "terminal_outcome": trace.terminal_summary["outcome"],
        "terminal_victory": trace.terminal_victory,
        "total_return": trace.total_return,
        "transition_count": trace.transition_count,
        "candidate_sha256": _sha256_json(candidate),
    }


def evaluate_route_action_with_current_continuation(
    source_environment: Any,
    *,
    action_id: str,
    continuation_session_factory: Callable[[], Any],
    source_category: str = "route",
    max_decisions: int = MAX_DECISIONS_PER_CONTINUATION,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> credit.BranchTrace:
    """Force a route action, then re-decide from every branched state."""
    if source_category != "route":
        raise credit.CounterfactualCreditBlocked(
            "Current continuation requires a route source"
        )
    source_snapshot, source_candidates = credit._environment_state(
        source_environment
    )
    if source_snapshot["terminal"] or source_snapshot["category"] != "route":
        raise credit.CounterfactualCreditBlocked(
            "source must be a live route state"
        )
    if isinstance(max_decisions, bool) or not isinstance(max_decisions, int) or (
        max_decisions <= 0
    ):
        raise credit.CounterfactualCreditBlocked(
            "continuation decision ceiling is invalid"
        )
    active_deadline = float("inf") if deadline is None else float(deadline)
    if deadline is not None and not math.isfinite(active_deadline):
        raise credit.CounterfactualCreditBlocked(
            "branch deadline is invalid"
        )
    try:
        session = continuation_session_factory()
    except Exception as exc:
        raise credit.CounterfactualCreditBlocked(
            "Current continuation session failed"
        ) from exc
    environment, first_transition = credit._apply_forced_action(
        source_environment, action_id
    )
    transitions = [first_transition]
    actions = [action_id]
    scalar, floor_progress, terminal_victory = credit._transition_reward(
        first_transition
    )
    rewards = [scalar]
    while True:
        if float(clock()) > active_deadline:
            raise credit.CounterfactualCreditBlocked("branch deadline reached")
        snapshot, candidates = credit._environment_state(environment)
        if snapshot["terminal"]:
            break
        if len(transitions) >= max_decisions:
            raise credit.CounterfactualCreditBlocked(
                "continuation decision ceiling reached"
            )
        decision_index = snapshot.get("decision_count")
        if isinstance(decision_index, bool) or not isinstance(decision_index, int):
            raise credit.CounterfactualCreditBlocked(
                "Current continuation decision index is invalid"
            )
        try:
            evaluation = session.evaluate(
                snapshot=snapshot,
                candidates=candidates,
                decision_index=decision_index,
            )
            selected_action_id = evaluation["action_id"]
        except current_bridge.BridgeBlocked as exc:
            raise credit.CounterfactualCreditBlocked(
                f"Current continuation failed: {exc.reason}"
            ) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise credit.CounterfactualCreditBlocked(
                "Current continuation action is invalid"
            ) from exc
        environment, transition = credit._apply_forced_action(
            environment, selected_action_id
        )
        transition_reward, progress, victory = credit._transition_reward(
            transition
        )
        transitions.append(transition)
        actions.append(selected_action_id)
        rewards.append(transition_reward)
        floor_progress += progress
        terminal_victory = max(terminal_victory, victory)

    credit._assert_source_unchanged(
        source_environment, source_snapshot, source_candidates
    )
    final_snapshot, final_candidates = credit._environment_state(environment)
    if final_candidates:
        raise credit.CounterfactualCreditBlocked(
            "terminal branch reported candidates"
        )
    summary = credit._terminal_summary(final_snapshot)
    return credit.BranchTrace(
        action_id=action_id,
        action_sequence=tuple(actions),
        floor_progress=floor_progress,
        initial_transition_sha256=credit._sha256_json(first_transition),
        terminal_state_sha256=credit._sha256_json(final_snapshot["state"]),
        terminal_summary=summary,
        terminal_victory=terminal_victory,
        total_return=math.fsum(rewards),
        transition_count=len(transitions),
    )


def collect_route_partition(
    environment_factory: Callable[[int], Any],
    baseline_session_factory: Callable[[int], Any],
    *,
    name: str,
    seeds: Sequence[int],
    max_source_states: int,
    max_action_branches: int,
    max_censored_sources: int,
    max_route_states_per_seed: int = MAX_ROUTE_STATES_PER_SEED,
    max_decisions: int = MAX_DECISIONS_PER_CONTINUATION,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    projector: Callable[
        [Mapping[str, Any], Sequence[Mapping[str, Any]]],
        StateConditionedPolicyInput,
    ] = project_state_conditioned_policy_input,
    branch_evaluator: Callable[..., credit.BranchTrace] = (
        credit.evaluate_action_branch_for_category
    ),
) -> RoutePartition:
    if name not in {"train", "development"}:
        raise RouteExperimentBlocked("partition name differs")
    normalized_seeds = tuple(seeds)
    if not normalized_seeds or len(set(normalized_seeds)) != len(normalized_seeds):
        raise RouteExperimentBlocked("partition seeds are invalid")
    limits = (
        max_source_states,
        max_action_branches,
        max_censored_sources,
        max_route_states_per_seed,
        max_decisions,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in limits
    ):
        raise RouteExperimentBlocked("partition limits are invalid")
    active_deadline = float("inf") if deadline is None else float(deadline)
    if deadline is not None and not math.isfinite(active_deadline):
        raise RouteExperimentBlocked("partition deadline is invalid")

    rows: list[RouteRow] = []
    censored: list[dict[str, Any]] = []
    branch_count = 0
    root_transitions = 0
    budget_exhausted = False
    source_hashes: set[str] = set()
    for seed in normalized_seeds:
        if len(rows) >= max_source_states:
            budget_exhausted = True
            break
        if float(clock()) > active_deadline:
            raise RouteExperimentBlocked("partition deadline reached")
        try:
            environment = environment_factory(seed)
        except Exception as exc:
            raise RouteExperimentBlocked(
                f"partition setup failed for seed {seed}"
            ) from exc
        route_states = 0
        decision_index = 0
        while True:
            snapshot, candidates = credit._environment_state(environment)
            if snapshot["terminal"]:
                break
            if decision_index >= max_decisions:
                raise RouteExperimentBlocked("root decision ceiling reached")
            eligible = (
                snapshot["category"] == "route"
                and len(candidates) > 1
                and route_states < max_route_states_per_seed
            )
            if eligible:
                if len(rows) >= max_source_states or (
                    branch_count + len(candidates) > max_action_branches
                ):
                    budget_exhausted = True
                    break
                source_sha256 = _sha256_json(
                    {"candidate_actions": candidates, "snapshot": snapshot}
                )
                if source_sha256 in source_hashes:
                    raise RouteExperimentBlocked("route source identity repeats")
                try:
                    baseline_session = baseline_session_factory(seed)
                    current = baseline_session.evaluate(
                        snapshot=snapshot,
                        candidates=candidates,
                        decision_index=decision_index,
                    )
                    policy_input = projector(snapshot, candidates)
                except Exception as exc:
                    raise RouteExperimentBlocked(
                        "route baseline or projection failed for "
                        f"seed {seed} decision {decision_index}"
                    ) from exc
                current_action_id = current.get("action_id")
                if current_action_id not in {
                    candidate["action_id"] for candidate in candidates
                }:
                    raise RouteExperimentBlocked("Current route action is not source legal")
                outcomes: list[dict[str, Any]] = []
                censor_reason: str | None = None
                for candidate in candidates:
                    branch_count += 1
                    try:
                        trace = branch_evaluator(
                            environment,
                            action_id=candidate["action_id"],
                            source_category="route",
                            max_decisions=max_decisions,
                            deadline=None if deadline is None else active_deadline,
                            clock=clock,
                        )
                    except credit.CounterfactualCreditBlocked as exc:
                        censor_reason = _registered_support_blocker(exc)
                        if censor_reason is None:
                            raise RouteExperimentBlocked(str(exc)) from exc
                        break
                    except Exception as exc:
                        raise RouteExperimentBlocked(
                            "route branch evaluation failed"
                        ) from exc
                    outcomes.append(_branch_outcome(trace, candidate))
                if censor_reason is not None:
                    censored.append(
                        {
                            "decision_index": decision_index,
                            "reason": censor_reason,
                            "seed": seed,
                            "source_sha256": source_sha256,
                        }
                    )
                    if len(censored) > max_censored_sources:
                        raise RouteExperimentBlocked(
                            f"{name} censored source limit exceeded"
                        )
                else:
                    if len(outcomes) != len(candidates):
                        raise RouteExperimentBlocked("route source row is incomplete")
                    row = RouteRow(
                        seed=seed,
                        decision_index=decision_index,
                        source_sha256=source_sha256,
                        state_features=policy_input.state_features.detach().clone(),
                        candidate_features=(
                            policy_input.candidate_features.detach().clone()
                        ),
                        candidates=tuple(copy.deepcopy(candidates)),
                        branch_outcomes=tuple(outcomes),
                        current_action_id=str(current_action_id),
                    )
                    rows.append(row)
                    source_hashes.add(source_sha256)
                    route_states += 1
            if budget_exhausted:
                break
            try:
                environment, _ = credit._advance_native(environment)
            except credit.CounterfactualCreditBlocked as exc:
                reason = _registered_support_blocker(exc)
                if reason is None:
                    raise RouteExperimentBlocked(str(exc)) from exc
                censored.append(
                    {
                        "decision_index": decision_index,
                        "reason": reason,
                        "seed": seed,
                        "source_sha256": None,
                    }
                )
                if len(censored) > max_censored_sources:
                    raise RouteExperimentBlocked(
                        f"{name} censored source limit exceeded"
                    )
                break
            root_transitions += 1
            decision_index += 1
        if budget_exhausted:
            break

    return RoutePartition(
        name=name,
        seeds=normalized_seeds,
        rows=tuple(rows),
        action_branches=branch_count,
        root_native_transitions=root_transitions,
        censored_sources=tuple(censored),
        budget_exhausted=budget_exhausted,
    )


def _new_model(input_dim: int) -> StateConditionedCandidateRanker:
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(MODEL_SEED)
        model = StateConditionedCandidateRanker(input_dim, DEFAULT_HIDDEN_DIM)
    return model.to(device="cpu", dtype=torch.float32)


def _batch_loss(
    model: StateConditionedCandidateRanker, rows: Sequence[RouteRow]
) -> torch.Tensor | None:
    losses: list[torch.Tensor] = []
    weights: list[float] = []
    for row in rows:
        scores = model(row.state_features, row.candidate_features)
        returns = row.action_returns
        for left in range(len(returns)):
            for right in range(left + 1, len(returns)):
                difference = returns[left] - returns[right]
                if difference == 0:
                    continue
                better, worse = (left, right) if difference > 0 else (right, left)
                weight = abs(difference)
                losses.append(weight * F.softplus(-(scores[better] - scores[worse])))
                weights.append(weight)
    if not losses:
        return None
    return torch.stack(losses).sum() / math.fsum(weights)


def train_model(
    rows: Sequence[RouteRow], *, epochs: int
) -> tuple[StateConditionedCandidateRanker, list[dict[str, float | int]]]:
    normalized = tuple(rows)
    if not normalized or epochs <= 0:
        raise RouteExperimentBlocked("training rows or epochs are invalid")
    input_dim = normalized[0].state_features.shape[0]
    if any(
        row.state_features.shape != (input_dim,)
        or row.candidate_features.shape[1] != input_dim
        for row in normalized
    ):
        raise RouteExperimentBlocked("training feature widths differ")
    model = _new_model(input_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    history: list[dict[str, float | int]] = []
    for epoch in range(1, epochs + 1):
        model.train()
        batch_losses: list[float] = []
        for offset in range(0, len(normalized), BATCH_SIZE):
            loss = _batch_loss(model, normalized[offset : offset + BATCH_SIZE])
            if loss is None:
                continue
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            batch_losses.append(float(loss.detach().item()))
        if not batch_losses:
            raise RouteExperimentBlocked("training rows contain no unequal returns")
        history.append(
            {"epoch": epoch, "mean_batch_loss": math.fsum(batch_losses) / len(batch_losses)}
        )
    model.eval()
    return model, history


def evaluate_model(
    model: StateConditionedCandidateRanker, rows: Sequence[RouteRow]
) -> dict[str, Any]:
    regrets: list[float] = []
    weighted_correct = 0.0
    weighted_total = 0.0
    unique_best = 0
    unique_correct = 0
    predictions: list[dict[str, Any]] = []
    model.eval()
    with torch.no_grad():
        for row in rows:
            scores = model(row.state_features, row.candidate_features)
            predicted_index = int(torch.argmax(scores).item())
            returns = row.action_returns
            best_return = max(returns)
            regret = best_return - returns[predicted_index]
            regrets.append(regret)
            best_indices = [
                index for index, value in enumerate(returns) if value == best_return
            ]
            if len(best_indices) == 1:
                unique_best += 1
                unique_correct += int(predicted_index == best_indices[0])
            for left in range(len(returns)):
                for right in range(left + 1, len(returns)):
                    difference = returns[left] - returns[right]
                    if difference == 0:
                        continue
                    weight = abs(difference)
                    score_difference = float(scores[left].item() - scores[right].item())
                    if score_difference * difference > 0:
                        weighted_correct += weight
                    elif score_difference == 0:
                        weighted_correct += 0.5 * weight
                    weighted_total += weight
            predictions.append(
                {
                    "action_id": row.candidates[predicted_index]["action_id"],
                    "decision_index": row.decision_index,
                    "regret": regret,
                    "seed": row.seed,
                    "source_sha256": row.source_sha256,
                }
            )
    if not regrets or weighted_total <= 0:
        raise RouteExperimentBlocked("evaluation support is insufficient")
    return {
        "maximum_regret": max(regrets),
        "mean_regret": math.fsum(regrets) / len(regrets),
        "predictions": predictions,
        "unique_best_accuracy": (
            unique_correct / unique_best if unique_best else None
        ),
        "unique_best_rows": unique_best,
        "weighted_pairwise_accuracy": weighted_correct / weighted_total,
    }


def evaluate_current(rows: Sequence[RouteRow]) -> dict[str, Any]:
    regrets: list[float] = []
    predictions: list[dict[str, Any]] = []
    unique_best = 0
    unique_correct = 0
    for row in rows:
        action_ids = [candidate["action_id"] for candidate in row.candidates]
        selected_index = action_ids.index(row.current_action_id)
        returns = row.action_returns
        best_return = max(returns)
        regret = best_return - returns[selected_index]
        regrets.append(regret)
        best_indices = [index for index, value in enumerate(returns) if value == best_return]
        if len(best_indices) == 1:
            unique_best += 1
            unique_correct += int(selected_index == best_indices[0])
        predictions.append(
            {
                "action_id": row.current_action_id,
                "decision_index": row.decision_index,
                "regret": regret,
                "seed": row.seed,
                "source_sha256": row.source_sha256,
            }
        )
    if not regrets:
        raise RouteExperimentBlocked("Current baseline has no rows")
    return {
        "maximum_regret": max(regrets),
        "mean_regret": math.fsum(regrets) / len(regrets),
        "predictions": predictions,
        "unique_best_accuracy": unique_correct / unique_best if unique_best else None,
        "unique_best_rows": unique_best,
    }


def _prediction_changes(
    current: Mapping[str, Any], trained: Mapping[str, Any]
) -> dict[str, int]:
    current_by_source = {
        row["source_sha256"]: row for row in current["predictions"]
    }
    trained_by_source = {
        row["source_sha256"]: row for row in trained["predictions"]
    }
    if set(current_by_source) != set(trained_by_source):
        raise RouteExperimentBlocked("prediction source sets differ")
    corrected = worsened = changed = 0
    for source, before in current_by_source.items():
        after = trained_by_source[source]
        if before["action_id"] != after["action_id"]:
            changed += 1
        if after["regret"] < before["regret"]:
            corrected += 1
        elif after["regret"] > before["regret"]:
            worsened += 1
    return {"action_changes": changed, "corrected": corrected, "worsened": worsened}


def _partition_summary(partition: RoutePartition) -> dict[str, Any]:
    spreads = [max(row.action_returns) - min(row.action_returns) for row in partition.rows]
    candidate_counts = Counter(len(row.candidates) for row in partition.rows)
    return {
        "action_branches": partition.action_branches,
        "budget_exhausted": partition.budget_exhausted,
        "candidate_count_distribution": {
            str(key): value for key, value in sorted(candidate_counts.items())
        },
        "censored_sources": len(partition.censored_sources),
        "censor_reasons": dict(
            sorted(Counter(row["reason"] for row in partition.censored_sources).items())
        ),
        "informative_source_states": sum(row.informative for row in partition.rows),
        "return_spread_maximum": max(spreads) if spreads else None,
        "return_spread_mean": math.fsum(spreads) / len(spreads) if spreads else None,
        "root_native_transitions": partition.root_native_transitions,
        "source_states": len(partition.rows),
    }


def run_experiment(
    environment_factory: Callable[[int], Any],
    baseline_session_factory: Callable[[int], Any],
    *,
    train_seeds: Sequence[int] = TRAIN_SEEDS,
    development_seeds: Sequence[int] = DEVELOPMENT_SEEDS,
    minimum_train_rows: int = MIN_TRAIN_SOURCE_STATES,
    minimum_development_rows: int = MIN_DEVELOPMENT_SOURCE_STATES,
    maximum_charged_seconds: float = MAX_CHARGED_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    projector: Callable[
        [Mapping[str, Any], Sequence[Mapping[str, Any]]],
        StateConditionedPolicyInput,
    ] = project_state_conditioned_policy_input,
    branch_evaluator: Callable[..., credit.BranchTrace] = (
        credit.evaluate_action_branch_for_category
    ),
) -> ExperimentResult:
    train_schedule = tuple(train_seeds)
    development_schedule = tuple(development_seeds)
    if set(train_schedule) & set(development_schedule):
        raise RouteExperimentBlocked("train and development seeds overlap")
    started = float(clock())
    deadline = started + maximum_charged_seconds
    train = collect_route_partition(
        environment_factory,
        baseline_session_factory,
        name="train",
        seeds=train_schedule,
        max_source_states=MAX_TRAIN_SOURCE_STATES,
        max_action_branches=MAX_TRAIN_BRANCHES,
        max_censored_sources=MAX_TRAIN_CENSORED_SOURCES,
        deadline=deadline,
        clock=clock,
        projector=projector,
        branch_evaluator=branch_evaluator,
    )
    if len(train.rows) < minimum_train_rows:
        raise RouteExperimentBlocked("train route support floor is unmet")
    fit_rows = tuple(row for row in train.rows if row.seed % 4 != 0)
    tune_rows = tuple(row for row in train.rows if row.seed % 4 == 0)
    if not fit_rows or not tune_rows:
        raise RouteExperimentBlocked("train-only fit/tune split is empty")
    checkpoint_metrics: list[dict[str, Any]] = []
    selected_model: StateConditionedCandidateRanker | None = None
    selected_epoch: int | None = None
    selected_key: tuple[float, float, int] | None = None
    for epoch in CHECKPOINT_EPOCHS:
        candidate, history = train_model(fit_rows, epochs=epoch)
        tune_metrics = evaluate_model(candidate, tune_rows)
        key = (
            tune_metrics["mean_regret"],
            -tune_metrics["weighted_pairwise_accuracy"],
            epoch,
        )
        checkpoint_metrics.append(
            {
                "epoch": epoch,
                "fit_final_loss": history[-1]["mean_batch_loss"],
                "tune": {key: value for key, value in tune_metrics.items() if key != "predictions"},
            }
        )
        if selected_key is None or key < selected_key:
            selected_key = key
            selected_epoch = epoch
            selected_model = candidate
    if selected_model is None or selected_epoch is None:
        raise RouteExperimentBlocked("train-only selection failed")
    trained_model, final_history = train_model(train.rows, epochs=selected_epoch)

    development = collect_route_partition(
        environment_factory,
        baseline_session_factory,
        name="development",
        seeds=development_schedule,
        max_source_states=MAX_DEVELOPMENT_SOURCE_STATES,
        max_action_branches=MAX_DEVELOPMENT_BRANCHES,
        max_censored_sources=MAX_DEVELOPMENT_CENSORED_SOURCES,
        deadline=deadline,
        clock=clock,
        projector=projector,
        branch_evaluator=branch_evaluator,
    )
    if len(development.rows) < minimum_development_rows:
        raise RouteExperimentBlocked("development route support floor is unmet")
    input_dim = development.rows[0].state_features.shape[0]
    untrained = evaluate_model(_new_model(input_dim), development.rows)
    trained = evaluate_model(trained_model, development.rows)
    current = evaluate_current(development.rows)
    changes = _prediction_changes(current, trained)
    checks = {
        "corrects_at_least_one_current_decision": changes["corrected"] >= 1,
        "development_support": len(development.rows) >= minimum_development_rows,
        "maximum_regret_noninferior_to_current": (
            trained["maximum_regret"] <= current["maximum_regret"] + 1e-12
        ),
        "mean_regret_improves_current": (
            trained["mean_regret"] + 1e-12 < current["mean_regret"]
        ),
        "pairwise_accuracy_improves_initialization": (
            trained["weighted_pairwise_accuracy"]
            > untrained["weighted_pairwise_accuracy"] + 1e-12
        ),
        "worsened_not_more_than_corrected": (
            changes["worsened"] <= changes["corrected"]
        ),
    }
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > maximum_charged_seconds:
        raise RouteExperimentBlocked("route experiment charged time differs")
    verdict = (
        "route_counterfactual_ranker_ready_for_fresh_evaluation_proposal"
        if all(checks.values())
        else "route_counterfactual_ranker_not_ready_after_development"
    )
    metrics = {
        "changes_vs_current": changes,
        "checks": checks,
        "development": {
            "current": current,
            "trained": trained,
            "untrained": untrained,
        },
        "development_access_count": 1,
        "selection": {
            "checkpoints": checkpoint_metrics,
            "selected_epoch": selected_epoch,
        },
        "training_final_history": final_history,
        "verdict": verdict,
    }
    model_artifact = {
        "architecture": trained_model.architecture_metadata(),
        "model_seed": MODEL_SEED,
        "schema_version": MODEL_SCHEMA_VERSION,
        "selected_epoch": selected_epoch,
        "state": model_codec._encode_model_state(trained_model),
    }
    configuration = {
        "batch_size": BATCH_SIZE,
        "checkpoint_epochs": list(CHECKPOINT_EPOCHS),
        "development_seeds": list(development_schedule),
        "learning_rate": LEARNING_RATE,
        "maximum_charged_seconds": maximum_charged_seconds,
        "maximum_route_states_per_seed": MAX_ROUTE_STATES_PER_SEED,
        "model_seed": MODEL_SEED,
        "reward": "strict-primary-dominance:2*victory+floor/57",
        "schema_version": SCHEMA_VERSION,
        "train_seeds": list(train_schedule),
    }
    report = {
        "authority": {
            "formal_rl": False,
            "gameplay": False,
            "policy_loading": False,
            "promotion": False,
            "qualification": False,
        },
        "charged_seconds": elapsed,
        "development": _partition_summary(development),
        "development_access_count": 1,
        "operations": {
            "communication_mod": False,
            "gameplay": False,
            "model_fitting": True,
            "native_loading": True,
            "production_checkpoint_access": False,
            "seed_access": True,
            "training": True,
        },
        "schema_version": SCHEMA_VERSION,
        "train": _partition_summary(train),
        "verdict": verdict,
    }
    return ExperimentResult(
        configuration=configuration,
        train=train,
        development=development,
        model=model_artifact,
        metrics=metrics,
        report=report,
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RouteExperimentBlocked(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RouteExperimentBlocked(f"JSON root must be an object: {path}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_identity(repo_root: Path) -> dict[str, Any]:
    files = [
        {
            "path": path.as_posix(),
            "sha256": _sha256_file(repo_root / path),
            "size_bytes": (repo_root / path).stat().st_size,
        }
        for path in BOUND_SOURCE_PATHS
    ]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            encoding="ascii",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RouteExperimentBlocked("cannot resolve source commit") from exc
    return {"commit": commit, "files": files, "source_sha256": _sha256_json(files)}


def _write_artifacts(output: Path, result: ExperimentResult, identity: dict[str, Any]) -> None:
    output.mkdir(parents=False, exist_ok=False)
    artifacts: dict[str, bytes] = {
        "configuration.json": _canonical_bytes(result.configuration),
        "development_dataset.json": encode_partition(result.development),
        "metrics.json": _canonical_bytes(result.metrics),
        "model.json": _canonical_bytes(result.model),
        "report.json": _canonical_bytes({**result.report, "identity": identity}),
        "train_dataset.json": encode_partition(result.train),
    }
    for name, payload in artifacts.items():
        (output / name).write_bytes(payload)
    manifest = {
        "artifacts": [
            {
                "path": name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
            for name, payload in sorted(artifacts.items())
        ],
        "schema_version": "noncombat-route-counterfactual-manifest-v1",
    }
    (output / "artifact_manifest.json").write_bytes(_canonical_bytes(manifest))
    development = result.metrics["development"]
    changes = result.metrics["changes_vs_current"]
    markdown = "\n".join(
        (
            "# Outcome-Backed Route Counterfactual Ranking",
            "",
            f"- Verdict: `{result.report['verdict']}`",
            f"- Charged seconds: `{result.report['charged_seconds']:.3f}`",
            f"- Train source states: `{len(result.train.rows)}`",
            f"- Development source states: `{len(result.development.rows)}`",
            f"- Selected epoch: `{result.metrics['selection']['selected_epoch']}`",
            "",
            "## Development",
            "",
            "| Policy | Mean regret | Max regret | Unique-best accuracy | Pairwise accuracy |",
            "| --- | ---: | ---: | ---: | ---: |",
            f"| Current | {development['current']['mean_regret']:.6f} | {development['current']['maximum_regret']:.6f} | {development['current']['unique_best_accuracy'] or 0:.6f} | n/a |",
            f"| Untrained | {development['untrained']['mean_regret']:.6f} | {development['untrained']['maximum_regret']:.6f} | {development['untrained']['unique_best_accuracy'] or 0:.6f} | {development['untrained']['weighted_pairwise_accuracy']:.6f} |",
            f"| Trained | {development['trained']['mean_regret']:.6f} | {development['trained']['maximum_regret']:.6f} | {development['trained']['unique_best_accuracy'] or 0:.6f} | {development['trained']['weighted_pairwise_accuracy']:.6f} |",
            "",
            f"Action changes versus Current: {changes['action_changes']}; corrected: {changes['corrected']}; worsened: {changes['worsened']}.",
            "",
            "Frozen Current-policy continuation is fixed downstream context, not an unbiased live-policy value estimate. No gameplay, CommunicationMod, production checkpoint, qualification, or promotion authority is granted.",
            "",
        )
    )
    (output / "report.md").write_text(markdown, encoding="ascii", newline="\n")


def execute_cli(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise RouteExperimentBlocked("output directory already exists")
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_registration = _read_json(native_registration_path)
    bridge_input = _read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
        current_policy = bridge_input["current_policy"]
    except KeyError as exc:
        raise RouteExperimentBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if (
        not metadata_path.is_file()
        or _sha256_file(metadata_path) != metadata_binding["sha256"]
    ):
        raise RouteExperimentBlocked("Current policy metadata bytes differ")
    forbidden_before = list(native_runner._forbidden_processes())
    if forbidden_before:
        raise RouteExperimentBlocked("game or CommunicationMod is active")
    environment_factory = native_runner._load_environment_factory(native_identity)
    metadata = current_bridge.MetadataCatalog(metadata_path)

    def baseline_session_factory(_seed: int) -> current_bridge.CurrentPolicyBridgeSession:
        return current_bridge.CurrentPolicyBridgeSession(
            metadata=metadata,
            current_policy=current_policy,
            event_semantics_identity=None,
            require_global_metadata_match=True,
            simulator_provenance=native_identity["provenance"],
        )

    def branch_evaluator(environment: Any, **kwargs: Any) -> credit.BranchTrace:
        return evaluate_route_action_with_current_continuation(
            environment,
            continuation_session_factory=lambda: baseline_session_factory(0),
            **kwargs,
        )

    result = run_experiment(
        environment_factory,
        baseline_session_factory,
        branch_evaluator=branch_evaluator,
    )
    forbidden_after = list(native_runner._forbidden_processes())
    if forbidden_after:
        raise RouteExperimentBlocked("game or CommunicationMod started during execution")
    identity = {
        "current_bridge_input": {
            "path": bridge_input_path.as_posix(),
            "sha256": _sha256_file(bridge_input_path),
        },
        "metadata": copy.deepcopy(metadata_binding),
        "native_module": copy.deepcopy(native_identity["module"]),
        "native_registration": {
            "path": native_registration_path.as_posix(),
            "sha256": _sha256_file(native_registration_path),
        },
        "source": _source_identity(repo_root),
    }
    _write_artifacts(output, result, identity)
    return {
        "development_source_states": len(result.development.rows),
        "output_dir": output.as_posix(),
        "selected_epoch": result.metrics["selection"]["selected_epoch"],
        "train_source_states": len(result.train.rows),
        "verdict": result.report["verdict"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    run.add_argument("--native-registration", default=str(DEFAULT_NATIVE_REGISTRATION))
    run.add_argument("--current-bridge-input", default=str(DEFAULT_CURRENT_BRIDGE_INPUT))
    run.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "run":
        raise RouteExperimentBlocked("unsupported command")
    print(json.dumps(execute_cli(args), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
