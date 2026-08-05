from __future__ import annotations

import copy
import hashlib
import inspect
import json
import math
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import torch

import analysis_scripts.noncombat_state_conditioned_simulator_learning_experiment as experiment
import analysis_scripts.verify_noncombat_state_conditioned_simulator_learning_experiment as terminal_verifier
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    TARGET_CATEGORIES,
    build_transition,
)
from analysis_scripts.noncombat_state_conditioned_ranker import (
    ARCHITECTURE_ID,
    StateConditionedCandidateRanker,
)


ROOT = Path(__file__).resolve().parents[1]
PREIMPLEMENTATION = (
    ROOT
    / (
        "reports/noncombat_state_conditioned_simulator_learning_"
        "experiment_20260805_preimplementation.json"
    )
)
IMPLEMENTATION_VERIFICATION = (
    ROOT
    / (
        "reports/noncombat_state_conditioned_simulator_learning_"
        "experiment_20260805_implementation_verification.json"
    )
)


def _candidate(
    action_id: str,
    category: str,
    *,
    kind: str,
    price: int,
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "available": True,
        "category": category,
        "kind": kind,
        "label": action_id,
        "raw": {"price": price},
    }


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


class OneStepEnvironment:
    def __init__(
        self,
        seed: int,
        *,
        mutate_source: bool = False,
        nonfinite: bool = False,
    ) -> None:
        self.seed = seed
        self.mutate_source = mutate_source
        self.nonfinite = nonfinite
        self.selected: str | None = None
        self.terminal = False

    @property
    def category(self) -> str:
        return TARGET_CATEGORIES[self.seed % len(TARGET_CATEGORIES)]

    def snapshot(self) -> dict[str, object]:
        terminal_floor = 57 if self.selected == "good" else 3
        return {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_control": {"history": [], "policy_id": "test-control"},
            "category": None if self.terminal else self.category,
            "decision_count": 1 if self.terminal else 0,
            "schema_version": STATE_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "state": {
                "cur_hp": 80,
                "floor": terminal_floor if self.terminal else 0,
                "gold": math.inf if self.nonfinite else 99 + self.seed,
                "outcome": (
                    "player_victory"
                    if self.terminal and self.selected == "good"
                    else "player_loss" if self.terminal else "undecided"
                ),
                "seed": str(self.seed),
            },
            "terminal": self.terminal,
        }

    def legal_actions(self) -> list[dict[str, object]]:
        if self.terminal:
            return []
        kinds = {
            "card_reward": ("skip", "take"),
            "event": ("choose", "choose"),
            "route": ("choose", "choose"),
            "shop": ("leave", "buy"),
        }[self.category]
        return [
            _candidate("bad", self.category, kind=kinds[0], price=0),
            _candidate("good", self.category, kind=kinds[1], price=1),
        ]

    def clone(self):
        return self if self.mutate_source else copy.deepcopy(self)

    def step(self, action_id: str) -> dict[str, object]:
        before = self.snapshot()
        candidates = self.legal_actions()
        self.selected = action_id
        self.terminal = True
        return build_transition(
            before=before,
            candidates=candidates,
            selected_action_id=action_id,
            after=self.snapshot(),
            provenance=_provenance(),
        )


def _factory(seed: int) -> OneStepEnvironment:
    return OneStepEnvironment(seed)


def _model_bytes(model: torch.nn.Module) -> bytes:
    payload = {
        name: tensor.detach().cpu().reshape(-1).tolist()
        for name, tensor in sorted(model.state_dict().items())
    }
    return experiment.canonical_json_bytes(payload)


def _diagnostic_row(
    decision_id: str,
    category: str,
    *,
    selected_kind: str,
    alternative_kind: str,
    state_effect: float = 0.25,
    relative_order_changed: bool | None = None,
) -> dict[str, object]:
    selected = f"{category}:{selected_kind}:0"
    alternative = f"{category}:{alternative_kind}:1"
    return {
        "candidate_scores": {alternative: 0.0, selected: 1.0},
        "candidates": [
            {"action_id": selected, "kind": selected_kind},
            {"action_id": alternative, "kind": alternative_kind},
        ],
        "category": category,
        "decision_id": decision_id,
        "selected_action_id": selected,
        "state_effect": {
            "max_abs_relative_score_change": state_effect,
            "relative_order_changed": (
                state_effect > 0.0
                if relative_order_changed is None
                else relative_order_changed
            ),
        },
    }


