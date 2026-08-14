"""Collect supported-domain shop action outcomes without fitting a model."""

from __future__ import annotations

import argparse
import copy
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import logging
import math
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from analysis_scripts.noncombat_native_preload import preload_native_registration


if __name__ == "__main__" and len(sys.argv) >= 2:
    if sys.argv[1] == "run":
        if "--native-registration" in sys.argv:
            _registration = Path(
                sys.argv[sys.argv.index("--native-registration") + 1]
            ).resolve()
        else:
            _registration = Path(
                "reports/noncombat_card_counterfactual_corpus_expansion_20260813_r1/registration.json"
            ).resolve()
        preload_native_registration(_registration)

from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as native_runner
from analysis_scripts import noncombat_current_policy_simulator_bridge as current_bridge
from analysis_scripts import noncombat_event_option_counterfactual_outcomes as event
from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    StateConditionedPolicyInput,
)


DEFAULT_NATIVE_REGISTRATION = event.DEFAULT_NATIVE_REGISTRATION
DEFAULT_CURRENT_BRIDGE_INPUT = event.DEFAULT_CURRENT_BRIDGE_INPUT
DEFAULT_OUTPUT_DIR = Path("reports/noncombat_shop_counterfactual_outcomes_20260814_r1")
SEEDS = tuple(range(95000, 95064))
MAX_SHOP_STATES_PER_SEED = 1
MAX_SOURCE_STATES = 64
MAX_ACTION_BRANCHES = 512
MAX_CENSORED_SOURCES = 32
MAX_DECISIONS_PER_CONTINUATION = 512
MAX_CHARGED_SECONDS = 7_200.0
REPLAY_SOURCE_COUNT = 8
MIN_COMPLETE_SOURCE_STATES = 24
MIN_INFORMATIVE_SOURCE_STATES = 12
MIN_ACTION_KINDS = 4
SCHEMA_VERSION = "noncombat-shop-counterfactual-outcomes-v1"


class ShopOutcomeBlocked(RuntimeError):
    """Raised when the fixed shop outcome collection cannot produce evidence."""


@dataclass(frozen=True)
class ShopOutcomeRow:
    seed: int
    decision_index: int
    source_sha256: str
    current_action_id: str
    action_kinds: tuple[str, ...]
    candidates: tuple[dict[str, Any], ...]
    branch_outcomes: tuple[dict[str, Any], ...]
    replay: dict[str, Any] | None
    state_features: Any | None = None
    candidate_features: Any | None = None

    @property
    def action_returns(self) -> tuple[float, ...]:
        return tuple(float(row["total_return"]) for row in self.branch_outcomes)

    @property
    def informative(self) -> bool:
        return max(self.action_returns) > min(self.action_returns)


@dataclass(frozen=True)
class ShopOutcomeResult:
    rows: tuple[ShopOutcomeRow, ...]
    censored_sources: tuple[dict[str, Any], ...]
    action_branches: int
    root_native_transitions: int
    budget_exhausted: bool
    charged_seconds: float
    checks: dict[str, bool]
    verdict: str


def _canonical_bytes(value: Any) -> bytes:
    try:
        return event._canonical_bytes(value)
    except event.EventOutcomeBlocked as exc:
        raise ShopOutcomeBlocked(str(exc)) from exc


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _candidate_kind(candidate: Mapping[str, Any]) -> str:
    kind = candidate.get("kind")
    if not isinstance(kind, str) or not kind:
        raise ShopOutcomeBlocked("shop candidate kind is missing")
    return kind


def _branch_outcome(
    trace: credit.BranchTrace,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **event._trace_identity(trace),
        "action_sequence_sha256": hashlib.sha256(
            _canonical_bytes(list(trace.action_sequence))
        ).hexdigest(),
        "candidate": copy.deepcopy(dict(candidate)),
        "candidate_sha256": _sha256_json(candidate),
    }


