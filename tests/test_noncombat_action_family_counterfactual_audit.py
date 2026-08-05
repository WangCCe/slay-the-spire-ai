from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest
import torch

from analysis_scripts import noncombat_action_family_counterfactual_audit as audit_module
from analysis_scripts.noncombat_action_family_counterfactual_audit import (
    ActionFamilyCounterfactualAuditError,
    audit_counterfactuals,
    publish_counterfactual_audit,
)


COLLAPSE_AUTHORITY_NAMES = (
    "causal_claim",
    "communication_mod",
    "formal_rl",
    "gameplay",
    "holdout_access",
    "model_fitting",
    "model_loading",
    "native_loading",
    "policy_promotion",
    "qualification",
    "seed_replay",
    "successor_experiment",
    "threshold_change",
    "training",
)
CATEGORIES = ("card_reward", "event", "route", "shop")


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _write(path: Path, value: object) -> bytes:
    payload = _canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def _decision(
    decision_id: str,
    category: str,
    candidates: list[tuple[str, str, float]],
    *,
    selected: str | None = None,
) -> dict[str, object]:
    return {
        "candidate_scores": {
            action_id: score for action_id, _kind, score in candidates
        },
        "candidates": [
            {"action_id": action_id, "kind": kind}
            for action_id, kind, _score in candidates
        ],
        "category": category,
        "decision_id": decision_id,
        "selected_action_id": selected or candidates[0][0],
        "state_effect": {
            "category": category,
            "decision_id": decision_id,
            "max_abs_relative_score_change": 0.0,
            "relative_order_changed": False,
            "zero_state_scores": [0.0 for _candidate in candidates],
        },
    }


def _phase_rows(prefix: str) -> list[dict[str, object]]:
    return [
        _decision(
            f"{prefix}:card",
            "card_reward",
            [
                ("card:take:a", "take", 1.0),
                ("card:take:b", "take", 0.9),
                ("card:take:c", "take", 0.8),
                ("card:skip", "skip", 0.95),
            ],
        ),
        _decision(
            f"{prefix}:event",
            "event",
            [
                ("event:0", "event_option", 0.5),
                ("event:1", "event_option", -0.5),
            ],
        ),
        _decision(
            f"{prefix}:route",
            "route",
            [("route:0", "map_node", 0.25)],
        ),
        _decision(
            f"{prefix}:shop",
            "shop",
            [
                ("shop:buy:a", "buy_card", 1.0),
                ("shop:buy:b", "buy_card", 0.9),
                ("shop:leave", "leave", 0.95),
                ("shop:remove", "remove_card", 0.8),
            ],
        ),
    ]


def _policy(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "categories": list(CATEGORIES),
        "diagnostic_rows": rows,
        "diagnostics": {
            "authority": {},
            "categories": list(CATEGORIES),
            "decision_count": len(rows),
            "schema_version": "fixture-diagnostics",
            "state_effect": {},
        },
        "episode_rows": [],
        "replay_diagnostic_rows": rows,
        "replay_episode_rows": [],
        "replay_exact": True,
        "unsupported_episodes": 0,
        "victories": 0,
    }


def _category_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    return {
        category: sum(row["category"] == category for row in rows)
        for category in CATEGORIES
    }


def _audit_phase(rows: list[dict[str, object]]) -> dict[str, object]:
    counts = _category_counts(rows)
    return {
        "card_reward": {"decision_count": counts["card_reward"]},
        "controls": {
            category: {"decision_count": counts[category]}
            for category in ("event", "route", "shop")
        },
        "decision_count": len(rows),
        "outcomes": {},
    }


