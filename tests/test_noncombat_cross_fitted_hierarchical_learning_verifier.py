from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import io
import json
import math
import os
import random
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from analysis_scripts import (
    verify_noncombat_cross_fitted_hierarchical_learning_experiment as verifier,
)


ROOT = Path(__file__).resolve().parents[1]


def _float32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def test_verifier_import_is_source_only_without_torch_or_native():
    source = (
        "import builtins,json,sys;"
        "original=builtins.__import__;"
        "blocked={'torch','sts_lightspeed_noncombat_adapter'};"
        "builtins.__import__=lambda name,*a,**k: "
        "(_ for _ in ()).throw(RuntimeError('blocked '+name)) "
        "if name.split('.')[0] in blocked else original(name,*a,**k);"
        "import analysis_scripts."
        "verify_noncombat_cross_fitted_hierarchical_learning_experiment as v;"
        "contract=v.verifier_contract();"
        "print(json.dumps({'native':'sts_lightspeed_noncombat_adapter' in sys.modules,"
        "'runtime':'analysis_scripts."
        "noncombat_cross_fitted_hierarchical_learning_runtime' in sys.modules,"
        "'torch':'torch' in sys.modules},sort_keys=True))"
    )

    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == (
        '{"native": false, "runtime": false, "torch": false}'
    )


def test_verifier_cli_routes_terminal_bundle_without_producer_import(
    tmp_path, monkeypatch, capsys
):
    output = tmp_path / "terminal"
    observed = []

    def verify_exact(path):
        observed.append(path)
        return {"verdict": "synthetic-verified"}

    monkeypatch.setattr(verifier, "verify_terminal_bundle", verify_exact)
    assert verifier.main(["--output", str(output)]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "verdict": "synthetic-verified"
    }
    assert observed == [output]


def test_seed_inventory_replays_the_producer_seed_first_row_order():
    commit = "a" * 40
    rows = [
        {
            "document_index": 0,
            "json_path": "/seed",
            "role": "seed",
            "seed": 1,
            "source_path": "reports/z.json",
        },
        {
            "document_index": 0,
            "json_path": "/seed",
            "role": "seed",
            "seed": 2,
            "source_path": "reports/a.json",
        },
    ]
    excluded = sorted(
        {1, 2}
        | set(
            range(
                verifier.PREVIOUS_UNTOUCHED_HOLDOUT_START,
                verifier.PREVIOUS_UNTOUCHED_HOLDOUT_END + 1,
            )
        )
    )
    inventory = {
        "canonical_search_start": 0,
        "excluded_seed_count": len(excluded),
        "excluded_seeds": excluded,
        "repository_commit": commit,
        "reserved_seed_ranges": [
            {
                "end_inclusive": verifier.PREVIOUS_UNTOUCHED_HOLDOUT_END,
                "name": "previous_untouched_holdout",
                "start_inclusive": verifier.PREVIOUS_UNTOUCHED_HOLDOUT_START,
            }
        ],
        "row_count": len(rows),
        "rows": rows,
        "schema_version": verifier.SEED_INVENTORY_SCHEMA_VERSION,
        "source_bindings": [
            {
                "document_count": 1,
                "format": "json",
                "path": path,
                "row_count": 1,
                "sha256": digest * 64,
                "size_bytes": 1,
            }
            for path, digest in (
                ("reports/a.json", "a"),
                ("reports/z.json", "b"),
            )
        ],
        "source_count": 2,
    }

    assert verifier._validate_seed_inventory(inventory, commit) == inventory

    source_first = copy.deepcopy(inventory)
    source_first["rows"].reverse()
    with pytest.raises(verifier.VerifierError, match="not canonical"):
        verifier._validate_seed_inventory(source_first, commit)


@pytest.mark.parametrize(
    ("dtype", "values", "shape", "format_code"),
    [
        ("float32", [1.0, -2.5, 0.0, 4.25], [2, 2], "f"),
        ("float64", [math.pi, -0.0, 1e100], [3], "d"),
        ("float32", [3.5], [], "f"),
        ("float64", [], [0, 7], "d"),
    ],
)
def test_float_payload_is_canonical_little_endian_and_round_trips(
    dtype, values, shape, format_code
):
    payload = verifier.encode_float_payload(
        values,
        dtype=dtype,
        shape=shape,
    )
    expected_raw = b"".join(
        struct.pack("<" + format_code, value) for value in values
    )

    assert payload == {
        "byte_order": "little",
        "data_base64": base64.b64encode(expected_raw).decode("ascii"),
        "data_sha256": hashlib.sha256(expected_raw).hexdigest(),
        "dtype": dtype,
        "shape": shape,
    }
    assert verifier.decode_float_payload(payload) == tuple(
        item[0] for item in struct.iter_unpack("<" + format_code, expected_raw)
    )


def test_float_payload_rejects_noncanonical_base64_even_when_bytes_match():
    payload = verifier.encode_float_payload([1.0], dtype="float32", shape=[1])
    assert payload["data_base64"] == "AACAPw=="
    payload["data_base64"] = "AACAPx=="
    assert base64.b64decode(payload["data_base64"], validate=True) == struct.pack(
        "<f", 1.0
    )

    with pytest.raises(verifier.VerifierError, match="canonical"):
        verifier.decode_float_payload(payload)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.__setitem__("data_base64", "***"), "base64"),
        (lambda value: value.__setitem__("shape", [2]), "shape"),
        (lambda value: value.__setitem__("data_sha256", "0" * 64), "hash"),
        (lambda value: value.__setitem__("byte_order", "big"), "little"),
        (lambda value: value.__setitem__("dtype", "float16"), "dtype"),
        (lambda value: value.__setitem__("extra", 1), "fields"),
    ],
)
def test_float_payload_rejects_tampering(mutation, message):
    payload = verifier.encode_float_payload([1.0], dtype="float32", shape=[1])
    mutation(payload)

    with pytest.raises(verifier.VerifierError, match=message):
        verifier.decode_float_payload(payload)


@pytest.mark.parametrize(("dtype", "format_code"), [("float32", "f"), ("float64", "d")])
def test_float_payload_rejects_nonfinite_decoded_values(dtype, format_code):
    raw = struct.pack("<" + format_code, math.nan)
    payload = {
        "byte_order": "little",
        "data_base64": base64.b64encode(raw).decode("ascii"),
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "dtype": dtype,
        "shape": [1],
    }

    with pytest.raises(verifier.VerifierError, match="non-finite"):
        verifier.decode_float_payload(payload)


def test_float_payload_rejects_nonfinite_or_out_of_range_encode_values():
    with pytest.raises(verifier.VerifierError, match="finite"):
        verifier.encode_float_payload([math.inf], dtype="float64", shape=[1])
    with pytest.raises(verifier.VerifierError, match="represented"):
        verifier.encode_float_payload([1e100], dtype="float32", shape=[1])


def _gzip_with_level(payload: bytes, level: int) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="",
        fileobj=buffer,
        mode="wb",
        compresslevel=level,
        mtime=0,
    ) as stream:
        stream.write(payload)
    return buffer.getvalue()


def test_deterministic_gzip_binds_and_reconstructs_both_identities():
    canonical = (b"ridge-gradient-adam\n" * 4096) + bytes(range(256))

    first_stored, first_binding = verifier.encode_deterministic_gzip(canonical)
    second_stored, second_binding = verifier.encode_deterministic_gzip(canonical)

    assert first_stored == second_stored
    assert first_binding == second_binding
    assert first_stored[:4] == b"\x1f\x8b\x08\x00"
    assert first_stored[4:8] == b"\x00\x00\x00\x00"
    assert first_binding["canonical_sha256"] == hashlib.sha256(
        canonical
    ).hexdigest()
    assert first_binding["sha256"] == hashlib.sha256(first_stored).hexdigest()
    assert verifier.verify_deterministic_gzip(
        first_stored, first_binding
    ) == canonical


def test_gzip_rejects_alternate_encoding_with_self_consistent_hashes():
    canonical = (b"0123456789abcdef" * 8192) + bytes(range(251))
    expected, binding = verifier.encode_deterministic_gzip(canonical)
    alternate = _gzip_with_level(canonical, 1)
    assert alternate != expected
    changed = copy.deepcopy(binding)
    changed["sha256"] = hashlib.sha256(alternate).hexdigest()
    changed["size_bytes"] = len(alternate)

    with pytest.raises(verifier.VerifierError, match="reconstruction"):
        verifier.verify_deterministic_gzip(alternate, changed)


def test_gzip_decompression_is_bounded_by_declared_and_local_limits():
    canonical = b"x" * 4096
    stored, binding = verifier.encode_deterministic_gzip(canonical)
    forged = copy.deepcopy(binding)
    forged["canonical_size_bytes"] = 32
    forged["canonical_sha256"] = hashlib.sha256(b"x" * 32).hexdigest()

    with pytest.raises(verifier.VerifierError, match="canonical size"):
        verifier.verify_deterministic_gzip(
            stored,
            forged,
            max_uncompressed_bytes=32,
        )
    with pytest.raises(verifier.VerifierError, match="byte bound"):
        verifier.verify_deterministic_gzip(
            stored,
            binding,
            max_uncompressed_bytes=32,
        )


def test_ridge_residual_replay_uses_fixed_coordinate_boundary():
    assert verifier.verify_ridge_residuals(
        normal_matrix=[[2.0, 0.0], [0.0, 4.0]],
        coefficients=[0.5, 0.25],
        rhs=[1.0, 1.0],
    ) == (0.0, 0.0)

    scale = 3.0
    limit = verifier.RIDGE_RESIDUAL_ATOL + verifier.RIDGE_RESIDUAL_RTOL * scale
    assert verifier.ridge_residual_within_tolerance(
        residual=math.nextafter(limit, 0.0),
        rhs=2.0,
        absolute_product_sum=scale,
    )
    assert not verifier.ridge_residual_within_tolerance(
        residual=math.nextafter(limit, math.inf),
        rhs=2.0,
        absolute_product_sum=scale,
    )
    with pytest.raises(verifier.VerifierError, match="coordinate 0"):
        verifier.verify_ridge_residuals(
            normal_matrix=[[1.0]],
            coefficients=[2e-9],
            rhs=[0.0],
        )


def test_preclip_prediction_replay_requires_exact_float64_value_and_bytes():
    coefficients = [0.5, -1.25, 2.0]
    augmented_features = [3.0, 4.0, 1.0]
    expected = math.fsum(
        coefficient * feature
        for coefficient, feature in zip(coefficients, augmented_features)
    )
    expected_hex = struct.pack("<d", expected).hex()

    assert verifier.replay_preclip_prediction(
        coefficients=coefficients,
        augmented_features=augmented_features,
        stored_prediction=expected,
        stored_little_endian_hex=expected_hex,
    ) == expected
    with pytest.raises(verifier.VerifierError, match="value"):
        verifier.replay_preclip_prediction(
            coefficients=coefficients,
            augmented_features=augmented_features,
            stored_prediction=math.nextafter(expected, math.inf),
            stored_little_endian_hex=expected_hex,
        )
    with pytest.raises(verifier.VerifierError, match="bytes"):
        verifier.replay_preclip_prediction(
            coefficients=coefficients,
            augmented_features=augmented_features,
            stored_prediction=expected,
            stored_little_endian_hex=struct.pack(
                "<d", math.nextafter(expected, math.inf)
            ).hex(),
        )


def _adam_transition() -> dict[str, object]:
    pre_parameters = (1.0, -2.0)
    gradient = (0.25, -0.5)
    pre_exp_avg = (0.0, 0.0)
    pre_exp_avg_sq = (0.0, 0.0)
    post_exp_avg = tuple(_float32(0.1 * value) for value in gradient)
    post_exp_avg_sq = tuple(_float32(0.001 * value * value) for value in gradient)
    step_size = 0.001 / (1.0 - 0.9)
    correction2_sqrt = math.sqrt(1.0 - 0.999)
    post_parameters = tuple(
        _float32(
            parameter
            - step_size
            * first_moment
            / (math.sqrt(second_moment) / correction2_sqrt + 1e-8)
        )
        for parameter, first_moment, second_moment in zip(
            pre_parameters, post_exp_avg, post_exp_avg_sq
        )
    )
    return {
        "pre_parameters": pre_parameters,
        "installed_gradient": gradient,
        "pre_exp_avg": pre_exp_avg,
        "pre_exp_avg_sq": pre_exp_avg_sq,
        "pre_step": 0,
        "post_parameters": post_parameters,
        "post_exp_avg": post_exp_avg,
        "post_exp_avg_sq": post_exp_avg_sq,
        "post_step": 1,
    }


def test_adam_transition_replay_uses_the_fixed_controls_and_tolerances():
    transition = _adam_transition()

    replayed = verifier.replay_adam_transition(**transition)

    assert replayed["post_step"] == 1
    assert replayed["post_parameters"] == transition["post_parameters"]
    assert verifier.ADAM_ATOL == 5e-7
    assert verifier.ADAM_RTOL == 5e-6
    assert verifier.verifier_contract()["adam_replay"] == {
        "atol": 5e-7,
        "betas": [0.9, 0.999],
        "epsilon": 1e-8,
        "learning_rate": 0.001,
        "rtol": 5e-6,
    }


def test_adam_transition_rejects_wrong_installed_gradient():
    transition = _adam_transition()
    transition["installed_gradient"] = (0.5, -0.5)

    with pytest.raises(verifier.VerifierError, match="first moment"):
        verifier.replay_adam_transition(**transition)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("post_exp_avg", (0.026, -0.05), "first moment"),
        ("post_exp_avg_sq", (0.001, 0.00025), "second moment"),
        ("post_parameters", (0.9, -1.999), "parameter"),
        ("post_step", 0, "step"),
    ],
)
def test_adam_transition_rejects_wrong_moment_parameter_or_step(
    field, replacement, message
):
    transition = _adam_transition()
    transition[field] = replacement

    with pytest.raises(verifier.VerifierError, match=message):
        verifier.replay_adam_transition(**transition)


def _fixture_canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )


def _fixture_float_payload(values, *, dtype, shape):
    format_code = "f" if dtype == "float32" else "d"
    raw = b"".join(struct.pack("<" + format_code, value) for value in values)
    return {
        "byte_order": "little",
        "data_base64": base64.b64encode(raw).decode("ascii"),
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "dtype": dtype,
        "shape": list(shape),
    }


def _fixture_sparse_feature(value: float) -> dict[str, object]:
    identity = {
        "dense_dim": 128,
        "dtype": "float32",
        "entries": [[0, _float32(value)]],
        "folding": "ascending-source-index-modulo-128-float32-add-v1",
        "schema_version": "cross-fitted-baseline-state-features-v1",
        "source_dim": 1024,
    }
    return {
        **identity,
        "sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(identity)
        ).hexdigest(),
    }


