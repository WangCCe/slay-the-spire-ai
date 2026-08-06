from __future__ import annotations

import base64
import copy
import hashlib
import inspect
import json
import subprocess
import sys
from collections import OrderedDict
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import torch

from analysis_scripts import noncombat_hierarchical_advantage_attribution as contract


ROOT = Path(__file__).resolve().parents[1]
JSON_REPORT_PATH = (
    ROOT
    / "reports"
    / "noncombat_hierarchical_advantage_attribution_contract_20260806.json"
)
MARKDOWN_REPORT_PATH = (
    ROOT
    / "reports"
    / "noncombat_hierarchical_advantage_attribution_contract_20260806.md"
)


def _sha256(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _folds() -> dict[str, tuple[str, ...]]:
    return {
        "fold-a": ("trajectory-a0", "trajectory-a1"),
        "fold-b": ("trajectory-b0", "trajectory-b1"),
    }


def _record(
    trajectory_id: str,
    fold_id: str,
    *,
    decision_index: int = 0,
    raw_return: float = 3.0,
    baseline_prediction: float = 1.0,
    scale: float = 2.0,
    baseline_mode: str = "cross_fitted",
    scale_mode: str = "cross_fitted",
    baseline_fit: tuple[str, ...] | None = None,
    scale_fit: tuple[str, ...] | None = None,
    feature_fields: tuple[str, ...] = ("pre_decision_state_features",),
) -> dict[str, object]:
    default_fit = (
        _folds()["fold-b"] if fold_id == "fold-a" else _folds()["fold-a"]
    )
    return {
        "baseline_fit_trajectory_ids": list(
            default_fit if baseline_fit is None else baseline_fit
        ),
        "baseline_mode": baseline_mode,
        "baseline_prediction": baseline_prediction,
        "decision_id": f"{trajectory_id}:decision-{decision_index}",
        "decision_index": decision_index,
        "feature_fields": list(feature_fields),
        "feature_schema_version": "pre-decision-state-features-v1",
        "feature_sha256": _sha256(
            f"{trajectory_id}:decision-{decision_index}:features"
        ),
        "fold_id": fold_id,
        "raw_return": raw_return,
        "scale": scale,
        "scale_fit_trajectory_ids": list(
            default_fit if scale_fit is None else scale_fit
        ),
        "scale_mode": scale_mode,
        "trajectory_id": trajectory_id,
    }


def _cross_fitted_records() -> list[dict[str, object]]:
    return [
        _record("trajectory-a0", "fold-a", raw_return=3.0),
        _record("trajectory-a1", "fold-a", raw_return=5.0),
        _record("trajectory-b0", "fold-b", raw_return=-1.0),
        _record("trajectory-b1", "fold-b", raw_return=1.0),
    ]


def _fixed_zero_record() -> dict[str, object]:
    return _record(
        "trajectory-a0",
        "fold-a",
        raw_return=2.5,
        baseline_prediction=0.0,
        scale=1.0,
        baseline_mode="fixed_zero",
        scale_mode="fixed_unit",
        baseline_fit=(),
        scale_fit=(),
    )


def _gradient_fixture():
    p = torch.nn.Parameter(torch.tensor([2.0, -1.0], dtype=torch.float32))
    q = torch.nn.Parameter(torch.tensor([0.5], dtype=torch.float32))
    components = OrderedDict(
        (
            ("card_reward_family_policy", 2.0 * p[0] + q[0]),
            ("card_reward_conditional_policy", p[1].square()),
            ("other_policy", -p[0] - 3.0 * q[0]),
            ("family_entropy_regularizer", 0.1 * (p[0] + p[1])),
            ("conditional_entropy_regularizer", -0.2 * q[0]),
        )
    )
    full_loss = (
        2.0 * p[0]
        + q[0]
        + p[1].square()
        - p[0]
        - 3.0 * q[0]
        + 0.1 * (p[0] + p[1])
        - 0.2 * q[0]
    )
    return full_loss, components, (("p", p), ("q", q))


def test_cross_fitted_advantages_bind_complete_disjoint_provenance():
    batch = contract.build_advantage_batch(
        _cross_fitted_records(), fold_trajectories=_folds()
    )

    assert tuple(row.trajectory_id for row in batch.records) == (
        "trajectory-a0",
        "trajectory-a1",
        "trajectory-b0",
        "trajectory-b1",
    )
    assert [row.advantage for row in batch.records] == [1.0, 2.0, -1.0, 0.0]
    assert len(batch.fold_manifest_sha256) == 64
    assert all(len(row.baseline_fit_sha256) == 64 for row in batch.records)
    assert all(len(row.scale_fit_sha256) == 64 for row in batch.records)
    with pytest.raises(FrozenInstanceError):
        batch.records[0].advantage = 4.0  # type: ignore[misc]


@pytest.mark.parametrize("leak", ["trajectory-a0", "trajectory-a1"])
def test_any_held_out_fold_member_in_a_fit_set_is_rejected(leak: str):
    rows = _cross_fitted_records()
    rows[0]["baseline_fit_trajectory_ids"] = [leak, "trajectory-b0"]

    with pytest.raises(contract.AdvantageAttributionError, match="held-out"):
        contract.build_advantage_batch(rows, fold_trajectories=_folds())


def test_one_trajectory_cannot_be_split_across_folds():
    rows = _cross_fitted_records()
    rows.append(_record("trajectory-a0", "fold-b", decision_index=1))

    with pytest.raises(contract.AdvantageAttributionError, match="one fold"):
        contract.build_advantage_batch(rows, fold_trajectories=_folds())


@pytest.mark.parametrize(
    "fit_ids, message",
    [
        (("trajectory-b1", "trajectory-b0"), "canonical"),
        (("trajectory-b0", "trajectory-b0"), "unique"),
        (("trajectory-b0", "unknown"), "known trajectory"),
        ((), "nonempty"),
    ],
)
def test_data_derived_fit_identity_must_be_complete_and_canonical(
    fit_ids: tuple[str, ...], message: str
):
    rows = _cross_fitted_records()
    rows[0]["baseline_fit_trajectory_ids"] = list(fit_ids)

    with pytest.raises(contract.AdvantageAttributionError, match=message):
        contract.build_advantage_batch(rows, fold_trajectories=_folds())


@pytest.mark.parametrize(
    "field",
    ["baseline_fit_trajectory_ids", "scale_fit_trajectory_ids"],
)
def test_data_derived_fit_set_covers_every_nonheldout_trajectory(field: str):
    rows = _cross_fitted_records()
    rows[0][field] = ["trajectory-b0"]

    with pytest.raises(contract.AdvantageAttributionError, match="complete"):
        contract.build_advantage_batch(rows, fold_trajectories=_folds())


@pytest.mark.parametrize(
    "field",
    [
        "selected_action_id",
        "selected_family",
        "candidate_scores",
        "successor_transition",
        "reward",
        "terminal_outcome",
        "later_observation",
    ],
)
def test_baseline_feature_provenance_rejects_post_action_fields(field: str):
    rows = _cross_fitted_records()
    rows[0]["feature_fields"] = ["pre_decision_state_features", field]

    with pytest.raises(contract.AdvantageAttributionError, match="feature fields"):
        contract.build_advantage_batch(rows, fold_trajectories=_folds())


def test_advantage_arithmetic_is_shift_invariant_without_hidden_normalization():
    first = contract.build_advantage_batch(
        _cross_fitted_records(), fold_trajectories=_folds()
    )
    shifted = _cross_fitted_records()
    for row in shifted:
        row["raw_return"] = float(row["raw_return"]) + 7.0
        row["baseline_prediction"] = float(row["baseline_prediction"]) + 7.0
    second = contract.build_advantage_batch(shifted, fold_trajectories=_folds())

    assert [row.advantage for row in first.records] == [
        row.advantage for row in second.records
    ]


def test_fixed_zero_unit_scale_is_an_explicit_raw_return_compatibility_path():
    rows = [_fixed_zero_record()]
    batch = contract.build_advantage_batch(
        rows, fold_trajectories={"fold-a": ("trajectory-a0",)}
    )

    assert batch.records[0].advantage == 2.5
    assert batch.records[0].baseline_fit_trajectory_ids == ()
    assert batch.records[0].scale_fit_trajectory_ids == ()
    assert batch.records[0].confounding_reduction_claimed is False


@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda row: row.__setitem__("scale", 0.0), "scale"),
        (lambda row: row.__setitem__("scale", float("nan")), "finite"),
        (lambda row: row.__setitem__("baseline_prediction", float("inf")), "finite"),
        (lambda row: row.__setitem__("normalization_mode", "batch"), "fields"),
        (lambda row: row.__setitem__("scale_mode", "hidden"), "scale_mode"),
        (
            lambda row: row.__setitem__("baseline_fit_trajectory_ids", []),
            "nonempty",
        ),
    ],
)
def test_invalid_or_hidden_advantage_arithmetic_fails_closed(mutator, message: str):
    rows = _cross_fitted_records()
    mutator(rows[0])

    with pytest.raises(contract.AdvantageAttributionError, match=message):
        contract.build_advantage_batch(rows, fold_trajectories=_folds())