def _make_fixture(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    source.mkdir(parents=True)
    training_rows = _phase_rows("training")
    initial_rows = _phase_rows("initial")
    trained_rows = _phase_rows("trained")
    training = {
        "chunks": [
            {
                "categories": list(CATEGORIES),
                "chunk_index": 0,
                "diagnostic_rows": training_rows,
                "entropy_coefficient": 0.01,
                "episode_end": 1,
                "episode_rows": [],
                "episode_start": 0,
                "episodes": 1,
                "gradient_norm_after_clip": 0.1,
                "gradient_norm_before_clip": 0.1,
                "loss": 0.2,
                "mean_entropy": 0.3,
                "mean_episode_return": 0.1,
                "optimizer_update": 1,
                "pass_index": 0,
                "unsupported_episodes": 0,
                "victories": 0,
            }
        ],
        "episode_count": 1,
        "schema_version": "noncombat-state-conditioned-training-rows-v1",
    }
    evaluation = {
        "canary": {
            "cohort": "canary",
            "floor_difference_ci": {},
            "initial": _policy(initial_rows),
            "paired_rows": [],
            "schema_version": (
                "noncombat-state-conditioned-simulator-learning-paired-evaluation-v1"
            ),
            "seeds": [71024],
            "trained": _policy(trained_rows),
            "unsupported_rate": 0.0,
            "unsupported_rate_denominator": 1,
        },
        "canary_gate": {
            "behavior_gate": {},
            "blockers": ["card_reward_selected_kind_saturation"],
            "floor_difference_ci": {},
            "initial_victories": 0,
            "passed": False,
            "trained_victories": 0,
            "unsupported_rate": 0.0,
            "verdict": "experiment_stopped_at_canary",
        },
        "holdout": {"accessed": False, "episode_count": 0},
        "verdict": "experiment_stopped_at_canary",
    }
    training_payload = _write(source / "training_rows.json", training)
    evaluation_payload = _write(source / "evaluation.json", evaluation)
    training_phase = _audit_phase(training_rows)
    collapse = {
        "authority": {name: False for name in COLLAPSE_AUTHORITY_NAMES},
        "canary": {
            "blockers": ["card_reward_selected_kind_saturation"],
            "initial": _audit_phase(initial_rows),
            "trained": _audit_phase(trained_rows),
            "verdict": "experiment_stopped_at_canary",
        },
        "command": [],
        "conclusion": {
            "bounded_interpretations": [],
            "prohibited_claims": [],
            "status": "mechanism_narrowed_causality_unresolved",
            "unresolved_hypotheses": [],
        },
        "integrity": {
            "checkpoint_count": 64,
            "checkpoint_identity": {},
            "holdout_accessed": False,
            "initial_model_sha256": "0" * 64,
            "logical_execution_id": "fixture-execution",
            "source_artifacts": [
                {
                    "path": "evaluation.json",
                    "sha256": hashlib.sha256(evaluation_payload).hexdigest(),
                    "size_bytes": len(evaluation_payload),
                },
                {
                    "path": "training_rows.json",
                    "sha256": hashlib.sha256(training_payload).hexdigest(),
                    "size_bytes": len(training_payload),
                },
            ],
            "source_root": str(source.resolve()),
            "status": "valid",
            "terminal_verdict": "experiment_stopped_at_canary",
        },
        "schema_version": "noncombat-state-conditioned-collapse-audit-v1",
        "trajectory": {
            "aggregate": training_phase,
            "boundaries": [],
            "chunk_count": 1,
            "chunks": [],
            "initial_tensor_gap": False,
            "pre_update_post_update_alignment": {},
        },
    }
    collapse_path = tmp_path / "collapse_audit.json"
    _write(collapse_path, collapse)
    return collapse_path, source


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_bytes())


def _rewrite(path: Path, value: object) -> None:
    path.write_bytes(_canonical(value))


def _rebind(collapse_path: Path, source: Path, artifact_name: str) -> None:
    collapse = _load(collapse_path)
    payload = (source / artifact_name).read_bytes()
    for identity in collapse["integrity"]["source_artifacts"]:
        if identity["path"] == artifact_name:
            identity["sha256"] = hashlib.sha256(payload).hexdigest()
            identity["size_bytes"] = len(payload)
            break
    _rewrite(collapse_path, collapse)


