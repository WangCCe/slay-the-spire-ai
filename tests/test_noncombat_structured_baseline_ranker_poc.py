from __future__ import annotations

import copy
import gzip
import json
import os
from pathlib import Path

import pytest

from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    TARGET_CATEGORIES,
    build_transition,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.noncombat_simulator_baseline_warm_start import (
    DEMONSTRATION_ARTIFACT_SCHEMA_VERSION,
    build_demonstration_dataset,
    build_demonstration_row,
)
from analysis_scripts.noncombat_structured_baseline_ranker_poc import (
    ARCHIVE_MANIFEST_SCHEMA_VERSION,
    FOLD_RULE,
    LEGACY_CANDIDATE_ID,
    MANIFEST_SCHEMA_VERSION,
    REGISTERED_SOURCE_FILES,
    REGISTERED_TRAIN_SEEDS,
    REGISTRATION_SCHEMA_VERSION,
    STRUCTURED_CANDIDATE_ID,
    STRUCTURED_FEATURE_VERSION,
    TIE_RULE,
    StructuredPocBlocked,
    build_artifacts,
    build_seed_folds,
    build_structured_model,
    build_train_input,
    canonical_model_payload,
    compare_candidates,
    feature_collision_diagnostics,
    load_model_payload,
    load_preserved_demonstrations,
    load_train_input_archive,
    metrics_from_predictions,
    prepare_rows,
    publish_artifacts,
    run_candidate_cross_validation,
    singleton_summary,
    structured_candidate_features,
    structured_feature_map,
    train_candidate_model,
    validate_artifact_directory,
    validate_artifact_payloads,
    validate_registration,
    validate_train_dataset,
    validate_train_input,
    write_train_input_archive,
)


FAKE_PROVENANCE = {
    "adapter_commit": "1" * 40,
    "adapter_source_sha256": "2" * 64,
    "build": {
        "adapter_api_version": ADAPTER_API_VERSION,
        "compiler": "test",
        "cpp_standard": 201703,
        "python": "3.10.18",
    },
    "module_sha256": "3" * 64,
    "simulator_commit": "4" * 40,
    "simulator_source_sha256": "5" * 64,
    "submodules": {"json": "6" * 40, "pybind11": "7" * 40},
}


def _binding(path: str) -> dict[str, object]:
    return {"path": path, "sha256": "a" * 64, "size_bytes": 1}


def _valid_registration() -> dict[str, object]:
    import torch

    return {
        "authority": {
            "dagger": False,
            "formal_noncombat_rl": False,
            "live_gameplay": False,
            "live_policy_loading": False,
            "native_evidence_collection": False,
            "ope_reinterpretation": False,
            "policy_promotion": False,
            "qualification": False,
            "simulator_rollout": False,
        },
        "identity": {
            "implementation": {
                "commit": "b" * 40,
                "source_files": list(REGISTERED_SOURCE_FILES),
                "source_sha256": "c" * 64,
            },
            "runtime": {
                "python": ".".join(map(str, __import__("sys").version_info[:3])),
                "torch": str(torch.__version__),
            },
            "source_archive": _binding("reports/source.json.gz"),
            "source_archive_manifest": _binding("reports/source-manifest.json"),
            "source_warm_start_manifest": _binding("reports/warm-manifest.json"),
            "teacher_policy_id": NATIVE_TARGET_POLICY_ID,
            "train_dataset_sha256": "d" * 64,
            "train_input": _binding("reports/train.json.gz"),
            "train_input_manifest": _binding("reports/train-manifest.json"),
        },
        "poc": {
            "candidates": {
                "control": {
                    "architecture": "shared-mlp-v1",
                    "feature_version": "noncombat-simulator-policy-features-v1",
                    "hash_dim": 1024,
                    "hidden_dim": 128,
                    "id": LEGACY_CANDIDATE_ID,
                },
                "structured": {
                    "architecture": "category-specific-mlp-v1",
                    "feature_version": STRUCTURED_FEATURE_VERSION,
                    "hash_dim": 2048,
                    "hidden_dim": 64,
                    "id": STRUCTURED_CANDIDATE_ID,
                },
            },
            "evaluation": {
                "primary_metric": "seed_grouped_heldout_multicandidate_action_agreement",
                "singleton_treatment": "report_only_excluded_from_fit_and_gate",
                "thresholds": {
                    "maximum_mean_cross_entropy_delta": 0.0,
                    "minimum_card_reward_agreement_delta": 0.0,
                    "minimum_macro_agreement_delta": 0.03,
                    "minimum_overall_agreement_delta": 0.03,
                    "minimum_route_agreement_delta": 0.0,
                },
            },
            "folds": {"count": 4, "rule": FOLD_RULE},
            "limits": {
                "max_candidates_per_row": 32,
                "max_model_fits_per_execution": 9,
                "max_rows": 1500,
                "max_wall_seconds_per_execution": 900.0,
            },
            "optimizer": {
                "algorithm": "adam",
                "beta1": 0.9,
                "beta2": 0.999,
                "category_balanced": True,
                "deterministic_order": True,
                "epochs": 20,
                "epsilon": 1e-8,
                "learning_rate": 0.001,
                "model_seed": 0,
                "multi_candidate_only": True,
                "torch_num_threads": 1,
                "weight_decay": 0.0,
            },
            "seeds": list(REGISTERED_TRAIN_SEEDS),
            "tie_rule": TIE_RULE,
        },
        "schema_version": REGISTRATION_SCHEMA_VERSION,
    }


