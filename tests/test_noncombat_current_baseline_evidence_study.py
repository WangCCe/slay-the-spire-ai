from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

import pytest

import analysis_scripts.noncombat_current_baseline_evidence_study as study


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_CANDIDATE_KEYS = {
    "action_id",
    "available",
    "category",
    "kind",
    "label",
    "raw",
}


def _preimplementation():
    return json.loads((REPO_ROOT / study.PREIMPLEMENTATION_PATH).read_text())


def _binding(path, *, display_path=None):
    payload = path.read_bytes()
    return {
        "path": display_path or str(path.resolve()),
        "sha256": study.sha256_bytes(payload),
        "size_bytes": len(payload),
    }


def _identity(tmp_path):
    preimplementation = _preimplementation()
    r2 = json.loads(
        (REPO_ROOT / "reports/noncombat_current_bridge_diagnostic_smoke_20260803_r2_input.json").read_text()
    )
    seed_inventory = tmp_path / "seed_inventory.json"
    seed_inventory.write_text("{}\n", encoding="utf-8")
    runtime = tmp_path / "python.exe"
    runtime.write_bytes(b"runtime")
    event_semantics = study.reachable_event_option_semantics_identity()
    event_contract_path = event_semantics["observation_contract"]["path"]
    return {
        "adapter_provenance": r2["identity"]["adapter_provenance"],
        "adapter_source_files": list(study.compatibility.ADAPTER_SOURCE_FILES),
        "event_contract": _binding(
            REPO_ROOT / event_contract_path,
            display_path=event_contract_path,
        ),
        "event_semantics": event_semantics,
        "implementation": {
            "commit": "a" * 40,
            "source_files": list(study.IMPLEMENTATION_SOURCE_FILES),
            "source_sha256": "b" * 64,
        },
        "metadata": copy.deepcopy(
            preimplementation["external_identity_expectations"]["metadata"]
        ),
        "module": copy.deepcopy(
            preimplementation["external_identity_expectations"]["module"]
        ),
        "preimplementation": {
            "path": study.PREIMPLEMENTATION_PATH,
            "sha256": study.EXPECTED_PREIMPLEMENTATION_SHA256,
            "size_bytes": study.EXPECTED_PREIMPLEMENTATION_SIZE_BYTES,
        },
        "runtime": {
            **copy.deepcopy(
                preimplementation["external_identity_expectations"]["runtime"]
            ),
            "sha256": study.sha256_file(runtime),
            "size_bytes": runtime.stat().st_size,
        },
        "seed_inventory": _binding(
            seed_inventory,
            display_path=study.DEFAULT_SEED_INVENTORY_PATH,
        ),
        "simulator": copy.deepcopy(
            preimplementation["external_identity_expectations"]["simulator"]
        ),
    }


def _registration(tmp_path):
    return study.build_registration(identity=_identity(tmp_path))


class FakeEnvironment:
    def __init__(
        self,
        seed,
        categories,
        *,
        terminal_floor=20,
        blocker=None,
        step_blocker=None,
        candidates_per_decision=2,
    ):
        self.seed = seed
        self.categories = list(categories)
        self.terminal_floor = terminal_floor
        self.blocker = blocker
        self.step_blocker = step_blocker
        self.candidates_per_decision = candidates_per_decision
        self.index = 0
        self.selected = []
        self.candidate_key_sets = []

    def snapshot(self):
        if self.index >= len(self.categories):
            if self.blocker is not None:
                raise RuntimeError(self.blocker)
            return {
                "state": {
                    "floor": self.terminal_floor,
                    "outcome": "player_loss",
                    "seed": str(self.seed),
                },
                "terminal": True,
            }
        category = self.categories[self.index]
        return {
            "category": category,
            "decision_count": self.index,
            "state": {
                "decision_context": {},
                "floor": min(self.terminal_floor, self.index + 1),
                "seed": str(self.seed),
            },
            "terminal": False,
        }

    def legal_actions(self):
        category = self.categories[self.index]
        candidates = [
            {
                "action_id": f"{category}:fixture:{candidate_index}",
                "available": True,
                "category": category,
                "kind": "fixture_action",
                "label": f"{category} fixture {candidate_index}",
                "raw": {},
            }
            for candidate_index in range(self.candidates_per_decision)
        ]
        self.candidate_key_sets.append(set(candidates[0]))
        return candidates

    def step(self, action_id):
        self.selected.append(action_id)
        self.index += 1
        if self.step_blocker is not None:
            raise RuntimeError(self.step_blocker)
        return {"selected_action_id": action_id}


