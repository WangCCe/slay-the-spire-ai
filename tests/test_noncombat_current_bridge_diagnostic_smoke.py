from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

import analysis_scripts.noncombat_current_bridge_diagnostic_smoke as smoke


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_CANDIDATE_KEYS = {
    "action_id",
    "available",
    "category",
    "kind",
    "label",
    "raw",
}


def _canonical_bytes(value):
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _binding(path, *, display_path=None):
    payload = path.read_bytes() if path.is_file() else b"fixture"
    return {
        "path": display_path or str(path.resolve()),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _provenance():
    contract = smoke.reachable_event_option_semantics_identity()
    return {
        "adapter_commit": smoke.EXPECTED_ADAPTER_COMMIT,
        "adapter_source_sha256": "a" * 64,
        "build": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "baseline_policy_id": "sts_lightspeed_simple_agent_no_potions_v1",
            "compiler": "15.2.0",
            "cpp_standard": 201703,
            "native_target_policy_id": "sts_lightspeed_simple_agent_target_v1",
            "pybind11_version": "3.0.2a0",
            "python": "3.10.18",
        },
        "module_sha256": smoke.EXPECTED_MODULE_SHA256,
        "module_size_bytes": smoke.EXPECTED_MODULE_SIZE_BYTES,
        "simulator_commit": contract["simulator_commit"],
        "simulator_dirty": True,
        "simulator_source_file_count": 79,
        "simulator_source_sha256": contract["simulator_source_sha256"],
        "submodules": {"json": "d" * 40, "pybind11": "e" * 40},
    }


def _identity(tmp_path, *, profile=None):
    profile = smoke.V1_PROFILE if profile is None else profile
    metadata = tmp_path / "items.json"
    metadata.write_text("{}\n", encoding="utf-8")
    module = tmp_path / "adapter.pyd"
    module.write_bytes(b"fixture")
    contract = smoke.reachable_event_option_semantics_identity()
    contract_path = contract["observation_contract"]["path"]
    return {
        "adapter_provenance": _provenance(),
        "adapter_source_files": list(smoke.ADAPTER_SOURCE_FILES),
        "contract": contract,
        "contract_file": {
            "path": contract_path,
            "sha256": contract["observation_contract"]["sha256"],
            "size_bytes": 1,
        },
        "implementation": {
            "commit": "f" * 40,
            "source_files": list(profile.implementation_source_files),
            "source_sha256": "1" * 64,
        },
        "metadata": _binding(metadata),
        "module_path": str(module.resolve()),
        "preimplementation": {
            "path": profile.preimplementation_path,
            "sha256": profile.preimplementation_sha256,
            "size_bytes": profile.preimplementation_size_bytes,
        },
        "runtime": {
            "executable": str((tmp_path / "python.exe").resolve()),
            "python": "3.10.18",
        },
        "simulator_path": str(tmp_path.resolve()),
    }


def _registration(tmp_path, *, profile=None):
    profile = smoke.V1_PROFILE if profile is None else profile
    return smoke.build_registration(
        identity=_identity(tmp_path, profile=profile), profile=profile
    )


class FakeEnvironment:
    def __init__(
        self,
        seed,
        categories,
        *,
        blocker=None,
        step_blocker=None,
        terminal_seed=None,
    ):
        self.seed = seed
        self.categories = list(categories)
        self.blocker = blocker
        self.step_blocker = step_blocker
        self.terminal_seed = terminal_seed
        self.index = 0

    def snapshot(self):
        if self.index >= len(self.categories):
            if self.blocker is not None:
                raise RuntimeError(self.blocker)
            return {
                "state": {
                    "floor": 2,
                    "outcome": "player_loss",
                    "seed": str(
                        self.seed if self.terminal_seed is None else self.terminal_seed
                    ),
                },
                "terminal": True,
            }
        category = self.categories[self.index]
        context = {}
        if category == "event":
            context = {"event_data": 0, "event_id": "The Cleric"}
        return {
            "category": category,
            "decision_count": self.index,
            "state": {
                "decision_context": context,
                "floor": 1,
                "seed": str(self.seed),
            },
            "terminal": False,
        }

    def legal_actions(self):
        category = self.categories[self.index]
        candidate = {
            "action_id": f"{category}:fixture:0",
            "available": True,
            "category": category,
            "kind": "event_option" if category == "event" else "test_action",
            "label": f"{category} fixture",
            "raw": {},
        }
        if category == "event":
            candidate["raw"] = {"idx1": 0}
        return [candidate]

    def step(self, action_id):
        self.index += 1
        if self.step_blocker is not None:
            raise RuntimeError(self.step_blocker)
        return {"selected_action_id": action_id}


