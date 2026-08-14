from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_cross_validated_shop_ensemble as ensemble
from analysis_scripts import noncombat_route_counterfactual_ranking as route


def _candidate(index: int) -> dict[str, Any]:
    return {
        "action_id": f"shop:test:{index}",
        "available": True,
        "category": "shop",
        "kind": "buy_card" if index == 0 else "leave",
        "label": f"option {index}",
        "raw": {"bits": index, "idx1": index, "idx2": 0},
    }


def _row(seed: int, *, current: int = 1) -> route.RouteRow:
    candidates = (_candidate(0), _candidate(1))
    return route.RouteRow(
        seed=seed,
        decision_index=0,
        source_sha256=f"{seed:064x}",
        state_features=torch.tensor([1.0, 0.0], dtype=torch.float32),
        candidate_features=torch.tensor(
            [[2.0, 0.0], [-2.0, 0.0]], dtype=torch.float32
        ),
        candidates=candidates,
        branch_outcomes=(
            {"action_id": candidates[0]["action_id"], "total_return": 1.0},
            {"action_id": candidates[1]["action_id"], "total_return": 0.0},
        ),
        current_action_id=candidates[current]["action_id"],
    )


def _rows_covering_folds(start: int, *, per_fold: int = 2) -> tuple[route.RouteRow, ...]:
    rows: list[route.RouteRow] = []
    counts = {fold: 0 for fold in range(ensemble.FOLD_COUNT)}
    seed = start
    while min(counts.values()) < per_fold:
        row = _row(seed)
        fold = ensemble._fold_for_source(row.source_sha256)
        if counts[fold] < per_fold:
            rows.append(row)
            counts[fold] += 1
        seed += 1
    return tuple(rows)


def _partition(name: str, rows: tuple[route.RouteRow, ...]) -> route.RoutePartition:
    return route.RoutePartition(
        name=name,
        seeds=tuple(row.seed for row in rows),
        rows=rows,
        action_branches=2 * len(rows),
        root_native_transitions=len(rows),
        censored_sources=(),
        budget_exhausted=False,
    )


def _write_binding(
    root: Path,
    cohort: str,
    name: str,
    rows: tuple[route.RouteRow, ...],
) -> ensemble.DatasetBinding:
    payload = route.encode_partition(_partition(name, rows))
    path = root / f"{cohort}.json"
    path.write_bytes(payload)
    return ensemble.DatasetBinding(
        cohort=cohort,
        path=path,
        sha256=hashlib.sha256(payload).hexdigest(),
        partition_name=name,
        source_count=len(rows),
    )


class _Fixed(torch.nn.Module):
    def __init__(self, choose: int) -> None:
        super().__init__()
        self.choose = choose

    def forward(
        self, _state: torch.Tensor, candidates: torch.Tensor
    ) -> torch.Tensor:
        scores = torch.zeros(candidates.shape[0], dtype=torch.float32)
        scores[self.choose] = 1.0
        return scores