class FakeSession:
    def __init__(self, *, action_index=1):
        self.action_index = action_index
        self.calls = []

    def evaluate(self, *, snapshot, candidates, decision_index):
        self.calls.append(decision_index)
        candidate = candidates[self.action_index]
        return {
            "action_id": candidate["action_id"],
            "action_type": "FixtureCurrentAction",
            "category": snapshot["category"],
            "fallback_used": False,
            "input_candidates_sha256": study.sha256_bytes(
                study.canonical_json_bytes(candidates)
            ),
            "input_snapshot_sha256": study.sha256_bytes(
                study.canonical_json_bytes(snapshot)
            ),
            "policy_id": study.CURRENT_POLICY_ID,
            "source_mutated": False,
            "tracker_enabled": False,
        }


def _row(
    seed,
    policy_id,
    floor,
    *,
    categories=("card_reward", "event", "route", "shop"),
    support=False,
):
    category_counts = Counter(categories)
    decisions = [
        {
            "action_id": f"{category}:fixture:0",
            "action_type": "FixtureAction",
            "candidate_actions_sha256": str(index + 1) * 64,
            "category": category,
            "decision_index": index,
            "policy_input_sha256": str(index + 2) * 64,
            "source_snapshot_sha256": str(index + 3) * 64,
        }
        for index, category in enumerate(categories)
    ]
    row = {
        "action_sequence_sha256": study.sha256_bytes(
            study.canonical_json_bytes(
                [decision["action_id"] for decision in decisions]
            )
        ),
        "category_counts": {
            category: category_counts[category]
            for category in study.TARGET_CATEGORIES
        },
        "decision_count": len(categories),
        "decisions": decisions,
        "disposition": "declared_support_blocked" if support else "terminal",
        "floor": floor,
        "outcome": "player_loss",
        "policy_id": policy_id,
        "seed": seed,
        "support_reason": study.DECLARED_SUPPORT_REASON if support else None,
    }
    row["trajectory_sha256"] = study.sha256_bytes(study.canonical_json_bytes(row))
    return {**row, "replay_count": study.REPLAY_COUNT}


def _stage_rows(
    seeds,
    *,
    current_floor,
    control_floor,
    current_categories=("card_reward", "event", "route", "shop"),
    current_support=(),
    control_support=(),
):
    rows = []
    for seed in seeds:
        rows.extend(
            [
                _row(
                    seed,
                    study.CURRENT_POLICY_ID,
                    current_floor,
                    categories=current_categories,
                    support=seed in current_support,
                ),
                _row(
                    seed,
                    study.CONTROL_POLICY_ID,
                    control_floor,
                    support=seed in control_support,
                ),
            ]
        )
    return rows


def test_preimplementation_is_exact_canonical_and_all_false():
    value = _preimplementation()

    normalized = study.validate_preimplementation(copy.deepcopy(value))

    assert normalized == value
    assert all(enabled is False for enabled in normalized["authority"].values())
    assert study.canonical_json_bytes(value) == (
        REPO_ROOT / study.PREIMPLEMENTATION_PATH
    ).read_bytes()


def test_unexecuted_study_artifacts_are_not_seed_exclusion_sources(
    tmp_path, monkeypatch
):
    reports = tmp_path / "reports"
    reports.mkdir()
    historical = reports / "historical.json"
    historical.write_text('{"seed": 42}\n', encoding="utf-8")
    managed_paths = (
        study.PREIMPLEMENTATION_PATH,
        study.DEFAULT_SEED_INVENTORY_PATH,
        study.DEFAULT_REGISTRATION_PATH,
        study.DEFAULT_PREFLIGHT_PATH,
        study.DEFAULT_EXECUTION_AUTHORIZATION_PATH,
    )
    for relative in managed_paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"seed": 11000}\n', encoding="utf-8")
    tracked = ["reports/historical.json", *managed_paths]
    monkeypatch.setattr(
        study.compatibility,
        "_git_text",
        lambda _root, *args: "\n".join(tracked),
    )

    documents = study.compatibility.discover_seed_documents(tmp_path)

    assert sorted(documents) == ["reports/historical.json"]