class FakeSession:
    def evaluate(self, *, snapshot, candidates, decision_index):
        candidate = candidates[0]
        category = snapshot["category"]
        result = {
            "action_id": candidate["action_id"],
            "action_type": "ChooseAction",
            "category": category,
            "fallback_used": False,
            "input_candidates_sha256": smoke.sha256_bytes(
                smoke.canonical_json_bytes(candidates)
            ),
            "input_snapshot_sha256": smoke.sha256_bytes(
                smoke.canonical_json_bytes(snapshot)
            ),
            "policy_id": smoke.POLICY_ID,
            "source_mutated": False,
            "tracker_enabled": False,
        }
        if category == "event":
            source = smoke.reachable_event_option_semantics_identity()["contract_id"]
            result.update(
                {
                    "event_observation": {
                        "current_event_id": "the_cleric",
                        "current_position": 0,
                        "event_data": 0,
                        "selected_action_id": candidate["action_id"],
                        "semantics_source": source,
                        "simulator_choice_index": 0,
                        "upstream_event_id": "The Cleric",
                    },
                    "event_semantics_source": source,
                }
            )
        return result


class InvalidActionTypeSession(FakeSession):
    def __init__(self, action_type):
        self.action_type = action_type

    def evaluate(self, *, snapshot, candidates, decision_index):
        result = super().evaluate(
            snapshot=snapshot,
            candidates=candidates,
            decision_index=decision_index,
        )
        result["action_type"] = self.action_type
        return result


def _factory(plans):
    def create(seed):
        categories, blocker = plans[seed]
        return FakeEnvironment(seed, categories, blocker=blocker)

    return create


def _passing_plans(*, support_seed=None):
    plans = {
        7000: (["route"], None),
        7100: (["shop"], None),
        2000: (["event"], None),
        10: (["card_reward"], None),
    }
    if support_seed is not None:
        categories, _ = plans[support_seed]
        plans[support_seed] = (categories, smoke.DECLARED_SUPPORT_REASON)
    return plans


def _rehash_row(row):
    payload = copy.deepcopy(row)
    payload.pop("replay_count")
    payload.pop("trajectory_sha256")
    row["trajectory_sha256"] = smoke.sha256_bytes(
        smoke.canonical_json_bytes(payload)
    )


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("seed", "registration_cohort_mismatch"),
        ("seed_type", "registration_cohort_mismatch"),
        ("replay", "registration_cohort_mismatch"),
        ("limit", "registration_limits_mismatch"),
        ("limit_type", "registration_limits_mismatch"),
        ("authority", "authority_must_be_all_false"),
        ("authority_type", "authority_must_be_all_false"),
        ("output", "registration_output_mismatch"),
        ("module", "registered_module_identity_mismatch"),
    ],
)
@pytest.mark.parametrize(
    "profile", [smoke.V1_PROFILE, smoke.R2_PROFILE], ids=lambda value: value.name
)
def test_registration_contract_is_exact(tmp_path, mutation, reason, profile):
    registration = _registration(tmp_path, profile=profile)
    if mutation == "seed":
        registration["cohort"]["seeds"][0] = 9999
    elif mutation == "seed_type":
        registration["cohort"]["seeds"][0] = 7000.0
    elif mutation == "replay":
        registration["cohort"]["replay_count"] = 3
    elif mutation == "limit":
        registration["limits"]["max_wall_seconds"] = 601.0
    elif mutation == "limit_type":
        registration["limits"]["max_wall_seconds"] = 600
    elif mutation == "authority":
        registration["authority"]["training_authorized"] = True
    elif mutation == "authority_type":
        registration["authority"]["training_authorized"] = 0
    elif mutation == "output":
        registration["output"]["directory"] = "reports/other"
    else:
        registration["identity"]["adapter_provenance"]["module_sha256"] = "0" * 64

    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke.validate_registration(registration, profile=profile)

    assert exc_info.value.reason == reason