def test_gradient_components_reconstruct_the_independent_full_gradient():
    full_loss, components, named_parameters = _gradient_fixture()
    ledger = contract.build_gradient_ledger(
        full_loss=full_loss,
        components=components,
        named_parameters=named_parameters,
        parameter_order=("p", "q"),
    )

    assert ledger.component_names == contract.COMPONENT_NAMES
    assert ledger.parameter_names == ("p", "q")
    assert ledger.parameter_shapes == ((2,), (1,))
    assert torch.allclose(ledger.component_sum, ledger.full_gradient)
    assert ledger.pre_clip_reconstruction_max_abs <= contract.GRADIENT_ATOL
    assert ledger.post_clip_reconstruction_max_abs <= contract.GRADIENT_ATOL
    assert torch.equal(
        ledger.component_vectors["card_reward_conditional_policy"][2:],
        torch.zeros(1, dtype=torch.float64),
    )


def test_cancellation_is_signed_and_not_reduced_to_component_norms():
    full_loss, components, named_parameters = _gradient_fixture()
    ledger = contract.build_gradient_ledger(
        full_loss=full_loss,
        components=components,
        named_parameters=named_parameters,
        parameter_order=("p", "q"),
    )

    family = ledger.component_vectors["card_reward_family_policy"]
    other = ledger.component_vectors["other_policy"]
    assert family[0].item() > 0.0
    assert other[0].item() < 0.0
    pair = next(
        row
        for row in ledger.pairwise_metrics
        if row["left"] == "card_reward_family_policy"
        and row["right"] == "other_policy"
    )
    assert pair["dot"] < 0.0