def test_seed_inventory_rejects_study_overlap_before_any_quality_use():
    inventory = study.compatibility.build_tracked_seed_inventory(REPO_ROOT)
    row = {
        "json_path": "$.seed",
        "role": "reserved",
        "seed": study.CANARY_SEEDS[0],
        "source_path": inventory["source_bindings"][0]["path"],
    }
    inventory["rows"].append(row)
    inventory["rows"].sort(
        key=lambda value: (value["seed"], value["source_path"], value["json_path"])
    )
    inventory["row_count"] = len(inventory["rows"])
    inventory["excluded_seeds"] = sorted(
        {value["seed"] for value in inventory["rows"]}
    )
    inventory["excluded_seed_count"] = len(inventory["excluded_seeds"])

    with pytest.raises(study.StudyBlocked) as exc_info:
        study.validate_study_seed_inventory(
            inventory, implementation_commit=inventory["repository_commit"]
        )

    assert exc_info.value.reason == "study_seed_overlap"


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("planning", "preimplementation_identity_mismatch"),
        ("cohort", "preimplementation_identity_mismatch"),
        ("threshold", "preimplementation_identity_mismatch"),
        ("authority", "preimplementation_identity_mismatch"),
        ("overlap", "preimplementation_identity_mismatch"),
        ("output", "preimplementation_identity_mismatch"),
    ],
)
def test_preimplementation_mutation_is_rejected(mutation, reason):
    value = _preimplementation()
    if mutation == "planning":
        value["planning_commit"] = "0" * 40
    elif mutation == "cohort":
        value["cohorts"]["canary"][0] = 10999
    elif mutation == "threshold":
        value["gates"]["holdout"]["current_mean_floor_min"] = 17.0
    elif mutation == "authority":
        value["authority"]["training_authorized"] = True
    elif mutation == "overlap":
        value["seed_exclusion"]["zero_overlap"]["canary"] = [11000]
    else:
        value["output"]["exists"] = True

    with pytest.raises(study.StudyBlocked) as exc_info:
        study.validate_preimplementation(value)

    assert exc_info.value.reason == reason


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("canary", "registration_cohort_mismatch"),
        ("holdout", "registration_cohort_mismatch"),
        ("policy", "registration_policy_mismatch"),
        ("gate", "registration_gate_mismatch"),
        ("bootstrap", "registration_bootstrap_mismatch"),
        ("limit", "registration_limit_mismatch"),
        ("authority", "authority_must_be_all_false"),
        ("output", "registration_output_mismatch"),
        ("source", "implementation_identity_mismatch"),
        ("module", "external_identity_mismatch"),
    ],
)
def test_registration_contract_rejects_every_fixed_field_drift(
    tmp_path, mutation, reason
):
    registration = _registration(tmp_path)
    if mutation == "canary":
        registration["cohorts"]["canary"][0] = 1
    elif mutation == "holdout":
        registration["cohorts"]["holdout"][-1] = 1
    elif mutation == "policy":
        registration["policies"]["control"]["policy_id"] = "other"
    elif mutation == "gate":
        registration["gates"]["canary"]["current_mean_floor_min"] = 14.0
    elif mutation == "bootstrap":
        registration["gates"]["bootstrap"]["resamples"] = 9999
    elif mutation == "limit":
        registration["limits"]["total_max_wall_seconds"] = 1801.0
    elif mutation == "authority":
        registration["authority"]["training_authorized"] = True
    elif mutation == "output":
        registration["output"]["directory"] = "reports/other"
    elif mutation == "source":
        registration["identity"]["implementation"]["source_files"] = []
    else:
        registration["identity"]["module"]["sha256"] = "0" * 64

    with pytest.raises(study.StudyBlocked) as exc_info:
        study.validate_registration(registration)

    assert exc_info.value.reason == reason


def test_invalid_registration_fails_before_environment_construction(tmp_path):
    registration = _registration(tmp_path)
    registration["cohorts"]["canary"][0] = 1
    constructed = []

    with pytest.raises(study.StudyBlocked) as exc_info:
        study.run_study(
            registration=registration,
            environment_factory=lambda *args: constructed.append(args),
            session_factory=FakeSession,
        )

    assert exc_info.value.reason == "registration_cohort_mismatch"
    assert constructed == []


