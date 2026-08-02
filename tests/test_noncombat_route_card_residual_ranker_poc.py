from __future__ import annotations

import copy
import json

import pytest

from analysis_scripts.noncombat_route_card_residual_ranker_poc import (
    COMPOSITE_MODEL_SCHEMA_VERSION,
    CONTROL_CANDIDATE_ID,
    DELEGATED_CATEGORIES,
    MANIFEST_SCHEMA_VERSION,
    REGISTERED_SOURCE_FILES,
    REGISTRATION_SCHEMA_VERSION,
    RESIDUAL_CANDIDATE_ID,
    RESIDUAL_CATEGORIES,
    RESIDUAL_FEATURE_VERSION,
    ResidualPocBlocked,
    _authority,
    _registered_thresholds,
    build_artifacts,
    canonical_composite_model_payload,
    build_residual_model,
    canonical_residual_model_payload,
    compare_paired_result,
    evaluate_paired_models,
    execute_poc,
    load_composite_model_payload,
    load_residual_model_payload,
    prepare_paired_rows,
    publish_artifacts,
    train_residual_model,
    validate_artifact_directory,
    validate_artifact_payloads,
    validate_registration,
)
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
)
from analysis_scripts.noncombat_simulator_baseline_warm_start import (
    DEMONSTRATION_ARTIFACT_SCHEMA_VERSION,
    build_warm_start_model,
    build_demonstration_dataset,
    build_demonstration_row,
    canonical_warm_start_model_payload,
)
from analysis_scripts.noncombat_structured_baseline_ranker_poc import (
    ARCHIVE_MANIFEST_SCHEMA_VERSION,
    FOLD_RULE,
    REGISTERED_TRAIN_SEEDS,
    TIE_RULE,
    build_train_input,
    train_candidate_model,
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


def _optimizer(epochs: int = 20) -> dict[str, object]:
    return {
        "algorithm": "adam",
        "beta1": 0.9,
        "beta2": 0.999,
        "category_balanced": True,
        "deterministic_order": True,
        "epochs": epochs,
        "epsilon": 1e-8,
        "learning_rate": 0.001,
        "model_seed": 0,
        "multi_candidate_only": True,
        "torch_num_threads": 1,
        "weight_decay": 0.0,
    }


def _control_candidate(hash_dim: int = 1024, hidden_dim: int = 128):
    return {
        "architecture": "shared-mlp-v1",
        "feature_version": "noncombat-simulator-policy-features-v1",
        "hash_dim": hash_dim,
        "hidden_dim": hidden_dim,
        "id": CONTROL_CANDIDATE_ID,
    }


def _residual_candidate(hash_dim: int = 2048, hidden_dim: int = 32):
    return {
        "architecture": "legacy-plus-two-head-bounded-residual-v1",
        "base_candidate_id": CONTROL_CANDIDATE_ID,
        "composition": "base-logit-plus-tanh-residual-v1",
        "feature_version": RESIDUAL_FEATURE_VERSION,
        "hash_dim": hash_dim,
        "hidden_dim": hidden_dim,
        "id": RESIDUAL_CANDIDATE_ID,
        "initialization": "zero-output-layer-v1",
        "residual_categories": list(RESIDUAL_CATEGORIES),
        "residual_scale": 1.0,
    }


def _valid_registration(train_dataset_sha256: str = "d" * 64):
    import torch

    return {
        "authority": _authority(),
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
            "structured_poc_failure_audit": _binding("reports/failure-audit.md"),
            "structured_poc_manifest": _binding("reports/structured/artifact_manifest.json"),
            "structured_poc_verdict": "poc_valid_without_structured_candidate",
            "teacher_policy_id": NATIVE_TARGET_POLICY_ID,
            "train_dataset_sha256": train_dataset_sha256,
            "train_input": _binding("reports/train.json.gz"),
            "train_input_manifest": _binding("reports/train-manifest.json"),
        },
        "poc": {
            "candidates": {
                "control": _control_candidate(),
                "residual": _residual_candidate(),
            },
            "evaluation": {
                "primary_metric": "seed_grouped_heldout_multicandidate_action_agreement",
                "singleton_treatment": "report_only_excluded_from_fit_and_gate",
                "thresholds": _registered_thresholds(),
            },
            "folds": {"count": 4, "rule": FOLD_RULE},
            "limits": {
                "max_candidates_per_row": 32,
                "max_model_fits_per_execution": 10,
                "max_rows": 1500,
                "max_wall_seconds_per_execution": 900.0,
            },
            "optimizers": {"base": _optimizer(), "residual": _optimizer()},
            "seeds": list(REGISTERED_TRAIN_SEEDS),
            "tie_rule": TIE_RULE,
        },
        "schema_version": REGISTRATION_SCHEMA_VERSION,
    }


