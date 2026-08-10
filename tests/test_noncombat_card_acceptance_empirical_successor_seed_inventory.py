from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

import analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment as control
from analysis_scripts import (
    noncombat_card_acceptance_empirical_successor_seed_inventory as seed_inventory,
)


ROOT = Path(__file__).resolve().parents[1]
SEED_INVENTORY_SCRIPT = (
    ROOT
    / "analysis_scripts"
    / "noncombat_card_acceptance_empirical_successor_seed_inventory.py"
)


def _dispatch_process_identity(*, isolated_mode=True):
    interpreter = Path(sys.executable).resolve().as_posix()
    script_path = SEED_INVENTORY_SCRIPT.resolve().as_posix()
    return {
        "command": [interpreter, "-I", script_path, "check-dispatch"],
        "interpreter": interpreter,
        "isolated_mode": isolated_mode,
        "script_path": script_path,
        "script_sha256": hashlib.sha256(
            SEED_INVENTORY_SCRIPT.read_bytes()
        ).hexdigest(),
        "working_directory": ROOT.resolve().as_posix(),
    }


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
        "grant": copy.deepcopy(control.STANDING_DELEGATION_GRANT),
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
        "task_id": delegation["grant"]["provenance"]["task_id"],
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


def _started_receipt_path(request) -> Path:
    output = Path(request["output_root"])
    return (
        output.with_name(f"{output.name}_attempts")
        / request["request_sha256"]
        / "started.json"
    )


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
    assert _started_receipt_path(request).is_file()
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


def test_started_receipt_persists_and_blocks_retry_after_source_failure(
    tmp_path, monkeypatch
):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seed": 1})},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )
    source_calls = 0

    def fail_after_start(*_args, **_kwargs):
        nonlocal source_calls
        source_calls += 1
        raise seed_inventory.SeedInventoryBlocked("synthetic historical source failure")

    monkeypatch.setattr(
        seed_inventory,
        "_build_source_registry_and_rows",
        fail_after_start,
    )

    with pytest.raises(
        seed_inventory.SeedInventoryBlocked,
        match="synthetic historical source failure",
    ):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
        )

    receipt_path = _started_receipt_path(request)
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    assert receipt_bytes == seed_inventory.canonical_json_bytes(receipt)
    assert receipt == {
        "approval_sha256": approval["approval_sha256"],
        "authorization_id": authorization["authorization_id"],
        "authorization_sha256": authorization["authorization_sha256"],
        "launch_observation_sha256": launch_observation["observation_sha256"],
        "receipt_sha256": receipt["receipt_sha256"],
        "request_id": request["request_id"],
        "request_sha256": request["request_sha256"],
        "schema_version": (
            "noncombat-card-acceptance-empirical-successor-"
            "seed-inventory-started-receipt-v1"
        ),
        "source_commit": request["source_commit"],
        "source_inventory_sha256": _SOURCE_INVENTORY["inventory_sha256"],
    }
    receipt_body = {
        key: value for key, value in receipt.items() if key != "receipt_sha256"
    }
    assert receipt["receipt_sha256"] == hashlib.sha256(
        seed_inventory.canonical_json_bytes(receipt_body)
    ).hexdigest()

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="already started"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
        )

    assert source_calls == 1
    assert receipt_path.read_bytes() == receipt_bytes
    output, staging = seed_inventory._inventory_paths(request)
    assert not output.exists()
    assert not staging.exists()


@pytest.mark.parametrize(
    "receipt_bytes",
    [b"", b"{", _json_bytes({"unexpected": True})],
    ids=["empty", "truncated", "invalid-canonical"],
)
def test_partial_started_receipt_blocks_before_source_discovery(
    tmp_path, monkeypatch, receipt_bytes
):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seed": 1})},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )
    receipt_path = _started_receipt_path(request)
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_bytes(receipt_bytes)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("source discovery ran after a partial started receipt")

    monkeypatch.setattr(
        seed_inventory,
        "_build_source_registry_and_rows",
        forbidden,
    )

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="already started"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
        )

    assert receipt_path.read_bytes() == receipt_bytes