def test_global_clip_factor_is_derived_once_from_the_complete_gradient():
    full_loss, components, named_parameters = _gradient_fixture()
    ledger = contract.build_gradient_ledger(
        full_loss=full_loss,
        components=components,
        named_parameters=named_parameters,
        parameter_order=("p", "q"),
    )

    expected = 1.0 / (ledger.pre_clip_norm + contract.CLIP_EPSILON)
    assert ledger.pre_clip_norm > contract.GRADIENT_NORM_CEILING
    assert ledger.clip_factor == expected
    assert ledger.post_clip_norm <= contract.GRADIENT_NORM_CEILING
    for name in contract.COMPONENT_NAMES:
        assert torch.equal(
            ledger.clipped_component_vectors[name],
            ledger.component_vectors[name] * ledger.clip_factor,
        )


def test_bounded_gradient_uses_exact_unit_clip_factor():
    p = torch.nn.Parameter(torch.tensor([0.0], dtype=torch.float32))
    components = OrderedDict(
        (name, (index + 1) * p[0] * 0.01)
        for index, name in enumerate(contract.COMPONENT_NAMES)
    )
    full_loss = p[0] * sum((index + 1) * 0.01 for index in range(5))
    ledger = contract.build_gradient_ledger(
        full_loss=full_loss,
        components=components,
        named_parameters=(("p", p),),
        parameter_order=("p",),
    )

    assert ledger.pre_clip_norm < 1.0
    assert ledger.clip_factor == 1.0
    assert torch.equal(ledger.full_gradient, ledger.clipped_full_gradient)


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("missing_component", "component"),
        ("reordered_component", "order"),
        ("full_loss", "full loss"),
        ("parameter_order", "parameter order"),
        ("duplicate_parameter", "unique"),
        ("aliased_parameter", "unique"),
        ("detached", "gradient"),
        ("nonfinite", "finite"),
        ("float64_parameter", "float32"),
    ],
)
def test_gradient_identity_and_numeric_drift_fail_closed(
    mutation: str, message: str
):
    full_loss, components, named_parameters = _gradient_fixture()
    parameter_order = ("p", "q")
    if mutation == "missing_component":
        components.pop("other_policy")
    elif mutation == "reordered_component":
        components.move_to_end("card_reward_family_policy")
    elif mutation == "full_loss":
        full_loss = full_loss + 1.0
    elif mutation == "parameter_order":
        parameter_order = ("q", "p")
    elif mutation == "duplicate_parameter":
        named_parameters = (("p", named_parameters[0][1]), ("p", named_parameters[1][1]))
        parameter_order = ("p", "p")
    elif mutation == "aliased_parameter":
        named_parameters = (
            ("p", named_parameters[0][1]),
            ("q", named_parameters[0][1]),
        )
    elif mutation == "detached":
        components["other_policy"] = components["other_policy"].detach()
    elif mutation == "nonfinite":
        components["other_policy"] = components["other_policy"] * float("inf")
    elif mutation == "float64_parameter":
        bad = torch.nn.Parameter(torch.tensor([1.0], dtype=torch.float64))
        named_parameters = (("p", bad),)
        parameter_order = ("p",)
        components = OrderedDict(
            (name, bad[0] * 0.0) for name in contract.COMPONENT_NAMES
        )
        full_loss = bad[0] * 0.0

    with pytest.raises(contract.AdvantageAttributionError, match=message):
        contract.build_gradient_ledger(
            full_loss=full_loss,
            components=components,
            named_parameters=named_parameters,
            parameter_order=parameter_order,
        )


