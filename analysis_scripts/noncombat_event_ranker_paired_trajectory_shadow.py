"""Run paired Current and event-ranker full simulator trajectories."""

from __future__ import annotations

import argparse
import copy
import ctypes
from ctypes import wintypes
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
DEFAULT_TRAINING_DIR = Path(
    "reports/noncombat_event_option_counterfactual_ranking_20260814_r1"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_event_ranker_paired_trajectory_shadow_20260814_r1"
)
SUPPORTED_OUTPUT_DIR = Path(
    "reports/noncombat_supported_event_ranker_paired_trajectory_shadow_20260814_r1"
)
SEEDS = tuple(range(94600, 94728))
SUPPORTED_SEEDS = tuple(range(94800, 94928))
MAX_DECISIONS = 512
MAX_CENSORED_PAIRS = 16
MIN_COMPLETE_PAIRS = 112
MIN_EVENT_EXPOSED_PAIRS = 96
MIN_OVERRIDE_PAIRS = 64
MIN_SUPPORT_EXPOSED_PAIRS = 64
MAX_CHARGED_SECONDS = 7_200.0
SCHEMA_VERSION = "noncombat-event-ranker-paired-trajectory-shadow-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-event-ranker-paired-trajectory-manifest-v1"
SUPPORTED_SCHEMA_VERSION = (
    "noncombat-supported-event-ranker-paired-trajectory-shadow-v1"
)
SUPPORTED_MANIFEST_SCHEMA_VERSION = (
    "noncombat-supported-event-ranker-paired-trajectory-manifest-v1"
)
EVENT_SUPPORT_SIGNATURE_SCHEMA_VERSION = (
    "noncombat-event-candidate-support-signature-v1"
)
BOUND_SOURCE_PATHS = (
    Path("analysis_scripts/noncombat_event_ranker_paired_trajectory_shadow.py"),
    Path("analysis_scripts/noncombat_event_option_ranker_shadow_evaluation.py"),
    Path("analysis_scripts/noncombat_event_option_counterfactual_ranking.py"),
    Path("analysis_scripts/noncombat_route_counterfactual_ranking.py"),
    Path("analysis_scripts/noncombat_card_action_counterfactual_credit.py"),
    Path("analysis_scripts/noncombat_current_policy_simulator_bridge.py"),
    Path("analysis_scripts/noncombat_state_conditioned_policy_input.py"),
    Path("analysis_scripts/noncombat_state_conditioned_ranker.py"),
    Path("analysis_scripts/noncombat_event_option_semantics.py"),
    Path("analysis_scripts/noncombat_policy_model.py"),
    Path("analysis_scripts/noncombat_simulator_adapter.py"),
    Path("analysis_scripts/noncombat_simulator_rl_experiment.py"),
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
        and sys.argv[1] in {"run", "run-supported"}
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
        raise RuntimeError("paired trajectory early native load failed") from exc


if __name__ == "__main__":
    _bootstrap_direct_script_imports()
    _early_preload_native()


import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as model_codec
from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as native_runner
from analysis_scripts import noncombat_current_policy_simulator_bridge as current_bridge
from analysis_scripts import noncombat_event_option_counterfactual_ranking as training
from analysis_scripts import noncombat_event_option_ranker_shadow_evaluation as shadow
from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    policy_input_metadata,
    project_state_conditioned_policy_input,
)
from analysis_scripts.noncombat_state_conditioned_ranker import StateConditionedCandidateRanker


