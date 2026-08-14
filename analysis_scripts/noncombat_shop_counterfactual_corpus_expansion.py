"""Collect one fixed independent expansion of shop counterfactual outcomes."""

from __future__ import annotations

import argparse
import copy
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import logging
import math
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from analysis_scripts.noncombat_native_preload import preload_native_registration


_DEFAULT_NATIVE_REGISTRATION = Path(
    "reports/noncombat_card_counterfactual_corpus_expansion_20260813_r1/registration.json"
)
if __name__ == "__main__" and len(sys.argv) >= 2 and sys.argv[1] == "run":
    if "--native-registration" in sys.argv:
        _registration = Path(
            sys.argv[sys.argv.index("--native-registration") + 1]
        ).resolve()
    else:
        _registration = _DEFAULT_NATIVE_REGISTRATION.resolve()
    preload_native_registration(_registration)


from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as native_runner
from analysis_scripts import noncombat_cross_validated_shop_ensemble as historical
from analysis_scripts import noncombat_current_policy_simulator_bridge as current_bridge
from analysis_scripts import noncombat_event_option_counterfactual_outcomes as event
from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts import noncombat_state_conditioned_shop_ranking as ranking


DEFAULT_NATIVE_REGISTRATION = event.DEFAULT_NATIVE_REGISTRATION
DEFAULT_CURRENT_BRIDGE_INPUT = event.DEFAULT_CURRENT_BRIDGE_INPUT
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_shop_counterfactual_corpus_expansion_20260814_r1"
)
EXPANSION_SEEDS = tuple(range(95556, 96324))
RESERVED_FRESH_SEEDS = tuple(range(95492, 95556))
MAX_SOURCE_STATES = 384
MAX_ACTION_BRANCHES = 6_144
MAX_CENSORED_SOURCES = 384
REPLAY_SOURCE_COUNT = 16
MIN_COMPLETE_SOURCES = 384
MIN_INFORMATIVE_SOURCES = 192
MIN_ACTION_KINDS = 4
MAX_CHARGED_SECONDS = 28_800.0
SCHEMA_VERSION = "noncombat-shop-counterfactual-corpus-expansion-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-shop-counterfactual-corpus-expansion-manifest-v1"
BOUND_SOURCE_PATHS = tuple(
    dict.fromkeys(
        (
            Path(
                "analysis_scripts/noncombat_shop_counterfactual_corpus_expansion.py"
            ),
            Path("analysis_scripts/noncombat_cross_validated_shop_ensemble.py"),
            *ranking.BOUND_SOURCE_PATHS,
        )
    )
)


class ShopCorpusExpansionBlocked(RuntimeError):
    """Raised when the fixed shop expansion cannot publish valid evidence."""


@dataclass(frozen=True)
class ShopCorpusExpansionResult:
    configuration: dict[str, Any]
    dataset: route.RoutePartition
    metrics: dict[str, Any]
    report: dict[str, Any]


def _canonical_bytes(value: Any) -> bytes:
    return event._canonical_bytes(value)


def _sha256_file(path: Path) -> str:
    return event._sha256_file(path)


def _configuration(corpus: historical.HistoricalCorpus) -> dict[str, Any]:
    return {
        "expansion_seeds": list(EXPANSION_SEEDS),
        "historical_bindings": copy.deepcopy(corpus.audit["bindings"]),
        "maximum_action_branches": MAX_ACTION_BRANCHES,
        "maximum_censored_sources": MAX_CENSORED_SOURCES,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_source_states": MAX_SOURCE_STATES,
        "minimum_action_kinds": MIN_ACTION_KINDS,
        "minimum_complete_sources": MIN_COMPLETE_SOURCES,
        "minimum_informative_sources": MIN_INFORMATIVE_SOURCES,
        "replay_source_count": REPLAY_SOURCE_COUNT,
        "reserved_fresh_seeds": list(RESERVED_FRESH_SEEDS),
        "schema_version": SCHEMA_VERSION,
    }


