from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

import analysis_scripts.noncombat_total_event_native_compatibility as compatibility_module
from analysis_scripts.noncombat_event_option_semantics import (
    event_option_semantics_identity,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.noncombat_total_event_native_compatibility import (
    ALL_FALSE_AUTHORITY,
    COHORT_SEEDS,
    DEFAULT_OUTPUT_DIRECTORY,
    INPUT_SCHEMA_VERSION,
    MAX_DECISIONS_PER_REPLAY,
    MAX_WALL_SECONDS,
    PREDECESSOR_PATHS,
    REPLAY_COUNT,
    CompatibilityBlocked,
    assert_pushed_registration,
    build_parser,
    build_registration,
    build_seed_ledger,
    collect_native_identity,
    consume_and_run,
    load_registration,
    run_compatibility_cohort,
    validate_registration,
    validate_registration_evidence,
    validate_seed_ledger,
    verify_artifact_directory,
)


def _binding(path: str, *, sha: str = "a" * 64, size: int = 1) -> dict:
    return {"path": path, "sha256": sha, "size_bytes": size}


def _provenance() -> dict:
    semantics = event_option_semantics_identity()
    return {
        "adapter_commit": "1" * 40,
        "adapter_source_sha256": "2" * 64,
        "build": {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_policy_id": "sts_lightspeed_simple_agent_no_potions_v1",
            "compiler": "test compiler",
            "cpp_standard": 201703,
            "native_target_policy_id": "sts_lightspeed_simple_agent_target_v1",
            "pybind11_version": "3.0.2",
            "python": sys.version.split()[0],
        },
        "module_sha256": "3" * 64,
        "module_size_bytes": 123,
        "simulator_commit": semantics["simulator_commit"],
        "simulator_dirty": True,
        "simulator_source_file_count": 79,
        "simulator_source_sha256": semantics["simulator_source_sha256"],
        "submodules": {"json": "4" * 40, "pybind11": "5" * 40},
    }


def _identity(tmp_path: Path) -> dict:
    contract = event_option_semantics_identity()
    contract_path = Path(contract["observation_contract"]["path"])
    return {
        "adapter_provenance": _provenance(),
        "adapter_source_files": [
            "simulator_adapters/sts_lightspeed/CMakeLists.txt",
            "simulator_adapters/sts_lightspeed/noncombat_adapter.cpp",
        ],
        "contract": contract,
        "contract_file": _binding(
            contract_path.as_posix(),
            sha=contract["observation_contract"]["sha256"],
            size=100,
        ),
        "implementation": {
            "commit": "6" * 40,
            "source_files": [
                "analysis_scripts/noncombat_total_event_native_compatibility.py",
                "analysis_scripts/noncombat_current_policy_simulator_bridge.py",
                "analysis_scripts/noncombat_event_option_observation_contract.py",
                "analysis_scripts/noncombat_event_option_semantics.py",
                "analysis_scripts/noncombat_simulator_adapter.py",
                "spirecomm/ai/agent.py",
                "spirecomm/ai/decision/base.py",
                "spirecomm/ai/heuristics/card.py",
                "spirecomm/ai/heuristics/deck.py",
                "spirecomm/ai/heuristics/ironclad_deck.py",
                "spirecomm/ai/heuristics/ironclad_evaluator.py",
                "spirecomm/ai/heuristics/map_routing.py",
                "spirecomm/ai/priorities.py",
                "spirecomm/data/loader.py",
                "spirecomm/spire/card.py",
                "spirecomm/spire/game.py",
                "spirecomm/spire/map.py",
                "spirecomm/spire/potion.py",
                "spirecomm/spire/relic.py",
                "spirecomm/spire/screen.py",
            ],
            "source_sha256": "7" * 64,
        },
        "metadata": _binding(str((tmp_path / "items.json").resolve())),
        "module_path": str((tmp_path / "adapter.pyd").resolve()),
        "predecessors": {
            name: _binding(path) for name, path in PREDECESSOR_PATHS.items()
        },
        "runtime": {
            "executable": str(Path(sys.executable).resolve()),
            "python": sys.version.split()[0],
        },
        "seed_ledger": _binding("reports/v3_seed_ledger.json"),
        "simulator_path": str((tmp_path / "sts_lightspeed").resolve()),
    }


def _registration(tmp_path: Path) -> dict:
    return build_registration(identity=_identity(tmp_path))


def _candidate(category: str, decision_index: int, *, divergent: bool = False) -> dict:
    suffix = "divergent" if divergent else "stable"
    raw = {"slot": 0}
    kind = {
        "card_reward": "take",
        "event": "event_option",
        "route": "map_node",
        "shop": "leave",
    }[category]
    if category == "event":
        raw = {"event_id": "The Cleric", "idx1": 2, "idx2": 0}
    elif category == "route":
        raw = {"x": 0, "y": decision_index}
    return {
        "action_id": f"{category}:{suffix}:{decision_index}",
        "available": True,
        "category": category,
        "kind": kind,
        "label": f"{category} action",
        "raw": raw,
    }


class _FakeEnvironment:
    categories = ("route", "card_reward", "event", "shop")

    def __init__(self, seed: int, *, divergent: bool = False):
        self.seed = seed
        self.index = 0
        self.divergent = divergent

    def snapshot(self) -> dict:
        terminal = self.index >= len(self.categories)
        category = None if terminal else self.categories[self.index]
        context = {}
        if category == "event":
            context = {
                "event_data": 0,
                "event_id": "The Cleric",
                "event_name": "The Cleric",
            }
        return {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_control": {"history": [], "policy_id": "test"},
            "category": category,
            "decision_count": self.index,
            "schema_version": "sts-lightspeed-state-v1",
            "source_type": "sts_lightspeed_simulation",
            "state": {
                "decision_context": context,
                "floor": self.index,
                "outcome": "player_loss" if terminal else "undecided",
                "seed": str(self.seed),
            },
            "terminal": terminal,
        }

    def legal_actions(self) -> list[dict]:
        return [
            _candidate(
                self.categories[self.index],
                self.index,
                divergent=self.divergent and self.index == 1,
            )
        ]

    def step(self, action_id: str) -> dict:
        self.index += 1
        return {"selected_action_id": action_id}


class _FakeSession:
    def __init__(self, *, semantics_source: str | None = None):
        self.semantics_source = semantics_source

    def evaluate(self, *, snapshot, candidates, decision_index):
        candidate = candidates[0]
        result = {
            "action_id": candidate["action_id"],
            "action_type": "TestAction",
            "category": snapshot["category"],
            "fallback_used": False,
            "input_candidates_sha256": sha256_bytes(
                canonical_json_bytes(candidates)
            ),
            "input_snapshot_sha256": sha256_bytes(canonical_json_bytes(snapshot)),
            "policy_id": "current_optimized_ironclad_a0_conservative_snapshot_v1",
            "source_mutated": False,
            "tracker_enabled": False,
        }
        if snapshot["category"] == "event":
            source = self.semantics_source or event_option_semantics_identity()[
                "contract_id"
            ]
            result["event_semantics_source"] = source
            result["event_observation"] = {
                "current_event_id": "The Cleric",
                "current_position": 0,
                "event_data": 0,
                "semantics_source": source,
                "simulator_choice_index": 2,
                "upstream_event_id": "The Cleric",
            }
        return result


def test_registration_freezes_exact_cohort_limits_and_false_authority(tmp_path):
    registration = validate_registration(_registration(tmp_path))

    assert registration["schema_version"] == INPUT_SCHEMA_VERSION
    assert registration["cohort"]["seeds"] == list(range(7000, 7008))
    assert tuple(registration["cohort"]["seeds"]) == COHORT_SEEDS
    assert registration["cohort"]["replay_count"] == REPLAY_COUNT == 2
    assert registration["limits"] == {
        "max_decisions_per_replay": MAX_DECISIONS_PER_REPLAY,
        "max_wall_seconds": MAX_WALL_SECONDS,
    }
    assert registration["output"]["directory"] == DEFAULT_OUTPUT_DIRECTORY
    assert registration["authority"] == ALL_FALSE_AUTHORITY
    assert not any(registration["authority"].values())


@pytest.mark.parametrize(
    "mutate, reason",
    [
        (lambda value: value["cohort"]["seeds"].pop(), "cohort_mismatch"),
        (
            lambda value: value["limits"].__setitem__(
                "max_decisions_per_replay", 499
            ),
            "limits_mismatch",
        ),
        (
            lambda value: value["identity"]["adapter_provenance"]["build"].__setitem__(
                "adapter_api_version", "sts-lightspeed-noncombat-adapter-v2"
            ),
            "native_adapter_api_mismatch",
        ),
        (
            lambda value: value["identity"]["adapter_provenance"]["build"].pop(
                "pybind11_version"
            ),
            "native_build_identity_incomplete",
        ),
        (
            lambda value: value["identity"]["adapter_provenance"].__setitem__(
                "simulator_source_sha256", "0" * 64
            ),
            "native_simulator_contract_mismatch",
        ),
        (
            lambda value: value["authority"].__setitem__(
                "training_authorized", True
            ),
            "authority_must_be_all_false",
        ),
    ],
)
def test_registration_rejects_execution_contract_drift(tmp_path, mutate, reason):
    registration = _registration(tmp_path)
    mutate(registration)

    with pytest.raises(CompatibilityBlocked, match=reason):
        validate_registration(registration)


def test_registration_loader_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "registration.json"
    path.write_text(
        '{"schema_version":"first","schema_version":"second"}',
        encoding="utf-8",
    )

    with pytest.raises(CompatibilityBlocked, match="duplicate_json_key"):
        load_registration(path)


def test_cli_exposes_no_seed_replay_or_limit_override():
    parser = build_parser()

    for option in ("--seed", "--replay-count", "--max-wall-seconds"):
        with pytest.raises(SystemExit):
            parser.parse_args(["execute", option, "1"])


def test_seed_ledger_expands_prior_sets_and_keeps_new_cohort_disjoint():
    repo_root = Path(__file__).resolve().parents[1]
    ledger = validate_seed_ledger(build_seed_ledger(repo_root))

    assert len(ledger["consumed_seeds"]) == 228
    assert ledger["reserved_seeds"] == list(range(6000, 6032))
    assert ledger["candidate_seeds"] == list(COHORT_SEEDS)
    assert not (
        set(ledger["candidate_seeds"])
        & (set(ledger["consumed_seeds"]) | set(ledger["reserved_seeds"]))
    )


def test_seed_ledger_rejects_candidate_overlap():
    repo_root = Path(__file__).resolve().parents[1]
    ledger = build_seed_ledger(repo_root)
    ledger["consumed_seeds"].append(COHORT_SEEDS[0])
    ledger["consumed_seeds"].sort()

    with pytest.raises(CompatibilityBlocked, match="seed_ledger_overlap"):
        validate_seed_ledger(ledger)


def test_pushed_registration_requires_clean_tracked_head_and_exact_blob(tmp_path):
    registration_path = tmp_path / "reports" / "registration.json"
    registration_path.parent.mkdir()
    registration_path.write_bytes(b"registered bytes\n")
    head = b"f" * 40

    def git_reader(_repo, *args):
        responses = {
            ("status", "--porcelain=v1", "--untracked-files=no"): b"",
            ("rev-parse", "HEAD"): head + b"\n",
            ("rev-parse", "origin/master"): head + b"\n",
            ("show", "HEAD:reports/registration.json"): registration_path.read_bytes(),
        }
        return responses[args]

    result = assert_pushed_registration(
        registration_path=registration_path,
        repo_root=tmp_path,
        git_reader=git_reader,
    )

    assert result["preregistration_commit"] == head.decode()


def test_pushed_registration_stops_before_seed_access_on_blob_drift(tmp_path):
    registration_path = tmp_path / "registration.json"
    registration_path.write_bytes(b"working tree\n")
    head = b"e" * 40

    def git_reader(_repo, *args):
        if args == ("status", "--porcelain=v1", "--untracked-files=no"):
            return b""
        if args in (("rev-parse", "HEAD"), ("rev-parse", "origin/master")):
            return head + b"\n"
        if args == ("show", "HEAD:registration.json"):
            return b"committed bytes\n"
        raise AssertionError(args)

    with pytest.raises(CompatibilityBlocked, match="registration_blob_mismatch"):
        assert_pushed_registration(
            registration_path=registration_path,
            repo_root=tmp_path,
            git_reader=git_reader,
        )


def test_native_identity_collection_never_constructs_environment(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    module_path = tmp_path / "adapter.pyd"
    module_path.write_bytes(b"api-v3-module")
    simulator = tmp_path / "sts_lightspeed"
    (simulator / "json").mkdir(parents=True)
    (simulator / "pybind11").mkdir()
    semantics = event_option_semantics_identity()

    class BuildInfoOnlyModule:
        def build_info_json(self):
            return json.dumps(_provenance()["build"])

        def Environment(self, *_args):
            raise AssertionError("Environment must not be constructed")

    def git_text(repo, *args):
        repo = Path(repo)
        if args == ("status", "--porcelain=v1"):
            return " M src/game/GameContext.cpp"
        if args == ("rev-parse", "HEAD") and repo.name == "json":
            return "4" * 40
        if args == ("rev-parse", "HEAD") and repo.name == "pybind11":
            return "5" * 40
        if args == ("rev-parse", "HEAD"):
            return semantics["simulator_commit"]
        raise AssertionError((repo, args))

    monkeypatch.setattr(
        compatibility_module,
        "hash_compiled_simulator_sources",
        lambda _repo: (semantics["simulator_source_sha256"], 79),
    )
    monkeypatch.setattr(compatibility_module, "_git_text", git_text)
    monkeypatch.setattr(
        compatibility_module, "_verify_sources_at_commit", lambda *_args: None
    )

    identity = collect_native_identity(
        module_path=module_path,
        simulator_repo=simulator,
        repo_root=repo_root,
        native_module=BuildInfoOnlyModule(),
        adapter_commit="1" * 40,
    )

    assert identity["build"]["adapter_api_version"] == ADAPTER_API_VERSION
    assert identity["module_sha256"] == sha256_file(module_path)
    assert identity["simulator_dirty"] is True


def test_registration_evidence_recomputes_bound_seed_ledger(tmp_path, monkeypatch):
    source_repo = Path(__file__).resolve().parents[1]
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    copied_paths = {
        source["path"] for source in compatibility_module.PRIOR_SEED_SOURCES
    }
    copied_paths.update(PREDECESSOR_PATHS.values())
    contract = event_option_semantics_identity()
    contract_relative = contract["observation_contract"]["path"]
    copied_paths.add(contract_relative)
    for relative in copied_paths:
        destination = repo_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((source_repo / relative).read_bytes())
    for relative in compatibility_module.IMPLEMENTATION_SOURCE_FILES:
        destination = repo_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(f"bound source: {relative}\n", encoding="utf-8")

    def actual_binding(path: Path, display: str) -> dict:
        return {
            "path": display,
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }

    metadata_path = tmp_path / "items.json"
    metadata_path.write_text(
        json.dumps({"cards": [], "potions": [], "relics": []}),
        encoding="utf-8",
    )
    module_path = tmp_path / "adapter.pyd"
    module_path.write_bytes(b"registered-api-v3-module")
    ledger_path = repo_root / "reports" / "seed_ledger.json"
    ledger_path.write_bytes(canonical_json_bytes(build_seed_ledger(repo_root)))
    ledger_relative = ledger_path.relative_to(repo_root).as_posix()
    contract_path = repo_root / contract_relative
    provenance = _provenance()
    provenance["module_sha256"] = sha256_file(module_path)
    provenance["module_size_bytes"] = module_path.stat().st_size
    identity = {
        "adapter_provenance": provenance,
        "adapter_source_files": list(compatibility_module.ADAPTER_SOURCE_FILES),
        "contract": contract,
        "contract_file": actual_binding(contract_path, contract_relative),
        "implementation": {
            "commit": "6" * 40,
            "source_files": list(
                compatibility_module.IMPLEMENTATION_SOURCE_FILES
            ),
            "source_sha256": compatibility_module.hash_bound_files(
                repo_root, compatibility_module.IMPLEMENTATION_SOURCE_FILES
            ),
        },
        "metadata": actual_binding(metadata_path, str(metadata_path.resolve())),
        "module_path": str(module_path.resolve()),
        "predecessors": {
            name: actual_binding(repo_root / path, path)
            for name, path in PREDECESSOR_PATHS.items()
        },
        "runtime": {
            "executable": str(Path(sys.executable).resolve()),
            "python": sys.version.split()[0],
        },
        "seed_ledger": actual_binding(ledger_path, ledger_relative),
        "simulator_path": str((tmp_path / "sts_lightspeed").resolve()),
    }
    registration = build_registration(identity=identity)
    monkeypatch.setattr(
        compatibility_module, "_verify_sources_at_commit", lambda *_args: None
    )

    ledger, metadata = validate_registration_evidence(registration, repo_root)

    assert ledger["candidate_seeds"] == list(COHORT_SEEDS)
    assert metadata.path == metadata_path.resolve()


def test_cohort_runs_only_registered_seeds_twice_and_passes_four_categories(tmp_path):
    registration = _registration(tmp_path)
    calls = []

    def factory(seed):
        calls.append(seed)
        return _FakeEnvironment(seed)

    result = run_compatibility_cohort(
        registration=registration,
        environment_factory=factory,
        session_factory=_FakeSession,
    )

    assert result["status"] == "passed"
    assert result["verdict"] == "total_event_native_compatibility_passed"
    assert result["category_counts"] == {
        "card_reward": 8,
        "event": 8,
        "route": 8,
        "shop": 8,
    }
    assert calls == [seed for seed in COHORT_SEEDS for _ in range(REPLAY_COUNT)]
    assert all(row["replay_count"] == 2 for row in result["rows"])


def test_cohort_preserves_first_nondeterministic_blocker(tmp_path):
    registration = _registration(tmp_path)
    calls = 0

    def factory(seed):
        nonlocal calls
        calls += 1
        return _FakeEnvironment(seed, divergent=(calls == 2))

    result = run_compatibility_cohort(
        registration=registration,
        environment_factory=factory,
        session_factory=_FakeSession,
    )

    assert result["status"] == "failed"
    assert result["reason"] == "trajectory_nondeterministic"
    assert result["verdict"] == "total_event_native_compatibility_failed"
    assert result["rows"] == []


def test_cohort_rejects_inline_event_semantics_source(tmp_path):
    result = run_compatibility_cohort(
        registration=_registration(tmp_path),
        environment_factory=_FakeEnvironment,
        session_factory=lambda: _FakeSession(semantics_source="inline_v2"),
    )

    assert result["status"] == "failed"
    assert result["reason"] == "event_semantics_source_mismatch"


def test_cohort_rejects_reported_policy_input_hash_drift(tmp_path):
    class BadHashSession(_FakeSession):
        def evaluate(self, **kwargs):
            result = super().evaluate(**kwargs)
            result["input_snapshot_sha256"] = "0" * 64
            return result

    result = run_compatibility_cohort(
        registration=_registration(tmp_path),
        environment_factory=_FakeEnvironment,
        session_factory=BadHashSession,
    )

    assert result["status"] == "failed"
    assert result["reason"] == "policy_input_hash_mismatch"


def test_cohort_rejects_event_current_position_drift(tmp_path):
    class BadPositionSession(_FakeSession):
        def evaluate(self, **kwargs):
            result = super().evaluate(**kwargs)
            if result["category"] == "event":
                result["event_observation"]["current_position"] = 1
            return result

    result = run_compatibility_cohort(
        registration=_registration(tmp_path),
        environment_factory=_FakeEnvironment,
        session_factory=BadPositionSession,
    )

    assert result["status"] == "failed"
    assert result["reason"] == "event_observation_mapping_invalid"


def test_journal_consumes_whole_cohort_before_first_environment(tmp_path):
    registration = _registration(tmp_path)
    output_dir = tmp_path / "output"

    def factory(seed):
        journal = json.loads(
            (output_dir / "execution_journal.json").read_text(encoding="utf-8")
        )
        assert journal["status"] == "started"
        assert journal["cohort_consumed"] is True
        assert journal["seeds"] == list(COHORT_SEEDS)
        return _FakeEnvironment(seed)

    result = consume_and_run(
        registration=registration,
        registration_sha256="8" * 64,
        preregistration_commit="9" * 40,
        output_dir=output_dir,
        environment_factory=factory,
        session_factory=_FakeSession,
        utc_now=lambda: "2026-08-03T00:00:00Z",
    )

    journal = json.loads(
        (output_dir / "execution_journal.json").read_text(encoding="utf-8")
    )
    assert result["status"] == "passed"
    assert journal["status"] == "finalized"
    assert journal["verdict"] == "total_event_native_compatibility_passed"


def test_started_journal_survives_crash_and_prohibits_retry(tmp_path):
    registration = _registration(tmp_path)
    output_dir = tmp_path / "output"

    def crash(_seed):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        consume_and_run(
            registration=registration,
            registration_sha256="8" * 64,
            preregistration_commit="9" * 40,
            output_dir=output_dir,
            environment_factory=crash,
            session_factory=_FakeSession,
            utc_now=lambda: "2026-08-03T00:00:00Z",
        )

    journal_path = output_dir / "execution_journal.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    assert journal["status"] == "started"
    assert journal["cohort_consumed"] is True

    with pytest.raises(CompatibilityBlocked, match="cohort_already_consumed"):
        consume_and_run(
            registration=registration,
            registration_sha256="8" * 64,
            preregistration_commit="9" * 40,
            output_dir=output_dir,
            environment_factory=_FakeEnvironment,
            session_factory=_FakeSession,
            utc_now=lambda: "2026-08-03T00:01:00Z",
        )


def test_published_result_recomputes_without_native_module(tmp_path):
    registration = _registration(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_bytes(canonical_json_bytes(registration))
    output_dir = tmp_path / "output"
    consume_and_run(
        registration=registration,
        registration_sha256=sha256_bytes(registration_path.read_bytes()),
        preregistration_commit="9" * 40,
        output_dir=output_dir,
        environment_factory=_FakeEnvironment,
        session_factory=_FakeSession,
        utc_now=lambda: "2026-08-03T00:00:00Z",
    )

    manifest = verify_artifact_directory(
        output_dir=output_dir,
        registration_path=registration_path,
    )

    assert manifest["verdict"] == "total_event_native_compatibility_passed"
    assert not any(manifest["authority"].values())


def test_no_native_verifier_rejects_coherent_inventory_tamper(tmp_path):
    registration = _registration(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_bytes(canonical_json_bytes(registration))
    output_dir = tmp_path / "output"
    consume_and_run(
        registration=registration,
        registration_sha256=sha256_bytes(registration_path.read_bytes()),
        preregistration_commit="9" * 40,
        output_dir=output_dir,
        environment_factory=_FakeEnvironment,
        session_factory=_FakeSession,
        utc_now=lambda: "2026-08-03T00:00:00Z",
    )
    metrics_path = output_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["category_counts"]["shop"] = 0
    metrics_path.write_bytes(canonical_json_bytes(metrics))

    with pytest.raises(CompatibilityBlocked, match="artifact_hash_mismatch"):
        verify_artifact_directory(
            output_dir=output_dir,
            registration_path=registration_path,
        )


def test_no_native_verifier_recomputes_rows_not_only_manifest_hashes(tmp_path):
    registration = _registration(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_bytes(canonical_json_bytes(registration))
    output_dir = tmp_path / "output"
    consume_and_run(
        registration=registration,
        registration_sha256=sha256_bytes(registration_path.read_bytes()),
        preregistration_commit="9" * 40,
        output_dir=output_dir,
        environment_factory=_FakeEnvironment,
        session_factory=_FakeSession,
        utc_now=lambda: "2026-08-03T00:00:00Z",
    )
    rows_path = output_dir / "trajectory_rows.json"
    trajectories = json.loads(rows_path.read_text(encoding="utf-8"))
    trajectories["execution"]["rows"][0]["decision_count"] += 1
    rows_bytes = canonical_json_bytes(trajectories)
    rows_path.write_bytes(rows_bytes)
    manifest_path = output_dir / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_bindings"]["trajectory_rows.json"].update(
        {"sha256": sha256_bytes(rows_bytes), "size_bytes": len(rows_bytes)}
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest))

    with pytest.raises(
        CompatibilityBlocked, match="execution_row_decision_count_mismatch"
    ):
        verify_artifact_directory(
            output_dir=output_dir,
            registration_path=registration_path,
        )
