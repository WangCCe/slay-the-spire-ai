from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest
import torch

import analysis_scripts.noncombat_simulator_rl_experiment as experiment_module
import scripts.run_noncombat_simulator_rl_experiment as experiment_runner
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    TARGET_CATEGORIES,
    build_transition,
)
from analysis_scripts.noncombat_simulator_rl_experiment import (
    ALGORITHM_VERSION,
    AUTHORIZATION_SCHEMA_VERSION,
    BOOTSTRAP_RESAMPLES,
    CANARY_SEEDS,
    CHECKPOINT_INTERVAL_EPISODES,
    CHECKPOINT_SCHEMA_VERSION,
    DISCOUNT,
    EXPERIMENT_SCHEMA_VERSION,
    FEATURE_VERSION,
    HASH_DIM,
    HOLDOUT_SEEDS,
    LEARNING_RATE,
    MAX_WALL_SECONDS,
    MODEL_SEED,
    REGISTERED_SUPPORT_BLOCKERS,
    REWARD_VERSION,
    TRAINING_EPISODES,
    TRAIN_PASSES,
    TRAIN_SEEDS,
    ExperimentBlocked,
    ExecutionLease,
    append_journal_record,
    build_checkpoint_envelope,
    build_checkpoint_state_payload,
    build_paired_evaluation,
    build_execution_authorization,
    canonical_json_bytes,
    candidate_feature_matrix_v2,
    decode_tensor,
    encode_tensor,
    classify_canary_evaluation,
    classify_holdout_evaluation,
    evaluate_frozen_policy,
    experiment_contract,
    load_canonical_json_bytes,
    project_policy_view_v2,
    paired_bootstrap_interval,
    paired_policy_evaluation,
    persist_completed_training_chunk,
    initialize_training_runtime,
    initialize_experiment_output,
    registered_chunk_coordinates,
    registration_authority,
    recover_pending_training_chunk,
    resume_training_runtime_from_output,
    restore_training_runtime,
    run_registered_training_chunk,
    run_conditional_evaluation,
    simulator_experiment_reward,
    validate_execution_authorization,
    validate_checkpoint_chain,
    validate_journal,
    validate_prefix_replay_result,
    validate_registration,
    verify_checkpoint_prefix_replay,
    publish_checkpoint,
    publish_prefix_replay_result,
    publish_training_chunk_summary,
    publish_terminal_artifacts,
    validate_terminal_artifact_directory,
)


def _binding(path: str, token: str) -> dict[str, object]:
    return {"path": path, "sha256": token * 64, "size_bytes": 123}


def _provenance() -> dict[str, object]:
    return {
        "adapter_commit": "1" * 40,
        "adapter_source_sha256": "2" * 64,
        "build": {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_policy_id": "sts_lightspeed_simple_agent_no_potions_v1",
            "compiler": "test-compiler",
            "cpp_standard": 201703,
            "native_target_policy_id": NATIVE_TARGET_POLICY_ID,
            "pybind11_version": "3.0.2",
            "python": "3.10.18",
        },
        "module_sha256": "3" * 64,
        "module_size_bytes": 123,
        "simulator_commit": "4" * 40,
        "simulator_dirty": False,
        "simulator_source_file_count": 79,
        "simulator_source_sha256": "5" * 64,
        "submodules": {"json": "6" * 40, "pybind11": "7" * 40},
    }


def _registration() -> dict[str, object]:
    return {
        "authority": registration_authority(),
        "experiment": experiment_contract(),
        "identity": {
            "adapter_provenance": _provenance(),
            "evidence": {
                "formal_readiness_manifest": _binding(
                    "reports/noncombat_formal_rl_readiness_audit_20260802_r2/artifact_manifest.json",
                    "8",
                ),
                "formal_reward_manifest": _binding(
                    "reports/noncombat_formal_reward_contract_20260802/artifact_manifest.json",
                    "9",
                ),
                "simulator_smoke_manifest": _binding(
                    "reports/noncombat_simulator_training_smoke_20260802/artifact_manifest.json",
                    "a",
                ),
                "simulator_smoke_registration": _binding(
                    "reports/noncombat_simulator_training_smoke_20260802_input.json",
                    "b",
                ),
            },
            "implementation": {
                "commit": "c" * 40,
                "source_files": [
                    "analysis_scripts/noncombat_formal_reward_contract.py",
                    "analysis_scripts/noncombat_policy_model.py",
                    "analysis_scripts/noncombat_simulator_adapter.py",
                    "analysis_scripts/noncombat_simulator_rl_experiment.py",
                    "analysis_scripts/verify_noncombat_simulator_rl_experiment.py",
                    "scripts/run_noncombat_simulator_rl_experiment.py",
                ],
                "source_sha256": "d" * 64,
            },
            "runtime": {
                "executable": "D:/anaconda/envs/stsai/python.exe",
                "platform": "win32",
                "python_version": "3.10.18",
                "torch_version": "2.5.1+cu121",
            },
            "seed_inventory": _binding(
                "reports/noncombat_simulator_rl_experiment_seed_inventory.json",
                "e",
            ),
        },
        "schema_version": EXPERIMENT_SCHEMA_VERSION,
    }


def _snapshot(category: str = "shop") -> dict[str, object]:
    return {
        "adapter_api_version": ADAPTER_API_VERSION,
        "baseline_control": {
            "history": [{"category": "combat", "outcome": "ignored"}],
            "policy_id": "test-baseline-v1",
        },
        "category": category,
        "decision_count": 7,
        "schema_version": STATE_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "state": {
            "cur_hp": 55,
            "deck": [{"id": "Strike_R", "upgrades": 0}],
            "floor": 8,
            "gold": 123,
            "nested": {"outcome": "undecided", "seed": "hidden"},
            "outcome": "undecided",
            "seed": "1234",
        },
        "terminal": False,
    }


def _candidate(action_id: str, category: str = "shop", price: int = 50):
    return {
        "action_id": action_id,
        "available": True,
        "category": category,
        "kind": "choose",
        "label": action_id,
        "raw": {"price": price, "provenance": {"source": "hidden"}},
    }


def test_contract_freezes_exact_cohorts_algorithm_reward_and_limits():
    contract = experiment_contract()

    assert TRAIN_SEEDS == tuple(range(50000, 51024))
    assert CANARY_SEEDS == tuple(range(51024, 51152))
    assert HOLDOUT_SEEDS == tuple(range(51152, 51664))
    assert TRAINING_EPISODES == 4096
    assert TRAIN_PASSES == 4
    assert CHECKPOINT_INTERVAL_EPISODES == 64
    assert MAX_WALL_SECONDS == 28_800.0
    assert contract["algorithm"] == {
        "discount": DISCOUNT,
        "feature_version": FEATURE_VERSION,
        "hash_dim": HASH_DIM,
        "learning_rate": LEARNING_RATE,
        "model_seed": MODEL_SEED,
        "optimizer": "adam",
        "passes": TRAIN_PASSES,
        "standardize_returns": True,
        "version": ALGORITHM_VERSION,
    }
    assert contract["reward"]["version"] == REWARD_VERSION
    assert contract["reward"]["victory_weight"] == 2.0
    assert contract["evaluation"]["bootstrap_resamples"] == BOOTSTRAP_RESAMPLES
    assert contract["support"]["registered_blockers"] == list(
        REGISTERED_SUPPORT_BLOCKERS
    )