def _fixture_diagnostic(
    *,
    category: str,
    chunk_index: int,
    decision_id: str,
    decision_index: int,
    reward: float,
    selected_action_id: str,
) -> tuple[dict[str, object], dict[str, object]]:
    selected_family = "take"
    alternative_family = "skip"
    alternative_action_id = f"{selected_action_id}:alternative"
    selected_score = _float32(math.log(3.0))
    normalization = math.exp(selected_score) + 1.0
    selected_probability = math.exp(selected_score) / normalization
    alternative_probability = 1.0 / normalization
    selected_log_probability = math.log(selected_probability)
    family_entropy = -math.fsum(
        (
            selected_probability * selected_log_probability,
            alternative_probability * math.log(alternative_probability),
        )
    )
    terminal_victory = 1 if reward >= 2.0 else 0
    floor_progress = reward - 2.0 * terminal_victory
    diagnostic = {
        "action_generator_state_sha256": {
            stage: hashlib.sha256(f"{decision_id}:{stage}".encode("ascii")).hexdigest()
            for stage in ("after_conditional", "after_family", "before_family")
        },
        "candidate_scores": {
            selected_action_id: selected_score,
            alternative_action_id: 0.0,
        },
        "candidates": [
            {"action_id": selected_action_id, "kind": selected_family},
            {"action_id": alternative_action_id, "kind": alternative_family},
        ],
        "category": category,
        "chunk_index": chunk_index,
        "conditional_probabilities": {
            selected_action_id: 1.0,
            alternative_action_id: 1.0,
        },
        "decision_id": decision_id,
        "decision_index": decision_index,
        "family_order": [alternative_family, selected_family],
        "family_probabilities": {
            alternative_family: alternative_probability,
            selected_family: selected_probability,
        },
        "formal_reward": {
            "floor_progress": floor_progress,
            "scalar_reward": reward,
            "terminal_victory": terminal_victory,
        },
        "joint_probabilities": {
            selected_action_id: selected_probability,
            alternative_action_id: alternative_probability,
        },
        "multi_family": True,
        "raw_score_max_action_ids": [selected_action_id],
        "raw_score_max_family_ids": [selected_family],
        "selected_action_id": selected_action_id,
        "selected_family": selected_family,
        "selection_mode": "family-first-then-conditional-v1",
    }
    policy_terms = {
        "conditional_entropy": 0.0,
        "family_entropy": family_entropy,
        "selected_action_id": selected_action_id,
        "selected_conditional_log_probability": 0.0,
        "selected_family": selected_family,
        "selected_family_log_probability": selected_log_probability,
        "selected_joint_log_probability": selected_log_probability,
    }
    return diagnostic, policy_terms


def _fixture_normal_equations(records, held_out):
    width = 129
    matrix = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width
    decisions_by_trajectory = {}
    for record in records:
        trajectory_id = record["trajectory_id"]
        decisions_by_trajectory[trajectory_id] = (
            decisions_by_trajectory.get(trajectory_id, 0) + 1
        )
    for record in records:
        if record["trajectory_id"] in held_out:
            continue
        weight = 1.0 / (
            48.0 * decisions_by_trajectory[record["trajectory_id"]]
        )
        sparse = ((0, 1.0), (1, record["feature_value"]))
        target = record["raw_return"]
        for row_index, row_value in sparse:
            rhs[row_index] = float(rhs[row_index]) + (
                (weight * target) * row_value
            )
            for column_index, column_value in sparse:
                matrix[row_index][column_index] = float(
                    matrix[row_index][column_index]
                ) + ((weight * row_value) * column_value)
    for coordinate in range(1, width):
        matrix[coordinate][coordinate] = (
            float(matrix[coordinate][coordinate]) + 0.001
        )
    return matrix, rhs


def _fixture_scalar_components(decision_rows):
    denominator = float(len(decision_rows))
    card_family = []
    card_conditional = []
    other = []
    family_entropy = []
    conditional_entropy = []
    for row in decision_rows:
        terms = row["policy_terms"]
        advantage = row["advantage"]
        if row["category"] == "card_reward":
            card_family.append(
                terms["selected_family_log_probability"] * advantage
            )
            card_conditional.append(
                terms["selected_conditional_log_probability"] * advantage
            )
        else:
            other.append(terms["selected_joint_log_probability"] * advantage)
        family_entropy.append(terms["family_entropy"])
        conditional_entropy.append(terms["conditional_entropy"])
    return {
        "card_reward_family_policy": -math.fsum(card_family) / denominator,
        "card_reward_conditional_policy": -math.fsum(card_conditional)
        / denominator,
        "other_policy": -math.fsum(other) / denominator,
        "family_entropy_regularizer": -0.01
        * math.fsum(family_entropy)
        / denominator,
        "conditional_entropy_regularizer": -0.01
        * math.fsum(conditional_entropy)
        / denominator,
    }


def _fixture_adam_parameter(name, shape, pre_parameters, gradient):
    post_exp_avg = tuple(_float32(0.1 * value) for value in gradient)
    post_exp_avg_sq = tuple(
        _float32(0.001 * value * value) for value in gradient
    )
    step_size = 0.001 / (1.0 - 0.9)
    correction2_sqrt = math.sqrt(1.0 - 0.999)
    post_parameters = tuple(
        _float32(
            parameter
            - step_size
            * first_moment
            / (math.sqrt(second_moment) / correction2_sqrt + 1e-8)
        )
        for parameter, first_moment, second_moment in zip(
            pre_parameters, post_exp_avg, post_exp_avg_sq, strict=True
        )
    )
    zeros = (0.0,) * len(pre_parameters)
    return {
        "installed_gradient": _fixture_float_payload(
            gradient, dtype="float32", shape=shape
        ),
        "name": name,
        "post_exp_avg": _fixture_float_payload(
            post_exp_avg, dtype="float32", shape=shape
        ),
        "post_exp_avg_sq": _fixture_float_payload(
            post_exp_avg_sq, dtype="float32", shape=shape
        ),
        "post_parameter": _fixture_float_payload(
            post_parameters, dtype="float32", shape=shape
        ),
        "post_step": 1,
        "pre_exp_avg": _fixture_float_payload(
            zeros, dtype="float32", shape=shape
        ),
        "pre_exp_avg_sq": _fixture_float_payload(
            zeros, dtype="float32", shape=shape
        ),
        "pre_parameter": _fixture_float_payload(
            pre_parameters, dtype="float32", shape=shape
        ),
        "pre_step": 0,
        "shape": list(shape),
    }


def _rehash_chunk(chunk):
    content = {
        key: value for key, value in chunk.items() if key != "content_sha256"
    }
    chunk["content_sha256"] = hashlib.sha256(
        _fixture_canonical_json_bytes(content)
    ).hexdigest()
    return chunk


def _chunk_evidence_fixture():
    seeds = [10_000 + 2 * index for index in range(64)]
    trajectory_ids = [f"seed-{seed}" for seed in seeds]
    folds = {
        f"fold-{fold_index}": [
            trajectory_ids[position]
            for position in range(64)
            if position % 4 == fold_index
        ]
        for fold_index in range(4)
    }
    coefficients = [1.5, 0.5 / 1.001] + [0.0] * 127
    records = []
    decision_rows = []
    for position, (seed, trajectory_id) in enumerate(
        zip(seeds, trajectory_ids, strict=True)
    ):
        feature_value = -1.0 if (position // 4) % 2 == 0 else 1.0
        raw_return = 1.5 + 0.5 * feature_value
        fold_id = f"fold-{position % 4}"
        prediction = math.fsum(
            coefficient * feature
            for coefficient, feature in zip(
                coefficients,
                [1.0, feature_value] + [0.0] * 127,
                strict=True,
            )
        )
        clipped = min(3.0, max(0.0, prediction))
        advantage = raw_return - clipped
        fit_ids = sorted(set(trajectory_ids).difference(folds[fold_id]))
        category = "card_reward" if feature_value > 0.0 else "shop"
        for decision_index in range(2):
            decision_id = f"seed-{seed}:decision-{decision_index}"
            reward = raw_return if decision_index == 1 else 0.0
            selected_action_id = f"action-{position:03d}-{decision_index}"
            diagnostic, policy_terms = _fixture_diagnostic(
                category=category,
                chunk_index=0,
                decision_id=decision_id,
                decision_index=decision_index,
                reward=reward,
                selected_action_id=selected_action_id,
            )
            row = {
                "advantage": advantage,
                "baseline_fit_trajectory_ids": fit_ids,
                "baseline_prediction": clipped,
                "category": category,
                "decision_id": decision_id,
                "decision_index": decision_index,
                "diagnostic": diagnostic,
                "feature": _fixture_sparse_feature(feature_value),
                "fold_id": fold_id,
                "policy_terms": policy_terms,
                "prediction": {
                    "clipped": clipped,
                    "preclip_little_endian_hex": struct.pack("<d", prediction).hex(),
                    "unclipped": prediction,
                    "was_clipped": clipped != prediction,
                },
                "raw_return": raw_return,
                "reward": reward,
                "scale": 1.0,
                "scale_mode": "fixed_unit",
                "seed": seed,
                "trajectory_id": trajectory_id,
            }
            records.append(
                {
                    "feature_value": feature_value,
                    "raw_return": raw_return,
                    "trajectory_id": trajectory_id,
                }
            )
            decision_rows.append(row)

    model_rows = []
    for fold_index in range(4):
        fold_id = f"fold-{fold_index}"
        held_out = folds[fold_id]
        matrix, rhs = _fixture_normal_equations(records, set(held_out))
        matrix_products = [
            math.fsum(
                matrix[row_index][column_index] * coefficients[column_index]
                for column_index in range(129)
            )
            for row_index in range(129)
        ]
        residuals = [
            matrix_products[index] - rhs[index] for index in range(129)
        ]
        product_sums = [
            math.fsum(
                abs(
                    matrix[row_index][column_index]
                    * coefficients[column_index]
                )
                for column_index in range(129)
            )
            for row_index in range(129)
        ]
        model_rows.append(
            {
                "absolute_product_sums": _fixture_float_payload(
                    product_sums, dtype="float64", shape=[129]
                ),
                "coefficients": _fixture_float_payload(
                    coefficients, dtype="float64", shape=[129]
                ),
                "fit_trajectory_ids": sorted(
                    set(trajectory_ids).difference(held_out)
                ),
                "fold_id": fold_id,
                "held_out_trajectory_ids": held_out,
                "kkt_residuals": _fixture_float_payload(
                    residuals, dtype="float64", shape=[129]
                ),
                "rhs": _fixture_float_payload(
                    rhs, dtype="float64", shape=[129]
                ),
            }
        )

    component_names = [
        "card_reward_family_policy",
        "card_reward_conditional_policy",
        "other_policy",
        "family_entropy_regularizer",
        "conditional_entropy_regularizer",
    ]
    component_values = {
        component_names[0]: [1.0, 0.0, 0.0],
        component_names[1]: [1.0, 0.0, 0.0],
        component_names[2]: [0.0, 0.0, 0.0],
        component_names[3]: [0.0, 0.0, 0.0],
        component_names[4]: [0.0, 0.0, 0.0],
    }
    full = [2.0, 0.0, 0.0]
    full_norm = 2.0
    clip_factor = 1.0 / (full_norm + 1e-6)
    clipped = [value * clip_factor for value in full]
    installed = [_float32(value) for value in clipped]
    consumed = list(installed)
    legacy = [-1.0, 0.0, 0.0]
    scalar_components = _fixture_scalar_components(decision_rows)
    scalar_full = math.fsum(
        scalar_components[name] for name in component_names
    )
    pre_parameter_values = [1.0, -2.0, 0.5]
    pre_parameter_raw = b"".join(
        struct.pack("<f", value) for value in pre_parameter_values
    )
    adam_parameters = [
        _fixture_adam_parameter(
            "weight", [2], tuple(pre_parameter_values[:2]), tuple(installed[:2])
        ),
        _fixture_adam_parameter(
            "bias", [1], tuple(pre_parameter_values[2:]), tuple(installed[2:])
        ),
    ]
    content = {
        "adam": {
            "betas": [0.9, 0.999],
            "epsilon": 1e-8,
            "learning_rate": 0.001,
            "parameters": adam_parameters,
            "weight_decay": 0.0,
        },
        "baseline": {
            "fold_trajectories": folds,
            "models": model_rows,
        },
        "chunk_index": 0,
        "decisions": decision_rows,
        "gradients": {
            "clip_comparison": {
                "max_abs_difference": 0.0,
                "max_relative_difference": 0.0,
            },
            "clip_factor": clip_factor,
            "clipped_full": _fixture_float_payload(
                clipped, dtype="float64", shape=[3]
            ),
            "component_order": component_names,
            "component_vectors": {
                name: _fixture_float_payload(
                    component_values[name], dtype="float64", shape=[3]
                )
                for name in component_names
            },
            "consumed_torch_clipped": _fixture_float_payload(
                consumed, dtype="float32", shape=[3]
            ),
            "full": _fixture_float_payload(full, dtype="float64", shape=[3]),
            "gradient_comparison": {
                "cosine": -1.0,
                "cross_fitted_norm": 2.0,
                "difference_norm": 3.0,
                "dot": -2.0,
                "legacy_norm": 1.0,
            },
            "installed": _fixture_float_payload(
                installed, dtype="float32", shape=[3]
            ),
            "legacy": _fixture_float_payload(
                legacy, dtype="float64", shape=[3]
            ),
            "legacy_loss_value": 0.125,
            "legacy_normalized_returns": _fixture_float_payload(
                [
                    -1.0 if row["raw_return"] == 1.0 else 1.0
                    for row in decision_rows
                ],
                dtype="float32",
                shape=[len(decision_rows)],
            ),
            "parameter_names": ["weight", "bias"],
            "parameter_shapes": [[2], [1]],
            "pre_parameter_sha256": hashlib.sha256(
                pre_parameter_raw
            ).hexdigest(),
            "scalar_components": scalar_components,
            "scalar_full_loss": scalar_full,
        },
        "schema_version": (
            "noncombat-cross-fitted-hierarchical-learning-chunk-evidence-v1"
        ),
        "torch_version": "synthetic-source-only",
    }
    return _rehash_chunk({**content, "content_sha256": "0" * 64})


def test_verify_chunk_evidence_reconstructs_complete_source_only_chunk():
    evidence = _chunk_evidence_fixture()

    result = verifier.verify_chunk_evidence(evidence)

    assert result == {
        "chunk_index": 0,
        "content_sha256": evidence["content_sha256"],
        "decision_count": 128,
        "fold_count": 4,
        "parameter_count": 3,
        "schema_version": (
            "noncombat-cross-fitted-hierarchical-learning-chunk-evidence-v1"
        ),
        "trajectory_count": 64,
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["decisions"][0]["diagnostic"].__setitem__(
                "unexpected", False
            ),
            "diagnostic fields",
        ),
        (
            lambda value: value["decisions"][0]["diagnostic"].__setitem__(
                "category", "event"
            ),
            "diagnostic category",
        ),
        (
            lambda value: value["decisions"][0]["diagnostic"].__setitem__(
                "family_order", ["take", "skip"]
            ),
            "family order",
        ),
        (
            lambda value: value["decisions"][0]["diagnostic"].__setitem__(
                "multi_family", False
            ),
            "multi-family",
        ),
        (
            lambda value: value["decisions"][0]["diagnostic"].__setitem__(
                "raw_score_max_action_ids", ["not-the-maximum"]
            ),
            "raw-score maximum action",
        ),
        (
            lambda value: value["decisions"][0]["diagnostic"][
                "family_probabilities"
            ].__setitem__("take", 0.5),
            "family probability",
        ),
        (
            lambda value: value["decisions"][0]["policy_terms"].__setitem__(
                "selected_action_id", "not-selected"
            ),
            "selected action",
        ),
        (
            lambda value: value["decisions"][0]["diagnostic"][
                "formal_reward"
            ].__setitem__("scalar_reward", 0.25),
            "formal reward scalar",
        ),
    ],
)
def test_verify_chunk_evidence_rejects_diagnostic_or_policy_drift(
    mutate, message
):
    evidence = _chunk_evidence_fixture()
    mutate(evidence)
    _rehash_chunk(evidence)

    with pytest.raises(verifier.VerifierError, match=message):
        verifier.verify_chunk_evidence(evidence)


