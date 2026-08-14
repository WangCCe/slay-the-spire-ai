from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

import torch

from analysis_scripts import noncombat_cross_validated_shop_ensemble as delegated
from analysis_scripts import noncombat_expanded_shop_ensemble_retraining as expanded
from analysis_scripts import noncombat_route_counterfactual_ranking as route


def test_script_starts_in_isolated_mode_outside_repo(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-I", str(Path(expanded.__file__).resolve()), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "verified 496-source corpus" in completed.stdout.lower()


def test_exact_production_corpus_loads_with_wrapper_identity() -> None:
    repo_root = Path(expanded.__file__).resolve().parents[1]

    corpus = expanded.load_expanded_corpus(repo_root)

    assert len(corpus.rows) == 496
    assert corpus.audit["cohorts"]["expansion384"]["source_count"] == 384
    assert corpus.audit["unique_source_count"] == 496
    assert expanded.BOUND_SOURCE_PATHS[0] == Path(
        "analysis_scripts/noncombat_expanded_shop_ensemble_retraining.py"
    )
    assert Path("analysis_scripts/noncombat_cross_validated_shop_ensemble.py") in expanded.BOUND_SOURCE_PATHS


def test_oof_no_go_preflight_publishes_without_fresh_access(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate = {
        "action_id": "shop:leave",
        "available": True,
        "category": "shop",
        "kind": "leave",
        "label": "leave",
        "raw": {"bits": 0, "idx1": 0, "idx2": 0},
    }
    row = route.RouteRow(
        seed=1,
        decision_index=0,
        source_sha256="1" * 64,
        state_features=torch.zeros(2, dtype=torch.float32),
        candidate_features=torch.zeros((1, 2), dtype=torch.float32),
        candidates=(candidate,),
        branch_outcomes=({"action_id": "shop:leave", "total_return": 0.0},),
        current_action_id="shop:leave",
    )
    corpus = delegated.HistoricalCorpus(
        rows=(row,),
        cohort_by_source={row.source_sha256: "test"},
        audit={"bindings": [], "feature_width": 2},
    )
    metrics = {
        "selected": None,
        "selected_epoch": None,
        "selected_vote_quorum": None,
        "verdict": "cross_validated_shop_ensemble_not_eligible_after_oof",
    }
    monkeypatch.setattr(expanded, "load_expanded_corpus", lambda _root: corpus)
    monkeypatch.setattr(
        expanded.delegated,
        "cross_validate",
        lambda _corpus: (_ for _ in ()).throw(delegated.CrossValidationNoGo(metrics)),
    )
    monkeypatch.setattr(
        expanded,
        "_source_identity",
        lambda _root: {"commit": "a" * 40, "files": [], "source_sha256": "b" * 64},
    )
    output = tmp_path / "preflight"
    args = argparse.Namespace(repo_root=str(tmp_path), output_dir=str(output))

    summary = expanded.execute_preflight(args)

    assert summary["source_count"] == 1
    assert summary["model_state_sha256"] is None
    report = json.loads((output / "report.json").read_text("ascii"))
    assert report["operations"]["fresh_source_access"] is False
    assert report["identity"]["source"]["commit"] == "a" * 40