def test_registration_is_closed_and_keeps_every_authority_false():
    registration = validate_registration(_registration())

    assert registration["authority"] == registration_authority()
    assert registration["authority"]
    assert not any(registration["authority"].values())

    extra = _registration()
    extra["unexpected"] = True
    with pytest.raises(ExperimentBlocked, match="registration fields"):
        validate_registration(extra)

    permissive = _registration()
    permissive["authority"]["formal_noncombat_rl"] = True
    with pytest.raises(ExperimentBlocked, match="authority"):
        validate_registration(permissive)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["experiment"]["cohorts"]["train_seeds"].append(
                51024
            ),
            "train_seeds",
        ),
        (
            lambda value: value["experiment"]["algorithm"].__setitem__(
                "passes", 5
            ),
            "passes",
        ),
        (
            lambda value: value["experiment"]["reward"].__setitem__(
                "victory_weight", 1.0
            ),
            "victory_weight",
        ),
        (
            lambda value: value["experiment"]["limits"].__setitem__(
                "max_wall_seconds", 28_801.0
            ),
            "max_wall_seconds",
        ),
        (
            lambda value: value["experiment"]["execution"].__setitem__(
                "allow_parameter_retry", True
            ),
            "allow_parameter_retry",
        ),
        (
            lambda value: value["experiment"]["outputs"].__setitem__(
                "checkpoint_complete_count", 63
            ),
            "checkpoint_complete_count",
        ),
        (
            lambda value: value["experiment"]["runtime"].__setitem__(
                "cuda_allowed", True
            ),
            "cuda_allowed",
        ),
    ],
)
def test_registration_rejects_any_experiment_contract_drift(mutate, message):
    registration = _registration()
    mutate(registration)

    with pytest.raises(ExperimentBlocked, match=message):
        validate_registration(registration)


def test_registration_binds_exact_v3_provenance_evidence_runtime_and_sources():
    registration = validate_registration(_registration())
    identity = registration["identity"]

    assert identity["adapter_provenance"]["build"]["adapter_api_version"] == (
        ADAPTER_API_VERSION
    )
    assert tuple(identity["evidence"]) == (
        "formal_readiness_manifest",
        "formal_reward_manifest",
        "simulator_smoke_manifest",
        "simulator_smoke_registration",
    )
    assert identity["runtime"]["platform"] == "win32"

    wrong_adapter = _registration()
    wrong_adapter["identity"]["adapter_provenance"]["build"][
        "adapter_api_version"
    ] = "sts-lightspeed-noncombat-adapter-v2"
    with pytest.raises(ExperimentBlocked, match="API v3"):
        validate_registration(wrong_adapter)

    missing_evidence = _registration()
    del missing_evidence["identity"]["evidence"]["formal_reward_manifest"]
    with pytest.raises(ExperimentBlocked, match="evidence fields"):
        validate_registration(missing_evidence)

    extra_provenance = _registration()
    extra_provenance["identity"]["adapter_provenance"]["unexpected"] = True
    with pytest.raises(ExperimentBlocked, match="adapter provenance fields"):
        validate_registration(extra_provenance)


def test_canonical_json_loader_rejects_duplicate_and_noncanonical_bytes():
    registration = _registration()
    canonical = canonical_json_bytes(registration)

    assert load_canonical_json_bytes(canonical, "registration") == registration

    with pytest.raises(ExperimentBlocked, match="canonical"):
        load_canonical_json_bytes(
            json.dumps(registration, sort_keys=True).encode("utf-8"), "registration"
        )
    with pytest.raises(ExperimentBlocked, match="duplicate"):
        load_canonical_json_bytes(b'{"schema_version":1,"schema_version":2}\n', "x")


def test_execution_authorization_is_separate_and_only_enables_experiment():
    registration = validate_registration(_registration())
    registration_bytes = canonical_json_bytes(registration)
    authorization = build_execution_authorization(
        registration_binding={
            "commit": "f" * 40,
            "path": "reports/noncombat_simulator_rl_experiment_registration.json",
            "sha256": hashlib.sha256(registration_bytes).hexdigest(),
            "size_bytes": len(registration_bytes),
        },
        logical_execution_id="noncombat-sim-rl-r1",
        output_directory="reports/noncombat_simulator_rl_experiment_r1",
    )

    validated = validate_execution_authorization(
        authorization,
        registration=registration,
        registration_bytes=registration_bytes,
    )

    assert validated["schema_version"] == AUTHORIZATION_SCHEMA_VERSION
    assert validated["authority"]["experiment_execution"] is True
    assert all(
        value is False
        for name, value in validated["authority"].items()
        if name != "experiment_execution"
    )

    permissive = copy.deepcopy(authorization)
    permissive["authority"]["live_policy_loading"] = True
    with pytest.raises(ExperimentBlocked, match="authority"):
        validate_execution_authorization(
            permissive,
            registration=registration,
            registration_bytes=registration_bytes,
        )


def test_source_only_contract_validation_does_not_load_native_or_live_modules():
    watched = {
        "sts_lightspeed_noncombat_adapter",
        "spirecomm.communication.coordinator",
        "spirecomm.communication.action",
    }
    before = watched & set(sys.modules)

    validate_registration(_registration())

    assert watched & set(sys.modules) == before


@pytest.mark.parametrize("category", TARGET_CATEGORIES)
def test_v2_projection_supports_every_category_and_excludes_leakage(category):
    snapshot = _snapshot(category)
    candidate = _candidate(f"{category}:choice:0", category)
    before_snapshot = copy.deepcopy(snapshot)
    before_candidate = copy.deepcopy(candidate)

    projected = project_policy_view_v2(snapshot, candidate)
    encoded = canonical_json_bytes(projected)

    assert projected["state"]["category"] == category
    assert projected["candidate"]["action_id"] == candidate["action_id"]
    for token in (
        b'"seed"',
        b'"outcome"',
        b'"provenance"',
        b'"baseline_control"',
        b'"terminal"',
    ):
        assert token not in encoded
    assert snapshot == before_snapshot
    assert candidate == before_candidate


def test_v2_features_are_deterministic_and_follow_candidate_reordering():
    snapshot = _snapshot()
    candidates = [_candidate("buy:a", price=10), _candidate("buy:b", price=20)]

    first = candidate_feature_matrix_v2(snapshot, candidates)
    second = candidate_feature_matrix_v2(snapshot, list(reversed(candidates)))

    assert first.shape == (2, HASH_DIM)
    assert first.dtype == torch.float32
    assert torch.isfinite(first).all().item()
    assert torch.equal(first[0], second[1])
    assert torch.equal(first[1], second[0])

    leaked = copy.deepcopy(snapshot)
    leaked["state"]["seed"] = "different"
    leaked["state"]["outcome"] = "player_victory"
    assert torch.equal(first, candidate_feature_matrix_v2(leaked, candidates))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda snapshot, candidates: candidates.clear(), "nonempty"),
        (
            lambda snapshot, candidates: candidates.append(copy.deepcopy(candidates[0])),
            "duplicate",
        ),
        (
            lambda snapshot, candidates: snapshot.__setitem__("category", "combat"),
            "category",
        ),
        (
            lambda snapshot, candidates: snapshot["state"].__setitem__(
                "gold", math.inf
            ),
            "finite",
        ),
        (
            lambda snapshot, candidates: candidates[0]["raw"].__setitem__(
                "price", math.nan
            ),
            "finite",
        ),
    ],
)
def test_v2_features_fail_closed_on_invalid_policy_input(mutate, message):
    snapshot = _snapshot()
    candidates = [_candidate("buy:a")]
    mutate(snapshot, candidates)

    with pytest.raises(ExperimentBlocked, match=message):
        candidate_feature_matrix_v2(snapshot, candidates)


def test_v2_hashed_features_accumulate_repeated_values_without_overwrite():
    snapshot = _snapshot()
    one = _candidate("buy:a")
    repeated = copy.deepcopy(one)
    repeated["raw"]["nested"] = {"price": 50}

    base = candidate_feature_matrix_v2(snapshot, [one])[0]
    accumulated = candidate_feature_matrix_v2(snapshot, [repeated])[0]

    assert not torch.equal(base, accumulated)
    assert torch.count_nonzero(accumulated).item() >= torch.count_nonzero(base).item()


def _transition(
    source_floor: object,
    successor_floor: object,
    *,
    terminal: object = False,
    outcome: object = "undecided",
) -> dict[str, object]:
    return {
        "source_state": {"floor": source_floor},
        "successor": {
            "state": {"floor": successor_floor, "outcome": outcome},
            "terminal": terminal,
        },
    }


def test_experiment_reward_is_strictly_victory_primary():
    assert simulator_experiment_reward(_transition(0, 57)) == 1.0
    assert simulator_experiment_reward(
        _transition(0, 0, terminal=True, outcome="player_victory")
    ) == 2.0
    assert simulator_experiment_reward(
        _transition(0, 57, terminal=True, outcome="player_victory")
    ) == 3.0
    assert simulator_experiment_reward(_transition(10, 8)) == 0.0
    assert 2.0 > simulator_experiment_reward(_transition(0, 57))