def test_verify_chunk_evidence_rejects_negative_seed_and_return_to_go_drift():
    evidence = _chunk_evidence_fixture()
    evidence["decisions"][0]["seed"] = -1
    _rehash_chunk(evidence)
    with pytest.raises(verifier.VerifierError, match="nonnegative"):
        verifier.verify_chunk_evidence(evidence)

    evidence = _chunk_evidence_fixture()
    evidence["decisions"][0]["raw_return"] += 0.25
    _rehash_chunk(evidence)
    with pytest.raises(verifier.VerifierError, match="return-to-go"):
        verifier.verify_chunk_evidence(evidence)


def test_verify_chunk_evidence_rejects_more_than_500_decisions_per_trajectory():
    evidence = _chunk_evidence_fixture()
    first = evidence["decisions"][0]
    extra = []
    for decision_index in range(2, 501):
        row = copy.deepcopy(first)
        decision_id = f"{row['trajectory_id']}:decision-{decision_index}"
        row["decision_id"] = decision_id
        row["decision_index"] = decision_index
        row["diagnostic"]["decision_id"] = decision_id
        row["diagnostic"]["decision_index"] = decision_index
        extra.append(row)
    evidence["decisions"][2:2] = extra
    _rehash_chunk(evidence)

    with pytest.raises(verifier.VerifierError, match="500 decisions"):
        verifier.verify_chunk_evidence(evidence)


def test_verify_chunk_evidence_rejects_content_hash_and_extra_fields():
    evidence = _chunk_evidence_fixture()
    evidence["content_sha256"] = "0" * 64
    with pytest.raises(verifier.VerifierError, match="content hash"):
        verifier.verify_chunk_evidence(evidence)

    evidence = _chunk_evidence_fixture()
    evidence["unexpected"] = False
    _rehash_chunk(evidence)
    with pytest.raises(verifier.VerifierError, match="fields"):
        verifier.verify_chunk_evidence(evidence)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["baseline"]["fold_trajectories"]["fold-0"].__setitem__(
                0, "trajectory-001"
            ),
            "duplicate|membership",
        ),
        (
            lambda value: (
                value["decisions"][0].__setitem__("decision_index", 1),
                value["decisions"][0]["diagnostic"].__setitem__(
                    "decision_index", 1
                ),
            ),
            "contiguous",
        ),
        (
            lambda value: value["decisions"][0]["baseline_fit_trajectory_ids"].pop(),
            "48",
        ),
        (
            lambda value: value["decisions"][0]["feature"].__setitem__(
                "sha256", "0" * 64
            ),
            "digest",
        ),
    ],
)
def test_verify_chunk_evidence_rejects_fold_trajectory_and_feature_drift(
    mutate, message
):
    evidence = _chunk_evidence_fixture()
    mutate(evidence)
    _rehash_chunk(evidence)

    with pytest.raises(verifier.VerifierError, match=message):
        verifier.verify_chunk_evidence(evidence)


def test_verify_chunk_evidence_rejects_rehashed_rhs_drift():
    evidence = _chunk_evidence_fixture()
    evidence["baseline"]["models"][0]["rhs"] = _fixture_float_payload(
        [9.0] + [0.0] * 128,
        dtype="float64",
        shape=[129],
    )
    _rehash_chunk(evidence)

    with pytest.raises(verifier.VerifierError, match="rhs"):
        verifier.verify_chunk_evidence(evidence)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        (
            "preclip_little_endian_hex",
            struct.pack("<d", 123.0).hex(),
            "float64 bytes",
        ),
        ("clipped", 2.75, "clipped prediction"),
    ],
)
def test_verify_chunk_evidence_rejects_prediction_replay_drift(
    field, replacement, message
):
    evidence = _chunk_evidence_fixture()
    evidence["decisions"][0]["prediction"][field] = replacement
    _rehash_chunk(evidence)

    with pytest.raises(verifier.VerifierError, match=message):
        verifier.verify_chunk_evidence(evidence)


def test_verify_chunk_evidence_rejects_advantage_and_scalar_drift():
    evidence = _chunk_evidence_fixture()
    evidence["decisions"][0]["advantage"] += 0.25
    _rehash_chunk(evidence)
    with pytest.raises(verifier.VerifierError, match="advantage"):
        verifier.verify_chunk_evidence(evidence)

    evidence = _chunk_evidence_fixture()
    evidence["gradients"]["scalar_components"][
        "other_policy"
    ] += 0.25
    _rehash_chunk(evidence)
    with pytest.raises(verifier.VerifierError, match="scalar components"):
        verifier.verify_chunk_evidence(evidence)


def test_verify_chunk_evidence_rejects_gradient_sum_clip_and_install_drift():
    evidence = _chunk_evidence_fixture()
    evidence["gradients"]["component_vectors"][
        "card_reward_family_policy"
    ] = _fixture_float_payload([1.25, 0.0, 0.0], dtype="float64", shape=[3])
    _rehash_chunk(evidence)
    with pytest.raises(verifier.VerifierError, match="component sum"):
        verifier.verify_chunk_evidence(evidence)

    evidence = _chunk_evidence_fixture()
    evidence["gradients"]["clip_factor"] = 1.0
    _rehash_chunk(evidence)
    with pytest.raises(verifier.VerifierError, match="clip factor"):
        verifier.verify_chunk_evidence(evidence)

    evidence = _chunk_evidence_fixture()
    evidence["gradients"]["installed"] = _fixture_float_payload(
        [0.0, 0.0, 0.0], dtype="float32", shape=[3]
    )
    _rehash_chunk(evidence)
    with pytest.raises(verifier.VerifierError, match="installed"):
        verifier.verify_chunk_evidence(evidence)


def test_verify_chunk_evidence_rejects_component_and_consumed_metric_order_drift():
    evidence = _chunk_evidence_fixture()
    evidence["gradients"]["component_order"] = list(
        reversed(evidence["gradients"]["component_order"])
    )
    _rehash_chunk(evidence)
    with pytest.raises(verifier.VerifierError, match="component order"):
        verifier.verify_chunk_evidence(evidence)

    evidence = _chunk_evidence_fixture()
    evidence["gradients"]["consumed_torch_clipped"] = _fixture_float_payload(
        [0.5, 0.0, 0.0], dtype="float32", shape=[3]
    )
    _rehash_chunk(evidence)
    with pytest.raises(verifier.VerifierError, match="clip comparison"):
        verifier.verify_chunk_evidence(evidence)


def test_verify_chunk_evidence_enforces_zero_norm_cosine_semantics():
    evidence = _chunk_evidence_fixture()
    evidence["gradients"]["legacy"] = _fixture_float_payload(
        [0.0, 0.0, 0.0], dtype="float64", shape=[3]
    )
    evidence["gradients"]["gradient_comparison"] = {
        "cosine": 0.0,
        "cross_fitted_norm": 2.0,
        "difference_norm": 2.0,
        "dot": 0.0,
        "legacy_norm": 0.0,
    }
    _rehash_chunk(evidence)

    with pytest.raises(verifier.VerifierError, match="undefined"):
        verifier.verify_chunk_evidence(evidence)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["adam"]["parameters"][1].__setitem__(
                "post_step", 0
            ),
            "step",
        ),
        (
            lambda value: value["adam"]["parameters"][1].__setitem__(
                "post_exp_avg",
                _fixture_float_payload(
                    [0.25], dtype="float32", shape=[1]
                ),
            ),
            "first moment",
        ),
        (
            lambda value: value["gradients"].__setitem__(
                "pre_parameter_sha256", "0" * 64
            ),
            "pre-parameter hash",
        ),
    ],
)
def test_verify_chunk_evidence_replays_adam_by_parameter_layout(mutate, message):
    evidence = _chunk_evidence_fixture()
    mutate(evidence)
    _rehash_chunk(evidence)

    with pytest.raises(verifier.VerifierError, match=message):
        verifier.verify_chunk_evidence(evidence)


def test_verify_terminal_bundle_rejects_an_empty_output_root(tmp_path):
    with pytest.raises(verifier.VerifierError, match="closed terminal bundle"):
        verifier.verify_terminal_bundle(tmp_path, repo_root=ROOT)


def _write_canonical(path: Path, value: object) -> bytes:
    payload = _fixture_canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def _git_fixture(repo_root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _git_commit_fixture(repo_root: Path, message: str) -> str:
    _git_fixture(repo_root, "add", "-A")
    _git_fixture(repo_root, "commit", "-q", "-m", message)
    return _git_fixture(repo_root, "rev-parse", "HEAD").decode("ascii").strip()


def _source_inventory_fixture(
    *,
    repo_root: Path = ROOT,
    commit: str | None = None,
    registration_schema_version: str = verifier.REGISTRATION_SCHEMA_VERSION,
) -> dict[str, object]:
    modules, dependencies = verifier._declared_source_rows(
        registration_schema_version
    )
    registered_commit = commit or _git_fixture(
        repo_root, "rev-parse", "HEAD"
    ).decode("ascii").strip()

    def bind(row):
        payload = _git_fixture(
            repo_root, "show", f"{registered_commit}:{row['path']}"
        )
        return {
            **row,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }

    body = {
        "modules": [bind(row) for row in modules],
        "public_dependencies": [bind(row) for row in dependencies],
        "schema_version": verifier.SOURCE_INVENTORY_SCHEMA_VERSION,
    }
    return {
        **body,
        "inventory_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(body)
        ).hexdigest(),
    }


def _file_binding_fixture(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {
        "path": path.resolve().as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _registration_fixture(
    output: Path,
    *,
    repo_root: Path = ROOT,
    commit: str | None = None,
    source_schema_version: str = verifier.REGISTRATION_SCHEMA_VERSION,
) -> dict[str, object]:
    registered_commit = commit or _git_fixture(
        repo_root, "rev-parse", "HEAD"
    ).decode("ascii").strip()
    excluded = list(
        range(
            verifier.PREVIOUS_UNTOUCHED_HOLDOUT_START,
            verifier.PREVIOUS_UNTOUCHED_HOLDOUT_END + 1,
        )
    )
    seed_inventory = {
        "canonical_search_start": 0,
        "excluded_seed_count": len(excluded),
        "excluded_seeds": excluded,
        "repository_commit": registered_commit,
        "reserved_seed_ranges": [
            {
                "end_inclusive": verifier.PREVIOUS_UNTOUCHED_HOLDOUT_END,
                "name": "previous_untouched_holdout",
                "start_inclusive": verifier.PREVIOUS_UNTOUCHED_HOLDOUT_START,
            }
        ],
        "row_count": 0,
        "rows": [],
        "schema_version": verifier.SEED_INVENTORY_SCHEMA_VERSION,
        "source_bindings": [],
        "source_count": 0,
    }
    seeds = list(range(verifier.SCHEDULED_TRAJECTORIES))
    chunks = [
        seeds[index : index + verifier.TRAJECTORIES_PER_CHUNK]
        for index in range(0, len(seeds), verifier.TRAJECTORIES_PER_CHUNK)
    ]
    schedule = {
        "canonical_search_start": 0,
        "chunk_count": verifier.CHUNK_COUNT,
        "chunks": chunks,
        "episodes_per_chunk": verifier.TRAJECTORIES_PER_CHUNK,
        "inventory_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(seed_inventory)
        ).hexdigest(),
        "seeds": seeds,
        "seeds_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(seeds)
        ).hexdigest(),
        "selection_schema_version": verifier.FRESH_SCHEDULE_SCHEMA_VERSION,
    }
    bound_file = _file_binding_fixture(Path(verifier.__file__))
    provenance = {
        "build": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3"
        },
        "module_sha256": bound_file["sha256"],
    }
    isolation = {
        "communication_mod_config": bound_file,
        "production_checkpoints": {
            "file_count": 0,
            "root": ROOT.resolve().as_posix(),
            "sha256": hashlib.sha256(b"").hexdigest(),
            "size_bytes": 0,
        },
    }
    return {
        "authority": dict(verifier._AUTHORITY),
        "contract": verifier._expected_contract(),
        "isolation_identity": isolation,
        "native_identity": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "dll_directories": [],
            "module": bound_file,
            "provenance": provenance,
            "provenance_sha256": hashlib.sha256(
                _fixture_canonical_json_bytes(provenance)
            ).hexdigest(),
        },
        "output_inventory": verifier._expected_output_inventory(),
        "output_root": output.resolve().as_posix(),
        "pushed_remote_ref": "origin/master",
        "registration_id": "synthetic-cross-fitted-terminal",
        "repository_commit": registered_commit,
        "runtime_identity": {
            "device": "cpu",
            "python_executable": Path(sys.executable).resolve().as_posix(),
            "python_version": "synthetic-source-only",
            "torch_version": "synthetic-source-only",
        },
        "schedule": schedule,
        "schema_version": verifier.REGISTRATION_SCHEMA_VERSION,
        "seed_inventory": seed_inventory,
        "source_inventory": _source_inventory_fixture(
            repo_root=repo_root,
            commit=registered_commit,
            registration_schema_version=source_schema_version,
        ),
    }


_READINESS_AUTHORITY_NAMES = (
    "causal_claim",
    "communication_mod",
    "empirical_registration",
    "evaluation",
    "execution_authorization",
    "execution_request",
    "external_approval",
    "formal_rl",
    "gameplay",
    "model_fitting",
    "model_loading",
    "native_loading",
    "ope",
    "policy_quality",
    "promotion",
    "qualification",
    "seed_access",
    "training",
)
_READINESS_SOURCE_PATHS = (
    (
        "readiness_auditor_source",
        "analysis_scripts/noncombat_cross_fitted_empirical_successor_readiness.py",
    ),
    (
        "readiness_verifier_source",
        "analysis_scripts/verify_noncombat_cross_fitted_empirical_successor_readiness.py",
    ),
    (
        "seed_inventory_source",
        "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_seed_inventory.py",
    ),
    (
        "control_plane_source",
        "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_experiment.py",
    ),
    (
        "terminal_verifier_source",
        "analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_experiment.py",
    ),
    ("consumed_registration", "reports/consumed_registration.json"),
    (
        "successor_contract",
        "openspec/specs/noncombat-cross-fitted-hierarchical-learning-successor/spec.md",
    ),
)
_READINESS_CANDIDATE_PATH = (
    "reports/synthetic_readiness/candidate_seed_inventory.json.gz"
)
_READINESS_REPORT_PATH = "reports/synthetic_readiness/readiness_report.json"
_READINESS_REPORT_MARKDOWN_PATH = (
    "reports/synthetic_readiness/readiness_report.md"
)
_READINESS_RECEIPT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-empirical-successor-readiness-attempt-verified-v1"
)
_READINESS_RECEIPT_ROOT = (
    "reports/noncombat_cross_fitted_empirical_successor_readiness_attempts"
)


def _deterministic_gzip_fixture(payload: bytes, *, compresslevel: int = 9) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="",
        mode="wb",
        compresslevel=compresslevel,
        fileobj=buffer,
        mtime=0,
    ) as stream:
        stream.write(payload)
    return buffer.getvalue()


def _readiness_authority_fixture() -> dict[str, bool]:
    return {name: False for name in _READINESS_AUTHORITY_NAMES}


