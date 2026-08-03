from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import analysis_scripts.noncombat_reachable_event_native_compatibility as module
from analysis_scripts.noncombat_reachable_event_native_compatibility import (
    ALL_FALSE_AUTHORITY,
    CANONICAL_ARTIFACT_NAMES,
    COHORT_SIZE,
    DEFAULT_SEED_INVENTORY_PATH,
    DEFAULT_SEED_LEDGER_PATH,
    CompatibilityBlocked,
    assert_pushed_registration,
    build_parser,
    build_registration,
    build_seed_inventory_from_documents,
    build_seed_ledger,
    collect_native_identity,
    consume_and_run,
    discover_seed_documents,
    reachable_event_option_semantics_identity,
    run_compatibility_cohort,
    select_untouched_cohort,
    validate_registration,
    validate_seed_inventory,
    validate_seed_ledger,
    verify_artifact_directory,
    verify_predecessor_bindings,
)
from analysis_scripts.noncombat_simulator_adapter import canonical_json_bytes, sha256_bytes


def _binding(path: str, payload: bytes = b"{}") -> dict:
    return {
        "path": path,
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
    }


def _provenance() -> dict:
    semantics = reachable_event_option_semantics_identity()
    return {
        "adapter_commit": "a" * 40,
        "adapter_source_sha256": "b" * 64,
        "build": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "baseline_policy_id": "sts_lightspeed_simple_agent_no_potions_v1",
            "compiler": "test compiler",
            "cpp_standard": 201703,
            "native_target_policy_id": "sts_lightspeed_simple_agent_target_v1",
            "python": "3.10.18",
        },
        "module_sha256": "c" * 64,
        "module_size_bytes": 100,
        "simulator_commit": semantics["simulator_commit"],
        "simulator_dirty": True,
        "simulator_source_file_count": 12,
        "simulator_source_sha256": semantics["simulator_source_sha256"],
        "submodules": {"json": "d" * 40, "pybind11": "e" * 40},
    }


def _inventory() -> dict:
    documents = {
        "reports/prior_input.json": canonical_json_bytes(
            {
                "study": {
                    "cohorts": {
                        "compatibility_seeds": [7000, 7001],
                        "train_seeds": [1, 2],
                    }
                }
            }
        ),
        "reports/prior_seed_ledger.json": canonical_json_bytes(
            {"reserved_final_test_seeds": [6000], "mystery_seed": 42}
        ),
    }
    return build_seed_inventory_from_documents(
        documents, repository_commit="1" * 40
    )


def _identity(tmp_path: Path, inventory: dict, ledger: dict) -> dict:
    contract = reachable_event_option_semantics_identity()
    contract_relative = contract["observation_contract"]["path"]
    contract_bytes = (
        Path(__file__).resolve().parents[1] / contract_relative
    ).read_bytes()
    inventory_bytes = canonical_json_bytes(inventory)
    ledger_bytes = canonical_json_bytes(ledger)
    metadata = tmp_path / "items.json"
    metadata.write_bytes(b"{}")
    module_path = tmp_path / "adapter.pyd"
    module_path.write_bytes(b"native")
    predecessors = {
        name: _binding(path)
        for name, path in module.PREDECESSOR_PATHS.items()
    }
    return {
        "adapter_provenance": _provenance(),
        "adapter_source_files": list(module.ADAPTER_SOURCE_FILES),
        "contract": contract,
        "contract_file": _binding(contract_relative, contract_bytes),
        "implementation": {
            "commit": "1" * 40,
            "source_files": list(module.IMPLEMENTATION_SOURCE_FILES),
            "source_sha256": "2" * 64,
        },
        "metadata": _binding(str(metadata.resolve()), metadata.read_bytes()),
        "module_path": str(module_path.resolve()),
        "predecessors": predecessors,
        "runtime": {
            "executable": str(Path(module.sys.executable).resolve()),
            "python": module.sys.version.split()[0],
        },
        "seed_inventory": _binding(
            DEFAULT_SEED_INVENTORY_PATH, inventory_bytes
        ),
        "seed_ledger": _binding(DEFAULT_SEED_LEDGER_PATH, ledger_bytes),
        "simulator_path": str(tmp_path.resolve()),
    }