def test_cli_has_no_seed_or_limit_override():
    parser = smoke.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["execute", "--seed", "1"])
    with pytest.raises(SystemExit):
        parser.parse_args(["execute", "--max-wall-seconds", "1"])
    with pytest.raises(SystemExit):
        parser.parse_args(["execute-r2", "--seed", "1"])
    assert parser.parse_args(["verify-r2"]).command == "verify-r2"


def test_r2_registration_has_distinct_versioned_publication_identity(tmp_path):
    registration = _registration(tmp_path, profile=smoke.R2_PROFILE)

    assert registration["schema_version"] == smoke.R2_PROFILE.input_schema_version
    assert registration["output"]["directory"] == smoke.R2_PROFILE.output_directory
    assert registration["identity"]["preimplementation"] == {
        "path": smoke.R2_PROFILE.preimplementation_path,
        "sha256": smoke.R2_PROFILE.preimplementation_sha256,
        "size_bytes": smoke.R2_PROFILE.preimplementation_size_bytes,
    }
    assert registration["cohort"] == {
        "replay_count": smoke.REPLAY_COUNT,
        "seeds": list(smoke.FIXED_SEEDS),
    }


def test_mixed_profile_fails_before_environment_construction(tmp_path):
    registration = _registration(tmp_path, profile=smoke.V1_PROFILE)
    constructed = []

    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke.run_diagnostic(
            registration=registration,
            environment_factory=lambda seed: constructed.append(seed),
            session_factory=FakeSession,
            profile=smoke.R2_PROFILE,
        )

    assert exc_info.value.reason == "registration_schema_mismatch"
    assert constructed == []


def test_r2_publication_uses_only_r2_schemas(tmp_path):
    registration = _registration(tmp_path, profile=smoke.R2_PROFILE)
    output = tmp_path / "r2-output"
    registration_sha256 = "2" * 64

    result = smoke.consume_and_run(
        registration=registration,
        registration_sha256=registration_sha256,
        preregistration_commit="3" * 40,
        output_directory=output,
        environment_factory=_factory(_passing_plans()),
        session_factory=FakeSession,
        profile=smoke.R2_PROFILE,
    )
    manifest = smoke.verify_artifact_directory(
        registration=registration,
        registration_sha256=registration_sha256,
        output_directory=output,
        profile=smoke.R2_PROFILE,
    )
    configuration = json.loads((output / "configuration.json").read_text())
    journal = json.loads((output / "execution_journal.json").read_text())
    metrics = json.loads((output / "metrics.json").read_text())
    trajectories = json.loads((output / "trajectory_rows.json").read_text())

    assert result["schema_version"] == smoke.R2_PROFILE.execution_schema_version
    assert (
        configuration["schema_version"]
        == smoke.R2_PROFILE.configuration_schema_version
    )
    assert journal["schema_version"] == smoke.R2_PROFILE.journal_schema_version
    assert metrics["schema_version"] == smoke.R2_PROFILE.metrics_schema_version
    assert (
        trajectories["schema_version"]
        == smoke.R2_PROFILE.trajectory_schema_version
    )
    assert manifest["schema_version"] == smoke.R2_PROFILE.manifest_schema_version

    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke.verify_artifact_directory(
            registration=registration,
            registration_sha256=registration_sha256,
            output_directory=output,
            profile=smoke.V1_PROFILE,
        )
    assert exc_info.value.reason == "registration_schema_mismatch"


def test_terminal_and_declared_support_rows_pass_and_continue(tmp_path):
    registration = _registration(tmp_path)
    plans = _passing_plans(support_seed=10)

    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=_factory(plans),
        session_factory=FakeSession,
    )

    assert result["verdict"] == "current_bridge_diagnostic_passed"
    assert result["status"] == "passed"
    assert result["terminal_row_count"] == 3
    assert result["support_blocker_count"] == 1
    assert [row["seed"] for row in result["rows"]] == list(smoke.FIXED_SEEDS)
    assert result["rows"][-1]["disposition"] == "declared_support_blocked"
    assert result["rows"][-1]["support_reason"] == smoke.DECLARED_SUPPORT_REASON
    assert result["rows"][-1]["outcome"] is None
    assert all(count > 0 for count in result["category_counts"].values())