def _initialize_compact_source_repo(tmp_path: Path) -> tuple[Path, str, bytes]:
    repo = tmp_path / "source-repo"
    repo.mkdir()
    _git_fixture(repo, "init", "-q", "-b", "master")
    _git_fixture(repo, "config", "user.email", "verifier@example.invalid")
    _git_fixture(repo, "config", "user.name", "Verifier Fixture")
    _git_fixture(repo, "config", "core.autocrlf", "false")
    _git_fixture(repo, "config", "core.longpaths", "true")

    modules, dependencies = verifier._declared_source_rows(
        verifier.REGISTRATION_V2_SCHEMA_VERSION
    )
    source_paths = {
        row["path"] for row in [*modules, *dependencies]
    } | {path for _role, path in _READINESS_SOURCE_PATHS}
    for relative in sorted(source_paths):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"fixture source: {relative}\n".encode("ascii"))

    consumed_seeds = list(range(1_000, 1_000 + verifier.SCHEDULED_TRAJECTORIES))
    consumed_chunks = [
        consumed_seeds[index : index + verifier.TRAJECTORIES_PER_CHUNK]
        for index in range(0, len(consumed_seeds), verifier.TRAJECTORIES_PER_CHUNK)
    ]
    consumed_registration = {
        "registration_id": "synthetic-consumed-registration",
        "schedule": {
            "canonical_search_start": 0,
            "chunk_count": verifier.CHUNK_COUNT,
            "chunks": consumed_chunks,
            "episodes_per_chunk": verifier.TRAJECTORIES_PER_CHUNK,
            "inventory_sha256": "a" * 64,
            "seeds": consumed_seeds,
            "seeds_sha256": hashlib.sha256(
                _fixture_canonical_json_bytes(consumed_seeds)
            ).hexdigest(),
            "selection_schema_version": verifier.FRESH_SCHEDULE_SCHEMA_VERSION,
        },
    }
    consumed_payload = _write_canonical(
        repo / "reports/consumed_registration.json", consumed_registration
    )
    source_commit = _git_commit_fixture(repo, "source identity")
    return repo, source_commit, consumed_payload


def _compact_candidate_fixture(
    source_commit: str, consumed_payload: bytes
) -> dict[str, object]:
    excluded = list(
        range(
            verifier.PREVIOUS_UNTOUCHED_HOLDOUT_START,
            verifier.PREVIOUS_UNTOUCHED_HOLDOUT_END + 1,
        )
    )
    inventory = {
        "canonical_search_start": 0,
        "excluded_seed_count": len(excluded),
        "excluded_seeds": excluded,
        "repository_commit": source_commit,
        "reserved_seed_ranges": [
            {
                "end_inclusive": verifier.PREVIOUS_UNTOUCHED_HOLDOUT_END,
                "name": "previous_untouched_holdout",
                "start_inclusive": verifier.PREVIOUS_UNTOUCHED_HOLDOUT_START,
            }
        ],
        "row_count": 0,
        "rows": [],
        "schema_version": verifier.SEED_INVENTORY_SCHEMA_VERSION,
        "source_bindings": [],
        "source_count": 0,
    }
    candidate_seeds = list(range(verifier.SCHEDULED_TRAJECTORIES))
    consumed_seeds = list(
        range(1_000, 1_000 + verifier.SCHEDULED_TRAJECTORIES)
    )
    return {
        "authority": _readiness_authority_fixture(),
        "candidate_schedule": {
            "canonical_search_start": 0,
            "inventory_sha256": hashlib.sha256(
                _fixture_canonical_json_bytes(inventory)
            ).hexdigest(),
            "schema_version": verifier.FRESH_SCHEDULE_SCHEMA_VERSION,
            "seed_count": verifier.SCHEDULED_TRAJECTORIES,
            "seeds": candidate_seeds,
        },
        "consumed_cohort": {
            "registration_binding": {
                "path": "reports/consumed_registration.json",
                "sha256": hashlib.sha256(consumed_payload).hexdigest(),
                "size_bytes": len(consumed_payload),
            },
            "registration_id": "synthetic-consumed-registration",
            "seed_count": verifier.SCHEDULED_TRAJECTORIES,
            "seeds": consumed_seeds,
            "seeds_sha256": hashlib.sha256(
                _fixture_canonical_json_bytes(consumed_seeds)
            ).hexdigest(),
        },
        "disjointness": {
            "collision_count": 0,
            "collisions": [],
            "status": "passed",
        },
        "historical_seed_inventory": inventory,
        "schema_version": (
            "noncombat-cross-fitted-empirical-successor-readiness-candidate-v1"
        ),
        "source_commit": source_commit,
    }


def _readiness_source_binding_fixture(
    repo: Path, source_commit: str
) -> dict[str, object]:
    rows = []
    for role, path in _READINESS_SOURCE_PATHS:
        payload = _git_fixture(repo, "show", f"{source_commit}:{path}")
        rows.append(
            {
                "path": path,
                "role": role,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    return {
        "bindings": rows,
        "bindings_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(rows)
        ).hexdigest(),
        "head_commit": source_commit,
        "origin_master_commit": source_commit,
        "source_commit": source_commit,
        "status": "passed",
        "tracked_clean": True,
    }


def _readiness_report_fixture(
    *,
    repo: Path,
    source_commit: str,
    candidate: dict[str, object],
    candidate_payload: bytes,
    candidate_stored: bytes,
) -> dict[str, object]:
    candidate_seeds = candidate["candidate_schedule"]["seeds"]
    consumed_seeds = candidate["consumed_cohort"]["seeds"]
    body = {
        "audit_id": "synthetic-cross-fitted-readiness-r3",
        "authority": _readiness_authority_fixture(),
        "budget": {
            "ceiling_seconds": "14400.000",
            "control_reservation_seconds": "3600.000",
            "historical_charged_seconds": "2165.452",
            "historical_counts": {
                "checkpoint_count": 8,
                "evaluation_episodes": 0,
                "optimizer_updates": 8,
                "training_chunk_count": 8,
                "training_episodes": 512,
            },
            "historical_multiplier": "3.000",
            "margin_seconds": "4303.644",
            "projected_total_seconds": "10096.356",
            "status": "passed",
        },
        "candidate_artifact_binding": {
            "canonical_sha256": hashlib.sha256(candidate_payload).hexdigest(),
            "canonical_size_bytes": len(candidate_payload),
            "encoding": "gzip-mtime-zero-v1",
            "path": "candidate_seed_inventory.json.gz",
            "sha256": hashlib.sha256(candidate_stored).hexdigest(),
            "size_bytes": len(candidate_stored),
        },
        "cohort": {
            "candidate_seed_count": len(candidate_seeds),
            "candidate_seeds_sha256": hashlib.sha256(
                _fixture_canonical_json_bytes(candidate_seeds)
            ).hexdigest(),
            "collision_count": candidate["disjointness"]["collision_count"],
            "collisions": candidate["disjointness"]["collisions"],
            "consumed_seed_count": len(consumed_seeds),
            "consumed_seeds_sha256": hashlib.sha256(
                _fixture_canonical_json_bytes(consumed_seeds)
            ).hexdigest(),
            "status": candidate["disjointness"]["status"],
        },
        "decision": {"failed_gates": [], "reason": "go", "status": "go"},
        "eligibility": {
            "empirical_successor_registration_proposal_eligible": True
        },
        "gates": {
            "artifact_binding": "passed",
            "budget_binding": "passed",
            "cohort_not_fresh": "passed",
            "control_plane_scaling": "passed",
            "rehearsal_boundary": "passed",
            "source_binding": "passed",
        },
        "limitations": [
            "This source-only result does not establish policy quality or causal effect.",
            "Candidate seed integers are data only and were not used to construct an environment.",
            "A go result permits only a separately reviewed empirical registration proposal.",
            "Native loading, seed access, fitting, training, evaluation, gameplay, qualification, and promotion remain unauthorized.",
        ],
        "rehearsal": {"status": "passed"},
        "schema_version": (
            "noncombat-cross-fitted-empirical-successor-readiness-report-v1"
        ),
        "source_binding": _readiness_source_binding_fixture(repo, source_commit),
        "source_commit": source_commit,
    }
    return {
        **body,
        "readiness_identity_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(body)
        ).hexdigest(),
    }


def _verification_receipt_fixture(
    *,
    source_commit: str,
    candidate: dict[str, object],
    candidate_stored: bytes,
    report_payload: bytes,
    report_markdown_payload: bytes,
) -> dict[str, object]:
    publication_bindings = {
        "candidate_seed_inventory.json.gz": {
            "sha256": hashlib.sha256(candidate_stored).hexdigest(),
            "size_bytes": len(candidate_stored),
        },
        "readiness_report.json": {
            "sha256": hashlib.sha256(report_payload).hexdigest(),
            "size_bytes": len(report_payload),
        },
        "readiness_report.md": {
            "sha256": hashlib.sha256(report_markdown_payload).hexdigest(),
            "size_bytes": len(report_markdown_payload),
        },
    }
    report = json.loads(report_payload)
    body = {
        "attempt_sha256": "a" * 64,
        "intended_output_dir": "D:/synthetic/readiness-publication",
        "publication_bindings": publication_bindings,
        "schema_version": _READINESS_RECEIPT_SCHEMA_VERSION,
        "source_commit": source_commit,
        "staging_dir": "D:/synthetic/.readiness-publication.staging",
        "status": "staging_independently_verified",
        "verification": {
            "candidate_inventory_sha256": publication_bindings[
                "candidate_seed_inventory.json.gz"
            ]["sha256"],
            "decision": "go",
            "independent_inventory_sha256": candidate["candidate_schedule"][
                "inventory_sha256"
            ],
            "proposal_eligible": True,
            "readiness_identity_sha256": report[
                "readiness_identity_sha256"
            ],
            "source_commit": source_commit,
            "status": "verified",
        },
    }
    return {
        **body,
        "verification_receipt_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(body)
        ).hexdigest(),
    }


def _compact_registration_fixture(
    tmp_path: Path,
    *,
    candidate_mutator=None,
    receipt_mutator=None,
    report_mutator=None,
    compresslevel: int = 9,
) -> dict[str, object]:
    repo, source_commit, consumed_payload = _initialize_compact_source_repo(
        tmp_path
    )
    candidate = _compact_candidate_fixture(source_commit, consumed_payload)
    if candidate_mutator is not None:
        candidate_mutator(candidate)
    candidate_payload = _fixture_canonical_json_bytes(candidate)
    candidate_stored = _deterministic_gzip_fixture(
        candidate_payload, compresslevel=compresslevel
    )
    report = _readiness_report_fixture(
        repo=repo,
        source_commit=source_commit,
        candidate=candidate,
        candidate_payload=candidate_payload,
        candidate_stored=candidate_stored,
    )
    if report_mutator is not None:
        report_mutator(report)
        report_body = {
            key: value
            for key, value in report.items()
            if key != "readiness_identity_sha256"
        }
        report["readiness_identity_sha256"] = hashlib.sha256(
            _fixture_canonical_json_bytes(report_body)
        ).hexdigest()
    report_payload = _fixture_canonical_json_bytes(report)
    report_markdown_payload = b"# Synthetic readiness report\n"
    receipt = _verification_receipt_fixture(
        source_commit=source_commit,
        candidate=candidate,
        candidate_stored=candidate_stored,
        report_payload=report_payload,
        report_markdown_payload=report_markdown_payload,
    )
    if receipt_mutator is not None:
        receipt_mutator(receipt)
        receipt_body = {
            key: value
            for key, value in receipt.items()
            if key != "verification_receipt_sha256"
        }
        receipt["verification_receipt_sha256"] = hashlib.sha256(
            _fixture_canonical_json_bytes(receipt_body)
        ).hexdigest()
    receipt_payload = _fixture_canonical_json_bytes(receipt)
    receipt_path = (
        f"{_READINESS_RECEIPT_ROOT}/{source_commit}/attempt_verified.json"
    )
    candidate_path = repo / _READINESS_CANDIDATE_PATH
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(candidate_stored)
    (repo / _READINESS_REPORT_PATH).write_bytes(report_payload)
    (repo / _READINESS_REPORT_MARKDOWN_PATH).write_bytes(
        report_markdown_payload
    )
    _write_canonical(repo / receipt_path, receipt)
    publication_commit = _git_commit_fixture(repo, "readiness publication")
    _git_fixture(
        repo,
        "update-ref",
        "refs/remotes/origin/master",
        publication_commit,
    )

    output = tmp_path / "terminal-bundle"
    registration = _registration_fixture(
        output,
        repo_root=repo,
        commit=source_commit,
        source_schema_version=verifier.REGISTRATION_V2_SCHEMA_VERSION,
    )
    registration["schema_version"] = (
        "noncombat-cross-fitted-hierarchical-learning-registration-v2"
    )
    del registration["seed_inventory"]
    registration["readiness_evidence"] = {
        "candidate_artifact": {
            "canonical_sha256": hashlib.sha256(candidate_payload).hexdigest(),
            "canonical_size_bytes": len(candidate_payload),
            "encoding": "gzip-mtime-zero-v1",
            "path": _READINESS_CANDIDATE_PATH,
            "sha256": hashlib.sha256(candidate_stored).hexdigest(),
            "size_bytes": len(candidate_stored),
        },
        "publication_commit": publication_commit,
        "readiness_report": {
            "path": _READINESS_REPORT_PATH,
            "readiness_identity_sha256": report[
                "readiness_identity_sha256"
            ],
            "sha256": hashlib.sha256(report_payload).hexdigest(),
            "size_bytes": len(report_payload),
        },
        "verification_receipt": {
            "path": receipt_path,
            "sha256": hashlib.sha256(receipt_payload).hexdigest(),
            "size_bytes": len(receipt_payload),
            "verification_receipt_sha256": receipt[
                "verification_receipt_sha256"
            ],
        },
    }
    return {
        "candidate": candidate,
        "output": output,
        "publication_commit": publication_commit,
        "registration": registration,
        "receipt": receipt,
        "receipt_path": receipt_path,
        "repo": repo,
        "report": report,
        "source_commit": source_commit,
    }