def test_experiment_reward_ignores_every_excluded_signal():
    transition = _transition(10, 12, terminal=True, outcome="player_victory")
    expected = simulator_experiment_reward(transition)

    transition.update(
        {
            "bottled_label": "buy:a",
            "current_label": "skip",
            "live_outcome": "victory",
            "ope_value": 999,
            "simple_agent_score": -999,
        }
    )
    transition["source_state"].update({"cur_hp": 1, "gold": 0})
    transition["successor"]["state"].update({"cur_hp": 999, "gold": 9999})

    assert simulator_experiment_reward(transition) == expected


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "8"])
def test_experiment_reward_rejects_invalid_floor_values(value):
    with pytest.raises(ExperimentBlocked, match="invalid_transition"):
        simulator_experiment_reward(_transition(value, 9))


class FakeTrainingEnvironment:
    def __init__(
        self,
        seed: int,
        *,
        blocker: str | None = None,
        duplicate: bool = False,
        mutate_source: bool = False,
        nonfinite: bool = False,
    ) -> None:
        self.seed = seed
        self.blocker = blocker
        self.duplicate = duplicate
        self.mutate_source = mutate_source
        self.nonfinite = nonfinite
        self.selected: str | None = None
        self.terminal = False

    @property
    def category(self) -> str:
        return TARGET_CATEGORIES[self.seed % len(TARGET_CATEGORIES)]

    def snapshot(self) -> dict[str, object]:
        floor = 0
        outcome = "undecided"
        if self.terminal:
            floor = 57 if self.selected == "good" else 3
            outcome = "player_victory" if self.selected == "good" else "player_loss"
        return {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_control": {
                "history": [],
                "policy_id": "test-baseline-v1",
            },
            "category": None if self.terminal else self.category,
            "decision_count": 1 if self.terminal else 0,
            "schema_version": STATE_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "state": {
                "cur_hp": 80,
                "floor": floor,
                "gold": math.inf if self.nonfinite else 99,
                "outcome": outcome,
                "seed": str(self.seed),
            },
            "terminal": self.terminal,
        }

    def legal_actions(self) -> list[dict[str, object]]:
        if self.terminal:
            return []
        first = _candidate("bad", self.category, price=0)
        second = _candidate("good", self.category, price=1)
        if self.duplicate:
            second["action_id"] = first["action_id"]
        return [first, second]

    def clone(self):
        if self.mutate_source:
            return self
        return copy.deepcopy(self)

    def step(self, action_id: str) -> dict[str, object]:
        before = self.snapshot()
        candidates = self.legal_actions()
        if self.blocker is not None:
            raise RuntimeError(self.blocker)
        self.selected = action_id
        self.terminal = True
        return build_transition(
            before=before,
            candidates=candidates,
            selected_action_id=action_id,
            after=self.snapshot(),
            provenance=_provenance(),
        )


def _training_factory(seed: int) -> FakeTrainingEnvironment:
    return FakeTrainingEnvironment(seed)


def _model_payload(runtime) -> dict[str, list[float]]:
    return {
        name: tensor.detach().cpu().reshape(-1).tolist()
        for name, tensor in sorted(runtime.model.state_dict().items())
    }


def test_registered_chunk_coordinates_cover_the_exact_training_cohort():
    coordinates = [registered_chunk_coordinates(index) for index in range(64)]

    assert coordinates[0] == {
        "chunk_index": 0,
        "episode_end": 64,
        "episode_start": 0,
        "pass_index": 0,
        "seeds": tuple(range(50000, 50064)),
    }
    assert coordinates[-1]["chunk_index"] == 63
    assert coordinates[-1]["pass_index"] == 3
    assert coordinates[-1]["seeds"] == tuple(range(50960, 51024))
    assert coordinates[-1]["episode_end"] == TRAINING_EPISODES
    assert [seed for row in coordinates[:16] for seed in row["seeds"]] == list(
        TRAIN_SEEDS
    )
    with pytest.raises(ExperimentBlocked, match="chunk_index"):
        registered_chunk_coordinates(64)


def test_training_runtime_is_cpu_only_and_one_chunk_is_reproducible():
    first = initialize_training_runtime()
    second = initialize_training_runtime()

    first_summary = run_registered_training_chunk(
        first, environment_factory=_training_factory
    )
    second_summary = run_registered_training_chunk(
        second, environment_factory=_training_factory
    )

    assert canonical_json_bytes(first_summary) == canonical_json_bytes(second_summary)
    assert _model_payload(first) == _model_payload(second)
    assert first.next_chunk_index == second.next_chunk_index == 1
    assert first.completed_episodes == second.completed_episodes == 64
    assert first.optimizer_updates == second.optimizer_updates == 1
    assert next(first.model.parameters()).device.type == "cpu"
    assert first_summary["candidate_legality"] is True
    assert first_summary["episodes"] == 64
    assert first_summary["categories"] == list(TARGET_CATEGORIES)
    assert all(row["retained"] for row in first_summary["episode_rows"])


def test_training_chunk_requires_the_unique_next_coordinate_and_full_chunk():
    runtime = initialize_training_runtime()

    with pytest.raises(ExperimentBlocked, match="next chunk"):
        run_registered_training_chunk(
            runtime, environment_factory=_training_factory, chunk_index=1
        )
    with pytest.raises(ExperimentBlocked, match="64"):
        run_registered_training_chunk(
            runtime,
            environment_factory=_training_factory,
            seed_override=TRAIN_SEEDS[:63],
        )


def test_registered_support_blockers_are_retained_as_nonvictories():
    reason = REGISTERED_SUPPORT_BLOCKERS[0]
    runtime = initialize_training_runtime()
    summary = run_registered_training_chunk(
        runtime,
        environment_factory=lambda seed: FakeTrainingEnvironment(
            seed, blocker=reason
        ),
    )

    assert summary["unsupported_episodes"] == 64
    assert summary["victories"] == 0
    assert all(row["unsupported_reason"] == reason for row in summary["episode_rows"])
    assert all(row["outcome"] is None for row in summary["episode_rows"])
    assert all(row["last_supported_floor"] == 0.0 for row in summary["episode_rows"])
    assert runtime.completed_episodes == 64
    assert runtime.optimizer_updates == 1


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda seed: FakeTrainingEnvironment(seed, blocker="unknown_blocker"),
            "unregistered blocker",
        ),
        (lambda seed: FakeTrainingEnvironment(seed, duplicate=True), "duplicate"),
        (
            lambda seed: FakeTrainingEnvironment(seed, mutate_source=True),
            "mutated the source",
        ),
        (lambda seed: FakeTrainingEnvironment(seed, nonfinite=True), "finite"),
    ],
)
def test_training_chunk_fails_closed_before_an_optimizer_update(factory, message):
    runtime = initialize_training_runtime()
    before = _model_payload(runtime)

    with pytest.raises(ExperimentBlocked, match=message):
        run_registered_training_chunk(runtime, environment_factory=factory)

    assert _model_payload(runtime) == before
    assert runtime.next_chunk_index == 0
    assert runtime.completed_episodes == 0
    assert runtime.optimizer_updates == 0


def test_training_chunk_rejects_nonfinite_model_and_optimizer_contract_drift():
    runtime = initialize_training_runtime()
    with torch.no_grad():
        next(runtime.model.parameters()).view(-1)[0] = math.nan
    with pytest.raises(ExperimentBlocked, match="model tensor"):
        run_registered_training_chunk(runtime, environment_factory=_training_factory)

    runtime = initialize_training_runtime()
    runtime.optimizer.param_groups[0]["lr"] = 0.1
    with pytest.raises(ExperimentBlocked, match="learning rate"):
        run_registered_training_chunk(runtime, environment_factory=_training_factory)


REGISTRATION_SHA256 = "8" * 64
IMPLEMENTATION_COMMIT = "9" * 40
LOGICAL_EXECUTION_ID = "noncombat-sim-rl-test"


