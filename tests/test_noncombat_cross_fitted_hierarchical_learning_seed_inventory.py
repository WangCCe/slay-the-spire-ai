from __future__ import annotations

import ast
import copy
import gzip
import hashlib
import io
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

import analysis_scripts.noncombat_cross_fitted_hierarchical_learning_seed_inventory as seed_inventory
import analysis_scripts.verify_noncombat_cross_fitted_empirical_successor_readiness as readiness_verifier


ROOT = Path(__file__).resolve().parents[1]


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit_files(tmp_path: Path, files: dict[str, bytes | str]) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "seed-inventory@example.invalid")
    _git(repo, "config", "user.name", "Seed Inventory Test")
    for relative, payload in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        else:
            path.write_text(payload, encoding="utf-8")
    _git(repo, "add", "--", "reports")
    _git(repo, "commit", "-m", "seed fixtures")
    return repo, _git(repo, "rev-parse", "HEAD")


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"


def _synthetic_inventory(repository_commit: str) -> dict[str, object]:
    reserved = list(range(71152, 71664))
    return seed_inventory.validate_seed_inventory(
        {
            "canonical_search_start": 0,
            "excluded_seed_count": len(reserved),
            "excluded_seeds": reserved,
            "repository_commit": repository_commit,
            "reserved_seed_ranges": [
                {
                    "end_inclusive": 71663,
                    "name": "previous_untouched_holdout",
                    "start_inclusive": 71152,
                }
            ],
            "row_count": 0,
            "rows": [],
            "schema_version": seed_inventory.SEED_INVENTORY_SCHEMA_VERSION,
            "source_bindings": [],
            "source_count": 0,
        }
    )


def _deterministic_gzip(payload: bytes, *, mtime: int = 0) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        fileobj=buffer, mode="wb", filename="", mtime=mtime
    ) as handle:
        handle.write(payload)
    return buffer.getvalue()


def _readiness_candidate(repository_commit: str) -> dict[str, object]:
    inventory = _synthetic_inventory(repository_commit)
    schedule = seed_inventory.materialize_fresh_schedule(inventory)
    consumed = list(range(10_000, 10_512))
    consumed_binding = {
        "path": (
            "reports/noncombat_cross_fitted_hierarchical_learning_successor_"
            "20260806_r1/registration.json"
        ),
        "sha256": "1" * 64,
        "size_bytes": 1,
    }
    return {
        "authority": {
            name: False
            for name in (
                "causal_claim",
                "communication_mod",
                "empirical_registration",
                "evaluation",
                "execution_authorization",
                "execution_request",
                "external_approval",
                "formal_rl",
                "gameplay",
                "model_fitting",
                "model_loading",
                "native_loading",
                "ope",
                "policy_quality",
                "promotion",
                "qualification",
                "seed_access",
                "training",
            )
        },
        "candidate_schedule": schedule,
        "consumed_cohort": {
            "registration_binding": consumed_binding,
            "registration_id": "consumed-registration",
            "seed_count": len(consumed),
            "seeds": consumed,
            "seeds_sha256": hashlib.sha256(_json_bytes(consumed)).hexdigest(),
        },
        "disjointness": {
            "collision_count": 0,
            "collisions": [],
            "status": "passed",
        },
        "historical_seed_inventory": inventory,
        "schema_version": (
            "noncombat-cross-fitted-empirical-successor-readiness-candidate-v1"
        ),
        "source_commit": repository_commit,
    }