def _registration(tmp_path: Path):
    inventory = _inventory()
    seeds = select_untouched_cohort(inventory)
    ledger = build_seed_ledger(inventory=inventory, seeds=seeds)
    registration = build_registration(
        identity=_identity(tmp_path, inventory, ledger), seeds=seeds
    )
    return registration, inventory, ledger


def _candidate(category: str, decision_index: int) -> dict:
    raw = {"slot": decision_index}
    if category == "event":
        raw = {"event_id": "Scrap Ooze", "idx1": 2, "idx2": 0}
    return {
        "action_id": f"{category}:action:{decision_index}",
        "available": True,
        "category": category,
        "kind": "event_option" if category == "event" else "test_action",
        "label": f"{category} candidate",
        "raw": raw,
    }


class _FakeEnvironment:
    categories = ("route", "shop", "event", "card_reward")

    def __init__(self, seed: int, *, divergent: bool = False):
        self.seed = seed
        self.index = 0
        self.divergent = divergent

    def snapshot(self):
        terminal = self.index >= len(self.categories)
        category = None if terminal else self.categories[self.index]
        context = {}
        if category == "event":
            context = {
                "event_data": 3,
                "event_id": "Scrap Ooze",
                "event_name": "Scrap Ooze",
            }
        return {
            "category": category,
            "decision_count": self.index,
            "state": {
                "decision_context": context,
                "floor": 4,
                "outcome": "player_loss" if terminal else "undecided",
                "seed": str(self.seed),
            },
            "terminal": terminal,
        }

    def legal_actions(self):
        return [_candidate(self.categories[self.index], self.index)]

    def step(self, action_id):
        self.index += 1
        selected = action_id
        if self.divergent and self.index == 1:
            selected = f"{action_id}:drift"
        return {"selected_action_id": selected}


class _FakeSession:
    def evaluate(self, *, snapshot, candidates, decision_index):
        candidate = candidates[0]
        result = {
            "action_id": candidate["action_id"],
            "action_type": "FakeAction",
            "category": snapshot["category"],
            "event_semantics_source": "not_applicable",
            "fallback_used": False,
            "input_candidates_sha256": sha256_bytes(
                canonical_json_bytes(candidates)
            ),
            "input_snapshot_sha256": sha256_bytes(
                canonical_json_bytes(snapshot)
            ),
            "policy_id": module.POLICY_ID,
            "source_mutated": False,
            "tracker_enabled": False,
        }
        if snapshot["category"] == "event":
            action_id = candidate["action_id"]
            result.update(
                {
                    "event_semantics_source": (
                        "sts_lightspeed_reachable_event_observation_v3"
                    ),
                    "event_observation": {
                        "current_event_id": "Scrap Ooze",
                        "current_position": 0,
                        "event_data": 3,
                        "selected_action_id": action_id,
                        "semantics_source": (
                            "sts_lightspeed_reachable_event_observation_v3"
                        ),
                        "simulator_choice_index": 2,
                        "upstream_event_id": "Scrap Ooze",
                    },
                }
            )
        return result


def test_seed_inventory_discovers_nested_paths_and_excludes_ambiguity():
    inventory = validate_seed_inventory(_inventory())

    rows = {
        (row["seed"], row["role"], row["json_path"])
        for row in inventory["rows"]
    }
    assert (7000, "compatibility", "study.cohorts.compatibility_seeds[0]") in rows
    assert (1, "training", "study.cohorts.train_seeds[0]") in rows
    assert (6000, "reserved", "reserved_final_test_seeds[0]") in rows
    assert (42, "ambiguous", "mystery_seed") in rows
    assert inventory["excluded_seeds"] == [1, 2, 42, 6000, 7000, 7001]