def test_preimplementation_record_is_canonical_all_false_and_exactly_bound():
    raw = PREIMPLEMENTATION.read_bytes()
    record = json.loads(raw)

    assert raw == experiment.canonical_json_bytes(record)
    assert set(record["authority"].values()) == {False}
    assert record["contract"]["source_only"] is True
    assert record["contract"]["cohorts_materialized"] is False
    assert record["contract"]["output_root_materialized"] is False
    assert len(record["evidence"]) == 14
    for binding in record["evidence"].values():
        payload = (ROOT / binding["path"]).read_bytes()
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]

    planning_commit = record["planning"]["commit"]
    for binding in record["planning"]["files"].values():
        payload = subprocess.run(
            ["git", "show", f"{planning_commit}:{binding['path']}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        assert len(payload) == binding["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == binding["sha256"]


def test_implementation_verification_is_canonical_all_false_and_replayable():
    raw = IMPLEMENTATION_VERIFICATION.read_bytes()
    report = json.loads(raw)

    assert raw == experiment.canonical_json_bytes(report)
    assert experiment.validate_implementation_verification_report(report, ROOT) == report
    assert set(report["authority"].values()) == {False}
    assert report["verdict"] == "source_only_implementation_verified"
    assert report["frozen_evidence"]["binding_count"] == 14
    assert report["external_isolation"]["communication_mod_config"]["unchanged"] is True
    assert report["external_isolation"]["production_checkpoints"]["unchanged"] is True
    assert report["r2_terminal"]["verification"]["verification"] == "verified"
    assert report["checks"] == {
        "communication_mod_config_unchanged": True,
        "empirical_seed_consumed": False,
        "environment_constructed": False,
        "frozen_evidence_unchanged": True,
        "native_module_imported": False,
        "planning_evidence_unchanged": True,
        "production_checkpoint_inventory_unchanged": True,
        "r2_terminal_artifacts_verified": True,
        "torch_imported": False,
        "training_started": False,
    }


def test_implementation_verification_rejects_a_false_unchanged_claim():
    report = json.loads(IMPLEMENTATION_VERIFICATION.read_bytes())
    report["external_isolation"]["production_checkpoints"]["unchanged"] = False

    with pytest.raises(experiment.ExperimentBlocked, match="checkpoint.*unchanged"):
        experiment.validate_implementation_verification_report(report, ROOT)


def _implementation_report_rebound_to_current_sources():
    report = json.loads(IMPLEMENTATION_VERIFICATION.read_bytes())
    source_payloads = []
    for binding in report["implementation"]["source_files"]:
        payload = (ROOT / binding["path"]).read_bytes()
        binding["sha256"] = hashlib.sha256(payload).hexdigest()
        binding["size_bytes"] = len(payload)
        source_payloads.append((binding["path"], payload))
    report["implementation"]["working_source_sha256"] = (
        experiment._hash_named_bytes(source_payloads)
    )
    return report


def test_implementation_verification_rereads_current_external_state(monkeypatch):
    report = _implementation_report_rebound_to_current_sources()
    current = report["external_isolation"]["communication_mod_config"]["current"]
    drifted = {**current, "sha256": "0" * 64}

    monkeypatch.setattr(experiment, "external_file_binding", lambda path: drifted)

    with pytest.raises(experiment.ExperimentBlocked, match="config|binding|drift"):
        experiment.validate_implementation_verification_report(report, ROOT)


def test_implementation_verification_resnapshots_production_checkpoints(monkeypatch):
    report = _implementation_report_rebound_to_current_sources()
    current = report["external_isolation"]["production_checkpoints"]["current"]
    drifted = {**current, "inventory_sha256": "0" * 64}

    monkeypatch.setattr(
        experiment,
        "snapshot_production_checkpoints",
        lambda path: drifted,
    )

    with pytest.raises(experiment.ExperimentBlocked, match="checkpoint|inventory|drift"):
        experiment.validate_implementation_verification_report(report, ROOT)


def test_implementation_verification_reruns_source_only_import_probes(monkeypatch):
    report = _implementation_report_rebound_to_current_sources()
    calls: list[Path] = []

    def contaminated_probe(source: Path, *, repo_root: Path):
        calls.append(source)
        return {
            "empirical_seed_file_accessed": False,
            "native_module_imported": False,
            "torch_imported": True,
        }

    monkeypatch.setattr(experiment, "_source_only_import_probe", contaminated_probe)

    with pytest.raises(experiment.ExperimentBlocked, match="probe|Torch|runtime"):
        experiment.validate_implementation_verification_report(report, ROOT)
    assert calls


def test_implementation_verification_reruns_r2_terminal_verifier(monkeypatch):
    report = _implementation_report_rebound_to_current_sources()
    original_run = experiment.subprocess.run
    verifier_calls: list[tuple[str, ...]] = []

    def fake_run(args, *run_args, **run_kwargs):
        command = tuple(str(value) for value in args)
        if any(
            value.replace("\\", "/").endswith(experiment.R2_VERIFIER_PATH)
            for value in command
        ):
            verifier_calls.append(command)
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps(
                    {
                        "artifact_count": 1,
                        "checks": 1,
                        "formal_readiness_verdict": "tampered",
                        "verdict": "tampered",
                        "verification": "tampered",
                    }
                ),
                stderr="",
            )
        return original_run(args, *run_args, **run_kwargs)

    monkeypatch.setattr(experiment.subprocess, "run", fake_run)

    with pytest.raises(experiment.ExperimentBlocked, match="r2|terminal|verification"):
        experiment.validate_implementation_verification_report(report, ROOT)
    assert verifier_calls


def test_contract_uses_separate_state_candidate_channels_and_no_reference_policy():
    contract = experiment.experiment_contract()

    assert contract["algorithm"]["algorithm_version"] == experiment.ALGORITHM_VERSION
    assert contract["algorithm"]["entropy_coefficient"] > 0.0
    assert contract["algorithm"]["gradient_norm_ceiling"] > 0.0
    assert contract["input"]["excluded_runtime_control_fields"] == [
        "follow_up_control"
    ]
    assert contract["environment"] == {
        "ascension": 0,
        "character": "IRONCLAD",
        "max_decisions_per_episode": 500,
        "registered_support_blockers": [
            "unsupported_shop_courier_restock_semantics"
        ],
    }
    assert contract["model"] == {
        "architecture_id": ARCHITECTURE_ID,
        "candidate_input_dim": experiment.HASH_DIM,
        "channel_composition": "separate_state_and_candidate",
        "device": "cpu",
        "dtype": "float32",
        "hidden_dim": experiment.HIDDEN_DIM,
        "state_conditioned": True,
        "state_input_dim": experiment.HASH_DIM,
    }
    serialized = json.dumps(contract, sort_keys=True).casefold()
    assert all(name not in serialized for name in experiment.REFERENCE_POLICY_NAMES)
    assert contract["control"]["policy_quality_baseline"] is False
    assert contract["lifecycle"]["pushed_remote_ref"] == "origin/master"
    assert (
        contract["lifecycle"]["same_identity_checkpoint_resume_authorized"]
        is True
    )
    assert {
        "causal_claim_authorized",
        "communication_mod_authorized",
        "live_execution_authorized",
        "production_checkpoint_mutation_authorized",
    }.issubset(experiment.registration_authority())
    assert set(experiment.registration_authority().values()) == {False}


def test_cli_rejects_remote_ref_override():
    with pytest.raises(SystemExit):
        experiment.build_parser().parse_args(
            [
                "preflight",
                "--registration",
                "registration.json",
                "--authorization",
                "authorization.json",
                "--output",
                "output",
                "--remote-ref",
                "HEAD",
            ]
        )


def test_main_and_terminal_verifier_reject_noncanonical_relative_paths():
    for value in ("reports//registration.json", "reports/registration.json/"):
        with pytest.raises(experiment.ExperimentBlocked, match="canonical"):
            experiment._canonical_relative_path(value, "path")
        with pytest.raises(terminal_verifier.VerificationError, match="canonical"):
            terminal_verifier._canonical_relative_path(value, "path")


def test_terminal_verifier_rejects_episode_above_registered_decision_limit():
    actions = [f"route:map_node:{index}:0" for index in range(501)]
    row = {
        "action_sequence_sha256": hashlib.sha256(
            experiment.canonical_json_bytes(actions)
        ).hexdigest(),
        "candidate_legality": True,
        "categories": ["route"],
        "decisions": len(actions),
        "last_supported_floor": 1.0,
        "outcome": "player_loss",
        "retained": True,
        "seed": 123,
        "selected_action_ids": actions,
        "terminal_floor": 1.0,
        "total_reward": 0.0,
        "unsupported_reason": None,
        "victory": False,
    }

    with pytest.raises(terminal_verifier.VerificationError, match="registered limit"):
        terminal_verifier._validate_episode_row(
            row,
            expected_seed=123,
            expected_chunk=None,
            label="episode",
        )


def test_runtime_initialization_is_deterministic_cpu_only_and_reference_free():
    first = experiment.initialize_training_runtime()
    second = experiment.initialize_training_runtime()

    assert _model_bytes(first.model) == _model_bytes(second.model)
    assert first.model.architecture_metadata()["architecture_id"] == ARCHITECTURE_ID
    assert next(first.model.parameters()).device.type == "cpu"
    assert isinstance(first.optimizer, torch.optim.Adam)
    assert first.optimizer.param_groups[0]["lr"] == experiment.LEARNING_RATE
    assert first.entropy_coefficient == experiment.ENTROPY_COEFFICIENT
    assert first.gradient_norm_ceiling == experiment.GRADIENT_NORM_CEILING
    assert not hasattr(first, "reference_policy")


def test_scoring_preserves_sources_and_records_actual_vs_zero_state_effect():
    environment = OneStepEnvironment(3)
    snapshot = environment.snapshot()
    candidates = environment.legal_actions()
    snapshot_before = copy.deepcopy(snapshot)
    candidates_before = copy.deepcopy(candidates)
    model = experiment.initialize_training_runtime().model
    model_before = _model_bytes(model)

    scored = experiment.score_decision(
        model,
        decision_id="episode-3:decision-0",
        snapshot=snapshot,
        candidates=candidates,
    )

    assert scored["scores"].shape == (2,)
    assert scored["scores"].dtype == torch.float32
    assert torch.isfinite(scored["scores"]).all().item()
    assert scored["diagnostic_row"]["selected_action_id"] in {
        candidate["action_id"] for candidate in candidates
    }
    assert scored["state_effect"]["decision_id"] == "episode-3:decision-0"
    assert math.isfinite(scored["state_effect"]["max_abs_relative_score_change"])
    assert len(scored["state_effect"]["zero_state_scores"]) == len(candidates)
    assert snapshot == snapshot_before
    assert candidates == candidates_before
    assert _model_bytes(model) == model_before


def test_successor_policy_input_excludes_native_follow_up_control():
    environment = OneStepEnvironment(1)
    snapshot = environment.snapshot()
    candidates = environment.legal_actions()
    candidates[0]["raw"]["follow_up_control"] = "baseline"
    candidates[1]["raw"]["follow_up_control"] = "teacher"
    before = copy.deepcopy(candidates)
    model = experiment.initialize_training_runtime().model

    with_control = experiment.score_decision(
        model,
        decision_id="event-control:decision-0",
        snapshot=snapshot,
        candidates=candidates,
    )
    without_control = copy.deepcopy(candidates)
    for candidate in without_control:
        del candidate["raw"]["follow_up_control"]
    excluded = experiment.score_decision(
        model,
        decision_id="event-control:decision-1",
        snapshot=snapshot,
        candidates=without_control,
    )

    assert torch.equal(with_control["scores"], excluded["scores"])
    assert candidates == before


def test_one_training_chunk_is_deterministic_finite_and_entropy_regularized():
    first = experiment.initialize_training_runtime()
    second = experiment.initialize_training_runtime()
    seeds = (10, 11, 12, 13)

    first_summary = experiment.run_training_chunk(
        first,
        environment_factory=_factory,
        seeds=seeds,
        chunk_index=0,
        max_wall_seconds=60.0,
    )
    second_summary = experiment.run_training_chunk(
        second,
        environment_factory=_factory,
        seeds=seeds,
        chunk_index=0,
        max_wall_seconds=60.0,
    )

    assert experiment.canonical_json_bytes(first_summary) == experiment.canonical_json_bytes(
        second_summary
    )
    assert _model_bytes(first.model) == _model_bytes(second.model)
    assert first_summary["episodes"] == 4
    assert first_summary["optimizer_update"] == 1
    assert first_summary["entropy_coefficient"] == experiment.ENTROPY_COEFFICIENT
    assert first_summary["mean_entropy"] > 0.0
    assert first_summary["gradient_norm_before_clip"] >= 0.0
    assert first_summary["gradient_norm_after_clip"] <= (
        experiment.GRADIENT_NORM_CEILING + 1e-6
    )
    assert math.isfinite(first_summary["loss"])
    assert set(first_summary["categories"]) == set(TARGET_CATEGORIES)


def test_adam_contract_binds_every_fixed_hyperparameter():
    algorithm = experiment.experiment_contract()["algorithm"]
    assert {
        "optimizer_amsgrad": algorithm["optimizer_amsgrad"],
        "optimizer_betas": algorithm["optimizer_betas"],
        "optimizer_eps": algorithm["optimizer_eps"],
        "optimizer_weight_decay": algorithm["optimizer_weight_decay"],
    } == {
        "optimizer_amsgrad": False,
        "optimizer_betas": [0.9, 0.999],
        "optimizer_eps": 1e-8,
        "optimizer_weight_decay": 0.0,
    }


@pytest.mark.parametrize(
    ("field", "drifted"),
    [
        ("betas", (0.8, 0.999)),
        ("eps", 1e-7),
        ("weight_decay", 0.01),
        ("amsgrad", True),
    ],
)
def test_runtime_rejects_any_adam_hyperparameter_drift(field, drifted):
    runtime = experiment.initialize_training_runtime()
    runtime.optimizer.param_groups[0][field] = drifted

    with pytest.raises(experiment.ExperimentBlocked, match=f"Adam|optimizer|{field}"):
        experiment._validate_runtime(runtime)


def test_failed_training_chunk_rolls_back_model_optimizer_and_coordinates():
    runtime = experiment.initialize_training_runtime()
    model_before = _model_bytes(runtime.model)
    optimizer_before = experiment.encode_optimizer_state(runtime.optimizer)
    generator_before = runtime.action_generator.get_state().clone()

    with pytest.raises(experiment.ExperimentBlocked, match="finite"):
        experiment.run_training_chunk(
            runtime,
            environment_factory=lambda seed: OneStepEnvironment(seed, nonfinite=True),
            seeds=(1, 2),
            chunk_index=0,
            max_wall_seconds=60.0,
        )

    assert _model_bytes(runtime.model) == model_before
    assert experiment.encode_optimizer_state(runtime.optimizer) == optimizer_before
    assert torch.equal(runtime.action_generator.get_state(), generator_before)
    assert runtime.next_chunk_index == 0
    assert runtime.completed_episodes == 0
    assert runtime.optimizer_updates == 0


def test_post_update_validation_failure_rolls_back_the_complete_chunk(monkeypatch):
    runtime = experiment.initialize_training_runtime()
    model_before = _model_bytes(runtime.model)
    optimizer_before = experiment.encode_optimizer_state(runtime.optimizer)
    generator_before = runtime.action_generator.get_state().clone()
    original = experiment._validate_runtime
    calls = 0

    def fail_after_update(value):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise experiment.ExperimentBlocked("synthetic post-update validation")
        return original(value)

    monkeypatch.setattr(experiment, "_validate_runtime", fail_after_update)

    with pytest.raises(experiment.ExperimentBlocked, match="post-update"):
        experiment.run_training_chunk(
            runtime,
            environment_factory=_factory,
            seeds=(10, 11, 12, 13),
            chunk_index=0,
            max_wall_seconds=60.0,
        )

    assert _model_bytes(runtime.model) == model_before
    assert experiment.encode_optimizer_state(runtime.optimizer) == optimizer_before
    assert torch.equal(runtime.action_generator.get_state(), generator_before)
    assert runtime.next_chunk_index == 0
    assert runtime.completed_episodes == 0
    assert runtime.optimizer_updates == 0


def test_state_effect_summary_is_order_independent_and_category_aware():
    rows = [
        _diagnostic_row("a", "card_reward", selected_kind="take", alternative_kind="skip"),
        _diagnostic_row("b", "shop", selected_kind="buy", alternative_kind="leave"),
        _diagnostic_row(
            "c", "route", selected_kind="choose", alternative_kind="choose"
        ),
        _diagnostic_row(
            "d", "event", selected_kind="choose", alternative_kind="choose"
        ),
    ]

    first = experiment.summarize_experiment_diagnostics(rows)
    second = experiment.summarize_experiment_diagnostics(list(reversed(rows)))

    assert experiment.canonical_json_bytes(first) == experiment.canonical_json_bytes(
        second
    )
    assert first["decision_count"] == 4
    assert first["state_effect"]["multi_candidate_decisions"] == 4
    assert first["state_effect"]["nonzero_effect_decisions"] == 4
    assert first["categories"]["route"]["distinct_candidate_kinds"] == ["choose"]


def test_state_effect_is_summarized_and_gated_for_each_target_category():
    rows = []
    for category in TARGET_CATEGORIES:
        for index in range(4):
            selected, alternative = (
                (("take", "skip") if index % 2 == 0 else ("skip", "take"))
                if category == "card_reward"
                else (("buy", "leave") if index % 2 == 0 else ("leave", "buy"))
                if category == "shop"
                else ("choose", "choose")
            )
            rows.append(
                _diagnostic_row(
                    f"{category}-{index}",
                    category,
                    selected_kind=selected,
                    alternative_kind=alternative,
                )
            )

    diagnostics = experiment.summarize_experiment_diagnostics(rows)

    for category in TARGET_CATEGORIES:
        state_effect = diagnostics["categories"][category]["state_effect"]
        assert state_effect["multi_candidate_decisions"] == 4
        assert state_effect["nonzero_effect_decisions"] == 4
        assert state_effect["relative_order_change_decisions"] == 4
    assert experiment.classify_behavior_gates(
        diagnostics, experiment.default_behavior_gate_contract()
    )["passed"] is True


@pytest.mark.parametrize("category", TARGET_CATEGORIES)
def test_each_category_requires_a_relative_order_change(category):
    rows = []
    for row_category in TARGET_CATEGORIES:
        for index in range(4):
            selected, alternative = (
                (("take", "skip") if index % 2 == 0 else ("skip", "take"))
                if row_category == "card_reward"
                else (("buy", "leave") if index % 2 == 0 else ("leave", "buy"))
                if row_category == "shop"
                else ("choose", "choose")
            )
            rows.append(
                _diagnostic_row(
                    f"{row_category}-{index}",
                    row_category,
                    selected_kind=selected,
                    alternative_kind=alternative,
                    relative_order_changed=row_category != category,
                )
            )

    diagnostics = experiment.summarize_experiment_diagnostics(rows)
    result = experiment.classify_behavior_gates(
        diagnostics, experiment.default_behavior_gate_contract()
    )

    assert result["passed"] is False
    assert f"{category}_state_effect" in result["blockers"]


def test_card_and_shop_saturation_fail_but_single_kind_route_does_not():
    rows = []
    for index in range(4):
        rows.extend(
            [
                _diagnostic_row(
                    f"card-{index}",
                    "card_reward",
                    selected_kind="take",
                    alternative_kind="skip",
                ),
                _diagnostic_row(
                    f"shop-{index}",
                    "shop",
                    selected_kind="buy",
                    alternative_kind="leave",
                ),
            ]
        )
    for category in ("route", "event"):
        rows.extend(
            _diagnostic_row(
                f"{category}-{index}",
                category,
                selected_kind="choose",
                alternative_kind="choose",
            )
            for index in range(4)
        )
    diagnostics = experiment.summarize_experiment_diagnostics(rows)

    result = experiment.classify_behavior_gates(
        diagnostics,
        experiment.default_behavior_gate_contract(),
    )

    assert result["passed"] is False
    assert "card_reward_selected_kind_saturation" in result["blockers"]
    assert "shop_selected_kind_saturation" in result["blockers"]
    assert all(not blocker.startswith("route_selected_kind") for blocker in result["blockers"])
    assert all(not blocker.startswith("event_selected_kind") for blocker in result["blockers"])


def test_card_and_shop_require_minimum_multi_kind_opportunities():
    rows = [
        _diagnostic_row(
            category,
            category,
            selected_kind="a",
            alternative_kind="b" if category in {"card_reward", "shop"} else "a",
        )
        for category in TARGET_CATEGORIES
    ]
    diagnostics = experiment.summarize_experiment_diagnostics(rows)

    result = experiment.classify_behavior_gates(
        diagnostics,
        experiment.default_behavior_gate_contract(),
    )

    assert result["passed"] is False
    assert "card_reward_multi_kind_opportunities" in result["blockers"]
    assert "shop_multi_kind_opportunities" in result["blockers"]


def test_saturation_rates_use_only_decisions_with_multi_kind_opportunities():
    rows = []
    for category, selected, alternative in (
        ("card_reward", "take", "skip"),
        ("shop", "buy", "leave"),
    ):
        for index in range(100):
            rows.append(
                _diagnostic_row(
                    f"{category}-forced-{index}",
                    category,
                    selected_kind=selected,
                    alternative_kind=selected,
                )
            )
        rows.extend(
            [
                _diagnostic_row(
                    f"{category}-choice-selected",
                    category,
                    selected_kind=selected,
                    alternative_kind=alternative,
                ),
                _diagnostic_row(
                    f"{category}-choice-alternative",
                    category,
                    selected_kind=alternative,
                    alternative_kind=selected,
                ),
            ]
        )
    for category in ("route", "event"):
        rows.extend(
            _diagnostic_row(
                f"{category}-{index}",
                category,
                selected_kind="choose",
                alternative_kind="choose",
            )
            for index in range(4)
        )
    diagnostics = experiment.summarize_experiment_diagnostics(rows)

    result = experiment.classify_behavior_gates(
        diagnostics,
        experiment.default_behavior_gate_contract(),
    )

    assert result["passed"] is True
    for category in ("card_reward", "shop"):
        selected = diagnostics["categories"][category]["multi_kind_selected_kinds"]
        assert sorted(row["rate"] for row in selected.values()) == [0.5, 0.5]


def test_zero_state_effect_blocks_canary_even_with_complete_category_coverage():
    rows = [
        _diagnostic_row(
            category,
            category,
            selected_kind="a",
            alternative_kind="b" if category in {"card_reward", "shop"} else "a",
            state_effect=0.0,
        )
        for category in TARGET_CATEGORIES
    ]
    diagnostics = experiment.summarize_experiment_diagnostics(rows)

    result = experiment.classify_behavior_gates(
        diagnostics,
        experiment.default_behavior_gate_contract(),
    )

    assert result["passed"] is False
    assert {
        f"{category}_state_effect" for category in TARGET_CATEGORIES
    }.issubset(result["blockers"])


@pytest.mark.parametrize(
    ("kwargs", "verdict"),
    [
        (
            {
                "complete": True,
                "structural_valid": True,
                "behavior_valid": True,
                "floor_signal": True,
                "initial_victories": 0,
                "trained_victories": 1,
            },
            "experiment_valid_with_victory_signal",
        ),
        (
            {
                "complete": True,
                "structural_valid": True,
                "behavior_valid": True,
                "floor_signal": True,
                "initial_victories": 0,
                "trained_victories": 0,
            },
            "experiment_valid_with_floor_only_signal",
        ),
        (
            {
                "complete": True,
                "structural_valid": True,
                "behavior_valid": False,
                "floor_signal": True,
                "initial_victories": 0,
                "trained_victories": 1,
            },
            "experiment_valid_without_learning_signal",
        ),
        (
            {
                "complete": False,
                "structural_valid": True,
                "behavior_valid": True,
                "floor_signal": True,
                "initial_victories": 0,
                "trained_victories": 1,
                "blocked": True,
            },
            "experiment_blocked",
        ),
        (
            {
                "complete": True,
                "structural_valid": False,
                "behavior_valid": True,
                "floor_signal": True,
                "initial_victories": 0,
                "trained_victories": 1,
            },
            "experiment_invalid",
        ),
    ],
)
def test_terminal_verdict_precedence(kwargs, verdict):
    assert experiment.classify_terminal_verdict(**kwargs)["verdict"] == verdict


def test_fresh_cohort_materialization_is_ascending_disjoint_and_exact():
    inventory = experiment.build_seed_exclusion_inventory(
        {"historical": [0, 2, 4], "reserved": [1, 8]}
    )
    selection = {
        "canary_count": 2,
        "holdout_count": 3,
        "search_start": 0,
        "train_count": 4,
    }

    cohorts = experiment.materialize_fresh_cohorts(inventory, selection)

    assert cohorts == {
        "train": [3, 5, 6, 7],
        "canary": [9, 10],
        "holdout": [11, 12, 13],
    }
    assert experiment.validate_fresh_cohorts(inventory, selection, cohorts) == cohorts
    overlap = copy.deepcopy(cohorts)
    overlap["holdout"][0] = overlap["train"][0]
    with pytest.raises(experiment.ExperimentBlocked, match="overlap|exact"):
        experiment.validate_fresh_cohorts(inventory, selection, overlap)


def test_tracked_seed_inventory_uses_one_fixed_git_tree_and_replays(monkeypatch):
    commit = "c" * 40
    tracked = {
        "reports/a.json": experiment.canonical_json_bytes(
            {"seed": 7, "nested": {"holdout_seeds": [8, 9]}}
        ),
        "reports/historical-registration.json": experiment.canonical_json_bytes(
            {
                "cohorts": {
                    "canary": [12],
                    "holdout": [13],
                    "train": [10, 11],
                },
                "selection": {"search_start": 10, "train_count": 2},
            }
        ),
        "reports/no-seeds.json": experiment.canonical_json_bytes(
            {"value": 10}
        ),
    }
    requested_paths = []

    def fake_git_text(root, *args):
        assert args == (
            "ls-tree",
            "-r",
            "--name-only",
            commit,
            "--",
            "reports",
        )
        return "\n".join(
            [
                "reports/a.json",
                "reports/historical-registration.json",
                "reports/no-seeds.json",
                experiment.DEFAULT_REGISTRATION_PATH,
                f"{experiment.DEFAULT_OUTPUT_DIRECTORY}/metrics.json",
                "reports/not-json.txt",
            ]
        )

    def fake_git_blob_batch(root, *, repository_commit, paths):
        assert repository_commit == commit
        requested_paths.append(list(paths))
        return {path: tracked[path] for path in paths}

    monkeypatch.setattr(experiment, "_git_text", fake_git_text)
    monkeypatch.setattr(experiment, "_git_blob_batch", fake_git_blob_batch)

    inventory = experiment.build_tracked_seed_exclusion_inventory(
        ROOT, repository_commit=commit
    )

    assert requested_paths == [
        [
            "reports/a.json",
            "reports/historical-registration.json",
            "reports/no-seeds.json",
        ]
    ]
    assert inventory["sources"] == {
        "reports/a.json": [7, 8, 9],
        "reports/historical-registration.json": [10, 11, 12, 13],
    }
    assert inventory["excluded_seeds"] == [7, 8, 9, 10, 11, 12, 13]
    assert experiment.verify_tracked_seed_exclusion_inventory(inventory, ROOT) == inventory
    tampered = copy.deepcopy(inventory)
    tampered["excluded_seeds"].append(10)
    tampered["excluded_seed_count"] += 1
    with pytest.raises(experiment.ExperimentBlocked, match="recomputation|counts"):
        experiment.verify_tracked_seed_exclusion_inventory(tampered, ROOT)


def test_process_inventory_includes_javaw_and_slay_the_spire(monkeypatch):
    requested_commands: list[str] = []
    rows = [
        {
            "CommandLine": "javaw.exe -jar ModTheSpire.jar",
            "Name": "javaw.exe",
            "ProcessId": 91001,
        },
        {
            "CommandLine": None,
            "Name": "SlayTheSpire.exe",
            "ProcessId": 91002,
        },
    ]

    def fake_run(args, **kwargs):
        requested_commands.append(str(args[-1]))
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps(rows),
            stderr="",
        )

    monkeypatch.setattr(experiment.subprocess, "run", fake_run)

    found = experiment.find_relevant_processes()

    assert "javaw.exe" in requested_commands[0]
    assert "SlayTheSpire.exe" in requested_commands[0]
    assert {(row["name"], row["process_id"]) for row in found} == {
        ("javaw.exe", 91001),
        ("SlayTheSpire.exe", 91002),
    }