def test_all_declared_support_rows_are_support_limited(tmp_path):
    registration = _registration(tmp_path)
    plans = {
        seed: ([], smoke.DECLARED_SUPPORT_REASON) for seed in smoke.FIXED_SEEDS
    }

    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=_factory(plans),
        session_factory=FakeSession,
    )

    assert result["status"] == "support_limited"
    assert result["verdict"] == "current_bridge_diagnostic_support_limited"
    assert result["terminal_row_count"] == 0
    assert result["support_blocker_count"] == 4
    assert len(result["rows"]) == 4


def test_mismatched_support_replays_fail_before_later_seeds(tmp_path):
    registration = _registration(tmp_path)
    calls = []

    def environment_factory(seed):
        calls.append(seed)
        if seed == 7000 and calls.count(seed) == 1:
            return FakeEnvironment(seed, [], blocker=smoke.DECLARED_SUPPORT_REASON)
        return FakeEnvironment(seed, ["route"])

    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=environment_factory,
        session_factory=FakeSession,
    )

    assert result["verdict"] == "current_bridge_diagnostic_failed"
    assert result["reason"] == "replay_disposition_mismatch"
    assert result["rows"] == []
    assert calls == [7000, 7000]


def test_unknown_blocker_preserves_prior_rows_and_stops(tmp_path):
    registration = _registration(tmp_path)
    plans = _passing_plans()
    plans[7100] = (["shop"], "unexpected_shop_failure")
    calls = []

    def environment_factory(seed):
        calls.append(seed)
        categories, blocker = plans[seed]
        return FakeEnvironment(seed, categories, blocker=blocker)

    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=environment_factory,
        session_factory=FakeSession,
    )

    assert result["verdict"] == "current_bridge_diagnostic_failed"
    assert result["reason"] == "native_snapshot_failed"
    assert [row["seed"] for row in result["rows"]] == [7000]
    assert calls == [7000, 7000, 7100]


@pytest.mark.parametrize(
    ("category", "step_blocker", "expected_disposition", "expected_reason"),
    [
        (
            "event",
            smoke.DECLARED_SUPPORT_REASON,
            "declared_support_blocked",
            None,
        ),
        ("shop", "unexpected_step_failure", None, "native_step_failed"),
    ],
)
def test_step_failure_classification_preserves_only_completed_transitions(
    tmp_path, category, step_blocker, expected_disposition, expected_reason
):
    registration = _registration(tmp_path)

    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=lambda seed: FakeEnvironment(
            seed, [category], step_blocker=step_blocker
        ),
        session_factory=FakeSession,
    )

    if expected_reason is not None:
        assert result["verdict"] == "current_bridge_diagnostic_failed"
        assert result["reason"] == expected_reason
        assert result["rows"] == []
    else:
        assert result["verdict"] == "current_bridge_diagnostic_support_limited"
        assert all(
            row["disposition"] == expected_disposition for row in result["rows"]
        )
        assert all(row["decision_count"] == 0 for row in result["rows"])
        assert all(row["category_counts"][category] == 0 for row in result["rows"])
        assert all(row["event_identities"] == [] for row in result["rows"])


def test_terminal_seed_mismatch_fails_closed(tmp_path):
    registration = _registration(tmp_path)

    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=lambda seed: FakeEnvironment(
            seed, ["route"], terminal_seed=seed + 1
        ),
        session_factory=FakeSession,
    )

    assert result["verdict"] == "current_bridge_diagnostic_failed"
    assert result["reason"] == "terminal_state_invalid"
    assert result["rows"] == []


def test_fake_candidate_matches_exact_production_schema():
    candidate = FakeEnvironment(7000, ["route"]).legal_actions()[0]

    assert set(candidate) == PRODUCTION_CANDIDATE_KEYS
    assert "action_type" not in candidate