def test_module_import_is_source_only_and_stdlib_only():
    source_path = (
        ROOT
        / "analysis_scripts"
        / "noncombat_cross_fitted_hierarchical_learning_seed_inventory.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots <= set(sys.stdlib_module_names)
    assert imported_roots.isdisjoint(
        {"analysis_scripts", "numpy", "spirecomm", "sts_lightspeed", "torch"}
    )


def test_readiness_candidate_decoder_reconstructs_complete_fresh_cohort():
    commit = "a" * 40
    candidate = _readiness_candidate(commit)
    canonical = _json_bytes(candidate)
    stored = _deterministic_gzip(canonical)
    binding = {
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_size_bytes": len(canonical),
        "encoding": "gzip-mtime-zero-v1",
        "sha256": hashlib.sha256(stored).hexdigest(),
        "size_bytes": len(stored),
    }

    decoded = seed_inventory.decode_readiness_candidate_artifact(
        stored,
        expected_binding=binding,
        expected_source_commit=commit,
    )

    assert decoded == candidate
    assert decoded["candidate_schedule"]["seeds"] == list(range(512))
    assert decoded["disjointness"] == {
        "collision_count": 0,
        "collisions": [],
        "status": "passed",
    }


def test_readiness_candidate_decoder_rejects_nondeterministic_gzip():
    commit = "a" * 40
    candidate = _readiness_candidate(commit)
    canonical = _json_bytes(candidate)
    stored = _deterministic_gzip(canonical, mtime=1)
    binding = {
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_size_bytes": len(canonical),
        "encoding": "gzip-mtime-zero-v1",
        "sha256": hashlib.sha256(stored).hexdigest(),
        "size_bytes": len(stored),
    }

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="deterministic"):
        seed_inventory.decode_readiness_candidate_artifact(
            stored,
            expected_binding=binding,
            expected_source_commit=commit,
        )


@pytest.mark.parametrize(
    ("case", "error"),
    [
        ("authority", "authority"),
        ("authority_zero", "authority"),
        ("authority_one", "authority"),
        ("consumed_count_float", "consumed cohort"),
        ("disjointness_count_float", "disjointness|not disjoint"),
        ("fresh_schedule", "fresh schedule|fixed selection"),
        ("historical_inventory", "source commit"),
        ("collision", "not disjoint"),
    ],
)
def test_readiness_candidate_decoder_rejects_semantic_drift(case, error):
    commit = "a" * 40
    candidate = _readiness_candidate(commit)
    if case == "authority":
        candidate["authority"]["training"] = True
    elif case == "authority_zero":
        candidate["authority"]["training"] = 0
    elif case == "authority_one":
        candidate["authority"]["training"] = 1
    elif case == "consumed_count_float":
        candidate["consumed_cohort"]["seed_count"] = 512.0
    elif case == "disjointness_count_float":
        candidate["disjointness"]["collision_count"] = 0.0
    elif case == "fresh_schedule":
        candidate["candidate_schedule"]["seeds"][0:2] = [1, 0]
    elif case == "historical_inventory":
        candidate["historical_seed_inventory"]["repository_commit"] = "b" * 40
    elif case == "collision":
        consumed = [0, *range(10_000, 10_511)]
        candidate["consumed_cohort"]["seeds"] = consumed
        candidate["consumed_cohort"]["seeds_sha256"] = hashlib.sha256(
            _json_bytes(consumed)
        ).hexdigest()
        candidate["disjointness"] = {
            "collision_count": 1,
            "collisions": [0],
            "status": "failed",
        }
    else:  # pragma: no cover - parametrization owns the cases.
        raise AssertionError(case)
    canonical = _json_bytes(candidate)
    stored = _deterministic_gzip(canonical)
    binding = {
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_size_bytes": len(canonical),
        "encoding": "gzip-mtime-zero-v1",
        "sha256": hashlib.sha256(stored).hexdigest(),
        "size_bytes": len(stored),
    }

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match=error):
        seed_inventory.decode_readiness_candidate_artifact(
            stored,
            expected_binding=binding,
            expected_source_commit=commit,
        )