def _registration(
    *, inventory_source: str = "historical"
) -> dict[str, object]:
    inventory = experiment.build_seed_exclusion_inventory(
        {inventory_source: [100, 101]}
    )
    selection = {
        "canary_count": 2,
        "holdout_count": 2,
        "search_start": 100,
        "train_count": 4,
    }
    cohorts = experiment.materialize_fresh_cohorts(inventory, selection)
    inventory_bytes = experiment.canonical_json_bytes(inventory)
    checkpoint_entries = [
        {"path": "fixture.pth", "sha256": "8" * 64, "size_bytes": 321}
    ]
    return experiment.build_source_only_registration(
        identity={
            "adapter_provenance": _provenance(),
            "evidence": {
                "fixture": {
                    "path": "reports/fixture.json",
                    "sha256": "9" * 64,
                    "size_bytes": 123,
                }
            },
            "implementation": {
                "commit": "a" * 40,
                "source_files": list(experiment.IMPLEMENTATION_SOURCE_FILES),
                "source_sha256": "7" * 64,
            },
            "isolation": {
                "communication_mod_config": {
                    "path": "C:/Users/test/CommunicationMod/config.properties",
                    "sha256": "6" * 64,
                    "size_bytes": 123,
                },
                "production_checkpoints": {
                    "entries": checkpoint_entries,
                    "inventory_sha256": hashlib.sha256(
                        experiment.canonical_json_bytes(checkpoint_entries)
                    ).hexdigest(),
                    "root": "D:/game/checkpoints",
                    "total_bytes": 321,
                },
            },
            "logical_execution_id": "state-conditioned-test-r1",
            "native": {
                "dll_directories": ["D:/anaconda/Library/bin"],
                "module": {
                    "path": "D:/native/sts_lightspeed_noncombat_adapter.pyd",
                    "sha256": "3" * 64,
                    "size_bytes": 123,
                },
                "simulator_repo": "D:/CLionProjects/sts_lightspeed",
            },
            "output_directory": "reports/noncombat_state_conditioned_simulator_learning_experiment_test",
            "runtime": {
                "executable": "D:/anaconda/envs/stsai/python.exe",
                "platform": "win32",
                "python_version": "3.10.18",
                "torch_version": "2.5.1",
            },
            "seed_inventory_binding": {
                "path": "reports/noncombat_state_conditioned_test_seed_inventory.json",
                "sha256": hashlib.sha256(inventory_bytes).hexdigest(),
                "size_bytes": len(inventory_bytes),
            },
        },
        inventory=inventory,
        selection=selection,
        cohorts=cohorts,
        limits={
            "bootstrap_resamples": 200,
            "max_checkpoint_count": 2,
            "max_evaluation_episodes": 16,
            "max_episodes": 8,
            "max_total_episodes": 24,
            "max_wall_seconds": 60.0,
            "train_passes": 2,
            "training_chunk_size": 4,
            "unsupported_rate_ceiling": 0.10,
        },
        behavior_gates=experiment.default_behavior_gate_contract(),
    )


def _exact_authorization(
    registration: dict[str, object], repo_root: Path
) -> tuple[dict[str, object], str, str]:
    registration_bytes = experiment.canonical_json_bytes(registration)
    registration_path = (
        "reports/noncombat_state_conditioned_simulator_learning_"
        "experiment_test_registration.json"
    )
    authorization_path = (
        "reports/noncombat_state_conditioned_simulator_learning_"
        "experiment_test_authorization.json"
    )
    authorization = experiment.build_execution_authorization(
        registration_path=registration_path,
        authorization_path=authorization_path,
        registration_bytes=registration_bytes,
        registration_commit="b" * 40,
        logical_execution_id="state-conditioned-test-r1",
        output_directory=registration["identity"]["output_directory"],
        repo_root=repo_root,
    )
    return authorization, registration_path, authorization_path


def _patch_source_only_preflight_dependencies(
    monkeypatch,
    *,
    registration,
    registration_bytes,
    authorization_bytes,
    registration_relative,
    authorization_relative,
    runtime_modules_present=False,
):
    for name in list(sys.modules):
        if name == "torch" or name.startswith("torch."):
            monkeypatch.delitem(sys.modules, name)
        if name == "sts_lightspeed_noncombat_adapter":
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(
        experiment,
        "_git_bytes",
        lambda root, *args: (
            authorization_bytes
            if str(args[-1]).endswith(authorization_relative)
            else registration_bytes
        ),
    )
    provenance = registration["identity"]["adapter_provenance"]

    def fake_git_text(cwd, *args):
        if args == ("status", "--porcelain=v1"):
            return ""
        if args == ("rev-parse", "HEAD"):
            name = Path(cwd).name
            return provenance["submodules"].get(
                name, provenance["simulator_commit"]
            )
        return ""

    monkeypatch.setattr(experiment, "_git_text", fake_git_text)
    monkeypatch.setattr(
        experiment,
        "git_source_hash",
        lambda *args, **kwargs: (
            provenance["adapter_source_sha256"]
            if tuple(kwargs["source_files"]) == experiment.ADAPTER_SOURCE_FILES
            else registration["identity"]["implementation"]["source_sha256"]
        ),
    )
    monkeypatch.setattr(
        experiment,
        "working_source_hash",
        lambda *args, **kwargs: registration["identity"]["implementation"][
            "source_sha256"
        ],
    )
    monkeypatch.setattr(experiment, "_verify_repo_binding", lambda *args: None)
    monkeypatch.setattr(
        experiment, "verify_tracked_seed_exclusion_inventory", lambda *args: None
    )
    monkeypatch.setattr(
        experiment,
        "_installed_torch_version",
        lambda: registration["identity"]["runtime"]["torch_version"],
    )
    monkeypatch.setattr(experiment, "_verify_external_binding", lambda *args: None)
    monkeypatch.setattr(
        experiment,
        "snapshot_production_checkpoints",
        lambda *args: registration["identity"]["isolation"][
            "production_checkpoints"
        ],
    )
    from analysis_scripts import noncombat_simulator_adapter

    monkeypatch.setattr(
        noncombat_simulator_adapter,
        "hash_compiled_simulator_sources",
        lambda *args: (
            provenance["simulator_source_sha256"],
            provenance["simulator_source_file_count"],
        ),
    )
    if runtime_modules_present:
        monkeypatch.setitem(sys.modules, "torch", object())
        monkeypatch.setitem(sys.modules, "sts_lightspeed_noncombat_adapter", object())


