from __future__ import annotations

import hashlib
import gzip
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from analysis_scripts import audit_cross_fitted_baseline_support as audit


REPO_ROOT = Path(__file__).resolve().parents[1]


def _decision(
    *,
    selected: str = "take",
    advantage: float = 0.25,
    unclipped: float = 0.1,
    greedy: str = "take",
    trajectory_id: str = "seed-1",
    fold_id: str = "fold-1",
    decision_index: int = 1,
) -> dict[str, object]:
    clipped = min(3.0, max(0.0, unclipped))
    return {
        "advantage": advantage,
        "baseline_fit_trajectory_ids": [
            "seed-0",
            "seed-2",
            "seed-3",
        ],
        "baseline_prediction": clipped,
        "category": "card_reward",
        "decision_id": f"{trajectory_id}:decision-{decision_index}",
        "decision_index": decision_index,
        "diagnostic": {
            "candidate_scores": {
                "take:a": 0.2 if greedy == "take" else 0.0,
                "skip": 0.2 if greedy == "skip" else 0.0,
                "bowl": 0.2 if greedy == "bowl" else -0.1,
            },
            "candidates": [
                {"action_id": "take:a", "kind": "take"},
                {"action_id": "skip", "kind": "skip"},
                {"action_id": "bowl", "kind": "bowl"},
            ],
            "category": "card_reward",
            "chunk_index": 4,
            "conditional_probabilities": {
                "take:a": 1.0,
                "skip": 1.0,
                "bowl": 1.0,
            },
            "decision_id": f"{trajectory_id}:decision-{decision_index}",
            "decision_index": decision_index,
            "family_order": ["bowl", "skip", "take"],
            "family_probabilities": {
                "bowl": 0.1,
                "skip": 0.4,
                "take": 0.5,
            },
            "formal_reward": {
                "floor_progress": 0.0,
                "scalar_reward": 0.0,
                "terminal_victory": 0,
            },
            "multi_family": True,
            "raw_score_max_action_ids": [
                "take:a" if greedy == "take" else greedy
            ],
            "raw_score_max_family_ids": [greedy],
            "selected_action_id": "take:a" if selected == "take" else selected,
            "selected_family": selected,
        },
        "fold_id": fold_id,
        "policy_terms": {
            "conditional_entropy": 0.0,
            "family_entropy": -sum(
                p * math.log(p) for p in (0.1, 0.4, 0.5)
            ),
            "selected_action_id": "take:a" if selected == "take" else selected,
            "selected_conditional_log_probability": 0.0,
            "selected_family": selected,
            "selected_family_log_probability": math.log(
                {"bowl": 0.1, "skip": 0.4, "take": 0.5}[selected]
            ),
            "selected_joint_log_probability": math.log(
                {"bowl": 0.1, "skip": 0.4, "take": 0.5}[selected]
            ),
        },
        "prediction": {
            "clipped": clipped,
            "unclipped": unclipped,
            "was_clipped": unclipped != clipped,
        },
        "raw_return": clipped + advantage,
        "reward": 0.0,
        "seed": int(trajectory_id.split("-")[-1]),
        "trajectory_id": trajectory_id,
    }


def test_canonical_parser_rejects_duplicate_and_nonfinite_json() -> None:
    with pytest.raises(audit.AuditError, match="duplicate"):
        audit.parse_json_bytes(b'{"a":1,"a":2}', "fixture")
    with pytest.raises(audit.AuditError, match="non-finite"):
        audit.parse_json_bytes(b'{"a":NaN}', "fixture")


def test_pushed_source_identity_and_verifier_result_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = "1" * 40

    def fake_git(_root: Path, *args: str, **_kwargs: object) -> bytes:
        if args == ("rev-parse", "origin/master"):
            return ("2" * 40 + "\n").encode()
        return (head + "\n").encode()

    monkeypatch.setattr(audit, "_git", fake_git)
    with pytest.raises(audit.AuditError, match="must match"):
        audit.verify_pushed_source(tmp_path, head)

    valid = {
        "checkpoint_count": 8,
        "completed_chunk_indices": list(range(8)),
        "manifest_sha256": audit.EXPECTED_MANIFEST_SHA256,
        "terminal_sha256": audit.EXPECTED_TERMINAL_SHA256,
        "verdict": audit.EXPECTED_VERDICT,
    }
    audit.validate_verifier_result(valid)
    valid["checkpoint_count"] = 7
    with pytest.raises(audit.AuditError, match="verifier result"):
        audit.validate_verifier_result(valid)


