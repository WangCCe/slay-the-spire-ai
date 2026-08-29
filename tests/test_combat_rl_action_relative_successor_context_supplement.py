from __future__ import annotations

import copy
import json

import pytest
import torch

from analysis_scripts import combat_rl_action_relative_successor_delta_ablation as base
from analysis_scripts import combat_rl_action_relative_successor_context_supplement as supplement


def _corpus(partition: str, *, seed: int, battle: int, value: float) -> dict:
    action_mask = torch.tensor([[True, True, False]], dtype=torch.bool)
    state = {
        "continuous": torch.tensor([[value, value + 1]], dtype=torch.float32),
        "card_ids": torch.tensor([[1, 0]], dtype=torch.long),
        "potion_ids": torch.tensor([[0]], dtype=torch.long),
        "relic_ids": torch.tensor([[1]], dtype=torch.long),
        "action_masks": action_mask,
    }
    tensors = {
        **state,
        "guard_actions": torch.tensor([0]),
        "target_actions": torch.tensor([1]),
        "advantages": torch.tensor([0.5]),
        "positive": torch.tensor([True]),
    }
    pairs = {
        "source_rows": torch.tensor([0]),
        "candidate_actions": torch.tensor([1]),
        "guard_returns": torch.tensor([0.0]),
        "candidate_returns": torch.tensor([0.5]),
        "advantages": torch.tensor([0.5]),
        "guard_immediate_rewards": torch.tensor([0.0]),
        "candidate_immediate_rewards": torch.tensor([0.25]),
        "guard_dispositions": torch.tensor([base.SUPPORTED]),
        "candidate_dispositions": torch.tensor([base.SUPPORTED]),
    }
    for prefix in ("guard", "candidate"):
        for name, tensor in state.items():
            pairs[f"{prefix}_successor_{name}"] = tensor.clone()
    return base.validate_successor_corpus(
        {
            "schema_version": base.CORPUS_SCHEMA,
            "corpus_kind": base.CORPUS_KIND,
            "partition": partition,
            "tensors": tensors,
            "metadata": [
                {
                    "seed": seed,
                    "battle_index": battle,
                    "floor": 5 if battle == 3 else 25,
                    "guard_action_index": 0,
                    "target_action_index": 1,
                    "branch_returns": {"0": 0.0, "1": 0.5},
                }
            ],
            "pairs": pairs,
            "row_count": 1,
            "pair_count": 1,
        },
        expected_partition=partition,
    )


def test_registration_binds_exact_slices_inputs_and_development_authority() -> None:
    registration = supplement.build_registration("a" * 40, smoke=False)
    validated = supplement.validate_registration(registration, smoke=False)

    assert validated["recipe"]["slices"] == {
        "fit_battle_3": {
            "partition": "fit",
            "seed_bounds": [283000, 283383],
            "battle_indices": [3],
        },
        "fresh_battle_3": {
            "partition": "fresh",
            "seed_bounds": [284000, 285023],
            "battle_indices": [3],
        },
        "fresh_battle_10": {
            "partition": "fresh",
            "seed_bounds": [286000, 287535],
            "battle_indices": [10],
        },
    }
    assert set(validated["inputs"]) >= {
        "r2_fit_corpus",
        "r2_calibration_corpus",
        "r2_fresh_corpus",
        "r2_report",
        "r2_manifest",
        "r2_registration",
    }
    assert validated["authority"]["native_loading"] is True
    assert validated["authority"]["model_fitting"] is False
    assert validated["authority"]["training"] is False
    assert validated["authority"]["gameplay"] is False

    registration["recipe"]["slices"]["fit_battle_3"]["seed_bounds"][0] += 1
    with pytest.raises(ValueError, match="registration payload differs"):
        supplement.validate_registration(registration, smoke=False)


def test_slice_contract_rejects_overlap_and_lineage_collision() -> None:
    supplement.validate_slice_contract(supplement.FIXED_SLICES, occupied_seeds={275000})

    overlapping = copy.deepcopy(supplement.FIXED_SLICES)
    overlapping["fresh_battle_3"]["seed_bounds"] = [283383, 284406]
    with pytest.raises(ValueError, match="overlap"):
        supplement.validate_slice_contract(overlapping, occupied_seeds=set())

    with pytest.raises(ValueError, match="lineage"):
        supplement.validate_slice_contract(
            supplement.FIXED_SLICES, occupied_seeds={283123}
        )


def test_complete_corpus_merge_offsets_pairs_and_preserves_order() -> None:
    left = _corpus("fit", seed=275000, battle=3, value=1.0)
    right = _corpus("fit", seed=283000, battle=3, value=3.0)
    merged = supplement.merge_successor_corpora("fit", left, right)

    assert merged["row_count"] == 2
    assert merged["pair_count"] == 2
    assert merged["pairs"]["source_rows"].tolist() == [0, 1]
    assert [row["seed"] for row in merged["metadata"]] == [275000, 283000]
    assert merged["tensors"]["continuous"][:, 0].tolist() == [1.0, 3.0]