@pytest.mark.parametrize(
    "tensor",
    [
        torch.tensor(3.5, dtype=torch.float32),
        torch.tensor([[1.0, -2.0]], dtype=torch.float64),
        torch.tensor([1, 2, 3], dtype=torch.int64),
        torch.tensor([0, 255], dtype=torch.uint8),
        torch.tensor([True, False], dtype=torch.bool),
    ],
)
def test_tensor_codec_is_explicit_canonical_and_round_trips(tensor):
    encoded = encode_tensor(tensor)
    decoded = decode_tensor(encoded, "tensor")

    assert encoded["byte_order"] == "little"
    assert encoded["shape"] == list(tensor.shape)
    assert len(encoded["data_sha256"]) == 64
    assert decoded.dtype == tensor.dtype
    assert torch.equal(decoded, tensor)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.__setitem__("byte_order", "big"), "little"),
        (lambda value: value.__setitem__("data_base64", "***"), "base64"),
        (lambda value: value["shape"].append(2), "byte length"),
        (lambda value: value.__setitem__("data_sha256", "0" * 64), "sha256"),
    ],
)
def test_tensor_codec_rejects_noncanonical_or_tampered_payloads(mutate, message):
    encoded = encode_tensor(torch.tensor([1.0], dtype=torch.float32))
    mutate(encoded)

    with pytest.raises(ExperimentBlocked, match=message):
        decode_tensor(encoded, "tensor")


def test_checkpoint_state_payload_excludes_measured_runtime_but_envelope_records_it():
    first = initialize_training_runtime()
    second = initialize_training_runtime()
    second.cumulative_wall_seconds = 12.5

    first_state = build_checkpoint_state_payload(
        first,
        registration_sha256=REGISTRATION_SHA256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
    )
    second_state = build_checkpoint_state_payload(
        second,
        registration_sha256=REGISTRATION_SHA256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
    )

    assert canonical_json_bytes(first_state) == canonical_json_bytes(second_state)
    first_envelope = build_checkpoint_envelope(
        first,
        registration_sha256=REGISTRATION_SHA256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
        previous_checkpoint_bytes=None,
    )
    second_envelope = build_checkpoint_envelope(
        second,
        registration_sha256=REGISTRATION_SHA256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
        previous_checkpoint_bytes=None,
    )
    assert first_envelope["state_payload"] == second_envelope["state_payload"]
    assert first_envelope["cumulative_wall_seconds"] == 0.0
    assert second_envelope["cumulative_wall_seconds"] == 12.5


def _publish_two_chunk_chain(output_dir: Path):
    runtime = initialize_training_runtime()
    append_journal_record(
        output_dir,
        phase="started",
        logical_execution_id=LOGICAL_EXECUTION_ID,
        details={"registration_sha256": REGISTRATION_SHA256},
    )
    checkpoint_bytes = None
    envelopes = []
    for _ in range(2):
        runtime_summary = run_registered_training_chunk(
            runtime, environment_factory=_training_factory
        )
        envelope = build_checkpoint_envelope(
            runtime,
            registration_sha256=REGISTRATION_SHA256,
            implementation_commit=IMPLEMENTATION_COMMIT,
            logical_execution_id=LOGICAL_EXECUTION_ID,
            previous_checkpoint_bytes=checkpoint_bytes,
        )
        path = publish_checkpoint(output_dir, envelope)
        checkpoint_bytes = path.read_bytes()
        training_path = publish_training_chunk_summary(
            output_dir, runtime_summary, checkpoint_bytes=checkpoint_bytes
        )
        append_journal_record(
            output_dir,
            phase="continued",
            logical_execution_id=LOGICAL_EXECUTION_ID,
            details={
                "checkpoint_index": envelope["checkpoint_index"],
                "checkpoint_sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
                "training_summary_sha256": hashlib.sha256(
                    training_path.read_bytes()
                ).hexdigest(),
            },
        )
        envelopes.append(envelope)
    return runtime, envelopes


def test_checkpoint_chain_journal_resume_and_prefix_replay_are_exact(tmp_path):
    output_dir = tmp_path / "experiment"
    primary, envelopes = _publish_two_chunk_chain(output_dir)
    replay_wall_seconds = 1.25
    prefix_cumulative_wall = (
        float(envelopes[1]["cumulative_wall_seconds"]) + replay_wall_seconds
    )
    publish_prefix_replay_result(
        output_dir,
        envelopes[1],
        replay_wall_seconds=replay_wall_seconds,
        cumulative_wall_seconds=prefix_cumulative_wall,
    )

    chain = validate_checkpoint_chain(
        output_dir,
        registration_sha256=REGISTRATION_SHA256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
    )
    journal = validate_journal(output_dir, LOGICAL_EXECUTION_ID)
    resumed = restore_training_runtime(
        chain[-1],
        registration_sha256=REGISTRATION_SHA256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
    )
    resumed_from_output = resume_training_runtime_from_output(
        output_dir,
        registration_sha256=REGISTRATION_SHA256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
    )

    assert len(chain) == 2
    assert [row["phase"] for row in journal] == [
        "started",
        "continued",
        "continued",
    ]
    assert _model_payload(resumed) == _model_payload(primary)
    assert _model_payload(resumed_from_output) == _model_payload(primary)
    assert resumed.next_chunk_index == primary.next_chunk_index == 2
    assert resumed.completed_episodes == primary.completed_episodes == 128
    assert resumed_from_output.cumulative_wall_seconds == prefix_cumulative_wall
    assert verify_checkpoint_prefix_replay(
        envelopes[1], environment_factory=_training_factory
    ) is True


def test_prefix_replay_uses_remaining_cumulative_wall_budget(tmp_path):
    output_dir = tmp_path / "experiment"
    _, envelopes = _publish_two_chunk_chain(output_dir)
    checkpoint_two = copy.deepcopy(envelopes[1])
    checkpoint_two["cumulative_wall_seconds"] = MAX_WALL_SECONDS - 0.5

    class StepClock:
        def __init__(self):
            self.value = 0.0

        def __call__(self):
            self.value += 1.0
            return self.value

    with pytest.raises(ExperimentBlocked, match="wall-time"):
        verify_checkpoint_prefix_replay(
            checkpoint_two,
            environment_factory=_training_factory,
            clock=StepClock(),
        )


@pytest.mark.parametrize("tamper", ["payload", "chain", "extra", "partial"])
def test_checkpoint_chain_fails_closed_on_tamper_or_partial_files(tmp_path, tamper):
    output_dir = tmp_path / "experiment"
    _, _ = _publish_two_chunk_chain(output_dir)
    checkpoint_dir = output_dir / "checkpoints"
    second = checkpoint_dir / "checkpoint_0002.json"

    if tamper == "payload":
        value = json.loads(second.read_text(encoding="utf-8"))
        value["state_payload_sha256"] = "0" * 64
        second.write_bytes(canonical_json_bytes(value))
    elif tamper == "chain":
        value = json.loads(second.read_text(encoding="utf-8"))
        value["previous_checkpoint_sha256"] = "0" * 64
        second.write_bytes(canonical_json_bytes(value))
    elif tamper == "extra":
        (checkpoint_dir / "checkpoint_9999.json").write_text("{}\n", encoding="utf-8")
    else:
        (checkpoint_dir / "checkpoint_0003.json.tmp").write_text(
            "partial", encoding="utf-8"
        )

    with pytest.raises(ExperimentBlocked):
        validate_checkpoint_chain(
            output_dir,
            registration_sha256=REGISTRATION_SHA256,
            implementation_commit=IMPLEMENTATION_COMMIT,
            logical_execution_id=LOGICAL_EXECUTION_ID,
        )


def test_interrupted_checkpoint_publication_preserves_last_complete_chain(
    tmp_path, monkeypatch
):
    output_dir = tmp_path / "experiment"
    runtime = initialize_training_runtime()
    run_registered_training_chunk(runtime, environment_factory=_training_factory)
    first = build_checkpoint_envelope(
        runtime,
        registration_sha256=REGISTRATION_SHA256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
        previous_checkpoint_bytes=None,
    )
    first_path = publish_checkpoint(output_dir, first)
    first_bytes = first_path.read_bytes()
    run_registered_training_chunk(runtime, environment_factory=_training_factory)
    second = build_checkpoint_envelope(
        runtime,
        registration_sha256=REGISTRATION_SHA256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
        previous_checkpoint_bytes=first_bytes,
    )

    def interrupted_replace(source, destination):
        raise OSError("simulated checkpoint interruption")

    monkeypatch.setattr(experiment_module.os, "replace", interrupted_replace)
    with pytest.raises(OSError, match="simulated"):
        publish_checkpoint(output_dir, second)

    assert first_path.read_bytes() == first_bytes
    assert not (output_dir / "checkpoints" / "checkpoint_0002.json").exists()
    assert not (output_dir / "checkpoints" / "checkpoint_0002.json.tmp").exists()


