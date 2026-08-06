from __future__ import annotations

import copy
import math
import struct
import subprocess
import sys
from pathlib import Path

import pytest
import torch

import analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment as experiment
import analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime as runtime
import analysis_scripts.verify_noncombat_cross_fitted_hierarchical_learning_experiment as verifier
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
)


ROOT = Path(__file__).resolve().parents[1]


def _snapshot(category: str = "shop") -> dict[str, object]:
    return {
        "adapter_api_version": ADAPTER_API_VERSION,
        "baseline_control": {
            "history": [{"outcome": "ignored", "seed": "ignored"}],
            "policy_id": "test-baseline-v1",
        },
        "category": category,
        "decision_count": 7,
        "schema_version": STATE_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "state": {
            "cur_hp": 55,
            "deck": [{"id": "Strike_R", "upgrades": 0}],
            "floor": 8,
            "gold": 123,
            "nested": {"outcome": "undecided", "seed": "hidden"},
        },
        "terminal": False,
    }


def _candidate(
    action_id: str,
    *,
    category: str = "shop",
    kind: str = "choose",
    price: int = 50,
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "available": True,
        "category": category,
        "kind": kind,
        "label": action_id,
        "raw": {"price": price, "provenance": {"source": "hidden"}},
    }


def _candidates(category: str = "shop") -> list[dict[str, object]]:
    return [
        _candidate(f"{category}:a", category=category, price=10),
        _candidate(f"{category}:b", category=category, price=20),
    ]


def test_control_and_verifier_import_without_torch_or_native():
    source = (
        "import builtins,json,sys;"
        "original=builtins.__import__;"
        "blocked={'torch','sts_lightspeed_noncombat_adapter'};"
        "builtins.__import__=lambda name,*a,**k: "
        "(_ for _ in ()).throw(RuntimeError('blocked '+name)) "
        "if name.split('.')[0] in blocked else original(name,*a,**k);"
        "import analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment as c;"
        "import analysis_scripts.verify_noncombat_cross_fitted_hierarchical_learning_experiment as v;"
        "c.experiment_contract();v.verifier_contract();"
        "print(json.dumps({'torch':'torch' in sys.modules,"
        "'native':'sts_lightspeed_noncombat_adapter' in sys.modules},sort_keys=True))"
    )

    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == '{"native": false, "torch": false}'


def test_source_contract_freezes_cross_fitted_mechanism_only():
    contract = experiment.experiment_contract()

    assert contract["baseline"] == {
        "feature_dim": 128,
        "fold_count": 4,
        "fit_trajectories_per_fold": 48,
        "held_out_trajectories_per_fold": 16,
        "prediction_bounds": [0.0, 3.0],
        "ridge_coefficient": 0.001,
        "ridge_residual_atol": 1e-9,
        "ridge_residual_rtol": 1e-9,
        "scale": 1.0,
        "solver": "cpu-float64-cholesky-v1",
        "trajectory_weighting": "equal-trajectory-mean-squared-error-v1",
    }
    assert contract["cohort"] == {
        "chunk_count": 8,
        "episodes_per_chunk": 64,
        "evaluation_cohorts": [],
        "scheduled_trajectories": 512,
        "selection": "tracked-fixed-tree-ascending-v1",
    }
    assert contract["limits"] == {
        "max_artifact_bytes": 64 * 1024 * 1024,
        "max_charged_seconds": 14_400.0,
        "max_decisions_per_episode": 500,
        "max_environment_accesses": 576,
        "max_optimizer_updates": 8,
        "max_retained_decisions": 32_768,
        "max_stored_bytes": 192 * 1024 * 1024,
        "max_uncompressed_bytes": 256 * 1024 * 1024,
    }
    assert set(contract["authority"].values()) == {False}
    assert contract["evaluation"] == {"authorized": False}


def test_baseline_state_projection_is_candidate_independent_and_leakage_controlled():
    snapshot = _snapshot()
    candidates = _candidates()

    first = runtime.project_baseline_state_features(snapshot, candidates)
    reordered = runtime.project_baseline_state_features(
        snapshot, list(reversed(candidates))
    )
    leaked_snapshot = copy.deepcopy(snapshot)
    leaked_snapshot["baseline_control"]["history"] = [
        {"outcome": "player_victory", "reward": 3.0, "seed": 999}
    ]
    leaked_snapshot["state"]["nested"] = {
        "outcome": "player_victory",
        "reward": 3.0,
        "seed": 999,
        "terminal_floor": 57,
    }
    leaked_candidates = copy.deepcopy(candidates)
    leaked_candidates[0]["raw"]["reward"] = 3.0
    leaked_candidates[0]["raw"]["selected_action_id"] = candidates[0][
        "action_id"
    ]
    leaked = runtime.project_baseline_state_features(
        leaked_snapshot, leaked_candidates
    )

    assert first.shape == (runtime.BASELINE_FEATURE_DIM,)
    assert first.dtype == torch.float32
    assert first.device.type == "cpu"
    assert torch.equal(first, reordered)
    assert torch.equal(first, leaked)


