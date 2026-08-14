"""Collect outcome-backed event-option branches without fitting a model."""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
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
    "reports/noncombat_event_option_counterfactual_outcomes_20260814_r1"
)
SEEDS = tuple(range(94000, 94064))
MAX_EVENT_STATES_PER_SEED = 2
MAX_SOURCE_STATES = 128
MAX_ACTION_BRANCHES = 512
MAX_CENSORED_SOURCES = 32
MAX_DECISIONS_PER_CONTINUATION = 512
MAX_CHARGED_SECONDS = 7_200.0
REPLAY_SOURCE_COUNT = 16
MIN_COMPLETE_SOURCE_STATES = 64
MIN_INFORMATIVE_SOURCE_STATES = 32
MIN_DISTINCT_EVENT_IDS = 8
SCHEMA_VERSION = "noncombat-event-option-counterfactual-outcomes-v1"


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


def preload_native_registration(registration_path: Path) -> None:
    from analysis_scripts.noncombat_native_preload import preload_native_registration as load

    load(registration_path)


def _early_preload_native() -> None:
    if not (
        __name__ == "__main__"
        and len(sys.argv) >= 2
        and sys.argv[1] == "run"
    ):
        return
    if "--native-registration" in sys.argv:
        registration_path = Path(
            sys.argv[sys.argv.index("--native-registration") + 1]
        ).resolve()
    else:
        registration_path = DEFAULT_NATIVE_REGISTRATION.resolve()
    preload_native_registration(registration_path)


if __name__ == "__main__":
    _bootstrap_direct_script_imports()
    _early_preload_native()


from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as native_runner
from analysis_scripts import noncombat_current_policy_simulator_bridge as current_bridge
from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts import noncombat_simulator_adapter as adapter


class EventOutcomeBlocked(RuntimeError):
    """Raised when the fixed event outcome POC cannot produce valid evidence."""


@dataclass(frozen=True)
class EventOutcomeRow:
    seed: int
    decision_index: int
    source_sha256: str
    event_id: str
    event_name: str
    semantics_source: str
    current_action_id: str
    candidates: tuple[dict[str, Any], ...]
    branch_outcomes: tuple[dict[str, Any], ...]
    replay: dict[str, Any] | None

    @property
    def action_returns(self) -> tuple[float, ...]:
        return tuple(float(row["total_return"]) for row in self.branch_outcomes)

    @property
    def informative(self) -> bool:
        return max(self.action_returns) > min(self.action_returns)


@dataclass(frozen=True)
class EventOutcomeResult:
    rows: tuple[EventOutcomeRow, ...]
    censored_sources: tuple[dict[str, Any], ...]
    action_branches: int
    root_native_transitions: int
    budget_exhausted: bool
    charged_seconds: float
    checks: dict[str, bool]
    verdict: str


def _canonical_bytes(value: Any) -> bytes:
    try:
        return adapter.canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise EventOutcomeBlocked("artifact is not canonical JSON") from exc


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _trace_identity(trace: credit.BranchTrace) -> dict[str, Any]:
    return {
        "action_id": trace.action_id,
        "action_sequence": list(trace.action_sequence),
        "floor_progress": trace.floor_progress,
        "initial_transition_sha256": trace.initial_transition_sha256,
        "terminal_state_sha256": trace.terminal_state_sha256,
        "terminal_summary": copy.deepcopy(trace.terminal_summary),
        "terminal_victory": trace.terminal_victory,
        "total_return": trace.total_return,
        "transition_count": trace.transition_count,
    }


def _branch_outcome(
    trace: credit.BranchTrace, candidate: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        **_trace_identity(trace),
        "action_sequence_sha256": hashlib.sha256(
            _canonical_bytes(list(trace.action_sequence))
        ).hexdigest(),
        "candidate": copy.deepcopy(dict(candidate)),
        "candidate_sha256": _sha256_json(candidate),
    }