def test_authorization_binds_exact_root_command_cohorts_module_and_limits(tmp_path):
    registration = _registration()
    repo_root = (tmp_path / "clean-clone").resolve()
    authorization, registration_path, authorization_path = _exact_authorization(
        registration, repo_root
    )
    registration_bytes = experiment.canonical_json_bytes(registration)
    root = repo_root.as_posix()
    execution = authorization["execution"]
    expected_command = [
        registration["identity"]["runtime"]["executable"],
        f"{root}/analysis_scripts/noncombat_state_conditioned_simulator_learning_experiment.py",
        "execute",
        "--repo-root",
        root,
        "--registration",
        f"{root}/{registration_path}",
        "--authorization",
        f"{root}/{authorization_path}",
        "--output",
        f'{root}/{registration["identity"]["output_directory"]}',
    ]

    assert execution == {
        "authorization_path": authorization_path,
        "cohorts_sha256": hashlib.sha256(
            experiment.canonical_json_bytes(registration["cohorts"])
        ).hexdigest(),
        "command": expected_command,
        "native_module": registration["identity"]["native"]["module"],
        "one_logical_attempt": True,
        "repository_root": root,
        "resource_limits": registration["limits"],
        "same_identity_checkpoint_resume_authorized": True,
    }
    assert experiment.validate_execution_authorization(
        authorization,
        registration=registration,
        registration_bytes=registration_bytes,
    ) == authorization


def test_actual_execution_command_binds_interpreter_source_and_complete_argv(
    monkeypatch,
):
    registration = _registration()
    authorization, _, _ = _exact_authorization(registration, ROOT)
    command = authorization["execution"]["command"]

    assert experiment.validate_actual_execution_command(
        authorization, command
    ) == command
    monkeypatch.setattr(sys, "argv", [command[1], *command[2:]])
    assert experiment.validate_actual_execution_command(
        authorization, experiment.current_process_execution_command()
    ) == command
    monkeypatch.setattr(sys, "argv", ["-c", *command[2:]])
    with pytest.raises(experiment.ExperimentBlocked, match="source|command"):
        experiment.validate_actual_execution_command(
            authorization, experiment.current_process_execution_command()
        )
    for index, replacement in (
        (0, "D:/other/python.exe"),
        (1, f"{ROOT.as_posix()}/analysis_scripts/copied_experiment.py"),
        (4, "D:/other/clone"),
    ):
        tampered = list(command)
        tampered[index] = replacement
        with pytest.raises(experiment.ExperimentBlocked, match="actual|command|source"):
            experiment.validate_actual_execution_command(authorization, tampered)
    with pytest.raises(experiment.ExperimentBlocked, match="shape|flags|command"):
        experiment.validate_actual_execution_command(authorization, command[:-2])


@pytest.mark.parametrize(
    ("field", "drift"),
    [
        ("command", ["D:/anaconda/envs/stsai/python.exe", "tampered.py"]),
        ("cohorts_sha256", "0" * 64),
        ("native_module", {"path": "D:/other/module.pyd", "sha256": "0" * 64, "size_bytes": 1}),
        ("resource_limits", {"max_episodes": 1}),
    ],
)
def test_authorization_rejects_exact_execution_binding_drift(
    tmp_path, field, drift
):
    registration = _registration()
    repo_root = (tmp_path / "clean-clone").resolve()
    authorization, _, _ = _exact_authorization(registration, repo_root)
    authorization["execution"][field] = drift

    with pytest.raises(
        experiment.ExperimentBlocked, match="authorization|execution|binding|limits"
    ):
        experiment.validate_execution_authorization(
            authorization,
            registration=registration,
            registration_bytes=experiment.canonical_json_bytes(registration),
        )


def test_authorization_rejects_replay_from_a_different_clone_root(
    tmp_path, monkeypatch
):
    registration = _registration()
    registered_root = (tmp_path / "registered-clone").resolve()
    replay_root = (tmp_path / "second-clone").resolve()
    authorization, registration_path, authorization_path = _exact_authorization(
        registration, registered_root
    )
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization_bytes = experiment.canonical_json_bytes(authorization)
    for name in list(sys.modules):
        if name == "torch" or name.startswith("torch."):
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(
        experiment,
        "_load_control_files",
        lambda registration_file, authorization_file: (
            registration,
            registration_bytes,
            authorization,
            authorization_bytes,
        ),
    )

    with pytest.raises(experiment.ExperimentBlocked, match="repository|root.*mismatch"):
        experiment.source_only_preflight(
            repo_root=replay_root,
            registration_path=replay_root / registration_path,
            authorization_path=replay_root / authorization_path,
            output_dir=replay_root / registration["identity"]["output_directory"],
            relevant_processes=[],
        )


def test_registration_is_all_false_and_authorization_is_separate_and_exact():
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)

    assert experiment.validate_registration(registration) == registration
    assert set(registration["authority"].values()) == {False}
    assert registration["experiment"] == experiment.experiment_contract()
    authorization = experiment.build_execution_authorization(
        registration_path=(
            "reports/noncombat_state_conditioned_simulator_learning_experiment_test_registration.json"
        ),
        registration_bytes=registration_bytes,
        registration_commit="b" * 40,
        logical_execution_id="state-conditioned-test-r1",
        output_directory=registration["identity"]["output_directory"],
    )
    normalized = experiment.validate_execution_authorization(
        authorization,
        registration=registration,
        registration_bytes=registration_bytes,
    )

    assert normalized == authorization
    assert normalized["authority"]["execution_authorized"] is True
    assert normalized["authority"]["native_loading_authorized"] is True
    for name in experiment.DOWNSTREAM_AUTHORITY_NAMES:
        assert normalized["authority"][name] is False
    tampered = copy.deepcopy(authorization)
    tampered["registration"]["sha256"] = "0" * 64
    with pytest.raises(experiment.ExperimentBlocked, match="registration sha256"):
        experiment.validate_execution_authorization(
            tampered,
            registration=registration,
            registration_bytes=registration_bytes,
        )


def test_registration_freezes_bootstrap_verdict_resource_and_output_terms():
    registration = _registration()

    assert registration["experiment"]["evaluation"] == {
        "bootstrap_confidence": 0.95,
        "bootstrap_seed": 0,
        "greedy_policy": True,
        "replay_episodes_per_seed": 4,
        "update_free": True,
    }
    assert registration["experiment"]["verdicts"] == {
        "blocked": "experiment_blocked",
        "canary_stop": "experiment_stopped_at_canary",
        "invalid": "experiment_invalid",
        "valid_floor_only": "experiment_valid_with_floor_only_signal",
        "valid_victory": "experiment_valid_with_victory_signal",
        "valid_without_learning": "experiment_valid_without_learning_signal",
    }
    assert registration["experiment"]["output"] == {
        "checkpoint_directory": "checkpoints",
        "checkpoint_filename_template": "checkpoint_{index:04d}.json",
        "conditional_terminal_artifacts": {
            "evaluation.json": "present_when_evaluation_evidence_exists",
        },
        "execution_lease": ".execution.lease",
        "manifest": "artifact_manifest.json",
        "required_terminal_artifacts": sorted(
            experiment.FULL_TERMINAL_ARTIFACT_NAMES - {"evaluation.json"}
        ),
    }
    assert registration["limits"]["max_checkpoint_count"] == 2
    assert registration["limits"]["max_evaluation_episodes"] == 16
    assert registration["limits"]["max_total_episodes"] == 24


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("max_checkpoint_count", 3, "checkpoint count"),
        ("max_evaluation_episodes", 15, "evaluation episode count"),
        ("max_total_episodes", 23, "total episode count"),
    ],
)
def test_registration_rejects_derived_resource_limit_drift(field, value, match):
    registration = _registration()
    registration["limits"][field] = value

    with pytest.raises(experiment.ExperimentBlocked, match=match):
        experiment.validate_registration(registration)


def test_registration_rejects_training_chunks_that_cross_pass_boundaries():
    registration = _registration()
    registration["limits"]["training_chunk_size"] = 3

    with pytest.raises(experiment.ExperimentBlocked, match="pass boundary"):
        experiment.validate_registration(registration)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("multi_kind", "maximum_selected_kind_rate"),
        ("state_effect", "minimum_nonzero_effect_rate"),
    ],
)
def test_registration_rejects_string_behavior_rates(section, field):
    registration = _registration()
    registration["behavior_gates"][section][field] = "0.5"

    with pytest.raises(experiment.ExperimentBlocked, match="finite number"):
        experiment.validate_registration(registration)


def test_source_only_control_validation_imports_no_torch_or_native(tmp_path):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization = experiment.build_execution_authorization(
        registration_path="reports/noncombat_state_conditioned_simulator_learning_experiment_test_registration.json",
        registration_bytes=registration_bytes,
        registration_commit="b" * 40,
        logical_execution_id="state-conditioned-test-r1",
        output_directory=registration["identity"]["output_directory"],
    )
    registration_path = tmp_path / "registration.json"
    authorization_path = tmp_path / "authorization.json"
    registration_path.write_bytes(registration_bytes)
    authorization_path.write_bytes(experiment.canonical_json_bytes(authorization))
    probe_code = (
        "import json,sys;"
        "import analysis_scripts.noncombat_state_conditioned_simulator_learning_experiment as e;"
        f"e._load_control_files({str(registration_path)!r},{str(authorization_path)!r});"
        "print(json.dumps({'torch':'torch' in sys.modules,"
        "'native':'sts_lightspeed_noncombat_adapter' in sys.modules},sort_keys=True))"
    )

    completed = subprocess.run(
        [sys.executable, "-c", probe_code],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"native": False, "torch": False}


def test_active_output_read_guard_fails_closed_until_process_exit(tmp_path):
    output = tmp_path / "active"

    with pytest.raises(experiment.ExperimentBlocked, match="active output"):
        experiment.assert_output_read_allowed(output, process_alive=True)
    assert experiment.assert_output_read_allowed(output, process_alive=False) is None


def test_standalone_verifier_rejects_every_output_while_lease_exists(tmp_path):
    output = tmp_path / "active-terminal"
    experiment.publish_terminal_bundle(
        output,
        {"neutral.json": {"purpose": "generic publication test"}},
    )

    with experiment.ExecutionLease.acquire(output, "state-conditioned-test-r1"):
        with pytest.raises(terminal_verifier.VerificationError, match="active|lease"):
            terminal_verifier.verify_output(output)


def test_resume_inventory_rejects_partial_terminal_publication(tmp_path):
    output = tmp_path / "resume"
    checkpoint_dir = output / "checkpoints"
    checkpoint_dir.mkdir(parents=True)
    for name in (
        "authorization.json",
        "configuration.json",
        "execution_journal.json",
        "registration.json",
    ):
        (output / name).write_text("{}\n", encoding="ascii")

    assert experiment.validate_nonterminal_output_inventory(output) == []
    (output / "metrics.json").write_text("{}\n", encoding="ascii")
    with pytest.raises(experiment.ExperimentBlocked, match="partial or extra"):
        experiment.validate_nonterminal_output_inventory(output)


def test_nonterminal_resume_coordinates_allow_only_one_unjournaled_checkpoint(
    tmp_path,
):
    output = tmp_path / "resume-coordinates"
    checkpoint_dir = output / "checkpoints"
    checkpoint_dir.mkdir(parents=True)
    journal = experiment.validate_journal(
        {
            "logical_execution_id": "state-conditioned-test-r1",
            "records": [
                {
                    "checkpoint_index": 0,
                    "completed_episodes": 0,
                    "sequence": 0,
                    "state": "started",
                },
                {
                    "checkpoint_index": 0,
                    "completed_episodes": 0,
                    "operation": "training_chunk:0",
                    "sequence": 1,
                    "state": "operation",
                },
            ],
            "schema_version": experiment.JOURNAL_SCHEMA_VERSION,
            "state": "started",
        },
        logical_execution_id="state-conditioned-test-r1",
    )

    first = {
        "checkpoint_index": 1,
        "runtime": {"completed_episodes": 4, "next_chunk_index": 1},
    }
    first_bytes = experiment.canonical_json_bytes(first)
    (checkpoint_dir / "checkpoint_0001.json").write_bytes(first_bytes)
    state = experiment.validate_nonterminal_resume_coordinates(
        output, journal=journal, checkpoint_names=["checkpoint_0001.json"]
    )
    assert state == {
        "checkpoint_count": 1,
        "journal_checkpoint_count": 0,
        "pending_checkpoint_sha256": hashlib.sha256(first_bytes).hexdigest(),
        "pending_completed_episodes": 4,
        "pending_journal_append": True,
    }

    second = {
        "checkpoint_index": 2,
        "runtime": {"completed_episodes": 8, "next_chunk_index": 2},
    }
    (checkpoint_dir / "checkpoint_0002.json").write_bytes(
        experiment.canonical_json_bytes(second)
    )
    with pytest.raises(experiment.ExperimentBlocked, match="journal/checkpoint gap"):
        experiment.validate_nonterminal_resume_coordinates(
            output,
            journal=journal,
            checkpoint_names=["checkpoint_0001.json", "checkpoint_0002.json"],
        )


def test_nonterminal_resume_rejects_journal_ahead_of_checkpoint_files(tmp_path):
    output = tmp_path / "journal-ahead"
    (output / "checkpoints").mkdir(parents=True)
    journal = experiment.validate_journal(
        {
            "logical_execution_id": "state-conditioned-test-r1",
            "records": [
                {
                    "checkpoint_index": 0,
                    "completed_episodes": 0,
                    "sequence": 0,
                    "state": "started",
                },
                {
                    "checkpoint_index": 1,
                    "checkpoint_sha256": "0" * 64,
                    "completed_episodes": 4,
                    "sequence": 1,
                    "state": "checkpoint",
                },
            ],
            "schema_version": experiment.JOURNAL_SCHEMA_VERSION,
            "state": "started",
        },
        logical_execution_id="state-conditioned-test-r1",
    )

    with pytest.raises(experiment.ExperimentBlocked, match="journal/checkpoint gap"):
        experiment.validate_nonterminal_resume_coordinates(
            output, journal=journal, checkpoint_names=[]
        )