def test_clipping_status_and_baseline_identity_fail_closed() -> None:
    low = _decision(unclipped=-0.2, advantage=0.3)
    assert audit.validate_baseline_row(low, "fixture") == "clipped_low"
    assert audit.validate_baseline_row(
        _decision(unclipped=3.4), "fixture"
    ) == "clipped_high"
    assert audit.validate_baseline_row(
        _decision(unclipped=0.2), "fixture"
    ) == "unclipped"

    changed = _decision(unclipped=-0.2)
    changed["advantage"] = 9.0
    with pytest.raises(audit.AuditError, match="advantage"):
        audit.validate_baseline_row(changed, "fixture")


def test_fold_validation_requires_disjoint_held_out_trajectory() -> None:
    rows = [_decision(trajectory_id="seed-1", fold_id="fold-1")]
    folds = {
        "fold-0": ["seed-0"],
        "fold-1": ["seed-1"],
        "fold-2": ["seed-2"],
        "fold-3": ["seed-3"],
    }
    models = {
        "fold-0": {"fit_trajectory_ids": ["seed-1", "seed-2", "seed-3"]},
        "fold-1": {"fit_trajectory_ids": ["seed-0", "seed-2", "seed-3"]},
        "fold-2": {"fit_trajectory_ids": ["seed-0", "seed-1", "seed-3"]},
        "fold-3": {"fit_trajectory_ids": ["seed-0", "seed-1", "seed-2"]},
    }
    audit.validate_fold_rows(
        rows,
        folds,
        models,
        expected_held_out=1,
        expected_fit=3,
    )
    rows[0]["baseline_fit_trajectory_ids"] = ["seed-0", "seed-1", "seed-2"]
    with pytest.raises(audit.AuditError, match="fit trajectories"):
        audit.validate_fold_rows(
            rows,
            folds,
            models,
            expected_held_out=1,
            expected_fit=3,
        )


def test_fold_validation_requires_exact_four_fold_complements() -> None:
    folds = {
        "fold-0": ["seed-0"],
        "fold-1": ["seed-1"],
        "fold-2": ["seed-2"],
        "fold-3": ["seed-3"],
    }
    models = {
        fold_id: {
            "fit_trajectory_ids": sorted(
                set().union(*folds.values()).difference(held_out)
            )
        }
        for fold_id, held_out in folds.items()
    }
    rows = [_decision(trajectory_id="seed-1", fold_id="fold-1")]
    rows[0]["baseline_fit_trajectory_ids"] = models["fold-1"][
        "fit_trajectory_ids"
    ]
    audit.validate_fold_rows(
        rows, folds, models, expected_held_out=1, expected_fit=3
    )

    models["fold-1"] = {
        "fit_trajectory_ids": ["seed-0", "seed-2", "outside"]
    }
    with pytest.raises(audit.AuditError, match="complement"):
        audit.validate_fold_rows(
            rows, folds, models, expected_held_out=1, expected_fit=3
        )


def test_direct_take_pressure_uses_cross_fitted_advantage_and_entropy() -> None:
    row = _decision(selected="take", advantage=0.25)
    result = audit.direct_take_pressure(row, total_chunk_decisions=100)
    family_entropy = row["policy_terms"]["family_entropy"]
    expected = (
        0.25 * (1.0 - 0.5)
        - 0.01 * 0.5 * (math.log(0.5) + family_entropy)
    ) / 100
    assert result["policy"] == pytest.approx(0.00125)
    assert result["family_entropy"] < 0.0
    assert result["conditional_entropy"] == pytest.approx(0.0)
    assert result["combined"] == pytest.approx(expected)


def test_scalar_components_reconcile_and_reject_drift() -> None:
    row = _decision(advantage=0.25)
    family_entropy = row["policy_terms"]["family_entropy"]
    stored = {
        "card_reward_conditional_policy": 0.0,
        "card_reward_family_policy": -0.25 * math.log(0.5),
        "conditional_entropy_regularizer": 0.0,
        "family_entropy_regularizer": -0.01 * family_entropy,
        "other_policy": 0.0,
    }
    evidence = {
        "decisions": [row],
        "gradients": {"scalar_components": stored},
    }
    assert audit._reconcile_scalar_components(evidence) == pytest.approx(stored)
    stored["other_policy"] = 1.0
    with pytest.raises(audit.AuditError, match="scalar component"):
        audit._reconcile_scalar_components(evidence)


