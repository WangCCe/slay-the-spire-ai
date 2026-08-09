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


_SOURCE_INVENTORY_BODY = {
    "consumed_evidence_preservation": {
        "manifest_sha256": "9" * 64,
        "verified": True,
    },
    "modules": [],
    "public_dependencies": [],
    "schema_version": (
        "noncombat-card-acceptance-empirical-successor-source-inventory-v2"
    ),
}
_SOURCE_INVENTORY = {
    **_SOURCE_INVENTORY_BODY,
    "inventory_sha256": control.canonical_json_sha256(_SOURCE_INVENTORY_BODY),
}


@pytest.fixture(autouse=True)
def _source_qualification(monkeypatch):
    monkeypatch.setattr(
        control,
        "build_source_inventory",
        lambda _repo_root: copy.deepcopy(_SOURCE_INVENTORY),
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
    commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/master", commit)
    return repo, commit


def _inventory_standing_delegation():
    body = {
        "exclusions": list(control.STANDING_DELEGATION_EXCLUSIONS),
        "grant": {
            "granted_at": "2026-08-08T09:46:47+00:00",
            "provenance": {
                "message_id": "inventory-external-human-grant",
                "source": "external-human-message",
                "task_id": "inventory-test-task",
            },
            "verbatim_text": "The agent may represent this solo-maintainer repository.",
        },
        "revocation": control.STANDING_DELEGATION_REVOCATION,
        "schema_version": control.STANDING_DELEGATION_SCHEMA_VERSION,
        "scope": {
            "pushed_remote_ref": "origin/master",
            "registration_id_prefix": control.DELEGATED_REGISTRATION_ID_PREFIX,
            "request_class": control.DELEGATED_REQUEST_CLASS,
        },
    }
    return {**body, "delegation_sha256": control.canonical_json_sha256(body)}


def _inventory_revocation_observation(
    request,
    delegation,
    *,
    phase,
    checked_at,
    message_timestamp,
    revoked=False,
):
    watermark = {
        "message_id": f"inventory-latest-human-{phase}",
        "message_timestamp": message_timestamp,
        "task_id": "inventory-test-task",
    }
    body = {
        "authoritative_state_available": True,
        "authority_mode": "standing-delegation",
        "checked_at": checked_at,
        "delegation_sha256": delegation["delegation_sha256"],
        "latest_human_message_watermark": watermark,
        "phase": phase,
        "request_sha256": request["request_sha256"],
        "revocation_message_watermark": watermark if revoked else None,
        "revocation_observed": revoked,
        "schema_version": control.REVOCATION_OBSERVATION_SCHEMA_VERSION,
        "stage": request["stage"],
    }
    return {**body, "observation_sha256": control.canonical_json_sha256(body)}


def _inventory_authority(repo: Path, commit: str):
    request = control.build_stage_request(
        stage="inventory",
        request_id="card-acceptance-20260809-inventory-request-v1",
        source_commit=commit,
        source_inventory_sha256=_SOURCE_INVENTORY["inventory_sha256"],
        configuration_identity=control.experiment_configuration_identity(),
        prerequisite_bindings={},
        output_root=(
            repo / "reports" / "noncombat_card_acceptance_empirical_successor_test"
        ).as_posix(),
    )
    delegation = _inventory_standing_delegation()
    approval_observation = _inventory_revocation_observation(
        request,
        delegation,
        phase="approval",
        checked_at="2026-08-09T10:00:00+00:00",
        message_timestamp="2026-08-09T09:59:59+00:00",
    )
    approval = control.bind_delegated_approval(
        request=request,
        request_review_sha256="c" * 64,
        delegation=delegation,
        approval_observation=approval_observation,
        resolved_at="2026-08-09T10:00:00+00:00",
    )
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="card-acceptance-20260809-inventory-authorization-v1",
        request_review_sha256="c" * 64,
        approval_record_sha256=approval["approval_sha256"],
    )
    launch_observation = _inventory_revocation_observation(
        request,
        delegation,
        phase="launch",
        checked_at="2026-08-09T10:01:00+00:00",
        message_timestamp="2026-08-09T10:00:59+00:00",
    )
    return request, authorization, approval, launch_observation


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
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )

    artifact = seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
        approval_record=approval,
        launch_observation=launch_observation,
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
    assert artifact["launch_authority_sha256"] == launch_observation[
        "observation_sha256"
    ]
    assert artifact["source_inventory_sha256"] == _SOURCE_INVENTORY[
        "inventory_sha256"
    ]
    assert artifact["authority_evidence"]["build_launch_observation"] == (
        launch_observation
    )
    assert artifact["authority_evidence"]["source_inventory"][
        "inventory_sha256"
    ] == _SOURCE_INVENTORY["inventory_sha256"]
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
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )

    artifact = seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
        approval_record=approval,
        launch_observation=launch_observation,
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
        approval_record=approval,
        launch_observation=launch_observation,
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
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )
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
        approval_record=approval,
        launch_observation=launch_observation,
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
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )
    artifact = seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
        approval_record=approval,
        launch_observation=launch_observation,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("verification gained cohort materialization authority")

    monkeypatch.setattr(seed_inventory, "_select_fresh_cohorts", forbidden)
    monkeypatch.setattr(seed_inventory, "_publish_inventory_once", forbidden)
    fresh_launch_observation = _inventory_revocation_observation(
        request,
        approval["delegation"],
        phase="launch",
        checked_at="2026-08-09T10:02:00+00:00",
        message_timestamp="2026-08-09T10:01:59+00:00",
    )

    assert seed_inventory.verify_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
        approval_record=approval,
        launch_observation=fresh_launch_observation,
    ) == artifact
    assert artifact["launch_authority_sha256"] == launch_observation[
        "observation_sha256"
    ]