def test_audit_reports_mass_entropy_and_argmax_boundaries(tmp_path: Path) -> None:
    collapse_path, source = _make_fixture(tmp_path)

    result = audit_counterfactuals(collapse_path, source)

    assert result["schema_version"] == (
        "noncombat-action-family-counterfactual-audit-v1"
    )
    assert not any(result["authority"].values())
    training = result["phases"]["training"]
    assert training["decision_count"] == 4
    card = training["categories"]["card_reward"]
    assert card["family_mass"]["take"]["flat_mean_when_present"] > card[
        "family_mass"
    ]["take"]["hierarchical_mean_when_present"]
    assert card["argmax"]["transition_counts"] == {"take->skip": 1}
    assert card["argmax"]["transition_rate"] == pytest.approx(1.0)
    shop = training["categories"]["shop"]
    assert shop["argmax"]["transition_counts"] == {"buy_card->leave": 1}
    event = training["categories"]["event"]
    route = training["categories"]["route"]
    assert event["row_shape"]["one_family_count"] == 1
    assert route["row_shape"]["one_family_count"] == 1
    assert event["entropy"]["family_mean"] == pytest.approx(0.0, abs=1e-15)
    assert route["invariants"]["one_family_fallback_max_abs_error"] == pytest.approx(
        0.0, abs=1e-15
    )
    assert card["argmax"]["two_stage_mismatch_count"] == 0


def test_score_ties_are_excluded_from_deterministic_claims(tmp_path: Path) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    training = _load(source / "training_rows.json")
    row = training["chunks"][0]["diagnostic_rows"][0]
    row["candidate_scores"] = {
        action_id: 0.0 for action_id in row["candidate_scores"]
    }
    _rewrite(source / "training_rows.json", training)
    _rebind(collapse_path, source, "training_rows.json")

    card = audit_counterfactuals(collapse_path, source)["phases"]["training"][
        "categories"
    ]["card_reward"]

    assert card["argmax"]["raw_score_tie_count"] == 1
    assert card["argmax"]["comparable_count"] == 0
    assert card["argmax"]["transition_rate"] is None