def test_contrast_preserves_upper_clipping_separately() -> None:
    contrast = audit.Contrast()
    contrast.add("clipped_low", "take", 1.0)
    contrast.add("clipped_high", "skip", 2.0)
    contrast.add("unclipped", "take", 3.0)
    result = contrast.result()
    assert result["clipped"]["count"] == 2
    assert result["clipped"]["direct_take_pressure_sum"] == pytest.approx(3.0)
    assert result["clipped_high"]["selected_families"] == {"skip": 1}
    assert result["unclipped"]["count"] == 1


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "<17"),
        (16, "<17"),
        (17, "17..33"),
        (33, "17..33"),
        (34, ">=34"),
    ],
)
def test_effective_floor_bands_are_fixed(value: int, expected: str) -> None:
    assert audit._floor_band(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "first"), (1, "second"), (2, "later"), (20, "later")],
)
def test_card_reward_ordinal_bands_are_fixed(value: int, expected: str) -> None:
    assert audit._ordinal_band(value) == expected


def test_summary_reports_exact_clipping_rates() -> None:
    summary = audit.Summary()
    summary.add(_decision(unclipped=-0.1), clipping="clipped_low", pressure=None)
    summary.add(_decision(unclipped=0.1), clipping="unclipped", pressure=None)
    result = summary.result()
    assert result["clipping"] == {"clipped_low": 1, "unclipped": 1}
    assert result["clipping_rates"] == {
        "clipped_low": 0.5,
        "unclipped": 0.5,
    }


def test_bounded_gzip_reader_stops_after_uncompressed_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical = b"{" + b'"padding":"' + (b"a" * 128) + b'"}\n'
    stored = gzip.compress(canonical, mtime=0)
    relative = "chunk.json.gz"
    (tmp_path / relative).write_bytes(stored)
    checkpoint = {
        "chunk_evidence": {
            "path": relative,
            "stored_sha256": hashlib.sha256(stored).hexdigest(),
            "stored_size_bytes": len(stored),
            "uncompressed_sha256": hashlib.sha256(canonical).hexdigest(),
            "uncompressed_size_bytes": len(canonical),
        }
    }
    monkeypatch.setattr(audit, "MAX_GZIP_UNCOMPRESSED_BYTES", 32)
    with pytest.raises(audit.AuditError, match="canonical bound"):
        audit._read_bound_chunk(tmp_path, checkpoint)


def test_terminal_snapshot_requires_exact_inventory_and_fixed_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    terminal = {
        "identity": audit.EXPECTED_IDENTITY,
        "terminal_sha256": audit.EXPECTED_TERMINAL_SHA256,
        "verdict": audit.EXPECTED_VERDICT,
    }
    terminal_raw = audit.verifier.canonical_json_bytes(terminal)
    payload = b"immutable evidence\n"
    artifacts = [
        {
            "path": "payload.bin",
            "stored_sha256": hashlib.sha256(payload).hexdigest(),
            "stored_size_bytes": len(payload),
        },
        {
            "path": "terminal.json",
            "stored_sha256": hashlib.sha256(terminal_raw).hexdigest(),
            "stored_size_bytes": len(terminal_raw),
        },
    ]
    manifest = {
        "artifact_inventory": {"artifacts": artifacts},
        "identity": audit.EXPECTED_IDENTITY,
        "manifest_sha256": audit.EXPECTED_MANIFEST_SHA256,
        "terminal_sha256": audit.EXPECTED_TERMINAL_SHA256,
    }
    manifest_raw = audit.verifier.canonical_json_bytes(manifest)
    (tmp_path / "payload.bin").write_bytes(payload)
    (tmp_path / "terminal.json").write_bytes(terminal_raw)
    (tmp_path / "artifact_manifest.json").write_bytes(manifest_raw)
    monkeypatch.setattr(
        audit, "EXPECTED_TERMINAL_FILE_SHA256", hashlib.sha256(terminal_raw).hexdigest()
    )
    monkeypatch.setattr(
        audit, "EXPECTED_MANIFEST_FILE_SHA256", hashlib.sha256(manifest_raw).hexdigest()
    )
    audit._validate_snapshot(tmp_path)

    (tmp_path / "unexpected.bin").write_bytes(b"unexpected")
    with pytest.raises(audit.AuditError, match="inventory"):
        audit._validate_snapshot(tmp_path)


@pytest.mark.parametrize(
    ("total", "clipped", "unclipped", "take", "skip", "expected"),
    [
        (64, 16, 48, 32, 32, "supported"),
        (63, 16, 47, 31, 32, "insufficient"),
        (64, 15, 49, 32, 32, "insufficient"),
        (64, 16, 48, 49, 15, "insufficient"),
    ],
)
def test_support_thresholds_are_fixed(
    total: int,
    clipped: int,
    unclipped: int,
    take: int,
    skip: int,
    expected: str,
) -> None:
    assert audit.support_status(
        total=total,
        clipped=clipped,
        unclipped=unclipped,
        selected_take=take,
        selected_skip=skip,
        require_clipping_contrast=True,
        require_take_skip=True,
    ) == expected