def _map_nodes() -> list[dict[str, object]]:
    return [
        {
            "edges": [{"x": 0, "y": 1}],
            "room": "MONSTER",
            "symbol": "M",
            "x": 0,
            "y": 0,
        },
        {
            "edges": [{"x": 1, "y": 1}],
            "room": "SHOP",
            "symbol": "$",
            "x": 1,
            "y": 0,
        },
        {
            "edges": [{"x": 0, "y": 2}],
            "room": "ELITE",
            "symbol": "E",
            "x": 0,
            "y": 1,
        },
        {
            "edges": [{"x": 0, "y": 2}],
            "room": "REST",
            "symbol": "R",
            "x": 1,
            "y": 1,
        },
        {
            "edges": [],
            "room": "MONSTER",
            "symbol": "M",
            "x": 0,
            "y": 2,
        },
    ]


def _state(category: str, seed: int) -> dict[str, object]:
    context: dict[str, object] = {}
    if category == "card_reward":
        context = {
            "cards": [
                {"id": "ANGER", "name": "Anger", "slot": 0, "upgraded": False, "upgrade_count": 0, "misc": 0},
                {"id": "SHRUG_IT_OFF", "name": "Shrug It Off", "slot": 1, "upgraded": False, "upgrade_count": 0, "misc": 0},
            ],
            "has_singing_bowl": False,
            "reward_index": 0,
        }
    elif category == "shop":
        context = {"cards": [], "potions": [], "relics": [], "remove_cost": 75}
    elif category == "event":
        context = {"event_data": seed % 3, "event_id": "BIG_FISH", "event_name": "Big Fish"}
    return {
        "act": 1,
        "ascension": 0,
        "blue_key": False,
        "boss": "THE_GUARDIAN",
        "cur_hp": 50 + seed % 10,
        "cur_map_node": {"x": 0, "y": -1},
        "cur_room": "NONE",
        "decision_context": context,
        "deck": [
            {"id": "STRIKE_RED", "name": "Strike", "slot": 0, "upgraded": False, "upgrade_count": 0, "misc": 0},
            {"id": "DEFEND_RED", "name": "Defend", "slot": 1, "upgraded": seed % 2 == 0, "upgrade_count": int(seed % 2 == 0), "misc": 0},
        ],
        "encounter": "INVALID",
        "floor": 0,
        "gold": 90 + seed % 20,
        "green_key": False,
        "map": {
            "burning_elite": {"buff": 0, "x": 0, "y": 1},
            "nodes": _map_nodes(),
        },
        "max_hp": 80,
        "outcome": "undecided",
        "potions": [{"id": "EMPTY", "name": "Empty", "slot": 0}],
        "red_key": False,
        "relics": [{"data": 0, "id": "BURNING_BLOOD", "name": "Burning Blood"}],
        "screen_state": category.upper(),
        "seed": str(seed),
    }