def _registered_resume_fixture(tmp_path):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    runtime = experiment.initialize_training_runtime()
    coordinates = experiment.registered_training_coordinates(registration, 0)
    summary = experiment.run_training_chunk(
        runtime,
        environment_factory=_factory,
        seeds=coordinates["seeds"],
        chunk_index=coordinates["chunk_index"],
        max_wall_seconds=60.0,
    )
    summary.update(
        {
            "episode_end": coordinates["episode_end"],
            "episode_start": coordinates["episode_start"],
            "pass_index": coordinates["pass_index"],
        }
    )
    checkpoint = experiment.build_checkpoint_payload(
        runtime,
        registration_sha256=hashlib.sha256(registration_bytes).hexdigest(),
        implementation_commit=registration["identity"]["implementation"]["commit"],
        logical_execution_id=registration["identity"]["logical_execution_id"],
        previous_checkpoint_bytes=None,
        training_chunk=summary,
    )
    output = tmp_path / "registered-resume"
    checkpoint_path = experiment.publish_checkpoint(output, checkpoint)
    checkpoint_sha256 = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    journal = {
        "logical_execution_id": registration["identity"]["logical_execution_id"],
        "records": [
            {
                "checkpoint_index": 0,
                "completed_episodes": 0,
                "sequence": 0,
                "state": "started",
            },
            {
                "checkpoint_index": 1,
                "checkpoint_sha256": checkpoint_sha256,
                "completed_episodes": coordinates["episode_end"],
                "sequence": 1,
                "state": "checkpoint",
            },
        ],
        "schema_version": experiment.JOURNAL_SCHEMA_VERSION,
        "state": "started",
    }
    return registration, output, checkpoint_path, journal


def test_resume_rejects_checkpoint_episode_end_outside_registration(tmp_path):
    registration, output, checkpoint_path, journal = _registered_resume_fixture(
        tmp_path
    )
    checkpoint = json.loads(checkpoint_path.read_bytes())
    checkpoint["training_chunk"]["episode_end"] += 1
    payload = experiment.canonical_json_bytes(checkpoint)
    checkpoint_path.write_bytes(payload)
    journal["records"][1]["checkpoint_sha256"] = hashlib.sha256(payload).hexdigest()

    with pytest.raises(experiment.ExperimentBlocked, match="registered|episode.*coordinate"):
        experiment.validate_nonterminal_resume_coordinates(
            output,
            journal=journal,
            checkpoint_names=[checkpoint_path.name],
            registration=registration,
        )


def test_resume_rejects_journal_checkpoint_sha_mismatch(tmp_path):
    registration, output, checkpoint_path, journal = _registered_resume_fixture(
        tmp_path
    )
    journal["records"][1]["checkpoint_sha256"] = "0" * 64

    with pytest.raises(
        experiment.ExperimentBlocked,
        match="checkpoint.*sha|hash|journal/checkpoint coordinates differ",
    ):
        experiment.validate_nonterminal_resume_coordinates(
            output,
            journal=journal,
            checkpoint_names=[checkpoint_path.name],
            registration=registration,
        )


@pytest.mark.parametrize("field", ["identity", "previous_checkpoint_sha256"])
def test_resume_rejects_checkpoint_identity_chain_drift(tmp_path, field):
    registration, output, checkpoint_path, journal = _registered_resume_fixture(
        tmp_path
    )
    checkpoint = json.loads(checkpoint_path.read_bytes())
    if field == "identity":
        checkpoint["identity"]["registration_sha256"] = "0" * 64
    else:
        checkpoint["previous_checkpoint_sha256"] = "0" * 64
    payload = experiment.canonical_json_bytes(checkpoint)
    checkpoint_path.write_bytes(payload)
    journal["records"][1]["checkpoint_sha256"] = hashlib.sha256(payload).hexdigest()

    with pytest.raises(
        experiment.ExperimentBlocked, match="identity|predecessor|hash"
    ):
        experiment.validate_nonterminal_resume_coordinates(
            output,
            journal=journal,
            checkpoint_names=[checkpoint_path.name],
            registration=registration,
        )


def test_journal_rejects_noninitial_started_and_checkpoint_coordinate_jumps():
    base = {
        "logical_execution_id": "state-conditioned-test-r1",
        "records": [
            {
                "checkpoint_index": 0,
                "completed_episodes": 0,
                "sequence": 0,
                "state": "started",
            },
            {
                "checkpoint_index": 0,
                "completed_episodes": 0,
                "sequence": 1,
                "state": "started",
            },
        ],
        "schema_version": experiment.JOURNAL_SCHEMA_VERSION,
        "state": "started",
    }
    with pytest.raises(experiment.ExperimentBlocked, match="started record"):
        experiment.validate_journal(
            base, logical_execution_id="state-conditioned-test-r1"
        )

    jumped = copy.deepcopy(base)
    jumped["records"][1] = {
        "checkpoint_index": 2,
        "checkpoint_sha256": "0" * 64,
        "completed_episodes": 8,
        "sequence": 1,
        "state": "checkpoint",
    }
    with pytest.raises(experiment.ExperimentBlocked, match="checkpoint sequence"):
        experiment.validate_journal(
            jumped, logical_execution_id="state-conditioned-test-r1"
        )


def test_execution_lease_blocks_live_owner_and_recovers_unlocked_stale(tmp_path):
    output = tmp_path / "lease"
    output.mkdir()
    path = output / ".execution.lease"

    with experiment.ExecutionLease.acquire(output, "state-conditioned-test-r1"):
        with pytest.raises(experiment.ExperimentBlocked, match="already held"):
            experiment.recover_stale_execution_lease(
                output, "state-conditioned-test-r1"
            )
        assert path.is_file()

    stale = {
        "logical_execution_id": "state-conditioned-test-r1",
        "process_id": 999_999,
        "schema_version": experiment.LEASE_SCHEMA_VERSION,
    }
    path.write_bytes(experiment.canonical_json_bytes(stale))

    assert (
        experiment.recover_stale_execution_lease(
            output, "state-conditioned-test-r1"
        )
        is True
    )
    assert path.exists()

    path.write_bytes(b'{"logical_execution_id":')
    assert (
        experiment.recover_stale_execution_lease(
            output, "state-conditioned-test-r1"
        )
        is True
    )
    assert path.exists()
    with experiment.ExecutionLease.acquire(
        output, "state-conditioned-test-r1"
    ) as owner:
        owner.handle.seek(0)
        lease_payload = json.loads(owner.handle.read())
        assert lease_payload["logical_execution_id"] == "state-conditioned-test-r1"
    assert path.exists()


def test_concurrent_first_lease_creation_never_writes_before_lock(
    tmp_path, monkeypatch
):
    output = tmp_path / "concurrent-lease"
    output.mkdir()
    original_lock = experiment._lock_execution_lease
    call_guard = threading.Lock()
    first_waiting = threading.Event()
    winner_locked = threading.Event()
    owner_ready = threading.Event()
    release_owner = threading.Event()
    call_count = 0
    outcomes = []

    def ordered_lock(handle):
        nonlocal call_count
        with call_guard:
            call_count += 1
            order = call_count
        if order == 1:
            first_waiting.set()
            assert winner_locked.wait(5.0)
            return original_lock(handle)
        original_lock(handle)
        winner_locked.set()

    monkeypatch.setattr(experiment, "_lock_execution_lease", ordered_lock)

    def contender(name):
        try:
            lease = experiment.ExecutionLease.acquire(
                output, "state-conditioned-test-r1"
            )
        except BaseException as exc:
            outcomes.append((name, "blocked", exc))
            return
        outcomes.append((name, "owner", lease))
        owner_ready.set()
        assert release_owner.wait(5.0)
        try:
            lease.release()
        except BaseException as exc:
            outcomes.append((name, "release_failed", exc))

    delayed = threading.Thread(target=contender, args=("delayed",))
    winner = threading.Thread(target=contender, args=("winner",))
    delayed.start()
    assert first_waiting.wait(5.0)
    winner.start()
    assert owner_ready.wait(5.0)
    delayed.join(5.0)
    owners = [row for row in outcomes if row[1] == "owner"]
    blocked = [row for row in outcomes if row[1] == "blocked"]
    assert len(owners) == 1
    assert len(blocked) == 1
    owner = owners[0][2]
    owner.handle.seek(0)
    payload = owner.handle.read()
    assert b"\0" not in payload
    assert json.loads(payload)["logical_execution_id"] == "state-conditioned-test-r1"
    release_owner.set()
    winner.join(5.0)
    assert not delayed.is_alive()
    assert not winner.is_alive()
    assert not [row for row in outcomes if row[1] == "release_failed"]


def test_prestart_initialization_failure_leaves_no_started_output(
    tmp_path, monkeypatch
):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization = experiment.build_execution_authorization(
        registration_path="reports/noncombat_state_conditioned_simulator_learning_experiment_test_registration.json",
        registration_bytes=registration_bytes,
        registration_commit="b" * 40,
        logical_execution_id="state-conditioned-test-r1",
        output_directory=registration["identity"]["output_directory"],
    )
    output = tmp_path / registration["identity"]["output_directory"]
    original = experiment._atomic_write_once

    def fail_configuration(path, payload):
        if path.name == "configuration.json":
            raise OSError("synthetic pre-start failure")
        return original(path, payload)

    monkeypatch.setattr(experiment, "_atomic_write_once", fail_configuration)

    with pytest.raises(OSError, match="synthetic pre-start failure"):
        experiment.initialize_experiment_output(
            output,
            registration_bytes=registration_bytes,
            authorization_bytes=experiment.canonical_json_bytes(authorization),
            repo_root=tmp_path,
        )
    assert not output.exists()


@pytest.mark.parametrize(
    ("interrupt_boundary", "first_missing_stage"),
    [
        ("before_registration", 0),
        ("after_registration", 1),
        ("after_authorization", 2),
        ("after_configuration", 3),
        ("before_journal", 4),
    ],
)
def test_real_prestart_interrupt_recovers_through_preflight_with_lease_held(
    tmp_path, monkeypatch, interrupt_boundary, first_missing_stage
):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization, registration_relative, authorization_relative = _exact_authorization(
        registration, tmp_path
    )
    authorization_bytes = experiment.canonical_json_bytes(authorization)
    registration_path = tmp_path / registration_relative
    authorization_path = tmp_path / authorization_relative
    registration_path.parent.mkdir(parents=True)
    registration_path.write_bytes(registration_bytes)
    authorization_path.write_bytes(authorization_bytes)
    seed_path = (
        tmp_path / registration["identity"]["seed_inventory_binding"]["path"]
    )
    seed_path.write_bytes(
        experiment.canonical_json_bytes(registration["seed_inventory"])
    )
    output = tmp_path / registration["identity"]["output_directory"]
    original_write = experiment._atomic_write_once
    after_target = {
        "after_registration": "registration.json",
        "after_authorization": "authorization.json",
        "after_configuration": "configuration.json",
    }.get(interrupt_boundary)

    def interrupt_initialization(path, payload):
        if (
            interrupt_boundary == "before_registration"
            and path.name == "registration.json"
        ) or (
            interrupt_boundary == "before_journal"
            and path.name == "execution_journal.json"
        ):
            raise KeyboardInterrupt(f"synthetic {interrupt_boundary}")
        result = original_write(path, payload)
        if path.name == after_target:
            raise KeyboardInterrupt(f"synthetic {interrupt_boundary}")
        return result

    monkeypatch.setattr(experiment, "_atomic_write_once", interrupt_initialization)
    with pytest.raises(KeyboardInterrupt, match=interrupt_boundary):
        experiment.initialize_experiment_output(
            output,
            registration_bytes=registration_bytes,
            authorization_bytes=authorization_bytes,
            repo_root=tmp_path,
            acquire_execution_lease=True,
        )
    monkeypatch.setattr(experiment, "_atomic_write_once", original_write)

    state = experiment.validate_abandoned_prestart_output(
        output,
        registration=registration,
        registration_bytes=registration_bytes,
        authorization_bytes=authorization_bytes,
    )
    assert state == {
        "first_missing_stage": first_missing_stage,
        "temporary_artifacts": [],
    }

    _patch_source_only_preflight_dependencies(
        monkeypatch,
        registration=registration,
        registration_bytes=registration_bytes,
        authorization_bytes=authorization_bytes,
        registration_relative=registration_relative,
        authorization_relative=authorization_relative,
    )
    preflight = experiment.source_only_preflight(
        repo_root=tmp_path,
        registration_path=registration_path,
        authorization_path=authorization_path,
        output_dir=output,
        relevant_processes=[],
    )
    assert preflight["output_state"] == "abandoned_prestart"
    monkeypatch.setattr(
        experiment,
        "validate_actual_execution_command",
        lambda value, actual_command: list(actual_command),
    )
    native_observations = []

    def fail_after_started(value):
        journal = json.loads((output / "execution_journal.json").read_bytes())
        with pytest.raises(experiment.ExperimentBlocked, match="already held"):
            experiment.ExecutionLease.acquire(
                output, registration["identity"]["logical_execution_id"]
            )
        native_observations.append((journal["state"], "lease_held"))
        raise experiment.ExperimentBlocked("synthetic native failure")

    monkeypatch.setattr(experiment, "_load_registered_native", fail_after_started)

    with pytest.raises(
        experiment.ExperimentBlocked, match="runtime_initialization_failed"
    ):
        experiment.execute_authorized_experiment(
            repo_root=tmp_path,
            registration_path=tmp_path / registration_relative,
            authorization_path=tmp_path / authorization_relative,
            output_dir=output,
        )

    assert native_observations == [("started", "lease_held")]
    journal = json.loads((output / "execution_journal.json").read_bytes())
    assert journal["state"] == "terminal"
    assert "runtime_initialization_failed" in journal["records"][-1]["reason"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("gap", "prefix"),
        ("temporary_out_of_order", "temporary.*order"),
        ("control_bytes", "bytes mismatch"),
        ("extra_file", "extra file"),
        ("extra_directory", "extra directory"),
        ("nonempty_checkpoints", "checkpoint.*empty"),
    ],
)
def test_abandoned_prestart_rejects_nonprefix_or_unbound_artifacts(
    tmp_path, mutation, message
):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization, _, _ = _exact_authorization(registration, tmp_path)
    authorization_bytes = experiment.canonical_json_bytes(authorization)
    output = tmp_path / mutation
    output.mkdir()
    configuration_bytes = experiment.canonical_json_bytes(
        experiment._initial_configuration(
            registration,
            registration_bytes=registration_bytes,
            authorization_bytes=authorization_bytes,
        )
    )
    if mutation == "gap":
        (output / "authorization.json").write_bytes(authorization_bytes)
    elif mutation == "temporary_out_of_order":
        (output / ".configuration.json.tmp").write_bytes(b"partial")
    elif mutation == "control_bytes":
        (output / "registration.json").write_bytes(b"{}\n")
    elif mutation == "extra_file":
        (output / "unknown.json").write_bytes(b"{}\n")
    elif mutation == "extra_directory":
        (output / "unknown").mkdir()
    else:
        (output / "registration.json").write_bytes(registration_bytes)
        (output / "authorization.json").write_bytes(authorization_bytes)
        (output / "configuration.json").write_bytes(configuration_bytes)
        (output / "checkpoints").mkdir()
        (output / "checkpoints" / "unexpected.json").write_bytes(b"{}\n")

    with pytest.raises(experiment.ExperimentBlocked, match=message):
        experiment.validate_abandoned_prestart_output(
            output,
            registration=registration,
            registration_bytes=registration_bytes,
            authorization_bytes=authorization_bytes,
        )