def _execution_authorization(registration, *, registration_sha256, commit):
    return {
        "approval": {
            "approved": True,
            "scope": "one_canary_and_conditional_holdout_same_attempt",
            "source": "explicit_user_approval",
        },
        "authority": {
            **copy.deepcopy(study.ALL_FALSE_AUTHORITY),
            "execution_authorized": True,
        },
        "command": list(study.EXACT_EXECUTION_COMMAND),
        "preregistration_commit": commit,
        "registration": {
            "path": study.DEFAULT_REGISTRATION_PATH,
            "sha256": registration_sha256,
            "size_bytes": len(study.canonical_json_bytes(registration)),
        },
        "schema_version": study.EXECUTION_AUTHORIZATION_SCHEMA_VERSION,
    }


def test_execution_authorization_is_separate_and_exact(tmp_path):
    registration = _registration(tmp_path)
    registration_sha256 = study.sha256_bytes(study.canonical_json_bytes(registration))
    commit = "c" * 40
    authorization = _execution_authorization(
        registration,
        registration_sha256=registration_sha256,
        commit=commit,
    )

    assert study.validate_execution_authorization(
        authorization,
        registration=registration,
        registration_sha256=registration_sha256,
        preregistration_commit=commit,
    ) == authorization

    for mutation in ("missing", "hash", "commit", "command", "authority"):
        candidate = None if mutation == "missing" else copy.deepcopy(authorization)
        if mutation == "hash":
            candidate["registration"]["sha256"] = "0" * 64
        elif mutation == "commit":
            candidate["preregistration_commit"] = "0" * 40
        elif mutation == "command":
            candidate["command"].append("--seed")
        elif mutation == "authority":
            candidate["authority"]["training_authorized"] = True
        with pytest.raises(study.StudyBlocked):
            study.validate_execution_authorization(
                candidate,
                registration=registration,
                registration_sha256=registration_sha256,
                preregistration_commit=commit,
            )