def _candidates(category: str) -> list[dict[str, object]]:
    if category == "route":
        values = [
            ("route:map_node:0:0", "M@0,0", "MONSTER", 0),
            ("route:map_node:1:0", "$@1,0", "SHOP", 1),
        ]
        return [
            {
                "action_id": action_id,
                "available": True,
                "category": category,
                "kind": "map_node",
                "label": label,
                "raw": {"idx1": x, "idx2": 0, "room": room, "x": x, "y": 0},
            }
            for action_id, label, room, x in values
        ]
    if category == "card_reward":
        values = [("ANGER", "Anger"), ("SHRUG_IT_OFF", "Shrug It Off")]
        return [
            {
                "action_id": f"card_reward:take:0:{index}:{identity.lower()}",
                "available": True,
                "category": category,
                "kind": "take",
                "label": name,
                "raw": {"id": identity, "misc": 0, "name": name, "reward_index": 0, "slot": index, "upgrade_count": 0, "upgraded": False},
            }
            for index, (identity, name) in enumerate(values)
        ]
    if category == "shop":
        return [
            {
                "action_id": "shop:buy_card:0:anger",
                "available": True,
                "category": category,
                "kind": "buy_card",
                "label": "Anger",
                "raw": {"id": "ANGER", "name": "Anger", "price": 45, "slot": 0, "upgrade_count": 0, "upgraded": False},
            },
            {
                "action_id": "shop:leave",
                "available": True,
                "category": category,
                "kind": "leave",
                "label": "leave",
                "raw": {"idx1": 0, "idx2": 0},
            },
        ]
    return [
        {
            "action_id": f"event:big_fish:option:{index}",
            "available": True,
            "category": category,
            "kind": "event_option",
            "label": f"Big Fish option {index}",
            "raw": {"event_id": "BIG_FISH", "idx1": index, "idx2": 0},
        }
        for index in range(2)
    ]


def _snapshot(category: str, state: dict[str, object], *, terminal: bool = False):
    return {
        "adapter_api_version": ADAPTER_API_VERSION,
        "baseline_control": {"history": [], "policy_id": "test-baseline"},
        "category": None if terminal else category,
        "decision_count": int(terminal),
        "schema_version": STATE_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "state": state,
        "terminal": terminal,
    }


def _dataset(seeds=tuple(range(8))):
    rows = []
    episodes = []
    for seed in seeds:
        seed_rows = []
        for decision_index, category in enumerate(TARGET_CATEGORIES):
            state = _state(category, seed)
            candidates = _candidates(category)
            target = candidates[(seed + decision_index) % 2]
            after_state = copy.deepcopy(state)
            after_state["outcome"] = "player_loss"
            after_state["floor"] = 1
            transition = build_transition(
                before=_snapshot(category, state),
                candidates=candidates,
                selected_action_id=target["action_id"],
                after=_snapshot(category, after_state, terminal=True),
                provenance=FAKE_PROVENANCE,
            )
            row = build_demonstration_row(
                cohort="train",
                seed=seed,
                decision_index=decision_index,
                source_snapshot=_snapshot(category, state),
                candidates=candidates,
                target_action={
                    "action_id": target["action_id"],
                    "category": category,
                    "policy_id": NATIVE_TARGET_POLICY_ID,
                    "schema_version": NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
                },
                transition=transition,
            )
            rows.append(row)
            seed_rows.append(row)
        episodes.append(
            {
                "action_sequence_sha256": sha256_bytes(
                    canonical_json_bytes([row["teacher"]["action_id"] for row in seed_rows])
                ),
                "categories": list(TARGET_CATEGORIES),
                "decisions": len(seed_rows),
                "outcome": "player_loss",
                "row_sha256s": [sha256_bytes(canonical_json_bytes(row)) for row in seed_rows],
                "seed": seed,
                "selected_action_ids": [row["teacher"]["action_id"] for row in seed_rows],
                "terminal_floor": 1.0,
            }
        )
    return build_demonstration_dataset(
        cohort="train",
        seeds=seeds,
        rows=rows,
        episodes=episodes,
    )


def _source_artifact(dataset):
    return {
        "datasets": {"final_test": None, "train": dataset, "validation": {"never": "used"}},
        "registration_sha256": "e" * 64,
        "schema_version": DEMONSTRATION_ARTIFACT_SCHEMA_VERSION,
    }


def _archive_manifest(raw: bytes) -> dict[str, object]:
    return {
        "compression": {"format": "gzip", "level": 9, "mtime": 0, "original_name": "demonstrations.json"},
        "gzip_path": "reports/source.json.gz",
        "gzip_sha256": "0" * 64,
        "gzip_size_bytes": 1,
        "raw_path": "reports/source.json",
        "raw_sha256": sha256_bytes(raw),
        "raw_size_bytes": len(raw),
        "registration_sha256": "e" * 64,
        "schema_version": ARCHIVE_MANIFEST_SCHEMA_VERSION,
    }