def test_competing_started_receipt_writer_wins_without_source_discovery(
    tmp_path, monkeypatch
):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seed": 1})},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )
    receipt_path = _started_receipt_path(request)
    winner_bytes = b"competing-writer-receipt"
    original_open = Path.open
    race_pending = True

    def competing_open(path, mode="r", *args, **kwargs):
        nonlocal race_pending
        if path == receipt_path and mode == "xb" and race_pending:
            race_pending = False
            with original_open(path, "wb") as handle:
                handle.write(winner_bytes)
                handle.flush()
            return original_open(path, mode, *args, **kwargs)
        return original_open(path, mode, *args, **kwargs)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("source discovery ran after losing the receipt race")

    monkeypatch.setattr(Path, "open", competing_open)
    monkeypatch.setattr(
        seed_inventory,
        "_build_source_registry_and_rows",
        forbidden,
    )

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="already started"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
        )

    assert not race_pending
    assert receipt_path.read_bytes() == winner_bytes


def test_prestart_authority_failure_creates_no_started_receipt(
    tmp_path, monkeypatch
):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seed": 1})},
    )
    request, authorization, approval, _launch_observation = _inventory_authority(
        repo, commit
    )
    revoked = _inventory_revocation_observation(
        request,
        approval["delegation"],
        phase="launch",
        checked_at="2026-08-09T10:02:00+00:00",
        message_timestamp="2026-08-09T10:01:59+00:00",
        revoked=True,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("source discovery ran before authority validation")

    monkeypatch.setattr(
        seed_inventory,
        "_build_source_registry_and_rows",
        forbidden,
    )

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="revocation|revoked"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=revoked,
        )

    assert not _started_receipt_path(request).exists()


def test_build_inventory_accepts_pushed_publication_descendant(tmp_path):
    repo, source_commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, source_commit
    )
    publication = repo / "reports" / "published_inventory_authorization.json"
    publication.write_bytes(_json_bytes({"authorization": "published"}))
    _git(repo, "add", publication.relative_to(repo).as_posix())
    _git(repo, "commit", "-q", "-m", "publish inventory authority")
    published_commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/master", published_commit)

    artifact = seed_inventory.build_inventory(
        repo_root=repo,
        request=request,
        authorization=authorization,
        approval_record=approval,
        launch_observation=launch_observation,
    )

    assert artifact["repository_commit"] == source_commit
    assert published_commit != source_commit


def test_build_inventory_rejects_source_drift_in_pushed_descendant(
    tmp_path, monkeypatch
):
    repo, source_commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, source_commit
    )
    changed_source = repo / "analysis_scripts" / "changed_source.py"
    changed_source.parent.mkdir(parents=True, exist_ok=True)
    changed_source.write_text("CHANGED = True\n", encoding="ascii")
    _git(repo, "add", changed_source.relative_to(repo).as_posix())
    _git(repo, "commit", "-q", "-m", "change bound source")
    published_commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/master", published_commit)
    changed_inventory = copy.deepcopy(_SOURCE_INVENTORY)
    changed_inventory["inventory_sha256"] = "a" * 64
    monkeypatch.setattr(
        control,
        "build_source_inventory",
        lambda _repo_root: copy.deepcopy(changed_inventory),
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("source discovery ran after source inventory drift")

    monkeypatch.setattr(seed_inventory, "_list_registered_source_paths", forbidden)
    with pytest.raises(
        seed_inventory.SeedInventoryBlocked,
        match="source inventory digest",
    ):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
        )

    assert not _started_receipt_path(request).exists()


def test_build_inventory_rejects_unpushed_head_before_discovery(
    tmp_path, monkeypatch
):
    repo, source_commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, source_commit
    )
    publication = repo / "reports" / "unpublished_authorization.json"
    publication.write_bytes(_json_bytes({"authorization": "unpublished"}))
    _git(repo, "add", publication.relative_to(repo).as_posix())
    _git(repo, "commit", "-q", "-m", "unpublished inventory authority")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("source discovery ran before pushed Git qualification")

    monkeypatch.setattr(seed_inventory, "_list_registered_source_paths", forbidden)
    with pytest.raises(
        seed_inventory.SeedInventoryBlocked,
        match="pushed origin/master",
    ):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
        )

    assert not _started_receipt_path(request).exists()


