from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

import analysis_scripts.noncombat_current_baseline_evidence_study as predecessor
import analysis_scripts.noncombat_current_baseline_replication as replication


REPO_ROOT = Path(__file__).resolve().parents[1]
CANARY = tuple(range(60000, 60016))
HOLDOUT = tuple(range(60016, 60080))


def _binding(path: Path, *, display_path: str | None = None):
    payload = path.read_bytes()
    return {
        "path": display_path or str(path.resolve()),
        "sha256": replication.sha256_bytes(payload),
        "size_bytes": len(payload),
    }


def _identity(tmp_path: Path):
    preimplementation = replication.load_preimplementation()
    consumed = json.loads(
        (
            REPO_ROOT
            / "reports/noncombat_current_baseline_evidence_study_20260803_input.json"
        ).read_text(encoding="utf-8")
    )
    seed_inventory = tmp_path / "seed_inventory.json"
    seed_inventory.write_text("{}\n", encoding="utf-8")
    event_semantics = predecessor.reachable_event_option_semantics_identity()
    event_contract_path = event_semantics["observation_contract"]["path"]
    return {
        "adapter_provenance": consumed["identity"]["adapter_provenance"],
        "adapter_source_files": list(replication.compatibility.ADAPTER_SOURCE_FILES),
        "event_contract": _binding(
            REPO_ROOT / event_contract_path,
            display_path=event_contract_path,
        ),
        "event_semantics": event_semantics,
        "implementation": {
            "commit": "a" * 40,
            "source_files": list(replication.IMPLEMENTATION_SOURCE_FILES),
            "source_sha256": "b" * 64,
        },
        "metadata": copy.deepcopy(
            preimplementation["external_identity_expectations"]["metadata"]
        ),
        "module": copy.deepcopy(
            preimplementation["external_identity_expectations"]["module"]
        ),
        "preimplementation": {
            "path": replication.PREIMPLEMENTATION_PATH,
            "sha256": replication.EXPECTED_PREIMPLEMENTATION_SHA256,
            "size_bytes": replication.EXPECTED_PREIMPLEMENTATION_SIZE_BYTES,
        },
        "runtime": copy.deepcopy(
            preimplementation["external_identity_expectations"]["runtime"]
        ),
        "seed_inventory": _binding(
            seed_inventory,
            display_path=replication.DEFAULT_SEED_INVENTORY_PATH,
        ),
        "simulator": copy.deepcopy(
            preimplementation["external_identity_expectations"]["simulator"]
        ),
    }


def _registration(tmp_path: Path):
    return replication.build_registration(
        identity=_identity(tmp_path), canary=CANARY, holdout=HOLDOUT
    )


def _inventory(*excluded: int, commit: str = "a" * 40):
    documents = {
        "reports/fixture.json": replication.canonical_json_bytes(
            {"selected_seeds": list(excluded)}
        )
    }
    return replication.compatibility.build_seed_inventory_from_documents(
        documents, repository_commit=commit
    )


def _row(
    seed: int,
    policy_id: str,
    floor: int,
    *,
    categories=("card_reward", "event", "route", "shop"),
    support: bool = False,
):
    counts = Counter(categories)
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
        "action_sequence_sha256": replication.sha256_bytes(
            replication.canonical_json_bytes(
                [decision["action_id"] for decision in decisions]
            )
        ),
        "category_counts": {
            category: counts[category] for category in replication.TARGET_CATEGORIES
        },
        "decision_count": len(decisions),
        "decisions": decisions,
        "disposition": "declared_support_blocked" if support else "terminal",
        "floor": floor,
        "outcome": "player_loss",
        "policy_id": policy_id,
        "seed": seed,
        "support_reason": replication.DECLARED_SUPPORT_REASON if support else None,
    }
    row["trajectory_sha256"] = replication.sha256_bytes(
        replication.canonical_json_bytes(row)
    )
    return {**row, "replay_count": replication.REPLAY_COUNT}


