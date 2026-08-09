from __future__ import annotations

import base64
from collections.abc import Mapping
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

import pytest

from analysis_scripts import audit_card_acceptance_objective_interventions as audit


REPO_ROOT = Path(__file__).resolve().parents[1]


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


def _gradient_fixture(
    *,
    family: list[float] | None = None,
    conditional: list[float] | None = None,
    clip_factor: float = 1.0,
) -> dict[str, object]:
    component_values = {
        "card_reward_family_policy": family or [1.0, -1.0],
        "card_reward_conditional_policy": conditional or [-1.0, 0.0],
        "other_policy": [0.25, 0.5],
        "family_entropy_regularizer": [0.0, 0.25],
        "conditional_entropy_regularizer": [0.0, 0.25],
    }
    full = [
        math.fsum(component[index] for component in component_values.values())
        for index in range(2)
    ]
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


def _component_fixture(
    *,
    family: tuple[float, ...] = (1.0, -1.0),
    conditional: tuple[float, ...] = (-1.0, 0.0),
) -> tuple[dict[str, tuple[float, ...]], tuple[float, ...]]:
    components = {
        "card_reward_family_policy": family,
        "card_reward_conditional_policy": conditional,
        "other_policy": (0.25, 0.5),
        "family_entropy_regularizer": (0.0, 0.25),
        "conditional_entropy_regularizer": (0.0, 0.25),
    }
    full = tuple(
        math.fsum(component[index] for component in components.values())
        for index in range(2)
    )
    return components, full


def _chunk(
    index: int, *, conflict: bool = False, conditional_supported: bool = True
) -> dict[str, object]:
    return {
        "chunk_index": index,
        "conditional_supported": conditional_supported,
        "family_conditional_dot": -0.25 if conflict else 0.25,
        "guard_invariants": {
            "conflict_projected_to_zero": True,
            "non_conflict_unchanged": True,
        },
    }


def _geometry() -> dict[str, float | None]:
    return {"cosine": 0.0, "dot": 0.0, "left_norm": 0.0, "right_norm": 0.0}


def _recorded_reconstruction() -> dict[str, object]:
    pairwise = {
        f"{left}__{right}": _geometry()
        for left_index, left in enumerate(audit.COMPONENT_NAMES)
        for right in audit.COMPONENT_NAMES[left_index + 1 :]
    }
    return {
        "clip_factor": 1.0,
        "component_norms": {name: 0.0 for name in audit.COMPONENT_NAMES},
        "family_conditional": _geometry(),
        "clipped_full_norm": 0.0,
        "full_norm": 0.0,
        "installed_matches_consumed": True,
        "pairwise": pairwise,
        "reconstruction_max_abs": 0.0,
        "to_full": {name: _geometry() for name in audit.COMPONENT_NAMES},
        "uniform_clip_max_abs": 0.0,
    }


def _report_chunk(index: int, *, conflict: bool) -> dict[str, object]:
    if conflict:
        components, full = _component_fixture()
    else:
        components, full = _component_fixture(
            family=(1.0, 0.0), conditional=(1.0, 1.0)
        )
    result = audit.analyze_gradient_components(components, full)
    result.pop("guarded_family")
    return {
        "chunk_index": index,
        "recorded_reconstruction": _recorded_reconstruction(),
        **result,
    }