def _map_nodes() -> list[dict[str, object]]:
    return [
        {"edges": [{"x": 0, "y": 1}], "room": "MONSTER", "symbol": "M", "x": 0, "y": 0},
        {"edges": [{"x": 1, "y": 1}], "room": "SHOP", "symbol": "$", "x": 1, "y": 0},
        {"edges": [{"x": 0, "y": 2}], "room": "ELITE", "symbol": "E", "x": 0, "y": 1},
        {"edges": [{"x": 0, "y": 2}], "room": "REST", "symbol": "R", "x": 1, "y": 1},
        {"edges": [], "room": "MONSTER", "symbol": "M", "x": 0, "y": 2},
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
        "map": {"burning_elite": {"buff": 0, "x": 0, "y": 1}, "nodes": _map_nodes()},
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
        return [
            {
                "action_id": f"route:map_node:{x}:0",
                "available": True,
                "category": category,
                "kind": "map_node",
                "label": f"{room}@{x},0",
                "raw": {"idx1": x, "idx2": 0, "room": room_name, "x": x, "y": 0},
            }
            for x, room, room_name in ((0, "M", "MONSTER"), (1, "$", "SHOP"))
        ]
    if category == "card_reward":
        values = (("ANGER", "Anger"), ("SHRUG_IT_OFF", "Shrug It Off"))
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


def _dataset(seeds: tuple[int, ...]):
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
                "action_sequence_sha256": sha256_bytes(canonical_json_bytes([row["teacher"]["action_id"] for row in seed_rows])),
                "categories": list(TARGET_CATEGORIES),
                "decisions": len(seed_rows),
                "outcome": "player_loss",
                "row_sha256s": [sha256_bytes(canonical_json_bytes(row)) for row in seed_rows],
                "seed": seed,
                "selected_action_ids": [row["teacher"]["action_id"] for row in seed_rows],
                "terminal_floor": 1.0,
            }
        )
    return build_demonstration_dataset(cohort="train", seeds=seeds, rows=rows, episodes=episodes)