def _stage_rows(
    seeds,
    *,
    current_floor: int,
    control_floor: int,
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
                    replication.CURRENT_POLICY_ID,
                    current_floor,
                    categories=current_categories,
                    support=seed in current_support,
                ),
                _row(
                    seed,
                    replication.CONTROL_POLICY_ID,
                    control_floor,
                    support=seed in control_support,
                ),
            ]
        )
    return rows


class FakeEnvironment:
    def __init__(self, seed, *, floor=14):
        self.seed = seed
        self.floor = floor
        self.index = 0

    def snapshot(self):
        if self.index:
            return {
                "state": {
                    "floor": self.floor,
                    "outcome": "player_loss",
                    "seed": str(self.seed),
                },
                "terminal": True,
            }
        return {
            "category": "route",
            "decision_count": 0,
            "state": {"decision_context": {}, "floor": 1, "seed": str(self.seed)},
            "terminal": False,
        }

    def legal_actions(self):
        return [
            {
                "action_id": f"route:fixture:{index}",
                "available": True,
                "category": "route",
                "kind": "fixture_action",
                "label": f"route fixture {index}",
                "raw": {},
            }
            for index in range(2)
        ]

    def step(self, action_id):
        self.index += 1
        return {"selected_action_id": action_id}


class FakeSession:
    def evaluate(self, *, snapshot, candidates, decision_index):
        candidate = candidates[1]
        return {
            "action_id": candidate["action_id"],
            "action_type": "FixtureCurrentAction",
            "category": snapshot["category"],
            "fallback_used": False,
            "input_candidates_sha256": replication.sha256_bytes(
                replication.canonical_json_bytes(candidates)
            ),
            "input_snapshot_sha256": replication.sha256_bytes(
                replication.canonical_json_bytes(snapshot)
            ),
            "policy_id": replication.CURRENT_POLICY_ID,
            "source_mutated": False,
            "tracker_enabled": False,
        }


def test_preimplementation_is_canonical_exact_and_nonempirical():
    path = REPO_ROOT / replication.PREIMPLEMENTATION_PATH
    value = json.loads(path.read_bytes())

    assert path.read_bytes() == replication.canonical_json_bytes(value)
    assert path.stat().st_size == replication.EXPECTED_PREIMPLEMENTATION_SIZE_BYTES
    assert replication.sha256_file(path) == replication.EXPECTED_PREIMPLEMENTATION_SHA256
    assert replication.load_preimplementation() == value
    assert all(flag is False for flag in value["authority"].values())
    assert value["contract"]["cohort_selection"] == {
        "canary_count": 16,
        "holdout_count": 64,
        "materialized": False,
        "search_start": 60000,
        "strategy": "first_ascending_unexcluded_integers_v1",
        "total_count": 80,
    }
    assert not (REPO_ROOT / value["output"]["directory"]).exists()


def test_preimplementation_mutation_is_rejected(tmp_path):
    value = replication.load_preimplementation()
    value["contract"]["cohort_selection"]["search_start"] = 60001
    path = tmp_path / "preimplementation.json"
    path.write_bytes(replication.canonical_json_bytes(value))

    with pytest.raises(replication.ReplicationBlocked) as exc_info:
        replication.load_preimplementation(path)

    assert exc_info.value.reason == "preimplementation_identity_mismatch"


def test_exact_historical_injury_lineage_is_accepted():
    value = replication.validate_lineage_evidence()

    assert value["planning"]["commit"] == "9c80b2c1bfeb0c017b43b07f5d5eb2a9c9cbd384"
    assert value["contract"]["old_partial_rows_authoritative"] is False