def _report() -> dict[str, object]:
    chunks = [
        _report_chunk(index, conflict=index in {1, 4}) for index in range(8)
    ]
    verdict, inputs = audit.classify_verdict(chunks)
    return {
        "authority": audit.audit_authority(),
        "evidence": {
            "chunk_results": chunks,
            "execution_counts": {
                "card_reward_rows": 3536,
                "chunks": 8,
                "decisions": 11729,
                "take_candidate_multiplicity": {"3": 3522, "4": 14},
                "trajectories": 512,
            },
            "synthetic_contracts": audit.synthetic_contracts(),
            "verdict": verdict,
            "verdict_inputs": inputs,
            "windows": audit.summarize_windows(chunks),
        },
        "identity": audit.EXPECTED_IDENTITY,
        "input_bindings": {
            "prior_json": {
                "path": audit.DEFAULT_PRIOR_JSON_PATH,
                "sha256": audit.EXPECTED_PRIOR_JSON_SHA256,
                "size_bytes": 1,
                "verdict": audit.EXPECTED_PRIOR_VERDICT,
            },
            "prior_markdown": {
                "path": audit.DEFAULT_PRIOR_MARKDOWN_PATH,
                "sha256": audit.EXPECTED_PRIOR_MARKDOWN_SHA256,
                "size_bytes": 1,
            },
            "terminal_manifest": {
                "manifest_sha256": audit.EXPECTED_MANIFEST_SHA256,
                "terminal_sha256": audit.EXPECTED_TERMINAL_SHA256,
            },
        },
        "limitations": list(audit.LIMITATIONS),
        "schema_version": audit.AUDIT_SCHEMA_VERSION,
        "scope": audit.audit_scope(),
        "source": {
            "bindings": {
                relative: {"sha256": "0" * 64, "size_bytes": 1}
                for relative in audit.SOURCE_BINDING_PATHS
            },
            "commit": "a" * 40,
            "origin_master": "a" * 40,
        },
        "terminal_verification": {
            "checkpoint_count": 8,
            "completed_chunk_indices": list(range(8)),
            "manifest_sha256": audit.EXPECTED_MANIFEST_SHA256,
            "terminal_sha256": audit.EXPECTED_TERMINAL_SHA256,
            "verdict": audit.EXPECTED_TERMINAL_VERDICT,
        },
        "verdict": verdict,
    }


def test_prior_audit_trust_root_accepts_exact_bytes_and_rejects_drift() -> None:
    json_raw = (REPO_ROOT / audit.DEFAULT_PRIOR_JSON_PATH).read_bytes()
    markdown_raw = (REPO_ROOT / audit.DEFAULT_PRIOR_MARKDOWN_PATH).read_bytes()
    result = audit.validate_prior_audit_bytes(json_raw, markdown_raw)

    assert result["verdict"] == audit.EXPECTED_PRIOR_VERDICT
    with pytest.raises(audit.AuditError, match="JSON binding"):
        audit.validate_prior_audit_bytes(json_raw + b" ", markdown_raw)
    with pytest.raises(audit.AuditError, match="Markdown binding"):
        audit.validate_prior_audit_bytes(json_raw, markdown_raw + b" ")


