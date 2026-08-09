from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment as control
from analysis_scripts import (
    noncombat_card_acceptance_empirical_successor_seed_inventory as seed_inventory,
)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit_files(tmp_path: Path, files: dict[str, bytes]) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "synthetic@example.invalid")
    _git(repo, "config", "user.name", "Synthetic Test")
    for relative, payload in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "synthetic seed evidence")
    return repo, _git(repo, "rev-parse", "HEAD")


def _inventory_authority(repo: Path, commit: str):
    request = control.build_stage_request(
        stage="inventory",
        request_id="card-acceptance-20260809-inventory-request-v1",
        source_commit=commit,
        source_inventory_sha256="b" * 64,
        configuration_identity=control.experiment_configuration_identity(),
        prerequisite_bindings={},
        output_root=(
            repo / "reports" / "noncombat_card_acceptance_empirical_successor_test"
        ).as_posix(),
    )
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="card-acceptance-20260809-inventory-authorization-v1",
        request_review_sha256="c" * 64,
        approval_record_sha256="d" * 64,
    )
    return request, authorization


def _first_eligible(excluded: set[int], count: int) -> list[int]:
    selected = []
    candidate = 0
    while len(selected) < count:
        if candidate not in excluded:
            selected.append(candidate)
        candidate += 1
    return selected


def test_build_inventory_publishes_exact_fresh_disjoint_cohorts(tmp_path):
    repo, commit = _commit_files(
        tmp_path,
        {
            "reports/history/a.json": _json_bytes(
                {
                    "consumed_seeds": [0, 2],
                    "diagnostic_seed": 4,
                    "evaluation_seeds": [6],
                    "failed_accesses": [{"seed": 8}],
                    "reserved_seeds": [10],
                    "cohorts": {
                        "canary": [12],
                        "holdout": [14],
                        "training": [16],
                    },
                    "used_seed": 18,
                }
            ),
            "reports/history/no-seeds.json": _json_bytes({"metric": 999}),
        },
    )
    request, authorization = _inventory_authority(repo, commit)

    artifact = seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
    )

    output = Path(request["output_root"])
    assert (output / seed_inventory.INVENTORY_FILENAME).read_bytes() == (
        seed_inventory.canonical_json_bytes(artifact)
    )
    assert not list(output.parent.glob(f".{output.name}.*.staging"))
    assert artifact["source_registry"]["repository_commit"] == commit
    assert [row["path"] for row in artifact["source_registry"]["sources"]] == [
        "reports/history/a.json",
        "reports/history/no-seeds.json",
    ]

    excluded = set(artifact["excluded_seeds"])
    assert set(range(0, 19, 2)) <= excluded
    expected = _first_eligible(excluded, 1_152)
    assert artifact["cohorts"]["training"] == expected[:512]
    assert artifact["cohorts"]["canary"] == expected[512:640]
    assert artifact["cohorts"]["holdout"] == expected[640:]
    assert len(set().union(*map(set, artifact["cohorts"].values()))) == 1_152
    assert artifact["role_sha256"] == {
        role: hashlib.sha256(seed_inventory.canonical_json_bytes(seeds)).hexdigest()
        for role, seeds in artifact["cohorts"].items()
    }
    body = {key: value for key, value in artifact.items() if key != "inventory_sha256"}
    assert artifact["inventory_sha256"] == hashlib.sha256(
        seed_inventory.canonical_json_bytes(body)
    ).hexdigest()


def test_historical_exclusion_roles_include_failed_and_untouched_reservations(
    tmp_path,
):
    repo, commit = _commit_files(
        tmp_path,
        {
            "reports/history/roles.json": _json_bytes(
                {
                    "consumed_seed": 101,
                    "failed_accesses": [{"seed": 102}],
                    "prior_untouched_holdout_seeds": [103, 104],
                    "reserved_seed": 105,
                }
            )
        },
    )
    request, authorization = _inventory_authority(repo, commit)

    artifact = seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
    )

    assert {101, 102, 103, 104, 105} <= set(artifact["excluded_seeds"])
    assert {(row["seed"], row["role"]) for row in artifact["rows"]} == {
        (101, "consumed"),
        (102, "failed_access"),
        (103, "holdout"),
        (104, "holdout"),
        (105, "reserved"),
    }
    assert seed_inventory.verify_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
    ) == artifact