@pytest.mark.parametrize("operation", ["training_chunk:0", "evaluation:canary"])
def test_started_operation_marker_consumes_resume_instead_of_rerunning(
    tmp_path, operation
):
    output = tmp_path / operation.replace(":", "-")
    (output / "checkpoints").mkdir(parents=True)
    journal = {
        "logical_execution_id": "state-conditioned-test-r1",
        "records": [
            {
                "checkpoint_index": 0,
                "completed_episodes": 0,
                "sequence": 0,
                "state": "started",
            },
            {
                "checkpoint_index": 0,
                "completed_episodes": 0,
                "operation": operation,
                "sequence": 1,
                "state": "operation",
            },
        ],
        "schema_version": experiment.JOURNAL_SCHEMA_VERSION,
        "state": "started",
    }

    with pytest.raises(experiment.ExperimentBlocked, match="operation.*consumed|cannot resume"):
        experiment.validate_nonterminal_resume_coordinates(
            output,
            journal=journal,
            checkpoint_names=[],
            registration=_registration(),
        )


def test_source_only_preflight_terminalizes_a_consumed_started_operation(
    tmp_path, monkeypatch
):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization, registration_relative, authorization_relative = _exact_authorization(
        registration, tmp_path
    )
    authorization_bytes = experiment.canonical_json_bytes(authorization)
    registration_path = tmp_path / registration_relative
    authorization_path = tmp_path / authorization_relative
    registration_path.parent.mkdir(parents=True)
    registration_path.write_bytes(registration_bytes)
    authorization_path.write_bytes(authorization_bytes)
    seed_path = (
        tmp_path / registration["identity"]["seed_inventory_binding"]["path"]
    )
    seed_path.write_bytes(
        experiment.canonical_json_bytes(registration["seed_inventory"])
    )
    output = tmp_path / registration["identity"]["output_directory"]
    experiment.initialize_experiment_output(
        output,
        registration_bytes=registration_bytes,
        authorization_bytes=authorization_bytes,
        repo_root=tmp_path,
    )
    execution_id = registration["identity"]["logical_execution_id"]
    experiment.append_journal_record(
        output,
        logical_execution_id=execution_id,
        state="operation",
        checkpoint_index=0,
        completed_episodes=0,
        operation="training_chunk:0",
    )

    _patch_source_only_preflight_dependencies(
        monkeypatch,
        registration=registration,
        registration_bytes=registration_bytes,
        authorization_bytes=authorization_bytes,
        registration_relative=registration_relative,
        authorization_relative=authorization_relative,
        runtime_modules_present=True,
    )

    with pytest.raises(experiment.ExperimentBlocked, match="terminalized|consumed"):
        experiment.source_only_preflight(
            repo_root=tmp_path,
            registration_path=registration_path,
            authorization_path=authorization_path,
            output_dir=output,
            relevant_processes=[{"name": "SlayTheSpire.exe", "process_id": 123}],
        )

    journal = json.loads((output / "execution_journal.json").read_bytes())
    assert journal["state"] == "terminal"
    assert journal["records"][-1]["reason"].endswith("training_chunk:0")
    verified = terminal_verifier.verify_output(output)
    assert verified["valid"] is False
    assert verified["consumed"] is True


@pytest.mark.parametrize(
    ("failure", "expected_phase"),
    [
        ("checkpoint_restore", "runtime_restore_failed"),
        ("keyboard_interrupt", "KeyboardInterrupt"),
        ("native_loading", "runtime_initialization_failed"),
        ("terminal_publication", "terminal_publication_failed"),
    ],
)
def test_execution_failures_leave_consumed_independently_classifiable_evidence(
    tmp_path, monkeypatch, failure, expected_phase
):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization, registration_relative, authorization_relative = _exact_authorization(
        registration, tmp_path
    )
    authorization_bytes = experiment.canonical_json_bytes(authorization)
    output = tmp_path / registration["identity"]["output_directory"]
    execution_id = registration["identity"]["logical_execution_id"]
    fresh = failure != "checkpoint_restore"
    if not fresh:
        experiment.initialize_experiment_output(
            output,
            registration_bytes=registration_bytes,
            authorization_bytes=authorization_bytes,
            repo_root=tmp_path,
        )

    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda **kwargs: {"output_state": "absent" if fresh else "resume"},
    )
    monkeypatch.setattr(
        experiment,
        "_load_control_files",
        lambda registration_path, authorization_path: (
            registration,
            registration_bytes,
            authorization,
            authorization_bytes,
        ),
    )
    monkeypatch.setattr(
        experiment,
        "_load_registered_native",
        lambda value: (object(), object, {}),
    )
    monkeypatch.setattr(
        experiment,
        "validate_actual_execution_command",
        lambda value, actual_command: list(actual_command),
    )
    if failure == "native_loading":
        monkeypatch.setattr(
            experiment,
            "_load_registered_native",
            lambda value: (_ for _ in ()).throw(
                experiment.ExperimentBlocked("synthetic native loading failure")
            ),
        )
    elif failure == "checkpoint_restore":
        monkeypatch.setattr(
            experiment,
            "_last_durable_runtime",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                experiment.ExperimentBlocked("synthetic restore failure")
            ),
        )
    elif failure == "keyboard_interrupt":
        monkeypatch.setattr(
            experiment,
            "run_training_chunk",
            lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
        )

        def publish_keyboard_terminal(path, *, blocked_reason, **kwargs):
            experiment.consume_started_journal(
                path,
                logical_execution_id=execution_id,
                reason=f"blocked:{blocked_reason}",
            )
            return {"verdict": "experiment_blocked"}

        monkeypatch.setattr(
            experiment, "publish_experiment_terminal", publish_keyboard_terminal
        )
    else:
        monkeypatch.setattr(experiment, "registered_training_chunk_count", lambda value: 0)
        monkeypatch.setattr(
            experiment,
            "run_conditional_evaluation",
            lambda *args, **kwargs: {
                "verdict": "experiment_valid_without_learning_signal"
            },
        )
        monkeypatch.setattr(
            experiment,
            "publish_experiment_terminal",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                OSError("synthetic publication failure")
            ),
        )

    try:
        experiment.execute_authorized_experiment(
            repo_root=tmp_path,
            registration_path=tmp_path / registration_relative,
            authorization_path=tmp_path / authorization_relative,
            output_dir=output,
        )
    except BaseException:
        pass

    journal = json.loads((output / "execution_journal.json").read_bytes())
    assert journal["state"] == "terminal"
    terminal = journal["records"][-1]
    assert terminal["state"] == "terminal"
    assert expected_phase in terminal["reason"]
    verified = terminal_verifier.verify_output(output)
    assert verified["valid"] is False
    assert verified["consumed"] is True
    assert verified["verdict"] == "experiment_invalid"


def test_interrupt_after_durable_checkpoint_journal_preserves_runtime(
    tmp_path, monkeypatch
):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization, registration_relative, authorization_relative = _exact_authorization(
        registration, tmp_path
    )
    authorization_bytes = experiment.canonical_json_bytes(authorization)
    output = tmp_path / registration["identity"]["output_directory"]
    execution_id = registration["identity"]["logical_execution_id"]
    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda **kwargs: {"output_state": "absent"},
    )
    monkeypatch.setattr(
        experiment,
        "_load_control_files",
        lambda *args: (
            registration,
            registration_bytes,
            authorization,
            authorization_bytes,
        ),
    )
    monkeypatch.setattr(
        experiment,
        "validate_actual_execution_command",
        lambda value, actual_command: list(actual_command),
    )
    monkeypatch.setattr(
        experiment,
        "_load_registered_native",
        lambda value: (object(), object, {}),
    )

    def complete_one_chunk(runtime, *, seeds, chunk_index, **kwargs):
        runtime.next_chunk_index += 1
        runtime.completed_episodes += len(seeds)
        runtime.optimizer_updates += 1
        return {
            "chunk_index": chunk_index,
            "diagnostic_rows": [],
            "episode_rows": [],
            "optimizer_update": runtime.optimizer_updates,
        }

    monkeypatch.setattr(experiment, "run_training_chunk", complete_one_chunk)
    original_append = experiment.append_journal_record
    interrupted = False

    def interrupt_after_checkpoint(*args, **kwargs):
        nonlocal interrupted
        result = original_append(*args, **kwargs)
        if kwargs["state"] == "checkpoint" and not interrupted:
            interrupted = True
            raise KeyboardInterrupt("synthetic post-journal interrupt")
        return result

    monkeypatch.setattr(
        experiment, "append_journal_record", interrupt_after_checkpoint
    )
    observed_runtime = []

    def publish_blocked(path, *, runtime, blocked_reason, **kwargs):
        journal = json.loads((output / "execution_journal.json").read_bytes())
        observed_runtime.append(
            (
                runtime.next_chunk_index,
                runtime.completed_episodes,
                journal["records"][-1]["checkpoint_index"],
                journal["records"][-1]["completed_episodes"],
            )
        )
        experiment.consume_started_journal(
            path,
            logical_execution_id=execution_id,
            reason=f"blocked:{blocked_reason}",
        )
        return {"verdict": "experiment_blocked"}

    monkeypatch.setattr(experiment, "publish_experiment_terminal", publish_blocked)

    result = experiment.execute_authorized_experiment(
        repo_root=tmp_path,
        registration_path=tmp_path / registration_relative,
        authorization_path=tmp_path / authorization_relative,
        output_dir=output,
    )

    assert interrupted is True
    assert observed_runtime == [(1, 4, 1, 4)]
    assert result["manifest"]["verdict"] == "experiment_blocked"
    journal = json.loads((output / "execution_journal.json").read_bytes())
    assert journal["state"] == "terminal"
    assert "synthetic post-journal interrupt" in journal["records"][-1]["reason"]


def test_prestart_lease_failure_cleans_output_before_native_loading(
    tmp_path, monkeypatch
):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization, registration_relative, authorization_relative = _exact_authorization(
        registration, tmp_path
    )
    authorization_bytes = experiment.canonical_json_bytes(authorization)
    output = tmp_path / registration["identity"]["output_directory"]
    monkeypatch.setattr(
        experiment,
        "source_only_preflight",
        lambda **kwargs: {"output_state": "absent"},
    )
    monkeypatch.setattr(
        experiment,
        "_load_control_files",
        lambda *args: (
            registration,
            registration_bytes,
            authorization,
            authorization_bytes,
        ),
    )
    monkeypatch.setattr(
        experiment,
        "validate_actual_execution_command",
        lambda value, actual_command: list(actual_command),
    )
    monkeypatch.setattr(
        experiment.ExecutionLease,
        "acquire",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError("synthetic pre-start lease failure")
        ),
    )
    monkeypatch.setattr(
        experiment,
        "_load_registered_native",
        lambda value: (_ for _ in ()).throw(
            AssertionError("native loading must not precede started ownership")
        ),
    )

    with pytest.raises(OSError, match="pre-start lease failure"):
        experiment.execute_authorized_experiment(
            repo_root=tmp_path,
            registration_path=tmp_path / registration_relative,
            authorization_path=tmp_path / authorization_relative,
            output_dir=output,
        )

    assert not output.exists()


