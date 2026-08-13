from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest
import torch

from analysis_scripts import noncombat_card_counterfactual_corpus_expansion_runner as corpus
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as uplift
from analysis_scripts import noncombat_large_corpus_card_uplift_residual as runner


def _candidate(slot: int, card_id: str) -> dict[str, object]:
    return {
        "action_id": f"card_reward:take:0:{slot}:{card_id.lower()}",
        "available": True,
        "category": "card_reward",
        "kind": "take",
        "label": card_id,
        "raw": {"id": card_id},
    }


def _row(
    seed: int,
    decision_index: int = 0,
    *,
    cards: tuple[str, str, str] = ("A", "B", "C"),
) -> ranking.CounterfactualRankingRow:
    return ranking.CounterfactualRankingRow(
        seed=seed,
        decision_index=decision_index,
        source_sha256=f"{seed * 10 + decision_index:064x}",
        state_features=torch.zeros(3, dtype=torch.float32),
        candidate_features=torch.zeros((4, 2), dtype=torch.float32),
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
        action_returns=(0.4, 0.2, 0.1, 0.0),
    )


def _rows(start: int, count: int) -> tuple[ranking.CounterfactualRankingRow, ...]:
    return tuple(_row(seed) for seed in range(start, start + count))


def _base_scores(rows):
    return {row.source_sha256: (0.0, 2.0, 0.0, -1.0) for row in rows}


def _corpus_registration() -> dict[str, object]:
    return {
        "authority": copy.deepcopy(corpus.AUTHORITY),
        "inputs": {},
        "operations": copy.deepcopy(corpus.OPERATIONS),
        "schedule": {
            "development_seeds": list(corpus.DEVELOPMENT_SEEDS),
            "reserved_audit_seeds": list(corpus.RESERVED_AUDIT_SEEDS),
            "seed_status": "new-train-development-with-untouched-audit",
            "train_seeds": list(corpus.TRAIN_SEEDS),
        },
    }


def _corpus_report(registration) -> dict[str, object]:
    return {
        "audit_accessed": False,
        "datasets": {},
        "schedule": copy.deepcopy(registration["schedule"]),
        "training_performed": False,
        "verdict": "card_counterfactual_corpus_ready_for_source_only_training_proposal",
    }


def test_fixed_contract_is_low_capacity_and_no_native_or_audit():
    assert runner.FOLD_COUNT == 5
    assert [item.as_dict() for item in uplift.GRID] == [
        {"shrinkage": shrinkage, "strength": strength}
        for shrinkage in (1, 3, 10)
        for strength in (16, 32, 64, 128)
    ]
    assert runner.MIN_DEVELOPMENT_CORRECTED_ACTIONS == 4
    assert runner.AUTHORITY["audit_access"] is False
    assert runner.OPERATIONS["native_loading"] is False
    assert runner.OPERATIONS["environment_construction"] is False


def test_corpus_metadata_rejects_audit_or_schedule_drift(tmp_path, monkeypatch):
    registration = _corpus_registration()
    report = _corpus_report(registration)

    def read(path):
        return report if Path(path).name == "report.json" else registration

    monkeypatch.setattr(runner, "_read_canonical", read)
    runner._validate_corpus_metadata(tmp_path)

    report["audit_accessed"] = True
    with pytest.raises(runner.LargeCorpusResidualBlocked, match="metadata"):
        runner._validate_corpus_metadata(tmp_path)


def test_train_selection_uses_complete_disjoint_seed_folds_and_is_deterministic():
    rows = _rows(100, 10)

    first = runner.select_train_configuration(rows, _base_scores(rows))
    second = runner.select_train_configuration(rows, _base_scores(rows))

    assert runner._canonical_bytes(
        {
            key: value.as_dict() if isinstance(value, uplift.ResidualConfiguration) else value
            for key, value in first.items()
            if key not in {"base_metrics", "candidate_metrics"}
        }
    ) == runner._canonical_bytes(
        {
            key: value.as_dict() if isinstance(value, uplift.ResidualConfiguration) else value
            for key, value in second.items()
            if key not in {"base_metrics", "candidate_metrics"}
        }
    )
    folds = [set(fold) for fold in first["folds"]]
    assert set().union(*folds) == set(range(100, 110))
    assert all(
        not folds[left] & folds[right]
        for left in range(len(folds))
        for right in range(left + 1, len(folds))
    )
    assert all(first["checks"].values())
    assert first["comparison"]["corrected_actions"] == len(rows)


