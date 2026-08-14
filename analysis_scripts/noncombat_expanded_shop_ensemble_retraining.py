"""Retrain the fixed shop ensemble on the verified 496-source corpus."""

from __future__ import annotations

import argparse
import copy
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import subprocess
import sys
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
from analysis_scripts import noncombat_cross_validated_shop_ensemble as delegated
from analysis_scripts import noncombat_current_policy_simulator_bridge as current_bridge
from analysis_scripts import noncombat_event_option_counterfactual_outcomes as event


DEFAULT_NATIVE_REGISTRATION = event.DEFAULT_NATIVE_REGISTRATION
DEFAULT_CURRENT_BRIDGE_INPUT = event.DEFAULT_CURRENT_BRIDGE_INPUT
DEFAULT_PREFLIGHT_OUTPUT_DIR = Path(
    "reports/noncombat_expanded_shop_ensemble_preflight_20260814_r1"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_expanded_shop_ensemble_retraining_20260814_r1"
)
EXPANSION_BINDING = delegated.DatasetBinding(
    cohort="expansion384",
    path=Path(
        "reports/noncombat_shop_counterfactual_corpus_expansion_20260814_r1/dataset.json"
    ),
    sha256="99efae73450c3848b04ea487a2e9ca9597430a78d1bebbea61b27bb00da0b3de",
    partition_name="train",
    source_count=384,
)
DATASET_BINDINGS = (*delegated.DATASET_BINDINGS, EXPANSION_BINDING)
EXPECTED_SOURCE_COUNT = 496
BOUND_SOURCE_PATHS = tuple(
    dict.fromkeys(
        (
            Path("analysis_scripts/noncombat_expanded_shop_ensemble_retraining.py"),
            *delegated.BOUND_SOURCE_PATHS,
        )
    )
)


class ExpandedShopRetrainingBlocked(RuntimeError):
    """Raised when expanded shop retraining cannot produce frozen evidence."""


def _canonical_bytes(value: Any) -> bytes:
    return event._canonical_bytes(value)


def _sha256_file(path: Path) -> str:
    return event._sha256_file(path)


def load_expanded_corpus(repo_root: Path) -> delegated.HistoricalCorpus:
    try:
        corpus = delegated.load_historical_corpus(
            repo_root, bindings=DATASET_BINDINGS
        )
    except delegated.CrossValidatedShopBlocked as exc:
        raise ExpandedShopRetrainingBlocked(str(exc)) from exc
    if (
        len(corpus.rows) != EXPECTED_SOURCE_COUNT
        or corpus.audit["cohorts"].get("expansion384", {}).get("source_count")
        != 384
        or corpus.audit.get("feature_width") != 1024
    ):
        raise ExpandedShopRetrainingBlocked("expanded shop corpus support differs")
    return corpus


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
        raise ExpandedShopRetrainingBlocked("cannot resolve source commit") from exc
    return {
        "commit": commit,
        "files": files,
        "source_sha256": hashlib.sha256(_canonical_bytes(files)).hexdigest(),
    }


def _prepare(
    repo_root: Path,
) -> tuple[
    delegated.HistoricalCorpus,
    delegated.CrossValidationSelection,
    tuple[Any, ...],
    dict[str, Any],
]:
    corpus = load_expanded_corpus(repo_root)
    try:
        selection = delegated.cross_validate(corpus)
        models, model_payload = delegated._fit_frozen_ensemble(corpus, selection)
    except delegated.CrossValidationNoGo:
        raise
    except delegated.CrossValidatedShopBlocked as exc:
        raise ExpandedShopRetrainingBlocked(str(exc)) from exc
    return corpus, selection, models, model_payload


def execute_preflight(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise ExpandedShopRetrainingBlocked("preflight output directory already exists")
    corpus = load_expanded_corpus(repo_root)
    try:
        selection = delegated.cross_validate(corpus)
    except delegated.CrossValidationNoGo as exc:
        oof_metrics = exc.metrics
        model_payload = None
    else:
        try:
            _models, model_payload = delegated._fit_frozen_ensemble(corpus, selection)
        except delegated.CrossValidatedShopBlocked as exc:
            raise ExpandedShopRetrainingBlocked(str(exc)) from exc
        oof_metrics = {
            **selection.metrics,
            "verdict": "expanded_shop_ensemble_preflight_passed",
        }
    identity = {"source": _source_identity(repo_root)}
    delegated.write_preflight_artifacts(
        output,
        corpus,
        oof_metrics,
        identity,
        model_payload=model_payload,
    )
    return {
        "model_state_sha256": (
            hashlib.sha256(_canonical_bytes(model_payload)).hexdigest()
            if model_payload is not None
            else None
        ),
        "output_dir": output.as_posix(),
        "selected_epoch": oof_metrics.get("selected_epoch"),
        "selected_vote_quorum": oof_metrics.get("selected_vote_quorum"),
        "source_count": len(corpus.rows),
        "verdict": oof_metrics["verdict"],
    }


def _load_registered_inputs(
    native_registration_path: Path,
    bridge_input_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    native_registration = event._read_json(native_registration_path)
    bridge_input = event._read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
    except KeyError as exc:
        raise ExpandedShopRetrainingBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if (
        not metadata_path.is_file()
        or _sha256_file(metadata_path) != metadata_binding["sha256"]
    ):
        raise ExpandedShopRetrainingBlocked("Current policy metadata bytes differ")
    return native_identity, bridge_input, metadata_path


def execute_run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise ExpandedShopRetrainingBlocked("output directory already exists")
    corpus, selection, models, model_payload = _prepare(repo_root)
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_identity, bridge_input, metadata_path = _load_registered_inputs(
        native_registration_path, bridge_input_path
    )
    if list(native_runner._forbidden_processes()):
        raise ExpandedShopRetrainingBlocked("game or CommunicationMod is active")
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

    try:
        result = delegated.evaluate_fresh(
            environment_factory,
            session_factory,
            corpus,
            selection,
            models,
            model_payload,
        )
    except delegated.CrossValidatedShopBlocked as exc:
        raise ExpandedShopRetrainingBlocked(str(exc)) from exc
    if list(native_runner._forbidden_processes()):
        raise ExpandedShopRetrainingBlocked(
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
    delegated.write_artifacts(output, result, identity)
    return {
        "fresh_sources": len(result.fresh.rows),
        "historical_sources": len(corpus.rows),
        "output_dir": output.as_posix(),
        "selected_epoch": selection.selected_epoch,
        "selected_vote_quorum": selection.selected_vote_quorum,
        "verdict": result.report["verdict"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument(
        "--repo-root", default=str(Path(__file__).resolve().parents[1])
    )
    preflight.add_argument(
        "--output-dir", default=str(DEFAULT_PREFLIGHT_OUTPUT_DIR)
    )
    run = subparsers.add_parser("run")
    run.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    run.add_argument("--native-registration", default=str(DEFAULT_NATIVE_REGISTRATION))
    run.add_argument("--current-bridge-input", default=str(DEFAULT_CURRENT_BRIDGE_INPUT))
    run.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "preflight":
        result = execute_preflight(args)
    elif args.command == "run":
        result = execute_run(args)
    else:
        raise ExpandedShopRetrainingBlocked("unsupported command")
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