def test_seed_inventory_rejects_duplicate_json_keys():
    documents = {"reports/bad_input.json": b'{"train_seeds":[1],"train_seeds":[2]}'}

    with pytest.raises(CompatibilityBlocked, match="seed_source_duplicate_key"):
        build_seed_inventory_from_documents(
            documents, repository_commit="1" * 40
        )


def test_seed_document_discovery_uses_only_tracked_seed_json(tmp_path, monkeypatch):
    tracked = tmp_path / "reports" / "tracked_input.json"
    irrelevant = tmp_path / "reports" / "irrelevant.json"
    untracked = tmp_path / "reports" / "untracked_input.json"
    managed = tmp_path / module.DEFAULT_REGISTRATION_PATH
    for path, payload in (
        (tracked, b'{"validation_seeds":[101]}'),
        (irrelevant, b'{"count":102}'),
        (untracked, b'{"training_seeds":[103]}'),
        (managed, b'{"compatibility_seeds":[104]}'),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    monkeypatch.setattr(
        module,
        "_git_text",
        lambda _root, *args: "\n".join(
            (
                "reports/tracked_input.json",
                "reports/irrelevant.json",
                module.DEFAULT_REGISTRATION_PATH,
            )
        ),
    )

    documents = discover_seed_documents(tmp_path)

    assert documents == {
        "reports/tracked_input.json": tracked.read_bytes(),
    }


def test_seed_selection_and_ledger_reject_overlap():
    inventory = _inventory()
    seeds = select_untouched_cohort(inventory)

    assert len(seeds) == COHORT_SIZE
    assert seeds == sorted(set(seeds))
    assert not set(seeds).intersection(inventory["excluded_seeds"])
    ledger = validate_seed_ledger(
        build_seed_ledger(inventory=inventory, seeds=seeds)
    )
    assert ledger["cohort_seeds"] == seeds
    drifted = copy.deepcopy(ledger)
    drifted["cohort_seeds"][0] = 7000
    with pytest.raises(CompatibilityBlocked, match="seed_ledger_candidate_overlap"):
        validate_seed_ledger(drifted, inventory=inventory)

    shifted = copy.deepcopy(ledger)
    shifted["cohort_seeds"] = [seed + 100 for seed in seeds]
    with pytest.raises(CompatibilityBlocked, match="seed_ledger_selection_mismatch"):
        validate_seed_ledger(shifted, inventory=inventory)


def test_registration_freezes_limits_identity_and_false_authority(tmp_path):
    registration, _, _ = _registration(tmp_path)

    normalized = validate_registration(registration)

    assert normalized["authority"] == ALL_FALSE_AUTHORITY
    assert normalized["cohort"]["replay_count"] == 2
    assert len(normalized["cohort"]["seeds"]) == COHORT_SIZE
    assert normalized["limits"] == {
        "max_decisions_per_replay": 500,
        "max_wall_seconds": 120.0,
    }
    assert normalized["output"]["artifact_names"] == list(
        CANONICAL_ARTIFACT_NAMES
    )


def test_v3_registration_rejects_predecessor_semantic_identity(tmp_path):
    registration, _, _ = _registration(tmp_path)
    registration["identity"]["contract"] = module.event_option_semantics_identity()

    with pytest.raises(CompatibilityBlocked, match="event_contract_identity_mismatch"):
        validate_registration(registration)


def test_predecessor_bindings_fail_on_byte_drift(tmp_path):
    registration, _, _ = _registration(tmp_path)
    for name, relative in module.PREDECESSOR_PATHS.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"{}")

    verify_predecessor_bindings(registration, tmp_path)
    first = tmp_path / next(iter(module.PREDECESSOR_PATHS.values()))
    first.write_bytes(b"drift")

    with pytest.raises(CompatibilityBlocked, match="predecessor_binding_mismatch"):
        verify_predecessor_bindings(registration, tmp_path)