def collect_shop_outcomes(
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[int], Any],
    *,
    seeds: Sequence[int] = SEEDS,
    max_source_states: int = MAX_SOURCE_STATES,
    max_action_branches: int = MAX_ACTION_BRANCHES,
    max_censored_sources: int = MAX_CENSORED_SOURCES,
    max_shop_states_per_seed: int = MAX_SHOP_STATES_PER_SEED,
    replay_source_count: int = REPLAY_SOURCE_COUNT,
    minimum_complete_sources: int = MIN_COMPLETE_SOURCE_STATES,
    minimum_informative_sources: int = MIN_INFORMATIVE_SOURCE_STATES,
    minimum_action_kinds: int = MIN_ACTION_KINDS,
    max_decisions: int = MAX_DECISIONS_PER_CONTINUATION,
    maximum_charged_seconds: float = MAX_CHARGED_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    branch_evaluator: Callable[..., credit.BranchTrace] | None = None,
    projector: Callable[
        [Mapping[str, Any], Sequence[Mapping[str, Any]]],
        StateConditionedPolicyInput,
    ]
    | None = None,
) -> ShopOutcomeResult:
    normalized_seeds = tuple(seeds)
    limits = (
        max_source_states,
        max_action_branches,
        max_censored_sources,
        max_shop_states_per_seed,
        replay_source_count,
        minimum_complete_sources,
        minimum_informative_sources,
        minimum_action_kinds,
        max_decisions,
    )
    if (
        not normalized_seeds
        or len(set(normalized_seeds)) != len(normalized_seeds)
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in limits
        )
        or not math.isfinite(maximum_charged_seconds)
        or maximum_charged_seconds <= 0
    ):
        raise ShopOutcomeBlocked("shop collection configuration is invalid")
    started = float(clock())
    deadline = started + maximum_charged_seconds
    if branch_evaluator is None:
        def branch_evaluator(environment: Any, **kwargs: Any) -> credit.BranchTrace:
            return route.evaluate_action_with_current_continuation(
                environment,
                continuation_session_factory=lambda: session_factory(0),
                **kwargs,
            )

    rows: list[ShopOutcomeRow] = []
    censored: list[dict[str, Any]] = []
    source_hashes: set[str] = set()
    action_branches = 0
    root_transitions = 0
    budget_exhausted = False
    for seed in normalized_seeds:
        if len(rows) >= max_source_states:
            budget_exhausted = True
            break
        if float(clock()) > deadline:
            raise ShopOutcomeBlocked("shop collection deadline reached")
        try:
            environment = environment_factory(seed)
        except Exception as exc:
            raise ShopOutcomeBlocked(
                f"shop environment construction failed for seed {seed}"
            ) from exc
        shop_states = 0
        decision_index = 0
        while True:
            try:
                snapshot, candidates = credit._environment_state(environment)
            except credit.CounterfactualCreditBlocked as exc:
                reason = route._registered_support_blocker(exc)
                if reason is None:
                    raise ShopOutcomeBlocked(str(exc)) from exc
                censored.append(
                    {
                        "decision_index": decision_index,
                        "reason": reason,
                        "seed": seed,
                        "source_sha256": None,
                    }
                )
                if len(censored) > max_censored_sources:
                    raise ShopOutcomeBlocked("shop censor limit exceeded")
                break
            if snapshot["terminal"]:
                break
            if decision_index >= max_decisions:
                raise ShopOutcomeBlocked("shop root decision ceiling reached")
            eligible = (
                snapshot["category"] == "shop"
                and len(candidates) > 1
                and shop_states < max_shop_states_per_seed
            )
            if eligible:
                if len(rows) >= max_source_states or (
                    action_branches + len(candidates) > max_action_branches
                ):
                    budget_exhausted = True
                    break
                source_sha256 = _sha256_json(
                    {"candidate_actions": candidates, "snapshot": snapshot}
                )
                if source_sha256 in source_hashes:
                    raise ShopOutcomeBlocked("shop source identity repeats")
                try:
                    current = session_factory(seed).evaluate(
                        snapshot=snapshot,
                        candidates=candidates,
                        decision_index=decision_index,
                    )
                except Exception as exc:
                    raise ShopOutcomeBlocked(
                        f"shop baseline failed for seed {seed} decision {decision_index}"
                    ) from exc
                current_action_id = current.get("action_id")
                legal_action_ids = {candidate["action_id"] for candidate in candidates}
                if current_action_id not in legal_action_ids:
                    raise ShopOutcomeBlocked("Current shop action is not source legal")
                action_kinds = tuple(_candidate_kind(candidate) for candidate in candidates)
                policy_input: StateConditionedPolicyInput | None = None
                if projector is not None:
                    try:
                        policy_input = projector(snapshot, candidates)
                    except Exception as exc:
                        raise ShopOutcomeBlocked("shop policy projection failed") from exc
                    if (
                        policy_input.state_features.ndim != 1
                        or policy_input.candidate_features.ndim != 2
                        or policy_input.candidate_features.shape[0] != len(candidates)
                        or policy_input.candidate_features.shape[1]
                        != policy_input.state_features.shape[0]
                    ):
                        raise ShopOutcomeBlocked("shop policy projection shape differs")
                traces: list[credit.BranchTrace] = []
                outcomes: list[dict[str, Any]] = []
                censor_reason: str | None = None
                for candidate in candidates:
                    action_branches += 1
                    try:
                        trace = branch_evaluator(
                            environment,
                            action_id=candidate["action_id"],
                            source_category="shop",
                            max_decisions=max_decisions,
                            deadline=deadline,
                            clock=clock,
                        )
                    except credit.CounterfactualCreditBlocked as exc:
                        censor_reason = route._registered_support_blocker(exc)
                        if censor_reason is None:
                            raise ShopOutcomeBlocked(str(exc)) from exc
                        break
                    except Exception as exc:
                        raise ShopOutcomeBlocked("shop branch evaluation failed") from exc
                    traces.append(trace)
                    outcomes.append(_branch_outcome(trace, candidate))
                replay: dict[str, Any] | None = None
                if censor_reason is None and len(rows) < replay_source_count:
                    try:
                        repeated = branch_evaluator(
                            environment,
                            action_id=candidates[0]["action_id"],
                            source_category="shop",
                            max_decisions=max_decisions,
                            deadline=deadline,
                            clock=clock,
                        )
                    except credit.CounterfactualCreditBlocked as exc:
                        censor_reason = route._registered_support_blocker(exc)
                        if censor_reason is None:
                            raise ShopOutcomeBlocked(str(exc)) from exc
                    except Exception as exc:
                        raise ShopOutcomeBlocked("shop replay failed") from exc
                    else:
                        expected = event._trace_identity(traces[0])
                        actual = event._trace_identity(repeated)
                        replay = {
                            "action_id": candidates[0]["action_id"],
                            "actual_sha256": _sha256_json(actual),
                            "expected_sha256": _sha256_json(expected),
                            "passed": actual == expected,
                        }
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
                        raise ShopOutcomeBlocked("shop censor limit exceeded")
                else:
                    if len(outcomes) != len(candidates):
                        raise ShopOutcomeBlocked("shop source row is incomplete")
                    rows.append(
                        ShopOutcomeRow(
                            seed=seed,
                            decision_index=decision_index,
                            source_sha256=source_sha256,
                            current_action_id=str(current_action_id),
                            action_kinds=action_kinds,
                            candidates=tuple(copy.deepcopy(candidates)),
                            branch_outcomes=tuple(outcomes),
                            replay=replay,
                            state_features=(
                                policy_input.state_features.detach().clone()
                                if policy_input is not None
                                else None
                            ),
                            candidate_features=(
                                policy_input.candidate_features.detach().clone()
                                if policy_input is not None
                                else None
                            ),
                        )
                    )
                    source_hashes.add(source_sha256)
                    shop_states += 1
            if budget_exhausted:
                break
            try:
                environment, _ = credit._advance_native(environment)
            except credit.CounterfactualCreditBlocked as exc:
                reason = route._registered_support_blocker(exc)
                if reason is None:
                    raise ShopOutcomeBlocked(str(exc)) from exc
                censored.append(
                    {
                        "decision_index": decision_index,
                        "reason": reason,
                        "seed": seed,
                        "source_sha256": None,
                    }
                )
                if len(censored) > max_censored_sources:
                    raise ShopOutcomeBlocked("shop censor limit exceeded")
                break
            root_transitions += 1
            decision_index += 1
        if budget_exhausted:
            break

    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > maximum_charged_seconds:
        raise ShopOutcomeBlocked("shop charged time differs")
    informative = sum(row.informative for row in rows)
    action_kinds = {kind for row in rows for kind in row.action_kinds}
    replays = [row.replay for row in rows if row.replay is not None]
    checks = {
        "action_kind_floor": len(action_kinds) >= minimum_action_kinds,
        "complete_source_floor": len(rows) >= minimum_complete_sources,
        "informative_source_floor": informative >= minimum_informative_sources,
        "replay_count": len(replays) == replay_source_count,
        "replay_identity": bool(replays) and all(row["passed"] for row in replays),
    }
    verdict = (
        "shop_counterfactual_signal_viable_for_learning_proposal"
        if all(checks.values())
        else "shop_counterfactual_signal_not_viable"
    )
    return ShopOutcomeResult(
        rows=tuple(rows),
        censored_sources=tuple(censored),
        action_branches=action_branches,
        root_native_transitions=root_transitions,
        budget_exhausted=budget_exhausted,
        charged_seconds=elapsed,
        checks=checks,
        verdict=verdict,
    )