def _authorization_documents_fixture(registration):
    registration_sha256 = hashlib.sha256(
        _fixture_canonical_json_bytes(registration)
    ).hexdigest()
    body = {
        "authority": dict(verifier._AUTHORITY),
        "native_identity": registration["native_identity"],
        "operations": {
            "baseline_fitting": "four-fold-cross-fitted-ridge-v1",
            "environment_construction": True,
            "native_loading": True,
            "optimizer_updates_maximum": 8,
            "policy_training": True,
        },
        "output_root": registration["output_root"],
        "registration_id": registration["registration_id"],
        "registration_sha256": registration_sha256,
        "repository_commit": registration["repository_commit"],
        "request_id": registration["registration_id"] + ":execution-request-v1",
        "requested_execution_authority": dict(verifier._EXECUTION_AUTHORITY),
        "resources": registration["contract"]["limits"],
        "resume": registration["contract"]["lifecycle"],
        "runtime_identity": registration["runtime_identity"],
        "schedule": registration["schedule"],
        "schema_version": verifier.EXECUTION_REQUEST_SCHEMA_VERSION,
        "source_inventory_sha256": registration["source_inventory"][
            "inventory_sha256"
        ],
    }
    request = {
        **body,
        "request_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(body)
        ).hexdigest(),
    }
    approval_body = {
        "approved_at": "2026-08-06T00:00:00+08:00",
        "approved_request_sha256": request["request_sha256"],
        "provenance": {
            "message_id": "synthetic-message",
            "source": "external-human-message",
            "task_id": "synthetic-task",
        },
        "schema_version": verifier.EXTERNAL_APPROVAL_SCHEMA_VERSION,
        "verbatim_approval_text": "approved " + request["request_sha256"],
    }
    approval = {
        **approval_body,
        "approval_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(approval_body)
        ).hexdigest(),
    }
    authorization_body = {
        "approval": approval,
        "authorization_id": registration["registration_id"] + ":authorization-v1",
        "authority": dict(verifier._EXECUTION_AUTHORITY),
        "registration_id": registration["registration_id"],
        "registration_sha256": registration_sha256,
        "request_id": request["request_id"],
        "request_sha256": request["request_sha256"],
        "schema_version": verifier.AUTHORIZATION_SCHEMA_VERSION,
    }
    authorization = {
        **authorization_body,
        "authorization_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(authorization_body)
        ).hexdigest(),
    }
    identity = {
        "authorization_sha256": authorization["authorization_sha256"],
        "logical_execution_id": registration["registration_id"],
        "registration_sha256": registration_sha256,
        "request_sha256": request["request_sha256"],
    }
    return request, approval, authorization, identity


def _delegated_authorization_documents_fixture(registration):
    request, _approval, _authorization, _identity = (
        _authorization_documents_fixture(registration)
    )
    delegation_body = {
        "exclusions": list(verifier.STANDING_DELEGATION_EXCLUSIONS),
        "grant": {
            "granted_at": "2026-08-08T18:58:05.0571093+08:00",
            "provenance": {
                "message_id": "synthetic-standing-delegation",
                "source": "external-human-message",
                "task_id": "independent-verifier-test",
            },
            "verbatim_text": "The solo maintainer delegates exact requests.",
        },
        "revocation": verifier.STANDING_DELEGATION_REVOCATION,
        "schema_version": verifier.STANDING_DELEGATION_SCHEMA_VERSION,
        "scope": {
            "pushed_remote_ref": "origin/master",
            "registration_id_prefix": verifier.DELEGATED_REGISTRATION_ID_PREFIX,
            "request_class": verifier.DELEGATED_REQUEST_CLASS,
        },
    }
    delegation = {
        **delegation_body,
        "delegation_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(delegation_body)
        ).hexdigest(),
    }
    resolution = {
        "delegation_sha256": delegation["delegation_sha256"],
        "request_sha256": request["request_sha256"],
        "resolved_at": "2026-08-08T19:00:00+08:00",
        "resolver": verifier.DELEGATED_APPROVAL_RESOLVER,
    }
    approval_body = {
        "approval_mode": "standing-delegation",
        "approved_request_sha256": request["request_sha256"],
        "delegation": delegation,
        "resolution": resolution,
        "schema_version": verifier.DELEGATED_APPROVAL_SCHEMA_VERSION,
    }
    approval = {
        **approval_body,
        "approval_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(approval_body)
        ).hexdigest(),
    }
    authorization_body = {
        "approval": approval,
        "authorization_id": registration["registration_id"] + ":authorization-v1",
        "authority": dict(verifier._EXECUTION_AUTHORITY),
        "registration_id": registration["registration_id"],
        "registration_sha256": request["registration_sha256"],
        "request_id": request["request_id"],
        "request_sha256": request["request_sha256"],
        "schema_version": verifier.AUTHORIZATION_SCHEMA_VERSION,
    }
    authorization = {
        **authorization_body,
        "authorization_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(authorization_body)
        ).hexdigest(),
    }
    return request, delegation, approval, authorization


def test_delegated_approval_v2_is_independently_verified_and_fail_closed(tmp_path):
    registration = _registration_fixture(tmp_path / "delegated-output")
    registration["registration_id"] = (
        verifier.DELEGATED_REGISTRATION_ID_PREFIX + "synthetic"
    )
    request, delegation, approval, authorization = (
        _delegated_authorization_documents_fixture(registration)
    )

    normalized_approval = verifier._validate_approval(
        approval,
        registration=registration,
        request=request,
    )
    assert normalized_approval == approval
    normalized_authorization, identity = verifier._validate_authorization(
        authorization,
        registration=registration,
        request=request,
        approval=normalized_approval,
    )
    assert normalized_authorization == authorization
    assert identity["request_sha256"] == request["request_sha256"]
    assert approval["delegation"] == delegation
    assert "verbatim_approval_text" not in approval

    drifted = copy.deepcopy(approval)
    drifted["resolution"]["delegation_sha256"] = "f" * 64
    body = {key: value for key, value in drifted.items() if key != "approval_sha256"}
    drifted["approval_sha256"] = hashlib.sha256(
        _fixture_canonical_json_bytes(body)
    ).hexdigest()
    with pytest.raises(verifier.VerifierError, match="resolution"):
        verifier._validate_approval(
            drifted,
            registration=registration,
            request=request,
        )

    _request, historical, _authorization, _identity = (
        _authorization_documents_fixture(registration)
    )
    assert verifier._validate_approval(
        historical,
        registration=registration,
        request=request,
    ) == historical


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("grant", "delegation identity"),
        ("scope", "delegation scope"),
        ("hybrid", "fields"),
        ("request", "resolution"),
    ],
)
def test_delegated_approval_v2_independently_rejects_tampering(
    tmp_path, case, message
):
    registration = _registration_fixture(tmp_path / f"delegated-{case}")
    registration["registration_id"] = (
        verifier.DELEGATED_REGISTRATION_ID_PREFIX + "synthetic"
    )
    request, _delegation, approval, _authorization = (
        _delegated_authorization_documents_fixture(registration)
    )
    drifted = copy.deepcopy(approval)
    if case == "grant":
        drifted["delegation"]["grant"]["verbatim_text"] = "changed"
    elif case == "scope":
        drifted["delegation"]["scope"]["pushed_remote_ref"] = "other"
        delegation_body = {
            key: value
            for key, value in drifted["delegation"].items()
            if key != "delegation_sha256"
        }
        drifted["delegation"]["delegation_sha256"] = hashlib.sha256(
            _fixture_canonical_json_bytes(delegation_body)
        ).hexdigest()
        drifted["resolution"]["delegation_sha256"] = drifted["delegation"][
            "delegation_sha256"
        ]
    elif case == "hybrid":
        drifted["verbatim_approval_text"] = "generated text"
    elif case == "request":
        drifted["resolution"]["request_sha256"] = "f" * 64
    approval_body = {
        key: value for key, value in drifted.items() if key != "approval_sha256"
    }
    drifted["approval_sha256"] = hashlib.sha256(
        _fixture_canonical_json_bytes(approval_body)
    ).hexdigest()

    with pytest.raises(verifier.VerifierError, match=message):
        verifier._validate_approval(
            drifted,
            registration=registration,
            request=request,
        )


def _encode_python_state(value):
    if isinstance(value, tuple):
        return {"items": [_encode_python_state(item) for item in value], "type": "tuple"}
    return value


def _generator_state_fixture(raw: bytes) -> dict[str, object]:
    return {
        "data_base64": base64.b64encode(raw).decode("ascii"),
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "dtype": "uint8",
        "shape": [len(raw)],
    }


def _runtime_checkpoint_fixture(state, coordinates, action_state):
    model = [
        {
            "name": name,
            "tensor": _fixture_float_payload(
                state["parameters"][index], dtype="float32", shape=shape
            ),
        }
        for index, (name, shape) in enumerate((('weight', [2]), ('bias', [1])))
    ]
    optimizer_rows = []
    for index, (name, _shape) in enumerate((('weight', [2]), ('bias', [1]))):
        if state["initialized"]:
            optimizer_rows.append(
                {
                    "exp_avg": _fixture_float_payload(
                        state["exp_avg"][index],
                        dtype="float32",
                        shape=[len(state["exp_avg"][index])],
                    ),
                    "exp_avg_sq": _fixture_float_payload(
                        state["exp_avg_sq"][index],
                        dtype="float32",
                        shape=[len(state["exp_avg_sq"][index])],
                    ),
                    "initialized": True,
                    "name": name,
                    "step": state["step"],
                }
            )
        else:
            optimizer_rows.append(
                {
                    "exp_avg": None,
                    "exp_avg_sq": None,
                    "initialized": False,
                    "name": name,
                    "step": 0,
                }
            )
    body = {
        "action_generator_state": _generator_state_fixture(action_state),
        "coordinates": dict(coordinates),
        "model": model,
        "optimizer": {
            "betas": [0.9, 0.999],
            "epsilon": 1e-8,
            "learning_rate": 0.001,
            "parameters": optimizer_rows,
            "weight_decay": 0.0,
        },
        "python_rng_state": _encode_python_state(random.Random(0).getstate()),
        "runtime_metadata": verifier._expected_runtime_metadata(),
        "schema_version": verifier.RUNTIME_CHECKPOINT_SCHEMA_VERSION,
    }
    return {
        **body,
        "checkpoint_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(body)
        ).hexdigest(),
    }


def _opaque_binding_fixture(payload):
    encoded = _fixture_canonical_json_bytes(payload)
    return {
        "payload": payload,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "size_bytes": len(encoded),
    }


def _advance_adam_fixture(state, installed_by_parameter):
    next_parameters = []
    next_exp_avg = []
    next_exp_avg_sq = []
    rows = []
    for index, (name, shape) in enumerate((('weight', [2]), ('bias', [1]))):
        pre_parameters = tuple(state["parameters"][index])
        pre_avg = tuple(state["exp_avg"][index])
        pre_sq = tuple(state["exp_avg_sq"][index])
        gradient = tuple(installed_by_parameter[index])
        expected_step = state["step"] + 1
        first = tuple(
            _float32(0.9 * pre_avg[position] + 0.1 * gradient[position])
            for position in range(len(gradient))
        )
        second = tuple(
            _float32(
                0.999 * pre_sq[position]
                + 0.001 * gradient[position] * gradient[position]
            )
            for position in range(len(gradient))
        )
        step_size = 0.001 / (1.0 - 0.9**expected_step)
        correction2 = math.sqrt(1.0 - 0.999**expected_step)
        parameters = tuple(
            _float32(
                pre_parameters[position]
                - step_size
                * first[position]
                / (math.sqrt(second[position]) / correction2 + 1e-8)
            )
            for position in range(len(gradient))
        )
        rows.append(
            {
                "installed_gradient": _fixture_float_payload(
                    gradient, dtype="float32", shape=shape
                ),
                "name": name,
                "post_exp_avg": _fixture_float_payload(
                    first, dtype="float32", shape=shape
                ),
                "post_exp_avg_sq": _fixture_float_payload(
                    second, dtype="float32", shape=shape
                ),
                "post_parameter": _fixture_float_payload(
                    parameters, dtype="float32", shape=shape
                ),
                "post_step": expected_step,
                "pre_exp_avg": _fixture_float_payload(
                    pre_avg, dtype="float32", shape=shape
                ),
                "pre_exp_avg_sq": _fixture_float_payload(
                    pre_sq, dtype="float32", shape=shape
                ),
                "pre_parameter": _fixture_float_payload(
                    pre_parameters, dtype="float32", shape=shape
                ),
                "pre_step": state["step"],
                "shape": shape,
            }
        )
        next_parameters.append(parameters)
        next_exp_avg.append(first)
        next_exp_avg_sq.append(second)
    return rows, {
        "exp_avg": next_exp_avg,
        "exp_avg_sq": next_exp_avg_sq,
        "initialized": True,
        "parameters": next_parameters,
        "step": state["step"] + 1,
    }


def _terminal_chunk_fixture(
    base,
    *,
    chunk_index,
    seeds,
    adam_state,
    action_state,
):
    chunk = copy.deepcopy(base)
    old_trajectories = sorted(
        {row["trajectory_id"] for row in chunk["decisions"]},
        key=lambda identity: next(
            row["seed"] for row in chunk["decisions"] if row["trajectory_id"] == identity
        ),
    )
    identity_map = {
        old: f"trajectory-{seed:06d}"
        for old, seed in zip(old_trajectories, seeds, strict=True)
    }
    seed_by_identity = dict(zip(identity_map.values(), seeds, strict=True))
    for row in chunk["decisions"]:
        trajectory_id = identity_map[row["trajectory_id"]]
        row["trajectory_id"] = trajectory_id
        row["seed"] = seed_by_identity[trajectory_id]
        row["baseline_fit_trajectory_ids"] = sorted(
            identity_map[item] for item in row["baseline_fit_trajectory_ids"]
        )
        decision_id = f"{trajectory_id}:decision-{row['decision_index']}"
        row["decision_id"] = decision_id
        row["diagnostic"]["decision_id"] = decision_id
        row["diagnostic"]["chunk_index"] = chunk_index
    chunk["baseline"]["fold_trajectories"] = {
        fold: [identity_map[item] for item in identities]
        for fold, identities in chunk["baseline"]["fold_trajectories"].items()
    }
    for model in chunk["baseline"]["models"]:
        model["fit_trajectory_ids"] = sorted(
            identity_map[item] for item in model["fit_trajectory_ids"]
        )
        model["held_out_trajectory_ids"] = [
            identity_map[item] for item in model["held_out_trajectory_ids"]
        ]
    chunk["chunk_index"] = chunk_index
    chunk["torch_version"] = "synthetic-source-only"
    installed = verifier.decode_float_payload(chunk["gradients"]["installed"])
    adam_rows, next_adam_state = _advance_adam_fixture(
        adam_state, (installed[:2], installed[2:])
    )
    chunk["adam"]["parameters"] = adam_rows
    parameter_bytes = b"".join(
        struct.pack("<f", value)
        for parameter in adam_state["parameters"]
        for value in parameter
    )
    chunk["gradients"]["pre_parameter_sha256"] = hashlib.sha256(
        parameter_bytes
    ).hexdigest()
    current_action_state = action_state
    for decision_offset, row in enumerate(chunk["decisions"]):
        next_action_state = (
            f"rng-{chunk_index}-{decision_offset + 1}".encode("ascii")
        )
        row["diagnostic"]["action_generator_state_sha256"] = {
            "after_conditional": hashlib.sha256(next_action_state).hexdigest(),
            "after_family": hashlib.sha256(
                current_action_state + b":family"
            ).hexdigest(),
            "before_family": hashlib.sha256(current_action_state).hexdigest(),
        }
        current_action_state = next_action_state
    return _rehash_chunk(chunk), next_adam_state, current_action_state


def _artifact_inventory_fixture(output: Path, excluded=()):
    excluded = set(excluded) | {verifier.LEASE_FILENAME}
    rows = []
    for path in sorted(
        candidate
        for candidate in output.rglob("*")
        if candidate.is_file()
        and candidate.relative_to(output).as_posix() not in excluded
    ):
        relative = path.relative_to(output).as_posix()
        stored = path.read_bytes()
        if relative.endswith(".gz"):
            uncompressed = gzip.decompress(stored)
            encoding = "deterministic-gzip-v1"
        else:
            uncompressed = stored
            encoding = "identity-bytes-v1"
        rows.append(
            {
                "encoding": encoding,
                "path": relative,
                "stored_sha256": hashlib.sha256(stored).hexdigest(),
                "stored_size_bytes": len(stored),
                "uncompressed_sha256": hashlib.sha256(uncompressed).hexdigest(),
                "uncompressed_size_bytes": len(uncompressed),
            }
        )
    return {
        "artifacts": rows,
        "stored_size_bytes": sum(row["stored_size_bytes"] for row in rows),
        "uncompressed_size_bytes": sum(
            row["uncompressed_size_bytes"] for row in rows
        ),
    }