def _train_input(seeds: tuple[int, ...]):
    dataset = _dataset(seeds)
    source = {
        "datasets": {"final_test": None, "train": dataset, "validation": {"never": "used"}},
        "registration_sha256": "e" * 64,
        "schema_version": DEMONSTRATION_ARTIFACT_SCHEMA_VERSION,
    }
    raw = canonical_json_bytes(source)
    archive = {
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
    return build_train_input(
        demonstrations_artifact=source,
        archive_manifest=archive,
        expected_seeds=seeds,
    )


def test_registration_is_exact_and_fails_closed():
    registration = _valid_registration()
    before = copy.deepcopy(registration)

    assert validate_registration(registration) == before
    assert registration == before

    invalid = copy.deepcopy(registration)
    invalid["poc"]["seeds"][-1] = 5000
    with pytest.raises(ResidualPocBlocked, match="4000..4031"):
        validate_registration(invalid)

    invalid = copy.deepcopy(registration)
    invalid["authority"]["formal_noncombat_rl"] = True
    with pytest.raises(ResidualPocBlocked, match="authority"):
        validate_registration(invalid)

    invalid = copy.deepcopy(registration)
    invalid["poc"]["evaluation"]["thresholds"]["minimum_overall_agreement_delta"] = 0.0
    with pytest.raises(ResidualPocBlocked, match="thresholds"):
        validate_registration(invalid)


def test_residual_model_starts_at_zero_is_bounded_and_round_trips():
    import torch

    candidate = _residual_candidate(hash_dim=32, hidden_dim=8)
    model = build_residual_model(hash_dim=32, hidden_dim=8, model_seed=0, residual_scale=1.0)
    features = torch.randn(3, 32) * 1000.0

    assert torch.equal(model(features, "route"), torch.zeros(3))
    with pytest.raises(ResidualPocBlocked, match="delegated category"):
        model(features, "event")
    payload = canonical_residual_model_payload(model, candidate=candidate)
    loaded = load_residual_model_payload(payload, candidate=candidate, model_seed=0)
    assert canonical_residual_model_payload(loaded, candidate=candidate) == payload

    tampered = copy.deepcopy(payload)
    first_name = sorted(tampered["tensors"])[0]
    tampered["tensors"][first_name]["values"][0] = "nan"
    with pytest.raises(ResidualPocBlocked, match="non-finite"):
        load_residual_model_payload(tampered, candidate=candidate, model_seed=0)


def test_selected_composite_model_round_trip_is_exact():
    registration = _valid_registration()
    base_model = build_warm_start_model(
        hash_dim=1024, hidden_dim=128, model_seed=0
    )
    residual_model = build_residual_model(
        hash_dim=2048, hidden_dim=32, model_seed=0, residual_scale=1.0
    )
    payload = canonical_composite_model_payload(
        base_model=base_model,
        residual_model=residual_model,
        registration=registration,
    )
    loaded_base, loaded_residual = load_composite_model_payload(
        payload, registration=registration
    )

    assert canonical_composite_model_payload(
        base_model=loaded_base,
        residual_model=loaded_residual,
        registration=registration,
    ) == payload


def test_shared_base_is_immutable_and_event_shop_delegate_exactly():
    dataset = _dataset(tuple(range(8)))
    control = _control_candidate(hash_dim=64, hidden_dim=8)
    residual = _residual_candidate(hash_dim=64, hidden_dim=8)
    pairs = prepare_paired_rows(
        dataset, control_candidate=control, residual_candidate=residual
    )
    base_model, _ = train_candidate_model(
        [row.legacy for row in pairs],
        candidate=control,
        optimizer_config=_optimizer(epochs=2),
    )
    base_before = canonical_warm_start_model_payload(base_model)
    residual_model, training = train_residual_model(
        pairs,
        base_model=base_model,
        candidate=residual,
        optimizer_config=_optimizer(epochs=2),
    )
    evaluation = evaluate_paired_models(
        base_model=base_model, residual_model=residual_model, rows=pairs, fold=0
    )

    assert training["base_immutable"] is True
    assert canonical_warm_start_model_payload(base_model) == base_before
    assert evaluation["delegation"]["exact"] is True
    assert set(evaluation["delegation"]["by_category"]) == set(DELEGATED_CATEGORIES)
    assert evaluation["residual_diagnostics"]["overall"]["max_abs"] <= 1.0
    assert all(
        row["candidate_count"] == len(row["candidate_action_ids"])
        for row in evaluation["candidate_predictions"]
    )

    singleton = copy.deepcopy(dataset)
    singleton["rows"][0]["candidate_actions"] = singleton["rows"][0][
        "candidate_actions"
    ][:1]
    singleton["rows"][0]["teacher"]["action_id"] = singleton["rows"][0][
        "candidate_actions"
    ][0]["action_id"]
    assert len(
        prepare_paired_rows(
            singleton, control_candidate=control, residual_candidate=residual
        )
    ) == len(pairs) - 1


def _metrics(agreement: dict[str, float], cross_entropy: dict[str, float]):
    by_category = {
        category: {
            "action_agreement": agreement[category],
            "mean_cross_entropy": cross_entropy[category],
            "row_count": 10,
        }
        for category in TARGET_CATEGORIES
    }
    return {
        "by_category": by_category,
        "macro_category_action_agreement": sum(agreement.values()) / 4,
        "macro_category_mean_cross_entropy": sum(cross_entropy.values()) / 4,
        "overall_action_agreement": sum(agreement.values()) / 4,
        "overall_mean_cross_entropy": sum(cross_entropy.values()) / 4,
        "row_count": 40,
    }


def _positive_gate_input():
    control_agreement = {category: 0.5 for category in TARGET_CATEGORIES}
    control_ce = {category: 1.0 for category in TARGET_CATEGORIES}
    candidate_agreement = {**control_agreement, "card_reward": 0.55, "route": 0.6}
    candidate_ce = {**control_ce, "card_reward": 0.98, "route": 0.95}
    control = _metrics(control_agreement, control_ce)
    candidate = _metrics(candidate_agreement, candidate_ce)
    delta = {
        "by_category": {
            category: {
                "action_agreement": candidate["by_category"][category]["action_agreement"]
                - control["by_category"][category]["action_agreement"],
                "mean_cross_entropy": candidate["by_category"][category]["mean_cross_entropy"]
                - control["by_category"][category]["mean_cross_entropy"],
                "row_count": 10,
            }
            for category in TARGET_CATEGORIES
        },
        "macro_category_action_agreement": candidate["macro_category_action_agreement"] - control["macro_category_action_agreement"],
        "macro_category_mean_cross_entropy": candidate["macro_category_mean_cross_entropy"] - control["macro_category_mean_cross_entropy"],
        "overall_action_agreement": candidate["overall_action_agreement"] - control["overall_action_agreement"],
        "overall_mean_cross_entropy": candidate["overall_mean_cross_entropy"] - control["overall_mean_cross_entropy"],
        "row_count": 40,
    }
    return {
        "aggregate_metrics": {"candidate": candidate, "control": control, "deltas": delta},
        "base_immutable": True,
        "delegation": {"exact": True},
        "fold_metrics": [{"deltas": copy.deepcopy(delta), "fold": fold} for fold in range(4)],
        "residual_diagnostics": {"overall": {"max_abs": 0.5}},
    }


def test_terminal_gate_distinguishes_positive_negative_and_blocked():
    positive_input = _positive_gate_input()
    positive = compare_paired_result(
        positive_input, thresholds=_registered_thresholds(), residual_scale=1.0
    )
    assert positive["verdict"] == "route_card_residual_selected"
    assert positive["selected_candidate_id"] == RESIDUAL_CANDIDATE_ID
    assert all(item["pass"] for item in positive["fold_checks"])

    negative_input = copy.deepcopy(positive_input)
    negative_input["fold_metrics"][2]["deltas"]["by_category"]["card_reward"][
        "mean_cross_entropy"
    ] = 0.001
    negative = compare_paired_result(
        negative_input, thresholds=_registered_thresholds(), residual_scale=1.0
    )
    assert negative["verdict"] == "poc_valid_without_route_card_residual"
    assert negative["selected_candidate_id"] is None

    blocked_input = copy.deepcopy(positive_input)
    blocked_input["delegation"]["exact"] = False
    blocked = compare_paired_result(
        blocked_input, thresholds=_registered_thresholds(), residual_scale=1.0
    )
    assert blocked["verdict"] == "blocked"
    assert blocked["selected_candidate_id"] is None


def test_synthetic_primary_replay_and_artifacts_are_deterministic(tmp_path):
    train_input = _train_input(REGISTERED_TRAIN_SEEDS)
    registration = _valid_registration(
        train_input["source"]["train_dataset_sha256"]
    )
    mismatched_registration = copy.deepcopy(registration)
    mismatched_registration["identity"]["train_dataset_sha256"] = "f" * 64
    with pytest.raises(ResidualPocBlocked, match="train dataset identity"):
        execute_poc(
            registration=mismatched_registration,
            train_input=train_input,
        )
    primary = execute_poc(registration=registration, train_input=train_input)
    replay = execute_poc(registration=registration, train_input=train_input)

    assert canonical_json_bytes(primary) == canonical_json_bytes(replay)
    artifacts = build_artifacts(
        registration=registration, primary=primary, replay=replay
    )
    manifest = validate_artifact_payloads(artifacts)
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["verdict"] in {
        "poc_valid_without_route_card_residual",
        "route_card_residual_selected",
    }
    assert not any(manifest["authority"].values())
    metrics = json.loads(artifacts["metrics.json"])
    models = json.loads(artifacts["models.json"])
    assert len(metrics["fold_metrics"]) == 4
    assert metrics["delegation"]["exact"] is True
    assert models["schema_version"] == COMPOSITE_MODEL_SCHEMA_VERSION

    publish_artifacts(tmp_path, artifacts)
    assert validate_artifact_directory(tmp_path) == manifest
    tampered = dict(artifacts)
    tampered["metrics.json"] += b" "
    with pytest.raises(ResidualPocBlocked, match="hash closure"):
        validate_artifact_payloads(tampered)

    semantically_tampered = dict(artifacts)
    prediction_payload = json.loads(semantically_tampered["predictions.json"])
    route_row = next(
        row
        for row in prediction_payload["candidate_predictions"]
        if row["category"] == "route"
    )
    route_row["residual_hexes"][0] = float(1.0).hex()
    semantically_tampered["predictions.json"] = canonical_json_bytes(
        prediction_payload
    )
    manifest_payload = json.loads(semantically_tampered["artifact_manifest.json"])
    manifest_payload["artifact_hashes"]["predictions.json"] = sha256_bytes(
        semantically_tampered["predictions.json"]
    )
    semantically_tampered["artifact_manifest.json"] = canonical_json_bytes(
        manifest_payload
    )
    with pytest.raises(ResidualPocBlocked, match="base score plus residual"):
        validate_artifact_payloads(semantically_tampered)