def test_inventory_authority_fails_before_source_discovery(tmp_path, monkeypatch):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    (
        inventory_request,
        _inventory_authorization,
        inventory_approval,
        inventory_launch,
    ) = _inventory_authority(repo, commit)
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
            approval_record=inventory_approval,
            launch_observation=inventory_launch,
        )
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="authorization"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=inventory_request,
            authorization=None,
            approval_record=inventory_approval,
            launch_observation=inventory_launch,
        )


def test_inventory_launch_and_source_qualification_fail_before_discovery(
    tmp_path, monkeypatch
):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("source discovery ran before launch/source qualification")

    monkeypatch.setattr(seed_inventory, "_list_registered_source_paths", forbidden)
    revoked = _inventory_revocation_observation(
        request,
        approval["delegation"],
        phase="launch",
        checked_at="2026-08-09T10:02:00+00:00",
        message_timestamp="2026-08-09T10:01:59+00:00",
        revoked=True,
    )
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="revocation|revoked"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=revoked,
        )

    monkeypatch.setattr(
        control,
        "build_source_inventory",
        lambda _repo_root: (_ for _ in ()).throw(
            control.SuccessorControlError("preservation drift")
        ),
    )
    with pytest.raises(
        seed_inventory.SeedInventoryBlocked,
        match="source qualification|preservation",
    ):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
        )


def test_inventory_is_write_once_and_rejects_mutated_materialized_bytes(tmp_path):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )
    seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
        approval_record=approval,
        launch_observation=launch_observation,
    )

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="already exists"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
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
            approval_record=approval,
            launch_observation=launch_observation,
        )


def test_verify_inventory_rejects_rehashed_build_launch_substitution(tmp_path):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )
    seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
        approval_record=approval,
        launch_observation=launch_observation,
    )
    path = Path(request["output_root"]) / seed_inventory.INVENTORY_FILENAME
    changed = json.loads(path.read_text(encoding="ascii"))
    changed["launch_authority_sha256"] = "1" * 64
    body = {key: value for key, value in changed.items() if key != "inventory_sha256"}
    changed["inventory_sha256"] = hashlib.sha256(_json_bytes(body)).hexdigest()
    path.write_bytes(_json_bytes(changed))

    with pytest.raises(
        seed_inventory.SeedInventoryBlocked,
        match="authority evidence|launch authority|build launch",
    ):
        seed_inventory.verify_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
        )


def test_inventory_validation_rejects_unknown_fields(tmp_path):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )
    artifact = seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
        approval_record=approval,
        launch_observation=launch_observation,
    )
    changed = copy.deepcopy(artifact)
    changed["extra"] = False
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="fields"):
        seed_inventory.validate_inventory(changed)


def test_inventory_cli_requires_and_forwards_approval_and_launch(
    tmp_path, monkeypatch, capsysbinary
):
    paths = {}
    for name in ("request", "authorization", "approval", "launch"):
        path = tmp_path / f"{name}.json"
        path.write_bytes(_json_bytes({"name": name}))
        paths[name] = path
    observed = {}

    def fake_build_inventory(**kwargs):
        observed.update(kwargs)
        return {"verified": True}

    monkeypatch.setattr(seed_inventory, "build_inventory", fake_build_inventory)
    assert seed_inventory.main(
        [
            "build-inventory",
            "--repo-root",
            str(tmp_path),
            "--request",
            str(paths["request"]),
            "--authorization",
            str(paths["authorization"]),
            "--approval-record",
            str(paths["approval"]),
            "--launch-observation",
            str(paths["launch"]),
        ]
    ) == 0
    assert observed == {
        "approval_record": {"name": "approval"},
        "authorization": {"name": "authorization"},
        "launch_observation": {"name": "launch"},
        "repo_root": str(tmp_path),
        "request": {"name": "request"},
    }
    assert capsysbinary.readouterr().out == _json_bytes({"verified": True})

    with pytest.raises(SystemExit, match="2"):
        seed_inventory.main(
            [
                "verify-inventory",
                "--repo-root",
                str(tmp_path),
                "--request",
                str(paths["request"]),
                "--authorization",
                str(paths["authorization"]),
                "--approval-record",
                str(paths["approval"]),
            ]
        )