class PairedTrajectoryBlocked(RuntimeError):
    """Raised when the paired trajectory experiment cannot produce evidence."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        return route._canonical_bytes(value)
    except route.RouteExperimentBlocked as exc:
        raise PairedTrajectoryBlocked(str(exc)) from exc


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _registered_blocker(exc: BaseException) -> str | None:
    current: BaseException | None = exc
    messages: list[str] = []
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        messages.append(str(current))
        current = current.__cause__ or current.__context__
    for blocker in (*model_codec.REGISTERED_SUPPORT_BLOCKERS, route.CURRENT_SHOP_MAPPING_BLOCKER):
        if any(blocker in message for message in messages):
            return blocker
    return None


def event_candidate_support_signature(
    candidates: Sequence[Mapping[str, Any]],
) -> str:
    semantics: list[dict[str, Any]] = []
    action_ids: set[str] = set()
    event_ids: set[str] = set()
    for candidate in candidates:
        action_id = candidate.get("action_id")
        kind = candidate.get("kind")
        raw = candidate.get("raw")
        if (
            candidate.get("category") != "event"
            or not isinstance(action_id, str)
            or not action_id.startswith("event:")
            or kind != "event_option"
            or not isinstance(raw, Mapping)
            or candidate.get("available") is not True
            or not isinstance(candidate.get("label"), str)
        ):
            raise PairedTrajectoryBlocked("event support candidate semantics differ")
        if action_id in action_ids:
            raise PairedTrajectoryBlocked("event support candidate actions repeat")
        event_id = raw.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise PairedTrajectoryBlocked("event support event identity differs")
        action_ids.add(action_id)
        event_ids.add(event_id)
        semantics.append(copy.deepcopy(dict(candidate)))
    if len(semantics) <= 1:
        raise PairedTrajectoryBlocked("event support candidate set is not multi-option")
    if len(event_ids) != 1:
        raise PairedTrajectoryBlocked("event support event identities differ")
    semantics.sort(key=_canonical_bytes)
    return _sha256_json(
        {
            "candidates": semantics,
            "event_id": next(iter(event_ids)),
            "schema_version": EVENT_SUPPORT_SIGNATURE_SCHEMA_VERSION,
            "target_category": "event",
        }
    )


def _event_action_prefix(candidates: Sequence[Mapping[str, Any]]) -> str:
    try:
        prefixes = {
            str(candidate["action_id"]).split(":", 2)[1] for candidate in candidates
        }
    except (IndexError, KeyError) as exc:
        raise PairedTrajectoryBlocked("event action prefix differs") from exc
    if len(prefixes) != 1:
        raise PairedTrajectoryBlocked("event action prefixes differ")
    return next(iter(prefixes))


def select_event_overlay_action(
    model: StateConditionedCandidateRanker,
    *,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    current_action_id: str,
    confidence_threshold: float,
    support_signatures: Mapping[str, int] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    action_ids = [str(candidate["action_id"]) for candidate in candidates]
    if current_action_id not in action_ids:
        raise PairedTrajectoryBlocked("Current trajectory action is not legal")
    if snapshot.get("category") != "event" or len(action_ids) <= 1:
        return current_action_id, None
    support_fields: dict[str, Any] = {}
    if support_signatures is not None:
        support_signature = event_candidate_support_signature(candidates)
        event_action_prefix = _event_action_prefix(candidates)
        support_count = int(support_signatures.get(support_signature, 0))
        support_fields = {
            "event_action_prefix": event_action_prefix,
            "support_signature": support_signature,
            "training_support_count": support_count,
        }
        if support_count <= 0:
            return current_action_id, {
                "candidate_action_ids": action_ids,
                "candidate_count": len(action_ids),
                "confidence": None,
                "current_action_id": current_action_id,
                "fallback_reason": "candidate_semantics_absent_from_training",
                "learned_action_id": None,
                "overridden": False,
                "ranker_evaluated": False,
                "selected_action_id": current_action_id,
                "source_sha256": _sha256_json(
                    {"candidate_actions": list(candidates), "snapshot": snapshot}
                ),
                "support_status": "fallback",
                **support_fields,
            }
    if confidence_threshold not in training.CONFIDENCE_THRESHOLDS:
        raise PairedTrajectoryBlocked("bound confidence threshold differs")
    try:
        policy_input = project_state_conditioned_policy_input(snapshot, candidates)
        model.eval()
        with torch.no_grad():
            scores = model(
                policy_input.state_features, policy_input.candidate_features
            )
    except Exception as exc:
        raise PairedTrajectoryBlocked("event overlay projection failed") from exc
    learned_index = int(torch.argmax(scores).item())
    current_index = action_ids.index(current_action_id)
    score_advantage = float(scores[learned_index].item() - scores[current_index].item())
    confidence = float(torch.sigmoid(torch.tensor(score_advantage)).item())
    selected_action_id = (
        action_ids[learned_index]
        if learned_index != current_index and confidence >= confidence_threshold
        else current_action_id
    )
    row = {
        "candidate_action_ids": action_ids,
        "candidate_count": len(action_ids),
        "confidence": confidence,
        "current_action_id": current_action_id,
        "learned_action_id": action_ids[learned_index],
        "overridden": selected_action_id != current_action_id,
        "ranker_evaluated": True,
        "selected_action_id": selected_action_id,
        "source_sha256": _sha256_json(
            {"candidate_actions": list(candidates), "snapshot": snapshot}
        ),
    }
    if support_signatures is not None:
        row.update({"support_status": "supported", **support_fields})
    return selected_action_id, row


def run_trajectory(
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[int], Any],
    *,
    seed: int,
    model: StateConditionedCandidateRanker | None,
    confidence_threshold: float | None,
    support_signatures: Mapping[str, int] | None = None,
    max_decisions: int = MAX_DECISIONS,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if max_decisions <= 0:
        raise PairedTrajectoryBlocked("trajectory decision ceiling is invalid")
    environment = environment_factory(seed)
    session = session_factory(seed)
    actions: list[str] = []
    event_decisions: list[dict[str, Any]] = []
    transition_return = 0.0
    while True:
        if deadline is not None and float(clock()) > deadline:
            raise PairedTrajectoryBlocked("paired trajectory deadline reached")
        snapshot, candidates = credit._environment_state(environment)
        if snapshot["terminal"]:
            break
        if len(actions) >= max_decisions:
            raise PairedTrajectoryBlocked("trajectory decision ceiling reached")
        decision_index = snapshot.get("decision_count")
        if isinstance(decision_index, bool) or not isinstance(decision_index, int):
            raise PairedTrajectoryBlocked("trajectory decision index differs")
        try:
            evaluation = session.evaluate(
                snapshot=snapshot,
                candidates=candidates,
                decision_index=decision_index,
            )
            current_action_id = str(evaluation["action_id"])
        except current_bridge.BridgeBlocked as exc:
            if snapshot.get("category") == "shop" and exc.reason == "candidate_mapping_absent":
                raise credit.CounterfactualCreditBlocked(
                    route.CURRENT_SHOP_MAPPING_BLOCKER
                ) from exc
            raise PairedTrajectoryBlocked(f"Current trajectory failed: {exc.reason}") from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise PairedTrajectoryBlocked("Current trajectory action is invalid") from exc
        selected_action_id = current_action_id
        event_row = None
        if model is not None:
            if confidence_threshold is None:
                raise PairedTrajectoryBlocked("event overlay threshold is missing")
            selected_action_id, event_row = select_event_overlay_action(
                model,
                snapshot=snapshot,
                candidates=candidates,
                current_action_id=current_action_id,
                confidence_threshold=confidence_threshold,
                support_signatures=support_signatures,
            )
        elif snapshot.get("category") == "event" and len(candidates) > 1:
            event_row = {
                "candidate_count": len(candidates),
                "current_action_id": current_action_id,
                "overridden": False,
                "selected_action_id": current_action_id,
                "source_sha256": _sha256_json(
                    {"candidate_actions": candidates, "snapshot": snapshot}
                ),
            }
        if event_row is not None:
            event_decisions.append(
                {**event_row, "decision_index": decision_index}
            )
        try:
            environment, transition = credit._apply_forced_action(
                environment, selected_action_id
            )
            scalar, _floor_progress, _victory = credit._transition_reward(transition)
        except credit.CounterfactualCreditBlocked:
            raise
        except Exception as exc:
            raise PairedTrajectoryBlocked("trajectory transition failed") from exc
        actions.append(selected_action_id)
        transition_return += scalar
    final_snapshot, final_candidates = credit._environment_state(environment)
    if final_candidates:
        raise PairedTrajectoryBlocked("terminal trajectory reported candidates")
    summary = credit._terminal_summary(final_snapshot)
    floor = summary.get("floor")
    outcome = summary.get("outcome")
    if isinstance(floor, bool) or not isinstance(floor, int) or floor < 0:
        raise PairedTrajectoryBlocked("terminal floor differs")
    victory = int(outcome == "player_victory")
    total_return = 2.0 * victory + floor / 57.0
    if not math.isclose(transition_return, total_return, rel_tol=0.0, abs_tol=1e-9):
        raise PairedTrajectoryBlocked("trajectory return decomposition differs")
    return {
        "action_count": len(actions),
        "action_sequence": actions,
        "action_sequence_sha256": _sha256_json(actions),
        "event_decisions": event_decisions,
        "event_source_count": len(event_decisions),
        "floor": floor,
        "outcome": outcome,
        "override_count": sum(bool(row["overridden"]) for row in event_decisions),
        "support_fallback_count": sum(
            row.get("support_status") == "fallback" for row in event_decisions
        ),
        "support_source_count": sum(
            row.get("support_status") == "supported" for row in event_decisions
        ),
        "terminal_state_sha256": _sha256_json(final_snapshot),
        "total_return": total_return,
        "victory": victory,
    }


def collect_pairs(
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[int], Any],
    model: StateConditionedCandidateRanker,
    *,
    confidence_threshold: float,
    support_signatures: Mapping[str, int] | None = None,
    seeds: Sequence[int] = SEEDS,
    max_censored_pairs: int = MAX_CENSORED_PAIRS,
    maximum_charged_seconds: float = MAX_CHARGED_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], float]:
    schedule = tuple(seeds)
    if not schedule or len(schedule) != len(set(schedule)):
        raise PairedTrajectoryBlocked("paired seed schedule differs")
    started = float(clock())
    deadline = started + maximum_charged_seconds
    pairs: list[dict[str, Any]] = []
    censored: list[dict[str, Any]] = []
    for seed in schedule:
        arms: dict[str, dict[str, Any]] = {}
        blocker = None
        for arm, arm_model in (("current", None), ("selected", model)):
            try:
                arms[arm] = run_trajectory(
                    environment_factory,
                    session_factory,
                    seed=seed,
                    model=arm_model,
                    confidence_threshold=(confidence_threshold if arm_model is not None else None),
                    support_signatures=(
                        support_signatures if arm_model is not None else None
                    ),
                    deadline=deadline,
                    clock=clock,
                )
            except Exception as exc:
                blocker = _registered_blocker(exc)
                if blocker is None:
                    raise PairedTrajectoryBlocked(
                        f"{arm} trajectory failed for seed {seed}"
                    ) from exc
                censored.append({"arm": arm, "reason": blocker, "seed": seed})
                if len(censored) > max_censored_pairs:
                    raise PairedTrajectoryBlocked("paired censor limit exceeded")
                break
        if blocker is not None:
            continue
        current = arms["current"]
        selected = arms["selected"]
        delta = selected["total_return"] - current["total_return"]
        pairs.append(
            {
                "current": current,
                "delta_floor": selected["floor"] - current["floor"],
                "delta_return": delta,
                "delta_victory": selected["victory"] - current["victory"],
                "seed": seed,
                "selected": selected,
            }
        )
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > maximum_charged_seconds:
        raise PairedTrajectoryBlocked("paired charged time differs")
    return tuple(pairs), tuple(censored), elapsed


def evaluate_pairs(
    pairs: Sequence[Mapping[str, Any]],
    censored: Sequence[Mapping[str, Any]],
    *,
    minimum_complete_pairs: int = MIN_COMPLETE_PAIRS,
    minimum_event_exposed_pairs: int = MIN_EVENT_EXPOSED_PAIRS,
    minimum_override_pairs: int = MIN_OVERRIDE_PAIRS,
) -> tuple[dict[str, Any], str]:
    rows = tuple(pairs)
    if not rows:
        raise PairedTrajectoryBlocked("paired evaluation has no complete rows")
    current_returns = [float(row["current"]["total_return"]) for row in rows]
    selected_returns = [float(row["selected"]["total_return"]) for row in rows]
    current_floors = [int(row["current"]["floor"]) for row in rows]
    selected_floors = [int(row["selected"]["floor"]) for row in rows]
    current_victories = sum(int(row["current"]["victory"]) for row in rows)
    selected_victories = sum(int(row["selected"]["victory"]) for row in rows)
    improved = sum(float(row["delta_return"]) > 1e-12 for row in rows)
    worsened = sum(float(row["delta_return"]) < -1e-12 for row in rows)
    tied = len(rows) - improved - worsened
    event_exposed_pairs = sum(int(row["selected"]["event_source_count"]) > 0 for row in rows)
    override_pairs = sum(int(row["selected"]["override_count"]) > 0 for row in rows)
    victory_gains = sum(int(row["delta_victory"]) > 0 for row in rows)
    victory_losses = sum(int(row["delta_victory"]) < 0 for row in rows)
    current_mean_return = math.fsum(current_returns) / len(rows)
    selected_mean_return = math.fsum(selected_returns) / len(rows)
    current_mean_floor = math.fsum(current_floors) / len(rows)
    selected_mean_floor = math.fsum(selected_floors) / len(rows)
    checks = {
        "complete_pair_support": len(rows) >= minimum_complete_pairs,
        "event_exposure_support": event_exposed_pairs >= minimum_event_exposed_pairs,
        "improves_at_least_one_pair": improved >= 1,
        "improved_not_fewer_than_worsened": improved >= worsened,
        "mean_floor_noninferior_to_current": selected_mean_floor + 1e-12 >= current_mean_floor,
        "mean_return_improves_current": selected_mean_return > current_mean_return + 1e-12,
        "no_paired_victory_loss": victory_losses == 0,
        "override_support": override_pairs >= minimum_override_pairs,
        "victory_count_noninferior_to_current": selected_victories >= current_victories,
    }
    verdict = (
        "event_ranker_paired_trajectory_integration_ready"
        if all(checks.values())
        else "event_ranker_paired_trajectory_integration_not_ready"
    )
    metrics = {
        "censor_reasons": dict(sorted(Counter(row["reason"] for row in censored).items())),
        "censored_pairs": len(censored),
        "checks": checks,
        "complete_pairs": len(rows),
        "current": {
            "mean_floor": current_mean_floor,
            "mean_return": current_mean_return,
            "victories": current_victories,
        },
        "event_exposed_pairs": event_exposed_pairs,
        "improved_pairs": improved,
        "override_pairs": override_pairs,
        "selected": {
            "mean_floor": selected_mean_floor,
            "mean_return": selected_mean_return,
            "total_event_overrides": sum(int(row["selected"]["override_count"]) for row in rows),
            "victories": selected_victories,
        },
        "tied_pairs": tied,
        "verdict": verdict,
        "victory_gains": victory_gains,
        "victory_losses": victory_losses,
        "worsened_pairs": worsened,
    }
    return metrics, verdict


def evaluate_supported_pairs(
    pairs: Sequence[Mapping[str, Any]],
    censored: Sequence[Mapping[str, Any]],
    *,
    minimum_complete_pairs: int = MIN_COMPLETE_PAIRS,
    minimum_event_exposed_pairs: int = MIN_EVENT_EXPOSED_PAIRS,
    minimum_support_exposed_pairs: int = MIN_SUPPORT_EXPOSED_PAIRS,
    minimum_override_pairs: int = MIN_OVERRIDE_PAIRS,
) -> tuple[dict[str, Any], str]:
    metrics, _raw_verdict = evaluate_pairs(
        pairs,
        censored,
        minimum_complete_pairs=minimum_complete_pairs,
        minimum_event_exposed_pairs=minimum_event_exposed_pairs,
        minimum_override_pairs=minimum_override_pairs,
    )
    support_exposed_pairs = 0
    fallback_pairs = 0
    supported_sources = 0
    fallback_sources = 0
    fallback_events: Counter[str] = Counter()
    accounting_complete = True
    out_of_support_overrides = 0
    invalid_override_statuses = 0
    for pair in pairs:
        selected = pair["selected"]
        event_decisions = tuple(selected.get("event_decisions", ()))
        statuses = [row.get("support_status") for row in event_decisions]
        supported = sum(status == "supported" for status in statuses)
        fallbacks = sum(status == "fallback" for status in statuses)
        support_exposed_pairs += supported > 0
        fallback_pairs += fallbacks > 0
        supported_sources += supported
        fallback_sources += fallbacks
        if (
            supported != selected.get("support_source_count")
            or fallbacks != selected.get("support_fallback_count")
            or supported + fallbacks != selected.get("event_source_count")
            or any(status not in {"supported", "fallback"} for status in statuses)
        ):
            accounting_complete = False
        for row in event_decisions:
            if row.get("overridden") and row.get("support_status") != "supported":
                invalid_override_statuses += 1
            if row.get("support_status") == "fallback":
                fallback_events[str(row.get("event_action_prefix"))] += 1
                out_of_support_overrides += bool(row.get("overridden"))
                if (
                    row.get("fallback_reason")
                    != "candidate_semantics_absent_from_training"
                    or row.get("selected_action_id") != row.get("current_action_id")
                    or row.get("ranker_evaluated") is not False
                    or row.get("learned_action_id") is not None
                    or row.get("confidence") is not None
                    or int(row.get("training_support_count", -1)) != 0
                ):
                    accounting_complete = False
    checks = dict(metrics["checks"])
    checks.update(
        {
            "fallback_accounting_complete": accounting_complete,
            "no_out_of_support_overrides": (
                out_of_support_overrides == 0 and invalid_override_statuses == 0
            ),
            "support_exposure": support_exposed_pairs
            >= minimum_support_exposed_pairs,
        }
    )
    verdict = (
        "supported_event_ranker_paired_trajectory_integration_ready"
        if all(checks.values())
        else "supported_event_ranker_paired_trajectory_integration_not_ready"
    )
    metrics.update(
        {
            "checks": checks,
            "support": {
                "fallback_event_counts": dict(sorted(fallback_events.items())),
                "fallback_pairs": fallback_pairs,
                "fallback_sources": fallback_sources,
                "out_of_support_overrides": out_of_support_overrides,
                "support_exposed_pairs": support_exposed_pairs,
                "supported_sources": supported_sources,
            },
            "verdict": verdict,
        }
    )
    return metrics, verdict


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PairedTrajectoryBlocked(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise PairedTrajectoryBlocked(f"JSON root must be an object: {path}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_bound_training_support(
    training_dir: Path,
) -> tuple[dict[str, int], dict[str, Any]]:
    root = training_dir.resolve()
    manifest_path = root / "artifact_manifest.json"
    dataset_path = root / "train_dataset.json"
    manifest_payload = manifest_path.read_bytes()
    manifest = _read_json(manifest_path)
    if (
        _canonical_bytes(manifest) != manifest_payload
        or manifest.get("schema_version") != training.MANIFEST_SCHEMA_VERSION
    ):
        raise PairedTrajectoryBlocked("training artifact manifest differs")
    expected_artifacts = {
        "configuration.json",
        "development_dataset.json",
        "metrics.json",
        "model.json",
        "report.json",
        "train_dataset.json",
    }
    bindings: dict[str, Mapping[str, Any]] = {}
    for row in manifest.get("artifacts", ()):
        if not isinstance(row, Mapping):
            raise PairedTrajectoryBlocked("training artifact binding differs")
        name = row.get("path")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name in bindings
        ):
            raise PairedTrajectoryBlocked("training artifact path differs")
        bindings[name] = row
    if set(bindings) != expected_artifacts:
        raise PairedTrajectoryBlocked("training artifact members differ")
    for name, binding in bindings.items():
        path = root / name
        if (
            not path.is_file()
            or path.stat().st_size != binding.get("size_bytes")
            or _sha256_file(path) != binding.get("sha256")
        ):
            raise PairedTrajectoryBlocked(f"training {name} manifest binding differs")
        try:
            value = json.loads(path.read_text(encoding="ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PairedTrajectoryBlocked(f"training {name} JSON differs") from exc
        if _canonical_bytes(value) != path.read_bytes():
            raise PairedTrajectoryBlocked(f"training {name} is not canonical")
    payload = dataset_path.read_bytes()
    try:
        partition = training.restore_event_partition(payload)
        if training.encode_event_partition(partition) != payload:
            raise PairedTrajectoryBlocked("training dataset round-trip differs")
        if partition.name != "train":
            raise PairedTrajectoryBlocked("training partition name differs")
        configuration = _read_json(root / "configuration.json")
        if tuple(configuration.get("train_seeds", ())) != partition.seeds:
            raise PairedTrajectoryBlocked("training partition seeds differ")
        signature_counts = Counter(
            event_candidate_support_signature(row.candidates)
            for row in partition.rows
        )
        event_ids = training._event_ids(partition)
    except training.EventRankingBlocked as exc:
        raise PairedTrajectoryBlocked(str(exc)) from exc
    if not signature_counts or not event_ids:
        raise PairedTrajectoryBlocked("training support is empty")
    support_values = [
        {"signature": signature, "training_row_count": count}
        for signature, count in sorted(signature_counts.items())
    ]
    identity = {
        "artifact_bindings": [copy.deepcopy(dict(bindings[name])) for name in sorted(bindings)],
        "dataset": {
            "path": dataset_path.as_posix(),
            "sha256": _sha256_file(dataset_path),
            "size_bytes": dataset_path.stat().st_size,
        },
        "event_ids": list(event_ids),
        "manifest": {
            "path": manifest_path.as_posix(),
            "sha256": _sha256_file(manifest_path),
        },
        "per_signature_counts": {
            signature: count for signature, count in sorted(signature_counts.items())
        },
        "policy_input": policy_input_metadata(),
        "signature_count": len(signature_counts),
        "signature_schema_version": EVENT_SUPPORT_SIGNATURE_SCHEMA_VERSION,
        "support_sha256": _sha256_json(support_values),
    }
    return dict(signature_counts), identity


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
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True,
            capture_output=True, text=True, encoding="ascii",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PairedTrajectoryBlocked("cannot resolve source commit") from exc
    return {
        "commit": commit,
        "files": files,
        "source_sha256": hashlib.sha256(_canonical_bytes(files)).hexdigest(),
    }


def _write_artifacts(
    output: Path,
    *,
    configuration: dict[str, Any],
    pairs: Sequence[Mapping[str, Any]],
    censored: Sequence[Mapping[str, Any]],
    metrics: dict[str, Any],
    report: dict[str, Any],
    manifest_schema_version: str = MANIFEST_SCHEMA_VERSION,
    report_title: str = "Event Ranker Paired Full-Trajectory Shadow",
    selected_label: str = "Event overlay",
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    artifacts = {
        "censored_pairs.json": _canonical_bytes(list(censored)),
        "configuration.json": _canonical_bytes(configuration),
        "metrics.json": _canonical_bytes(metrics),
        "pairs.json": _canonical_bytes(list(pairs)),
        "report.json": _canonical_bytes(report),
    }
    for name, payload in artifacts.items():
        (output / name).write_bytes(payload)
    manifest = {
        "artifacts": [
            {"path": name, "sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}
            for name, payload in sorted(artifacts.items())
        ],
        "schema_version": manifest_schema_version,
    }
    (output / "artifact_manifest.json").write_bytes(_canonical_bytes(manifest))
    lines = [
        f"# {report_title}",
        "",
        f"- Verdict: `{metrics['verdict']}`",
        f"- Charged seconds: `{report['charged_seconds']:.3f}`",
        f"- Complete pairs: `{metrics['complete_pairs']}`",
        f"- Censored pairs: `{metrics['censored_pairs']}`",
        f"- Event-exposed pairs: `{metrics['event_exposed_pairs']}`",
        f"- Override pairs: `{metrics['override_pairs']}`",
        "",
        "| Arm | Victories | Mean floor | Mean return |",
        "| --- | ---: | ---: | ---: |",
        f"| Current | {metrics['current']['victories']} | {metrics['current']['mean_floor']:.6f} | {metrics['current']['mean_return']:.6f} |",
        f"| {selected_label} | {metrics['selected']['victories']} | {metrics['selected']['mean_floor']:.6f} | {metrics['selected']['mean_return']:.6f} |",
        "",
        f"Improved pairs: {metrics['improved_pairs']}; worsened: {metrics['worsened_pairs']}; tied: {metrics['tied_pairs']}; victory gains: {metrics['victory_gains']}; victory losses: {metrics['victory_losses']}.",
    ]
    if "support" in metrics:
        support = metrics["support"]
        lines.extend(
            [
                "",
                "## Training Support",
                "",
                f"Supported sources: {support['supported_sources']}; fallbacks: {support['fallback_sources']}; support-exposed pairs: {support['support_exposed_pairs']}; fallback pairs: {support['fallback_pairs']}.",
            ]
        )
    lines.extend(
        [
            "",
            "This is a no-training simulator shadow. It grants no gameplay, production loading, qualification, or promotion authority.",
            "",
        ]
    )
    (output / "report.md").write_text("\n".join(lines), encoding="ascii", newline="\n")


def execute_cli(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise PairedTrajectoryBlocked("output directory already exists")
    supported_mode = args.command == "run-supported"
    support_signatures: dict[str, int] | None = None
    support_identity: dict[str, Any] | None = None
    if supported_mode:
        support_signatures, support_identity = load_bound_training_support(
            Path(args.training_dir)
        )
    model, training_identity = shadow.load_bound_model(Path(args.training_dir))
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_registration = _read_json(native_registration_path)
    bridge_input = _read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
        current_policy = bridge_input["current_policy"]
    except KeyError as exc:
        raise PairedTrajectoryBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if not metadata_path.is_file() or _sha256_file(metadata_path) != metadata_binding["sha256"]:
        raise PairedTrajectoryBlocked("Current policy metadata bytes differ")
    if list(native_runner._forbidden_processes()):
        raise PairedTrajectoryBlocked("game or CommunicationMod is active")
    environment_factory = native_runner._load_environment_factory(native_identity)
    metadata = current_bridge.MetadataCatalog(metadata_path)

    def session_factory(_seed: int) -> current_bridge.CurrentPolicyBridgeSession:
        return current_bridge.CurrentPolicyBridgeSession(
            metadata=metadata,
            current_policy=current_policy,
            event_semantics_identity=None,
            require_global_metadata_match=True,
            simulator_provenance=native_identity["provenance"],
        )

    pairs, censored, elapsed = collect_pairs(
        environment_factory,
        session_factory,
        model,
        confidence_threshold=training_identity["selected_confidence_threshold"],
        seeds=(SUPPORTED_SEEDS if supported_mode else SEEDS),
        support_signatures=support_signatures,
    )
    if supported_mode:
        metrics, verdict = evaluate_supported_pairs(pairs, censored)
    else:
        metrics, verdict = evaluate_pairs(pairs, censored)
    if list(native_runner._forbidden_processes()):
        raise PairedTrajectoryBlocked("game or CommunicationMod started during execution")
    configuration = {
        "maximum_censored_pairs": MAX_CENSORED_PAIRS,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_decisions": MAX_DECISIONS,
        "minimum_complete_pairs": MIN_COMPLETE_PAIRS,
        "minimum_event_exposed_pairs": MIN_EVENT_EXPOSED_PAIRS,
        "minimum_override_pairs": MIN_OVERRIDE_PAIRS,
        "schema_version": (
            SUPPORTED_SCHEMA_VERSION if supported_mode else SCHEMA_VERSION
        ),
        "seeds": list(SUPPORTED_SEEDS if supported_mode else SEEDS),
    }
    if supported_mode:
        configuration["minimum_support_exposed_pairs"] = MIN_SUPPORT_EXPOSED_PAIRS
    identity = {
        "current_bridge_input": {"path": bridge_input_path.as_posix(), "sha256": _sha256_file(bridge_input_path)},
        "metadata": copy.deepcopy(metadata_binding),
        "native_module": copy.deepcopy(native_identity["module"]),
        "native_registration": {"path": native_registration_path.as_posix(), "sha256": _sha256_file(native_registration_path)},
        "source": _source_identity(repo_root),
        "training": training_identity,
    }
    if supported_mode:
        identity["training_support"] = support_identity
    report = {
        "authority": {"formal_rl": False, "gameplay": False, "policy_loading": False, "promotion": False, "qualification": False},
        "charged_seconds": elapsed,
        "identity": identity,
        "operations": {"communication_mod": False, "gameplay": False, "model_fitting": False, "model_loading": True, "native_loading": True, "production_checkpoint_access": False, "seed_access": True, "training": False},
        "paired_access_count": 1,
        "schema_version": (
            SUPPORTED_SCHEMA_VERSION if supported_mode else SCHEMA_VERSION
        ),
        "verdict": verdict,
    }
    _write_artifacts(
        output,
        configuration=configuration,
        pairs=pairs,
        censored=censored,
        metrics=metrics,
        report=report,
        manifest_schema_version=(
            SUPPORTED_MANIFEST_SCHEMA_VERSION
            if supported_mode
            else MANIFEST_SCHEMA_VERSION
        ),
        report_title=(
            "Supported Event Ranker Paired Full-Trajectory Shadow"
            if supported_mode
            else "Event Ranker Paired Full-Trajectory Shadow"
        ),
        selected_label=("Supported overlay" if supported_mode else "Event overlay"),
    )
    return {"complete_pairs": len(pairs), "output_dir": output.as_posix(), "verdict": verdict}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, output_dir in (
        ("run", DEFAULT_OUTPUT_DIR),
        ("run-supported", SUPPORTED_OUTPUT_DIR),
    ):
        run = subparsers.add_parser(command)
        run.add_argument(
            "--repo-root", default=str(Path(__file__).resolve().parents[1])
        )
        run.add_argument(
            "--native-registration", default=str(DEFAULT_NATIVE_REGISTRATION)
        )
        run.add_argument(
            "--current-bridge-input", default=str(DEFAULT_CURRENT_BRIDGE_INPUT)
        )
        run.add_argument("--training-dir", default=str(DEFAULT_TRAINING_DIR))
        run.add_argument("--output-dir", default=str(output_dir))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command not in {"run", "run-supported"}:
        raise PairedTrajectoryBlocked("unsupported command")
    print(json.dumps(execute_cli(args), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