def test_failed_lease_cleanup_does_not_consume_a_new_active_owner(
    tmp_path, monkeypatch
):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization, _, _ = _exact_authorization(registration, tmp_path)
    output = tmp_path / registration["identity"]["output_directory"]
    experiment.initialize_experiment_output(
        output,
        registration_bytes=registration_bytes,
        authorization_bytes=experiment.canonical_json_bytes(authorization),
        repo_root=tmp_path,
    )
    execution_id = registration["identity"]["logical_execution_id"]
    original_acquire = experiment.ExecutionLease.acquire
    competing_owner = []

    def owner_appears(path, logical_execution_id):
        competing_owner.append(original_acquire(path, logical_execution_id))
        return False

    monkeypatch.setattr(
        experiment, "recover_stale_execution_lease", owner_appears
    )
    try:
        with pytest.raises(experiment.ExperimentBlocked, match="owner appeared"):
            experiment.consume_after_lease_acquisition_failure(
                output,
                logical_execution_id=execution_id,
                acquisition_error=OSError("synthetic initial acquire failure"),
            )
        journal = json.loads((output / "execution_journal.json").read_bytes())
        assert journal["state"] == "started"
        assert (output / ".execution.lease").is_file()
    finally:
        for lease in competing_owner:
            lease.release()


def test_incomplete_consumed_classifier_rejects_unbound_controls(tmp_path):
    registration = _registration()
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization, _, _ = _exact_authorization(registration, tmp_path)
    output = tmp_path / registration["identity"]["output_directory"]
    experiment.initialize_experiment_output(
        output,
        registration_bytes=registration_bytes,
        authorization_bytes=experiment.canonical_json_bytes(authorization),
        repo_root=tmp_path,
    )
    experiment.consume_started_journal(
        output,
        logical_execution_id=registration["identity"]["logical_execution_id"],
        reason="synthetic_consumed_failure",
    )
    tampered = copy.deepcopy(authorization)
    tampered["registration"]["sha256"] = "0" * 64
    (output / "authorization.json").write_bytes(
        experiment.canonical_json_bytes(tampered)
    )

    with pytest.raises(terminal_verifier.VerificationError, match="binding|sha256"):
        terminal_verifier.verify_output(output)


def test_execute_never_launches_standalone_verifier_in_the_parent_process():
    source = inspect.getsource(experiment.execute_authorized_experiment)

    assert "_verify_terminal_with_fresh_process" not in source
    assert "actual_command" not in inspect.signature(
        experiment.execute_authorized_experiment
    ).parameters