def test_production_candidate_schema_does_not_require_action_type(tmp_path):
    registration = _registration(tmp_path)

    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=_factory(_passing_plans()),
        session_factory=FakeSession,
    )

    assert result["verdict"] == "current_bridge_diagnostic_passed"
    assert result["reason"] is None
    assert len(result["rows"]) == len(smoke.FIXED_SEEDS)


@pytest.mark.parametrize("action_type", [None, "", 1])
def test_current_evaluation_action_type_must_be_nonempty_string(
    tmp_path, action_type
):
    registration = _registration(tmp_path)
    environments = []

    def environment_factory(seed):
        categories, blocker = _passing_plans()[seed]
        environment = FakeEnvironment(seed, categories, blocker=blocker)
        environments.append(environment)
        return environment

    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=environment_factory,
        session_factory=lambda: InvalidActionTypeSession(action_type),
    )

    assert result["verdict"] == "current_bridge_diagnostic_failed"
    assert result["reason"] == "current_evaluation_contract_invalid"
    assert result["rows"] == []
    assert len(environments) == 1
    assert environments[0].index == 0


def test_missing_category_coverage_fails_after_complete_rows(tmp_path):
    registration = _registration(tmp_path)
    plans = {seed: (["route"], None) for seed in smoke.FIXED_SEEDS}

    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=_factory(plans),
        session_factory=FakeSession,
    )

    assert result["verdict"] == "current_bridge_diagnostic_failed"
    assert result["reason"] == "aggregate_category_coverage_missing"
    assert len(result["rows"]) == 4


def test_deadline_failure_is_fail_closed(tmp_path):
    registration = _registration(tmp_path)
    ticks = iter([0.0, 601.0])

    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=_factory(_passing_plans()),
        session_factory=FakeSession,
        monotonic=lambda: next(ticks),
    )

    assert result["verdict"] == "current_bridge_diagnostic_failed"
    assert result["reason"] == "execution_deadline_exceeded"
    assert result["rows"] == []


def test_started_journal_precedes_environment_and_output_is_one_shot(tmp_path):
    registration = _registration(tmp_path)
    output = tmp_path / "output"
    registration_sha256 = "2" * 64
    preregistration_commit = "3" * 40

    def environment_factory(seed):
        journal = json.loads((output / "execution_journal.json").read_text())
        assert journal["status"] == "started"
        assert journal["attempted_seeds"] == list(smoke.FIXED_SEEDS)
        return _factory(_passing_plans())(seed)

    result = smoke.consume_and_run(
        registration=registration,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        output_directory=output,
        environment_factory=environment_factory,
        session_factory=FakeSession,
    )

    assert result["verdict"] == "current_bridge_diagnostic_passed"
    assert sorted(path.name for path in output.iterdir()) == sorted(
        smoke.CANONICAL_ARTIFACT_NAMES
    )
    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke.consume_and_run(
            registration=registration,
            registration_sha256=registration_sha256,
            preregistration_commit=preregistration_commit,
            output_directory=output,
            environment_factory=environment_factory,
            session_factory=FakeSession,
        )
    assert exc_info.value.reason == "output_directory_already_exists"


def test_interruption_leaves_started_journal(tmp_path):
    registration = _registration(tmp_path)
    output = tmp_path / "interrupted"

    def interrupted_environment(_seed):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        smoke.consume_and_run(
            registration=registration,
            registration_sha256="4" * 64,
            preregistration_commit="5" * 40,
            output_directory=output,
            environment_factory=interrupted_environment,
            session_factory=FakeSession,
        )

    journal = json.loads((output / "execution_journal.json").read_text())
    assert journal["status"] == "started"
    assert journal["result_sha256"] is None


def test_no_native_verifier_replays_artifacts_and_rejects_drift(tmp_path):
    registration = _registration(tmp_path)
    output = tmp_path / "output"
    registration_sha256 = "6" * 64
    preregistration_commit = "7" * 40
    smoke.consume_and_run(
        registration=registration,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        output_directory=output,
        environment_factory=_factory(_passing_plans(support_seed=10)),
        session_factory=FakeSession,
    )

    manifest = smoke.verify_artifact_directory(
        registration=registration,
        registration_sha256=registration_sha256,
        output_directory=output,
    )
    assert manifest["verdict"] == "current_bridge_diagnostic_passed"

    extra = output / "extra"
    extra.mkdir()
    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke.verify_artifact_directory(
            registration=registration,
            registration_sha256=registration_sha256,
            output_directory=output,
        )
    assert exc_info.value.reason == "artifact_inventory_mismatch"
    extra.rmdir()

    (output / "report.md").write_text("drift\n", encoding="utf-8")
    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke.verify_artifact_directory(
            registration=registration,
            registration_sha256=registration_sha256,
            output_directory=output,
        )
    assert exc_info.value.reason == "artifact_recomputation_mismatch"