def test_pushed_source_binds_every_reused_helper(
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
    assert set(result["bindings"]) == set(audit.SOURCE_BINDING_PATHS)


def test_repository_build_holds_inactive_lease_during_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = False
    prior_module = audit._load_prior()
    verification = {
        "checkpoint_count": 8,
        "completed_chunk_indices": list(range(8)),
        "manifest_sha256": audit.EXPECTED_MANIFEST_SHA256,
        "terminal_sha256": audit.EXPECTED_TERMINAL_SHA256,
        "verdict": audit.EXPECTED_TERMINAL_VERDICT,
    }

    @contextmanager
    def held(_path: Path):
        nonlocal active
        active = True
        try:
            yield audit.EXPECTED_IDENTITY
        finally:
            active = False

    def analyze(
        _root: Path, _prior_report: Mapping[str, object] | None = None
    ) -> dict[str, object]:
        assert active
        chunks = [_chunk(index, conflict=index in {1, 4}) for index in range(8)]
        verdict, inputs = audit.classify_verdict(chunks)
        return {
            "chunk_results": chunks,
            "execution_counts": {
                "card_reward_rows": 3536,
                "chunks": 8,
                "decisions": 11729,
                "trajectories": 512,
            },
            "synthetic_contracts": audit.synthetic_contracts(),
            "verdict": verdict,
            "verdict_inputs": inputs,
            "windows": audit.summarize_windows(chunks),
        }

    def verify(
        output: Path, *, root: Path, lease_identity: Mapping[str, str]
    ) -> dict[str, object]:
        assert active
        assert output == (REPO_ROOT / audit.DEFAULT_TERMINAL_ROOT).resolve()
        assert root == REPO_ROOT.resolve()
        assert lease_identity == audit.EXPECTED_IDENTITY
        return verification

    def reject_outer_verifier(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("outer verifier must not reacquire the held lease")

    monkeypatch.setattr(
        prior_module.baseline.verifier,
        "_verify_terminal_bundle_contents",
        verify,
    )
    monkeypatch.setattr(
        prior_module.baseline.verifier,
        "verify_terminal_bundle",
        reject_outer_verifier,
    )
    monkeypatch.setattr(
        prior_module.baseline, "validate_verifier_result", lambda *_: None
    )
    monkeypatch.setattr(
        prior_module.baseline.verifier,
        "_hold_inactive_execution_lease",
        held,
    )
    monkeypatch.setattr(prior_module.baseline, "_validate_snapshot", lambda *_: None)
    monkeypatch.setattr(audit, "forbidden_loaded_modules", lambda: [])
    monkeypatch.setattr(
        audit,
        "verify_pushed_source",
        lambda *_args, **_kwargs: {"bindings": {}, "commit": "a" * 40},
    )
    monkeypatch.setattr(audit, "_analyze_bound_chunks", analyze)

    result = audit.build_repository_audit(REPO_ROOT, source_commit="a" * 40)
    assert result["verdict"] == "bounded_conditional_conflict_guard_feasible"
    assert active is False


@pytest.mark.parametrize(
    "message",
    [
        "execution lease owner is still alive",
        "execution lease owner liveness is ambiguous",
    ],
)
def test_repository_build_rejects_noninactive_execution_lease(
    monkeypatch: pytest.MonkeyPatch, message: str
) -> None:
    prior_module = audit._load_prior()

    @contextmanager
    def rejected(_path: Path):
        raise prior_module.baseline.verifier.VerifierError(message)
        yield audit.EXPECTED_IDENTITY

    monkeypatch.setattr(
        prior_module.baseline.verifier,
        "_hold_inactive_execution_lease",
        rejected,
    )
    monkeypatch.setattr(
        audit,
        "verify_pushed_source",
        lambda *_args, **_kwargs: {"bindings": {}, "commit": "a" * 40},
    )

    with pytest.raises(audit.AuditError, match=message):
        audit.build_repository_audit(REPO_ROOT, source_commit="a" * 40)


def test_recorded_gradient_decode_reconstructs_and_clips() -> None:
    result = audit.decode_recorded_gradients(_gradient_fixture())
    assert result["reconciliation"]["reconstruction_max_abs"] == 0.0
    assert result["components"]["card_reward_family_policy"] == (1.0, -1.0)
    assert result["full"] == (0.25, 0.0)


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("component_order", "component order"),
        ("component_digest", "digest"),
        ("full", "reconstruct"),
        ("clip", "clipping"),
    ],
)
def test_recorded_gradient_decode_rejects_malformed_evidence(
    mutation: str, match: str
) -> None:
    payload = _gradient_fixture()
    if mutation == "component_order":
        payload["component_order"] = []
    elif mutation == "component_digest":
        payload["component_vectors"]["card_reward_family_policy"][
            "data_sha256"
        ] = "0" * 64
    elif mutation == "full":
        payload["full"] = _vector_payload([9.0, 9.0])
    else:
        payload["clipped_full"] = _vector_payload([9.0, 9.0])
    with pytest.raises(audit.AuditError, match=match):
        audit.decode_recorded_gradients(payload)


def test_conflict_guard_removes_only_opposing_family_component() -> None:
    components, full = _component_fixture()
    result = audit.analyze_gradient_components(components, full)

    assert result["conditional_supported"] is True
    assert result["family_conditional_dot"] == pytest.approx(-1.0)
    assert result["projection_applied"] is True
    assert result["projection_multiplier"] == pytest.approx(-1.0)
    assert result["guarded_family_conditional_dot"] == pytest.approx(0.0)
    assert result["guard_invariants"]["conflict_projected_to_zero"] is True


def test_non_conflicting_guard_is_byte_identical() -> None:
    components, full = _component_fixture(
        family=(1.0, 0.0), conditional=(1.0, 1.0)
    )
    result = audit.analyze_gradient_components(components, full)
    assert result["projection_applied"] is False
    assert result["guarded_family"] == components["card_reward_family_policy"]
    assert result["guard_invariants"]["non_conflict_unchanged"] is True


def test_family_policy_ablation_removes_exact_family_vector() -> None:
    components, full = _component_fixture()
    result = audit.analyze_gradient_components(components, full)
    ablated = result["interventions"]["family_policy_ablated"]
    assert ablated["displacement_from_recorded"] == pytest.approx(math.sqrt(2.0))
    assert ablated["retained_family_policy_norm"] == 0.0