def test_pushed_registration_and_output_are_checked_before_execution(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    registration_path = tmp_path / study.DEFAULT_REGISTRATION_PATH
    registration_path.parent.mkdir(parents=True)
    registration_path.write_bytes(study.canonical_json_bytes(registration))
    head = "c" * 40

    def git_text(_root, *args):
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return ""
        if args in {("rev-parse", "HEAD"), ("rev-parse", "origin/master")}:
            return head
        raise AssertionError(args)

    monkeypatch.setattr(study, "_git_text", git_text)
    monkeypatch.setattr(
        study,
        "_git_bytes",
        lambda _root, *args: registration_path.read_bytes(),
    )

    pushed = study.assert_pushed_registration(
        registration_path=registration_path,
        repo_root=tmp_path,
    )
    assert pushed == {
        "preregistration_commit": head,
        "registration_sha256": study.sha256_file(registration_path),
    }

    output = tmp_path / registration["output"]["directory"]
    output.mkdir(parents=True)
    with pytest.raises(study.StudyBlocked) as output_exc:
        study.assert_pushed_registration(
            registration_path=registration_path,
            repo_root=tmp_path,
        )
    assert output_exc.value.reason == "output_directory_already_exists"


def test_unpushed_or_dirty_registration_is_rejected(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    registration_path = tmp_path / study.DEFAULT_REGISTRATION_PATH
    registration_path.parent.mkdir(parents=True)
    registration_path.write_bytes(study.canonical_json_bytes(registration))

    monkeypatch.setattr(
        study,
        "_git_text",
        lambda _root, *args: "dirty" if args[0] == "status" else "c" * 40,
    )
    with pytest.raises(study.StudyBlocked) as dirty_exc:
        study.assert_pushed_registration(
            registration_path=registration_path,
            repo_root=tmp_path,
        )
    assert dirty_exc.value.reason == "tracked_tree_dirty"

    def diverged(_root, *args):
        if args[0] == "status":
            return ""
        return "c" * 40 if args[-1] == "HEAD" else "d" * 40

    monkeypatch.setattr(study, "_git_text", diverged)
    with pytest.raises(study.StudyBlocked) as pushed_exc:
        study.assert_pushed_registration(
            registration_path=registration_path,
            repo_root=tmp_path,
        )
    assert pushed_exc.value.reason == "head_not_pushed"


def test_current_and_control_use_isolated_environments_and_distinct_actions():
    environments = []
    sessions = []

    def environment_factory(seed, policy_id, replay_index):
        environment = FakeEnvironment(seed, ["route"])
        environments.append((seed, policy_id, replay_index, environment))
        return environment

    def session_factory():
        session = FakeSession(action_index=1)
        sessions.append(session)
        return session

    rows = study.run_policy_pair(
        seed=11000,
        environment_factory=environment_factory,
        session_factory=session_factory,
        deadline=100.0,
        monotonic=lambda: 0.0,
    )

    assert len(environments) == 4
    assert len({id(row[3]) for row in environments}) == 4
    assert len(sessions) == 2
    assert rows[0]["policy_id"] == study.CURRENT_POLICY_ID
    assert rows[0]["decisions"][0]["action_id"].endswith(":1")
    assert rows[1]["policy_id"] == study.CONTROL_POLICY_ID
    assert rows[1]["decisions"][0]["action_id"].endswith(":0")
    assert all(
        environment.candidate_key_sets == [PRODUCTION_CANDIDATE_KEYS]
        for _, _, _, environment in environments
    )


def test_control_never_constructs_or_calls_current_session():
    environment = FakeEnvironment(11000, ["shop"])

    row = study.run_episode(
        environment=environment,
        session=None,
        seed=11000,
        policy_id=study.CONTROL_POLICY_ID,
        max_decisions=10,
        deadline=100.0,
        monotonic=lambda: 0.0,
    )

    assert row["policy_id"] == study.CONTROL_POLICY_ID
    assert environment.selected == ["shop:fixture:0"]
    assert row["decisions"][0]["source_snapshot_sha256"]
    assert row["decisions"][0]["candidate_actions_sha256"]
    assert row["action_sequence_sha256"]


def test_terminal_row_retains_complete_outcome_and_policy_identity():
    row = study.run_episode(
        environment=FakeEnvironment(11000, ["route", "shop"], terminal_floor=23),
        session=FakeSession(),
        seed=11000,
        policy_id=study.CURRENT_POLICY_ID,
        max_decisions=10,
        deadline=100.0,
        monotonic=lambda: 0.0,
    )

    assert row["disposition"] == "terminal"
    assert row["floor"] == 23
    assert row["outcome"] == "player_loss"
    assert row["policy_id"] == study.CURRENT_POLICY_ID
    assert row["decision_count"] == 2
    assert len(row["decisions"]) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fallback_used", True),
        ("tracker_enabled", True),
        ("source_mutated", True),
        ("policy_id", "simpleagent"),
        ("policy_id", "bottled"),
    ],
)
def test_current_rejects_fallback_tracker_mutation_and_reference_policy(field, value):
    class InvalidSession(FakeSession):
        def evaluate(self, **kwargs):
            result = super().evaluate(**kwargs)
            result[field] = value
            return result

    with pytest.raises(study.StudyBlocked) as exc_info:
        study.run_episode(
            environment=FakeEnvironment(11000, ["route"]),
            session=InvalidSession(),
            seed=11000,
            policy_id=study.CURRENT_POLICY_ID,
            max_decisions=10,
            deadline=100.0,
            monotonic=lambda: 0.0,
        )

    assert exc_info.value.reason == "current_evaluation_contract_invalid"


@pytest.mark.parametrize("boundary", ["snapshot", "legal_actions", "step"])
def test_exact_courier_blocker_becomes_conservative_nonvictory(boundary):
    environment = FakeEnvironment(11000, ["shop"], terminal_floor=9)
    if boundary == "snapshot":
        environment.categories = []
        environment.index = 0
        environment.blocker = study.DECLARED_SUPPORT_REASON
        with pytest.raises(study.StudyBlocked) as exc_info:
            study.run_episode(
                environment=environment,
                session=None,
                seed=11000,
                policy_id=study.CONTROL_POLICY_ID,
                max_decisions=10,
                deadline=100.0,
                monotonic=lambda: 0.0,
            )
        assert exc_info.value.reason == "declared_support_without_supported_floor"
        return
    if boundary == "legal_actions":
        environment.legal_actions = lambda: (_ for _ in ()).throw(
            RuntimeError(study.DECLARED_SUPPORT_REASON)
        )
    else:
        environment.step_blocker = study.DECLARED_SUPPORT_REASON

    row = study.run_episode(
        environment=environment,
        session=None,
        seed=11000,
        policy_id=study.CONTROL_POLICY_ID,
        max_decisions=10,
        deadline=100.0,
        monotonic=lambda: 0.0,
    )

    assert row["disposition"] == "declared_support_blocked"
    assert row["floor"] == 1
    assert row["outcome"] == "player_loss"
    assert row["support_reason"] == study.DECLARED_SUPPORT_REASON


