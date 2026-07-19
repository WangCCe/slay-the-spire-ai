import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True

INPUT_PATHS = (
    "analysis_scripts/render_pre_request_qualification_observability_vectors.py",
    "analysis_scripts/verify_noncombat_outcome_evidence_expansion.py",
    "scripts/run_noncombat_outcome_evidence_expansion.py",
    "tests/test_noncombat_outcome_evidence_runner.py",
    "tests/test_noncombat_outcome_evidence_verifier.py",
)
EXPECTED_COMPATIBILITY_VECTORS = {
    "request_v1": (
        5996,
        "fedb4c8d0fdf7d7f2c211455a42a794f0bddf18a7b392b62de89da8032f61936",
    ),
    "request_v2": (
        8886,
        "28c174d6fba875ba110b107c92da5d522664ead81d9bf5c0db71db6fc3748b69",
    ),
    "request_v3": (
        10700,
        "285698c9726312fc6631fd69fd1216ba65be028376439c2baa673c87c61fa662",
    ),
    "result_v1": (
        6848,
        "15bebc995815380d9adaed69533fd3d370763e6775c9f9298f51781a45186349",
    ),
    "result_v2": (
        7184,
        "401272257f085a23e17c62752e312d0dad5b0ba96d3d7982e1258f28285a9a86",
    ),
    "result_v3": (
        7191,
        "f8599566b724f652900c2756aa25469bd13db716d7635d1fca67c667cdf8c19b",
    ),
    "review_v1": (
        2094,
        "1e68c9c609e870107f47cf8484639420db26b7331288fc1e1b70b89a2833e044",
    ),
    "review_v3": (
        2096,
        "5ac5716b1f08c75cbef6e6f9b969c3cddd24ae2dfc442e1882d530495d5e8441",
    ),
}