@pytest.mark.parametrize(
    "boundary", ["checkpoint", "training", "journal", "pending_cleanup"]
)
def test_pending_chunk_recovers_each_cross_artifact_commit_boundary(
    tmp_path, monkeypatch, boundary
):
    output_name = f"noncombat_simulator_rl_experiment_pending_{boundary}"
    output_dir = tmp_path / output_name
    registration_bytes, authorization_bytes = _terminal_controls(output_name)
    initialize_experiment_output(
        output_dir,
        registration_bytes=registration_bytes,
        authorization_bytes=authorization_bytes,
    )
    registration_sha256 = hashlib.sha256(registration_bytes).hexdigest()
    runtime = initialize_training_runtime()
    summary = run_registered_training_chunk(
        runtime, environment_factory=_training_factory
    )
    original_install = experiment_module._install_exact_artifact
    original_append = experiment_module.append_journal_record
    original_unlink = Path.unlink
    install_calls = 0

    def interrupt_install(path, payload):
        nonlocal install_calls
        install_calls += 1
        if (boundary == "checkpoint" and install_calls == 1) or (
            boundary == "training" and install_calls == 2
        ):
            raise OSError(f"simulated {boundary} interruption")
        return original_install(path, payload)

    def interrupt_journal(*args, **kwargs):
        if boundary == "journal" and kwargs.get("phase") == "continued":
            raise OSError("simulated journal interruption")
        return original_append(*args, **kwargs)

    def interrupt_cleanup(path, *args, **kwargs):
        if boundary == "pending_cleanup" and Path(path).name == "pending_chunk.json":
            raise OSError("simulated pending cleanup interruption")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(experiment_module, "_install_exact_artifact", interrupt_install)
    monkeypatch.setattr(experiment_module, "append_journal_record", interrupt_journal)
    monkeypatch.setattr(Path, "unlink", interrupt_cleanup)
    with pytest.raises(OSError, match="simulated"):
        persist_completed_training_chunk(
            output_dir,
            runtime,
            summary,
            registration_sha256=registration_sha256,
            implementation_commit=IMPLEMENTATION_COMMIT,
            logical_execution_id=LOGICAL_EXECUTION_ID,
        )
    assert (output_dir / "pending_chunk.json").is_file()

    monkeypatch.setattr(experiment_module, "_install_exact_artifact", original_install)
    monkeypatch.setattr(experiment_module, "append_journal_record", original_append)
    monkeypatch.setattr(Path, "unlink", original_unlink)
    envelope = recover_pending_training_chunk(
        output_dir,
        registration_sha256=registration_sha256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
    )
    resumed = resume_training_runtime_from_output(
        output_dir,
        registration_sha256=registration_sha256,
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
    )

    assert envelope["checkpoint_index"] == 1
    assert resumed.next_chunk_index == 1
    assert _model_payload(resumed) == _model_payload(runtime)
    assert not (output_dir / "pending_chunk.json").exists()


def test_terminal_journal_rejects_additional_records_and_resume(tmp_path):
    output_dir = tmp_path / "experiment"
    append_journal_record(
        output_dir,
        phase="started",
        logical_execution_id=LOGICAL_EXECUTION_ID,
        details={"registration_sha256": REGISTRATION_SHA256},
    )
    append_journal_record(
        output_dir,
        phase="terminal",
        logical_execution_id=LOGICAL_EXECUTION_ID,
        details={"verdict": "experiment_stopped_at_canary"},
    )

    with pytest.raises(ExperimentBlocked, match="terminal"):
        append_journal_record(
            output_dir,
            phase="continued",
            logical_execution_id=LOGICAL_EXECUTION_ID,
            details={},
        )
    with pytest.raises(ExperimentBlocked, match="terminal"):
        resume_training_runtime_from_output(
            output_dir,
            registration_sha256=REGISTRATION_SHA256,
            implementation_commit=IMPLEMENTATION_COMMIT,
            logical_execution_id=LOGICAL_EXECUTION_ID,
        )