@pytest.mark.parametrize(
    ("label", "mutation", "reason"),
    [
        (
            "consumed study journal",
            lambda value: {**value, "detail": "Burn"},
            "consumed_study_terminal_identity_mismatch",
        ),
        (
            "consumed study metrics",
            lambda value: {**value, "row_count": 19},
            "consumed_study_partial_rows_mismatch",
        ),
    ],
)
def test_any_other_historical_boundary_is_not_the_exception(
    monkeypatch, label, mutation, reason
):
    original = predecessor._load_json

    def altered(path, actual_label):
        value = original(path, actual_label)
        return mutation(value) if actual_label == label else value

    monkeypatch.setattr(predecessor, "_load_json", altered)

    with pytest.raises(replication.ReplicationBlocked) as exc_info:
        replication.validate_lineage_evidence()

    assert exc_info.value.reason == reason


@pytest.mark.parametrize(
    "case",
    [
        {
            "attempt_identity": "consumed_integrated_study",
            "verdict": "study_valid_without_baseline_floor",
            "reason": None,
            "detail": None,
            "completed_row_count": 160,
            "canary_complete": True,
            "holdout_accessed": True,
        },
        {
            "attempt_identity": "consumed_integrated_study",
            "verdict": "study_blocked",
            "reason": "card_metadata_cost_invalid",
            "detail": "Burn",
            "completed_row_count": 18,
            "canary_complete": False,
            "holdout_accessed": False,
        },
        {
            "attempt_identity": "final_replication",
            "verdict": "replication_valid_with_baseline_floor",
            "reason": None,
            "detail": None,
            "completed_row_count": 160,
            "canary_complete": True,
            "holdout_accessed": True,
        },
        {
            "attempt_identity": "final_replication",
            "verdict": "replication_blocked",
            "reason": "card_metadata_cost_invalid",
            "detail": "Injury",
            "completed_row_count": 18,
            "canary_complete": False,
            "holdout_accessed": False,
        },
    ],
)
def test_complete_other_or_final_result_cannot_authorize_another_replication(case):
    assert (
        replication.classify_final_replication_eligibility(**case)
        == "baseline_lane_terminal"
    )


def test_only_exact_historical_incomplete_injury_result_permits_final_proposal():
    assert (
        replication.classify_final_replication_eligibility(
            attempt_identity="consumed_integrated_study",
            verdict="study_blocked",
            reason="card_metadata_cost_invalid",
            detail="Injury",
            completed_row_count=18,
            canary_complete=False,
            holdout_accessed=False,
        )
        == "ready_for_final_baseline_replication_proposal"
    )


def test_predecessor_policy_source_drift_blocks_lineage(monkeypatch):
    monkeypatch.setattr(replication, "hash_bound_files", lambda *_args: "0" * 64)

    with pytest.raises(replication.ReplicationBlocked) as exc_info:
        replication.validate_lineage_evidence()

    assert exc_info.value.reason == "predecessor_source_identity_mismatch"


def test_selection_is_fixed_and_skips_only_registered_exclusions():
    inventory = _inventory(60000, 60002, 60080)

    canary, holdout = replication.select_replication_cohorts(inventory)

    assert canary[:3] == (60001, 60003, 60004)
    assert len(canary) == 16
    assert len(holdout) == 64
    assert 60080 not in canary + holdout
    assert list(canary + holdout) == sorted(canary + holdout)


def test_inventory_validation_rejects_discretionary_cohort():
    inventory = _inventory(60000)
    expected_canary, expected_holdout = replication.select_replication_cohorts(
        inventory
    )

    with pytest.raises(replication.ReplicationBlocked) as exc_info:
        replication._validate_replication_inventory(
            inventory,
            implementation_commit="a" * 40,
            canary=(60000, *expected_canary[1:]),
            holdout=expected_holdout,
        )

    assert exc_info.value.reason == "replication_cohort_selection_mismatch"