def test_fixed_tree_inventory_covers_formats_roles_and_predecessor_outputs(tmp_path):
    json_payload = _json_bytes(
        {
            "used_seeds": [1, "2"],
            "nested": {"future_seed": 3},
            "cohorts": {"train": [4], "canary": [5], "holdout": [6]},
        }
    )
    jsonl_payload = b"\n".join(
        [
            _json_bytes({"diagnostic_seeds": [7]}).rstrip(b"\n"),
            _json_bytes({"reserved_seeds": [8]}).rstrip(b"\n"),
        ]
    ) + b"\n"
    gzip_document = _json_bytes({"qualification_seed": 9})
    gzip_payload = gzip.compress(gzip_document, mtime=0)
    gzip_jsonl_payload = gzip.compress(
        _json_bytes({"diagnostic_seed": 12}), mtime=0
    )
    predecessor_payload = _json_bytes(
        {"registration": {"scheduled_seeds": [10]}, "output_seed": 11}
    )
    repo, commit = _commit_files(
        tmp_path,
        {
            "reports/a.json": json_payload,
            "reports/b.jsonl": jsonl_payload,
            "reports/c.json.gz": gzip_payload,
            "reports/d.jsonl.gz": gzip_jsonl_payload,
            "reports/noncombat_hierarchical_predecessor/output/registration.json": (
                predecessor_payload
            ),
            "reports/no-seeds.json": _json_bytes({"value": 999}),
            "reports/notes.md": "seed 777 is prose, not a structured artifact\n",
        },
    )

    (repo / "reports" / "a.json").write_bytes(_json_bytes({"used_seeds": [900]}))
    (repo / "reports" / "dirty-untracked.json").write_bytes(
        _json_bytes({"used_seeds": [901]})
    )

    inventory = seed_inventory.build_seed_inventory(
        repo, repository_commit=commit
    )
    assert set(inventory) == {
        "canonical_search_start",
        "excluded_seed_count",
        "excluded_seeds",
        "repository_commit",
        "reserved_seed_ranges",
        "row_count",
        "rows",
        "schema_version",
        "source_bindings",
        "source_count",
    }
    assert inventory["repository_commit"] == commit
    assert inventory["canonical_search_start"] == 0
    assert inventory["reserved_seed_ranges"] == [
        {
            "end_inclusive": 71663,
            "name": "previous_untouched_holdout",
            "start_inclusive": 71152,
        }
    ]
    assert set(range(1, 13)) <= set(inventory["excluded_seeds"])
    assert set(range(71152, 71664)) <= set(inventory["excluded_seeds"])
    assert 900 not in inventory["excluded_seeds"]
    assert 901 not in inventory["excluded_seeds"]

    roles = {(row["seed"], row["role"]) for row in inventory["rows"]}
    assert {
        (1, "used"),
        (2, "used"),
        (3, "seed"),
        (4, "training"),
        (5, "canary"),
        (6, "holdout"),
        (7, "diagnostic"),
        (8, "reserved"),
        (9, "qualification"),
        (10, "seed"),
        (11, "seed"),
        (12, "diagnostic"),
    } <= roles
    assert all(
        set(row)
        == {"document_index", "json_path", "role", "seed", "source_path"}
        for row in inventory["rows"]
    )

    bindings = {row["path"]: row for row in inventory["source_bindings"]}
    assert "reports/no-seeds.json" not in bindings
    assert "reports/dirty-untracked.json" not in bindings
    assert bindings["reports/a.json"] == {
        "document_count": 1,
        "format": "json",
        "path": "reports/a.json",
        "row_count": 6,
        "sha256": hashlib.sha256(json_payload).hexdigest(),
        "size_bytes": len(json_payload),
    }
    assert bindings["reports/b.jsonl"]["document_count"] == 2
    assert bindings["reports/c.json.gz"]["sha256"] == hashlib.sha256(
        gzip_payload
    ).hexdigest()
    assert bindings["reports/d.jsonl.gz"] == {
        "document_count": 1,
        "format": "jsonl.gz",
        "path": "reports/d.jsonl.gz",
        "row_count": 1,
        "sha256": hashlib.sha256(gzip_jsonl_payload).hexdigest(),
        "size_bytes": len(gzip_jsonl_payload),
    }
    assert (
        "reports/noncombat_hierarchical_predecessor/output/registration.json"
        in bindings
    )
    assert seed_inventory.verify_seed_inventory(inventory, repo) == inventory


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            "reports/noncombat_cross_fitted_empirical_successor_readiness_"
            "20260808_r2/candidate_seed_inventory.json.gz",
            True,
        ),
        (
            "reports/noncombat_cross_fitted_empirical_successor_readiness_"
            "attempts/commit/attempt_terminal.json",
            True,
        ),
        (
            "reports/.noncombat_cross_fitted_empirical_successor_readiness_"
            "20260808_r3.commit.staging/candidate_seed_inventory.json.gz",
            True,
        ),
        (
            "reports/.noncombat_cross_fitted_empirical_successor_readiness_"
            "20260808_r3.random.sealed/report.json",
            True,
        ),
        ("reports/legitimate/candidate_seed_inventory.json.gz", False),
        (
            "reports/archive/noncombat_cross_fitted_empirical_successor_readiness_"
            "20260808_r2/report.json",
            False,
        ),
        (
            "reports/noncombat_cross_fitted_empirical_successor_readiness/"
            "report.json",
            False,
        ),
        (
            "reports/Noncombat_cross_fitted_empirical_successor_readiness_"
            "20260808_r2/report.json",
            False,
        ),
    ],
)
def test_readiness_derived_path_classifiers_are_exact_and_independent(path, expected):
    assert seed_inventory._is_readiness_derived_report_path(path) is expected
    assert readiness_verifier._is_readiness_derived_report_path(path) is expected