@pytest.mark.parametrize(
    "reason",
    [
        "unsupported_shop_courier_restock_semantics_extra",
        "unsupported_event_semantics",
        "current_policy_exception",
    ],
)
def test_every_other_runtime_failure_is_unexpected(reason):
    environment = FakeEnvironment(11000, ["shop"], step_blocker=reason)

    with pytest.raises(study.StudyBlocked) as exc_info:
        study.run_episode(
            environment=environment,
            session=None,
            seed=11000,
            policy_id=study.CONTROL_POLICY_ID,
            max_decisions=10,
            deadline=100.0,
            monotonic=lambda: 0.0,
        )

    assert exc_info.value.reason == "native_step_failed"


def test_decision_and_deadline_limits_are_terminal_blockers():
    environment = FakeEnvironment(11000, ["route", "route"])
    with pytest.raises(study.StudyBlocked) as decision_exc:
        study.run_episode(
            environment=environment,
            session=None,
            seed=11000,
            policy_id=study.CONTROL_POLICY_ID,
            max_decisions=1,
            deadline=100.0,
            monotonic=lambda: 0.0,
        )
    assert decision_exc.value.reason == "decision_limit_exceeded"

    with pytest.raises(study.StudyBlocked) as deadline_exc:
        study.run_episode(
            environment=FakeEnvironment(11000, ["route"]),
            session=None,
            seed=11000,
            policy_id=study.CONTROL_POLICY_ID,
            max_decisions=1,
            deadline=0.0,
            monotonic=lambda: 1.0,
        )
    assert deadline_exc.value.reason == "execution_deadline_exceeded"

    ticks = iter((0.0, 101.0))
    with pytest.raises(study.StudyBlocked) as slow_snapshot_exc:
        study.run_episode(
            environment=FakeEnvironment(11000, [], terminal_floor=20),
            session=None,
            seed=11000,
            policy_id=study.CONTROL_POLICY_ID,
            max_decisions=1,
            deadline=100.0,
            monotonic=lambda: next(ticks),
        )
    assert slow_snapshot_exc.value.reason == "execution_deadline_exceeded"


def test_replay_mismatch_is_terminal_and_not_retried():
    calls = []

    def environment_factory(seed, policy_id, replay_index):
        calls.append((seed, policy_id, replay_index))
        floor = 20 if replay_index == 0 else 19
        return FakeEnvironment(seed, ["route"], terminal_floor=floor)

    with pytest.raises(study.StudyBlocked) as exc_info:
        study.run_policy_pair(
            seed=11000,
            environment_factory=environment_factory,
            session_factory=FakeSession,
            deadline=100.0,
            monotonic=lambda: 0.0,
        )

    assert exc_info.value.reason == "trajectory_nondeterministic"
    assert calls == [
        (11000, study.CURRENT_POLICY_ID, 0),
        (11000, study.CURRENT_POLICY_ID, 1),
    ]


def test_canary_exact_numeric_boundaries_pass():
    rows = _stage_rows(
        study.CANARY_SEEDS,
        current_floor=15,
        control_floor=15,
    )

    classification = study.classify_canary(rows)

    assert classification["passes"] is True
    assert classification["current_mean_floor"] == 15.0
    assert classification["paired_mean_floor_difference"] == 0.0


@pytest.mark.parametrize(
    "rows",
    [
        _stage_rows(study.CANARY_SEEDS, current_floor=14, control_floor=14),
        _stage_rows(study.CANARY_SEEDS, current_floor=15, control_floor=16),
        _stage_rows(
            study.CANARY_SEEDS,
            current_floor=15,
            control_floor=15,
            current_categories=("route",),
        ),
        _stage_rows(
            study.CANARY_SEEDS,
            current_floor=15,
            control_floor=15,
            current_support=study.CANARY_SEEDS[:2],
        ),
    ],
)
def test_any_canary_quality_gate_stops_study(rows):
    classification = study.classify_canary(rows)

    assert classification["passes"] is False
    assert classification["verdict"] == "study_stopped_at_canary"


def test_incomplete_canary_denominator_is_structurally_blocked():
    rows = _stage_rows(study.CANARY_SEEDS, current_floor=15, control_floor=15)

    with pytest.raises(study.StudyBlocked) as exc_info:
        study.classify_canary(rows[:-1])

    assert exc_info.value.reason == "stage_denominator_incomplete"