def test_successor_managed_json_is_not_a_seed_source(monkeypatch):
    managed = replication.canonical_json_bytes({"cohort_seeds": [60000]})
    retained = replication.canonical_json_bytes({"evaluation_seeds": [60001]})
    documents = {
        replication.DEFAULT_REGISTRATION_PATH: managed,
        f"{replication.DEFAULT_OUTPUT_DIRECTORY}/metrics.json": managed,
        "reports/retained.json": retained,
    }
    monkeypatch.setattr(
        replication.compatibility,
        "discover_seed_documents",
        lambda _root: copy.deepcopy(documents),
    )
    monkeypatch.setattr(predecessor, "_git_text", lambda *_args: "a" * 40)

    inventory = replication.build_replication_seed_inventory(REPO_ROOT)

    assert inventory["excluded_seeds"] == [60001]
    assert replication.select_replication_cohorts(inventory)[0][0] == 60000


def test_registration_uses_new_identity_and_unchanged_contract(tmp_path):
    registration = _registration(tmp_path)

    assert registration["schema_version"] == replication.REGISTRATION_SCHEMA_VERSION
    assert registration["cohorts"] == {
        "canary": list(CANARY),
        "holdout": list(HOLDOUT),
    }
    assert registration["gates"] == predecessor.GATES
    assert registration["limits"] == predecessor.LIMITS
    assert registration["policies"] == {
        "control": replication.CONTROL_POLICY,
        "current": replication.CURRENT_POLICY,
    }
    assert registration["output"]["directory"] == replication.DEFAULT_OUTPUT_DIRECTORY


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (
            lambda value: value["authority"].__setitem__(
                "execution_authorized", True
            ),
            "authority_must_be_all_false",
        ),
        (
            lambda value: value["gates"]["holdout"].__setitem__(
                "current_mean_floor_min", 17.0
            ),
            "registration_gate_mismatch",
        ),
        (
            lambda value: value["limits"].__setitem__(
                "total_max_wall_seconds", 1801.0
            ),
            "registration_limit_mismatch",
        ),
        (
            lambda value: value["policies"]["control"].__setitem__(
                "action_selection", "last_candidate"
            ),
            "registration_policy_mismatch",
        ),
        (
            lambda value: value["cohorts"]["canary"].reverse(),
            "registration_cohort_shape_mismatch",
        ),
    ],
)
def test_registration_drift_fails_closed(tmp_path, mutation, reason):
    registration = _registration(tmp_path)
    mutation(registration)

    with pytest.raises(replication.ReplicationBlocked) as exc_info:
        replication.validate_registration(registration)

    assert exc_info.value.reason == reason


def test_contract_context_never_leaks_into_predecessor(tmp_path):
    original = {
        "canary": predecessor.CANARY_SEEDS,
        "holdout": predecessor.HOLDOUT_SEEDS,
        "registration_schema": predecessor.REGISTRATION_SCHEMA_VERSION,
        "run_study": predecessor.run_study,
    }

    replication.validate_registration(_registration(tmp_path))

    assert predecessor.CANARY_SEEDS is original["canary"]
    assert predecessor.HOLDOUT_SEEDS is original["holdout"]
    assert predecessor.REGISTRATION_SCHEMA_VERSION == original["registration_schema"]
    assert predecessor.run_study is original["run_study"]


def _authorization(registration):
    registration_bytes = replication.canonical_json_bytes(registration)
    return {
        "approval": {
            "approved": True,
            "scope": "one_canary_and_conditional_holdout_same_attempt",
            "source": "explicit_user_approval",
        },
        "authority": {
            **copy.deepcopy(replication.ALL_FALSE_AUTHORITY),
            "execution_authorized": True,
        },
        "command": list(replication.EXACT_EXECUTION_COMMAND),
        "preregistration_commit": "c" * 40,
        "registration": {
            "path": replication.DEFAULT_REGISTRATION_PATH,
            "sha256": replication.sha256_bytes(registration_bytes),
            "size_bytes": len(registration_bytes),
        },
        "schema_version": replication.EXECUTION_AUTHORIZATION_SCHEMA_VERSION,
    }