def _event_identity(
    snapshot: Mapping[str, Any], evaluation: Mapping[str, Any]
) -> tuple[str, str, str]:
    state = snapshot.get("state")
    context = state.get("decision_context") if isinstance(state, Mapping) else None
    if not isinstance(context, Mapping):
        raise EventOutcomeBlocked("event decision context is missing")
    event_id = context.get("event_id")
    event_name = context.get("event_name")
    semantics_source = evaluation.get("event_semantics_source")
    observation = evaluation.get("event_observation")
    if isinstance(observation, Mapping):
        event_id = observation.get("current_event_id", event_id)
    if not all(isinstance(value, str) and value for value in (event_id, event_name, semantics_source)):
        raise EventOutcomeBlocked("event semantic identity is incomplete")
    return str(event_id), str(event_name), str(semantics_source)


def collect_event_outcomes(
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[int], Any],
    *,
    seeds: Sequence[int] = SEEDS,
    max_source_states: int = MAX_SOURCE_STATES,
    max_action_branches: int = MAX_ACTION_BRANCHES,
    max_censored_sources: int = MAX_CENSORED_SOURCES,
    max_event_states_per_seed: int = MAX_EVENT_STATES_PER_SEED,
    replay_source_count: int = REPLAY_SOURCE_COUNT,
    minimum_complete_sources: int = MIN_COMPLETE_SOURCE_STATES,
    minimum_informative_sources: int = MIN_INFORMATIVE_SOURCE_STATES,
    minimum_distinct_events: int = MIN_DISTINCT_EVENT_IDS,
    max_decisions: int = MAX_DECISIONS_PER_CONTINUATION,
    maximum_charged_seconds: float = MAX_CHARGED_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    branch_evaluator: Callable[..., credit.BranchTrace] | None = None,
) -> EventOutcomeResult:
    normalized_seeds = tuple(seeds)
    limits = (
        max_source_states,
        max_action_branches,
        max_censored_sources,
        max_event_states_per_seed,
        replay_source_count,
        minimum_complete_sources,
        minimum_informative_sources,
        minimum_distinct_events,
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
        raise EventOutcomeBlocked("event POC configuration is invalid")
    started = float(clock())
    deadline = started + maximum_charged_seconds
    if branch_evaluator is None:
        def branch_evaluator(environment: Any, **kwargs: Any) -> credit.BranchTrace:
            return route.evaluate_action_with_current_continuation(
                environment,
                continuation_session_factory=lambda: session_factory(0),
                **kwargs,
            )

    rows: list[EventOutcomeRow] = []
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
            raise EventOutcomeBlocked("event POC deadline reached")
        try:
            environment = environment_factory(seed)
        except Exception as exc:
            raise EventOutcomeBlocked(
                f"event environment construction failed for seed {seed}"
            ) from exc
        event_states = 0
        decision_index = 0
        while True:
            snapshot, candidates = credit._environment_state(environment)
            if snapshot["terminal"]:
                break
            if decision_index >= max_decisions:
                raise EventOutcomeBlocked("event root decision ceiling reached")
            eligible = (
                snapshot["category"] == "event"
                and len(candidates) > 1
                and event_states < max_event_states_per_seed
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
                    raise EventOutcomeBlocked("event source identity repeats")
                try:
                    current = session_factory(seed).evaluate(
                        snapshot=snapshot,
                        candidates=candidates,
                        decision_index=decision_index,
                    )
                    event_id, event_name, semantics_source = _event_identity(
                        snapshot, current
                    )
                except Exception as exc:
                    raise EventOutcomeBlocked(
                        f"event baseline failed for seed {seed} decision {decision_index}"
                    ) from exc
                current_action_id = current.get("action_id")
                if current_action_id not in {
                    candidate["action_id"] for candidate in candidates
                }:
                    raise EventOutcomeBlocked("Current event action is not source legal")
                traces: list[credit.BranchTrace] = []
                outcomes: list[dict[str, Any]] = []
                censor_reason: str | None = None
                for candidate in candidates:
                    action_branches += 1
                    try:
                        trace = branch_evaluator(
                            environment,
                            action_id=candidate["action_id"],
                            source_category="event",
                            max_decisions=max_decisions,
                            deadline=deadline,
                            clock=clock,
                        )
                    except credit.CounterfactualCreditBlocked as exc:
                        censor_reason = route._registered_support_blocker(exc)
                        if censor_reason is None:
                            raise EventOutcomeBlocked(str(exc)) from exc
                        break
                    except Exception as exc:
                        raise EventOutcomeBlocked(
                            "event branch evaluation failed"
                        ) from exc
                    traces.append(trace)
                    outcomes.append(_branch_outcome(trace, candidate))
                replay: dict[str, Any] | None = None
                if censor_reason is None and len(rows) < replay_source_count:
                    try:
                        repeated = branch_evaluator(
                            environment,
                            action_id=candidates[0]["action_id"],
                            source_category="event",
                            max_decisions=max_decisions,
                            deadline=deadline,
                            clock=clock,
                        )
                    except credit.CounterfactualCreditBlocked as exc:
                        censor_reason = route._registered_support_blocker(exc)
                        if censor_reason is None:
                            raise EventOutcomeBlocked(str(exc)) from exc
                    except Exception as exc:
                        raise EventOutcomeBlocked("event replay failed") from exc
                    else:
                        expected = _trace_identity(traces[0])
                        actual = _trace_identity(repeated)
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
                            "event_id": event_id,
                            "reason": censor_reason,
                            "seed": seed,
                            "source_sha256": source_sha256,
                        }
                    )
                    if len(censored) > max_censored_sources:
                        raise EventOutcomeBlocked("event censor limit exceeded")
                else:
                    if len(outcomes) != len(candidates):
                        raise EventOutcomeBlocked("event source row is incomplete")
                    rows.append(
                        EventOutcomeRow(
                            seed=seed,
                            decision_index=decision_index,
                            source_sha256=source_sha256,
                            event_id=event_id,
                            event_name=event_name,
                            semantics_source=semantics_source,
                            current_action_id=str(current_action_id),
                            candidates=tuple(copy.deepcopy(candidates)),
                            branch_outcomes=tuple(outcomes),
                            replay=replay,
                        )
                    )
                    source_hashes.add(source_sha256)
                    event_states += 1
            if budget_exhausted:
                break
            try:
                environment, _ = credit._advance_native(environment)
            except credit.CounterfactualCreditBlocked as exc:
                reason = route._registered_support_blocker(exc)
                if reason is None:
                    raise EventOutcomeBlocked(str(exc)) from exc
                censored.append(
                    {
                        "decision_index": decision_index,
                        "event_id": None,
                        "reason": reason,
                        "seed": seed,
                        "source_sha256": None,
                    }
                )
                if len(censored) > max_censored_sources:
                    raise EventOutcomeBlocked("event censor limit exceeded")
                break
            root_transitions += 1
            decision_index += 1
        if budget_exhausted:
            break

    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > maximum_charged_seconds:
        raise EventOutcomeBlocked("event charged time differs")
    informative = sum(row.informative for row in rows)
    event_ids = {row.event_id for row in rows}
    replays = [row.replay for row in rows if row.replay is not None]
    checks = {
        "complete_source_floor": len(rows) >= minimum_complete_sources,
        "distinct_event_floor": len(event_ids) >= minimum_distinct_events,
        "informative_source_floor": informative >= minimum_informative_sources,
        "replay_count": len(replays) == replay_source_count,
        "replay_identity": bool(replays) and all(row["passed"] for row in replays),
    }
    verdict = (
        "event_option_counterfactual_signal_viable_for_learning_proposal"
        if all(checks.values())
        else "event_option_counterfactual_signal_not_viable"
    )
    return EventOutcomeResult(
        rows=tuple(rows),
        censored_sources=tuple(censored),
        action_branches=action_branches,
        root_native_transitions=root_transitions,
        budget_exhausted=budget_exhausted,
        charged_seconds=elapsed,
        checks=checks,
        verdict=verdict,
    )