def test_gradient_api_exposes_no_optimizer_or_parameter_delta_surface():
    signature = inspect.signature(contract.build_gradient_ledger)
    forbidden = {
        "optimizer",
        "optimizer_state",
        "parameter_delta",
        "checkpoint",
        "path",
        "seed",
        "cohort",
        "environment_factory",
    }
    assert forbidden.isdisjoint(signature.parameters)
    full_loss, components, named_parameters = _gradient_fixture()
    with pytest.raises(TypeError):
        contract.build_gradient_ledger(
            full_loss=full_loss,
            components=components,
            named_parameters=named_parameters,
            parameter_order=("p", "q"),
            optimizer_state={},  # type: ignore[call-arg]
        )


def test_synthetic_evidence_preserves_aligned_opposing_and_tie_boundaries():
    evidence = contract.build_design_evidence()
    gradient = evidence["synthetic_gradient_evidence"]
    ties = evidence["max_pool_tie_evidence"]

    assert gradient["aligned"]["direct_take_pressure"] > 0.0
    assert gradient["aligned"]["shared_probe_pressure"] > 0.0
    assert gradient["opposing"]["direct_take_pressure"] > 0.0
    assert gradient["opposing"]["shared_probe_pressure"] < 0.0
    assert gradient["opposing"]["signs_disagree"] is True
    assert ties["within_family"]["score_greedy_action_ids"] == [
        "take-a",
        "take-z",
    ]
    assert ties["across_family"]["score_greedy_action_ids"] == [
        "skip",
        "take",
    ]
    assert ties["candidate_order_used_as_tie_break"] is False