def test_build_inventory_rejects_source_commit_outside_pushed_ancestry(
    tmp_path, monkeypatch
):
    repo, pushed_commit = _commit_files(
        tmp_path,
        {"reports/history/seeds.json": _json_bytes({"used_seeds": [1]})},
    )
    future = repo / "reports" / "future_source.json"
    future.write_bytes(_json_bytes({"source": "future"}))
    _git(repo, "add", future.relative_to(repo).as_posix())
    _git(repo, "commit", "-q", "-m", "future source")
    future_commit = _git(repo, "rev-parse", "HEAD")
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, future_commit
    )
    _git(repo, "checkout", "-q", pushed_commit)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("source discovery ran before source ancestry qualification")

    monkeypatch.setattr(seed_inventory, "_list_registered_source_paths", forbidden)
    with pytest.raises(
        seed_inventory.SeedInventoryBlocked,
        match="ancestor",
    ):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
        )

    assert not _started_receipt_path(request).exists()


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
        "reports/.readiness.r3.staging/candidate_seed_inventory.json.gz": (
            b"not a gzip stream"
        ),
        "reports/.historical_inventory.x.scratch/rows.json": b"malformed",
        "reports/.historical_inventory.x.sealed/rows.json": b"malformed",
        "reports/.historical_inventory.x.staging/rows.json.gz": b"malformed",
        "reports/.historical_inventory.x.temporary/rows.json": b"malformed",
        "reports/.historical_inventory.x.tmp/rows.json": b"malformed",
        "reports/historical_inventory_attempts/a/rows.json": b"malformed",
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
    excluded_by_path = {
        root["path"]: root["kind"]
        for root in artifact["source_registry"]["excluded_roots"]
    }
    assert excluded_by_path["reports/.readiness.r3.staging"] == "staging"
    assert excluded_by_path["reports/.historical_inventory.x.scratch"] == "scratch"
    assert excluded_by_path["reports/.historical_inventory.x.sealed"] == "sealed"
    assert excluded_by_path["reports/.historical_inventory.x.staging"] == "staging"
    assert excluded_by_path[
        "reports/.historical_inventory.x.temporary"
    ] == "temporary"
    assert excluded_by_path["reports/.historical_inventory.x.tmp"] == "temporary"
    assert excluded_by_path["reports/historical_inventory_attempts"] == "attempt"
    assert 99 in artifact["excluded_seeds"]
    assert {0, 1, 2, 3, 4, 5}.isdisjoint(artifact["excluded_seeds"])
    assert all(
        row["source_path"] not in generated
        for row in artifact["rows"]
    )
    assert artifact["source_registry"]["excluded_roots"] == sorted(
        artifact["source_registry"]["excluded_roots"],
        key=lambda row: row["path"],
    )


def test_exact_readiness_staging_path_is_excluded_before_blob_request(
    tmp_path, monkeypatch
):
    path = (
        "reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r3."
        "5777eef4a43065e6246481926f95d6cfcba04c88.staging/"
        "candidate_seed_inventory.json.gz"
    )
    root = path.rsplit("/", 1)[0]
    requested_paths = []

    monkeypatch.setattr(
        seed_inventory,
        "_list_tree_report_paths",
        lambda _repo_root, _repository_commit: [path],
    )

    def observe_blob_batch(_repo_root, *, repository_commit, paths):
        assert repository_commit == "0" * 40
        requested_paths.extend(paths)
        return {}

    monkeypatch.setattr(seed_inventory, "_git_blob_batch", observe_blob_batch)

    registry, rows, excluded = seed_inventory._build_source_registry_and_rows(
        tmp_path,
        repository_commit="0" * 40,
        output_root=(tmp_path / "reports" / "candidate").as_posix(),
    )

    assert requested_paths == []
    assert registry["sources"] == []
    assert registry["excluded_roots"] == [{"kind": "staging", "path": root}]
    assert rows == []
    assert excluded == []


def test_generated_root_tokens_in_ordinary_paths_remain_eligible(
    tmp_path, monkeypatch
):
    ordinary = {
        "reports/history/staging-result.json": _json_bytes({"used_seed": 91}),
        "reports/history/scratch/rows.json": _json_bytes({"used_seed": 92}),
        "reports/history/sealed-evidence/rows.json": _json_bytes({"used_seed": 93}),
        "reports/history/temporary.tmp-result.json": _json_bytes({"used_seed": 94}),
        "reports/history_attempt_log/rows.json": _json_bytes({"used_seed": 95}),
        "reports/history.staging/rows.json": _json_bytes({"used_seed": 96}),
        "reports/.staging.archive/rows.json": _json_bytes({"used_seed": 97}),
    }
    repo, commit = _commit_files(tmp_path, ordinary)
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

    assert loaded_paths == sorted(ordinary)
    assert artifact["source_registry"]["excluded_roots"] == []
    assert {row["path"] for row in artifact["source_registry"]["sources"]} == set(
        ordinary
    )
    assert {91, 92, 93, 94, 95, 96, 97} <= set(artifact["excluded_seeds"])