def _summary(result: EventOutcomeResult) -> dict[str, Any]:
    spreads = [max(row.action_returns) - min(row.action_returns) for row in result.rows]
    event_counts = Counter(row.event_id for row in result.rows)
    semantics_counts = Counter(row.semantics_source for row in result.rows)
    return {
        "action_branches": result.action_branches,
        "budget_exhausted": result.budget_exhausted,
        "censored_sources": len(result.censored_sources),
        "censor_reasons": dict(sorted(Counter(row["reason"] for row in result.censored_sources).items())),
        "complete_source_states": len(result.rows),
        "distinct_event_ids": len(event_counts),
        "event_counts": dict(sorted(event_counts.items())),
        "informative_source_states": sum(row.informative for row in result.rows),
        "replay_passed": sum(bool(row.replay and row.replay["passed"]) for row in result.rows),
        "return_spread_maximum": max(spreads) if spreads else None,
        "return_spread_mean": math.fsum(spreads) / len(spreads) if spreads else None,
        "root_native_transitions": result.root_native_transitions,
        "semantics_source_counts": dict(sorted(semantics_counts.items())),
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EventOutcomeBlocked(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise EventOutcomeBlocked(f"JSON root must be an object: {path}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


BOUND_SOURCE_PATHS = (
    Path("analysis_scripts/noncombat_event_option_counterfactual_outcomes.py"),
    Path("analysis_scripts/noncombat_native_preload.py"),
    *route.BOUND_SOURCE_PATHS,
    Path("analysis_scripts/noncombat_event_option_semantics.py"),
)


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
        raise EventOutcomeBlocked("cannot resolve source commit") from exc
    return {"commit": commit, "files": files, "source_sha256": _sha256_json(files)}


def _write_artifacts(
    output: Path,
    result: EventOutcomeResult,
    *,
    configuration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    rows = [asdict(row) for row in result.rows]
    summary = _summary(result)
    report = {
        "authority": {
            "formal_rl": False,
            "gameplay": False,
            "model_fitting": False,
            "policy_loading": False,
            "promotion": False,
            "qualification": False,
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
        "schema_version": "noncombat-event-option-counterfactual-manifest-v1",
    }
    (output / "artifact_manifest.json").write_bytes(_canonical_bytes(manifest))
    markdown = "\n".join(
        (
            "# Event Option Counterfactual Outcomes",
            "",
            f"- Verdict: `{result.verdict}`",
            f"- Charged seconds: `{result.charged_seconds:.3f}`",
            f"- Complete sources: `{summary['complete_source_states']}`",
            f"- Informative sources: `{summary['informative_source_states']}`",
            f"- Distinct events: `{summary['distinct_event_ids']}`",
            f"- Replay passed: `{summary['replay_passed']}`",
            f"- Censored sources: `{summary['censored_sources']}`",
            "",
            "This is action-level simulator outcome evidence under frozen Current-policy continuation. It does not establish policy quality or authorize training, gameplay, loading, qualification, or promotion.",
            "",
        )
    )
    (output / "report.md").write_text(markdown, encoding="ascii", newline="\n")


def execute_cli(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise EventOutcomeBlocked("output directory already exists")
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_registration = _read_json(native_registration_path)
    bridge_input = _read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
        current_policy = bridge_input["current_policy"]
    except KeyError as exc:
        raise EventOutcomeBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if not metadata_path.is_file() or _sha256_file(metadata_path) != metadata_binding["sha256"]:
        raise EventOutcomeBlocked("Current policy metadata bytes differ")
    if list(native_runner._forbidden_processes()):
        raise EventOutcomeBlocked("game or CommunicationMod is active")
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

    result = collect_event_outcomes(environment_factory, session_factory)
    if list(native_runner._forbidden_processes()):
        raise EventOutcomeBlocked("game or CommunicationMod started during execution")
    configuration = {
        "maximum_action_branches": MAX_ACTION_BRANCHES,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_event_states_per_seed": MAX_EVENT_STATES_PER_SEED,
        "maximum_source_states": MAX_SOURCE_STATES,
        "replay_source_count": REPLAY_SOURCE_COUNT,
        "reward": "strict-primary-dominance:2*victory+floor/57",
        "schema_version": SCHEMA_VERSION,
        "seeds": list(SEEDS),
        "viability_floors": {
            "complete_sources": MIN_COMPLETE_SOURCE_STATES,
            "distinct_event_ids": MIN_DISTINCT_EVENT_IDS,
            "informative_sources": MIN_INFORMATIVE_SOURCE_STATES,
            "replays": REPLAY_SOURCE_COUNT,
        },
    }
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
    _write_artifacts(
        output,
        result,
        configuration=configuration,
        identity=identity,
    )
    summary = _summary(result)
    return {
        "complete_source_states": summary["complete_source_states"],
        "distinct_event_ids": summary["distinct_event_ids"],
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
        raise EventOutcomeBlocked("unsupported command")
    print(json.dumps(execute_cli(args), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
