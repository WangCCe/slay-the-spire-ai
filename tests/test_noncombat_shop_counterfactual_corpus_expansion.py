from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_cross_validated_shop_ensemble as historical
from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts import noncombat_shop_counterfactual_corpus_expansion as expansion


def _candidate(index: int) -> dict[str, Any]:
    kinds = ("buy_card", "buy_potion", "remove_card", "leave")
    return {
        "action_id": f"shop:test:{index}",
        "available": True,
        "category": "shop",
        "kind": kinds[index],
        "label": f"option {index}",
        "raw": {"bits": index, "idx1": index, "idx2": 0},
    }


_STATE = torch.zeros(1024, dtype=torch.float32)
_CANDIDATES = tuple(_candidate(index) for index in range(4))
_CANDIDATE_FEATURES = torch.eye(4, 1024, dtype=torch.float32)


def _row(seed: int) -> route.RouteRow:
    returns = (1.0, 0.5, 0.2, 0.0)
    return route.RouteRow(
        seed=seed,
        decision_index=0,
        source_sha256=f"{seed:064x}",
        state_features=_STATE,
        candidate_features=_CANDIDATE_FEATURES,
        candidates=_CANDIDATES,
        branch_outcomes=tuple(
            {
                "action_id": candidate["action_id"],
                "total_return": value,
            }
            for candidate, value in zip(_CANDIDATES, returns, strict=True)
        ),
        current_action_id=_CANDIDATES[-1]["action_id"],
    )


def _partition(count: int = 384, *, start: int = 10_000) -> route.RoutePartition:
    rows = tuple(_row(start + index) for index in range(count))
    return route.RoutePartition(
        name="train",
        seeds=tuple(row.seed for row in rows),
        rows=rows,
        action_branches=4 * len(rows),
        root_native_transitions=len(rows),
        censored_sources=(),
        budget_exhausted=False,
    )


def _historical() -> historical.HistoricalCorpus:
    rows = tuple(_row(index + 1) for index in range(112))
    return historical.HistoricalCorpus(
        rows=rows,
        cohort_by_source={row.source_sha256: "historical" for row in rows},
        audit={"bindings": [], "feature_width": 1024},
    )


def _collect(
    monkeypatch: pytest.MonkeyPatch,
    partition: route.RoutePartition,
) -> expansion.ShopCorpusExpansionResult:
    monkeypatch.setattr(
        expansion.ranking,
        "_collect_partition",
        lambda *_args, **_kwargs: partition,
    )
    ticks = iter((0.0, 1.0))
    return expansion.collect_expansion(
        lambda _seed: object(),
        lambda _seed: object(),
        _historical(),
        maximum_charged_seconds=10.0,
        clock=lambda: next(ticks),
    )


def test_script_starts_in_isolated_mode_outside_repo(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-I", str(Path(expansion.__file__).resolve()), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "shop counterfactual outcomes" in completed.stdout.lower()


def test_complete_independent_expansion_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _collect(monkeypatch, _partition())

    assert result.report["verdict"] == "shop_counterfactual_expansion_ready_for_retraining_proposal"
    assert all(result.metrics["checks"].values())
    assert result.metrics["combined_source_count"] == 496
    assert result.metrics["informative_source_count"] == 384


def test_historical_overlap_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = list(_partition().rows)
    rows[0] = _row(1)
    overlapping = route.RoutePartition(
        name="train",
        seeds=tuple(row.seed for row in rows),
        rows=tuple(rows),
        action_branches=4 * len(rows),
        root_native_transitions=len(rows),
        censored_sources=(),
        budget_exhausted=False,
    )
    monkeypatch.setattr(
        expansion.ranking,
        "_collect_partition",
        lambda *_args, **_kwargs: overlapping,
    )

    with pytest.raises(expansion.ShopCorpusExpansionBlocked, match="historical"):
        expansion.collect_expansion(
            lambda _seed: object(),
            lambda _seed: object(),
            _historical(),
        )


def test_short_support_is_terminal_no_go(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _collect(monkeypatch, _partition(383))

    assert result.report["verdict"] == "shop_counterfactual_expansion_not_ready"
    assert result.metrics["checks"]["complete_source_support"] is False
    assert result.report["authority"]["retraining_proposal"] is False


def test_artifacts_match_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _collect(monkeypatch, _partition())
    output = tmp_path / "shop-expansion"

    expansion.write_artifacts(
        output,
        result,
        {"source": {"commit": "a" * 40}},
    )

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert len(manifest["artifacts"]) == 5
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
    encoded = (output / "dataset.json").read_bytes()
    assert route.encode_partition(route.restore_partition(encoded)) == encoded