def test_generated_roots_are_excluded_before_blob_loading_and_recursion(
    tmp_path, monkeypatch
):
    legitimate = "reports/history/seeds.json"
    generated = {
        "reports/noncombat_card_acceptance_empirical_successor_old/rows.json": (
            _json_bytes({"used_seed": 0})
        ),
        "reports/noncombat_card_acceptance_empirical_successor_attempts/a/rows.json": (
            _json_bytes({"failed_seed": 1})
        ),
        "reports/.noncombat_card_acceptance_empirical_successor_old.x.scratch/rows.json": (
            _json_bytes({"reserved_seed": 2})
        ),
        "reports/.noncombat_card_acceptance_empirical_successor_old.x.sealed/rows.json": (
            _json_bytes({"holdout_seed": 3})
        ),
        "reports/.noncombat_card_acceptance_empirical_successor_old.x.staging/rows.json.gz": (
            b"not a gzip stream"
        ),
        "reports/.noncombat_card_acceptance_empirical_successor_old.x.tmp/rows.json": (
            _json_bytes({"training_seed": 5})
        ),
    }
    repo, commit = _commit_files(
        tmp_path,
        {
            legitimate: _json_bytes({"used_seed": 99}),
            **generated,
        },
    )
    request, authorization = _inventory_authority(repo, commit)
    loaded_paths = []
    original_blob_batch = seed_inventory._git_blob_batch

    def observe_blob_batch(repo_root, *, repository_commit, paths):
        loaded_paths.extend(paths)
        return original_blob_batch(
            repo_root,
            repository_commit=repository_commit,
            paths=paths,
        )

    monkeypatch.setattr(seed_inventory, "_git_blob_batch", observe_blob_batch)

    artifact = seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
    )

    assert loaded_paths == [legitimate]
    assert {source["path"] for source in artifact["source_registry"]["sources"]} == {
        legitimate
    }
    assert {root["kind"] for root in artifact["source_registry"]["excluded_roots"]} == {
        "attempt",
        "candidate",
        "scratch",
        "sealed",
        "staging",
        "temporary",
    }
    assert 99 in artifact["excluded_seeds"]
    assert {0, 1, 2, 3, 4, 5}.isdisjoint(artifact["excluded_seeds"])
    assert all(
        row["source_path"] not in generated
        for row in artifact["rows"]
    )


def test_verify_inventory_reconstructs_without_selector_or_materializer(
    tmp_path, monkeypatch
):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [0, 3, 7]})},
    )
    request, authorization = _inventory_authority(repo, commit)
    artifact = seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("verification gained cohort materialization authority")

    monkeypatch.setattr(seed_inventory, "_select_fresh_cohorts", forbidden)
    monkeypatch.setattr(seed_inventory, "_publish_inventory_once", forbidden)

    assert seed_inventory.verify_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
    ) == artifact


def test_inventory_authority_fails_before_source_discovery(tmp_path, monkeypatch):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    inventory_request, _inventory_authorization = _inventory_authority(repo, commit)
    training_request = control.build_stage_request(
        stage="training",
        request_id="card-acceptance-20260809-training-request-v1",
        source_commit=commit,
        source_inventory_sha256="b" * 64,
        configuration_identity=control.experiment_configuration_identity(),
        prerequisite_bindings={"registration_sha256": "e" * 64},
        output_root=(repo / "reports" / "training").as_posix(),
    )
    training_authorization = control.build_stage_authorization(
        request=training_request,
        authorization_id="card-acceptance-20260809-training-authorization-v1",
        request_review_sha256="c" * 64,
        approval_record_sha256="d" * 64,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("source discovery ran before authority validation")

    monkeypatch.setattr(seed_inventory, "_list_registered_source_paths", forbidden)

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="inventory"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=training_request,
            authorization=training_authorization,
        )
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="authorization"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=inventory_request,
            authorization=None,
        )


def test_inventory_is_write_once_and_rejects_mutated_materialized_bytes(tmp_path):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    request, authorization = _inventory_authority(repo, commit)
    seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
    )

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="already exists"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
        )

    path = Path(request["output_root"]) / seed_inventory.INVENTORY_FILENAME
    changed = json.loads(path.read_text(encoding="ascii"))
    changed["cohorts"]["training"][0] += 1
    path.write_bytes(_json_bytes(changed))
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="cohort|inventory"):
        seed_inventory.verify_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
        )


def test_inventory_validation_rejects_unknown_fields(tmp_path):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    request, authorization = _inventory_authority(repo, commit)
    artifact = seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
    )
    changed = copy.deepcopy(artifact)
    changed["extra"] = False
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="fields"):
        seed_inventory.validate_inventory(changed)