def test_counterfactual_clipping_uses_frozen_norm_rule() -> None:
    components, full = _component_fixture(
        family=(2.0, 0.0), conditional=(1.0, 0.0)
    )
    result = audit.analyze_gradient_components(components, full)
    for candidate in result["interventions"].values():
        raw_norm = candidate["raw_norm"]
        expected_factor = (
            1.0
            if raw_norm <= audit.GRADIENT_NORM_CEILING
            else audit.GRADIENT_NORM_CEILING
            / (raw_norm + audit.GRADIENT_CLIP_EPSILON)
        )
        assert candidate["clip_factor"] == pytest.approx(expected_factor)
        assert candidate["clipped_norm"] == pytest.approx(
            raw_norm * expected_factor
        )

    small_components, small_full = _component_fixture()
    small = audit.analyze_gradient_components(small_components, small_full)
    assert small["interventions"]["recorded"]["raw_norm"] <= 1.0
    assert small["interventions"]["recorded"]["clip_factor"] == 1.0
    assert small["interventions"]["recorded"]["clipped_norm"] == small[
        "interventions"
    ]["recorded"]["raw_norm"]


def test_zero_conditional_norm_is_unsupported_without_projection() -> None:
    components, full = _component_fixture(conditional=(0.0, 0.0))
    result = audit.analyze_gradient_components(components, full)
    assert result["conditional_supported"] is False
    assert result["projection_applied"] is False
    assert result["guarded_family"] == components["card_reward_family_policy"]


def test_fixed_verdicts_and_chunk_identity() -> None:
    no_conflict = [_chunk(index) for index in range(8)]
    assert audit.classify_verdict(no_conflict)[0] == (
        "no_recorded_family_conditional_conflict"
    )

    conflict = [_chunk(index, conflict=index == 3) for index in range(8)]
    assert audit.classify_verdict(conflict)[0] == (
        "bounded_conditional_conflict_guard_feasible"
    )

    unsupported = [_chunk(index) for index in range(8)]
    unsupported[5]["conditional_supported"] = False
    assert audit.classify_verdict(unsupported)[0] == (
        "insufficient_conditional_gradient_support"
    )

    conflict[7]["chunk_index"] = 9
    with pytest.raises(audit.AuditError, match="chunk indices"):
        audit.classify_verdict(conflict)


def _independent_logits() -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    return (
        {"skip": -0.3, "take": 0.2},
        {"skip": {"skip": 0.0}, "take": {"a": 0.5, "b": 0.1, "c": -0.2}},
    )


def test_independent_acceptance_translation_preserves_conditionals() -> None:
    family, conditional = _independent_logits()
    original = audit.independent_distribution(family, conditional)
    changed = audit.independent_distribution(
        {**family, "take": family["take"] + 0.75}, conditional
    )
    assert changed["family_probabilities"]["take"] != pytest.approx(
        original["family_probabilities"]["take"]
    )
    assert changed["conditional_probabilities"] == original[
        "conditional_probabilities"
    ]
    assert changed["conditional_order"] == original["conditional_order"]
    assert changed["conditional_entropies"] == original[
        "conditional_entropies"
    ]
    assert changed["conditional_top_two_margin"] == original[
        "conditional_top_two_margin"
    ]


def test_independent_conditional_perturbation_preserves_family_mass() -> None:
    family, conditional = _independent_logits()
    original = audit.independent_distribution(family, conditional)
    changed_logits = {
        **conditional,
        "take": {"a": 0.7, "b": 0.0, "c": -0.3},
    }
    assert math.fsum(
        changed_logits["take"][name] - conditional["take"][name]
        for name in conditional["take"]
    ) == pytest.approx(0.0)
    changed = audit.independent_distribution(family, changed_logits)
    assert changed["family_probabilities"] == pytest.approx(
        original["family_probabilities"]
    )
    assert changed["conditional_probabilities"]["take"] != pytest.approx(
        original["conditional_probabilities"]["take"]
    )


def test_one_family_fallback_has_inactive_acceptance() -> None:
    conditional = {"take": {"a": 0.2, "b": -0.1}}
    original = audit.independent_distribution({"take": 0.0}, conditional)
    changed = audit.independent_distribution({"take": 10.0}, conditional)
    assert original["family_probabilities"] == {"take": 1.0}
    assert changed == original