@pytest.mark.parametrize("tamper", ["extra", "missing_checkpoint", "missing_journal", "identity"])
def test_directory_resume_rejects_inventory_and_identity_drift(tmp_path, tamper):
    output_dir = tmp_path / "experiment"
    _publish_two_chunk_chain(output_dir)

    if tamper == "extra":
        (output_dir / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    elif tamper == "missing_checkpoint":
        (output_dir / "checkpoints" / "checkpoint_0002.json").unlink()
    elif tamper == "missing_journal":
        (output_dir / "journal" / "record_000002.json").unlink()

    kwargs = {
        "registration_sha256": REGISTRATION_SHA256,
        "implementation_commit": (
            "a" * 40 if tamper == "identity" else IMPLEMENTATION_COMMIT
        ),
        "logical_execution_id": LOGICAL_EXECUTION_ID,
    }
    with pytest.raises(ExperimentBlocked):
        resume_training_runtime_from_output(output_dir, **kwargs)


def test_execution_lease_is_exclusive_and_recoverable_for_same_logical_id(tmp_path):
    output_dir = tmp_path / "experiment"

    first = ExecutionLease.acquire(output_dir, LOGICAL_EXECUTION_ID)
    try:
        with pytest.raises(ExperimentBlocked, match="lease"):
            ExecutionLease.acquire(output_dir, LOGICAL_EXECUTION_ID)
    finally:
        first.close()

    resumed = ExecutionLease.acquire(output_dir, LOGICAL_EXECUTION_ID)
    resumed.close()


def test_chunk_wall_bound_rolls_back_model_optimizer_and_coordinates():
    class StepClock:
        def __init__(self):
            self.value = 0.0

        def __call__(self):
            self.value += 10_000.0
            return self.value

    runtime = initialize_training_runtime()
    before = _model_payload(runtime)

    with pytest.raises(ExperimentBlocked, match="wall-time"):
        run_registered_training_chunk(
            runtime,
            environment_factory=_training_factory,
            clock=StepClock(),
        )

    assert _model_payload(runtime) == before
    assert runtime.next_chunk_index == 0


def test_checkpoint_envelope_rejects_nonfinite_runtime():
    runtime = initialize_training_runtime()
    runtime.cumulative_wall_seconds = math.nan

    with pytest.raises(ExperimentBlocked, match="cumulative wall"):
        build_checkpoint_envelope(
            runtime,
            registration_sha256=REGISTRATION_SHA256,
            implementation_commit=IMPLEMENTATION_COMMIT,
            logical_execution_id=LOGICAL_EXECUTION_ID,
            previous_checkpoint_bytes=None,
        )


def _frozen_model_payload(model) -> bytes:
    return canonical_json_bytes(
        {
            name: encode_tensor(tensor)
            for name, tensor in sorted(model.state_dict().items())
        }
    )


def test_frozen_canary_evaluation_is_paired_deterministic_and_non_updating():
    initial = initialize_training_runtime().model
    trained = initialize_training_runtime().model
    initial_before = _frozen_model_payload(initial)
    trained_before = _frozen_model_payload(trained)

    first = paired_policy_evaluation(
        initial,
        trained,
        environment_factory=_training_factory,
        cohort="canary",
    )
    second = paired_policy_evaluation(
        initial,
        trained,
        environment_factory=_training_factory,
        cohort="canary",
    )

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert len(first["initial"]["rows"]) == len(CANARY_SEEDS)
    assert len(first["trained"]["rows"]) == len(CANARY_SEEDS)
    assert len(first["paired_rows"]) == len(CANARY_SEEDS)
    assert first["unsupported_rate_denominator"] == 2 * len(CANARY_SEEDS)
    assert _frozen_model_payload(initial) == initial_before
    assert _frozen_model_payload(trained) == trained_before


def _synthetic_policy_rows(
    seeds,
    *,
    floor: float,
    victories: int = 0,
    unsupported: int = 0,
):
    rows = []
    for index, seed in enumerate(seeds):
        is_unsupported = index < unsupported
        is_victory = not is_unsupported and index < victories
        category = TARGET_CATEGORIES[index % len(TARGET_CATEGORIES)]
        rows.append(
            {
                "action_sequence_sha256": "c" * 64,
                "candidate_legality": True,
                "categories": [category],
                "decisions": 1,
                "last_supported_floor": floor,
                "outcome": (
                    None
                    if is_unsupported
                    else "player_victory" if is_victory else "player_loss"
                ),
                "policy_input_sha256s": ["d" * 64],
                "retained": True,
                "seed": int(seed),
                "selected_action_ids": [f"{category}:fixture:0"],
                "terminal_floor": None if is_unsupported else floor,
                "total_reward": 0.0,
                "unsupported_reason": (
                    REGISTERED_SUPPORT_BLOCKERS[0] if is_unsupported else None
                ),
                "victory": is_victory,
            }
        )
    return rows


def _synthetic_evaluation(
    cohort: str,
    *,
    initial_floor: float = 10.0,
    trained_floor: float = 12.0,
    initial_victories: int = 0,
    trained_victories: int = 0,
    initial_unsupported: int = 0,
    trained_unsupported: int = 0,
):
    seeds = CANARY_SEEDS if cohort == "canary" else HOLDOUT_SEEDS
    return build_paired_evaluation(
        _synthetic_policy_rows(
            seeds,
            floor=initial_floor,
            victories=initial_victories,
            unsupported=initial_unsupported,
        ),
        _synthetic_policy_rows(
            seeds,
            floor=trained_floor,
            victories=trained_victories,
            unsupported=trained_unsupported,
        ),
        cohort=cohort,
    )


def test_paired_bootstrap_is_fixed_and_strictly_positive_only_when_supported():
    positive = paired_bootstrap_interval([2.0] * 128)
    repeated = paired_bootstrap_interval([2.0] * 128)
    inconclusive = paired_bootstrap_interval([-1.0, 0.0, 1.0, 1.0])

    assert positive == repeated
    assert positive["lower"] == 2.0
    assert inconclusive["mean"] > 0.0
    assert inconclusive["lower"] <= 0.0


def test_canary_gate_uses_policy_episode_support_victory_and_floor_checks():
    passed = classify_canary_evaluation(_synthetic_evaluation("canary"))

    assert passed["passed"] is True
    assert passed["blockers"] == []
    assert passed["unsupported_rate"] == 0.0

    support_failed = classify_canary_evaluation(
        _synthetic_evaluation("canary", trained_unsupported=26)
    )
    assert support_failed["passed"] is False
    assert "unsupported_rate" in support_failed["blockers"]
    assert support_failed["unsupported_rate_denominator"] == 256


def test_paired_evaluation_rejects_unknown_episode_fields():
    initial = _synthetic_policy_rows(CANARY_SEEDS, floor=10.0)
    trained = _synthetic_policy_rows(CANARY_SEEDS, floor=12.0)
    initial[0]["unexpected"] = True

    with pytest.raises(ExperimentBlocked, match="fields mismatch"):
        build_paired_evaluation(initial, trained, cohort="canary")

    victory_failed = classify_canary_evaluation(
        _synthetic_evaluation(
            "canary", initial_victories=2, trained_victories=1
        )
    )
    assert "trained_victory_noninferiority" in victory_failed["blockers"]

    floor_failed = classify_canary_evaluation(
        _synthetic_evaluation("canary", trained_floor=10.0)
    )
    assert "paired_floor_lower_bound" in floor_failed["blockers"]


def test_holdout_learning_signal_requires_both_more_victories_and_positive_floor():
    positive = classify_holdout_evaluation(
        _synthetic_evaluation("holdout", trained_victories=1)
    )
    no_victory = classify_holdout_evaluation(_synthetic_evaluation("holdout"))
    no_floor = classify_holdout_evaluation(
        _synthetic_evaluation(
            "holdout", trained_floor=10.0, trained_victories=1
        )
    )

    assert positive["verdict"] == "experiment_valid_with_learning_signal"
    assert positive["victory_signal"] is True
    assert positive["floor_signal"] is True
    assert no_victory["verdict"] == "experiment_valid_without_learning_signal"
    assert no_floor["verdict"] == "experiment_valid_without_learning_signal"


def test_conditional_evaluation_keeps_holdout_untouched_after_canary_failure(
    monkeypatch,
):
    calls = []

    def fake_paired(*args, cohort, **kwargs):
        calls.append(cohort)
        if cohort == "holdout":
            raise AssertionError("holdout must remain untouched")
        return _synthetic_evaluation("canary", trained_floor=10.0)

    monkeypatch.setattr(experiment_module, "paired_policy_evaluation", fake_paired)
    result = run_conditional_evaluation(
        object(), object(), environment_factory=lambda seed: None
    )

    assert calls == ["canary"]
    assert result["verdict"] == "experiment_stopped_at_canary"
    assert result["holdout"] == {"accessed": False, "episode_count": 0}


def test_conditional_evaluation_accesses_holdout_once_only_after_canary_pass(
    monkeypatch,
):
    calls = []

    def fake_paired(*args, cohort, **kwargs):
        calls.append(cohort)
        if cohort == "canary":
            return _synthetic_evaluation("canary")
        return _synthetic_evaluation("holdout", trained_victories=1)

    monkeypatch.setattr(experiment_module, "paired_policy_evaluation", fake_paired)
    result = run_conditional_evaluation(
        object(), object(), environment_factory=lambda seed: None
    )

    assert calls == ["canary", "holdout"]
    assert result["holdout"]["accessed"] is True
    assert result["verdict"] == "experiment_valid_with_learning_signal"


def _terminal_controls(output_name: str):
    registration = _registration()
    registration["identity"]["implementation"]["commit"] = IMPLEMENTATION_COMMIT
    registration = validate_registration(registration)
    registration_bytes = canonical_json_bytes(registration)
    authorization = build_execution_authorization(
        registration_binding={
            "commit": "f" * 40,
            "path": "reports/noncombat_simulator_rl_experiment_test_registration.json",
            "sha256": hashlib.sha256(registration_bytes).hexdigest(),
            "size_bytes": len(registration_bytes),
        },
        logical_execution_id=LOGICAL_EXECUTION_ID,
        output_directory=f"reports/{output_name}",
    )
    return registration_bytes, canonical_json_bytes(authorization)


def _run_standalone_verifier(output_dir: Path):
    return subprocess.run(
        [
            sys.executable,
            str(
                Path(__file__).resolve().parents[1]
                / "analysis_scripts"
                / "verify_noncombat_simulator_rl_experiment.py"
            ),
            str(output_dir),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def _synthetic_training_summary(chunk_index: int):
    rows = []
    coordinates = registered_chunk_coordinates(chunk_index)
    for row_index, seed in enumerate(coordinates["seeds"]):
        category = TARGET_CATEGORIES[row_index % len(TARGET_CATEGORIES)]
        rows.append(
            {
                "action_sequence_sha256": "a" * 64,
                "candidate_legality": True,
                "categories": [category],
                "chunk_index": chunk_index,
                "decisions": 1,
                "last_supported_floor": 1.0,
                "outcome": "player_loss",
                "pass_index": coordinates["pass_index"],
                "policy_input_sha256s": ["b" * 64],
                "retained": True,
                "seed": seed,
                "selected_action_ids": [f"{category}:fixture:0"],
                "terminal_floor": 1.0,
                "total_reward": 0.0,
                "unsupported_reason": None,
                "victory": False,
            }
        )
    return {
        "candidate_legality": True,
        "categories": list(TARGET_CATEGORIES),
        "chunk_index": chunk_index,
        "episode_rows": rows,
        "episodes": CHECKPOINT_INTERVAL_EPISODES,
        "loss": 0.0,
        "mean_episode_return": 0.0,
        "optimizer_update": chunk_index + 1,
        "pass_index": coordinates["pass_index"],
        "unsupported_episodes": 0,
        "victories": 0,
    }


def _publish_synthetic_chain(output_dir: Path, chunk_count: int):
    registration_bytes, authorization_bytes = _terminal_controls(output_dir.name)
    initialize_experiment_output(
        output_dir,
        registration_bytes=registration_bytes,
        authorization_bytes=authorization_bytes,
    )
    registration_sha256 = hashlib.sha256(registration_bytes).hexdigest()
    runtime = initialize_training_runtime()
    previous = None
    for chunk_index in range(chunk_count):
        runtime.next_chunk_index = chunk_index + 1
        runtime.completed_episodes = (chunk_index + 1) * CHECKPOINT_INTERVAL_EPISODES
        runtime.optimizer_updates = chunk_index + 1
        runtime.cumulative_wall_seconds = (chunk_index + 1) / 100.0
        envelope = build_checkpoint_envelope(
            runtime,
            registration_sha256=registration_sha256,
            implementation_commit=IMPLEMENTATION_COMMIT,
            logical_execution_id=LOGICAL_EXECUTION_ID,
            previous_checkpoint_bytes=previous,
        )
        checkpoint_path = publish_checkpoint(output_dir, envelope)
        previous = checkpoint_path.read_bytes()
        training_path = publish_training_chunk_summary(
            output_dir,
            _synthetic_training_summary(chunk_index),
            checkpoint_bytes=previous,
        )
        append_journal_record(
            output_dir,
            phase="continued",
            logical_execution_id=LOGICAL_EXECUTION_ID,
            details={
                "checkpoint_index": chunk_index + 1,
                "checkpoint_sha256": hashlib.sha256(previous).hexdigest(),
                "training_summary_sha256": hashlib.sha256(
                    training_path.read_bytes()
                ).hexdigest(),
            },
        )
        if chunk_index == 1:
            replay_wall_seconds = 0.005
            runtime.cumulative_wall_seconds += replay_wall_seconds
            publish_prefix_replay_result(
                output_dir,
                envelope,
                replay_wall_seconds=replay_wall_seconds,
                cumulative_wall_seconds=runtime.cumulative_wall_seconds,
            )
    return runtime


def test_prefix_replay_time_survives_interruption_before_checkpoint_three(tmp_path):
    output_dir = tmp_path / "noncombat_simulator_rl_experiment_prefix_resume"
    runtime = _publish_synthetic_chain(output_dir, 2)

    resumed = resume_training_runtime_from_output(
        output_dir,
        registration_sha256=hashlib.sha256(
            (output_dir / "registration.json").read_bytes()
        ).hexdigest(),
        implementation_commit=IMPLEMENTATION_COMMIT,
        logical_execution_id=LOGICAL_EXECUTION_ID,
    )
    prefix = validate_prefix_replay_result(output_dir)

    assert resumed.cumulative_wall_seconds == runtime.cumulative_wall_seconds
    assert resumed.cumulative_wall_seconds == prefix["cumulative_wall_seconds"]


def test_resume_rejects_checkpoint_that_drops_prefix_replay_time(tmp_path):
    output_dir = tmp_path / "noncombat_simulator_rl_experiment_prefix_regression"
    _publish_synthetic_chain(output_dir, 3)
    prefix_path = output_dir / "prefix_replay.json"
    prefix = json.loads(prefix_path.read_text(encoding="utf-8"))
    checkpoint_two = json.loads(
        (output_dir / "checkpoints" / "checkpoint_0002.json").read_text(
            encoding="utf-8"
        )
    )
    prefix["replay_wall_seconds"] = 1.0
    prefix["cumulative_wall_seconds"] = (
        checkpoint_two["cumulative_wall_seconds"] + 1.0
    )
    prefix_path.write_bytes(canonical_json_bytes(prefix))

    with pytest.raises(ExperimentBlocked, match="precedes prefix replay"):
        resume_training_runtime_from_output(
            output_dir,
            registration_sha256=hashlib.sha256(
                (output_dir / "registration.json").read_bytes()
            ).hexdigest(),
            implementation_commit=IMPLEMENTATION_COMMIT,
            logical_execution_id=LOGICAL_EXECUTION_ID,
        )


def _terminal_evaluation(verdict: str):
    if verdict == "experiment_stopped_at_canary":
        canary = _synthetic_evaluation("canary", trained_floor=10.0)
        return {
            "canary": canary,
            "canary_gate": classify_canary_evaluation(canary),
            "holdout": {"accessed": False, "episode_count": 0},
            "verdict": verdict,
        }
    canary = _synthetic_evaluation("canary")
    holdout = _synthetic_evaluation(
        "holdout",
        trained_victories=(
            1 if verdict == "experiment_valid_with_learning_signal" else 0
        ),
    )
    return {
        "canary": canary,
        "canary_gate": classify_canary_evaluation(canary),
        "holdout": {
            "accessed": True,
            "classification": classify_holdout_evaluation(holdout),
            "episode_count": 2 * len(HOLDOUT_SEEDS),
            "evaluation": holdout,
        },
        "verdict": verdict,
    }


def test_output_initialization_binds_controls_and_starts_one_journal(tmp_path):
    output_dir = tmp_path / "noncombat_simulator_rl_experiment_init"
    registration_bytes, authorization_bytes = _terminal_controls(output_dir.name)

    configuration = initialize_experiment_output(
        output_dir,
        registration_bytes=registration_bytes,
        authorization_bytes=authorization_bytes,
    )

    assert configuration["formal_readiness_verdict"] == (
        "not_ready_for_bounded_training_proposal"
    )
    assert not any(configuration["authority"].values())
    assert (output_dir / "registration.json").read_bytes() == registration_bytes
    assert (output_dir / "authorization.json").read_bytes() == authorization_bytes
    assert (output_dir / "checkpoints").is_dir()
    assert (output_dir / "training").is_dir()
    assert [row["phase"] for row in validate_journal(output_dir, LOGICAL_EXECUTION_ID)] == [
        "started"
    ]
    with pytest.raises(ExperimentBlocked, match="absent"):
        initialize_experiment_output(
            output_dir,
            registration_bytes=registration_bytes,
            authorization_bytes=authorization_bytes,
        )


@pytest.mark.parametrize(
    "verdict",
    [
        "experiment_stopped_at_canary",
        "experiment_valid_without_learning_signal",
        "experiment_valid_with_learning_signal",
    ],
)
def test_terminal_publication_is_hash_closed_and_non_authorizing(tmp_path, verdict):
    output_dir = tmp_path / f"noncombat_simulator_rl_experiment_{verdict}"
    runtime = _publish_synthetic_chain(output_dir, 64)

    manifest = publish_terminal_artifacts(
        output_dir,
        runtime=runtime,
        evaluation=_terminal_evaluation(verdict),
        prefix_replay_verified=True,
    )
    validated = validate_terminal_artifact_directory(output_dir)

    assert manifest == validated
    assert manifest["verdict"] == verdict
    assert not any(manifest["authority"].values())
    assert manifest["formal_readiness_verdict"] == (
        "not_ready_for_bounded_training_proposal"
    )
    assert (output_dir / "artifact_manifest.json").is_file()
    assert (output_dir / "evaluation.json").is_file()
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["training"]["episodes"] == TRAINING_EPISODES
    assert metrics["training"]["optimizer_updates"] == 64
    assert not any(metrics["authority"].values())
    verified = _run_standalone_verifier(output_dir)
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["verdict"] == verdict


def test_blocked_terminal_uses_reached_evidence_without_evaluation(tmp_path):
    output_dir = tmp_path / "noncombat_simulator_rl_experiment_blocked"
    runtime = _publish_synthetic_chain(output_dir, 2)

    manifest = publish_terminal_artifacts(
        output_dir,
        runtime=runtime,
        blocked_reason="registered wall-time bound reached",
    )

    assert manifest["verdict"] == "experiment_blocked"
    assert not (output_dir / "evaluation.json").exists()
    assert validate_terminal_artifact_directory(output_dir) == manifest
    journal = validate_journal(output_dir, LOGICAL_EXECUTION_ID)
    assert journal[-1]["phase"] == "blocked"
    verified = _run_standalone_verifier(output_dir)
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["verdict"] == "experiment_blocked"


def test_standalone_verifier_has_no_torch_native_or_project_imports():
    source = (
        Path(__file__).resolve().parents[1]
        / "analysis_scripts"
        / "verify_noncombat_simulator_rl_experiment.py"
    ).read_text(encoding="utf-8")

    assert "import torch" not in source
    assert "\nimport analysis_scripts" not in source
    assert "\nfrom analysis_scripts" not in source


def test_runner_help_and_control_validation_are_source_only(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    runner = repo_root / "scripts" / "run_noncombat_simulator_rl_experiment.py"
    help_result = subprocess.run(
        [sys.executable, str(runner), "--help"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert help_result.returncode == 0, help_result.stderr
    assert "execute" in help_result.stdout

    registration_bytes, authorization_bytes = _terminal_controls(
        "noncombat_simulator_rl_experiment_cli"
    )
    registration_path = tmp_path / "registration.json"
    authorization_path = tmp_path / "authorization.json"
    registration_path.write_bytes(registration_bytes)
    authorization_path.write_bytes(authorization_bytes)
    validated = subprocess.run(
        [
            sys.executable,
            str(runner),
            "validate-controls",
            "--registration",
            str(registration_path),
            "--authorization",
            str(authorization_path),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert validated.returncode == 0, validated.stderr
    payload = json.loads(validated.stdout)
    assert payload["validated"] is True
    assert payload["execution_authorized"] is True
    assert "sts_lightspeed_noncombat_adapter" not in validated.stdout


def test_runner_rejects_output_path_substitution_before_git_or_native(
    tmp_path, monkeypatch
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    registration = validate_registration(_registration())
    registration_bytes = canonical_json_bytes(registration)
    authorization = build_execution_authorization(
        registration_binding={
            "commit": "f" * 40,
            "path": "reports/noncombat_simulator_rl_experiment_r1_registration.json",
            "sha256": hashlib.sha256(registration_bytes).hexdigest(),
            "size_bytes": len(registration_bytes),
        },
        logical_execution_id=LOGICAL_EXECUTION_ID,
        output_directory="reports/noncombat_simulator_rl_experiment_r1",
    )
    authorization_bytes = canonical_json_bytes(authorization)
    monkeypatch.setattr(
        experiment_runner,
        "_load_controls",
        lambda *_args: (
            registration,
            registration_bytes,
            authorization,
            authorization_bytes,
        ),
    )
    monkeypatch.setattr(
        experiment_runner,
        "_git_bytes",
        lambda *_args: pytest.fail("Git must not run after output path substitution"),
    )

    with pytest.raises(ExperimentBlocked, match="output path mismatch"):
        experiment_runner.source_only_preflight(
            repo_root=repo_root,
            registration_path=repo_root / "reports" / "registration.json",
            authorization_path=repo_root / "reports" / "authorization.json",
            output_dir=tmp_path / "elsewhere" / "noncombat_simulator_rl_experiment_r1",
            simulator_repo=tmp_path / "simulator",
            module_path=tmp_path / "adapter.pyd",
        )


def test_started_execution_publishes_verifiable_blocked_terminal_on_native_failure(
    tmp_path, monkeypatch
):
    output_name = "noncombat_simulator_rl_experiment_native_block"
    registration_bytes, authorization_bytes = _terminal_controls(output_name)
    registration_path = tmp_path / "registration.json"
    authorization_path = tmp_path / "authorization.json"
    output_dir = tmp_path / output_name
    registration_path.write_bytes(registration_bytes)
    authorization_path.write_bytes(authorization_bytes)
    monkeypatch.setattr(
        experiment_runner,
        "source_only_preflight",
        lambda **_kwargs: {"source_only_preflight": True},
    )
    monkeypatch.setattr(
        experiment_runner,
        "load_native_module",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("fixture native load failure")
        ),
    )
    args = experiment_runner.build_parser().parse_args(
        [
            "execute",
            "--repo-root",
            str(Path(__file__).resolve().parents[1]),
            "--registration",
            str(registration_path),
            "--authorization",
            str(authorization_path),
            "--output-dir",
            str(output_dir),
            "--simulator-repo",
            str(tmp_path / "simulator"),
            "--module",
            str(tmp_path / "adapter.pyd"),
        ]
    )

    result = experiment_runner.execute_authorized_experiment(args)

    assert result["manifest"]["verdict"] == "experiment_blocked"
    assert validate_terminal_artifact_directory(output_dir)["verdict"] == (
        "experiment_blocked"
    )
    verified = _run_standalone_verifier(output_dir)
    assert verified.returncode == 0, verified.stderr


def test_runner_cli_returns_distinct_status_for_published_blocked_terminal(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(
        experiment_runner,
        "execute_authorized_experiment",
        lambda _args: {"manifest": {"verdict": "experiment_blocked"}},
    )
    result = experiment_runner.main(
        [
            "execute",
            "--repo-root",
            str(tmp_path),
            "--registration",
            str(tmp_path / "registration.json"),
            "--authorization",
            str(tmp_path / "authorization.json"),
            "--output-dir",
            str(tmp_path / "output"),
            "--simulator-repo",
            str(tmp_path / "simulator"),
            "--module",
            str(tmp_path / "adapter.pyd"),
        ]
    )

    assert result == 2
    assert json.loads(capsys.readouterr().out)["manifest"]["verdict"] == (
        "experiment_blocked"
    )


def test_live_entrypoints_do_not_import_experiment_or_runner():
    repo_root = Path(__file__).resolve().parents[1]
    for relative in ("main.py", "scripts/run_training_batch.py"):
        source = (repo_root / relative).read_text(encoding="utf-8")
        assert "noncombat_simulator_rl_experiment" not in source
        assert "run_noncombat_simulator_rl_experiment" not in source


def test_terminal_manifest_detects_tampering(tmp_path):
    output_dir = tmp_path / "noncombat_simulator_rl_experiment_tamper"
    runtime = _publish_synthetic_chain(output_dir, 2)
    publish_terminal_artifacts(
        output_dir,
        runtime=runtime,
        blocked_reason="fixture blocker",
    )
    metrics_path = output_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["authority"]["policy_promotion"] = True
    metrics_path.write_bytes(canonical_json_bytes(metrics))

    with pytest.raises(ExperimentBlocked, match="inventory"):
        validate_terminal_artifact_directory(output_dir)


@pytest.mark.parametrize("artifact", ["model", "prefix", "report", "lease"])
def test_standalone_verifier_rejects_semantic_tampering_after_rehash(
    tmp_path, artifact
):
    output_dir = tmp_path / f"noncombat_simulator_rl_experiment_tamper_{artifact}"
    runtime = _publish_synthetic_chain(output_dir, 2)
    publish_terminal_artifacts(
        output_dir,
        runtime=runtime,
        blocked_reason="fixture blocker",
    )

    if artifact == "model":
        path = output_dir / "model.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["unexpected"] = True
        path.write_bytes(canonical_json_bytes(value))
    elif artifact == "prefix":
        path = output_dir / "prefix_replay.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["cumulative_wall_seconds"] += 1.0
        path.write_bytes(canonical_json_bytes(value))
    elif artifact == "report":
        (output_dir / "report.md").write_text("altered\n", encoding="utf-8")
    else:
        (output_dir / ".execution.lease").write_bytes(
            canonical_json_bytes(
                {
                    "logical_execution_id": "different-execution",
                    "schema_version": experiment_module.LEASE_SCHEMA_VERSION,
                }
            )
        )

    manifest_path = output_dir / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_inventory"] = experiment_module._artifact_inventory(output_dir)
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    verified = _run_standalone_verifier(output_dir)

    assert verified.returncode != 0


def test_interrupted_terminal_publication_never_installs_manifest(
    tmp_path, monkeypatch
):
    output_dir = tmp_path / "noncombat_simulator_rl_experiment_interrupted"
    runtime = _publish_synthetic_chain(output_dir, 2)
    replace = experiment_module.os.replace

    def interrupt_model(source, destination):
        if Path(destination).name == "model.json":
            raise OSError("simulated terminal publication interruption")
        return replace(source, destination)

    monkeypatch.setattr(experiment_module.os, "replace", interrupt_model)
    with pytest.raises(OSError, match="simulated"):
        publish_terminal_artifacts(
            output_dir,
            runtime=runtime,
            blocked_reason="fixture blocker",
        )

    assert not (output_dir / "artifact_manifest.json").exists()
    assert validate_journal(output_dir, LOGICAL_EXECUTION_ID)[-1]["phase"] == (
        "continued"
    )