def _summary(result: ShopOutcomeResult) -> dict[str, Any]:
    spreads = [max(row.action_returns) - min(row.action_returns) for row in result.rows]
    kind_counts = Counter(kind for row in result.rows for kind in row.action_kinds)
    return {
        "action_branches": result.action_branches,
        "action_kind_counts": dict(sorted(kind_counts.items())),
        "action_kinds": sorted(kind_counts),
        "budget_exhausted": result.budget_exhausted,
        "censored_sources": len(result.censored_sources),
        "censor_reasons": dict(
            sorted(Counter(row["reason"] for row in result.censored_sources).items())
        ),
        "complete_source_states": len(result.rows),
        "informative_source_states": sum(row.informative for row in result.rows),
        "replay_passed": sum(
            bool(row.replay and row.replay["passed"]) for row in result.rows
        ),
        "return_spread_maximum": max(spreads) if spreads else None,
        "return_spread_mean": math.fsum(spreads) / len(spreads) if spreads else None,
        "root_native_transitions": result.root_native_transitions,
    }


BOUND_SOURCE_PATHS = (
    Path("analysis_scripts/noncombat_shop_counterfactual_outcomes.py"),
    *event.BOUND_SOURCE_PATHS,
)


def _write_artifacts(
    output: Path,
    result: ShopOutcomeResult,
    *,
    configuration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    rows = []
    for row in result.rows:
        serialized = asdict(row)
        state_features = serialized.pop("state_features")
        candidate_features = serialized.pop("candidate_features")
        if (state_features is None) != (candidate_features is None):
            raise ShopOutcomeBlocked("shop row feature presence differs")
        if state_features is not None:
            serialized["state_features"] = route._encode_sparse_tensor(
                row.state_features
            )
            serialized["candidate_features"] = route._encode_sparse_tensor(
                row.candidate_features
            )
        rows.append(serialized)
    summary = _summary(result)
    report = {
        "authority": {
            "formal_rl": False,
            "gameplay": False,
            "model_fitting": False,
            "policy_loading": False,
            "promotion": False,
            "qualification": False,
            "training": False,
        },
        "charged_seconds": result.charged_seconds,
        "checks": copy.deepcopy(result.checks),
        "identity": copy.deepcopy(dict(identity)),
        "operations": {
            "communication_mod": False,
            "gameplay": False,
            "model_fitting": False,
            "native_loading": True,
            "production_checkpoint_access": False,
            "seed_access": True,
            "training": False,
        },
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
        "verdict": result.verdict,
    }
    artifacts = {
        "censored_sources.json": _canonical_bytes(list(result.censored_sources)),
        "configuration.json": _canonical_bytes(configuration),
        "report.json": _canonical_bytes(report),
        "source_rows.json": _canonical_bytes(rows),
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
        "schema_version": "noncombat-shop-counterfactual-manifest-v1",
    }
    (output / "artifact_manifest.json").write_bytes(_canonical_bytes(manifest))
    markdown = "\n".join(
        (
            "# Shop Counterfactual Outcomes",
            "",
            f"- Verdict: `{result.verdict}`",
            f"- Charged seconds: `{result.charged_seconds:.3f}`",
            f"- Complete sources: `{summary['complete_source_states']}`",
            f"- Informative sources: `{summary['informative_source_states']}`",
            f"- Action kinds: `{', '.join(summary['action_kinds'])}`",
            f"- Replay passed: `{summary['replay_passed']}`",
            f"- Censored sources: `{summary['censored_sources']}`",
            "",
            "This is supported-domain A0 action-level simulator evidence under frozen Current continuation. It excludes Courier replacement semantics and grants no training, gameplay, policy-quality, qualification, or promotion authority.",
            "",
        )
    )
    (output / "report.md").write_text(markdown, encoding="ascii", newline="\n")


def _source_identity(repo_root: Path) -> dict[str, Any]:
    files = [
        {
            "path": path.as_posix(),
            "sha256": event._sha256_file(repo_root / path),
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
        raise ShopOutcomeBlocked("cannot resolve source commit") from exc
    return {"commit": commit, "files": files, "source_sha256": _sha256_json(files)}


def execute_cli(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise ShopOutcomeBlocked("output directory already exists")
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_registration = event._read_json(native_registration_path)
    bridge_input = event._read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
        current_policy = bridge_input["current_policy"]
    except KeyError as exc:
        raise ShopOutcomeBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if (
        not metadata_path.is_file()
        or event._sha256_file(metadata_path) != metadata_binding["sha256"]
    ):
        raise ShopOutcomeBlocked("Current policy metadata bytes differ")
    if list(native_runner._forbidden_processes()):
        raise ShopOutcomeBlocked("game or CommunicationMod is active")
    if "sts_lightspeed_noncombat_adapter" not in sys.modules:
        preload_native_registration(native_registration_path)
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

    result = collect_shop_outcomes(environment_factory, session_factory)
    if list(native_runner._forbidden_processes()):
        raise ShopOutcomeBlocked("game or CommunicationMod started during execution")
    configuration = {
        "ascension": 0,
        "maximum_action_branches": MAX_ACTION_BRANCHES,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_shop_states_per_seed": MAX_SHOP_STATES_PER_SEED,
        "maximum_source_states": MAX_SOURCE_STATES,
        "replay_source_count": REPLAY_SOURCE_COUNT,
        "reward": "strict-primary-dominance:2*victory+floor/57",
        "schema_version": SCHEMA_VERSION,
        "seeds": list(SEEDS),
        "support_exclusions": [
            "courier_restock_semantics",
            "invalid_potion_transactions",
            "non_a0_pricing",
        ],
        "viability_floors": {
            "action_kinds": MIN_ACTION_KINDS,
            "complete_sources": MIN_COMPLETE_SOURCE_STATES,
            "informative_sources": MIN_INFORMATIVE_SOURCE_STATES,
            "replays": REPLAY_SOURCE_COUNT,
        },
    }
    identity = {
        "current_bridge_input": {
            "path": bridge_input_path.as_posix(),
            "sha256": event._sha256_file(bridge_input_path),
        },
        "metadata": copy.deepcopy(metadata_binding),
        "native_module": copy.deepcopy(native_identity["module"]),
        "native_registration": {
            "path": native_registration_path.as_posix(),
            "sha256": event._sha256_file(native_registration_path),
        },
        "source": _source_identity(repo_root),
    }
    _write_artifacts(output, result, configuration=configuration, identity=identity)
    summary = _summary(result)
    return {
        "action_kinds": summary["action_kinds"],
        "complete_source_states": summary["complete_source_states"],
        "informative_source_states": summary["informative_source_states"],
        "output_dir": output.as_posix(),
        "verdict": result.verdict,
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
        raise ShopOutcomeBlocked("unsupported command")
    print(json.dumps(execute_cli(args), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