def test_malformed_ordinary_generated_token_path_still_fails_closed(tmp_path):
    repo, commit = _commit_files(
        tmp_path,
        {"reports/history/ordinary.staging.json": b"{"},
    )
    request, authorization, approval, launch_observation = _inventory_authority(
        repo, commit
    )

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="invalid strict JSON"):
        seed_inventory.build_inventory(
            repo_root=repo,
            request=request,
            authorization=authorization,
            approval_record=approval,
            launch_observation=launch_observation,
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


def test_isolated_dispatch_check_is_canonical_and_deterministic():
    command = [
        sys.executable,
        "-I",
        str(SEED_INVENTORY_SCRIPT),
        "check-dispatch",
    ]
    runs = [
        subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=False,
        )
        for _ in range(2)
    ]

    for completed in runs:
        assert completed.returncode == 0, completed.stderr.decode(
            "utf-8", errors="replace"
        )
        assert completed.stderr == b""
    assert runs[0].stdout == runs[1].stdout

    artifact = json.loads(runs[0].stdout)
    process_identity = _dispatch_process_identity()
    assert artifact == {
        **process_identity,
        "control_contract_sha256": hashlib.sha256(
            _json_bytes(control.experiment_contract())
        ).hexdigest(),
        "control_module": (
            "analysis_scripts."
            "noncombat_card_acceptance_empirical_successor_experiment"
        ),
        "control_module_path": (
            "analysis_scripts/"
            "noncombat_card_acceptance_empirical_successor_experiment.py"
        ),
        "schema_version": (
            "noncombat-card-acceptance-empirical-successor-"
            "seed-inventory-dispatch-check-v1"
        ),
    }
    assert runs[0].stdout == seed_inventory.canonical_json_bytes(artifact)


def test_dispatch_evidence_has_no_inventory_lifecycle_side_effects(
    monkeypatch, capsysbinary
):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("inventory lifecycle operation reached")

    for name in (
        "_build_source_registry_and_rows",
        "_git_blob_batch",
        "_git_command",
        "_inventory_paths",
        "_list_registered_source_paths",
        "_load_json_file",
        "_publish_inventory_once",
        "_require_unmaterialized",
        "_select_fresh_cohorts",
        "_start_inventory_once",
        "_started_receipt_path",
        "_validate_inventory_authority",
        "build_inventory",
        "verify_inventory",
    ):
        monkeypatch.setattr(seed_inventory, name, forbidden)

    expected_path = SEED_INVENTORY_SCRIPT.with_name(
        "noncombat_card_acceptance_empirical_successor_experiment.py"
    )
    control = types.SimpleNamespace(
        __file__=str(expected_path),
        experiment_contract=lambda: {"contract": "source-only"},
    )

    def import_module(name):
        assert name == (
            "analysis_scripts."
            "noncombat_card_acceptance_empirical_successor_experiment"
        )
        return control

    monkeypatch.setattr(seed_inventory.importlib, "import_module", import_module)
    monkeypatch.setattr(
        seed_inventory,
        "_dispatch_process_identity",
        _dispatch_process_identity,
    )

    assert seed_inventory.main(["check-dispatch"]) == 0
    artifact = json.loads(capsysbinary.readouterr().out)

    assert artifact["control_contract_sha256"] == hashlib.sha256(
        _json_bytes(control.experiment_contract())
    ).hexdigest()
    assert artifact["control_module_path"] == (
        "analysis_scripts/"
        "noncombat_card_acceptance_empirical_successor_experiment.py"
    )


def test_dispatch_evidence_requires_isolated_mode():
    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="isolated mode"):
        seed_inventory._build_dispatch_evidence(
            process_identity=_dispatch_process_identity(isolated_mode=False)
        )


def test_dispatch_evidence_rejects_control_module_path_drift(monkeypatch, tmp_path):
    control = types.SimpleNamespace(
        __file__=str(tmp_path / "substituted_control.py"),
        experiment_contract=lambda: {"contract": "substituted"},
    )
    monkeypatch.setattr(
        seed_inventory.importlib,
        "import_module",
        lambda _name: control,
    )

    with pytest.raises(seed_inventory.SeedInventoryBlocked, match="path is invalid"):
        seed_inventory._build_dispatch_evidence(
            process_identity=_dispatch_process_identity()
        )