def test_registration_is_exact_and_fails_closed():
    registration = _valid_registration()
    before = copy.deepcopy(registration)

    assert validate_registration(registration) == before
    assert registration == before

    invalid = copy.deepcopy(registration)
    invalid["poc"]["seeds"][-1] = 5000
    with pytest.raises(StructuredPocBlocked, match="4000..4031"):
        validate_registration(invalid)

    invalid = copy.deepcopy(registration)
    invalid["authority"]["formal_noncombat_rl"] = True
    with pytest.raises(StructuredPocBlocked, match="authority"):
        validate_registration(invalid)


def test_train_input_excludes_other_cohorts_and_round_trips_gzip(tmp_path):
    dataset = _dataset()
    source = _source_artifact(dataset)
    raw = canonical_json_bytes(source)
    train_input = build_train_input(
        demonstrations_artifact=source,
        archive_manifest=_archive_manifest(raw),
        expected_seeds=tuple(range(8)),
    )

    assert set(train_input) == {"dataset", "schema_version", "source"}
    assert "validation" not in canonical_json_bytes(train_input).decode("utf-8")
    output = tmp_path / "train.json.gz"
    manifest = tmp_path / "train-manifest.json"
    write_train_input_archive(
        train_input,
        output_path=output,
        manifest_path=manifest,
        expected_seeds=tuple(range(8)),
    )
    loaded = load_train_input_archive(
        output,
        manifest_path=manifest,
        expected_seeds=tuple(range(8)),
    )
    assert canonical_json_bytes(loaded) == canonical_json_bytes(train_input)

    invalid = copy.deepcopy(train_input)
    invalid["dataset"]["cohort"] = "validation"
    with pytest.raises(StructuredPocBlocked, match="cohort"):
        validate_train_input(invalid, expected_seeds=tuple(range(8)))


def test_preserved_source_loader_accepts_matching_raw_and_gzip(tmp_path):
    source = _source_artifact(_dataset())
    raw = canonical_json_bytes(source)
    raw_path = tmp_path / "source.json"
    gzip_path = tmp_path / "source.json.gz"
    manifest_path = tmp_path / "manifest.json"
    raw_path.write_bytes(raw)
    with gzip.GzipFile(filename="", mode="wb", fileobj=gzip_path.open("wb"), mtime=0) as handle:
        handle.write(raw)
    manifest = _archive_manifest(raw)
    manifest["gzip_sha256"] = sha256_file(gzip_path)
    manifest["gzip_size_bytes"] = gzip_path.stat().st_size
    manifest_path.write_bytes(canonical_json_bytes(manifest))

    loaded_raw, _ = load_preserved_demonstrations(
        raw_path, archive_manifest_path=manifest_path
    )
    loaded_gzip, _ = load_preserved_demonstrations(
        gzip_path, archive_manifest_path=manifest_path
    )
    assert canonical_json_bytes(loaded_raw) == raw
    assert canonical_json_bytes(loaded_gzip) == raw


def test_structured_features_are_collection_order_and_leakage_invariant():
    state = _state("route", 1)
    candidate = _candidates("route")[0]
    original = structured_feature_map(state, candidate, category="route")
    reordered = copy.deepcopy(state)
    for field in ("deck", "relics", "potions"):
        reordered[field] = list(reversed(reordered[field]))
    reordered["map"]["nodes"] = list(reversed(reordered["map"]["nodes"]))
    for node in reordered["map"]["nodes"]:
        node["edges"] = list(reversed(node["edges"]))
    reordered["seed"] = "different"
    reordered["outcome"] = "player_victory"

    assert structured_feature_map(reordered, candidate, category="route") == original


def test_each_category_has_candidate_relative_features():
    expected_prefix = {
        "card_reward": "card_reward.deck_duplicate_count",
        "event": "event.option_index",
        "route": "route.suffix.path_count",
        "shop": "shop.affordable=",
    }
    for category, prefix in expected_prefix.items():
        candidates = _candidates(category)
        first = structured_feature_map(_state(category, 0), candidates[0], category=category)
        second = structured_feature_map(_state(category, 0), candidates[1], category=category)
        assert first != second
        assert any(key.startswith(prefix) for key in first)