def _terminal_bundle_fixture(
    tmp_path,
    *,
    registration=None,
    resume_mode=None,
    verdict="experiment_stopped_during_training_for_family_saturation",
    wrapper_runtime_mismatch=False,
    runtime_transition_mismatch=None,
    failure_witness=False,
    failure_infrastructure=False,
    failure_digest_mismatch=False,
    infrastructure_charge=False,
    fail_before_checkpoint=False,
    access_resource_mode="per_access",
    terminal_charge=True,
    trailing_infrastructure_charge=False,
):
    assert access_resource_mode in {
        "batched_reconcile",
        "checkpoint",
        "per_access",
    }
    output = tmp_path / "terminal-bundle"
    output.mkdir()
    registration = registration or _registration_fixture(output)
    assert registration["output_root"] == output.resolve().as_posix()
    request, approval, authorization, identity = _authorization_documents_fixture(
        registration
    )
    registration_sha256 = identity["registration_sha256"]
    preflight = {
        "checks": {
            "communication_mod_unchanged": True,
            "native_module_unchanged": True,
            "production_checkpoints_unchanged": True,
            "pushed_registration_exact": True,
            "pushed_source_exact": True,
            "runtime_identity_exact": True,
            "source_inventory_exact": True,
            "tracked_authorization_exact": True,
            "tracked_worktree_clean": True,
        },
        "pushed_head_commit": registration.get("readiness_evidence", {}).get(
            "publication_commit", "b" * 40
        ),
        "registration_sha256": registration_sha256,
        "repository_commit": registration["repository_commit"],
        "schema_version": verifier.SOURCE_PREFLIGHT_SCHEMA_VERSION,
    }
    if registration["schema_version"] == verifier.REGISTRATION_V2_SCHEMA_VERSION:
        preflight["checks"].update(
            {
                "readiness_candidate_exact": True,
                "readiness_publication_exact": True,
                "readiness_source_exact": True,
                "readiness_verification_receipt_exact": True,
            }
        )
    pre_isolation = {
        "isolation_identity": registration["isolation_identity"],
        "matches_registration": True,
        "phase": "pre",
        "registration_sha256": registration_sha256,
        "schema_version": verifier.ISOLATION_OBSERVATION_SCHEMA_VERSION,
    }
    for filename, document in (
        (verifier.REGISTRATION_FILENAME, registration),
        (verifier.EXECUTION_REQUEST_FILENAME, request),
        (verifier.EXTERNAL_APPROVAL_FILENAME, approval),
        (verifier.AUTHORIZATION_FILENAME, authorization),
        (verifier.SOURCE_PREFLIGHT_FILENAME, preflight),
        (verifier.PRE_ISOLATION_FILENAME, pre_isolation),
    ):
        _write_canonical(output / filename, document)

    journal_events = [
        {
            "event_index": 0,
            "identity": identity,
            "kind": "journal_opened",
            "registration_sha256": registration_sha256,
            "schedule_sha256": registration["schedule"]["seeds_sha256"],
            "schema_version": verifier.ACCESS_JOURNAL_SCHEMA_VERSION,
        }
    ]
    resources = verifier._zero_resources()
    ledger_events = [
        {
            "identity": identity,
            "kind": "resource_ledger_opened",
            "limits": verifier._resource_limits(),
            "resources": dict(resources),
            "revision": 0,
            "schema_version": verifier.RESOURCE_LEDGER_SCHEMA_VERSION,
        }
    ]

    def append_journal(kind, **values):
        journal_events.append(
            {
                **values,
                "event_index": len(journal_events),
                "kind": kind,
                "schema_version": verifier.ACCESS_JOURNAL_SCHEMA_VERSION,
            }
        )

    def append_resource(reason):
        ledger_events.append(
            {
                "kind": "resource_prefix_advanced",
                "previous_event_sha256": hashlib.sha256(
                    _fixture_canonical_json_bytes(ledger_events[-1])
                ).hexdigest(),
                "reason": reason,
                "resources": dict(resources),
                "revision": len(ledger_events),
                "schema_version": verifier.RESOURCE_LEDGER_SCHEMA_VERSION,
            }
        )

    access_ordinal = 0

    def complete_accesses(chunk_index, attempt_ordinal):
        nonlocal access_ordinal
        for seed in registration["schedule"]["chunks"][chunk_index]:
            access_ordinal += 1
            coordinate = {
                "access_ordinal": access_ordinal,
                "attempt_ordinal": attempt_ordinal,
                "chunk_index": chunk_index,
                "seed": seed,
            }
            append_journal("access_debited", **coordinate, status="debited")
            resources["environment_accesses"] += 1
            if access_resource_mode == "per_access":
                append_resource("access-journal-reconcile")
            append_journal("access_terminal", **coordinate, status="completed")
        if access_resource_mode == "batched_reconcile":
            append_resource("access-journal-reconcile")

    initial_adam_state = {
        "exp_avg": [(0.0, 0.0), (0.0,)],
        "exp_avg_sq": [(0.0, 0.0), (0.0,)],
        "initialized": False,
        "parameters": [(1.0, -2.0), (0.5,)],
        "step": 0,
    }
    action_state = b"synthetic-action-generator-state-0"
    bootstrap_runtime = _runtime_checkpoint_fixture(
        initial_adam_state,
        {
            "completed_decisions": 0,
            "completed_episodes": 0,
            "next_chunk_index": 0,
            "optimizer_updates": 0,
        },
        action_state,
    )
    bootstrap_body = {
        "authority": dict(verifier._AUTHORITY),
        "identity": identity,
        "registration_sha256": registration_sha256,
        "resource_use": verifier._zero_resources(),
        "runtime_checkpoint": _opaque_binding_fixture(bootstrap_runtime),
        "schema_version": verifier.BOOTSTRAP_SCHEMA_VERSION,
    }
    bootstrap = {
        **bootstrap_body,
        "bootstrap_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(bootstrap_body)
        ).hexdigest(),
    }
    _write_canonical(output / verifier.BOOTSTRAP_FILENAME, bootstrap)

    base_chunk = _chunk_evidence_fixture()
    adam_state = initial_adam_state
    previous_checkpoint_sha256 = bootstrap["bootstrap_sha256"]
    completed_evidences = []
    checkpoint_sha256s = []
    cumulative_stored = 0
    cumulative_uncompressed = 0
    checkpoint_dir = output / "checkpoints"
    if not fail_before_checkpoint:
        checkpoint_dir.mkdir()
    else:
        access_ordinal += 1
        coordinate = {
            "access_ordinal": access_ordinal,
            "attempt_ordinal": 0,
            "chunk_index": 0,
            "seed": registration["schedule"]["chunks"][0][0],
        }
        append_journal("access_debited", **coordinate, status="debited")
        resources["environment_accesses"] += 1
        append_resource("access-journal-reconcile")
        append_journal("access_terminal", **coordinate, status="failed")
    for chunk_index in range(0 if fail_before_checkpoint else 4):
        if resume_mode == "continue_after_checkpoint" and chunk_index == 1:
            append_journal(
                "resume_started",
                attempt_ordinal=1,
                chunk_index=1,
                mode="continue_after_checkpoint",
                status="resume_used",
            )
        complete_accesses(chunk_index, 0)
        if resume_mode == "replay_uncheckpointed_chunk" and chunk_index == 0:
            append_journal(
                "resume_started",
                attempt_ordinal=1,
                chunk_index=0,
                mode="replay_uncheckpointed_chunk",
                status="resume_used",
            )
            complete_accesses(chunk_index, 1)
        journal_prefix = b"".join(
            _fixture_canonical_json_bytes(event) for event in journal_events
        )
        evidence, next_adam_state, next_action_state = _terminal_chunk_fixture(
            base_chunk,
            chunk_index=chunk_index,
            seeds=registration["schedule"]["chunks"][chunk_index],
            adam_state=adam_state,
            action_state=action_state,
        )
        completed_evidences.append(evidence)
        completed_decisions = sum(
            len(chunk["decisions"]) for chunk in completed_evidences
        )
        post_runtime = _runtime_checkpoint_fixture(
            next_adam_state,
            {
                "completed_decisions": completed_decisions,
                "completed_episodes": (chunk_index + 1) * 64,
                "next_chunk_index": chunk_index + 1,
                "optimizer_updates": chunk_index + 1,
            },
            next_action_state,
        )
        if runtime_transition_mismatch is not None and chunk_index == 3:
            post_runtime = copy.deepcopy(post_runtime)
            if runtime_transition_mismatch == "model":
                post_runtime["model"][0]["tensor"] = _fixture_float_payload(
                    (99.0, -99.0), dtype="float32", shape=[2]
                )
            elif runtime_transition_mismatch == "adam":
                post_runtime["optimizer"]["parameters"][0]["exp_avg"] = (
                    _fixture_float_payload(
                        (0.25, -0.25), dtype="float32", shape=[2]
                    )
                )
            elif runtime_transition_mismatch == "rng":
                post_runtime["action_generator_state"] = _generator_state_fixture(
                    b"transition-mismatched-action-state"
                )
            else:
                raise AssertionError("unknown synthetic runtime mismatch")
            post_body = {
                key: value
                for key, value in post_runtime.items()
                if key != "checkpoint_sha256"
            }
            post_runtime["checkpoint_sha256"] = hashlib.sha256(
                _fixture_canonical_json_bytes(post_body)
            ).hexdigest()
        checkpoint_runtime_binding = _opaque_binding_fixture(post_runtime)
        wrapper_runtime = post_runtime
        if wrapper_runtime_mismatch and chunk_index == 3:
            wrapper_runtime = copy.deepcopy(post_runtime)
            wrapper_runtime["action_generator_state"] = _generator_state_fixture(
                b"individually-valid-but-mismatched-wrapper-state"
            )
            wrapper_body = {
                key: value
                for key, value in wrapper_runtime.items()
                if key != "checkpoint_sha256"
            }
            wrapper_runtime["checkpoint_sha256"] = hashlib.sha256(
                _fixture_canonical_json_bytes(wrapper_body)
            ).hexdigest()
        evidence_document = {
            "chunk_index": chunk_index,
            "evidence": evidence,
            "runtime_checkpoint": _opaque_binding_fixture(wrapper_runtime),
            "schema_version": verifier.CHUNK_EVIDENCE_DOCUMENT_SCHEMA_VERSION,
        }
        uncompressed = _fixture_canonical_json_bytes(evidence_document)
        stored = _gzip_with_level(uncompressed, 9)
        evidence_path = (
            checkpoint_dir / f"chunk_{chunk_index + 1:04d}_evidence.json.gz"
        )
        evidence_path.write_bytes(stored)
        evidence_binding = {
            "encoding": "deterministic-gzip-canonical-json-v1",
            "path": (
                f"checkpoints/chunk_{chunk_index + 1:04d}_evidence.json.gz"
            ),
            "stored_sha256": hashlib.sha256(stored).hexdigest(),
            "stored_size_bytes": len(stored),
            "uncompressed_sha256": hashlib.sha256(uncompressed).hexdigest(),
            "uncompressed_size_bytes": len(uncompressed),
        }
        resource_revision = len(ledger_events)
        checkpoint_size = 0
        for _ in range(16):
            checkpoint_resources = dict(resources)
            checkpoint_resources.update(
                {
                    "charged_seconds": float(chunk_index + 1),
                    "optimizer_updates": chunk_index + 1,
                    "retained_decisions": completed_decisions,
                    "stored_bytes": cumulative_stored + len(stored) + checkpoint_size,
                    "uncompressed_bytes": (
                        cumulative_uncompressed + len(uncompressed) + checkpoint_size
                    ),
                }
            )
            checkpoint_body = {
                "access_journal_prefix": {
                    "sha256": hashlib.sha256(journal_prefix).hexdigest(),
                    "size_bytes": len(journal_prefix),
                },
                "checkpoint_index": chunk_index + 1,
                "chunk_evidence": evidence_binding,
                "chunk_index": chunk_index,
                "identity": identity,
                "previous_checkpoint_sha256": previous_checkpoint_sha256,
                "registration_sha256": registration_sha256,
                "resource_revision": resource_revision,
                "resource_use": checkpoint_resources,
                "resume_used": resume_mode is not None and (
                    resume_mode == "replay_uncheckpointed_chunk" or chunk_index >= 1
                ),
                "runtime_checkpoint": checkpoint_runtime_binding,
                "schema_version": verifier.CHECKPOINT_ENVELOPE_SCHEMA_VERSION,
            }
            checkpoint = {
                **checkpoint_body,
                "checkpoint_sha256": hashlib.sha256(
                    _fixture_canonical_json_bytes(checkpoint_body)
                ).hexdigest(),
            }
            checkpoint_bytes = _fixture_canonical_json_bytes(checkpoint)
            if len(checkpoint_bytes) == checkpoint_size:
                break
            checkpoint_size = len(checkpoint_bytes)
        else:
            raise AssertionError("synthetic checkpoint size did not converge")
        resources = checkpoint_resources
        append_resource(f"complete-chunk-checkpoint-{chunk_index + 1}")
        (checkpoint_dir / f"checkpoint_{chunk_index + 1:04d}.json").write_bytes(
            checkpoint_bytes
        )
        cumulative_stored = resources["stored_bytes"]
        cumulative_uncompressed = resources["uncompressed_bytes"]
        previous_checkpoint_sha256 = checkpoint["checkpoint_sha256"]
        checkpoint_sha256s.append(previous_checkpoint_sha256)
        adam_state = next_adam_state
        action_state = next_action_state
        if infrastructure_charge and chunk_index == 0:
            resources = dict(resources)
            resources["charged_seconds"] += 0.25
            append_resource("infrastructure-interruption-charge")

    if terminal_charge:
        resources = dict(resources)
        if fail_before_checkpoint:
            resources["charged_seconds"] += 0.5
        append_resource("terminal-attempt-charge")
    if trailing_infrastructure_charge:
        resources = dict(resources)
        resources["charged_seconds"] += 0.25
        append_resource("infrastructure-interruption-charge")

    journal_bytes = b"".join(
        _fixture_canonical_json_bytes(event) for event in journal_events
    )
    ledger_bytes = b"".join(
        _fixture_canonical_json_bytes(event) for event in ledger_events
    )
    (output / verifier.ACCESS_JOURNAL_FILENAME).write_bytes(journal_bytes)
    (output / verifier.RESOURCE_LEDGER_FILENAME).write_bytes(ledger_bytes)
    post_isolation = {
        **pre_isolation,
        "phase": "post",
    }
    _write_canonical(output / verifier.POST_ISOLATION_FILENAME, post_isolation)
    saturation = verifier._classify_family_saturation(completed_evidences)
    failure = None
    if failure_witness:
        failure_body = {
            "exception_type": "SyntheticTrainingFailure",
            "infrastructure": failure_infrastructure,
            "message": "synthetic typed failure",
            "phase": "training",
            "schema_version": verifier.FAILURE_WITNESS_SCHEMA_VERSION,
        }
        failure = {
            **failure_body,
            "failure_sha256": (
                "0" * 64
                if failure_digest_mismatch
                else hashlib.sha256(
                    _fixture_canonical_json_bytes(failure_body)
                ).hexdigest()
            ),
        }
        _write_canonical(output / verifier.FAILURE_FILENAME, failure)
    details = {"evaluation": None, "failure": failure, "saturation": saturation}
    prefix_inventory = _artifact_inventory_fixture(
        output,
        excluded={
            verifier.MANIFEST_FILENAME,
            verifier.TERMINAL_FILENAME,
            verifier.TERMINAL_INTENT_FILENAME,
        },
    )
    intent_body = {
        "artifact_prefix_inventory": prefix_inventory,
        "authority": dict(verifier._AUTHORITY),
        "checkpoint_sha256s": checkpoint_sha256s,
        "details": details,
        "identity": identity,
        "journal_prefix": {
            "sha256": hashlib.sha256(journal_bytes).hexdigest(),
            "size_bytes": len(journal_bytes),
        },
        "registration_sha256": registration_sha256,
        "resource_revision": len(ledger_events) - 1,
        "resource_use": resources,
        "schema_version": verifier.TERMINAL_INTENT_SCHEMA_VERSION,
        "verdict": verdict,
    }
    intent = {
        **intent_body,
        "terminal_intent_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(intent_body)
        ).hexdigest(),
    }
    _write_canonical(output / verifier.TERMINAL_INTENT_FILENAME, intent)
    terminal_body = {
        "authority": dict(verifier._AUTHORITY),
        "checkpoint_count": len(completed_evidences),
        "completed_chunk_indices": list(range(len(completed_evidences))),
        "details": details,
        "identity": identity,
        "registration_sha256": registration_sha256,
        "resource_use": resources,
        "resume_used": resume_mode is not None,
        "schema_version": verifier.TERMINAL_SCHEMA_VERSION,
        "terminal_intent_sha256": intent["terminal_intent_sha256"],
        "verdict": verdict,
    }
    terminal = {
        **terminal_body,
        "terminal_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(terminal_body)
        ).hexdigest(),
    }
    _write_canonical(output / verifier.TERMINAL_FILENAME, terminal)
    inventory = _artifact_inventory_fixture(
        output, excluded={verifier.MANIFEST_FILENAME}
    )
    manifest_body = {
        "artifact_inventory": inventory,
        "authority": dict(verifier._AUTHORITY),
        "identity": identity,
        "registration_sha256": registration_sha256,
        "schema_version": verifier.MANIFEST_SCHEMA_VERSION,
        "terminal_sha256": terminal["terminal_sha256"],
    }
    manifest = {
        **manifest_body,
        "manifest_sha256": hashlib.sha256(
            _fixture_canonical_json_bytes(manifest_body)
        ).hexdigest(),
    }
    _write_canonical(output / verifier.MANIFEST_FILENAME, manifest)
    return output