def test_main_rejects_injected_execute_argv(monkeypatch, capsys):
    called = False

    def unexpected_execute(**kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(experiment, "execute_authorized_experiment", unexpected_execute)
    result = experiment.main(
        [
            "execute",
            "--repo-root",
            str(ROOT),
            "--registration",
            "registration.json",
            "--authorization",
            "authorization.json",
            "--output",
            "output",
        ]
    )

    assert result == 1
    assert called is False
    assert "real process argv" in capsys.readouterr().err


def test_terminal_publication_is_canonical_atomic_and_standard_library_verifiable(
    tmp_path,
):
    output = tmp_path / "terminal"
    artifacts = {
        "alpha.json": {"sequence": 1},
        "beta.json": {"sequence": 2},
    }

    manifest = experiment.publish_terminal_bundle(output, artifacts)

    assert manifest["schema_version"] == experiment.MANIFEST_SCHEMA_VERSION
    assert manifest["manifest_kind"] == "generic_bundle"
    assert set(manifest["authority"].values()) == {False}
    assert not list(output.rglob("*.tmp"))
    for path in output.glob("*.json"):
        value = json.loads(path.read_bytes())
        assert path.read_bytes() == experiment.canonical_json_bytes(value)

    command = [
        sys.executable,
        str(
            ROOT
            / "analysis_scripts/verify_noncombat_state_conditioned_simulator_learning_experiment.py"
        ),
        "--output",
        str(output),
        "--allow-generic-bundle",
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
    assert completed.returncode == 2, completed.stderr
    result = json.loads(completed.stdout)
    assert result["valid"] is False
    assert result["bundle_valid"] is True
    assert result["qualification_eligible"] is False
    assert result["verification_scope"] == "generic_bundle_only"
    assert result["artifact_count"] == len(artifacts)
    with pytest.raises(terminal_verifier.VerificationError, match="full terminal"):
        terminal_verifier.verify_output(output)


def test_generic_terminal_cannot_downgrade_full_terminal_artifacts(tmp_path):
    with pytest.raises(experiment.ExperimentBlocked, match="full-terminal"):
        experiment.publish_terminal_bundle(
            tmp_path / "publisher-rejects",
            {"Metrics.json": {"verdict": "experiment_invalid"}},
        )

    output = tmp_path / "verifier-rejects"
    output.mkdir()
    payload = experiment.canonical_json_bytes(
        {"verdict": "experiment_valid_with_victory_signal"}
    )
    (output / "Metrics.json").write_bytes(payload)
    manifest = {
        "artifact_count": 1,
        "artifacts": [
            {
                "path": "Metrics.json",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        ],
        "authority": experiment.registration_authority(),
        "manifest_kind": "generic_bundle",
        "schema_version": experiment.MANIFEST_SCHEMA_VERSION,
    }
    (output / "artifact_manifest.json").write_bytes(
        experiment.canonical_json_bytes(manifest)
    )

    with pytest.raises(terminal_verifier.VerificationError, match="artifact path"):
        terminal_verifier.verify_output(output, allow_generic_bundle=True)


def test_standalone_verifier_rechecks_lease_before_return(tmp_path, monkeypatch):
    output = tmp_path / "lease-race"
    experiment.publish_terminal_bundle(
        output, {"neutral.json": {"purpose": "lease race"}}
    )
    original = terminal_verifier._verify_manifest
    owners = []

    def race(directory, manifest):
        result = original(directory, manifest)
        owners.append(
            experiment.ExecutionLease.acquire(
                directory, "state-conditioned-test-r1"
            )
        )
        return result

    monkeypatch.setattr(terminal_verifier, "_verify_manifest", race)

    try:
        with pytest.raises(terminal_verifier.VerificationError, match="active|lease"):
            terminal_verifier.verify_output(output, allow_generic_bundle=True)
    finally:
        for owner in owners:
            owner.release()


def test_standalone_verifier_rejects_transient_execution_output_change(
    tmp_path, monkeypatch
):
    output = tmp_path / "transient-lease-race"
    experiment.publish_terminal_bundle(
        output, {"neutral.json": {"purpose": "transient lease race"}}
    )
    original = terminal_verifier._verify_manifest

    def race(directory, manifest):
        result = original(directory, manifest)
        with experiment.ExecutionLease.acquire(
            directory, "state-conditioned-test-r1"
        ):
            pass
        (directory / "late.json").write_bytes(b"{}\n")
        return result

    monkeypatch.setattr(terminal_verifier, "_verify_manifest", race)

    with pytest.raises(terminal_verifier.VerificationError, match="changed"):
        terminal_verifier.verify_output(output, allow_generic_bundle=True)


def test_full_lifecycle_terminal_is_independently_verifiable(tmp_path):
    registration = _registration()
    communication_mod_config = tmp_path / "CommunicationMod-config.properties"
    communication_mod_bytes = b"command=synthetic\n"
    communication_mod_config.write_bytes(communication_mod_bytes)
    production_checkpoint_root = tmp_path / "production-checkpoints"
    production_checkpoint_root.mkdir()
    production_checkpoint = production_checkpoint_root / "fixture.pth"
    production_checkpoint_bytes = b"synthetic production checkpoint"
    production_checkpoint.write_bytes(production_checkpoint_bytes)
    registration["identity"]["isolation"] = {
        "communication_mod_config": experiment.external_file_binding(
            communication_mod_config
        ),
        "production_checkpoints": experiment.snapshot_production_checkpoints(
            production_checkpoint_root
        ),
    }
    registration_bytes = experiment.canonical_json_bytes(registration)
    authorization = experiment.build_execution_authorization(
        registration_path="reports/noncombat_state_conditioned_simulator_learning_experiment_test_registration.json",
        registration_bytes=registration_bytes,
        registration_commit="b" * 40,
        logical_execution_id="state-conditioned-test-r1",
        output_directory=registration["identity"]["output_directory"],
        repo_root=tmp_path,
    )
    authorization_bytes = experiment.canonical_json_bytes(authorization)
    output = tmp_path / registration["identity"]["output_directory"]
    journal = experiment.initialize_experiment_output(
        output,
        registration_bytes=registration_bytes,
        authorization_bytes=authorization_bytes,
        repo_root=tmp_path,
    )

    assert journal["state"] == "started"
    registration_sha256 = hashlib.sha256(registration_bytes).hexdigest()
    runtime = experiment.initialize_training_runtime()
    with experiment.ExecutionLease.acquire(
        output, registration["identity"]["logical_execution_id"]
    ):
        with pytest.raises(experiment.ExperimentBlocked, match="already held"):
            experiment.ExecutionLease.acquire(
                output, registration["identity"]["logical_execution_id"]
            )
        previous_checkpoint_bytes = None
        for chunk_index in range(
            experiment.registered_training_chunk_count(registration)
        ):
            coordinates = experiment.registered_training_coordinates(
                registration, chunk_index
            )
            experiment.append_journal_record(
                output,
                logical_execution_id=registration["identity"]["logical_execution_id"],
                state="operation",
                checkpoint_index=runtime.next_chunk_index,
                completed_episodes=runtime.completed_episodes,
                operation=f"training_chunk:{runtime.next_chunk_index}",
            )
            chunk = experiment.run_training_chunk(
                runtime,
                environment_factory=_factory,
                seeds=coordinates["seeds"],
                chunk_index=coordinates["chunk_index"],
                max_wall_seconds=60.0,
            )
            chunk.update(
                {
                    "episode_end": coordinates["episode_end"],
                    "episode_start": coordinates["episode_start"],
                    "pass_index": coordinates["pass_index"],
                }
            )
            checkpoint = experiment.build_checkpoint_payload(
                runtime,
                registration_sha256=registration_sha256,
                implementation_commit=registration["identity"]["implementation"]["commit"],
                logical_execution_id=registration["identity"]["logical_execution_id"],
                previous_checkpoint_bytes=previous_checkpoint_bytes,
                training_chunk=chunk,
            )
            checkpoint_path = experiment.publish_checkpoint(output, checkpoint)
            previous_checkpoint_bytes = checkpoint_path.read_bytes()
            experiment.append_journal_record(
                output,
                logical_execution_id=registration["identity"]["logical_execution_id"],
                state="checkpoint",
                checkpoint_index=runtime.next_chunk_index,
                completed_episodes=runtime.completed_episodes,
            )
        experiment.append_journal_record(
            output,
            logical_execution_id=registration["identity"]["logical_execution_id"],
            state="operation",
            checkpoint_index=runtime.next_chunk_index,
            completed_episodes=runtime.completed_episodes,
            operation="evaluation:canary",
        )

        def preserve_canary(result):
            experiment.append_journal_record(
                output,
                logical_execution_id=registration["identity"]["logical_execution_id"],
                state="evidence",
                checkpoint_index=runtime.next_chunk_index,
                completed_episodes=runtime.completed_episodes,
                evidence_name="canary_evaluation",
                evidence=result,
            )

        evaluation = experiment.run_conditional_evaluation(
            experiment.initialize_training_runtime().model,
            runtime.model,
            environment_factory=_factory,
            canary_seeds=registration["cohorts"]["canary"],
            holdout_seeds=registration["cohorts"]["holdout"],
            gate_contract=registration["behavior_gates"],
            unsupported_rate_ceiling=registration["limits"][
                "unsupported_rate_ceiling"
            ],
            bootstrap_resamples=registration["limits"]["bootstrap_resamples"],
            on_canary_complete=preserve_canary,
        )
        assert evaluation["verdict"] == "experiment_stopped_at_canary"
        assert evaluation["holdout"] == {"accessed": False, "episode_count": 0}
        manifest = experiment.publish_experiment_terminal(
            output,
            runtime=runtime,
            evaluation=evaluation,
            isolation_post=registration["identity"]["isolation"],
        )
        assert manifest["manifest_kind"] == "full_terminal"
        assert (output / ".execution.lease").is_file()
        assert all(
            row["path"] != ".execution.lease" for row in manifest["artifacts"]
        )

    assert (output / ".execution.lease").is_file()
    completed = subprocess.run(
        [
            sys.executable,
            str(
                ROOT
                / "analysis_scripts/verify_noncombat_state_conditioned_simulator_learning_experiment.py"
            ),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["valid"] is True
    assert result["checkpoint_count"] == 2
    assert result["completed_training_episodes"] == 8
    assert result["verdict"] == "experiment_stopped_at_canary"

    communication_mod_config.write_bytes(b"command=drifted\n")
    config_rejected = subprocess.run(
        completed.args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert config_rejected.returncode == 1
    assert "CommunicationMod" in config_rejected.stderr
    communication_mod_config.write_bytes(communication_mod_bytes)

    production_checkpoint.write_bytes(b"drifted production checkpoint")
    checkpoint_rejected = subprocess.run(
        completed.args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert checkpoint_rejected.returncode == 1
    assert "checkpoint inventory drifted" in checkpoint_rejected.stderr
    production_checkpoint.write_bytes(production_checkpoint_bytes)

    probe_code = (
        "import importlib.util,json,sys;"
        f"p={str(ROOT / 'analysis_scripts/verify_noncombat_state_conditioned_simulator_learning_experiment.py')!r};"
        "s=importlib.util.spec_from_file_location('terminal_verifier_probe',p);"
        "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        f"r=m.verify_output({str(output)!r});"
        "r['torch_imported']='torch' in sys.modules;"
        "r['native_imported']='sts_lightspeed_noncombat_adapter' in sys.modules;"
        "print(json.dumps(r,sort_keys=True))"
    )
    probe = subprocess.run(
        [sys.executable, "-c", probe_code],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stderr
    probe_result = json.loads(probe.stdout)
    assert probe_result["torch_imported"] is False
    assert probe_result["native_imported"] is False

    first_path = output / "checkpoints/checkpoint_0001.json"
    second_path = output / "checkpoints/checkpoint_0002.json"
    first = json.loads(first_path.read_bytes())
    first["training_chunk"]["episode_rows"][0]["seed"] += 1
    first_bytes = experiment.canonical_json_bytes(first)
    first_path.write_bytes(first_bytes)
    second = json.loads(second_path.read_bytes())
    second["previous_checkpoint_sha256"] = hashlib.sha256(first_bytes).hexdigest()
    second_bytes = experiment.canonical_json_bytes(second)
    second_path.write_bytes(second_bytes)
    training_path = output / "training_rows.json"
    training = json.loads(training_path.read_bytes())
    training["chunks"][0] = first["training_chunk"]
    training["chunks"][1] = second["training_chunk"]
    training_path.write_bytes(experiment.canonical_json_bytes(training))
    manifest_path = output / "artifact_manifest.json"
    tampered_manifest = json.loads(manifest_path.read_bytes())
    for binding in tampered_manifest["artifacts"]:
        payload = (output / binding["path"]).read_bytes()
        binding["sha256"] = hashlib.sha256(payload).hexdigest()
        binding["size_bytes"] = len(payload)
    manifest_path.write_bytes(experiment.canonical_json_bytes(tampered_manifest))
    rejected = subprocess.run(
        completed.args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode == 1
    assert "seed coordinate mismatch" in rejected.stderr


def test_reference_policy_fields_are_rejected_recursively():
    registration = _registration()
    registration["identity"]["bottled_policy"] = "forbidden"

    with pytest.raises(experiment.ExperimentBlocked, match="reference policy"):
        experiment.validate_registration(registration)
    with pytest.raises(terminal_verifier.VerificationError, match="reference policy"):
        terminal_verifier._reject_reference_policy_leakage(registration)


def test_historical_seed_source_paths_do_not_trigger_policy_leakage():
    registration = _registration(
        inventory_source=(
            "reports/known_propensity_exploration_eval_20260714_b1_config.json"
        )
    )

    assert experiment.validate_registration(registration) == registration
    assert terminal_verifier._reject_reference_policy_leakage(registration) is None


def test_checkpoint_round_trip_restores_exact_runtime_and_hash_chain(tmp_path):
    runtime = experiment.initialize_training_runtime()
    experiment.run_training_chunk(
        runtime,
        environment_factory=_factory,
        seeds=(20, 21, 22, 23),
        chunk_index=0,
        max_wall_seconds=60.0,
    )
    model_before = _model_bytes(runtime.model)
    optimizer_before = experiment.encode_optimizer_state(runtime.optimizer)
    generator_before = runtime.action_generator.get_state().clone()
    first = experiment.build_checkpoint_payload(
        runtime,
        registration_sha256="1" * 64,
        implementation_commit="2" * 40,
        logical_execution_id="state-conditioned-test-r1",
        previous_checkpoint_bytes=None,
    )
    first_path = experiment.publish_checkpoint(tmp_path, first)
    first_bytes = first_path.read_bytes()
    restored = experiment.restore_training_runtime_from_checkpoint(
        first,
        registration_sha256="1" * 64,
        implementation_commit="2" * 40,
        logical_execution_id="state-conditioned-test-r1",
    )

    assert _model_bytes(restored.model) == model_before
    assert experiment.encode_optimizer_state(restored.optimizer) == optimizer_before
    assert torch.equal(restored.action_generator.get_state(), generator_before)
    assert restored.next_chunk_index == 1
    assert restored.completed_episodes == 4
    assert restored.optimizer_updates == 1

    experiment.run_training_chunk(
        restored,
        environment_factory=_factory,
        seeds=(24, 25, 26, 27),
        chunk_index=1,
        max_wall_seconds=60.0,
    )
    second = experiment.build_checkpoint_payload(
        restored,
        registration_sha256="1" * 64,
        implementation_commit="2" * 40,
        logical_execution_id="state-conditioned-test-r1",
        previous_checkpoint_bytes=first_bytes,
    )
    experiment.publish_checkpoint(tmp_path, second)
    chain = experiment.validate_checkpoint_chain(
        tmp_path,
        registration_sha256="1" * 64,
        implementation_commit="2" * 40,
        logical_execution_id="state-conditioned-test-r1",
    )
    assert [row["checkpoint_index"] for row in chain] == [1, 2]


def test_frozen_paired_evaluation_is_replay_exact_and_non_updating():
    initial = experiment.initialize_training_runtime().model
    trained = experiment.initialize_training_runtime().model
    initial_before = _model_bytes(initial)
    trained_before = _model_bytes(trained)

    first = experiment.paired_policy_evaluation(
        initial,
        trained,
        environment_factory=_factory,
        seeds=(30, 31, 32, 33),
        cohort="canary",
        bootstrap_resamples=200,
    )
    second = experiment.paired_policy_evaluation(
        initial,
        trained,
        environment_factory=_factory,
        seeds=(30, 31, 32, 33),
        cohort="canary",
        bootstrap_resamples=200,
    )

    assert experiment.canonical_json_bytes(first) == experiment.canonical_json_bytes(
        second
    )
    assert len(first["paired_rows"]) == 4
    assert first["initial"]["replay_exact"] is True
    assert first["trained"]["replay_exact"] is True
    assert first["initial"]["replay_episode_rows"] == first["initial"]["episode_rows"]
    assert first["initial"]["replay_diagnostic_rows"] == first["initial"]["diagnostic_rows"]
    assert set(first["initial"]["categories"]) == set(TARGET_CATEGORIES)
    assert _model_bytes(initial) == initial_before
    assert _model_bytes(trained) == trained_before


def test_rollout_checks_deadline_before_constructing_environment():
    touched: list[int] = []

    def factory(seed: int):
        touched.append(seed)
        return OneStepEnvironment(seed)

    with pytest.raises(experiment.ExperimentBlocked, match="wall-time"):
        experiment.rollout_episode(
            experiment.initialize_training_runtime().model,
            environment_factory=factory,
            seed=39,
            training=False,
            action_generator=None,
            deadline=10.0,
            clock=lambda: 10.1,
        )

    assert touched == []


def test_canary_failure_keeps_holdout_factory_unaccessed():
    initial = experiment.initialize_training_runtime().model
    trained = experiment.initialize_training_runtime().model
    touched: list[int] = []

    def factory(seed: int):
        touched.append(seed)
        return OneStepEnvironment(seed)

    result = experiment.run_conditional_evaluation(
        initial,
        trained,
        environment_factory=factory,
        canary_seeds=(40, 41, 42, 43),
        holdout_seeds=(50, 51, 52, 53),
        gate_contract=experiment.default_behavior_gate_contract(),
        unsupported_rate_ceiling=0.10,
        bootstrap_resamples=200,
    )

    assert result["canary_gate"]["passed"] is False
    assert result["holdout"] == {"accessed": False, "episode_count": 0}
    assert not set(touched).intersection({50, 51, 52, 53})


def test_canary_success_accesses_only_the_registered_holdout(monkeypatch):
    calls: list[tuple[str, tuple[int, ...]]] = []

    def fake_paired(
        initial_model,
        trained_model,
        *,
        environment_factory,
        seeds,
        cohort,
        bootstrap_resamples,
        bootstrap_seed,
        deadline,
        clock,
    ):
        seed_values = tuple(seeds)
        calls.append((cohort, seed_values))
        policy = {
            "categories": list(TARGET_CATEGORIES),
            "diagnostics": {},
            "replay_exact": True,
            "victories": 0,
        }
        return {
            "cohort": cohort,
            "floor_difference_ci": {"lower": 1.0},
            "initial": copy.deepcopy(policy),
            "schema_version": experiment.EVALUATION_SCHEMA_VERSION,
            "trained": copy.deepcopy(policy),
            "unsupported_rate": 0.0,
        }

    monkeypatch.setattr(experiment, "paired_policy_evaluation", fake_paired)
    monkeypatch.setattr(
        experiment,
        "classify_behavior_gates",
        lambda diagnostics, contract: {
            "blockers": [],
            "passed": True,
            "schema_version": "noncombat-state-conditioned-behavior-gate-v1",
        },
    )

    result = experiment.run_conditional_evaluation(
        object(),
        object(),
        environment_factory=lambda seed: None,
        canary_seeds=(60, 61),
        holdout_seeds=(70, 71, 72),
        gate_contract=experiment.default_behavior_gate_contract(),
        unsupported_rate_ceiling=0.10,
        bootstrap_resamples=200,
    )

    assert calls == [("canary", (60, 61)), ("holdout", (70, 71, 72))]
    assert result["canary_gate"]["passed"] is True
    assert result["holdout"]["accessed"] is True
    assert result["holdout"]["episode_count"] == 12
    assert result["verdict"] == "experiment_valid_with_floor_only_signal"


def test_deadline_exhausted_after_passing_canary_never_enters_holdout(monkeypatch):
    holdout_touched: list[int] = []

    def fake_paired(
        initial_model,
        trained_model,
        *,
        environment_factory,
        seeds,
        cohort,
        bootstrap_resamples,
        bootstrap_seed,
        deadline,
        clock,
    ):
        if cohort == "holdout":
            for seed in seeds:
                environment_factory(seed)
            pytest.fail("holdout evaluation began after the deadline")
        policy = {
            "categories": list(TARGET_CATEGORIES),
            "diagnostics": {},
            "replay_exact": True,
            "victories": 0,
        }
        return {
            "cohort": "canary",
            "floor_difference_ci": {"lower": 1.0},
            "initial": copy.deepcopy(policy),
            "schema_version": experiment.EVALUATION_SCHEMA_VERSION,
            "trained": copy.deepcopy(policy),
            "unsupported_rate": 0.0,
        }

    monkeypatch.setattr(experiment, "paired_policy_evaluation", fake_paired)
    monkeypatch.setattr(
        experiment,
        "classify_behavior_gates",
        lambda diagnostics, contract: {
            "blockers": [],
            "passed": True,
            "schema_version": "noncombat-state-conditioned-behavior-gate-v1",
        },
    )

    with pytest.raises(experiment.ExperimentBlocked, match="wall-time"):
        experiment.run_conditional_evaluation(
            object(),
            object(),
            environment_factory=lambda seed: holdout_touched.append(seed),
            canary_seeds=(60, 61),
            holdout_seeds=(70, 71),
            gate_contract=experiment.default_behavior_gate_contract(),
            unsupported_rate_ceiling=0.10,
            bootstrap_resamples=200,
            deadline=10.0,
            clock=lambda: 10.1,
        )

    assert holdout_touched == []


def test_completed_canary_evidence_is_durable_before_holdout_failure(monkeypatch):
    preserved: list[dict[str, object]] = []

    def fake_paired(
        initial_model,
        trained_model,
        *,
        environment_factory,
        seeds,
        cohort,
        bootstrap_resamples,
        bootstrap_seed,
        deadline,
        clock,
    ):
        if cohort == "holdout":
            raise experiment.ExperimentBlocked("synthetic holdout failure")
        policy = {
            "categories": list(TARGET_CATEGORIES),
            "diagnostics": {},
            "replay_exact": True,
            "victories": 0,
        }
        return {
            "cohort": "canary",
            "floor_difference_ci": {"lower": 1.0},
            "initial": copy.deepcopy(policy),
            "schema_version": experiment.EVALUATION_SCHEMA_VERSION,
            "trained": copy.deepcopy(policy),
            "unsupported_rate": 0.0,
        }

    monkeypatch.setattr(experiment, "paired_policy_evaluation", fake_paired)
    monkeypatch.setattr(
        experiment,
        "classify_behavior_gates",
        lambda diagnostics, contract: {
            "blockers": [],
            "passed": True,
            "schema_version": "noncombat-state-conditioned-behavior-gate-v1",
        },
    )

    with pytest.raises(experiment.ExperimentBlocked, match="holdout failure"):
        experiment.run_conditional_evaluation(
            object(),
            object(),
            environment_factory=lambda seed: None,
            canary_seeds=(80, 81),
            holdout_seeds=(90, 91),
            gate_contract=experiment.default_behavior_gate_contract(),
            unsupported_rate_ceiling=0.10,
            bootstrap_resamples=200,
            deadline=100.0,
            clock=lambda: 0.0,
            on_canary_complete=lambda result: preserved.append(copy.deepcopy(result)),
        )

    assert len(preserved) == 1
    assert preserved[0]["canary"]["cohort"] == "canary"
    assert preserved[0]["canary_gate"]["passed"] is True
    assert preserved[0]["holdout"] == {"accessed": False, "episode_count": 0}