def test_structured_vectors_preserve_complete_candidate_order_and_report_collisions():
    candidates = _candidates("card_reward")
    vectors, keys = structured_candidate_features(
        _state("card_reward", 0), candidates, category="card_reward", hash_dim=64
    )
    diagnostics = feature_collision_diagnostics(keys, hash_dim=64)

    assert list(vectors.shape) == [2, 64]
    assert len(keys) == len(candidates)
    assert diagnostics["unique_feature_count"] > 0
    assert diagnostics["occupied_bin_count"] <= 64

    invalid = copy.deepcopy(candidates)
    invalid[1]["action_id"] = invalid[0]["action_id"]
    with pytest.raises(StructuredPocBlocked, match="duplicate candidate"):
        structured_candidate_features(
            _state("card_reward", 0),
            invalid,
            category="card_reward",
            hash_dim=64,
        )


def test_structured_model_round_trip_is_exact():
    candidate = {
        "architecture": "category-specific-mlp-v1",
        "feature_version": STRUCTURED_FEATURE_VERSION,
        "hash_dim": 32,
        "hidden_dim": 8,
        "id": STRUCTURED_CANDIDATE_ID,
    }
    model = build_structured_model(hash_dim=32, hidden_dim=8, model_seed=7)
    payload = canonical_model_payload(model, candidate=candidate)
    loaded = load_model_payload(payload, candidate=candidate, model_seed=7)

    assert canonical_model_payload(loaded, candidate=candidate) == payload
    tampered = copy.deepcopy(payload)
    first_name = sorted(tampered["tensors"])[0]
    tampered["tensors"][first_name]["values"][0] = "nan"
    with pytest.raises(StructuredPocBlocked, match="non-finite"):
        load_model_payload(tampered, candidate=candidate, model_seed=7)


def test_seed_folds_are_grouped_exhaustive_and_deterministic():
    folds = build_seed_folds(tuple(range(8)), fold_count=4)

    assert folds == build_seed_folds(tuple(range(8)), fold_count=4)
    assert [fold["heldout_seeds"] for fold in folds] == [[0, 4], [1, 5], [2, 6], [3, 7]]
    assert set().union(*(set(fold["heldout_seeds"]) for fold in folds)) == set(range(8))
    assert all(not set(fold["fit_seeds"]) & set(fold["heldout_seeds"]) for fold in folds)


def test_training_uses_only_multi_candidate_rows_and_is_deterministic():
    dataset = _dataset()
    candidate = {
        "architecture": "category-specific-mlp-v1",
        "feature_version": STRUCTURED_FEATURE_VERSION,
        "hash_dim": 64,
        "hidden_dim": 8,
        "id": STRUCTURED_CANDIDATE_ID,
    }
    rows = prepare_rows(dataset, candidate=candidate)
    optimizer = {
        "algorithm": "adam",
        "beta1": 0.9,
        "beta2": 0.999,
        "category_balanced": True,
        "deterministic_order": True,
        "epochs": 2,
        "epsilon": 1e-8,
        "learning_rate": 0.001,
        "model_seed": 0,
        "multi_candidate_only": True,
        "torch_num_threads": 1,
        "weight_decay": 0.0,
    }
    _, first = train_candidate_model(rows, candidate=candidate, optimizer_config=optimizer)
    _, second = train_candidate_model(rows, candidate=candidate, optimizer_config=optimizer)

    assert first == second
    assert first["row_count"] == 32

    singleton_dataset = copy.deepcopy(dataset)
    singleton_dataset["rows"][0]["candidate_actions"] = singleton_dataset["rows"][0]["candidate_actions"][:1]
    singleton_dataset["rows"][0]["teacher"]["action_id"] = singleton_dataset["rows"][0]["candidate_actions"][0]["action_id"]
    assert singleton_summary(singleton_dataset)["row_count"] == 1