def test_execution_authorization_is_separate_and_exact(tmp_path):
    registration = _registration(tmp_path)
    authorization = _authorization(registration)

    normalized = replication.validate_execution_authorization(
        authorization,
        registration=registration,
        registration_sha256=authorization["registration"]["sha256"],
        preregistration_commit="c" * 40,
    )

    assert normalized == authorization
    assert normalized["command"][-1] == "execute"


def test_canary_and_holdout_keep_old_numeric_gates_with_new_verdicts():
    canary = _stage_rows(CANARY, current_floor=15, control_floor=15)
    holdout = _stage_rows(
        HOLDOUT,
        current_floor=18,
        control_floor=15,
        current_support=HOLDOUT[:3],
        control_support=HOLDOUT[:3],
    )

    canary_result = replication.classify_canary(canary, CANARY)
    holdout_result, draws = replication.classify_holdout(holdout, HOLDOUT)

    assert canary_result["passes"] is True
    assert canary_result["current_mean_floor"] == 15.0
    assert holdout_result["passes"] is True
    assert holdout_result["verdict"] == "replication_valid_with_baseline_floor"
    assert holdout_result["absolute_bootstrap"]["lower"] == 18.0
    assert holdout_result["paired_bootstrap"]["lower"] == 3.0
    assert len(draws["absolute_current_mean"]) == 10000


@pytest.mark.parametrize(
    "rows",
    [
        _stage_rows(CANARY, current_floor=14, control_floor=14),
        _stage_rows(CANARY, current_floor=15, control_floor=16),
        _stage_rows(
            CANARY,
            current_floor=15,
            control_floor=15,
            current_categories=("route",),
        ),
        _stage_rows(
            CANARY,
            current_floor=15,
            control_floor=15,
            current_support=CANARY[:2],
        ),
    ],
)
def test_any_canary_gate_is_terminal_for_final_replication(rows):
    classification = replication.classify_canary(rows, CANARY)

    assert classification["passes"] is False
    assert classification["verdict"] == "replication_stopped_at_canary"


def test_failed_canary_never_constructs_holdout(tmp_path):
    registration = _registration(tmp_path)
    constructed = []

    def environment_factory(seed, policy_id, replay_index):
        constructed.append((seed, policy_id, replay_index))
        return FakeEnvironment(seed, floor=14)

    result = replication.run_study(
        registration=registration,
        environment_factory=environment_factory,
        session_factory=FakeSession,
        monotonic=lambda: 0.0,
    )

    assert result["verdict"] == "replication_stopped_at_canary"
    assert result["holdout_accessed"] is False
    assert len(constructed) == replication.CANARY_POLICY_EPISODE_LIMIT
    assert not set(HOLDOUT).intersection(seed for seed, _, _ in constructed)


def test_canonical_publication_uses_replication_identity(tmp_path):
    registration = _registration(tmp_path)
    output = tmp_path / "replication-output"

    result = replication.consume_and_run(
        registration=registration,
        registration_sha256="c" * 64,
        preregistration_commit="d" * 40,
        output_directory=output,
        environment_factory=lambda seed, _policy, _replay: FakeEnvironment(seed),
        session_factory=FakeSession,
        monotonic=lambda: 0.0,
    )
    manifest = replication.verify_artifact_directory(
        registration=registration,
        registration_sha256="c" * 64,
        output_directory=output,
    )

    assert result["verdict"] == "replication_stopped_at_canary"
    assert manifest["schema_version"] == replication.MANIFEST_SCHEMA_VERSION
    assert manifest["verdict"] == result["verdict"]
    assert (output / "report.md").read_text(encoding="utf-8").startswith(
        "# Final Current Baseline Replication\n"
    )
    assert all(
        value is False
        for value in json.loads((output / "metrics.json").read_text())["authority"].values()
    )