def test_historical_v1_source_inventory_replays_registered_git_blobs(tmp_path):
    repo, source_commit, _consumed_payload = _initialize_compact_source_repo(
        tmp_path
    )
    output = tmp_path / "historical-v1"
    registration = _registration_fixture(
        output, repo_root=repo, commit=source_commit
    )
    control_path = repo / _READINESS_SOURCE_PATHS[3][1]
    control_path.write_bytes(b"mutable worktree drift after registration\n")

    validated = verifier._validate_registration(
        copy.deepcopy(registration), output=output, repo_root=repo
    )

    assert validated["schema_version"] == verifier.REGISTRATION_SCHEMA_VERSION
    assert validated["repository_commit"] == source_commit


def test_real_r1_registration_validates_without_changing_evidence_bytes():
    registration_path = (
        ROOT
        / "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260806_r1/registration.json"
    )
    payload = registration_path.read_bytes()
    registration = verifier._parse_canonical_json(payload, label="real r1 registration")

    validated = verifier._validate_registration(
        registration,
        output=registration_path.parent.resolve(),
        repo_root=ROOT,
    )

    assert validated["schema_version"] == verifier.REGISTRATION_SCHEMA_VERSION
    assert registration_path.read_bytes() == payload


def test_compact_v2_registration_replays_immutable_readiness_evidence(tmp_path):
    fixture = _compact_registration_fixture(tmp_path)

    validated = verifier._validate_registration(
        copy.deepcopy(fixture["registration"]),
        output=fixture["output"],
        repo_root=fixture["repo"],
    )

    assert validated["schema_version"].endswith("registration-v2")
    assert "seed_inventory" not in validated
    assert validated["readiness_evidence"] == fixture["registration"][
        "readiness_evidence"
    ]
    assert not fixture["output"].exists()


def test_compact_v2_rejects_missing_verification_receipt_binding(tmp_path):
    fixture = _compact_registration_fixture(tmp_path)
    del fixture["registration"]["readiness_evidence"][
        "verification_receipt"
    ]

    with pytest.raises(verifier.VerifierError, match="verification receipt"):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def test_compact_v2_terminal_bundle_closes_without_copying_readiness(tmp_path):
    fixture = _compact_registration_fixture(tmp_path)
    output = _terminal_bundle_fixture(
        tmp_path, registration=fixture["registration"]
    )

    result = verifier.verify_terminal_bundle(output, repo_root=fixture["repo"])

    assert result["verdict"] == (
        "experiment_stopped_during_training_for_family_saturation"
    )
    assert not (output / "candidate_seed_inventory.json.gz").exists()
    assert not (output / "readiness_report.json").exists()
    assert not (output / "attempt_verified.json").exists()


def _mutate_report_authority(report):
    report["authority"]["training"] = True


def _mutate_report_authority_zero(report):
    report["authority"]["training"] = 0


def _mutate_report_eligibility_one(report):
    report["eligibility"] = {
        "empirical_successor_registration_proposal_eligible": 1
    }


def _mutate_report_decision(report):
    report["decision"] = {
        "failed_gates": ["artifact_binding"],
        "reason": "no_go_artifact_binding",
        "status": "no_go",
    }
    report["eligibility"] = {
        "empirical_successor_registration_proposal_eligible": False
    }
    report["gates"]["artifact_binding"] = "failed"


def _mutate_report_source_binding(report):
    rows = report["source_binding"]["bindings"]
    rows[3]["sha256"] = "0" * 64
    report["source_binding"]["bindings_sha256"] = hashlib.sha256(
        _fixture_canonical_json_bytes(rows)
    ).hexdigest()


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (_mutate_report_authority, "authority"),
        (_mutate_report_authority_zero, "authority"),
        (_mutate_report_eligibility_one, "registration eligible"),
        (_mutate_report_decision, "go"),
        (_mutate_report_source_binding, "source binding"),
    ],
)
def test_compact_v2_rejects_self_consistent_readiness_report_drift(
    tmp_path, mutator, message
):
    fixture = _compact_registration_fixture(tmp_path, report_mutator=mutator)

    with pytest.raises(verifier.VerifierError, match=message):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def _mutate_candidate_inventory(candidate):
    candidate["historical_seed_inventory"]["excluded_seed_count"] -= 1


def _mutate_candidate_schedule(candidate):
    candidate["candidate_schedule"]["seeds"][-1] += 1


def _mutate_candidate_collision(candidate):
    consumed = candidate["consumed_cohort"]
    consumed["seeds"][0] = 0
    consumed["seeds_sha256"] = hashlib.sha256(
        _fixture_canonical_json_bytes(consumed["seeds"])
    ).hexdigest()
    candidate["disjointness"] = {
        "collision_count": 1,
        "collisions": [0],
        "status": "failed",
    }


def _mutate_candidate_authority_zero(candidate):
    candidate["authority"]["training"] = 0


def _mutate_candidate_authority_one(candidate):
    candidate["authority"]["training"] = 1


def _mutate_candidate_consumed_count_float(candidate):
    candidate["consumed_cohort"]["seed_count"] = 512.0


def _mutate_candidate_disjointness_count_float(candidate):
    candidate["disjointness"]["collision_count"] = 0.0


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (_mutate_candidate_authority_zero, "authority"),
        (_mutate_candidate_authority_one, "authority"),
        (_mutate_candidate_consumed_count_float, "consumed cohort"),
        (_mutate_candidate_disjointness_count_float, "collision|disjointness"),
        (_mutate_candidate_inventory, "inventory"),
        (_mutate_candidate_schedule, "schedule"),
        (_mutate_candidate_collision, "collision"),
    ],
)
def test_compact_v2_rejects_self_consistent_candidate_semantic_drift(
    tmp_path, mutator, message
):
    fixture = _compact_registration_fixture(tmp_path, candidate_mutator=mutator)

    with pytest.raises(verifier.VerifierError, match=message):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def test_compact_v2_rejects_registration_schedule_drift(tmp_path):
    fixture = _compact_registration_fixture(tmp_path)
    fixture["registration"]["schedule"]["chunks"][0][0] = 999_999

    with pytest.raises(verifier.VerifierError, match="schedule"):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def test_compact_v2_rejects_self_consistent_nondeterministic_gzip(tmp_path):
    fixture = _compact_registration_fixture(tmp_path, compresslevel=1)

    with pytest.raises(verifier.VerifierError, match="deterministic gzip"):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def test_compact_v2_rejects_missing_publication_commit_report(tmp_path):
    fixture = _compact_registration_fixture(tmp_path)
    (fixture["repo"] / _READINESS_REPORT_PATH).unlink()
    missing_report_commit = _git_commit_fixture(
        fixture["repo"], "remove readiness report"
    )
    _git_fixture(
        fixture["repo"],
        "update-ref",
        "refs/remotes/origin/master",
        missing_report_commit,
    )
    fixture["registration"]["readiness_evidence"][
        "publication_commit"
    ] = missing_report_commit

    with pytest.raises(verifier.VerifierError, match="readiness report"):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def test_compact_v2_rejects_missing_publication_commit_receipt(tmp_path):
    fixture = _compact_registration_fixture(tmp_path)
    (fixture["repo"] / fixture["receipt_path"]).unlink()
    missing_receipt_commit = _git_commit_fixture(
        fixture["repo"], "remove verification receipt"
    )
    _git_fixture(
        fixture["repo"],
        "update-ref",
        "refs/remotes/origin/master",
        missing_receipt_commit,
    )
    fixture["registration"]["readiness_evidence"][
        "publication_commit"
    ] = missing_receipt_commit

    with pytest.raises(verifier.VerifierError, match="verification receipt"):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def _mutate_receipt_publication_binding(receipt):
    receipt["publication_bindings"][
        "candidate_seed_inventory.json.gz"
    ]["sha256"] = "0" * 64


def _mutate_receipt_verification_summary(receipt):
    receipt["verification"]["status"] = "unverified"


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (_mutate_receipt_publication_binding, "publication binding"),
        (_mutate_receipt_verification_summary, "verified go"),
    ],
)
def test_compact_v2_rejects_self_consistent_verification_receipt_drift(
    tmp_path, mutator, message
):
    fixture = _compact_registration_fixture(
        tmp_path, receipt_mutator=mutator
    )

    with pytest.raises(verifier.VerifierError, match=message):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def test_compact_v2_rejects_invalid_verification_receipt_self_digest(tmp_path):
    fixture = _compact_registration_fixture(tmp_path)
    receipt = fixture["receipt"]
    receipt["verification_receipt_sha256"] = "0" * 64
    receipt_payload = _write_canonical(
        fixture["repo"] / fixture["receipt_path"], receipt
    )
    invalid_receipt_commit = _git_commit_fixture(
        fixture["repo"], "invalidate verification receipt identity"
    )
    _git_fixture(
        fixture["repo"],
        "update-ref",
        "refs/remotes/origin/master",
        invalid_receipt_commit,
    )
    evidence = fixture["registration"]["readiness_evidence"]
    evidence["publication_commit"] = invalid_receipt_commit
    evidence["verification_receipt"] = {
        "path": fixture["receipt_path"],
        "sha256": hashlib.sha256(receipt_payload).hexdigest(),
        "size_bytes": len(receipt_payload),
        "verification_receipt_sha256": "0" * 64,
    }

    with pytest.raises(verifier.VerifierError, match="receipt digest"):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def test_compact_v2_rejects_publication_outside_pushed_head(tmp_path):
    fixture = _compact_registration_fixture(tmp_path)
    _git_fixture(
        fixture["repo"],
        "update-ref",
        "refs/remotes/origin/master",
        fixture["source_commit"],
    )

    with pytest.raises(verifier.VerifierError, match="publication ancestry"):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def test_compact_v2_rejects_old_readiness_with_changed_registered_source(
    tmp_path,
):
    fixture = _compact_registration_fixture(tmp_path)
    control_path = fixture["repo"] / _READINESS_SOURCE_PATHS[3][1]
    control_path.write_bytes(b"post-readiness control plane\n")
    changed_commit = _git_commit_fixture(
        fixture["repo"], "change registered control plane"
    )
    _git_fixture(
        fixture["repo"],
        "update-ref",
        "refs/remotes/origin/master",
        changed_commit,
    )
    fixture["registration"]["repository_commit"] = changed_commit
    fixture["registration"]["source_inventory"] = _source_inventory_fixture(
        repo_root=fixture["repo"],
        commit=changed_commit,
        registration_schema_version=verifier.REGISTRATION_V2_SCHEMA_VERSION,
    )

    with pytest.raises(
        verifier.VerifierError,
        match="verification receipt path|source commit",
    ):
        verifier._validate_registration(
            fixture["registration"],
            output=fixture["output"],
            repo_root=fixture["repo"],
        )


def test_compact_v2_rechecks_external_evidence_despite_persisted_preflight(
    tmp_path,
):
    fixture = _compact_registration_fixture(tmp_path)
    registration = fixture["registration"]
    registration["readiness_evidence"]["candidate_artifact"]["sha256"] = (
        "0" * 64
    )
    output = fixture["output"]
    output.mkdir()
    registration_sha256 = hashlib.sha256(
        _fixture_canonical_json_bytes(registration)
    ).hexdigest()
    preflight = {
        "checks": {
            "communication_mod_unchanged": True,
            "native_module_unchanged": True,
            "production_checkpoints_unchanged": True,
            "pushed_registration_exact": True,
            "pushed_source_exact": True,
            "runtime_identity_exact": True,
            "source_inventory_exact": True,
            "tracked_authorization_exact": True,
            "tracked_worktree_clean": True,
        },
        "pushed_head_commit": fixture["publication_commit"],
        "registration_sha256": registration_sha256,
        "repository_commit": registration["repository_commit"],
        "schema_version": verifier.SOURCE_PREFLIGHT_SCHEMA_VERSION,
    }
    _write_canonical(output / verifier.REGISTRATION_FILENAME, registration)
    _write_canonical(output / verifier.SOURCE_PREFLIGHT_FILENAME, preflight)
    _write_canonical(output / verifier.TERMINAL_FILENAME, {})
    _write_canonical(output / verifier.MANIFEST_FILENAME, {})

    with pytest.raises(
        verifier.VerifierError,
        match="readiness report candidate binding|candidate artifact binding",
    ):
        verifier.verify_terminal_bundle(output, repo_root=fixture["repo"])


def _write_execution_lease_fixture(output, *, process_id):
    identity = json.loads(
        (output / verifier.TERMINAL_FILENAME).read_bytes()
    )["identity"]
    _write_canonical(
        output / verifier.LEASE_FILENAME,
        {
            "identity": identity,
            "owner": {
                "acquired_at_ns": 1,
                "process_id": process_id,
                "token": "1" * 32,
            },
            "reclaimed_owner": None,
            "schema_version": verifier.LEASE_SCHEMA_VERSION,
        },
    )


