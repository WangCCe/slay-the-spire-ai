from __future__ import annotations

import base64
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

import pytest

from analysis_scripts import audit_card_acceptance_conditional_choice as audit


REPO_ROOT = Path(__file__).resolve().parents[1]


def _candidates() -> list[dict[str, str]]:
    return [
        {"action_id": "take:a", "kind": "take"},
        {"action_id": "take:b", "kind": "take"},
        {"action_id": "take:c", "kind": "take"},
        {"action_id": "skip", "kind": "skip"},
        {"action_id": "bowl", "kind": "bowl"},
    ]


def _scores() -> dict[str, float]:
    return {
        "take:a": 0.4,
        "take:b": 0.2,
        "take:c": -0.1,
        "skip": 0.1,
        "bowl": -0.2,
    }


def _row(
    *,
    scores: dict[str, float] | None = None,
    selected_action_id: str = "take:b",
    advantage: float = 1.5,
) -> dict[str, object]:
    candidate_scores = dict(_scores() if scores is None else scores)
    distribution = audit.reconstruct_distribution(_candidates(), candidate_scores)
    family_by_action = {
        candidate["action_id"]: candidate["kind"] for candidate in _candidates()
    }
    selected_family = family_by_action[selected_action_id]
    conditional = distribution["conditional_probabilities"]
    family_probabilities = distribution["family_probabilities"]
    return {
        "advantage": advantage,
        "category": "card_reward",
        "diagnostic": {
            "candidate_scores": candidate_scores,
            "candidates": _candidates(),
            "conditional_probabilities": conditional,
            "family_order": distribution["family_order"],
            "family_probabilities": family_probabilities,
            "joint_probabilities": distribution["joint_probabilities"],
            "multi_family": True,
            "raw_score_max_action_ids": distribution[
                "raw_score_max_action_ids"
            ],
            "raw_score_max_family_ids": distribution[
                "raw_score_max_family_ids"
            ],
            "selected_action_id": selected_action_id,
            "selected_family": selected_family,
            "selection_mode": "family-first-then-conditional-v1",
        },
        "policy_terms": {
            "conditional_entropy": distribution[
                "expected_conditional_entropy"
            ],
            "family_entropy": distribution["family_entropy"],
            "selected_action_id": selected_action_id,
            "selected_conditional_log_probability": math.log(
                conditional[selected_action_id]
            ),
            "selected_family": selected_family,
            "selected_family_log_probability": math.log(
                family_probabilities[selected_family]
            ),
            "selected_joint_log_probability": math.log(
                distribution["joint_probabilities"][selected_action_id]
            ),
        },
    }


def _chunks() -> list[dict[str, object]]:
    return [
        {
            "acceptance_pressure_sum": 0.1 + index * 0.01,
            "chunk_index": index,
            "conditional_margin_pressure_sum": 0.05,
            "eligible_rows": 128,
            "mean_max_conditional_probability": 0.34 + index * 0.01,
            "mean_normalized_take_entropy": 0.99 - index * 0.01,
            "mean_top_two_probability_gap": 0.01 + index * 0.01,
            "selected_non_take_rows": 48,
            "selected_take_rows": 80,
            "take_tie_rows": 0,
            "unique_greedy_rows": 128,
        }
        for index in range(8)
    ]


def _vector_payload(
    values: list[float], *, dtype: str = "float64"
) -> dict[str, object]:
    formats = {"float32": "f", "float64": "d"}
    raw = struct.pack(f"<{len(values)}{formats[dtype]}", *values)
    return {
        "byte_order": "little",
        "data_base64": base64.b64encode(raw).decode("ascii"),
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "dtype": dtype,
        "shape": [len(values)],
    }


def _gradient_fixture(*, clip_factor: float = 1.0) -> dict[str, object]:
    component_values = {
        "card_reward_conditional_policy": [0.0, 0.2],
        "card_reward_family_policy": [0.1, 0.0],
        "conditional_entropy_regularizer": [0.0, 0.0],
        "family_entropy_regularizer": [0.0, 0.0],
        "other_policy": [0.05, 0.05],
    }
    full = [0.15, 0.25]
    clipped = [value * clip_factor for value in full]
    return {
        "clip_factor": clip_factor,
        "clipped_full": _vector_payload(clipped),
        "component_order": list(audit.COMPONENT_NAMES),
        "component_vectors": {
            name: _vector_payload(values)
            for name, values in component_values.items()
        },
        "consumed_torch_clipped": _vector_payload(clipped, dtype="float32"),
        "full": _vector_payload(full),
        "installed": _vector_payload(clipped, dtype="float32"),
    }