def test_interruption_after_started_journal_is_not_retryable(tmp_path):
    registration = _registration(tmp_path)
    output = tmp_path / "replication-output"

    def interrupt(*_args):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        replication.consume_and_run(
            registration=registration,
            registration_sha256="c" * 64,
            preregistration_commit="d" * 40,
            output_directory=output,
            environment_factory=interrupt,
            session_factory=FakeSession,
        )

    assert json.loads((output / "execution_journal.json").read_text())["state"] == "started"
    with pytest.raises(replication.ReplicationBlocked) as exc_info:
        replication.consume_and_run(
            registration=registration,
            registration_sha256="c" * 64,
            preregistration_commit="d" * 40,
            output_directory=output,
            environment_factory=interrupt,
            session_factory=FakeSession,
        )
    assert exc_info.value.reason == "output_directory_already_exists"


def test_repeatable_preflight_does_not_import_native_or_create_output(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    registration_path = tmp_path / replication.DEFAULT_REGISTRATION_PATH
    preflight_path = tmp_path / replication.DEFAULT_PREFLIGHT_PATH
    registration_path.parent.mkdir(parents=True, exist_ok=True)
    registration_bytes = replication.canonical_json_bytes(registration)
    registration_path.write_bytes(registration_bytes)
    registration_binding = {
        "path": replication.DEFAULT_REGISTRATION_PATH,
        "sha256": replication.sha256_bytes(registration_bytes),
        "size_bytes": len(registration_bytes),
    }
    with replication._contract_context(CANARY, HOLDOUT):
        preflight = predecessor._preflight(
            implementation_commit=registration["identity"]["implementation"][
                "commit"
            ],
            registration_binding=registration_binding,
            seed_inventory_binding=registration["identity"]["seed_inventory"],
        )
    preflight_path.write_bytes(replication.canonical_json_bytes(preflight))
    calls = []
    monkeypatch.setattr(
        replication,
        "validate_registration_evidence",
        lambda *_args, **_kwargs: calls.append("validated"),
    )
    before = "sts_lightspeed_noncombat_adapter" in sys.modules

    first = replication.preflight_registered(tmp_path)
    second = replication.preflight_registered(tmp_path)

    assert first == second
    assert calls == ["validated", "validated"]
    assert first["verified_without_seed_access"] is True
    assert before is False
    assert "sts_lightspeed_noncombat_adapter" not in sys.modules
    assert not (tmp_path / replication.DEFAULT_OUTPUT_DIRECTORY).exists()


def test_prepare_derives_context_from_inventory_without_writing(
    monkeypatch,
):
    inventory = _inventory(60000)
    captured = {}
    monkeypatch.setattr(
        predecessor, "_assert_clean_pushed_head", lambda _root: "a" * 40
    )
    monkeypatch.setattr(
        replication, "build_replication_seed_inventory", lambda _root: inventory
    )

    def observe(_root):
        captured["canary"] = predecessor.CANARY_SEEDS
        captured["holdout"] = predecessor.HOLDOUT_SEEDS
        return {"prepared": True}

    monkeypatch.setattr(replication, "_ORIGINAL_PREPARE_REGISTRATION", observe)

    assert replication.prepare_registration(REPO_ROOT) == {"prepared": True}
    assert captured["canary"][0] == 60001
    assert len(captured["canary"]) == 16
    assert len(captured["holdout"]) == 64


def test_cli_exposes_no_seed_threshold_limit_or_policy_override():
    parser = replication.build_parser()

    for arguments in (
        ["execute", "--seed", "1"],
        ["execute", "--max-wall-seconds", "1"],
        ["execute", "--threshold", "1"],
        ["execute", "--policy", "other"],
    ):
        with pytest.raises(SystemExit):
            parser.parse_args(arguments)
    assert parser.parse_args(["prepare"]).command == "prepare"
    assert parser.parse_args(["preflight"]).command == "preflight"
    assert parser.parse_args(["verify"]).command == "verify"