def test_build_only_identity_collection_never_constructs_environment(
    tmp_path, monkeypatch
):
    class FakeModule:
        def build_info_json(self):
            return json.dumps(
                {
                    "adapter_api_version": (
                        "sts-lightspeed-noncombat-adapter-v3"
                    ),
                    "baseline_policy_id": (
                        "sts_lightspeed_simple_agent_no_potions_v1"
                    ),
                    "compiler": "test",
                    "cpp_standard": 201703,
                    "native_target_policy_id": (
                        "sts_lightspeed_simple_agent_target_v1"
                    ),
                }
            )

        def Environment(self, *_args):
            raise AssertionError("environment constructed during discovery")

    module_path = tmp_path / "adapter.pyd"
    module_path.write_bytes(b"native")
    monkeypatch.setattr(module.predecessor, "collect_native_identity", lambda **kwargs: _provenance())

    identity = collect_native_identity(
        module_path=module_path,
        simulator_repo=tmp_path,
        repo_root=tmp_path,
        native_module=FakeModule(),
        adapter_commit="1" * 40,
    )

    assert identity == _provenance()


def test_pushed_registration_requires_exact_registration_and_ledger_blobs(
    tmp_path, monkeypatch
):
    registration, inventory, ledger = _registration(tmp_path)
    registration_path = tmp_path / "registration.json"
    inventory_path = tmp_path / DEFAULT_SEED_INVENTORY_PATH
    ledger_path = tmp_path / DEFAULT_SEED_LEDGER_PATH
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    registration_path.write_bytes(canonical_json_bytes(registration))
    inventory_path.write_bytes(canonical_json_bytes(inventory))
    ledger_path.write_bytes(canonical_json_bytes(ledger))
    monkeypatch.setattr(
        module,
        "_git_text",
        lambda _root, *args: "" if args[0] == "status" else "1" * 40,
    )
    blobs = {
        "registration.json": registration_path.read_bytes(),
        DEFAULT_SEED_INVENTORY_PATH: inventory_path.read_bytes(),
        DEFAULT_SEED_LEDGER_PATH: ledger_path.read_bytes(),
    }
    monkeypatch.setattr(
        module,
        "_git_bytes",
        lambda _root, _command, spec: blobs[spec.split(":", 1)[1]],
    )

    result = assert_pushed_registration(
        registration_path=registration_path,
        repo_root=tmp_path,
    )
    assert result["preregistration_commit"] == "1" * 40

    blobs[DEFAULT_SEED_LEDGER_PATH] = b"drift"
    with pytest.raises(CompatibilityBlocked, match="pushed_seed_ledger_mismatch"):
        assert_pushed_registration(
            registration_path=registration_path,
            repo_root=tmp_path,
        )


def test_cli_has_no_seed_replay_or_limit_override():
    help_text = build_parser().format_help()

    for forbidden in ("--seed", "--replay", "--max-decisions", "--max-wall"):
        assert forbidden not in help_text


def test_cohort_runs_registered_seeds_twice_and_covers_all_categories(tmp_path):
    registration, _, _ = _registration(tmp_path)
    calls = []

    def environment_factory(seed):
        calls.append(seed)
        return _FakeEnvironment(seed)

    result = run_compatibility_cohort(
        registration=registration,
        environment_factory=environment_factory,
        session_factory=_FakeSession,
        monotonic=lambda: 0.0,
    )

    assert result["status"] == "passed"
    assert result["verdict"] == "reachable_event_native_compatibility_passed"
    assert calls == [seed for seed in registration["cohort"]["seeds"] for _ in range(2)]
    assert all(count > 0 for count in result["category_counts"].values())
    event = result["rows"][0]["event_identities"][0]
    assert event["selected_action_id"].startswith("event:action")


def test_cohort_preserves_first_structural_blocker(tmp_path):
    registration, _, _ = _registration(tmp_path)

    result = run_compatibility_cohort(
        registration=registration,
        environment_factory=lambda seed: _FakeEnvironment(seed, divergent=True),
        session_factory=_FakeSession,
        monotonic=lambda: 0.0,
    )

    assert result["status"] == "failed"
    assert result["reason"] == "transition_action_mismatch"
    assert result["rows"] == []