def _load(name, relative_path):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical(record):
    return json.dumps(
        record,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _compatibility_entries(verifier_tests, runner):
    records = verifier_tests._canonical_public_v1_v2_compatibility_vectors()
    request_v2_path = (
        REPO_ROOT
        / "reports"
        / (
            "noncombat_outcome_evidence_expansion_20260716_v2_r6_"
            "qualification_request.json"
        )
    )
    request_v2 = json.loads(request_v2_path.read_text(encoding="ascii"))
    request_v3 = deepcopy(request_v2)
    request_v3["child_command"].insert(3, "-B")
    request_v3["bootstrap"] = runner._qualification_bootstrap_paths(
        Path(request_v3["qualification_root"])
    )
    request_v3["schema_version"] = runner.QUALIFICATION_REQUEST_SCHEMA_VERSION
    request_v3["request_hash"] = verifier_tests._self_hash(
        request_v3,
        "request_hash",
    )
    records["request_v3"] = request_v3
    entries = {
        f"compatibility/{name}.json": _canonical(record) + b"\n"
        for name, record in records.items()
    }
    observed = {
        name.removeprefix("compatibility/").removesuffix(".json"): (
            len(raw),
            hashlib.sha256(raw).hexdigest(),
        )
        for name, raw in entries.items()
    }
    if observed != EXPECTED_COMPATIBILITY_VECTORS:
        raise RuntimeError("compatibility vector bytes drifted")
    return entries


def _bootstrap_vector_entries(verifier_tests, runner_tests, runner):
    producer_envelope = runner._qualification_bootstrap_envelope(
        request=runner_tests.BOOTSTRAP_VECTOR_REQUEST,
        expected_request_file_sha256="c" * 64,
        expected_request_size=123,
        review_commit="d" * 40,
        runner_sha256="e" * 64,
    )
    producer_raw = _canonical(producer_envelope)
    producer_token = runner._qualification_bootstrap_token(producer_envelope)

    verifier_request = {
        "bootstrap": verifier_tests._independent_bootstrap_paths(
            Path(r"D:\qualification-root")
        ),
        "qualification_id": "fixture-qualification",
        "qualification_root": r"D:\qualification-root",
        "request_hash": "b" * 64,
        "source_commit": "c" * 40,
    }
    verifier_envelope = (
        verifier_tests._verifier()._qualification_bootstrap_expected_envelope(
            request=verifier_request,
            expected_request_file_sha256="e" * 64,
            expected_request_size=123,
            review_commit="d" * 40,
            runner_sha256="a" * 64,
        )
    )
    verifier_raw = _canonical(verifier_envelope)
    verifier_token = hashlib.sha256(
        b"noncombat-outcome-evidence-qualification-bootstrap-token-v1\x00"
        + verifier_raw
    ).hexdigest()
    if (
        len(producer_raw),
        hashlib.sha256(producer_raw).hexdigest(),
        producer_token,
    ) != (
        1734,
        "601d300a7f67a82b6f44495a488228e4366135d5591cb1ce3176e0645a29322e",
        "6f21f2b4324bea5277ef12e03b87e2ab84f3ead09b1def0fda52d3f201aa4089",
    ):
        raise RuntimeError("producer bootstrap vector drifted")
    if (
        len(verifier_raw),
        hashlib.sha256(verifier_raw).hexdigest(),
        verifier_token,
    ) != (
        1617,
        "926af6b9addd083e2127050d09947d58e714aaa590988354b3639c0487c3aa42",
        "17ba93387ea9ac596ab0a8b4fddcd3838b2ad11d3ed8fb2f5d8d83834ef6d34f",
    ):
        raise RuntimeError("verifier bootstrap vector drifted")
    return {
        "bootstrap/producer-envelope.json": producer_raw,
        "bootstrap/producer-token.txt": producer_token.encode("ascii") + b"\n",
        "bootstrap/verifier-envelope.json": verifier_raw,
        "bootstrap/verifier-token.txt": verifier_token.encode("ascii") + b"\n",
    }


def _terminal_entries(verifier_tests, fixture_root):
    fixture = verifier_tests._literal_v3_terminal_fixture(fixture_root)
    request = fixture["request"]
    bootstrap = request["bootstrap"]
    entries = {
        "terminal/request-source.json": fixture["request_source_path"].read_bytes(),
        "terminal/active-request.json": Path(request["request_path"]).read_bytes(),
        "terminal/result.json": fixture["result_raw"],
        "terminal/review-binding.json": (
            _canonical(fixture["result"]["review_binding"]) + b"\n"
        ),
        "terminal/bootstrap-summary.json": (
            _canonical(fixture["bootstrap_summary"]) + b"\n"
        ),
        "terminal/bootstrap-claim.json": Path(bootstrap["claim_path"]).read_bytes(),
        "terminal/bootstrap-handoff.json": Path(bootstrap["handoff_path"]).read_bytes(),
    }
    for row in bootstrap["stage_paths"]:
        entries[f"terminal/bootstrap-stage-{row['index']:02d}.json"] = Path(
            row["path"]
        ).read_bytes()
    return entries


def _history_entries(verifier_tests):
    entries = {}
    root = verifier_tests.QUALIFICATION_HISTORY_FIXTURE_ROOT
    for identity in ("r1", "r2", "r3", "r4", "r5", "r6"):
        fixture_root = root / identity
        manifest = json.loads(
            (fixture_root / "manifest.json").read_text(encoding="ascii")
        )
        entries[f"history/{identity}/expected-absences.json"] = (
            _canonical(manifest["expected_absences"]) + b"\n"
        )
        for row in manifest["expected_absences"]:
            if (fixture_root / row["path"]).exists():
                raise RuntimeError(
                    f"historical expected absence is present: {identity}/{row['path']}"
                )
        for row in manifest["available_files"]:
            raw = (fixture_root / row["path"]).read_bytes()
            if len(raw) != row["size"] or hashlib.sha256(raw).hexdigest() != row[
                "sha256"
            ]:
                raise RuntimeError(
                    f"historical file bytes drifted: {identity}/{row['path']}"
                )
            entries[f"history/{identity}/{row['path']}"] = raw
    return entries


def _frame(entries):
    blocks = []
    for name in sorted(entries):
        name_raw = name.encode("ascii")
        payload = entries[name]
        blocks.extend(
            (
                len(name_raw).to_bytes(4, "big"),
                name_raw,
                len(payload).to_bytes(8, "big"),
                payload,
            )
        )
    return b"".join(blocks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output_path = args.output.resolve()
    try:
        output_path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise SystemExit("output must stay within the repository") from exc
    if output_path.exists():
        raise SystemExit(f"output already exists: {output_path}")

    fixture_parent = (
        REPO_ROOT / ".pytest-tmp-pre-request-observability"
    ).resolve()
    fixture_root = (fixture_parent / "vector-render").resolve()
    if fixture_root.parent != fixture_parent:
        raise SystemExit("fixture root escaped its guarded parent")
    try:
        output_path.relative_to(fixture_root)
    except ValueError:
        pass
    else:
        raise SystemExit("output must not overlap renderer fixture root")
    if fixture_root.exists():
        shutil.rmtree(fixture_root)
    fixture_root.mkdir(parents=True)

    sys.path.insert(0, str(REPO_ROOT))
    runner = __import__(
        "scripts.run_noncombat_outcome_evidence_expansion",
        fromlist=["*"],
    )
    verifier_tests = _load(
        "task8_verifier_tests",
        "tests/test_noncombat_outcome_evidence_verifier.py",
    )
    runner_tests = _load(
        "task8_runner_tests",
        "tests/test_noncombat_outcome_evidence_runner.py",
    )

    try:
        entries = {}
        entries.update(_compatibility_entries(verifier_tests, runner))
        entries.update(
            _bootstrap_vector_entries(verifier_tests, runner_tests, runner)
        )
        entries.update(_terminal_entries(verifier_tests, fixture_root))
        entries.update(_history_entries(verifier_tests))
        if len(entries) != 73:
            raise RuntimeError(f"unexpected vector entry count: {len(entries)}")
        bundle = _frame(entries)
        result = {
            "bundle_sha256": hashlib.sha256(bundle).hexdigest(),
            "bundle_size": len(bundle),
            "entry_count": len(entries),
            "entries": [
                {
                    "name": name,
                    "sha256": hashlib.sha256(entries[name]).hexdigest(),
                    "size": len(entries[name]),
                }
                for name in sorted(entries)
            ],
            "inputs": [
                {
                    "path": relative_path,
                    "sha256": hashlib.sha256(
                        (REPO_ROOT / relative_path).read_bytes()
                    ).hexdigest(),
                    "size": (REPO_ROOT / relative_path).stat().st_size,
                }
                for relative_path in INPUT_PATHS
            ],
            "raw_payload_size": sum(len(raw) for raw in entries.values()),
            "schema_version": "pre-request-qualification-vector-render-v1",
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(_canonical(result) + b"\n")
    finally:
        if fixture_root.exists():
            shutil.rmtree(fixture_root)


if __name__ == "__main__":
    main()