def test_metadata_is_exactly_bounded_and_all_authority_is_false():
    metadata = contract.contract_metadata()

    assert metadata["schema_version"] == contract.CONTRACT_SCHEMA_VERSION
    assert metadata["component_names"] == list(contract.COMPONENT_NAMES)
    assert metadata["gradient_target"] == "pre-clip-model-parameter-gradient"
    assert metadata["clip_semantics"] == "aggregate-first-uniform-global-norm-v1"
    assert metadata["optimizer_attribution"] is False
    assert metadata["input_surface"]["paths"] is False
    assert metadata["input_surface"]["seeds"] is False
    assert metadata["input_surface"]["checkpoints"] is False
    assert metadata["input_surface"]["environments"] is False
    assert metadata["authority"]
    assert all(value is False for value in metadata["authority"].values())


def test_rendering_is_deterministic_in_process_and_across_fresh_processes():
    first = contract.render_design_report()
    second = contract.render_design_report()
    assert first == second
    assert first[0].endswith(b"\n")
    assert first[1].endswith(b"\n")
    json.loads(first[0])

    code = (
        "import base64,json;"
        "from analysis_scripts.noncombat_hierarchical_advantage_attribution "
        "import render_design_report;"
        "a,b=render_design_report();"
        "print(json.dumps([base64.b64encode(a).decode(),"
        "base64.b64encode(b).decode()],separators=(',',':')))"
    )
    outputs = [
        subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        for _ in range(2)
    ]
    assert outputs[0] == outputs[1]
    encoded = json.loads(outputs[0])
    assert base64.b64decode(encoded[0]) == first[0]
    assert base64.b64decode(encoded[1]) == first[1]


def test_tracked_reports_match_the_canonical_renderer():
    rendered_json, rendered_markdown = contract.render_design_report()

    assert JSON_REPORT_PATH.read_bytes() == rendered_json
    assert MARKDOWN_REPORT_PATH.read_bytes() == rendered_markdown


def test_direct_script_entrypoint_bootstraps_before_argument_rejection():
    completed = subprocess.run(
        [sys.executable, str(Path(contract.__file__)), "--unexpected"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "this source-only command accepts no arguments" in completed.stderr
    assert "ModuleNotFoundError" not in completed.stderr


def test_existing_runtime_and_production_sources_do_not_import_the_contract():
    module_name = "analysis_scripts.noncombat_hierarchical_advantage_attribution"
    for path in (
        ROOT / "analysis_scripts" / "noncombat_hierarchical_simulator_learning_runtime.py",
        ROOT / "analysis_scripts" / "noncombat_hierarchical_simulator_learning_experiment.py",
        ROOT / "analysis_scripts" / "noncombat_state_conditioned_ranker.py",
        ROOT / "analysis_scripts" / "noncombat_state_conditioned_policy_input.py",
        ROOT / "main.py",
    ):
        assert module_name not in path.read_text(encoding="utf-8")

    code = (
        "import json,sys;"
        "from analysis_scripts import "
        "noncombat_hierarchical_simulator_learning_runtime;"
        f"print(json.dumps({{'loaded':{module_name!r} in sys.modules}}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == {"loaded": False}


def test_public_api_accepts_no_empirical_or_execution_inputs():
    forbidden = {
        "path",
        "seed",
        "cohort",
        "checkpoint",
        "environment",
        "environment_factory",
        "optimizer",
        "optimizer_state",
        "parameter_delta",
        "execution",
    }
    for function in (
        contract.build_advantage_batch,
        contract.build_gradient_ledger,
        contract.build_design_evidence,
        contract.contract_metadata,
        contract.render_design_report,
        contract.write_design_report,
    ):
        assert forbidden.isdisjoint(inspect.signature(function).parameters)