def test_max_pooled_control_couples_and_preserves_ties() -> None:
    candidates = [
        {"action_id": "a", "kind": "take"},
        {"action_id": "b", "kind": "take"},
        {"action_id": "skip", "kind": "skip"},
    ]
    original = audit.max_pooled_distribution(
        candidates, {"a": 0.5, "b": 0.1, "skip": 0.2}
    )
    changed = audit.max_pooled_distribution(
        candidates, {"a": 0.8, "b": 0.1, "skip": 0.2}
    )
    assert changed["family_probabilities"]["take"] != pytest.approx(
        original["family_probabilities"]["take"]
    )
    assert changed["conditional_probabilities"]["a"] != pytest.approx(
        original["conditional_probabilities"]["a"]
    )
    tied = audit.max_pooled_distribution(
        candidates, {"a": 0.5, "b": 0.5, "skip": 0.2}
    )
    assert tied["raw_score_max_action_ids"] == ["a", "b"]


def test_synthetic_extremes_remain_finite() -> None:
    result = audit.independent_distribution(
        {"skip": -3.4e38, "take": 3.4e38},
        {"skip": {"skip": 0.0}, "take": {"a": 3.4e38, "b": -3.4e38}},
    )
    values = [
        *result["family_probabilities"].values(),
        *result["conditional_probabilities"]["take"].values(),
    ]
    assert all(math.isfinite(value) for value in values)


def test_analytical_softmax_direction_matches_finite_difference() -> None:
    logits = {"a": 0.5, "b": 0.1, "c": -0.2}
    direction = {"a": 0.2, "b": -0.1, "c": -0.1}
    analytical = audit.softmax_directional_derivative(logits, direction)
    numerical = audit.finite_difference_softmax(logits, direction, epsilon=1e-6)
    assert analytical == pytest.approx(numerical, abs=1e-9)


@pytest.mark.parametrize(
    "family,conditional,match",
    [
        ({}, {}, "nonempty"),
        ({"take": math.inf}, {"take": {"a": 0.0}}, "finite"),
        ({"take": 0.0}, {"skip": {"a": 0.0}}, "coverage"),
        ({"take": 0.0}, {"take": {}}, "nonempty"),
    ],
)
def test_independent_distribution_rejects_malformed_inputs(
    family: dict[str, float],
    conditional: dict[str, dict[str, float]],
    match: str,
) -> None:
    with pytest.raises(audit.AuditError, match=match):
        audit.independent_distribution(family, conditional)


def test_authority_scope_and_synthetic_contracts_are_bounded() -> None:
    assert audit.audit_authority()
    assert set(audit.audit_authority().values()) == {False}
    assert {"causal", "causal_claim", "policy_quality", "training"} <= set(
        audit.audit_authority()
    )
    assert audit.audit_scope()["source_only"] is True
    assert audit.synthetic_contracts()["all_passed"] is True


def test_publication_is_deterministic_bounded_and_vector_free(
    tmp_path: Path,
) -> None:
    report = _report()
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_result = audit.publish_reports(report, first)
    second_result = audit.publish_reports(report, second)

    for name in (audit.DEFAULT_JSON_NAME, audit.DEFAULT_MARKDOWN_NAME):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    assert first_result == second_result
    assert first_result["json"]["size_bytes"] <= audit.MAX_JSON_REPORT_BYTES
    assert (
        first_result["markdown"]["size_bytes"]
        <= audit.MAX_MARKDOWN_REPORT_BYTES
    )
    raw = (first / audit.DEFAULT_JSON_NAME).read_text(encoding="utf-8")
    assert "data_base64" not in raw
    assert "component_vectors" not in raw


def test_publication_is_deterministic_across_isolated_processes(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_bytes(audit.canonical_json_bytes(_report()))
    code = """
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()))
from analysis_scripts import audit_card_acceptance_objective_interventions as audit
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


def test_report_construction_is_deterministic_across_isolated_processes(
    tmp_path: Path,
) -> None:
    code = """
import contextlib, pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()))
from analysis_scripts import audit_card_acceptance_objective_interventions as audit
prior = audit._load_prior()
verification = {
    'checkpoint_count': 8,
    'completed_chunk_indices': list(range(8)),
    'manifest_sha256': audit.EXPECTED_MANIFEST_SHA256,
    'terminal_sha256': audit.EXPECTED_TERMINAL_SHA256,
    'verdict': audit.EXPECTED_TERMINAL_VERDICT,
}
@contextlib.contextmanager
def held(_path):
    yield audit.EXPECTED_IDENTITY