def test_canonical_parser_rejects_duplicate_and_nonfinite_json() -> None:
    with pytest.raises(audit.AuditError, match="duplicate"):
        audit.parse_json_bytes(b'{"a":1,"a":2}', "fixture")
    with pytest.raises(audit.AuditError, match="non-finite"):
        audit.parse_json_bytes(b'{"a":NaN}', "fixture")


def test_distribution_reconstructs_factorization_and_entropy() -> None:
    result = audit.reconstruct_distribution(_candidates(), _scores())

    assert result["family_order"] == ["bowl", "skip", "take"]
    assert sum(result["family_probabilities"].values()) == pytest.approx(1.0)
    assert sum(
        result["conditional_probabilities"][action]
        for action in ("take:a", "take:b", "take:c")
    ) == pytest.approx(1.0)
    for candidate in _candidates():
        action = candidate["action_id"]
        family = candidate["kind"]
        assert result["joint_probabilities"][action] == pytest.approx(
            result["family_probabilities"][family]
            * result["conditional_probabilities"][action]
        )
    assert result["raw_score_max_action_ids"] == ["take:a"]
    assert result["raw_score_max_family_ids"] == ["take"]
    assert result["family_entropy"] > 0.0
    assert result["expected_conditional_entropy"] > 0.0


def test_distribution_is_identity_stable_under_permutation() -> None:
    candidates = list(reversed(_candidates()))
    result = audit.reconstruct_distribution(candidates, _scores())
    original = audit.reconstruct_distribution(_candidates(), _scores())

    assert result["family_order"] == original["family_order"]
    assert result["family_probabilities"] == pytest.approx(
        original["family_probabilities"]
    )
    assert result["conditional_probabilities"] == pytest.approx(
        original["conditional_probabilities"]
    )


@pytest.mark.parametrize(
    "candidates,scores,match",
    [
        (_candidates() + [_candidates()[0]], _scores(), "duplicate"),
        (_candidates(), {**_scores(), "extra": 1.0}, "coverage"),
        (_candidates(), {**_scores(), "take:a": math.inf}, "finite"),
        ([{"action_id": "", "kind": "take"}], {"": 0.0}, "identity"),
    ],
)
def test_distribution_rejects_malformed_inputs(
    candidates: list[dict[str, str]],
    scores: dict[str, float],
    match: str,
) -> None:
    with pytest.raises(audit.AuditError, match=match):
        audit.reconstruct_distribution(candidates, scores)


def test_uniform_take_translation_changes_acceptance_only() -> None:
    original = audit.reconstruct_distribution(_candidates(), _scores())
    translated_scores = {
        action: score + (0.75 if action.startswith("take:") else 0.0)
        for action, score in _scores().items()
    }
    translated = audit.reconstruct_distribution(_candidates(), translated_scores)

    for action in ("take:a", "take:b", "take:c"):
        assert translated["conditional_probabilities"][action] == pytest.approx(
            original["conditional_probabilities"][action]
        )
    assert translated["conditional_entropies"]["take"] == pytest.approx(
        original["conditional_entropies"]["take"]
    )
    assert translated["family_probabilities"]["take"] > original[
        "family_probabilities"
    ]["take"]


def test_nonmax_redistribution_changes_conditional_at_fixed_family_mass() -> None:
    original = audit.reconstruct_distribution(_candidates(), _scores())
    redistributed_scores = {**_scores(), "take:b": 0.35, "take:c": -0.25}
    redistributed = audit.reconstruct_distribution(
        _candidates(), redistributed_scores
    )

    assert redistributed["family_scores"] == original["family_scores"]
    assert redistributed["family_probabilities"] == pytest.approx(
        original["family_probabilities"]
    )
    assert redistributed["conditional_probabilities"]["take:b"] != pytest.approx(
        original["conditional_probabilities"]["take:b"]
    )


def test_max_take_perturbation_couples_coordinates() -> None:
    original = audit.reconstruct_distribution(_candidates(), _scores())
    perturbed = audit.reconstruct_distribution(
        _candidates(), {**_scores(), "take:a": 0.8}
    )

    assert perturbed["family_probabilities"]["take"] != pytest.approx(
        original["family_probabilities"]["take"]
    )
    assert perturbed["conditional_probabilities"]["take:a"] != pytest.approx(
        original["conditional_probabilities"]["take:a"]
    )