def test_merge_rejects_malformed_or_cross_partition_input() -> None:
    left = _corpus("fit", seed=275000, battle=3, value=1.0)
    bad = _corpus("fit", seed=283000, battle=3, value=3.0)
    bad["pairs"]["source_rows"][0] = 2
    with pytest.raises(ValueError, match="source row"):
        supplement.merge_successor_corpora("fit", left, bad)

    fresh = _corpus("fresh", seed=284000, battle=3, value=4.0)
    with pytest.raises(ValueError, match="partition"):
        supplement.merge_successor_corpora("fit", left, fresh)


def test_collected_slice_must_match_registered_seed_and_battle() -> None:
    valid = _corpus("fit", seed=283000, battle=3, value=1.0)
    supplement.validate_collected_slice(
        valid, slice_name="fit_battle_3", slices=supplement.FIXED_SLICES
    )

    wrong_battle = _corpus("fit", seed=283000, battle=10, value=1.0)
    with pytest.raises(ValueError, match="outside registered slice"):
        supplement.validate_collected_slice(
            wrong_battle,
            slice_name="fit_battle_3",
            slices=supplement.FIXED_SLICES,
        )


def test_merged_support_delegates_to_unchanged_base_gate(monkeypatch) -> None:
    corpora = {
        "fit": _corpus("fit", seed=275000, battle=3, value=1.0),
        "calibration": _corpus(
            "calibration", seed=275768, battle=3, value=2.0
        ),
        "fresh": _corpus("fresh", seed=277000, battle=10, value=3.0),
    }
    expected = {
        "gate": {
            "passed": False,
            "decision": "corpus_support_insufficient_close_without_fit",
        }
    }
    observed = {}

    def fake_support(values, paths):
        observed["corpora"] = values
        observed["paths"] = paths
        return expected

    monkeypatch.setattr(base, "_corpus_support_evidence", fake_support)
    assert supplement.evaluate_merged_support(corpora, {"sentinel": "path"}) is expected
    assert observed["corpora"] is corpora
    assert observed["paths"] == {"sentinel": "path"}


def test_report_decision_never_grants_fit_or_game_authority() -> None:
    support = {
        "gate": {
            "passed": True,
            "decision": "corpus_support_ready_for_separate_weighted_fit",
        }
    }
    report = supplement.build_report_payload(
        registration=supplement.build_registration("a" * 40, smoke=False),
        started={"started_unix": 1.0},
        support=support,
        partition_summaries={},
        merged_identities={},
        provenance={"test": True},
        elapsed_seconds=2.0,
    )
    assert report["decision"] == "merged_support_ready_for_separate_fit"
    assert report["authority"]["model_fitting"] is False
    assert report["authority"]["training"] is False
    assert report["authority"]["gameplay"] is False
    assert report["authority"]["communication_mod"] is False


def test_atomic_publication_roundtrips_corpora_and_hashes_manifest(tmp_path) -> None:
    corpora = {
        "fit": _corpus("fit", seed=275000, battle=3, value=1.0),
        "calibration": _corpus(
            "calibration", seed=275768, battle=3, value=2.0
        ),
        "fresh": _corpus("fresh", seed=277000, battle=10, value=3.0),
    }
    output = tmp_path / "published"
    supplement.publish_artifacts(
        output=output,
        corpora=corpora,
        report={"experiment_id": "test", "source_commit": "a" * 40},
        registration={"test": True},
        preflight={"test": True},
        started={"test": True},
        max_stored_bytes=8 * 1024 * 1024,
    )

    assert output.is_dir()
    manifest = json.loads((output / "manifest.json").read_text(encoding="ascii"))
    assert set(manifest["artifacts"]) >= {
        "fit_corpus.pt",
        "calibration_corpus.pt",
        "fresh_corpus.pt",
        "report.json",
    }
    for partition, expected in corpora.items():
        loaded = torch.load(
            output / f"{partition}_corpus.pt", map_location="cpu", weights_only=False
        )
        assert base.successor_corpus_identity(loaded) == base.successor_corpus_identity(
            expected
        )


def test_smoke_recipe_is_small_and_has_no_formal_evidence_authority() -> None:
    registration = supplement.build_registration("a" * 40, smoke=True)
    assert registration["smoke"] is True
    assert sum(
        value["seed_bounds"][1] - value["seed_bounds"][0] + 1
        for value in registration["recipe"]["slices"].values()
    ) == 16
    assert registration["authority"]["formal_evidence"] is False
    assert registration["authority"]["model_fitting"] is False


def test_post_start_failure_receipt_is_small_and_identity_scoped(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(supplement, "REPORTS_ROOT", tmp_path)
    registration_path = tmp_path / "registration.json"
    registration = {
        "experiment_id": "test-supplement-r1",
        "source_commit": "a" * 40,
        "output_dir": str(tmp_path / "output"),
        "authority": {"model_fitting": False, "gameplay": False},
    }
    registration_path.write_text(json.dumps(registration), encoding="ascii")
    (tmp_path / ".test-supplement-r1.started.json").write_text(
        json.dumps({"started_unix": 1.0}), encoding="ascii"
    )

    failure_path = supplement.record_started_failure(
        registration_path, RuntimeError("test failure")
    )
    assert failure_path == tmp_path / "test_supplement_r1_failure.json"
    failure = json.loads(failure_path.read_text(encoding="ascii"))
    assert failure["error_type"] == "RuntimeError"
    assert failure["output_exists"] is False
    assert failure["optimizer_constructed"] is False