def test_folded_state_and_sparse_identity_are_exact_and_repeatable():
    source = torch.arange(1024, dtype=torch.float32)
    expected = torch.zeros(128, dtype=torch.float32)
    for source_index in range(1024):
        target_index = source_index % 128
        expected[target_index] = torch.tensor(
            float(expected[target_index]) + float(source[source_index]),
            dtype=torch.float32,
        )

    folded = runtime.fold_state_features(source)
    first = runtime.sparse_state_feature_payload(folded)
    second = runtime.sparse_state_feature_payload(folded.clone())

    assert torch.equal(folded, expected)
    assert first == second
    assert first["schema_version"] == runtime.BASELINE_FEATURE_SCHEMA_VERSION
    assert first["dense_dim"] == 128
    assert [entry[0] for entry in first["entries"]] == list(range(128))
    assert all(entry[1] != 0.0 for entry in first["entries"])
    assert len(first["sha256"]) == 64

    zeros = torch.tensor([0.0, -0.0] + [0.0] * 126, dtype=torch.float32)
    assert runtime.sparse_state_feature_payload(zeros)["entries"] == []


@pytest.mark.parametrize(
    "value",
    [
        torch.zeros(1023, dtype=torch.float32),
        torch.zeros(1024, dtype=torch.float64),
        torch.full((1024,), math.inf, dtype=torch.float32),
    ],
)
def test_folded_state_rejects_malformed_policy_features(value):
    with pytest.raises(runtime.RuntimeBlocked):
        runtime.fold_state_features(value)


def _baseline_decisions() -> list[runtime.BaselineDecision]:
    decisions: list[runtime.BaselineDecision] = []
    for seed in range(64):
        for decision_index in range(2):
            state = torch.zeros(128, dtype=torch.float32)
            state[0] = float(seed % 7) / 7.0
            state[1] = float(decision_index)
            decisions.append(
                runtime.BaselineDecision(
                    category="card_reward" if seed % 2 == 0 else "shop",
                    decision_id=f"seed-{seed}:decision-{decision_index}",
                    decision_index=decision_index,
                    raw_return=float((seed + decision_index) % 4),
                    seed=seed,
                    state_features=state,
                    trajectory_id=f"seed-{seed}",
                )
            )
    return decisions


def test_cross_fitted_ridge_uses_complete_disjoint_trajectory_folds():
    result = runtime.build_cross_fitted_baseline(_baseline_decisions())

    assert list(result.fold_trajectories) == [
        "fold-0",
        "fold-1",
        "fold-2",
        "fold-3",
    ]
    assert all(len(values) == 16 for values in result.fold_trajectories.values())
    assert len(result.models) == 4
    assert len(result.predictions) == 128
    assert len(result.advantage_batch.records) == 128
    for model in result.models:
        assert len(model.fit_trajectory_ids) == 48
        assert len(model.held_out_trajectory_ids) == 16
        assert not set(model.fit_trajectory_ids).intersection(
            model.held_out_trajectory_ids
        )
        assert len(model.coefficients) == 129
        assert max(abs(value) for value in model.kkt_residuals) <= 1e-7
    for record in result.advantage_batch.records:
        assert record.scale_mode == "fixed_unit"
        assert record.scale == 1.0
        assert record.baseline_mode == "cross_fitted"
        assert 0.0 <= record.baseline_prediction <= 3.0
        assert record.advantage == pytest.approx(
            record.raw_return - record.baseline_prediction
        )


def test_ridge_coordinate_zero_is_the_unpenalized_intercept():
    decisions = []
    for seed in range(64):
        decisions.append(
            runtime.BaselineDecision(
                category="shop",
                decision_id=f"seed-{seed}:decision-0",
                decision_index=0,
                raw_return=1.0,
                seed=seed,
                state_features=torch.zeros(128, dtype=torch.float32),
                trajectory_id=f"seed-{seed}",
            )
        )

    result = runtime.build_cross_fitted_baseline(decisions)

    for model in result.models:
        assert model.coefficients[0] == pytest.approx(1.0, abs=1e-12)
        assert max(abs(value) for value in model.coefficients[1:]) == 0.0
    assert all(
        prediction.unclipped == pytest.approx(1.0, abs=1e-12)
        for prediction in result.predictions
    )


def test_fold_assignment_uses_ascending_seed_position_not_input_or_identity_order():
    seeds = [1000 + index * 7 for index in range(64)]
    decisions = []
    expected = {f"fold-{index}": set() for index in range(4)}
    for position, seed in enumerate(seeds):
        trajectory_id = f"trajectory-{63 - position:02d}"
        expected[f"fold-{position % 4}"].add(trajectory_id)
        decisions.append(
            runtime.BaselineDecision(
                category="shop",
                decision_id=f"{trajectory_id}:decision-0",
                decision_index=0,
                raw_return=1.0,
                seed=seed,
                state_features=torch.zeros(128, dtype=torch.float32),
                trajectory_id=trajectory_id,
            )
        )

    result = runtime.build_cross_fitted_baseline(list(reversed(decisions)))

    for fold_id, trajectory_ids in result.fold_trajectories.items():
        assert set(trajectory_ids) == expected[fold_id]