def test_acceptance_pressure_reconstructs_named_components() -> None:
    row = _row()
    result = audit.direct_acceptance_pressure(row, total_chunk_decisions=10)
    diagnostic = row["diagnostic"]
    terms = row["policy_terms"]
    p_take = diagnostic["family_probabilities"]["take"]
    h_take = audit.reconstruct_distribution(_candidates(), _scores())[
        "conditional_entropies"
    ]["take"]
    expected_policy = 1.5 * (1.0 - p_take) / 10
    expected_family_entropy = (
        -0.01 * p_take * (math.log(p_take) + terms["family_entropy"]) / 10
    )
    expected_conditional_entropy = (
        0.01
        * p_take
        * (h_take - terms["conditional_entropy"])
        / 10
    )

    assert result["policy"] == pytest.approx(expected_policy)
    assert result["family_entropy"] == pytest.approx(expected_family_entropy)
    assert result["conditional_entropy"] == pytest.approx(
        expected_conditional_entropy
    )
    assert result["combined"] == pytest.approx(
        expected_policy + expected_family_entropy + expected_conditional_entropy
    )


def test_conditional_pressure_reconstructs_zero_sum_and_greedy_margin() -> None:
    row = _row(selected_action_id="take:b")
    result = audit.direct_conditional_pressure(row, total_chunk_decisions=10)
    pressures = result["candidate_pressures"]

    assert sum(value["policy"] for value in pressures.values()) == pytest.approx(0.0)
    assert sum(
        value["conditional_entropy"] for value in pressures.values()
    ) == pytest.approx(0.0)
    assert result["greedy_action_ids"] == ["take:a"]
    expected_margin = pressures["take:a"]["combined"] - sum(
        pressures[action]["combined"] for action in ("take:b", "take:c")
    ) / 2
    assert result["greedy_margin_pressure"] == pytest.approx(expected_margin)
    assert 0.0 <= result["normalized_take_entropy"] <= 1.0
    assert result["max_conditional_probability"] > 1.0 / 3.0
    assert result["top_two_probability_gap"] > 0.0


def test_non_take_selection_has_only_take_entropy_pressure() -> None:
    result = audit.direct_conditional_pressure(
        _row(selected_action_id="skip"), total_chunk_decisions=10
    )
    assert all(
        value["policy"] == 0.0
        for value in result["candidate_pressures"].values()
    )


def test_tied_greedy_take_preserves_row_without_margin() -> None:
    tied_scores = {**_scores(), "take:b": _scores()["take:a"]}
    result = audit.direct_conditional_pressure(
        _row(scores=tied_scores), total_chunk_decisions=10
    )
    assert result["greedy_action_ids"] == ["take:a", "take:b"]
    assert result["greedy_margin_pressure"] is None


def test_row_reconciliation_rejects_retained_probability_drift() -> None:
    row = _row()
    row["diagnostic"]["family_probabilities"]["take"] += 0.01
    with pytest.raises(audit.AuditError, match="family probabilities"):
        audit.direct_acceptance_pressure(row, total_chunk_decisions=10)


def test_verdict_all_consistent() -> None:
    verdict, inputs = audit.classify_verdict(_chunks())
    assert verdict == "acceptance_and_conditional_pressure_consistently_aligned"
    assert inputs == {
        "acceptance_pressure_consistent": True,
        "conditional_concentration_progresses": True,
        "conditional_pressure_consistent": True,
        "support": "supported",
    }


def test_verdict_mixed_conditional_pressure() -> None:
    chunks = _chunks()
    chunks[6]["conditional_margin_pressure_sum"] = 0.0
    verdict, inputs = audit.classify_verdict(chunks)
    assert verdict == (
        "acceptance_pressure_with_conditional_concentration_but_"
        "mixed_direct_pressure"
    )
    assert inputs["conditional_pressure_consistent"] is False


def test_verdict_without_monotonic_concentration() -> None:
    chunks = _chunks()
    chunks[3]["mean_normalized_take_entropy"] = chunks[2][
        "mean_normalized_take_entropy"
    ]
    verdict, inputs = audit.classify_verdict(chunks)
    assert verdict == (
        "acceptance_pressure_without_monotonic_conditional_concentration"
    )
    assert inputs["conditional_concentration_progresses"] is False


def test_verdict_acceptance_not_consistent() -> None:
    chunks = _chunks()
    chunks[2]["acceptance_pressure_sum"] = -0.01
    verdict, _ = audit.classify_verdict(chunks)
    assert verdict == "acceptance_pressure_not_consistent"


