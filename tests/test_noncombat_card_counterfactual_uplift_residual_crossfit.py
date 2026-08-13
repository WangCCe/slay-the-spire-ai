from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as crossfit
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot


def _candidate(slot: int, card_id: str) -> dict[str, object]:
    return {
        "action_id": f"card_reward:take:0:{slot}:{card_id.lower()}",
        "available": True,
        "category": "card_reward",
        "kind": "take",
        "label": card_id,
        "raw": {
            "id": card_id,
            "misc": 0,
            "name": card_id,
            "reward_index": 0,
            "slot": slot,
            "upgrade_count": 0,
            "upgraded": False,
        },
    }


def _row(
    seed: int,
    *,
    cards: tuple[str, str, str] = ("A", "B", "C"),
    returns: tuple[float, float, float, float] = (0.4, 0.2, 0.1, 0.0),
) -> ranking.CounterfactualRankingRow:
    return ranking.CounterfactualRankingRow(
        seed=seed,
        decision_index=0,
        source_sha256=f"{seed:064x}",
        state_features=torch.zeros(1024, dtype=torch.float32),
        candidate_features=torch.zeros((4, 1024), dtype=torch.float32),
        candidates=(
            _candidate(0, cards[0]),
            _candidate(1, cards[1]),
            _candidate(2, cards[2]),
            {
                "action_id": "card_reward:skip:0",
                "available": True,
                "category": "card_reward",
                "kind": "skip",
                "label": "skip",
                "raw": {"reward_index": 0},
            },
        ),
        action_returns=returns,
    )


def _rows() -> tuple[ranking.CounterfactualRankingRow, ...]:
    return tuple(_row(seed) for seed in range(8))


def _base_scores(rows, *, perfect: bool = False):
    scores = (3.0, 1.0, 0.0, -1.0) if perfect else (0.0, 2.0, 0.0, -1.0)
    return {row.source_sha256: scores for row in rows}


def test_seed_folds_are_sorted_complete_and_disjoint():
    folds = crossfit.build_seed_folds((8, 3, 5, 2, 7, 4, 6, 1), 4)

    assert folds == ((1, 5), (2, 6), (3, 7), (4, 8))
    assert set().union(*(set(fold) for fold in folds)) == set(range(1, 9))
    assert all(
        not set(folds[left]) & set(folds[right])
        for left in range(4)
        for right in range(left + 1, 4)
    )


def test_unseen_card_uses_fit_only_global_prior():
    model = crossfit.fit_uplift_model(_rows(), shrinkage=3)
    heldout = _row(20, cards=("UNSEEN", "B", "C"))

    scores, unseen = crossfit.compose_scores(
        heldout,
        (0.0, 0.0, 0.0, 0.0),
        model,
        strength=16,
    )

    assert unseen == 1
    assert scores[0] == pytest.approx(16 * model.global_uplift)
    assert scores[3] == 0.0


def test_cross_fit_rejects_overlapping_or_incomplete_seed_folds():
    rows = _rows()
    with pytest.raises(crossfit.UpliftCrossfitBlocked, match="seed isolation"):
        crossfit._cross_fitted_scores(
            rows,
            ((0, 1, 2, 3), (3, 4, 5, 6, 7)),
            crossfit.ResidualConfiguration(shrinkage=3, strength=16),
            _base_scores(rows),
        )


def test_nested_selection_is_deterministic_and_can_pass_fixed_gate():
    rows = _rows()

    first = crossfit.run_nested_crossfit(rows, _base_scores(rows))
    second = crossfit.run_nested_crossfit(rows, _base_scores(rows))

    assert crossfit._canonical_bytes(first) == crossfit._canonical_bytes(second)
    assert first["verdict"] == (
        "card_counterfactual_uplift_residual_ready_for_audit_proposal"
    )
    assert first["comparison"]["corrected_actions"] == len(rows)
    assert all(first["checks"].values())
    assert all(
        fold["selected_configuration"] in [item.as_dict() for item in crossfit.GRID]
        for fold in first["folds"]
    )


def test_already_perfect_base_fails_improvement_and_correction_gate():
    rows = _rows()

    result = crossfit.run_nested_crossfit(rows, _base_scores(rows, perfect=True))

    assert result["verdict"] == "card_counterfactual_uplift_residual_not_ready"
    assert result["checks"]["corrected_actions"] is False
    assert result["checks"]["mean_regret_decreased"] is False


def test_base_scoring_keeps_entry_model_byte_identical():
    bootstrap = runtime.build_matched_bootstrap()
    before = pilot.encode_candidate_card_policy(bootstrap)

    scores = crossfit._base_scores(bootstrap, (_row(30),))

    assert set(scores) == {f"{30:064x}"}
    assert len(scores[f"{30:064x}"]) == 4
    assert pilot.encode_candidate_card_policy(bootstrap) == before


def test_published_binding_uses_final_path(tmp_path):
    staging = tmp_path / ".staging"
    output = tmp_path / "output"
    staging.mkdir()

    binding = crossfit._write_artifact(staging, output, "report.json", b"{}")

    assert (staging / "report.json").read_bytes() == b"{}"
    assert binding["path"] == (output / "report.json").as_posix()
    assert binding["size_bytes"] == 2


def test_isolated_direct_entry_can_load_package():
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(Path(crossfit.__file__).resolve()),
            "--help",
        ],
        cwd=Path(crossfit.__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--source-commit" in completed.stdout