def collect_expansion(
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[int], Any],
    corpus: historical.HistoricalCorpus,
    *,
    expansion_seeds: Sequence[int] = EXPANSION_SEEDS,
    maximum_charged_seconds: float = MAX_CHARGED_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    branch_evaluator: Callable[..., Any] | None = None,
) -> ShopCorpusExpansionResult:
    schedule = tuple(expansion_seeds)
    if (
        schedule != EXPANSION_SEEDS
        or len(set(schedule)) != len(schedule)
        or set(schedule).intersection(RESERVED_FRESH_SEEDS)
    ):
        raise ShopCorpusExpansionBlocked("shop expansion seed schedule differs")
    if len(corpus.rows) != 112 or corpus.audit.get("feature_width") != 1024:
        raise ShopCorpusExpansionBlocked("historical shop support differs")
    started = float(clock())
    try:
        dataset = ranking._collect_partition(
            environment_factory,
            session_factory,
            name="train",
            seeds=schedule,
            max_source_states=MAX_SOURCE_STATES,
            max_action_branches=MAX_ACTION_BRANCHES,
            max_censored_sources=MAX_CENSORED_SOURCES,
            replay_source_count=REPLAY_SOURCE_COUNT,
            minimum_complete_sources=MIN_COMPLETE_SOURCES,
            minimum_informative_sources=MIN_INFORMATIVE_SOURCES,
            maximum_charged_seconds=maximum_charged_seconds,
            clock=clock,
            branch_evaluator=branch_evaluator,
        )
    except ranking.StateConditionedShopBlocked as exc:
        raise ShopCorpusExpansionBlocked(str(exc)) from exc
    historical_hashes = {row.source_sha256 for row in corpus.rows}
    expansion_hashes = [row.source_sha256 for row in dataset.rows]
    if len(expansion_hashes) != len(set(expansion_hashes)):
        raise ShopCorpusExpansionBlocked("shop expansion source identities overlap")
    if historical_hashes.intersection(expansion_hashes):
        raise ShopCorpusExpansionBlocked("shop expansion overlaps historical sources")
    feature_widths = {int(row.state_features.shape[0]) for row in dataset.rows}
    candidate_widths = {
        int(row.candidate_features.shape[1]) for row in dataset.rows
    }
    if feature_widths != {1024} or candidate_widths != {1024}:
        raise ShopCorpusExpansionBlocked("shop expansion feature boundary differs")
    action_kinds = Counter(
        str(candidate["kind"])
        for row in dataset.rows
        for candidate in row.candidates
    )
    informative_sources = sum(row.informative for row in dataset.rows)
    checks = {
        "action_kind_support": len(action_kinds) >= MIN_ACTION_KINDS,
        "action_branch_bound": dataset.action_branches <= MAX_ACTION_BRANCHES,
        "complete_source_support": len(dataset.rows) == MAX_SOURCE_STATES,
        "historical_independence": not historical_hashes.intersection(expansion_hashes),
        "informative_source_support": informative_sources >= MIN_INFORMATIVE_SOURCES,
        "replay_support": REPLAY_SOURCE_COUNT == 16,
        "unique_source_support": len(expansion_hashes) == len(set(expansion_hashes)),
    }
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > maximum_charged_seconds:
        raise ShopCorpusExpansionBlocked("shop expansion charged time differs")
    verdict = (
        "shop_counterfactual_expansion_ready_for_retraining_proposal"
        if all(checks.values())
        else "shop_counterfactual_expansion_not_ready"
    )
    metrics = {
        "action_kinds": dict(sorted(action_kinds.items())),
        "checks": checks,
        "combined_source_count": len(corpus.rows) + len(dataset.rows),
        "expansion_source_count": len(dataset.rows),
        "historical_source_count": len(corpus.rows),
        "informative_source_count": informative_sources,
        "verdict": verdict,
    }
    report = {
        "authority": {
            "evaluation": False,
            "formal_rl": False,
            "policy_quality": False,
            "promotion": False,
            "retraining_proposal": all(checks.values()),
            "training": False,
        },
        "charged_seconds": elapsed,
        "dataset": ranking._partition_summary(dataset),
        "operations": {
            "communication_mod": False,
            "fresh_evaluation_seed_access": False,
            "gameplay": False,
            "historical_corpus_access": True,
            "model_fitting": False,
            "model_loading": False,
            "native_loading": True,
            "production_checkpoint_access": False,
            "protected_seed_access": False,
            "training": False,
        },
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
    }
    return ShopCorpusExpansionResult(
        configuration=_configuration(corpus),
        dataset=dataset,
        metrics=metrics,
        report=report,
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
        raise ShopCorpusExpansionBlocked("cannot resolve source commit") from exc
    return {
        "commit": commit,
        "files": files,
        "source_sha256": hashlib.sha256(_canonical_bytes(files)).hexdigest(),
    }


def write_artifacts(
    output: Path,
    result: ShopCorpusExpansionResult,
    identity: Mapping[str, Any],
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    metrics = result.metrics
    report = {**result.report, "identity": copy.deepcopy(dict(identity))}
    markdown = "\n".join(
        (
            "# Shop Counterfactual Corpus Expansion",
            "",
            f"- Verdict: `{result.report['verdict']}`",
            f"- Historical/expansion/combined sources: `{metrics['historical_source_count']}/{metrics['expansion_source_count']}/{metrics['combined_source_count']}`",
            f"- Informative sources: `{metrics['informative_source_count']}`",
            f"- Action kinds: `{len(metrics['action_kinds'])}`",
            f"- Action branches: `{result.report['dataset']['action_branches']}`",
            "",
            "No learned model was trained or evaluated by this collection run.",
            "",
        )
    ).encode("ascii")
    artifacts = {
        "configuration.json": _canonical_bytes(result.configuration),
        "dataset.json": route.encode_partition(result.dataset),
        "metrics.json": _canonical_bytes(result.metrics),
        "report.json": _canonical_bytes(report),
        "report.md": markdown,
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
        "schema_version": MANIFEST_SCHEMA_VERSION,
    }
    (output / "artifact_manifest.json").write_bytes(_canonical_bytes(manifest))


def _load_registered_inputs(
    native_registration_path: Path,
    bridge_input_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    native_registration = event._read_json(native_registration_path)
    bridge_input = event._read_json(bridge_input_path)
    try:
        metadata_binding = bridge_input["identity"]["metadata"]
        native_identity = native_registration["native"]["identity"]
    except KeyError as exc:
        raise ShopCorpusExpansionBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if (
        not metadata_path.is_file()
        or _sha256_file(metadata_path) != metadata_binding["sha256"]
    ):
        raise ShopCorpusExpansionBlocked("Current policy metadata bytes differ")
    return native_identity, bridge_input, metadata_path


def execute_preflight(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    corpus = historical.load_historical_corpus(repo_root)
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    _load_registered_inputs(native_registration_path, bridge_input_path)
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise ShopCorpusExpansionBlocked("output directory already exists")
    if list(native_runner._forbidden_processes()):
        raise ShopCorpusExpansionBlocked("game or CommunicationMod is active")
    return {
        "expansion_seed_count": len(EXPANSION_SEEDS),
        "historical_sources": len(corpus.rows),
        "output_dir": output.as_posix(),
        "source_target": MAX_SOURCE_STATES,
        "verdict": "shop_counterfactual_expansion_preflight_passed",
    }


def execute_run(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise ShopCorpusExpansionBlocked("output directory already exists")
    corpus = historical.load_historical_corpus(repo_root)
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_identity, bridge_input, metadata_path = _load_registered_inputs(
        native_registration_path, bridge_input_path
    )
    if list(native_runner._forbidden_processes()):
        raise ShopCorpusExpansionBlocked("game or CommunicationMod is active")
    if "sts_lightspeed_noncombat_adapter" not in sys.modules:
        preload_native_registration(native_registration_path)
    environment_factory = native_runner._load_environment_factory(native_identity)
    metadata = current_bridge.MetadataCatalog(metadata_path)
    current_policy = bridge_input["current_policy"]

    def session_factory(_seed: int) -> current_bridge.CurrentPolicyBridgeSession:
        return current_bridge.CurrentPolicyBridgeSession(
            metadata=metadata,
            current_policy=current_policy,
            event_semantics_identity=None,
            require_global_metadata_match=True,
            simulator_provenance=native_identity["provenance"],
        )

    result = collect_expansion(environment_factory, session_factory, corpus)
    if list(native_runner._forbidden_processes()):
        raise ShopCorpusExpansionBlocked(
            "game or CommunicationMod started during execution"
        )
    identity = {
        "current_bridge_input": {
            "path": bridge_input_path.as_posix(),
            "sha256": _sha256_file(bridge_input_path),
        },
        "metadata": copy.deepcopy(bridge_input["identity"]["metadata"]),
        "native_module": copy.deepcopy(native_identity["module"]),
        "native_registration": {
            "path": native_registration_path.as_posix(),
            "sha256": _sha256_file(native_registration_path),
        },
        "source": _source_identity(repo_root),
    }
    write_artifacts(output, result, identity)
    return {
        "action_branches": result.dataset.action_branches,
        "expansion_sources": len(result.dataset.rows),
        "informative_sources": result.metrics["informative_source_count"],
        "output_dir": output.as_posix(),
        "verdict": result.report["verdict"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("preflight", "run"):
        child = subparsers.add_parser(command)
        child.add_argument(
            "--repo-root", default=str(Path(__file__).resolve().parents[1])
        )
        child.add_argument(
            "--native-registration", default=str(DEFAULT_NATIVE_REGISTRATION)
        )
        child.add_argument(
            "--current-bridge-input", default=str(DEFAULT_CURRENT_BRIDGE_INPUT)
        )
        child.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "preflight":
        result = execute_preflight(args)
    elif args.command == "run":
        result = execute_run(args)
    else:
        raise ShopCorpusExpansionBlocked("unsupported command")
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