@pytest.mark.parametrize(
    "field,value",
    [
        ("eligible_rows", 63),
        ("unique_greedy_rows", 63),
        ("selected_take_rows", 15),
        ("selected_non_take_rows", 15),
    ],
)
def test_verdict_insufficient_support(field: str, value: int) -> None:
    chunks = _chunks()
    chunks[0][field] = value
    verdict, inputs = audit.classify_verdict(chunks)
    assert verdict == "insufficient_support_or_evidence"
    assert inputs["support"] == "insufficient"


def test_verdict_rejects_chunk_identity_or_nonfinite_arithmetic() -> None:
    chunks = _chunks()
    chunks[7]["chunk_index"] = 8
    with pytest.raises(audit.AuditError, match="chunk indices"):
        audit.classify_verdict(chunks)

    chunks = _chunks()
    chunks[0]["acceptance_pressure_sum"] = math.nan
    with pytest.raises(audit.AuditError, match="finite"):
        audit.classify_verdict(chunks)


def test_float64_vector_decode_and_geometry() -> None:
    first = audit.decode_float64_vector(_vector_payload([3.0, 4.0]), "first")
    second = audit.decode_float64_vector(_vector_payload([0.0, 5.0]), "second")
    geometry = audit.vector_geometry(first, second)

    assert first == (3.0, 4.0)
    assert geometry["left_norm"] == pytest.approx(5.0)
    assert geometry["right_norm"] == pytest.approx(5.0)
    assert geometry["dot"] == pytest.approx(20.0)
    assert geometry["cosine"] == pytest.approx(0.8)


@pytest.mark.parametrize("field,value,match", [
    ("dtype", "float32", "dtype"),
    ("byte_order", "big", "byte order"),
    ("shape", [3], "shape"),
    ("data_sha256", "0" * 64, "digest"),
])
def test_float64_vector_rejects_malformed_payload(
    field: str, value: object, match: str
) -> None:
    payload = _vector_payload([1.0, 2.0])
    payload[field] = value
    with pytest.raises(audit.AuditError, match=match):
        audit.decode_float64_vector(payload, "vector")


def test_component_vectors_reconstruct_full_and_report_geometry() -> None:
    result = audit.reconcile_gradient_vectors(_gradient_fixture())

    assert result["reconstruction_max_abs"] <= audit.VECTOR_ATOL
    assert result["uniform_clip_max_abs"] == 0.0
    assert result["installed_matches_consumed"] is True
    assert result["family_conditional"]["dot"] == 0.0
    assert "vectors" not in result


def test_component_vector_reconstruction_rejects_mismatch() -> None:
    gradients = _gradient_fixture()
    gradients["component_vectors"] = {
        name: _vector_payload([0.0, 0.0]) for name in audit.COMPONENT_NAMES
    }
    with pytest.raises(audit.AuditError, match="reconstruct"):
        audit.reconcile_gradient_vectors(gradients)


@pytest.mark.parametrize(
    "field,dtype,values,match",
    [
        ("clipped_full", "float64", [0.15, 0.24], "uniform clipping"),
        ("installed", "float32", [0.15, 0.24], "installed gradient"),
        (
            "consumed_torch_clipped",
            "float32",
            [0.15, 0.24],
            "consumed gradient",
        ),
    ],
)
def test_uniform_gradient_clipping_rejects_drift(
    field: str, dtype: str, values: list[float], match: str
) -> None:
    gradients = _gradient_fixture()
    gradients[field] = _vector_payload(values, dtype=dtype)
    with pytest.raises(audit.AuditError, match=match):
        audit.reconcile_gradient_vectors(gradients)


def test_scalar_components_reconstruct_and_reject_drift() -> None:
    row = _row()
    expected = {
        "card_reward_conditional_policy": -1.5
        * row["policy_terms"]["selected_conditional_log_probability"],
        "card_reward_family_policy": -1.5
        * row["policy_terms"]["selected_family_log_probability"],
        "conditional_entropy_regularizer": -0.01
        * row["policy_terms"]["conditional_entropy"],
        "family_entropy_regularizer": -0.01
        * row["policy_terms"]["family_entropy"],
        "other_policy": 0.0,
    }
    expected_full = math.fsum(expected.values())
    assert audit.reconcile_scalar_components(
        [row], expected, expected_full
    ) == pytest.approx(expected)

    changed = dict(expected)
    changed["card_reward_family_policy"] += 0.01
    with pytest.raises(audit.AuditError, match="scalar component"):
        audit.reconcile_scalar_components([row], changed, expected_full)

    with pytest.raises(audit.AuditError, match="scalar full loss"):
        audit.reconcile_scalar_components([row], expected, expected_full + 0.01)