prior.baseline.verifier._hold_inactive_execution_lease = held
prior.baseline.verifier._verify_terminal_bundle_contents = (
    lambda *_args, **_kwargs: verification
)
prior.baseline.validate_verifier_result = lambda *_args: None
prior.baseline._validate_snapshot = lambda *_args: None
audit.verify_pushed_source = lambda *_args, **_kwargs: {
    'bindings': {}, 'commit': 'a' * 40, 'origin_master': 'a' * 40,
}
chunks = [
    {
        'chunk_index': index,
        'conditional_supported': True,
        'family_conditional_dot': -0.25 if index in (1, 4) else 0.25,
        'guard_invariants': {
            'conflict_projected_to_zero': True,
            'non_conflict_unchanged': True,
        },
    }
    for index in range(8)
]
verdict, inputs = audit.classify_verdict(chunks)
analysis = {
    'chunk_results': chunks,
    'execution_counts': {
        'card_reward_rows': 3536,
        'chunks': 8,
        'decisions': 11729,
        'take_candidate_multiplicity': {'3': 3522, '4': 14},
        'trajectories': 512,
    },
    'synthetic_contracts': audit.synthetic_contracts(),
    'verdict': verdict,
    'verdict_inputs': inputs,
    'windows': audit.summarize_windows(chunks),
}
audit._analyze_bound_chunks = lambda *_args, **_kwargs: analysis
report = audit.build_repository_audit(pathlib.Path.cwd(), source_commit='a' * 40)
pathlib.Path(sys.argv[1]).write_bytes(audit.canonical_json_bytes(report))
"""
    outputs = [tmp_path / "build-first.json", tmp_path / "build-second.json"]
    for output in outputs:
        result = subprocess.run(
            [sys.executable, "-I", "-c", code, str(output)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
    assert outputs[0].read_bytes() == outputs[1].read_bytes()


def test_publication_rejects_missing_or_true_authority(tmp_path: Path) -> None:
    report = _report()
    report["authority"]["training"] = True
    with pytest.raises(audit.AuditError, match="authority"):
        audit.publish_reports(report, tmp_path / "true-authority")

    report = _report()
    del report["authority"]
    with pytest.raises(audit.AuditError, match="schema"):
        audit.publish_reports(report, tmp_path / "missing-authority")

    report = _report()
    report["input_bindings"]["prior_json"]["payload"] = "AAAA"
    with pytest.raises(audit.AuditError, match="prior JSON binding schema"):
        audit.publish_reports(report, tmp_path / "nested-payload")

    report = _report()
    report["evidence"]["synthetic_contracts"] = {"all_passed": True}
    with pytest.raises(audit.AuditError, match="synthetic contracts"):
        audit.publish_reports(report, tmp_path / "partial-synthetic")


def test_publication_rejects_raw_vectors_and_size_overflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = _report()
    report["evidence"]["chunk_results"][0]["diagnostic_vector"] = [0.0, 1.0]
    with pytest.raises(audit.AuditError, match="raw vector"):
        audit.publish_reports(report, tmp_path / "raw")

    report = _report()
    monkeypatch.setattr(audit, "MAX_JSON_REPORT_BYTES", 1)
    with pytest.raises(audit.AuditError, match="JSON report"):
        audit.publish_reports(report, tmp_path / "large")


def test_publication_refuses_existing_or_consumed_output(tmp_path: Path) -> None:
    report = _report()
    output = tmp_path / "output"
    audit.publish_reports(report, output)
    with pytest.raises(audit.AuditError, match="already exists"):
        audit.publish_reports(report, output)

    consumed = tmp_path / "consumed"
    consumed.mkdir()
    with pytest.raises(audit.AuditError, match="consumed"):
        audit.publish_reports(report, consumed / "child", consumed_root=consumed)


def test_existing_modules_do_not_load_objective_intervention_audit() -> None:
    code = """
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()))
for name in (
    'analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime',
    'analysis_scripts.noncombat_state_conditioned_ranker',
    'spirecomm.ai.agent',
):
    __import__(name)
assert 'analysis_scripts.audit_card_acceptance_objective_interventions' not in sys.modules
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


def test_objective_intervention_import_defers_bound_helpers() -> None:
    code = """
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()))
from analysis_scripts import audit_card_acceptance_objective_interventions
assert 'analysis_scripts.audit_card_acceptance_conditional_choice' not in sys.modules
assert 'analysis_scripts.audit_cross_fitted_baseline_support' not in sys.modules
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
from analysis_scripts import audit_card_acceptance_objective_interventions as audit
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
    monkeypatch.setattr(
        audit, "build_repository_audit", lambda *_args, **_kwargs: _report()
    )
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


def test_cli_failure_leaves_no_partial_output(
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