def test_extreme_finite_float32_scores_keep_flat_entropy_finite(
    tmp_path: Path,
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    training = _load(source / "training_rows.json")
    row = training["chunks"][0]["diagnostic_rows"][0]
    limit = float(torch.finfo(torch.float32).max)
    for index, action_id in enumerate(row["candidate_scores"]):
        row["candidate_scores"][action_id] = limit if index == 0 else -limit
    _rewrite(source / "training_rows.json", training)
    _rebind(collapse_path, source, "training_rows.json")

    entropy = audit_counterfactuals(collapse_path, source)["phases"]["training"][
        "categories"
    ]["card_reward"]["entropy"]

    assert math.isfinite(entropy["flat_candidate_mean"])
    assert entropy["flat_candidate_mean"] == pytest.approx(0.0, abs=1e-15)


def test_publication_is_byte_identical_and_outside_source(tmp_path: Path) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    output_json = tmp_path / "published" / "audit.json"
    output_markdown = tmp_path / "published" / "audit.md"

    publish_counterfactual_audit(
        collapse_path,
        source,
        output_json=output_json,
        output_markdown=output_markdown,
    )
    first = (output_json.read_bytes(), output_markdown.read_bytes())
    publish_counterfactual_audit(
        collapse_path,
        source,
        output_json=output_json,
        output_markdown=output_markdown,
    )

    assert (output_json.read_bytes(), output_markdown.read_bytes()) == first
    assert output_json.read_bytes().endswith(b"\n")
    assert b"training_authority: false" in output_markdown.read_bytes()


def test_source_hash_drift_fails_before_analysis(tmp_path: Path) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    with (source / "training_rows.json").open("ab") as stream:
        stream.write(b" ")

    with pytest.raises(
        ActionFamilyCounterfactualAuditError, match="source identity mismatch"
    ):
        audit_counterfactuals(collapse_path, source)


def test_noncanonical_bound_source_fails_closed(tmp_path: Path) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    training_path = source / "training_rows.json"
    training_path.write_text(
        json.dumps(_load(training_path), sort_keys=True), encoding="utf-8"
    )
    _rebind(collapse_path, source, "training_rows.json")

    with pytest.raises(
        ActionFamilyCounterfactualAuditError, match="not canonical JSON"
    ):
        audit_counterfactuals(collapse_path, source)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("duplicate_candidate", "duplicate candidate action_id"),
        ("float32_overflow", "finite float32"),
        ("score_alignment", "candidate score identities"),
    ],
)
def test_invalid_decision_rows_fail_closed(
    tmp_path: Path, mutation: str, message: str
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    training = _load(source / "training_rows.json")
    row = training["chunks"][0]["diagnostic_rows"][0]
    if mutation == "duplicate_candidate":
        row["candidates"][1]["action_id"] = row["candidates"][0]["action_id"]
    elif mutation == "float32_overflow":
        first = row["candidates"][0]["action_id"]
        row["candidate_scores"][first] = 1e300
    else:
        row["candidate_scores"].pop(row["candidates"][0]["action_id"])
    _rewrite(source / "training_rows.json", training)
    _rebind(collapse_path, source, "training_rows.json")

    with pytest.raises(ActionFamilyCounterfactualAuditError, match=message):
        audit_counterfactuals(collapse_path, source)


def test_authority_holdout_and_count_drift_fail_closed(tmp_path: Path) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    collapse = _load(collapse_path)
    collapse["authority"]["training"] = True
    _rewrite(collapse_path, collapse)
    with pytest.raises(ActionFamilyCounterfactualAuditError, match="authority"):
        audit_counterfactuals(collapse_path, source)

    collapse_path, source = _make_fixture(tmp_path / "holdout")
    evaluation = _load(source / "evaluation.json")
    evaluation["holdout"]["accessed"] = True
    _rewrite(source / "evaluation.json", evaluation)
    _rebind(collapse_path, source, "evaluation.json")
    with pytest.raises(ActionFamilyCounterfactualAuditError, match="holdout"):
        audit_counterfactuals(collapse_path, source)

    collapse_path, source = _make_fixture(tmp_path / "counts")
    collapse = _load(collapse_path)
    collapse["trajectory"]["aggregate"]["card_reward"]["decision_count"] = 2
    _rewrite(collapse_path, collapse)
    with pytest.raises(ActionFamilyCounterfactualAuditError, match="count mismatch"):
        audit_counterfactuals(collapse_path, source)


def test_unexpected_or_missing_trusted_wrapper_keys_fail_closed(
    tmp_path: Path,
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    collapse = _load(collapse_path)
    collapse["conclusion"]["unexpected"] = False
    _rewrite(collapse_path, collapse)
    with pytest.raises(ActionFamilyCounterfactualAuditError, match="keys mismatch"):
        audit_counterfactuals(collapse_path, source)

    collapse_path, source = _make_fixture(tmp_path / "chunk")
    training = _load(source / "training_rows.json")
    training["chunks"][0].pop("loss")
    _rewrite(source / "training_rows.json", training)
    _rebind(collapse_path, source, "training_rows.json")
    with pytest.raises(ActionFamilyCounterfactualAuditError, match="keys mismatch"):
        audit_counterfactuals(collapse_path, source)

    collapse_path, source = _make_fixture(tmp_path / "state-effect")
    training = _load(source / "training_rows.json")
    training["chunks"][0]["diagnostic_rows"][0]["state_effect"][
        "unexpected"
    ] = False
    _rewrite(source / "training_rows.json", training)
    _rebind(collapse_path, source, "training_rows.json")
    with pytest.raises(ActionFamilyCounterfactualAuditError, match="keys mismatch"):
        audit_counterfactuals(collapse_path, source)


def test_distribution_metadata_drift_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    metadata = audit_module.family_distribution.distribution_metadata()
    metadata["family_aggregation"] = "changed"
    monkeypatch.setattr(
        audit_module.family_distribution,
        "distribution_metadata",
        lambda: metadata,
    )

    with pytest.raises(
        ActionFamilyCounterfactualAuditError, match="distribution metadata"
    ):
        audit_counterfactuals(collapse_path, source)


def test_output_boundary_and_validation_failure_preserve_destinations(
    tmp_path: Path,
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    with pytest.raises(ActionFamilyCounterfactualAuditError, match="outside source root"):
        publish_counterfactual_audit(
            collapse_path,
            source,
            output_json=source / "audit.json",
            output_markdown=tmp_path / "audit.md",
        )

    output_json = tmp_path / "audit.json"
    output_markdown = tmp_path / "audit.md"
    output_json.write_bytes(b"old-json")
    output_markdown.write_bytes(b"old-markdown")
    collapse = _load(collapse_path)
    collapse["integrity"]["holdout_accessed"] = True
    _rewrite(collapse_path, collapse)
    with pytest.raises(ActionFamilyCounterfactualAuditError, match="holdout"):
        publish_counterfactual_audit(
            collapse_path,
            source,
            output_json=output_json,
            output_markdown=output_markdown,
        )
    assert output_json.read_bytes() == b"old-json"
    assert output_markdown.read_bytes() == b"old-markdown"


def test_second_replace_failure_rolls_back_both_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    output_json = tmp_path / "audit.json"
    output_markdown = tmp_path / "audit.md"
    output_json.write_bytes(b"old-json")
    output_markdown.write_bytes(b"old-markdown")
    real_replace = audit_module.os.replace

    def fail_new_markdown(source_path: object, destination_path: object) -> None:
        source_value = Path(source_path)
        destination_value = Path(destination_path)
        if (
            source_value.suffix == ".tmp"
            and destination_value.resolve(strict=False)
            == output_markdown.resolve(strict=False)
        ):
            raise PermissionError("injected second replace failure")
        real_replace(source_path, destination_path)

    monkeypatch.setattr(audit_module.os, "replace", fail_new_markdown)

    with pytest.raises(PermissionError, match="injected second replace failure"):
        publish_counterfactual_audit(
            collapse_path,
            source,
            output_json=output_json,
            output_markdown=output_markdown,
        )

    assert output_json.read_bytes() == b"old-json"
    assert output_markdown.read_bytes() == b"old-markdown"


def test_rollback_failure_preserves_recovery_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    output_json = tmp_path / "audit.json"
    output_markdown = tmp_path / "audit.md"
    output_json.write_bytes(b"old-json")
    output_markdown.write_bytes(b"old-markdown")
    real_replace = audit_module.os.replace
    replace_count = 0

    def fail_install_and_rollback(
        source_path: object, destination_path: object
    ) -> None:
        nonlocal replace_count
        replace_count += 1
        if replace_count in {2, 3}:
            raise PermissionError(f"injected replace failure {replace_count}")
        real_replace(source_path, destination_path)

    monkeypatch.setattr(audit_module.os, "replace", fail_install_and_rollback)

    with pytest.raises(
        ActionFamilyCounterfactualAuditError, match="rollback was incomplete"
    ):
        publish_counterfactual_audit(
            collapse_path,
            source,
            output_json=output_json,
            output_markdown=output_markdown,
        )

    recovery_payloads = [
        path.read_bytes() for path in tmp_path.glob(".audit.json.*.tmp")
    ]
    assert b"old-json" in recovery_payloads


def test_training_is_analyzed_before_evaluation_is_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    events: list[str] = []
    real_load = audit_module._load_bound_source
    real_analyze = audit_module._analyze_phase

    def tracked_load(
        source_root: Path, identity: dict[str, object]
    ) -> dict[str, object]:
        events.append(f"load:{identity['path']}")
        return real_load(source_root, identity)

    def tracked_analyze(
        rows: object, expected_counts: object, phase_name: str
    ) -> dict[str, object]:
        events.append(f"analyze:{phase_name}")
        return real_analyze(rows, expected_counts, phase_name)

    monkeypatch.setattr(audit_module, "_load_bound_source", tracked_load)
    monkeypatch.setattr(audit_module, "_analyze_phase", tracked_analyze)

    audit_counterfactuals(collapse_path, source)

    assert events[:3] == [
        "load:training_rows.json",
        "analyze:training",
        "load:evaluation.json",
    ]


def _symlink_or_skip(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")


@pytest.mark.parametrize(
    "boundary",
    ("collapse", "source_root", "training", "evaluation", "output"),
)
def test_symlink_and_reparse_boundaries_fail_closed(
    tmp_path: Path, boundary: str
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    if boundary == "collapse":
        linked_collapse = tmp_path / "linked-collapse.json"
        _symlink_or_skip(linked_collapse, collapse_path)
        with pytest.raises(ActionFamilyCounterfactualAuditError, match="non-symlink"):
            audit_counterfactuals(linked_collapse, source)
    elif boundary == "source_root":
        linked_root = tmp_path / "linked-source"
        _symlink_or_skip(linked_root, source, directory=True)
        with pytest.raises(ActionFamilyCounterfactualAuditError, match="non-symlink"):
            audit_counterfactuals(collapse_path, linked_root)
    elif boundary in {"training", "evaluation"}:
        artifact_name = f"{boundary}_rows.json" if boundary == "training" else "evaluation.json"
        artifact = source / artifact_name
        external = tmp_path / f"external-{artifact_name}"
        artifact.replace(external)
        _symlink_or_skip(artifact, external)
        with pytest.raises(ActionFamilyCounterfactualAuditError, match="non-symlink"):
            audit_counterfactuals(collapse_path, source)
    else:
        target = tmp_path / "target.json"
        target.write_bytes(b"old")
        linked_output = tmp_path / "linked-output.json"
        _symlink_or_skip(linked_output, target)
        with pytest.raises(ActionFamilyCounterfactualAuditError, match="symlink"):
            publish_counterfactual_audit(
                collapse_path,
                source,
                output_json=linked_output,
                output_markdown=tmp_path / "audit.md",
            )


def test_generic_reparse_point_is_rejected_without_symlink_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    training_path = (source / "training_rows.json").resolve(strict=True)
    real_check = audit_module._is_reparse_point

    def mark_training_as_reparse(path: Path) -> bool:
        return path.resolve(strict=False) == training_path or real_check(path)

    monkeypatch.setattr(audit_module, "_is_reparse_point", mark_training_as_reparse)

    with pytest.raises(ActionFamilyCounterfactualAuditError, match="non-symlink"):
        audit_counterfactuals(collapse_path, source)


def test_missing_output_marked_as_reparse_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    collapse_path, source = _make_fixture(tmp_path)
    output_json = (tmp_path / "missing-output.json").resolve(strict=False)
    real_check = audit_module._is_reparse_point

    def mark_missing_output(path: Path) -> bool:
        return path.resolve(strict=False) == output_json or real_check(path)

    monkeypatch.setattr(audit_module, "_is_reparse_point", mark_missing_output)

    with pytest.raises(ActionFamilyCounterfactualAuditError, match="symlink"):
        publish_counterfactual_audit(
            collapse_path,
            source,
            output_json=output_json,
            output_markdown=tmp_path / "audit.md",
        )


def test_canonical_input_comparison_does_not_build_full_serialized_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _canonical({"rows": [{"value": index} for index in range(100)]})

    def forbidden_full_copy(_value: object) -> bytes:
        raise AssertionError("full canonical serialization is forbidden while loading")

    monkeypatch.setattr(audit_module, "canonical_json_bytes", forbidden_full_copy)

    assert audit_module._parse_canonical_json(raw, "fixture")["rows"][99] == {
        "value": 99
    }