def test_consumed_artifact_directory_recomputes_without_native_loading():
    registration_path = REPO_ROOT / smoke.V1_PROFILE.registration_path
    output = REPO_ROOT / smoke.V1_PROFILE.output_directory
    protected_paths = [
        registration_path,
        REPO_ROOT
        / "reports"
        / "noncombat_current_bridge_diagnostic_smoke_20260803_closeout.md",
        *sorted(output.iterdir()),
    ]
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in protected_paths
    }
    registration = smoke.load_registration(
        registration_path, profile=smoke.V1_PROFILE
    )

    manifest = smoke.verify_artifact_directory(
        registration=registration,
        registration_sha256=smoke.sha256_file(registration_path),
        output_directory=output,
        profile=smoke.V1_PROFILE,
    )

    after = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in protected_paths
    }
    assert manifest["verdict"] == "current_bridge_diagnostic_failed"
    assert before == after
    assert "sts_lightspeed_noncombat_adapter" not in sys.modules


def test_committed_r2_preimplementation_is_canonical_and_exact():
    path = REPO_ROOT / smoke.R2_PROFILE.preimplementation_path
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.read_bytes() == _canonical_bytes(payload)
    validated = smoke.validate_preimplementation_file(
        path, repo_root=REPO_ROOT, profile=smoke.R2_PROFILE
    )
    assert validated["lineage"]["consumed_v1"]["failure"] == {
        "category_counts": {
            "card_reward": 0,
            "event": 0,
            "route": 0,
            "shop": 0,
        },
        "reason": "diagnostic_execution_failed",
        "retained_rows": 0,
        "status": "failed",
        "support_blocker_count": 0,
        "terminal_row_count": 0,
        "verdict": "current_bridge_diagnostic_failed",
    }
    assert validated["lineage"]["candidate_schema_fix"]["commit"] == (
        "b0c7ccc0b88a7a847b1119a984b6378032d94b78"
    )


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("failure", "consumed_v1_failure_mismatch"),
        ("fix_commit", "candidate_schema_fix_commit_mismatch"),
        ("artifact_path", "preimplementation_lineage_path_mismatch"),
        ("authority", "preimplementation_authority_mismatch"),
    ],
)
def test_r2_preimplementation_rejects_lineage_drift(mutation, reason):
    path = REPO_ROOT / smoke.R2_PROFILE.preimplementation_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "failure":
        payload["lineage"]["consumed_v1"]["failure"]["retained_rows"] = 1
    elif mutation == "fix_commit":
        payload["lineage"]["candidate_schema_fix"]["commit"] = "0" * 40
    elif mutation == "artifact_path":
        payload["lineage"]["consumed_v1"]["artifacts"][0]["path"] = (
            "reports/other.json"
        )
    else:
        payload["authority"]["training_authorized"] = True

    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke.validate_preimplementation(payload, profile=smoke.R2_PROFILE)

    assert exc_info.value.reason == reason