def test_holdout_exact_numeric_boundaries_and_bootstrap_pass():
    rows = _stage_rows(
        study.HOLDOUT_SEEDS,
        current_floor=18,
        control_floor=15,
        current_support=study.HOLDOUT_SEEDS[:3],
        control_support=study.HOLDOUT_SEEDS[:3],
    )

    classification, draws = study.classify_holdout(rows)

    assert classification["passes"] is True
    assert classification["verdict"] == "study_valid_with_baseline_floor"
    assert classification["current_mean_floor"] == 18.0
    assert classification["paired_mean_floor_difference"] == 3.0
    assert classification["absolute_bootstrap"]["lower"] == 18.0
    assert classification["paired_bootstrap"]["lower"] == 3.0
    assert len(draws["absolute_current_mean"]) == study.BOOTSTRAP_RESAMPLES
    assert len(draws["paired_floor_difference_mean"]) == study.BOOTSTRAP_RESAMPLES


@pytest.mark.parametrize(
    "rows",
    [
        _stage_rows(study.HOLDOUT_SEEDS, current_floor=17, control_floor=13),
        _stage_rows(study.HOLDOUT_SEEDS, current_floor=18, control_floor=16),
        _stage_rows(
            study.HOLDOUT_SEEDS,
            current_floor=18,
            control_floor=15,
            current_categories=("route",),
        ),
        _stage_rows(
            study.HOLDOUT_SEEDS,
            current_floor=18,
            control_floor=15,
            current_support=study.HOLDOUT_SEEDS[:4],
        ),
    ],
)
def test_any_holdout_floor_gate_is_terminal_without_floor(rows):
    classification, _ = study.classify_holdout(rows)

    assert classification["passes"] is False
    assert classification["verdict"] == "study_valid_without_baseline_floor"


def test_bootstrap_is_deterministic_and_bound_to_fixed_parameters():
    rows = _stage_rows(study.HOLDOUT_SEEDS, current_floor=20, control_floor=15)

    first, first_draws = study.classify_holdout(rows)
    second, second_draws = study.classify_holdout(rows)

    assert first == second
    assert first_draws == second_draws
    assert first["absolute_bootstrap"] == study.paired_bootstrap_interval(
        [20.0] * 64,
        seed=study.BOOTSTRAP_SEED,
        resamples=study.BOOTSTRAP_RESAMPLES,
        confidence_level=study.BOOTSTRAP_CONFIDENCE,
    )


def test_failed_canary_never_accesses_holdout(tmp_path):
    registration = _registration(tmp_path)
    constructed = []

    def environment_factory(seed, policy_id, replay_index):
        constructed.append((seed, policy_id, replay_index))
        return FakeEnvironment(seed, ["route"], terminal_floor=14)

    result = study.run_study(
        registration=registration,
        environment_factory=environment_factory,
        session_factory=FakeSession,
        monotonic=lambda: 0.0,
    )

    assert result["verdict"] == "study_stopped_at_canary"
    assert result["holdout_accessed"] is False
    assert len(constructed) == study.CANARY_POLICY_EPISODE_LIMIT
    assert not set(study.HOLDOUT_SEEDS).intersection(seed for seed, _, _ in constructed)


def test_publication_is_canonical_atomic_and_no_native_verifiable(tmp_path):
    registration = _registration(tmp_path)
    output = tmp_path / "study-output"

    def environment_factory(seed, policy_id, replay_index):
        return FakeEnvironment(seed, ["route"], terminal_floor=14)

    result = study.consume_and_run(
        registration=registration,
        registration_sha256="c" * 64,
        preregistration_commit="d" * 40,
        output_directory=output,
        environment_factory=environment_factory,
        session_factory=FakeSession,
        monotonic=lambda: 0.0,
    )
    manifest = study.verify_artifact_directory(
        registration=registration,
        registration_sha256="c" * 64,
        output_directory=output,
    )

    assert result["verdict"] == "study_stopped_at_canary"
    assert sorted(path.name for path in output.iterdir()) == sorted(
        study.CANONICAL_ARTIFACT_NAMES
    )
    assert manifest["verdict"] == result["verdict"]
    assert all(
        path.read_bytes() == study.canonical_json_bytes(json.loads(path.read_text()))
        for path in output.glob("*.json")
        if path.name != "artifact_manifest.json" or path.is_file()
    )