def test_journal_consumes_whole_cohort_before_first_environment(tmp_path):
    registration, _, _ = _registration(tmp_path)
    output = tmp_path / registration["output"]["directory"]

    def environment_factory(seed):
        journal = json.loads((output / "execution_journal.json").read_text())
        assert journal["status"] == "started"
        assert journal["consumed_seeds"] == registration["cohort"]["seeds"]
        return _FakeEnvironment(seed)

    result = consume_and_run(
        registration=registration,
        registration_sha256="f" * 64,
        preregistration_commit="1" * 40,
        output_directory=output,
        environment_factory=environment_factory,
        session_factory=_FakeSession,
        monotonic=lambda: 0.0,
    )

    assert result["status"] == "passed"
    assert json.loads((output / "execution_journal.json").read_text())[
        "status"
    ] == "finalized"


def test_started_journal_survives_interrupt_and_blocks_retry(tmp_path):
    registration, _, _ = _registration(tmp_path)
    output = tmp_path / registration["output"]["directory"]

    with pytest.raises(KeyboardInterrupt):
        consume_and_run(
            registration=registration,
            registration_sha256="f" * 64,
            preregistration_commit="1" * 40,
            output_directory=output,
            environment_factory=lambda _seed: (_ for _ in ()).throw(
                KeyboardInterrupt()
            ),
            session_factory=_FakeSession,
            monotonic=lambda: 0.0,
        )

    journal = json.loads((output / "execution_journal.json").read_text())
    assert journal["status"] == "started"
    with pytest.raises(
        CompatibilityBlocked, match="output_directory_already_exists"
    ):
        consume_and_run(
            registration=registration,
            registration_sha256="f" * 64,
            preregistration_commit="1" * 40,
            output_directory=output,
            environment_factory=_FakeEnvironment,
            session_factory=_FakeSession,
            monotonic=lambda: 0.0,
        )


def test_existing_empty_output_directory_blocks_consumption(tmp_path):
    registration, _, _ = _registration(tmp_path)
    output = tmp_path / registration["output"]["directory"]
    output.mkdir(parents=True)

    with pytest.raises(
        CompatibilityBlocked, match="output_directory_already_exists"
    ):
        consume_and_run(
            registration=registration,
            registration_sha256="f" * 64,
            preregistration_commit="1" * 40,
            output_directory=output,
            environment_factory=lambda _seed: pytest.fail(
                "environment constructed for an existing output directory"
            ),
            session_factory=_FakeSession,
            monotonic=lambda: 0.0,
        )
    assert not (output / "execution_journal.json").exists()


def test_no_native_verifier_recomputes_and_rejects_tamper(tmp_path):
    registration, _, _ = _registration(tmp_path)
    output = tmp_path / registration["output"]["directory"]
    consume_and_run(
        registration=registration,
        registration_sha256="f" * 64,
        preregistration_commit="1" * 40,
        output_directory=output,
        environment_factory=_FakeEnvironment,
        session_factory=_FakeSession,
        monotonic=lambda: 0.0,
    )

    manifest = verify_artifact_directory(
        registration=registration,
        registration_sha256="f" * 64,
        output_directory=output,
    )
    assert manifest["verdict"] == "reachable_event_native_compatibility_passed"

    metrics_path = output / "metrics.json"
    metrics = json.loads(metrics_path.read_text())
    metrics["category_counts"]["event"] += 1
    metrics_path.write_bytes(canonical_json_bytes(metrics))
    with pytest.raises(CompatibilityBlocked, match="artifact_recomputation_mismatch"):
        verify_artifact_directory(
            registration=registration,
            registration_sha256="f" * 64,
            output_directory=output,
        )


def test_execution_validation_recomputes_trajectory_rows(tmp_path):
    registration, _, _ = _registration(tmp_path)
    result = run_compatibility_cohort(
        registration=registration,
        environment_factory=_FakeEnvironment,
        session_factory=_FakeSession,
        monotonic=lambda: 0.0,
    )
    result["rows"][0]["decisions"][0]["action_id"] = "coherent:tamper"

    with pytest.raises(CompatibilityBlocked, match="trajectory_hash_mismatch"):
        module._validate_execution_result(result, registration)