def test_script_starts_in_isolated_mode_outside_repo(tmp_path: Path) -> None:
    script = Path(ensemble.__file__).resolve()

    completed = subprocess.run(
        [sys.executable, "-I", str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "cross-validated shop ensemble" in completed.stdout.lower()


def _corpus(rows: tuple[route.RouteRow, ...]) -> ensemble.HistoricalCorpus:
    normalized = tuple(sorted(rows, key=lambda row: row.source_sha256))
    return ensemble.HistoricalCorpus(
        rows=normalized,
        cohort_by_source={row.source_sha256: "test" for row in normalized},
        audit={"bindings": [], "source_count": len(normalized)},
    )


def test_historical_loader_binds_hashes_and_preserves_fold_support(
    tmp_path: Path,
) -> None:
    first = _rows_covering_folds(1)
    second = _rows_covering_folds(10_000)
    bindings = (
        _write_binding(tmp_path, "first", "train", first),
        _write_binding(tmp_path, "second", "development", second),
    )

    corpus = ensemble.load_historical_corpus(tmp_path, bindings=bindings)

    assert len(corpus.rows) == 20
    assert corpus.audit["unique_source_count"] == 20
    assert all(
        set(row["cohorts"]) == {"first", "second"}
        for row in corpus.audit["fold_support"].values()
    )


def test_historical_loader_fails_closed_on_identity_or_overlap(
    tmp_path: Path,
) -> None:
    first = _rows_covering_folds(1)
    second = _rows_covering_folds(10_000)
    valid = _write_binding(tmp_path, "first", "train", first)
    wrong_hash = ensemble.DatasetBinding(
        cohort=valid.cohort,
        path=valid.path,
        sha256="0" * 64,
        partition_name=valid.partition_name,
        source_count=valid.source_count,
    )
    with pytest.raises(ensemble.CrossValidatedShopBlocked, match="identity"):
        ensemble.load_historical_corpus(tmp_path, bindings=(wrong_hash,))

    duplicate = _write_binding(tmp_path, "second", "development", first)
    with pytest.raises(ensemble.CrossValidatedShopBlocked, match="overlap"):
        ensemble.load_historical_corpus(tmp_path, bindings=(valid, duplicate))


def test_cross_validation_holds_out_every_prediction_source() -> None:
    corpus = _corpus(_rows_covering_folds(100, per_fold=4))
    fit_source_sets: list[set[str]] = []

    def trainer(rows: tuple[route.RouteRow, ...], **_kwargs: Any) -> tuple[tuple[_Fixed, ...], list[dict[str, Any]]]:
        fit_source_sets.append({row.source_sha256 for row in rows})
        return tuple(_Fixed(0) for _ in ensemble.MODEL_SEEDS), []

    selection = ensemble.cross_validate(
        corpus,
        checkpoint_epochs=(1,),
        vote_quorums=(3,),
        trainer=trainer,
    )

    assert selection.selected_epoch == 1
    assert selection.selected_vote_quorum == 3
    assert len(fit_source_sets) == ensemble.FOLD_COUNT
    for fold, fit_sources in enumerate(fit_source_sets):
        held_out = {
            row.source_sha256
            for row in corpus.rows
            if ensemble._fold_for_source(row.source_sha256) == fold
        }
        assert held_out.isdisjoint(fit_sources)
        assert fit_sources | held_out == {row.source_sha256 for row in corpus.rows}


def test_cross_validation_is_deterministic_and_fails_without_eligible_override() -> None:
    corpus = _corpus(_rows_covering_folds(500, per_fold=4))

    def better(rows: tuple[route.RouteRow, ...], **_kwargs: Any) -> tuple[tuple[_Fixed, ...], list[dict[str, Any]]]:
        return tuple(_Fixed(0) for _ in ensemble.MODEL_SEEDS), []

    first = ensemble.cross_validate(
        corpus, checkpoint_epochs=(1,), vote_quorums=(3, 5), trainer=better
    )
    second = ensemble.cross_validate(
        corpus, checkpoint_epochs=(1,), vote_quorums=(3, 5), trainer=better
    )
    assert ensemble._canonical_bytes(first.metrics) == ensemble._canonical_bytes(second.metrics)

    def current(rows: tuple[route.RouteRow, ...], **_kwargs: Any) -> tuple[tuple[_Fixed, ...], list[dict[str, Any]]]:
        return tuple(_Fixed(1) for _ in ensemble.MODEL_SEEDS), []

    with pytest.raises(ensemble.CrossValidationNoGo, match="no eligible") as captured:
        ensemble.cross_validate(
            corpus, checkpoint_epochs=(1,), vote_quorums=(3,), trainer=current
        )
    assert captured.value.metrics["selected"] is None
    assert captured.value.metrics["verdict"].endswith("not_eligible_after_oof")


def test_trained_ensemble_round_trip_preserves_predictions() -> None:
    corpus = _corpus(_rows_covering_folds(1_000, per_fold=4))
    selection = ensemble.CrossValidationSelection(
        selected_epoch=4,
        selected_vote_quorum=3,
        metrics={},
    )
    models, _histories = ensemble.train_ensemble(corpus.rows, epochs=4)
    payload = ensemble.encode_ensemble(models, selection)
    restored = ensemble.restore_ensemble(payload)

    before = ensemble.evaluate_ensemble(models, corpus.rows, vote_quorum=3)
    after = ensemble.evaluate_ensemble(restored, corpus.rows, vote_quorum=3)

    assert ensemble._canonical_bytes(before) == ensemble._canonical_bytes(after)


def test_fresh_gate_uses_exact_new_support(monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = _corpus(_rows_covering_folds(2_000, per_fold=4))
    fresh_rows = tuple(_row(50_000 + index) for index in range(32))
    fresh = _partition("development", fresh_rows)
    monkeypatch.setattr(
        ensemble.ranking, "_collect_partition", lambda *_args, **_kwargs: fresh
    )
    selection = ensemble.CrossValidationSelection(
        selected_epoch=1,
        selected_vote_quorum=3,
        metrics={"selected_epoch": 1, "selected_vote_quorum": 3},
    )
    ticks = iter((0.0, 1.0))

    result = ensemble.evaluate_fresh(
        lambda _seed: object(),
        lambda _seed: object(),
        corpus,
        selection,
        tuple(_Fixed(0) for _ in ensemble.MODEL_SEEDS),
        {
            "selected_epoch": 1,
            "selected_vote_quorum": 3,
            "schema_version": ensemble.MODEL_SCHEMA_VERSION,
        },
        maximum_charged_seconds=10.0,
        clock=lambda: next(ticks),
    )

    assert result.report["verdict"] == "cross_validated_shop_ensemble_ready_for_live_shadow_proposal"
    assert all(result.metrics["checks"].values())


def test_artifacts_match_manifest(tmp_path: Path) -> None:
    fresh_rows = tuple(_row(60_000 + index) for index in range(32))
    fresh = _partition("development", fresh_rows)
    result = ensemble.CrossValidatedShopResult(
        configuration={"schema_version": ensemble.SCHEMA_VERSION},
        corpus_audit={"source_count": 112},
        fresh=fresh,
        model={"selected_epoch": 1, "selected_vote_quorum": 3},
        oof_metrics={"selected_epoch": 1},
        metrics={
            "changes_vs_current": {"corrected": 1, "worsened": 0},
            "fresh": {
                "current": {"mean_regret": 1.0},
                "gated": {"mean_regret": 0.0, "override_count": 32},
            },
        },
        report={
            "fresh": {"source_count": 32},
            "historical_source_count": 112,
            "verdict": "test",
        },
    )
    output = tmp_path / "cross-validated-shop"

    ensemble.write_artifacts(
        output, result, {"source": {"commit": "a" * 40}}
    )

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert len(manifest["artifacts"]) == 8
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]


def test_no_go_preflight_artifacts_match_manifest(tmp_path: Path) -> None:
    corpus = _corpus(_rows_covering_folds(70_000, per_fold=2))
    output = tmp_path / "preflight"
    metrics = {
        "selected": None,
        "selected_epoch": None,
        "selected_vote_quorum": None,
        "verdict": "cross_validated_shop_ensemble_not_eligible_after_oof",
    }

    ensemble.write_preflight_artifacts(
        output,
        corpus,
        metrics,
        {"source": {"commit": "a" * 40}},
        model_payload=None,
    )

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert len(manifest["artifacts"]) == 5
    assert not (output / "model.json").exists()
    report = json.loads((output / "report.json").read_text("ascii"))
    assert report["operations"]["fresh_source_access"] is False