def test_r2_source_drift_fails_before_native_loading(tmp_path, monkeypatch):
    registration = _registration(tmp_path, profile=smoke.R2_PROFILE)
    contract_path = registration["identity"]["contract_file"]["path"]
    registration["identity"]["contract_file"] = _binding(
        REPO_ROOT / contract_path, display_path=contract_path
    )
    native_loads = []
    monkeypatch.setattr(
        smoke,
        "load_native_module",
        lambda *_args, **_kwargs: native_loads.append(True),
    )

    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke.validate_registration_evidence(
            registration, REPO_ROOT, profile=smoke.R2_PROFILE
        )

    assert exc_info.value.reason == "implementation_source_hash_mismatch"
    assert native_loads == []


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("event_identity", "execution_row_event_identities_mismatch"),
        ("decision_hash", "execution_row_decision_invalid"),
        ("row_seed_type", "execution_row_identity_mismatch"),
        ("row_count_type", "execution_row_counts_mismatch"),
    ],
)
def test_execution_row_validator_rejects_forged_nested_evidence(
    tmp_path, mutation, reason
):
    registration = _registration(tmp_path)
    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=_factory(_passing_plans()),
        session_factory=FakeSession,
    )
    forged = copy.deepcopy(result)
    event_row = forged["rows"][2]
    if mutation == "event_identity":
        event_row["event_identities"][0]["current_event_id"] = "forged"
    elif mutation == "decision_hash":
        event_row["decisions"][0]["candidate_actions_sha256"] = "z" * 64
    elif mutation == "row_seed_type":
        event_row["seed"] = 2000.0
    else:
        event_row["category_counts"]["event"] = True
    _rehash_row(event_row)

    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke._validate_execution_result(forged, registration)

    assert exc_info.value.reason == reason


def test_execution_result_rejects_forged_lower_verdict(tmp_path):
    registration = _registration(tmp_path)
    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=_factory(_passing_plans()),
        session_factory=FakeSession,
    )
    forged = copy.deepcopy(result)
    forged.update(
        {
            "detail": {"forged": True},
            "reason": "forged_failure",
            "status": "failed",
            "verdict": "current_bridge_diagnostic_failed",
        }
    )

    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke._validate_execution_result(forged, registration)

    assert exc_info.value.reason == "execution_verdict_precedence_invalid"


def test_execution_result_rejects_boolean_aggregate_count(tmp_path):
    registration = _registration(tmp_path)
    result = smoke.run_diagnostic(
        registration=registration,
        environment_factory=_factory(_passing_plans()),
        session_factory=FakeSession,
    )
    forged = copy.deepcopy(result)
    forged["category_counts"]["route"] = True

    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke._validate_execution_result(forged, registration)

    assert exc_info.value.reason == "execution_aggregate_counts_mismatch"


def test_preimplementation_rejects_extra_non_mapping_seed_rationale():
    path = REPO_ROOT / smoke.PREIMPLEMENTATION_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["seed_rationale"].append(None)

    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke.validate_preimplementation(payload)

    assert exc_info.value.reason == "preimplementation_seed_rationale_mismatch"


def test_committed_preimplementation_is_canonical_and_exact():
    path = (
        REPO_ROOT
        / "reports"
        / "noncombat_current_bridge_diagnostic_smoke_20260803_preimplementation.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.read_bytes() == _canonical_bytes(payload)
    validated = smoke.validate_preimplementation(payload)
    assert validated["cohort"]["seeds"] == list(smoke.FIXED_SEEDS)
    assert len(validated["tracked_evidence"]) == 19
    assert len(validated["module_evidence"]) == 3


def test_pushed_registration_requires_exact_head_blob(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    path = tmp_path / smoke.DEFAULT_REGISTRATION_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(_canonical_bytes(registration))
    head = "8" * 40

    def git_text(_root, *args):
        if args[:2] == ("status", "--porcelain"):
            return ""
        if args == ("rev-parse", "HEAD") or args == ("rev-parse", "origin/master"):
            return head
        raise AssertionError(args)

    monkeypatch.setattr(smoke, "_git_text", git_text)
    monkeypatch.setattr(
        smoke,
        "_git_bytes",
        lambda _root, *args: path.read_bytes()
        if args == ("show", f"{head}:{smoke.DEFAULT_REGISTRATION_PATH}")
        else (_ for _ in ()).throw(AssertionError(args)),
    )

    pushed = smoke.assert_pushed_registration(
        registration_path=path,
        repo_root=tmp_path,
    )
    assert pushed["preregistration_commit"] == head

    monkeypatch.setattr(smoke, "_git_bytes", lambda *_args: b"drift")
    with pytest.raises(smoke.DiagnosticBlocked) as exc_info:
        smoke.assert_pushed_registration(
            registration_path=path,
            repo_root=tmp_path,
        )
    assert exc_info.value.reason == "pushed_registration_mismatch"