def test_existing_output_rejects_without_environment_or_retry(tmp_path):
    registration = _registration(tmp_path)
    output = tmp_path / "study-output"
    output.mkdir()
    constructed = []

    with pytest.raises(study.StudyBlocked) as exc_info:
        study.consume_and_run(
            registration=registration,
            registration_sha256="c" * 64,
            preregistration_commit="d" * 40,
            output_directory=output,
            environment_factory=lambda *args: constructed.append(args),
            session_factory=FakeSession,
        )

    assert exc_info.value.reason == "output_directory_already_exists"
    assert constructed == []


def test_interruption_leaves_started_journal_and_blocks_second_attempt(tmp_path):
    registration = _registration(tmp_path)
    output = tmp_path / "study-output"

    def interrupt(*_args):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        study.consume_and_run(
            registration=registration,
            registration_sha256="c" * 64,
            preregistration_commit="d" * 40,
            output_directory=output,
            environment_factory=interrupt,
            session_factory=FakeSession,
        )

    journal = json.loads((output / "execution_journal.json").read_text())
    assert journal["state"] == "started"

    with pytest.raises(study.StudyBlocked) as exc_info:
        study.consume_and_run(
            registration=registration,
            registration_sha256="c" * 64,
            preregistration_commit="d" * 40,
            output_directory=output,
            environment_factory=interrupt,
            session_factory=FakeSession,
        )
    assert exc_info.value.reason == "output_directory_already_exists"


def test_execute_writes_started_journal_before_native_loading(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    registration_path = tmp_path / study.DEFAULT_REGISTRATION_PATH
    inventory_path = tmp_path / study.DEFAULT_SEED_INVENTORY_PATH
    preflight_path = tmp_path / study.DEFAULT_PREFLIGHT_PATH
    authorization_path = tmp_path / study.DEFAULT_EXECUTION_AUTHORIZATION_PATH
    for path in (registration_path, inventory_path, preflight_path, authorization_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    inventory_payload = b"{}\n"
    inventory_path.write_bytes(inventory_payload)
    registration_bytes = study.canonical_json_bytes(registration)
    registration_path.write_bytes(registration_bytes)
    preregistration_commit = "c" * 40
    registration_binding = {
        "path": study.DEFAULT_REGISTRATION_PATH,
        "sha256": study.sha256_bytes(registration_bytes),
        "size_bytes": len(registration_bytes),
    }
    preflight = study._preflight(
        implementation_commit=registration["identity"]["implementation"]["commit"],
        registration_binding=registration_binding,
        seed_inventory_binding=registration["identity"]["seed_inventory"],
    )
    preflight_path.write_bytes(study.canonical_json_bytes(preflight))
    authorization = _execution_authorization(
        registration,
        registration_sha256=registration_binding["sha256"],
        commit=preregistration_commit,
    )
    authorization_path.write_bytes(study.canonical_json_bytes(authorization))
    monkeypatch.setattr(study, "_assert_clean_pushed_head", lambda _root: "d" * 40)

    def git_bytes(_root, _command, spec):
        relative = spec.split(":", 1)[1]
        return (tmp_path / relative).read_bytes()

    monkeypatch.setattr(study, "_git_bytes", git_bytes)
    monkeypatch.setattr(
        study,
        "validate_registration_evidence",
        lambda *_args, **_kwargs: ({}, inventory_path),
    )

    def fail_after_journal(*_args, **_kwargs):
        journal_path = tmp_path / study.DEFAULT_OUTPUT_DIRECTORY / "execution_journal.json"
        journal = json.loads(journal_path.read_text())
        assert journal["state"] == "started"
        raise study.SimulatorAdapterError("fixture native load failure")

    monkeypatch.setattr(study, "load_native_module", fail_after_journal)

    result = study.execute_registered(tmp_path)

    assert result["verdict"] == "study_blocked"
    assert result["reason"] == "native_module_load_failed"
    manifest = json.loads(
        (
            tmp_path
            / study.DEFAULT_OUTPUT_DIRECTORY
            / "artifact_manifest.json"
        ).read_text()
    )
    assert manifest["verdict"] == "study_blocked"


def test_cli_has_no_seed_threshold_limit_or_policy_override():
    parser = study.build_parser()

    for arguments in (
        ["execute", "--seed", "1"],
        ["execute", "--max-wall-seconds", "1"],
        ["execute", "--threshold", "1"],
        ["execute", "--policy", "other"],
    ):
        with pytest.raises(SystemExit):
            parser.parse_args(arguments)
    assert parser.parse_args(["verify"]).command == "verify"