def test_fixed_window_summary_reports_actual_early_and_final_values() -> None:
    chunks = _chunks()
    summary = audit.summarize_windows(chunks)

    assert summary["early"]["chunk_indices"] == [0, 1, 2, 3]
    assert summary["final"]["chunk_indices"] == [4, 5, 6, 7]
    assert summary["early"]["eligible_rows"] == 512
    assert summary["final"]["acceptance_pressure_sum"] == pytest.approx(
        sum(row["acceptance_pressure_sum"] for row in chunks[4:8])
    )
    assert summary["early"]["mean_normalized_take_entropy"] == pytest.approx(
        sum(row["mean_normalized_take_entropy"] for row in chunks[:4]) / 4
    )


def test_pushed_source_binds_every_reused_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = "1" * 40
    payloads: dict[str, bytes] = {}
    for relative in audit.SOURCE_BINDING_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = f"source:{relative}\n".encode("ascii")
        path.write_bytes(raw)
        payloads[relative] = raw

    def fake_git(_root: Path, *args: str, **_kwargs: object) -> bytes:
        if args in (("rev-parse", "HEAD"), ("rev-parse", "origin/master")):
            return (head + "\n").encode("ascii")
        if args[:2] == ("status", "--porcelain"):
            return b""
        if args[0] == "show":
            _, relative = args[1].split(":", 1)
            return payloads[relative]
        raise AssertionError(args)

    monkeypatch.setattr(audit, "_git", fake_git)
    result = audit.verify_pushed_source(tmp_path, head)
    assert result["commit"] == head
    assert set(result["bindings"]) == set(audit.SOURCE_BINDING_PATHS)

    def dirty_git(_root: Path, *args: str, **_kwargs: object) -> bytes:
        if args[:2] == ("status", "--porcelain"):
            return b" M changed.py\n"
        return fake_git(_root, *args, **_kwargs)

    monkeypatch.setattr(audit, "_git", dirty_git)
    with pytest.raises(audit.AuditError, match="worktree"):
        audit.verify_pushed_source(tmp_path, head)


def test_prior_audit_binding_accepts_exact_tracked_bytes_and_rejects_drift() -> None:
    path = REPO_ROOT / audit.DEFAULT_PRIOR_JSON_PATH
    raw = path.read_bytes()
    result = audit.validate_prior_audit_bytes(raw)
    assert result["verdict"] == audit.EXPECTED_PRIOR_VERDICT

    changed = raw.replace(
        audit.EXPECTED_PRIOR_VERDICT.encode("ascii"), b"changed-verdict"
    )
    with pytest.raises(audit.AuditError, match="prior audit.*binding"):
        audit.validate_prior_audit_bytes(changed)


def test_authority_and_scope_remain_all_false() -> None:
    assert audit.audit_authority()
    assert set(audit.audit_authority().values()) == {False}
    assert {"causal", "causal_claim", "policy_quality"} <= set(
        audit.audit_authority()
    )
    assert audit.audit_scope() == {
        "artifact_mutation": False,
        "environment_construction": False,
        "evaluation": False,
        "model_loading": False,
        "native_loading": False,
        "new_seed_access": False,
        "source_only": True,
        "training_or_replay": False,
    }


def test_render_and_publication_are_deterministic_and_bounded(tmp_path: Path) -> None:
    report = {
        "authority": audit.audit_authority(),
        "evidence": {
            "chunk_results": _chunks(),
            "execution_counts": {
                "card_reward_rows": 3536,
                "chunks": 8,
                "decisions": 11729,
                "trajectories": 512,
            },
            "verdict_inputs": audit.classify_verdict(_chunks())[1],
        },
        "identity": {"logical_execution_id": audit.LOGICAL_EXECUTION_ID},
        "limitations": list(audit.LIMITATIONS),
        "schema_version": audit.AUDIT_SCHEMA_VERSION,
        "scope": audit.audit_scope(),
        "source": {"commit": "a" * 40},
        "verdict": audit.classify_verdict(_chunks())[0],
    }
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_result = audit.publish_reports(report, first)
    second_result = audit.publish_reports(report, second)

    assert (first / audit.DEFAULT_JSON_NAME).read_bytes() == (
        second / audit.DEFAULT_JSON_NAME
    ).read_bytes()
    assert (first / audit.DEFAULT_MARKDOWN_NAME).read_bytes() == (
        second / audit.DEFAULT_MARKDOWN_NAME
    ).read_bytes()
    assert first_result == second_result
    assert first_result["json"]["size_bytes"] <= audit.MAX_REPORT_BYTES
    assert first_result["markdown"]["size_bytes"] <= audit.MAX_REPORT_BYTES