def test_readiness_derived_reports_are_excluded_before_blob_loading_and_recursion(
    tmp_path, monkeypatch
):
    legitimate_candidate = "reports/legitimate/candidate_seed_inventory.json.gz"
    lookalike = (
        "reports/archive/noncombat_cross_fitted_empirical_successor_readiness_"
        "20260808_r2/attempt_terminal.json"
    )
    excluded_final = (
        "reports/noncombat_cross_fitted_empirical_successor_readiness_"
        "20260808_r2/candidate_seed_inventory.json.gz"
    )
    excluded_attempt = (
        "reports/noncombat_cross_fitted_empirical_successor_readiness_"
        "attempts/deadbeef/attempt_terminal.json"
    )
    excluded_closeout = (
        "reports/noncombat_cross_fitted_empirical_successor_readiness_"
        "20260808_r3_closeout.json"
    )
    excluded_staging = (
        "reports/.noncombat_cross_fitted_empirical_successor_readiness_"
        "20260808_r3.commit.staging/candidate_seed_inventory.json.gz"
    )
    excluded_sealed = (
        "reports/.noncombat_cross_fitted_empirical_successor_readiness_"
        "20260808_r3.random.sealed/candidate_seed_inventory.json.gz"
    )
    repo, commit = _commit_files(
        tmp_path,
        {
            legitimate_candidate: _deterministic_gzip(
                _json_bytes({"used_seeds": [101]})
            ),
            lookalike: _json_bytes({"used_seeds": [102]}),
            excluded_final: _deterministic_gzip(
                _json_bytes(
                    {
                        "historical_seed_inventory": {
                            "rows": [{"seed": 901}, {"seed": 902}]
                        }
                    }
                )
            ),
            excluded_attempt: _json_bytes({"attempt_seed": 903}),
            excluded_closeout: _json_bytes({"closeout_seed": 904}),
            excluded_staging: b"not a gzip stream",
            excluded_sealed: b"also not a gzip stream",
        },
    )

    producer_blob_paths = []
    original_blob_batch = seed_inventory._git_blob_batch

    def observe_producer_blobs(repo_root, *, repository_commit, paths):
        producer_blob_paths.extend(paths)
        return original_blob_batch(
            repo_root,
            repository_commit=repository_commit,
            paths=paths,
        )

    verifier_blob_paths = []
    original_iter_blobs = readiness_verifier._iter_git_blobs

    def observe_verifier_blobs(repo_root, *, commit, paths):
        verifier_blob_paths.extend(paths)
        yield from original_iter_blobs(repo_root, commit=commit, paths=paths)

    monkeypatch.setattr(seed_inventory, "_git_blob_batch", observe_producer_blobs)
    monkeypatch.setattr(
        readiness_verifier, "_iter_git_blobs", observe_verifier_blobs
    )

    produced = seed_inventory.build_seed_inventory(repo, repository_commit=commit)
    rebuilt = readiness_verifier.rebuild_seed_inventory(
        repo, repository_commit=commit
    )

    assert produced == rebuilt
    assert producer_blob_paths == sorted([legitimate_candidate, lookalike])
    assert verifier_blob_paths == producer_blob_paths
    assert {101, 102} <= set(produced["excluded_seeds"])
    assert {901, 902, 903, 904}.isdisjoint(produced["excluded_seeds"])
    assert {binding["path"] for binding in produced["source_bindings"]} == {
        legitimate_candidate,
        lookalike,
    }


