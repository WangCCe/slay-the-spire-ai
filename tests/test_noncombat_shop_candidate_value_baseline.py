from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import torch

from analysis_scripts import noncombat_shop_candidate_value_baseline as shop


def _candidate(index: int, *, kind: str | None = None) -> dict[str, Any]:
    resolved_kind = kind or ("buy_card" if index == 0 else "leave")
    raw: dict[str, Any] = {"bits": index, "slot": index}
    if resolved_kind.startswith("buy_"):
        raw["price"] = 50 + index
    if resolved_kind == "buy_card":
        raw.update({"id": f"CARD_{index}", "upgrade_count": 0, "upgraded": False})
    return {
        "action_id": f"shop:{resolved_kind}:{index}",
        "available": True,
        "category": "shop",
        "kind": resolved_kind,
        "label": f"candidate {index}",
        "raw": raw,
    }


def _raw_row(seed: int, *, good_first: bool = True) -> dict[str, Any]:
    candidates = [_candidate(0), _candidate(1)]
    returns = (1.0, 0.0) if good_first else (0.0, 1.0)
    return {
        "branch_outcomes": [
            {"action_id": candidate["action_id"], "total_return": value}
            for candidate, value in zip(candidates, returns, strict=True)
        ],
        "candidates": candidates,
        "current_action_id": candidates[1]["action_id"],
        "decision_index": seed % 7,
        "seed": seed,
        "source_sha256": f"{seed:064x}",
    }


def _rows(count: int = shop.EXPECTED_SOURCE_COUNT) -> tuple[shop.ShopRow, ...]:
    return tuple(shop._parse_row(_raw_row(seed)) for seed in range(1, count + 1))


def test_candidate_features_are_deterministic_and_candidate_only() -> None:
    candidate = _candidate(0)
    first = shop.encode_candidate(candidate)
    second = shop.encode_candidate(copy.deepcopy(candidate))

    assert torch.equal(first, second)
    assert first.shape == (shop.FEATURE_DIM,)
    assert first[shop.ACTION_KINDS.index("buy_card")].item() == 1.0
    assert int(torch.count_nonzero(first).item()) >= 4


def test_load_corpus_rejects_identity_before_parsing(tmp_path: Path) -> None:
    path = tmp_path / "source_rows.json"
    path.write_text("[]\n", encoding="ascii")

    with pytest.raises(shop.ShopBaselineBlocked, match="identity differs"):
        shop.load_corpus(path)


def test_source_split_is_exact_disjoint_and_deterministic() -> None:
    rows = _rows()
    first = shop.split_rows(rows)
    second = shop.split_rows(tuple(reversed(rows)))

    assert [row.source_sha256 for row in first.fit] == [row.source_sha256 for row in second.fit]
    assert [row.source_sha256 for row in first.tune] == [row.source_sha256 for row in second.tune]
    assert [row.source_sha256 for row in first.holdout] == [row.source_sha256 for row in second.holdout]
    assert (len(first.fit), len(first.tune), len(first.holdout)) == (24, 8, 11)
    all_sources = [row.source_sha256 for part in (first.fit, first.tune, first.holdout) for row in part]
    assert len(all_sources) == len(set(all_sources)) == shop.EXPECTED_SOURCE_COUNT


def test_training_is_deterministic_and_learns_candidate_signal() -> None:
    rows = _rows(16)
    first, first_history = shop.train_model(rows, epochs=32)
    second, second_history = shop.train_model(rows, epochs=32)

    assert first_history == second_history
    assert first_history[-1]["mean_batch_loss"] < first_history[0]["mean_batch_loss"]
    assert shop.evaluate_model(first, rows) == shop.evaluate_model(second, rows)
    for name, value in first.state_dict().items():
        assert torch.equal(value, second.state_dict()[name])


def test_artifacts_have_matching_manifest(tmp_path: Path) -> None:
    policy = {
        "maximum_regret": 1.0,
        "mean_regret": 0.5,
        "predictions": [],
        "weighted_pairwise_accuracy": 0.5,
    }
    result = shop.BaselineResult(
        configuration={"schema_version": shop.SCHEMA_VERSION},
        split={"fit_sources": [], "holdout_sources": [], "tune_sources": []},
        model={"schema_version": shop.MODEL_SCHEMA_VERSION},
        metrics={
            "holdout": {"current": policy, "trained": policy, "untrained": policy},
            "selection": {"selected_epoch": 1},
            "verdict": "test",
        },
        report={
            "fit": {"source_count": 24},
            "holdout": {"source_count": 11},
            "tune": {"source_count": 8},
            "verdict": "test",
        },
    )
    output = tmp_path / "artifacts"
    shop.write_artifacts(output, result, {"source": {"commit": "a" * 40}})

    manifest = json.loads((output / "artifact_manifest.json").read_text("ascii"))
    assert len(manifest["artifacts"]) == 6
    for binding in manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]
