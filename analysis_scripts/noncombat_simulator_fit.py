"""Fail-closed fit audit for the optional sts_lightspeed non-combat POC."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from analysis_scripts.noncombat_simulator_adapter import (
    TARGET_CATEGORIES,
    canonical_json_bytes,
    collect_provenance,
    load_native_module,
    sha256_file,
    validate_candidates,
    validate_native_baseline_action,
    validate_provenance,
    validate_snapshot,
)


INPUT_SCHEMA_VERSION = "noncombat-simulator-fit-input-v1"
REPORT_SCHEMA_VERSION = "noncombat-simulator-fit-report-v1"
HISTORICAL_FIXTURE_SCHEMA_VERSION = "sts-lightspeed-historical-prefix-v1"
DEFAULT_MAX_DECISIONS = 500
DEFAULT_THROUGHPUT_BUDGET_SECONDS = 30.0


class SimulatorFitError(ValueError):
    """Raised when fit inputs or generated evidence violate the contract."""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SimulatorFitError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path | str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SimulatorFitError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SimulatorFitError(f"JSON root must be an object: {path}")
    return value


def load_historical_fixture(path: Path | str) -> dict[str, Any]:
    fixture = load_json(path)
    if fixture.get("schema_version") != HISTORICAL_FIXTURE_SCHEMA_VERSION:
        raise SimulatorFitError("historical fixture schema mismatch")
    runs = fixture.get("runs")
    if not isinstance(runs, list) or len(runs) != 6:
        raise SimulatorFitError("historical fixture must contain exactly six runs")
    seen_files: set[str] = set()
    for run_index, raw_run in enumerate(runs):
        if not isinstance(raw_run, dict):
            raise SimulatorFitError(f"historical run {run_index} must be an object")
        run_file = raw_run.get("run_file")
        if not isinstance(run_file, str) or not run_file.endswith(".run"):
            raise SimulatorFitError(f"historical run {run_index} has invalid run_file")
        if run_file in seen_files:
            raise SimulatorFitError(f"duplicate historical run_file: {run_file}")
        seen_files.add(run_file)
        if not isinstance(raw_run.get("sha256"), str) or len(raw_run["sha256"]) != 64:
            raise SimulatorFitError(f"historical run {run_file} has invalid sha256")
        if not isinstance(raw_run.get("size_bytes"), int) or raw_run["size_bytes"] <= 0:
            raise SimulatorFitError(f"historical run {run_file} has invalid size")
        try:
            int(raw_run["seed_played"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SimulatorFitError(f"historical run {run_file} has invalid seed") from exc
        decisions = raw_run.get("decisions")
        if not isinstance(decisions, list) or len(decisions) != 2:
            raise SimulatorFitError(f"historical run {run_file} needs two decisions")
        if [decision.get("floor") for decision in decisions] != [0, 1]:
            raise SimulatorFitError(f"historical run {run_file} must bind floors 0 and 1")
        for decision in decisions:
            candidates = decision.get("candidates")
            if not isinstance(candidates, list) or not candidates:
                raise SimulatorFitError(f"historical run {run_file} has empty candidates")
            if candidates != sorted(candidates) or len(candidates) != len(set(candidates)):
                raise SimulatorFitError(f"historical run {run_file} candidates are not canonical")
            if decision.get("picked") not in candidates:
                raise SimulatorFitError(f"historical run {run_file} picked card is not offered")
    return fixture


def verify_historical_run_sources(
    fixture: Mapping[str, Any],
    runs_directory: Path | str,
) -> list[dict[str, Any]]:
    root = Path(runs_directory).resolve()
    results: list[dict[str, Any]] = []
    for run in fixture["runs"]:
        path = root / run["run_file"]
        actual_size = path.stat().st_size if path.is_file() else None
        actual_sha256 = sha256_file(path) if path.is_file() else None
        results.append(
            {
                "actual_sha256": actual_sha256,
                "actual_size_bytes": actual_size,
                "expected_sha256": run["sha256"],
                "expected_size_bytes": run["size_bytes"],
                "matched": (
                    actual_size == run["size_bytes"]
                    and actual_sha256 == run["sha256"]
                ),
                "run_file": run["run_file"],
            }
        )
    return results


def _run_first_candidate_batch(
    module: Any,
    *,
    seeds: Sequence[int],
    max_decisions: int,
    exercise_all_candidates_seed: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    all_categories: set[str] = set()
    checked_candidates = 0
    clone_isolation = True

    for seed in seeds:
        environment = module.Environment(seed, 0)
        categories: set[str] = set()
        decisions = 0
        while not environment.terminal():
            if decisions >= max_decisions:
                raise SimulatorFitError(
                    f"seed {seed} exceeded {max_decisions} target decisions"
                )
            before_bytes = environment.snapshot_json()
            before = validate_snapshot(json.loads(before_bytes))
            candidates = validate_candidates(
                json.loads(environment.legal_actions_json()),
                category=before["category"],
            )
            category = before["category"]
            if category is None:
                raise SimulatorFitError(f"seed {seed} stopped outside a target decision")
            categories.add(category)
            all_categories.add(category)

            if seed == exercise_all_candidates_seed:
                for candidate in candidates:
                    branch = environment.clone()
                    branch.step(candidate["action_id"])
                    branch_snapshot = validate_snapshot(json.loads(branch.snapshot_json()))
                    if environment.snapshot_json() != before_bytes:
                        clone_isolation = False
                    if branch_snapshot.get("decision_count") != before.get("decision_count", 0) + 1:
                        raise SimulatorFitError("candidate branch did not advance one target decision")
                    checked_candidates += 1

            environment.step(candidates[0]["action_id"])
            decisions += 1

        terminal = validate_snapshot(json.loads(environment.snapshot_json()))
        rows.append(
            {
                "categories": sorted(categories),
                "decisions": decisions,
                "floor": terminal["state"]["floor"],
                "outcome": terminal["state"]["outcome"],
                "seed": seed,
            }
        )

    return {
        "all_categories": sorted(all_categories),
        "checked_candidates": checked_candidates,
        "clone_isolation": clone_isolation,
        "rows": rows,
    }


def _run_native_baseline_batch(
    module: Any,
    *,
    seeds: Sequence[int],
    max_decisions: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    all_categories: set[str] = set()
    checked_decisions = 0
    candidate_legality = True
    non_mutation = True

    for seed in seeds:
        environment = module.Environment(seed, 0)
        categories: set[str] = set()
        action_ids: list[str] = []
        decisions = 0
        while not environment.terminal():
            if decisions >= max_decisions:
                raise SimulatorFitError(
                    f"native baseline seed {seed} exceeded {max_decisions} target decisions"
                )
            before_snapshot_bytes = environment.snapshot_json()
            before = validate_snapshot(json.loads(before_snapshot_bytes))
            before_candidate_bytes = environment.legal_actions_json()
            candidates = validate_candidates(
                json.loads(before_candidate_bytes),
                category=before["category"],
            )
            category = before["category"]
            if category is None:
                raise SimulatorFitError(
                    f"native baseline seed {seed} stopped outside a target decision"
                )

            first_action = validate_native_baseline_action(
                json.loads(environment.native_baseline_action_json()),
                category=category,
                candidates=candidates,
            )
            second_action = validate_native_baseline_action(
                json.loads(environment.native_baseline_action_json()),
                category=category,
                candidates=candidates,
            )
            if first_action != second_action:
                raise SimulatorFitError("native baseline repeated query differs")
            if (
                environment.snapshot_json() != before_snapshot_bytes
                or environment.legal_actions_json() != before_candidate_bytes
            ):
                non_mutation = False

            selected_action_id = environment.step_native_baseline()
            if selected_action_id != first_action["action_id"]:
                candidate_legality = False
            categories.add(category)
            all_categories.add(category)
            action_ids.append(selected_action_id)
            checked_decisions += 1
            decisions += 1

        terminal = validate_snapshot(json.loads(environment.snapshot_json()))
        rows.append(
            {
                "action_sequence_sha256": hashlib.sha256(
                    canonical_json_bytes(action_ids)
                ).hexdigest(),
                "categories": sorted(categories),
                "decisions": decisions,
                "floor": terminal["state"]["floor"],
                "outcome": terminal["state"]["outcome"],
                "seed": seed,
            }
        )

    return {
        "all_categories": sorted(all_categories),
        "candidate_legality": candidate_legality,
        "checked_decisions": checked_decisions,
        "non_mutation": non_mutation,
        "rows": rows,
    }


def _audit_historical_prefixes(module: Any, fixture: Mapping[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    matched_decisions = 0
    for run in fixture["runs"]:
        probe = json.loads(
            module.historical_prefix_json(
                int(run["seed_played"]) % (1 << 64),
                run["ascension_level"],
                run["decisions"][0]["picked"],
            )
        )
        neow_match = probe.get("neow_candidates") == run["decisions"][0]["candidates"]
        floor_one_match = (
            probe.get("floor_one_candidates") == run["decisions"][1]["candidates"]
        )
        matched_decisions += int(neow_match) + int(floor_one_match)
        rows.append(
            {
                "encounter": probe.get("encounter"),
                "floor": probe.get("floor"),
                "floor_one_match": floor_one_match,
                "neow_match": neow_match,
                "run_file": run["run_file"],
            }
        )
    return {
        "expected_decisions": len(fixture["runs"]) * 2,
        "matched_decisions": matched_decisions,
        "rows": rows,
    }


def compare_registered_provenance(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> list[str]:
    mismatches: list[str] = []

    def visit(prefix: str, expected_value: Any, actual_value: Any) -> None:
        if isinstance(expected_value, Mapping):
            if not isinstance(actual_value, Mapping):
                mismatches.append(prefix or "provenance")
                return
            for key in sorted(expected_value):
                visit(
                    f"{prefix}.{key}" if prefix else str(key),
                    expected_value[key],
                    actual_value.get(key),
                )
        elif expected_value != actual_value:
            mismatches.append(prefix)

    visit("", expected, actual)
    return mismatches


def classify_fit_report(
    *,
    provenance: Mapping[str, Any],
    registered_provenance: Mapping[str, Any],
    first_batch: Mapping[str, Any],
    second_batch: Mapping[str, Any],
    first_native_baseline_batch: Mapping[str, Any],
    second_native_baseline_batch: Mapping[str, Any],
    historical: Mapping[str, Any],
    historical_sources: Sequence[Mapping[str, Any]],
    throughput_within_budget: bool,
    seeds: Sequence[int],
) -> dict[str, Any]:
    normalized_provenance = validate_provenance(provenance)
    provenance_mismatches = compare_registered_provenance(
        registered_provenance,
        normalized_provenance,
    )
    rows = first_batch.get("rows", [])
    all_terminal = bool(rows) and all(
        row.get("outcome") in {"player_loss", "player_victory"} for row in rows
    )
    categories = set(first_batch.get("all_categories", []))
    native_rows = first_native_baseline_batch.get("rows", [])
    native_categories = set(first_native_baseline_batch.get("all_categories", []))
    native_terminal = bool(native_rows) and all(
        row.get("outcome") in {"player_loss", "player_victory"}
        for row in native_rows
    )
    checks = {
        "candidate_legality": first_batch.get("checked_candidates", 0) > 0,
        "clone_isolation": first_batch.get("clone_isolation") is True,
        "four_category_coverage": categories == set(TARGET_CATEGORIES),
        "historical_prefix_agreement": (
            historical.get("matched_decisions") == historical.get("expected_decisions") == 12
        ),
        "historical_source_identity": bool(historical_sources)
        and all(row.get("matched") is True for row in historical_sources),
        "native_baseline_candidate_mapping": (
            first_native_baseline_batch.get("candidate_legality") is True
            and first_native_baseline_batch.get("checked_decisions", 0) > 0
        ),
        "native_baseline_four_category_coverage": (
            native_categories == set(TARGET_CATEGORIES)
        ),
        "native_baseline_non_mutation": (
            first_native_baseline_batch.get("non_mutation") is True
        ),
        "native_baseline_repeated_seed_determinism": (
            first_native_baseline_batch == second_native_baseline_batch
        ),
        "native_baseline_terminal_outcomes": (
            native_terminal and len(native_rows) == len(seeds)
        ),
        "provenance_identity": not provenance_mismatches,
        "repeated_seed_determinism": first_batch == second_batch,
        "terminal_outcomes": all_terminal and len(rows) == len(seeds),
        "throughput_budget": throughput_within_budget,
    }
    blockers = [name for name, passed in checks.items() if not passed]
    verdict = "adapter_poc_ready" if not blockers else "blocked"
    return {
        "authority": {
            "formal_noncombat_rl": False,
            "live_gameplay": False,
            "live_policy_loading": False,
            "live_study_launch": False,
            "ope_reinterpretation": False,
            "policy_promotion": False,
            "simulator_policy_validity": False,
            "simulator_training_smoke": False,
        },
        "batch": {
            "checked_candidates": first_batch.get("checked_candidates", 0),
            "first": first_batch,
            "native_baseline": {
                "first": first_native_baseline_batch,
                "second": second_native_baseline_batch,
            },
            "second": second_batch,
            "seeds": list(seeds),
        },
        "blockers": blockers,
        "checks": checks,
        "historical_prefix": dict(historical),
        "historical_sources": [dict(row) for row in historical_sources],
        "limitations": [
            "Simulator outcomes are not live outcomes and do not enter live OPE or supported-victory counts.",
            "Combat uses the declared SimpleAgent baseline with battle potion use disabled.",
            "Neow, boss relics, campfires, treasure, and follow-up card selections are baseline-controlled.",
            "Historical agreement covers twelve early reward candidate sets, not full-run mechanics equivalence.",
            "The upstream save loader cannot import arbitrary non-combat live states.",
            "The native target query is valid only while target actions follow that baseline.",
            "Adapter fit and policy validity do not authorize formal simulator training.",
        ],
        "provenance": normalized_provenance,
        "provenance_mismatches": provenance_mismatches,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "verdict": verdict,
    }


def run_native_audit(
    *,
    module: Any,
    provenance: Mapping[str, Any],
    registered_provenance: Mapping[str, Any],
    fixture: Mapping[str, Any],
    historical_sources: Sequence[Mapping[str, Any]],
    seeds: Sequence[int],
    max_decisions: int,
    throughput_budget_seconds: float,
) -> dict[str, Any]:
    if not seeds or len(set(seeds)) != len(seeds):
        raise SimulatorFitError("audit seeds must be non-empty and unique")
    if max_decisions <= 0:
        raise SimulatorFitError("max_decisions must be positive")
    if throughput_budget_seconds <= 0:
        raise SimulatorFitError("throughput budget must be positive")

    started = time.perf_counter()
    first = _run_first_candidate_batch(
        module,
        seeds=seeds,
        max_decisions=max_decisions,
        exercise_all_candidates_seed=seeds[0],
    )
    second = _run_first_candidate_batch(
        module,
        seeds=seeds,
        max_decisions=max_decisions,
        exercise_all_candidates_seed=seeds[0],
    )
    first_native_baseline = _run_native_baseline_batch(
        module,
        seeds=seeds,
        max_decisions=max_decisions,
    )
    second_native_baseline = _run_native_baseline_batch(
        module,
        seeds=seeds,
        max_decisions=max_decisions,
    )
    historical = _audit_historical_prefixes(module, fixture)
    within_budget = (time.perf_counter() - started) <= throughput_budget_seconds
    return classify_fit_report(
        provenance=provenance,
        registered_provenance=registered_provenance,
        first_batch=first,
        second_batch=second,
        first_native_baseline_batch=first_native_baseline,
        second_native_baseline_batch=second_native_baseline,
        historical=historical,
        historical_sources=historical_sources,
        throughput_within_budget=within_budget,
        seeds=seeds,
    )


def render_markdown(report: Mapping[str, Any]) -> str:
    checks = report["checks"]
    authority = report["authority"]
    lines = [
        "# Non-Combat Simulator Fit Audit",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Simulator commit: `{report['provenance']['simulator_commit']}`",
        f"- Adapter source commit: `{report['provenance']['adapter_commit']}`",
        f"- Seeds: {len(report['batch']['seeds'])}",
        f"- Clone candidates checked: {report['batch']['checked_candidates']}",
        (
            "- Native baseline decisions checked: "
            f"{report['batch']['native_baseline']['first']['checked_decisions']}"
        ),
        (
            "- Historical reward candidates: "
            f"{report['historical_prefix']['matched_decisions']}/"
            f"{report['historical_prefix']['expected_decisions']}"
        ),
        "",
        "## Checks",
        "",
    ]
    for name in sorted(checks):
        lines.append(f"- {name}: `{'pass' if checks[name] else 'fail'}`")
    lines.extend(["", "## Blockers", ""])
    if report["blockers"]:
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    else:
        lines.append("- None for the adapter POC fit gate.")
    lines.extend(["", "## Authority", ""])
    for name in sorted(authority):
        lines.append(f"- {name}: `{str(authority[name]).lower()}`")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    return "\n".join(lines) + "\n"


def report_json_bytes(report: Mapping[str, Any]) -> bytes:
    encoded = canonical_json_bytes(report)
    decoded = json.loads(encoded)
    if decoded.get("report_schema_version") != REPORT_SCHEMA_VERSION:
        raise SimulatorFitError("rendered report schema mismatch")
    return encoded


def publish_report_pair(
    report: Mapping[str, Any],
    *,
    json_output: Path | str,
    markdown_output: Path | str,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], None] = os.replace,
) -> None:
    json_path = Path(json_output)
    markdown_path = Path(markdown_output)
    json_bytes = report_json_bytes(report)
    markdown_bytes = render_markdown(report).encode("utf-8")
    if not markdown_bytes.endswith(b"\n"):
        raise SimulatorFitError("Markdown report must end with LF")

    destinations = (json_path, markdown_path)
    payloads = (json_bytes, markdown_bytes)
    previous = [path.read_bytes() if path.exists() else None for path in destinations]
    temp_paths = [path.with_name(path.name + ".tmp") for path in destinations]
    for path in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)
    for temp, payload in zip(temp_paths, payloads):
        temp.write_bytes(payload)

    published = 0
    try:
        for temp, destination in zip(temp_paths, destinations):
            replace(temp, destination)
            published += 1
    except Exception:
        for index in range(published):
            destination = destinations[index]
            prior = previous[index]
            if prior is None:
                destination.unlink(missing_ok=True)
            else:
                restore = destination.with_name(destination.name + ".restore")
                restore.write_bytes(prior)
                os.replace(restore, destination)
        raise
    finally:
        for temp in temp_paths:
            temp.unlink(missing_ok=True)


def load_bound_input(input_path: Path | str, repo_root: Path | str) -> tuple[dict[str, Any], Path]:
    manifest = load_json(input_path)
    if manifest.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise SimulatorFitError("fit input schema mismatch")
    root = Path(repo_root).resolve()
    fixture_binding = manifest.get("fixture")
    if not isinstance(fixture_binding, dict):
        raise SimulatorFitError("fit input fixture binding is required")
    fixture_path = (root / fixture_binding.get("path", "")).resolve()
    try:
        fixture_path.relative_to(root)
    except ValueError as exc:
        raise SimulatorFitError("fixture path escapes repository root") from exc
    if not fixture_path.is_file():
        raise SimulatorFitError("bound fixture is missing")
    if fixture_path.stat().st_size != fixture_binding.get("size_bytes"):
        raise SimulatorFitError("bound fixture size mismatch")
    if sha256_file(fixture_path) != fixture_binding.get("sha256"):
        raise SimulatorFitError("bound fixture sha256 mismatch")
    validate_provenance(manifest.get("registered_provenance"))
    audit = manifest.get("audit")
    if not isinstance(audit, dict):
        raise SimulatorFitError("fit input audit contract is required")
    seeds = audit.get("seeds")
    if not isinstance(seeds, list) or not all(isinstance(seed, int) for seed in seeds):
        raise SimulatorFitError("fit input seeds must be integers")
    return manifest, fixture_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--simulator-repo", type=Path, required=True)
    parser.add_argument("--module", type=Path, required=True)
    parser.add_argument("--dll-directory", type=Path, action="append", default=[])
    parser.add_argument("--runs-directory", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    manifest, fixture_path = load_bound_input(args.input, repo_root)
    fixture = load_historical_fixture(fixture_path)
    module = load_native_module(args.module, dll_directories=args.dll_directory)
    provenance = collect_provenance(
        simulator_repo=args.simulator_repo,
        module_path=args.module,
        adapter_repo=repo_root,
        adapter_source_paths=[
            repo_root / "analysis_scripts" / "noncombat_simulator_adapter.py",
            repo_root / "analysis_scripts" / "noncombat_simulator_fit.py",
            repo_root / "simulator_adapters" / "sts_lightspeed" / "CMakeLists.txt",
            repo_root / "simulator_adapters" / "sts_lightspeed" / "noncombat_adapter.cpp",
        ],
        native_module=module,
    )
    historical_sources = verify_historical_run_sources(fixture, args.runs_directory)
    audit_contract = manifest["audit"]
    report = run_native_audit(
        module=module,
        provenance=provenance,
        registered_provenance=manifest["registered_provenance"],
        fixture=fixture,
        historical_sources=historical_sources,
        seeds=audit_contract["seeds"],
        max_decisions=audit_contract.get("max_decisions", DEFAULT_MAX_DECISIONS),
        throughput_budget_seconds=audit_contract.get(
            "throughput_budget_seconds",
            DEFAULT_THROUGHPUT_BUDGET_SECONDS,
        ),
    )
    publish_report_pair(
        report,
        json_output=args.json_output,
        markdown_output=args.markdown_output,
    )
    print(
        json.dumps(
            {
                "blockers": report["blockers"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
                "verdict": report["verdict"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["verdict"] == "adapter_poc_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