def test_cross_validation_scores_each_seed_only_in_its_heldout_fold():
    dataset = _dataset()
    candidate = {
        "architecture": "category-specific-mlp-v1",
        "feature_version": STRUCTURED_FEATURE_VERSION,
        "hash_dim": 64,
        "hidden_dim": 8,
        "id": STRUCTURED_CANDIDATE_ID,
    }
    optimizer = {
        "algorithm": "adam",
        "beta1": 0.9,
        "beta2": 0.999,
        "category_balanced": True,
        "deterministic_order": True,
        "epochs": 1,
        "epsilon": 1e-8,
        "learning_rate": 0.001,
        "model_seed": 0,
        "multi_candidate_only": True,
        "torch_num_threads": 1,
        "weight_decay": 0.0,
    }
    rows = prepare_rows(dataset, candidate=candidate)
    folds = build_seed_folds(tuple(range(8)), fold_count=4)

    result = run_candidate_cross_validation(
        rows,
        candidate=candidate,
        folds=folds,
        optimizer_config=optimizer,
        deadline=100.0,
        clock=lambda: 0.0,
    )

    assert result["metrics"]["row_count"] == len(rows)
    assert len(result["predictions"]) == len(rows)
    assert len({(row["seed"], row["decision_index"]) for row in result["predictions"]}) == len(rows)
    expected_fold = {seed: index % 4 for index, seed in enumerate(range(8))}
    assert all(row["fold"] == expected_fold[row["seed"]] for row in result["predictions"])


def _metrics(agreement: float, cross_entropy: float) -> dict[str, object]:
    by_category = {
        category: {"action_agreement": agreement, "mean_cross_entropy": cross_entropy, "row_count": 2}
        for category in TARGET_CATEGORIES
    }
    return {
        "by_category": by_category,
        "macro_category_action_agreement": agreement,
        "macro_category_mean_cross_entropy": cross_entropy,
        "overall_action_agreement": agreement,
        "overall_mean_cross_entropy": cross_entropy,
        "row_count": 8,
    }


def test_candidate_gate_distinguishes_positive_and_valid_negative():
    thresholds = _valid_registration()["poc"]["evaluation"]["thresholds"]
    positive = compare_candidates(
        control={"metrics": _metrics(0.50, 0.9)},
        structured={"metrics": _metrics(0.60, 0.7)},
        thresholds=thresholds,
    )
    negative = compare_candidates(
        control={"metrics": _metrics(0.60, 0.7)},
        structured={"metrics": _metrics(0.61, 0.8)},
        thresholds=thresholds,
    )

    assert positive["verdict"] == "structured_candidate_selected"
    assert positive["selected_candidate_id"] == STRUCTURED_CANDIDATE_ID
    assert negative["verdict"] == "poc_valid_without_structured_candidate"
    assert negative["selected_candidate_id"] is None


def _negative_execution():
    comparison = compare_candidates(
        control={"metrics": _metrics(0.60, 0.7)},
        structured={"metrics": _metrics(0.61, 0.8)},
        thresholds=_valid_registration()["poc"]["evaluation"]["thresholds"],
    )
    candidate_results = {}
    for name, metrics in (("control", _metrics(0.60, 0.7)), ("structured", _metrics(0.61, 0.8))):
        candidate_results[name] = {
            "candidate_id": name,
            "folds": [{"model_sha256": str(index) * 64} for index in range(1, 5)],
            "metrics": metrics,
            "predictions": [],
        }
    return {
        "candidate_results": candidate_results,
        "comparison": comparison,
        "feature_collision_diagnostics": {
            "collided_bin_count": 1,
            "collision_count": 1,
            "collision_fraction": 0.1,
            "hash_dim": 2048,
            "occupied_bin_count": 9,
            "unique_feature_count": 10,
        },
        "fit_count": 8,
        "folds": list(build_seed_folds(REGISTERED_TRAIN_SEEDS, fold_count=4)),
        "schema_version": "noncombat-structured-baseline-ranker-execution-v1",
        "selected_model": None,
        "selected_model_sha256": None,
        "selected_training": None,
        "singleton_summary": {
            "by_category": {category: 1 for category in TARGET_CATEGORIES},
            "excluded_from_competence_metrics": True,
            "row_count": 4,
            "total_by_category": {category: 3 for category in TARGET_CATEGORIES},
            "total_row_count": 12,
        },
        "train_dataset_sha256": "d" * 64,
    }


def test_artifacts_are_hash_closed_atomic_and_no_authority(tmp_path):
    registration = _valid_registration()
    execution = _negative_execution()
    artifacts = build_artifacts(
        registration=registration, primary=execution, replay=copy.deepcopy(execution)
    )

    manifest = validate_artifact_payloads(artifacts)
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["verdict"] == "poc_valid_without_structured_candidate"
    assert not any(manifest["authority"].values())
    publish_artifacts(tmp_path, artifacts)
    assert validate_artifact_directory(tmp_path) == manifest

    tampered = dict(artifacts)
    tampered["metrics.json"] += b" "
    with pytest.raises(StructuredPocBlocked, match="hash closure"):
        validate_artifact_payloads(tampered)