def test_verify_terminal_bundle_replays_complete_saturated_prefix(tmp_path):
    output = _terminal_bundle_fixture(tmp_path)

    result = verifier.verify_terminal_bundle(output, repo_root=ROOT)

    assert result["checkpoint_count"] == 4
    assert result["completed_chunk_indices"] == [0, 1, 2, 3]
    assert result["resume_used"] is False
    assert result["verdict"] == (
        "experiment_stopped_during_training_for_family_saturation"
    )


@pytest.mark.parametrize(
    "resume_mode",
    ["replay_uncheckpointed_chunk", "continue_after_checkpoint"],
)
def test_verify_terminal_bundle_replays_both_journal_v2_resume_modes(
    tmp_path, resume_mode
):
    output = _terminal_bundle_fixture(tmp_path, resume_mode=resume_mode)

    result = verifier.verify_terminal_bundle(output, repo_root=ROOT)

    assert result["resume_used"] is True
    assert result["resume_mode"] == resume_mode


def test_verify_terminal_bundle_rejects_mismatched_v2_runtime_binding(tmp_path):
    output = _terminal_bundle_fixture(tmp_path, wrapper_runtime_mismatch=True)

    with pytest.raises(verifier.VerifierError, match="runtime bindings differ"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_evidence_only_as_incomplete(tmp_path):
    output = _terminal_bundle_fixture(tmp_path)
    (output / "checkpoints" / "checkpoint_0004.json").unlink()

    with pytest.raises(verifier.VerifierError, match="checkpoint inventory"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_completion_after_earliest_saturation(tmp_path):
    output = _terminal_bundle_fixture(
        tmp_path,
        verdict="experiment_completed_with_cross_fitted_mechanism_evidence",
    )

    with pytest.raises(verifier.VerifierError, match="completion verdict"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


@pytest.mark.parametrize(
    "mutation", ["extra", "missing", "oversized", "directory"]
)
def test_verify_terminal_bundle_rejects_nonexact_or_overlimit_closure(
    tmp_path, mutation
):
    output = _terminal_bundle_fixture(tmp_path)
    if mutation == "extra":
        (output / "extra.json").write_text("{}\n", encoding="ascii")
    elif mutation == "missing":
        (output / verifier.POST_ISOLATION_FILENAME).unlink()
    else:
        if mutation == "oversized":
            with (output / "oversized.bin").open("wb") as handle:
                handle.truncate(verifier.MAX_ARTIFACT_BYTES + 1)
        else:
            (output / "unexpected-empty-directory").mkdir()

    with pytest.raises(verifier.VerifierError):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_symlink_artifacts_when_supported(tmp_path):
    output = _terminal_bundle_fixture(tmp_path)
    target = output / verifier.POST_ISOLATION_FILENAME
    link = output / "post-isolation-link.json"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("local Windows policy does not permit symlink creation")

    with pytest.raises(verifier.VerifierError, match="symlink"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_excludes_the_bounded_execution_lease(
    tmp_path, monkeypatch
):
    output = _terminal_bundle_fixture(tmp_path)
    _write_execution_lease_fixture(output, process_id=999_999)
    monkeypatch.setattr(verifier, "_process_is_alive", lambda _pid: False)
    original_enumerate = verifier._enumerate_output_files

    def enumerate_while_lease_is_held(path):
        blocked = False
        handle = (output / verifier.LEASE_FILENAME).open("r+b", buffering=0)
        try:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                blocked = True
            else:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
        assert blocked is True
        return original_enumerate(path)

    monkeypatch.setattr(
        verifier, "_enumerate_output_files", enumerate_while_lease_is_held
    )

    result = verifier.verify_terminal_bundle(output, repo_root=ROOT)

    assert result["checkpoint_count"] == 4


def test_verify_terminal_bundle_rejects_live_lease_before_evidence_read(
    tmp_path, monkeypatch
):
    output = _terminal_bundle_fixture(tmp_path)
    _write_execution_lease_fixture(output, process_id=os.getpid())
    monkeypatch.setattr(verifier, "_process_is_alive", lambda _pid: True)

    def reject_evidence_read(*_args, **_kwargs):
        raise AssertionError("live lease must block evidence reads")

    monkeypatch.setattr(verifier, "_load_canonical_document", reject_evidence_read)
    with pytest.raises(verifier.VerifierError, match="owner is still alive"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_unreadable_lease_before_evidence_read(
    tmp_path, monkeypatch
):
    output = _terminal_bundle_fixture(tmp_path)
    (output / verifier.LEASE_FILENAME).write_bytes(b"not-canonical-json")

    def reject_evidence_read(*_args, **_kwargs):
        raise AssertionError("invalid lease must block evidence reads")

    monkeypatch.setattr(verifier, "_load_canonical_document", reject_evidence_read)
    with pytest.raises(verifier.VerifierError, match="execution lease"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rechecks_lease_before_evidence_read(
    tmp_path, monkeypatch
):
    output = _terminal_bundle_fixture(tmp_path)
    original_verify = verifier._verify_terminal_bundle_contents

    def verify_after_lease_appears(*args, **kwargs):
        _write_execution_lease_fixture(output, process_id=os.getpid())
        return original_verify(*args, **kwargs)

    monkeypatch.setattr(
        verifier, "_verify_terminal_bundle_contents", verify_after_lease_appears
    )
    with pytest.raises(verifier.VerifierError, match="execution lease"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_replaced_lease_handle(
    tmp_path, monkeypatch
):
    output = _terminal_bundle_fixture(tmp_path)
    _write_execution_lease_fixture(output, process_id=999_999)
    lease_path = output / verifier.LEASE_FILENAME
    replacement = tmp_path / ".replacement-lease"
    replacement.write_bytes(lease_path.read_bytes())
    original_open = os.open

    def open_replacement(path, flags, *args, **kwargs):
        if Path(path) == lease_path:
            return original_open(replacement, flags, *args, **kwargs)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(verifier.os, "open", open_replacement)
    monkeypatch.setattr(verifier, "_process_is_alive", lambda _pid: False)
    with pytest.raises(verifier.VerifierError, match="execution lease"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_rehashed_authority_escalation(tmp_path):
    output = _terminal_bundle_fixture(tmp_path)
    authorization_path = output / verifier.AUTHORIZATION_FILENAME
    authorization = json.loads(authorization_path.read_bytes())
    authorization["authority"]["evaluation"] = True
    body = {
        key: value
        for key, value in authorization.items()
        if key != "authorization_sha256"
    }
    authorization["authorization_sha256"] = hashlib.sha256(
        _fixture_canonical_json_bytes(body)
    ).hexdigest()
    _write_canonical(authorization_path, authorization)

    with pytest.raises(verifier.VerifierError, match="authorization binding"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


@pytest.mark.parametrize(
    ("mismatch", "message"),
    [
        ("model", "post model checkpoint"),
        ("adam", "post Adam checkpoint"),
        ("rng", "action RNG checkpoint"),
    ],
)
def test_verify_terminal_bundle_rejects_runtime_transition_drift(
    tmp_path, mismatch, message
):
    output = _terminal_bundle_fixture(
        tmp_path, runtime_transition_mismatch=mismatch
    )

    with pytest.raises(verifier.VerifierError, match=message):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_accepts_bound_typed_failure(tmp_path):
    output = _terminal_bundle_fixture(
        tmp_path,
        verdict="experiment_failed_after_seed_access",
        failure_witness=True,
    )

    result = verifier.verify_terminal_bundle(output, repo_root=ROOT)

    assert result["verdict"] == "experiment_failed_after_seed_access"


def test_verify_terminal_bundle_accepts_infrastructure_failure_after_resume(
    tmp_path,
):
    output = _terminal_bundle_fixture(
        tmp_path,
        resume_mode="continue_after_checkpoint",
        verdict="experiment_failed_after_seed_access",
        failure_witness=True,
        failure_infrastructure=True,
    )

    result = verifier.verify_terminal_bundle(output, repo_root=ROOT)

    assert result["verdict"] == "experiment_failed_after_seed_access"
    assert result["resume_used"] is True


def test_verify_terminal_bundle_rejects_infrastructure_failure_before_resume(
    tmp_path,
):
    output = _terminal_bundle_fixture(
        tmp_path,
        verdict="experiment_failed_after_seed_access",
        failure_witness=True,
        failure_infrastructure=True,
    )

    with pytest.raises(verifier.VerifierError, match="infrastructure failure"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_accepts_bounded_infrastructure_charge(tmp_path):
    output = _terminal_bundle_fixture(tmp_path, infrastructure_charge=True)

    result = verifier.verify_terminal_bundle(output, repo_root=ROOT)

    assert result["resource_use"]["charged_seconds"] == 4.0


@pytest.mark.parametrize(
    "access_resource_mode", ["batched_reconcile", "checkpoint"]
)
def test_verify_terminal_bundle_accepts_batched_journal_resource_reconciliation(
    tmp_path, access_resource_mode
):
    output = _terminal_bundle_fixture(
        tmp_path, access_resource_mode=access_resource_mode
    )

    result = verifier.verify_terminal_bundle(output, repo_root=ROOT)

    assert result["resource_use"]["environment_accesses"] == 256


def test_verify_terminal_bundle_reconciles_failure_before_first_checkpoint(tmp_path):
    output = _terminal_bundle_fixture(
        tmp_path,
        verdict="experiment_failed_after_seed_access",
        failure_witness=True,
        fail_before_checkpoint=True,
        terminal_charge=True,
    )

    result = verifier.verify_terminal_bundle(output, repo_root=ROOT)

    assert result["checkpoint_count"] == 0
    assert result["resource_use"]["environment_accesses"] == 1
    assert result["resource_use"]["charged_seconds"] == 0.5


def test_verify_terminal_bundle_rejects_missing_final_attempt_charge(tmp_path):
    output = _terminal_bundle_fixture(
        tmp_path,
        verdict="experiment_failed_after_seed_access",
        failure_witness=True,
        fail_before_checkpoint=True,
        terminal_charge=False,
    )

    with pytest.raises(verifier.VerifierError, match="terminal attempt charge"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_nonfinal_attempt_charge(tmp_path):
    output = _terminal_bundle_fixture(
        tmp_path,
        trailing_infrastructure_charge=True,
    )

    with pytest.raises(verifier.VerifierError, match="not the final revision"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_typed_failure_digest_drift(tmp_path):
    output = _terminal_bundle_fixture(
        tmp_path,
        verdict="experiment_failed_after_seed_access",
        failure_witness=True,
        failure_digest_mismatch=True,
    )

    with pytest.raises(verifier.VerifierError, match="failure witness digest"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_post_isolation_drift(tmp_path):
    output = _terminal_bundle_fixture(tmp_path)
    path = output / verifier.POST_ISOLATION_FILENAME
    observation = json.loads(path.read_bytes())
    observation["matches_registration"] = False
    _write_canonical(path, observation)

    with pytest.raises(verifier.VerifierError, match="post isolation binding"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_ascension_or_evaluation_drift(tmp_path):
    output = _terminal_bundle_fixture(tmp_path)
    path = output / verifier.REGISTRATION_FILENAME
    registration = json.loads(path.read_bytes())
    registration["contract"]["environment"]["ascension"] = 1
    registration["contract"]["evaluation"]["authorized"] = True
    _write_canonical(path, registration)

    with pytest.raises(verifier.VerifierError, match="registration contract"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_manifest_body_digest_drift(tmp_path):
    output = _terminal_bundle_fixture(tmp_path)
    path = output / verifier.MANIFEST_FILENAME
    manifest = json.loads(path.read_bytes())
    manifest["manifest_sha256"] = "0" * 64
    _write_canonical(path, manifest)

    with pytest.raises(verifier.VerifierError, match="manifest body digest"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


def test_verify_terminal_bundle_rejects_resource_hash_chain_drift(tmp_path):
    output = _terminal_bundle_fixture(tmp_path)
    path = output / verifier.RESOURCE_LEDGER_FILENAME
    events = [json.loads(line) for line in path.read_bytes().splitlines()]
    events[2]["previous_event_sha256"] = "0" * 64
    path.write_bytes(
        b"".join(_fixture_canonical_json_bytes(event) for event in events)
    )

    with pytest.raises(verifier.VerifierError, match="hash-chain"):
        verifier.verify_terminal_bundle(output, repo_root=ROOT)


@pytest.mark.parametrize(
    "journal_patch",
    [
        {"terminal_access_failure": True},
        {"resume_used": True, "resume_complete": False},
    ],
)
def test_terminal_completion_rejects_unclosed_access_or_resume_state(
    tmp_path, monkeypatch, journal_patch
):
    saturation = {
        "category": None,
        "family": None,
        "multi_family_decisions": 0,
        "stop": False,
        "window_chunk_indices": [],
    }
    monkeypatch.setattr(
        verifier,
        "_classify_family_saturation",
        lambda _evidence: dict(saturation),
    )
    journal = {
        "completed_chunk_indices": list(range(verifier.CHUNK_COUNT)),
        "debited_accesses": verifier.SCHEDULED_TRAJECTORIES,
        "pending_access": None,
        "primary_next_position": verifier.SCHEDULED_TRAJECTORIES,
        "resume_candidate_chunk_index": None,
        "resume_complete": True,
        "resume_failed": False,
        "resume_used": False,
        "terminal_access_failure": False,
    }
    journal.update(journal_patch)
    chain = [
        {"chunk": {"evidence": {"chunk_index": index}}}
        for index in range(verifier.CHUNK_COUNT)
    ]
    details = {
        "evaluation": None,
        "failure": None,
        "saturation": saturation,
    }

    with pytest.raises(verifier.VerifierError, match="completion verdict"):
        verifier._verify_terminal_state(
            verdict="experiment_completed_with_cross_fitted_mechanism_evidence",
            details=details,
            chain=chain,
            journal=journal,
            ledger={"resources": verifier._zero_resources()},
            output=tmp_path,
            files=set(),
        )


def test_terminal_saturation_rejects_access_after_the_last_checkpoint(
    tmp_path, monkeypatch
):
    def classify(evidence):
        stop = len(evidence) >= 4
        return {
            "category": "card_reward" if stop else None,
            "family": "take" if stop else None,
            "multi_family_decisions": 64 if stop else 0,
            "stop": stop,
            "window_chunk_indices": [
                row["chunk_index"] for row in evidence[-4:]
            ],
        }

    monkeypatch.setattr(verifier, "_classify_family_saturation", classify)
    chain = [
        {"chunk": {"evidence": {"chunk_index": index}}}
        for index in range(4)
    ]
    saturation = classify([row["chunk"]["evidence"] for row in chain])
    journal = {
        "completed_chunk_indices": list(range(4)),
        "debited_accesses": 257,
        "pending_access": None,
        "primary_next_position": 257,
        "resume_candidate_chunk_index": 4,
        "resume_complete": False,
        "resume_failed": False,
        "resume_used": False,
        "terminal_access_failure": False,
    }

    with pytest.raises(verifier.VerifierError, match="checkpoint boundary"):
        verifier._verify_terminal_state(
            verdict="experiment_stopped_during_training_for_family_saturation",
            details={
                "evaluation": None,
                "failure": None,
                "saturation": saturation,
            },
            chain=chain,
            journal=journal,
            ledger={"resources": verifier._zero_resources()},
            output=tmp_path,
            files=set(),
        )