def test_held_out_prediction_retains_preclip_bytes_and_uses_fixed_bounds():
    decisions = []
    for position in range(64):
        state = torch.zeros(128, dtype=torch.float32)
        if position % 4 == 0:
            state[0] = 100.0
            raw_return = 0.0
        else:
            state[0] = float(position) / 63.0
            raw_return = 3.0 * float(state[0])
        decisions.append(
            runtime.BaselineDecision(
                category="shop",
                decision_id=f"seed-{position}:decision-0",
                decision_index=0,
                raw_return=raw_return,
                seed=position,
                state_features=state,
                trajectory_id=f"seed-{position}",
            )
        )

    result = runtime.build_cross_fitted_baseline(decisions)
    clipped = [prediction for prediction in result.predictions if prediction.was_clipped]

    assert clipped
    assert any(prediction.unclipped > 3.0 for prediction in clipped)
    for prediction in clipped:
        assert 0.0 <= prediction.clipped <= 3.0
        assert len(prediction.preclip_little_endian_hex) == 16


def test_failed_cholesky_has_no_alternate_solver(monkeypatch):
    decisions = _baseline_decisions()

    def fail_cholesky(*args, **kwargs):
        raise RuntimeError("synthetic factorization failure")

    monkeypatch.setattr(torch.linalg, "cholesky", fail_cholesky)

    with pytest.raises(runtime.RuntimeBlocked, match="Cholesky"):
        runtime.build_cross_fitted_baseline(decisions)


def test_ridge_rhs_uses_canonical_float64_multiply_add_order():
    decisions = []
    by_id = {}
    for seed in range(64):
        state = torch.zeros(128, dtype=torch.float32)
        state[0] = torch.tensor(10_000_000.0 + seed, dtype=torch.float32)
        decision = runtime.BaselineDecision(
            category="shop",
            decision_id=f"seed-{seed}:decision-0",
            decision_index=0,
            raw_return=float(seed % 4),
            seed=seed,
            state_features=state,
            trajectory_id=f"seed-{seed}",
        )
        decisions.append(decision)
        by_id[decision.trajectory_id] = decision

    result = runtime.build_cross_fitted_baseline(list(reversed(decisions)))
    model = result.models[0]
    expected_rhs = 0.0
    for trajectory_id in sorted(
        model.fit_trajectory_ids, key=lambda value: by_id[value].seed
    ):
        decision = by_id[trajectory_id]
        expected_rhs += (
            (1.0 / 48.0) * float(decision.raw_return)
        ) * float(decision.state_features[0])

    assert model.rhs[1] == expected_rhs


def test_preclip_prediction_replays_exact_math_fsum_and_float64_bytes():
    decisions = _baseline_decisions()
    by_id = {decision.decision_id: decision for decision in decisions}

    result = runtime.build_cross_fitted_baseline(decisions)
    models = {model.fold_id: model for model in result.models}

    for prediction in result.predictions:
        decision = by_id[prediction.decision_id]
        values = [1.0] + [float(value) for value in decision.state_features]
        expected = math.fsum(
            float(coefficient) * float(value)
            for coefficient, value in zip(
                models[prediction.fold_id].coefficients, values, strict=True
            )
        )
        assert prediction.unclipped == expected
        assert struct.unpack(
            "<d", bytes.fromhex(prediction.preclip_little_endian_hex)
        )[0] == expected


def test_cross_fitted_ridge_requires_exact_64_complete_trajectories():
    decisions = _baseline_decisions()

    with pytest.raises(runtime.RuntimeBlocked, match="64"):
        runtime.build_cross_fitted_baseline(decisions[:-2])

    changed = copy.deepcopy(decisions)
    changed[1] = runtime.BaselineDecision(
        **{**changed[1].__dict__, "decision_index": 2}
    )
    with pytest.raises(runtime.RuntimeBlocked, match="contiguous"):
        runtime.build_cross_fitted_baseline(changed)


def test_ridge_residual_tolerance_is_frozen_at_the_boundary():
    scale = 3.0
    limit = verifier.RIDGE_RESIDUAL_ATOL + verifier.RIDGE_RESIDUAL_RTOL * scale
    within = math.nextafter(limit, 0.0)
    beyond = math.nextafter(limit, math.inf)

    assert verifier.ridge_residual_within_tolerance(
        residual=within, rhs=2.0, absolute_product_sum=scale
    )
    assert not verifier.ridge_residual_within_tolerance(
        residual=beyond, rhs=2.0, absolute_product_sum=scale
    )