@pytest.mark.parametrize(
    ("global_supported", "clip", "unclip", "window", "expected"),
    [
        (
            True,
            1.0,
            2.0,
            [0.1, 0.2, 0.3, 0.4],
            "take_pressure_persists_on_supported_unclipped_rows",
        ),
        (
            True,
            1.0,
            0.0,
            [0.1, 0.2, 0.3, 0.4],
            "take_pressure_concentrated_in_clipped_rows",
        ),
        (
            True,
            -1.0,
            2.0,
            [0.1, 0.2, -0.3, 0.4],
            "take_pressure_not_consistently_aligned",
        ),
        (
            False,
            1.0,
            2.0,
            [0.1, 0.2, 0.3, 0.4],
            "insufficient_support_or_evidence",
        ),
    ],
)
def test_verdict_precedence_is_bounded(
    global_supported: bool,
    clip: float,
    unclip: float,
    window: list[float],
    expected: str,
) -> None:
    assert audit.classify_verdict(
        global_supported=global_supported,
        clipped_pressure=clip,
        unclipped_pressure=unclip,
        final_window_unclipped_pressures=window,
        final_window_supported=[True] * 4,
    ) == expected


def test_final_window_preserves_the_single_non_take_exception() -> None:
    rows = [
        {
            "chunk_index": chunk,
            "trajectory_id": f"seed-{chunk}",
            **_decision(
                trajectory_id=f"seed-{chunk}",
                greedy="bowl" if chunk == 7 and offset == 0 else "take",
                decision_index=offset,
            ),
        }
        for chunk in range(4, 8)
        for offset in range(444 if chunk < 7 else 442)
    ]
    result = audit.summarize_final_window(rows)
    assert result["multi_family_decisions"] == 1774
    assert result["greedy_families"] == {"bowl": 1, "take": 1773}
    assert result["registered_stop"] is False
    assert len(result["non_take_exceptions"]) == 1


def test_report_publication_is_deterministic_and_all_false(tmp_path: Path) -> None:
    report = {
        "authority": audit.audit_authority(),
        "schema_version": audit.AUDIT_SCHEMA_VERSION,
        "verdict": "insufficient_support_or_evidence",
    }
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_paths = audit.publish_reports(report, first)
    second_paths = audit.publish_reports(report, second)
    assert first_paths[0].read_bytes() == second_paths[0].read_bytes()
    assert first_paths[1].read_bytes() == second_paths[1].read_bytes()
    assert all(value is False for value in report["authority"].values())


def test_inactive_lease_requires_fixed_identity_and_preserves_bytes(
    tmp_path: Path,
) -> None:
    lease = {
        "identity": audit.EXPECTED_IDENTITY,
        "owner": {
            "acquired_at_ns": 1,
            "process_id": 1,
            "token": "0" * 32,
        },
        "reclaimed_owner": None,
        "schema_version": audit.LEASE_SCHEMA_VERSION,
    }
    path = tmp_path / ".execution.lease"
    payload = audit.verifier.canonical_json_bytes(lease)
    path.write_bytes(payload)
    with audit.hold_inactive_lease(path) as observed:
        assert observed == payload
    assert path.read_bytes() == payload

    lease["identity"] = {**audit.EXPECTED_IDENTITY, "request_sha256": "0" * 64}
    path.write_bytes(audit.verifier.canonical_json_bytes(lease))
    with pytest.raises(audit.AuditError, match="identity"):
        with audit.hold_inactive_lease(path):
            pass


def test_cli_rejects_unregistered_analytical_overrides() -> None:
    parser = audit.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "--source-commit",
                "0" * 40,
                "--output-dir",
                "out",
                "--support-minimum",
                "1",
            ]
        )


def test_fresh_import_loads_no_forbidden_modules() -> None:
    code = (
        "import json,sys; "
        "from analysis_scripts import audit_cross_fitted_baseline_support as a; "
        "print(json.dumps(a.forbidden_loaded_modules()))"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", f"import sys;sys.path.insert(0,{str(REPO_ROOT)!r});{code}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == []


def test_source_digest_helper_binds_exact_bytes(tmp_path: Path) -> None:
    path = tmp_path / "source.py"
    path.write_bytes(b"source\n")
    binding = audit.file_binding(path, relative_path="source.py")
    assert binding == {
        "path": "source.py",
        "sha256": hashlib.sha256(b"source\n").hexdigest(),
        "size_bytes": 7,
    }