@pytest.mark.parametrize(
    ("path", "payload", "message"),
    [
        ("reports/bad.json", b'{"seed":1,"seed":2}\n', "duplicate"),
        ("reports/bad.json", b'{"seed":NaN}\n', "non-finite"),
        ("reports/bad.jsonl", b'{"seed":1}\n\n{"seed":2}\n', "blank"),
        ("reports/bad.jsonl", b'{"seed":1}\nnot-json\n', "JSONL"),
        ("reports/bad.json.gz", b"not gzip", "gzip"),
        (
            "reports/bad.json.gz",
            gzip.compress(b'{"seed":1,"seed":2}\n', mtime=0),
            "duplicate",
        ),
        ("reports/historical-seeds.yaml", b"seeds: [1, 2]\n", "unsupported"),
        ("reports/historical-cohort.jsonl.gz", b"opaque", "gzip"),
    ],
)
def test_candidate_seed_artifacts_fail_closed(tmp_path, path, payload, message):
    repo, commit = _commit_files(tmp_path, {path: payload})
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match=message):
        seed_inventory.build_seed_inventory(repo, repository_commit=commit)


def test_inventory_validation_and_fixed_tree_rebuild_are_strict(tmp_path):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/seeds.json": _json_bytes({"used_seeds": [0, 2, 4]})},
    )
    inventory = seed_inventory.build_seed_inventory(repo, repository_commit=commit)
    assert seed_inventory.validate_seed_inventory(inventory) == inventory
    assert seed_inventory.rebuild_seed_inventory(
        repo, repository_commit=commit
    ) == inventory

    mutations = []
    extra = copy.deepcopy(inventory)
    extra["extra"] = False
    mutations.append(extra)
    row_extra = copy.deepcopy(inventory)
    row_extra["rows"][0]["extra"] = False
    mutations.append(row_extra)
    binding_extra = copy.deepcopy(inventory)
    binding_extra["source_bindings"][0]["extra"] = False
    mutations.append(binding_extra)
    wrong_union = copy.deepcopy(inventory)
    wrong_union["excluded_seeds"].append(999999)
    wrong_union["excluded_seed_count"] += 1
    mutations.append(wrong_union)

    for changed in mutations:
        with pytest.raises(seed_inventory.SeedInventoryBlocked):
            seed_inventory.validate_seed_inventory(changed)

    rebound = copy.deepcopy(inventory)
    rebound["source_bindings"][0]["sha256"] = "f" * 64
    assert seed_inventory.validate_seed_inventory(rebound) == rebound
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="rebuild"):
        seed_inventory.verify_seed_inventory(rebound, repo)


def test_fresh_schedule_is_the_only_first_512_ascending_selection(tmp_path):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/seeds.json": _json_bytes({"used_seeds": [0, 2, 4]})},
    )
    inventory = seed_inventory.build_seed_inventory(repo, repository_commit=commit)
    schedule = seed_inventory.materialize_fresh_schedule(inventory)
    expected = []
    candidate = seed_inventory.CANONICAL_SEARCH_START
    excluded = set(inventory["excluded_seeds"])
    while len(expected) < seed_inventory.TRAINING_SEED_COUNT:
        if candidate not in excluded:
            expected.append(candidate)
        candidate += 1

    assert set(schedule) == {
        "canonical_search_start",
        "inventory_sha256",
        "schema_version",
        "seed_count",
        "seeds",
    }
    assert schedule["canonical_search_start"] == 0
    assert schedule["seed_count"] == 512
    assert schedule["seeds"] == expected
    assert schedule["seeds"][:4] == [1, 3, 5, 6]
    assert schedule["inventory_sha256"] == hashlib.sha256(
        seed_inventory.canonical_json_bytes(inventory)
    ).hexdigest()
    assert seed_inventory.validate_fresh_schedule(inventory, schedule) == schedule

    assert list(inspect.signature(seed_inventory.materialize_fresh_schedule).parameters) == [
        "inventory"
    ]
    for override in (
        {"start": 1000},
        {"search_start": 1000},
        {"seeds": range(512)},
        {"scheduled_seeds": range(512)},
    ):
        with pytest.raises(TypeError):
            seed_inventory.materialize_fresh_schedule(inventory, **override)

    changed = copy.deepcopy(schedule)
    changed["seeds"][0] = 999
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="schedule"):
        seed_inventory.validate_fresh_schedule(inventory, changed)
    extra = copy.deepcopy(schedule)
    extra["extra"] = False
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="schedule"):
        seed_inventory.validate_fresh_schedule(inventory, extra)
