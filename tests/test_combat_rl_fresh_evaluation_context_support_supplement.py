from __future__ import annotations

import copy
from pathlib import Path

import pytest
import torch

from analysis_scripts import combat_rl_fresh_evaluation_context_support_supplement as fresh
from analysis_scripts import combat_rl_real_context_balanced_corpus as balanced


def _corpus(
    *,
    partition: str,
    floors: list[int],
    seeds: list[int],
    source_components: list[str] | None = None,
) -> dict:
    count = len(floors)
    assert len(seeds) == count
    positive = torch.tensor([row % 2 == 0 for row in range(count)])
    continuous = torch.zeros((count, 4), dtype=torch.float32)
    continuous[:, 0] = 0.5
    continuous[:, 3] = torch.tensor(floors, dtype=torch.float32) / 50.0
    metadata = []
    for row, (seed, floor) in enumerate(zip(seeds, floors, strict=True)):
        value = {
            "seed": seed,
            "floor": floor,
            "encounter": f"encounter-{row}",
            "guard_action_index": 1,
            "target_action_index": 2,
        }
        if source_components is not None:
            value["source_component"] = source_components[row]
        metadata.append(value)
    return {
        "partition": partition,
        "tensors": {
            "continuous": continuous,
            "card_ids": torch.zeros((count, 10), dtype=torch.long),
            "potion_ids": torch.zeros((count, 3), dtype=torch.long),
            "relic_ids": torch.ones((count, 8), dtype=torch.long),
            "action_masks": torch.ones((count, 6), dtype=torch.bool),
            "guard_actions": torch.ones(count, dtype=torch.long),
            "target_actions": torch.full((count,), 2, dtype=torch.long),
            "advantages": torch.where(positive, 1.0, -1.0),
            "positive": positive,
        },
        "metadata": metadata,
        "row_count": count,
    }


def test_fixed_recipe_is_evaluation_only_and_uses_fresh_early_mid_cohort() -> None:
    assert fresh.FIXED_RECIPE["evaluation_seed_first"] == 271000
    assert fresh.FIXED_RECIPE["evaluation_seed_last"] == 272023
    assert fresh.FIXED_RECIPE["battle_indices"] == [0, 3, 6, 9]
    assert fresh.FIXED_RECIPE["target_floor_first"] == 0
    assert fresh.FIXED_RECIPE["target_floor_last"] == 22
    assert fresh.FIXED_RECIPE["collect_training_partition"] is False
    assert fresh.FIXED_GATES == balanced.FIXED_GATES
    assert fresh.AUTHORITY["training"] is False
    assert fresh.AUTHORITY["gameplay"] is False


def test_filter_and_append_preserve_prior_metadata_and_tag_only_new_rows() -> None:
    prior = _corpus(
        partition="evaluation",
        floors=[12, 30],
        seeds=[266000, 270000],
        source_components=["expanded_base", "late_supplement"],
    )
    supplement = _corpus(
        partition="evaluation",
        floors=[0, 17, 22, 23],
        seeds=[271000, 271001, 271002, 271003],
    )
    prior_before = copy.deepcopy(prior["metadata"])

    filtered, exclusions = fresh.filter_evaluation_supplement(supplement)
    combined = fresh.append_evaluation_corpus(prior, filtered)

    assert exclusions == {"above_target_floor": 1}
    assert prior["metadata"] == prior_before
    assert combined["row_count"] == 5
    assert combined["metadata"][:2] == prior_before
    assert [row["source_component"] for row in combined["metadata"][2:]] == [
        "early_mid_fresh_evaluation_supplement",
        "early_mid_fresh_evaluation_supplement",
        "early_mid_fresh_evaluation_supplement",
    ]
    assert [row["floor"] for row in combined["metadata"]] == [12, 30, 0, 17, 22]


def test_append_rejects_source_tagged_or_dimension_incompatible_rows() -> None:
    prior = _corpus(
        partition="evaluation",
        floors=[12, 30],
        seeds=[266000, 270000],
        source_components=["expanded_base", "late_supplement"],
    )
    tagged = _corpus(
        partition="evaluation",
        floors=[17, 18],
        seeds=[271000, 271001],
        source_components=["unexpected", "unexpected"],
    )
    with pytest.raises(ValueError, match="source_component"):
        fresh.append_evaluation_corpus(prior, tagged)

    incompatible = _corpus(
        partition="evaluation", floors=[17, 18], seeds=[271000, 271001]
    )
    incompatible["tensors"]["card_ids"] = torch.zeros((2, 11), dtype=torch.long)
    with pytest.raises(ValueError, match="shape differs"):
        fresh.append_evaluation_corpus(prior, incompatible)


def test_seed_isolation_rejects_prior_or_cross_partition_overlap() -> None:
    fresh.validate_fresh_seed_isolation(
        prior_train_seeds=[264000, 268000],
        prior_evaluation_seeds=[266000, 270000],
        fresh_evaluation_seeds=[271000, 271001],
    )
    with pytest.raises(ValueError, match="seed partitions overlap"):
        fresh.validate_fresh_seed_isolation(
            prior_train_seeds=[264000],
            prior_evaluation_seeds=[266000, 271000],
            fresh_evaluation_seeds=[271000, 271001],
        )


def test_copy_verified_file_preserves_exact_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.pt"
    target = tmp_path / "nested" / "train_corpus.pt"
    source.write_bytes(b"exact training corpus bytes\x00\x01")
    expected = fresh.sha256_file(source)

    evidence = fresh.copy_verified_file(source, target, expected_sha256=expected)

    assert target.read_bytes() == source.read_bytes()
    assert evidence == {"sha256": expected, "size_bytes": source.stat().st_size}


def test_registration_binds_prior_publication_and_reuses_gate_implementation() -> None:
    registration = fresh.build_registration("a" * 40)
    normalized = fresh.validate_registration(registration)

    assert normalized["recipe"] == fresh.FIXED_RECIPE
    assert normalized["gates"] == balanced.FIXED_GATES
    assert {
        "prior_train_corpus",
        "prior_evaluation_corpus",
        "prior_context_weights",
        "prior_report",
        "prior_manifest",
    }.issubset(normalized["inputs"])
    assert fresh.derive_context_weights is balanced.derive_context_weights
    assert fresh.apply_support_gates is balanced.apply_support_gates


@pytest.mark.parametrize("mutation", ["recipe", "gate", "input", "authority"])
def test_registration_rejects_any_bound_drift(mutation: str) -> None:
    registration = fresh.build_registration("a" * 40)
    if mutation == "recipe":
        registration["recipe"]["battle_indices"] = [0, 3]
    elif mutation == "gate":
        registration["gates"]["real_context_mass_covered_minimum"] = 0.80
    elif mutation == "input":
        registration["inputs"]["prior_evaluation_corpus"]["sha256"] = "0" * 64
    else:
        registration["authority"]["training"] = True
    with pytest.raises(ValueError, match="differ"):
        fresh.validate_registration(registration)