def test_publication_is_deterministic_across_isolated_processes(
    tmp_path: Path,
) -> None:
    report = {
        "authority": audit.audit_authority(),
        "evidence": {
            "chunk_results": _chunks(),
            "execution_counts": {
                "card_reward_rows": 3536,
                "chunks": 8,
                "decisions": 11729,
                "trajectories": 512,
            },
            "verdict_inputs": audit.classify_verdict(_chunks())[1],
        },
        "identity": {"logical_execution_id": audit.LOGICAL_EXECUTION_ID},
        "limitations": list(audit.LIMITATIONS),
        "schema_version": audit.AUDIT_SCHEMA_VERSION,
        "scope": audit.audit_scope(),
        "source": {"commit": "a" * 40},
        "verdict": audit.classify_verdict(_chunks())[0],
    }
    report_path = tmp_path / "report.json"
    report_path.write_bytes(audit.canonical_json_bytes(report))
    code = """
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()))
from analysis_scripts import audit_card_acceptance_conditional_choice as audit
report = audit.parse_json_bytes(pathlib.Path(sys.argv[1]).read_bytes(), 'report')
audit.publish_reports(report, pathlib.Path(sys.argv[2]))
assert not audit.forbidden_loaded_modules()
"""
    outputs = [tmp_path / "isolated-first", tmp_path / "isolated-second"]
    for output in outputs:
        result = subprocess.run(
            [sys.executable, "-I", "-c", code, str(report_path), str(output)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
    for name in (audit.DEFAULT_JSON_NAME, audit.DEFAULT_MARKDOWN_NAME):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()


def test_publication_refuses_existing_or_consumed_output(tmp_path: Path) -> None:
    report = {"verdict": "insufficient_support_or_evidence"}
    output = tmp_path / "output"
    audit.publish_reports(report, output)
    with pytest.raises(audit.AuditError, match="already exists"):
        audit.publish_reports(report, output)

    consumed = tmp_path / "consumed"
    consumed.mkdir()
    with pytest.raises(audit.AuditError, match="consumed"):
        audit.publish_reports(report, consumed / "child", consumed_root=consumed)


def test_existing_module_imports_do_not_load_audit() -> None:
    code = """
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()))
for name in (
    'analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime',
    'analysis_scripts.noncombat_state_conditioned_ranker',
    'spirecomm.ai.agent',
):
    __import__(name)
assert 'analysis_scripts.audit_card_acceptance_conditional_choice' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_audit_import_remains_source_only() -> None:
    code = """
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()))
from analysis_scripts import audit_card_acceptance_conditional_choice as audit
assert not audit.forbidden_loaded_modules(), audit.forbidden_loaded_modules()
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_cli_publishes_mocked_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = {
        "authority": audit.audit_authority(),
        "evidence": {
            "chunk_results": _chunks(),
            "execution_counts": {"card_reward_rows": 3536},
            "verdict_inputs": audit.classify_verdict(_chunks())[1],
        },
        "identity": {"logical_execution_id": audit.LOGICAL_EXECUTION_ID},
        "limitations": list(audit.LIMITATIONS),
        "schema_version": audit.AUDIT_SCHEMA_VERSION,
        "scope": audit.audit_scope(),
        "source": {"commit": "a" * 40},
        "verdict": audit.classify_verdict(_chunks())[0],
    }
    monkeypatch.setattr(audit, "build_repository_audit", lambda *_args, **_kwargs: report)
    output = tmp_path / "cli"
    assert audit.main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--source-commit",
            "a" * 40,
            "--output-dir",
            str(output),
        ]
    ) == 0
    assert (output / audit.DEFAULT_JSON_NAME).is_file()
    assert (output / audit.DEFAULT_MARKDOWN_NAME).is_file()


def test_cli_failure_leaves_no_partial_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise audit.AuditError("blocked")

    monkeypatch.setattr(audit, "build_repository_audit", fail)
    output = tmp_path / "failed"
    assert audit.main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--source-commit",
            "a" * 40,
            "--output-dir",
            str(output),
        ]
    ) == 2
    assert not output.exists()