def test_train_selection_rejects_duplicate_source_identity():
    rows = (_row(100), _row(100))

    with pytest.raises(uplift.UpliftCrossfitBlocked, match="source identities"):
        runner.select_train_configuration(rows, _base_scores(rows))


def test_development_gate_requires_corrections_and_bounds_regressions():
    base = {
        "maximum_top_action_regret": 0.4,
        "mean_top_action_regret": 0.2,
        "unique_best_accuracy": 0.4,
        "weighted_pairwise_accuracy": 0.5,
    }
    candidate = {
        "maximum_top_action_regret": 0.3,
        "mean_top_action_regret": 0.1,
        "unique_best_accuracy": 0.5,
        "weighted_pairwise_accuracy": 0.6,
    }

    passing = runner._development_checks(
        base,
        candidate,
        {"action_flips": 5, "corrected_actions": 4, "worsened_actions": 2},
    )
    failing = runner._development_checks(
        base,
        candidate,
        {"action_flips": 5, "corrected_actions": 3, "worsened_actions": 4},
    )

    assert all(passing.values())
    assert failing["corrected_actions"] is False
    assert failing["worsened_actions_bounded"] is False


def test_execute_persists_model_before_development_access(tmp_path, monkeypatch):
    train_rows = _rows(100, 10)
    development_rows = (
        _row(200, cards=("UNSEEN", "B", "C")),
        *(_row(seed) for seed in range(201, 210)),
    )
    output = tmp_path / "output"
    corpus_root = tmp_path / "corpus"
    events: list[str] = []
    monkeypatch.setattr(runner, "_source_bindings", lambda _root, _commit: {})
    monkeypatch.setattr(
        runner,
        "_load_train_inputs",
        lambda _root: (
            train_rows,
            object(),
            {
                "corpus_registration": {"path": "registration"},
                "corpus_report": {"path": "report"},
                "entry_checkpoint": {"path": "entry"},
                "lineage_registration": {"path": "lineage"},
                "train_dataset": {"path": "train"},
            },
        ),
    )
    monkeypatch.setattr(runner.pilot, "encode_candidate_card_policy", lambda _x: b"entry")
    monkeypatch.setattr(runner, "_base_scores", lambda _bootstrap, rows: _base_scores(rows))
    monkeypatch.setattr(
        runner,
        "_read_canonical",
        lambda _path: {"datasets": {"development": {"path": "development"}}},
    )

    def load_development(_root, _report):
        assert (
            output.with_name(f".{output.name}.{'c' * 40}.staging")
            / "residual_model.json"
        ).is_file()
        events.append("development_loaded")
        return development_rows, {"path": "development"}

    monkeypatch.setattr(runner, "_load_development_inputs", load_development)

    report = runner.execute(
        repo_root=tmp_path,
        source_commit="c" * 40,
        corpus_root=corpus_root,
        output_dir=output,
    )

    assert events == ["development_loaded"]
    assert report["model_parameters"] == 4
    assert report["unseen_development_take_actions"] == 1
    assert report["verdict"] == (
        "large_corpus_card_uplift_residual_ready_for_reserved_audit_proposal"
    )
    manifest = json.loads((output / "artifact_manifest.json").read_text())
    assert set(manifest["artifacts"]) == {
        "configuration.json",
        "folds.json",
        "metrics.json",
        "predictions.json",
        "report.json",
        "report.md",
        "residual_model.json",
    }


def test_isolated_direct_entry_can_load_package():
    completed = subprocess.run(
        [sys.executable, "-I", str(Path(runner.__file__).resolve()), "--help"],
        cwd=Path(runner.__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--source-commit" in completed.stdout
