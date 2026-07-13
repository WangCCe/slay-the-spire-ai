import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from analysis_scripts.noncombat_exploration_evidence import (
    CANONICAL_EXPLORATION_SCHEMA_VERSION,
    ExplorationEvidenceError,
    ExplorationExportResult,
    behavior_evidence_status,
    compare_isolation_snapshots,
    evaluate_known_propensity_qualification,
    export_confirmed_exploration_samples,
    render_known_propensity_qualification_report,
)
from spirecomm.ai.noncombat_exploration import (
    CONFIG_SCHEMA_VERSION,
    ExplorationConfig,
    NonCombatExplorationController,
    build_card_reward_proposal,
    create_exploration_session_manifest,
    make_trajectory_session_id,
    sample_exploration,
)
from spirecomm.communication.action import CardRewardAction
from spirecomm.spire.screen import ScreenType


SOURCE_COMMIT = "e" * 40


def _card(name):
    return SimpleNamespace(name=name, card_id=name, price=0, upgrades=0)


def _reward_game():
    anger = _card("Anger")
    return SimpleNamespace(
        screen_type=ScreenType.CARD_REWARD,
        screen=SimpleNamespace(cards=[anger], can_skip=True, can_bowl=False),
        available_commands=["choose", "cancel", "state"],
        cancel_available=True,
        proceed_available=False,
        in_combat=False,
        floor=3,
        act=1,
        room_type="MonsterRoom",
        gold=99,
        current_hp=70,
        max_hp=80,
        deck=[_card("Strike_R")],
        relics=[],
        potions=[],
        hand=[],
        monsters=[],
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=3),
    )


def _config(tmp_path, *, seed, trace_name="exploration.jsonl"):
    return ExplorationConfig(
        schema_version=CONFIG_SCHEMA_VERSION,
        session_id="evidence-session",
        seed=seed,
        enabled_categories=("card_reward", "shop"),
        category_rates_bps={"card_reward": 1000, "shop": 1000},
        per_run_alternative_budget=2,
        trace_path=(tmp_path / trace_name).resolve(),
        manifest_path=(tmp_path / "manifest.json").resolve(),
        source_commit=SOURCE_COMMIT,
        source_path=(tmp_path / "config.json").resolve(),
    )


def _config_for_arm(tmp_path, proposal, target_action_id):
    trajectory_id = make_trajectory_session_id("evidence-session", "run-1")
    for seed in range(20_000):
        config = _config(tmp_path, seed=seed)
        selected = sample_exploration(
            config,
            proposal,
            trajectory_session_id=trajectory_id,
            decision_index=0,
        )
        if selected.selected_action_id == target_action_id:
            return config
    raise AssertionError("deterministic target arm was not found")


def _write_config_source(config):
    payload = config.to_record()
    payload.pop("source_path", None)
    Path(config.source_path).write_text(json.dumps(payload), encoding="utf-8")


def _build_session(
    tmp_path,
    *,
    arm="baseline",
    resolution="confirmed",
    isolation_hashes=None,
):
    game = _reward_game()
    current = CardRewardAction(game.screen.cards[0])
    adapter = build_card_reward_proposal(game, current)
    target = (
        adapter.proposal.baseline_action_id
        if arm == "baseline"
        else adapter.proposal.alternative_action_id
    )
    config = _config_for_arm(tmp_path, adapter.proposal, target)
    _write_config_source(config)
    if isolation_hashes is None:
        isolation_hashes = {
            r"C:\Users\test\AppData\Local\ModTheSpire\CommunicationMod\config.properties": {
                "exists": True,
                "is_file": True,
                "size": 12,
                "mtime_ns": 34,
                "sha256": "f" * 64,
                "semantic_sha256": "c" * 64,
            },
            r"D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints\rl_combat_model_ep1.pth": {
                "exists": True,
                "is_file": True,
                "size": 56,
                "mtime_ns": 78,
                "sha256": "a" * 64,
            },
        }
    manifest = create_exploration_session_manifest(
        config,
        source_clean=True,
        python_executable=r"D:\anaconda\envs\stsai\python.exe",
        command=["python", "main.py", "--agent", "optimized"],
        isolation_hashes=isolation_hashes,
    )
    controller = NonCombatExplorationController(config, clock=lambda: 1780000001.0)
    controller.begin_trajectory("run-1", started_unix=1780000000.25)
    selected = controller.consider(adapter, game)
    after = deepcopy(game)
    after.screen_type = ScreenType.COMBAT_REWARD
    after.screen = SimpleNamespace(rewards=[])
    after.available_commands = ["proceed", "state"]
    if selected.selected_action_id == adapter.proposal.baseline_action_id:
        after.deck.append(_card("Anger"))
    if resolution == "confirmed":
        controller.resolve_pending(after)
    elif resolution == "rejected":
        contradictory = deepcopy(after)
        if selected.selected_action_id == adapter.proposal.baseline_action_id:
            contradictory.deck = deepcopy(game.deck)
        else:
            contradictory.deck.append(_card("Anger"))
        controller.resolve_pending(contradictory)
    elif resolution == "unresolved":
        controller.end_trajectory()
    else:
        raise AssertionError(resolution)
    return config, manifest, selected


def _outcome(*, start=1780000000, run_file="1780000000.run", floor=20, victory=False):
    return {
        "run_file": run_file,
        "start_unix": start,
        "end_unix": start + 300,
        "victory": victory,
        "floor_reached": floor,
        "killed_by": "Gremlin Nob" if not victory else "",
        "playtime": 300,
        "ai_marked": True,
    }


def _rewrite_trace(path, mutate):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
    mutate(rows)
    Path(path).write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_confirmed_record_exports_additive_v3_exact_behavior_evidence(tmp_path):
    config, manifest, selected = _build_session(tmp_path, arm="alternative")

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
        outcomes=[_outcome(victory=True)],
        expected_pre_isolation_hashes=manifest["pre_session_isolation_hashes"],
        post_isolation_hashes=manifest["pre_session_isolation_hashes"],
        expected_source_commit=SOURCE_COMMIT,
    )

    assert result.exclusions == ()
    assert result.isolation_verified is True
    assert result.provenance_verified is True
    [sample] = result.samples
    assert sample["schema_version"] == CANONICAL_EXPLORATION_SCHEMA_VERSION
    assert sample["sample_id"] == selected.decision_id
    assert sample["trajectory_group_id"] == "run:1780000000"
    assert sample["behavior_policy_id"] == "known-propensity-epsilon-v1:evidence-session"
    assert sample["behavior_policy_commit"] == SOURCE_COMMIT
    assert sample["behavior_probability_status"] == "verified_known_propensity"
    assert sample["behavior_action_probability"] == pytest.approx(0.1)
    assert behavior_evidence_status(sample) == {
        "verified": True,
        "reason": "verified_known_propensity",
    }
    block = sample["exploration"]
    assert block["decision_id"] == selected.decision_id
    assert block["selected_arm"] == "alternative"
    assert block["selected_probability"] == {
        "numerator": 1000,
        "denominator": 10000,
        "value": 0.1,
    }
    assert block["candidate_distribution"] == [
        {
            "action_id": "card_reward:take:anger",
            "numerator": 9000,
            "denominator": 10000,
            "value": 0.9,
        },
        {
            "action_id": "card_reward:skip",
            "numerator": 1000,
            "denominator": 10000,
            "value": 0.1,
        },
    ]
    assert block["replay_status"] == "valid"
    assert block["confirmation_status"] == "confirmed"
    assert block["candidate_legality"] == "valid"
    assert block["manifest_hash"] == manifest["manifest_hash"]
    assert block["proposal_record_hash"]
    assert block["resolution_record_hash"]


def test_manifest_or_config_source_tampering_is_rejected(tmp_path):
    manifest_dir = tmp_path / "manifest"
    manifest_dir.mkdir()
    manifest_config, manifest, _selected = _build_session(manifest_dir)
    manifest["session_id"] = "tampered-session"
    manifest_config.manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(ExplorationEvidenceError, match="manifest hash mismatch"):
        export_confirmed_exploration_samples(
            manifest_config.trace_path,
            manifest_config.manifest_path,
        )

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_config, _manifest, _selected = _build_session(source_dir)
    source_config.source_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ExplorationEvidenceError, match="config file hash mismatch"):
        export_confirmed_exploration_samples(
            source_config.trace_path,
            source_config.manifest_path,
        )


def test_independent_source_and_isolation_allowlists_are_required(tmp_path):
    fingerprint = {
        "exists": True,
        "is_file": True,
        "size": 12,
        "mtime_ns": 34,
        "sha256": "f" * 64,
    }
    arbitrary_isolation = {r"D:\arbitrary\sentinel.bin": fingerprint}
    config, manifest, _selected = _build_session(
        tmp_path,
        isolation_hashes=arbitrary_isolation,
    )

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
        expected_pre_isolation_hashes=arbitrary_isolation,
        post_isolation_hashes=arbitrary_isolation,
        expected_source_commit="f" * 40,
    )

    assert result.provenance_verified is False
    assert result.isolation_verified is False
    assert "source_commit_mismatch" in result.provenance_comparison["mismatches"]
    assert "communication_mod_config_missing" in result.isolation_comparison[
        "mismatches"
    ]
    assert "combat_checkpoint_missing" in result.isolation_comparison["mismatches"]


def test_independent_pre_allows_communication_mod_startup_mtime_rewrite(tmp_path):
    config, manifest, _selected = _build_session(tmp_path)
    independent_pre = deepcopy(manifest["pre_session_isolation_hashes"])
    config_path = next(
        path for path in independent_pre if path.endswith("config.properties")
    )
    independent_pre[config_path]["mtime_ns"] += 1
    independent_pre[config_path]["sha256"] = "0" * 64

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
        expected_pre_isolation_hashes=independent_pre,
        post_isolation_hashes=manifest["pre_session_isolation_hashes"],
        expected_source_commit=SOURCE_COMMIT,
    )

    assert result.provenance_verified is True
    assert result.isolation_verified is True


def test_independent_pre_content_change_blocks_provenance_not_post_isolation(
    tmp_path,
):
    config, manifest, _selected = _build_session(tmp_path)
    independent_pre = deepcopy(manifest["pre_session_isolation_hashes"])
    config_path = next(
        path for path in independent_pre if path.endswith("config.properties")
    )
    independent_pre[config_path]["semantic_sha256"] = "0" * 64

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
        expected_pre_isolation_hashes=independent_pre,
        post_isolation_hashes=manifest["pre_session_isolation_hashes"],
        expected_source_commit=SOURCE_COMMIT,
    )

    assert result.provenance_verified is False
    assert result.provenance_comparison["mismatches"] == [
        "independent_pre_isolation_mismatch"
    ]
    assert result.isolation_verified is True


@pytest.mark.parametrize(
    "schema_version",
    ["noncombat-rl-decision-v1", "noncombat-rl-decision-v2"],
)
def test_v1_v2_samples_remain_readable_but_do_not_gain_verified_probability(
    schema_version,
):
    sample = {
        "schema_version": schema_version,
        "behavior_action_probability": None,
        "behavior_probability_status": "unknown",
    }
    before = deepcopy(sample)

    status = behavior_evidence_status(sample)

    assert status == {
        "verified": False,
        "reason": "legacy_schema_without_confirmed_exploration",
    }
    assert sample == before


@pytest.mark.parametrize(
    ("resolution", "expected_reason"),
    [
        ("rejected", "confirmation_rejected"),
        ("unresolved", "confirmation_terminal_unresolved"),
    ],
)
def test_rejected_and_unresolved_records_are_excluded(
    tmp_path, resolution, expected_reason
):
    config, _manifest, _selected = _build_session(
        tmp_path,
        arm="alternative",
        resolution=resolution,
    )

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
    )

    assert result.samples == ()
    assert [row["reason"] for row in result.exclusions] == [expected_reason]


def test_shadow_record_is_excluded_from_executable_support(tmp_path):
    config, _manifest, _selected = _build_session(tmp_path)

    def make_shadow(rows):
        proposal = rows[0]["proposal"]
        proposal["execution_eligible"] = False
        proposal["rollout_mode"] = "shadow"
        proposal["ineligibility_reason"] = "category_shadow_only"

    _rewrite_trace(config.trace_path, make_shadow)

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
    )

    assert result.samples == ()
    assert [row["reason"] for row in result.exclusions] == ["shadow_only"]
    assert result.validation_summary["eligible_proposals"] == 0


def test_replay_mismatch_and_candidate_illegality_are_explicit_exclusions(tmp_path):
    replay_dir = tmp_path / "replay"
    replay_dir.mkdir()
    replay_config, _manifest, _selected = _build_session(replay_dir)
    _rewrite_trace(
        replay_config.trace_path,
        lambda rows: rows[0]["selection"].__setitem__(
            "draw_bucket", rows[0]["selection"]["draw_bucket"] + 1
        ),
    )

    replay_result = export_confirmed_exploration_samples(
        replay_config.trace_path,
        replay_config.manifest_path,
    )

    illegal_dir = tmp_path / "illegal"
    illegal_dir.mkdir()
    illegal_config, _manifest, _selected = _build_session(illegal_dir)
    _rewrite_trace(
        illegal_config.trace_path,
        lambda rows: rows[0]["selected_candidate"].__setitem__(
            "action_id", "card_reward:not-a-candidate"
        ),
    )
    illegal_result = export_confirmed_exploration_samples(
        illegal_config.trace_path,
        illegal_config.manifest_path,
    )

    assert [row["reason"] for row in replay_result.exclusions] == ["replay_mismatch"]
    assert [row["reason"] for row in illegal_result.exclusions] == [
        "selected_candidate_illegal"
    ]


def test_probability_float_near_miss_is_not_exact_replay_evidence(tmp_path):
    config, _manifest, _selected = _build_session(tmp_path)

    def perturb_probability(rows):
        rows[0]["selection"]["distribution"][0]["value"] += 5e-13

    _rewrite_trace(config.trace_path, perturb_probability)

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
    )

    assert result.samples == ()
    assert [row["reason"] for row in result.exclusions] == ["replay_mismatch"]


@pytest.mark.parametrize(
    ("field_path", "mutate"),
    [
        (("selection", "draw_bucket"), lambda value: str(value)),
        (("selection", "draw_counter"), lambda value: float(value) + 0.9),
        (
            ("selection", "selected_probability_numerator"),
            lambda value: str(value),
        ),
        (
            ("selection", "distribution", 0, "numerator"),
            lambda value: str(value),
        ),
    ],
)
def test_replay_rejects_coercible_noninteger_json_values(
    tmp_path,
    field_path,
    mutate,
):
    config, _manifest, _selected = _build_session(tmp_path)

    def corrupt_type(rows):
        target = rows[0]
        for key in field_path[:-1]:
            target = target[key]
        key = field_path[-1]
        target[key] = mutate(target[key])

    _rewrite_trace(config.trace_path, corrupt_type)

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
    )

    assert result.samples == ()
    assert [row["reason"] for row in result.exclusions] == ["replay_mismatch"]


def test_non_monotonic_record_timestamps_are_excluded(tmp_path):
    config, _manifest, _selected = _build_session(tmp_path)

    def reverse_resolution_clock(rows):
        rows[1]["resolved_unix"] = rows[0]["proposed_unix"] - 1

    _rewrite_trace(config.trace_path, reverse_resolution_clock)

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
    )

    assert result.samples == ()
    assert [row["reason"] for row in result.exclusions] == [
        "timestamp_order_invalid"
    ]


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        ("decision_id", "decision_id_mismatch"),
        ("trajectory", "trajectory_identity_invalid"),
        ("index", "trajectory_decision_index_mismatch"),
        ("budget", "alternative_budget_history_mismatch"),
        ("policy", "behavior_policy_id_mismatch"),
    ],
)
def test_proposal_history_identity_budget_and_policy_are_replayed(
    tmp_path,
    mutation,
    expected_reason,
):
    config, _manifest, _selected = _build_session(tmp_path)

    def mutate_history(rows):
        if mutation == "decision_id":
            rows[0]["decision_id"] = "decision-" + "0" * 32
            rows[1]["decision_id"] = rows[0]["decision_id"]
        elif mutation == "trajectory":
            rows[0]["trajectory_session_id"] = ""
            rows[0]["selection"]["trajectory_session_id"] = ""
            rows[1]["trajectory_session_id"] = ""
        elif mutation == "index":
            rows[0]["decision_index"] = -1
            rows[0]["selection"]["decision_index"] = -1
        elif mutation == "budget":
            rows[0]["alternative_attempt_budget"]["used_before"] = 1
        elif mutation == "policy":
            rows[0]["behavior_policy_id"] = "unverified-policy"

    _rewrite_trace(config.trace_path, mutate_history)

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
    )

    assert result.samples == ()
    assert [row["reason"] for row in result.exclusions] == [expected_reason]


def test_duplicate_trajectory_decision_index_cannot_inflate_support(tmp_path):
    config, _manifest, _selected = _build_session(tmp_path)

    def duplicate_draw(rows):
        proposed = deepcopy(rows[0])
        resolution = deepcopy(rows[1])
        proposed["decision_id"] = "decision-" + "1" * 32
        resolution["decision_id"] = proposed["decision_id"]
        rows.extend((proposed, resolution))

    _rewrite_trace(config.trace_path, duplicate_draw)

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
    )

    assert len(result.samples) == 1
    assert [row["reason"] for row in result.exclusions] == [
        "duplicate_trajectory_decision_index"
    ]
    assert result.validation_summary["eligible_proposals"] == 2


def test_trajectory_history_stays_untrusted_after_an_index_gap(tmp_path):
    initial_game = _reward_game()
    initial_action = CardRewardAction(initial_game.screen.cards[0])
    initial_adapter = build_card_reward_proposal(initial_game, initial_action)
    config = _config_for_arm(
        tmp_path,
        initial_adapter.proposal,
        initial_adapter.proposal.baseline_action_id,
    )
    _write_config_source(config)
    create_exploration_session_manifest(
        config,
        source_clean=True,
        python_executable=r"D:\anaconda\envs\stsai\python.exe",
        command=["python", "main.py", "--agent", "optimized"],
        isolation_hashes={
            r"C:\Users\test\AppData\Local\ModTheSpire\CommunicationMod\config.properties": {
                "exists": True,
                "is_file": True,
                "size": 12,
                "mtime_ns": 34,
                "sha256": "f" * 64,
            },
            r"D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints\rl_combat_model_ep1.pth": {
                "exists": True,
                "is_file": True,
                "size": 56,
                "mtime_ns": 78,
                "sha256": "a" * 64,
            },
        },
    )
    controller = NonCombatExplorationController(
        config,
        clock=lambda: 1780000001.0,
    )
    controller.begin_trajectory("run-1", started_unix=1780000000.25)
    for _ in range(3):
        game = _reward_game()
        current = CardRewardAction(game.screen.cards[0])
        adapter = build_card_reward_proposal(game, current)
        selected = controller.consider(adapter, game)
        after = deepcopy(game)
        after.screen_type = ScreenType.COMBAT_REWARD
        after.screen = SimpleNamespace(rewards=[])
        after.available_commands = ["proceed", "state"]
        if selected.selected_action_id == adapter.proposal.baseline_action_id:
            after.deck.append(_card("Anger"))
        controller.resolve_pending(after)

    def introduce_gap(rows):
        first_proposal = next(row for row in rows if row["record_type"] == "proposed")
        first_proposal["decision_index"] = 5

    _rewrite_trace(config.trace_path, introduce_gap)

    result = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
    )

    assert result.samples == ()
    assert [row["reason"] for row in result.exclusions] == [
        "trajectory_decision_index_mismatch",
        "trajectory_history_invalid",
        "trajectory_history_invalid",
    ]


def test_outcome_join_is_conservative_for_ambiguous_or_floor_inconsistent_runs(
    tmp_path,
):
    config, _manifest, _selected = _build_session(tmp_path)

    ambiguous = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
        outcomes=[
            _outcome(),
            _outcome(start=1779999999, run_file="1779999999.run"),
        ],
    )
    floor_inconsistent = export_confirmed_exploration_samples(
        config.trace_path,
        config.manifest_path,
        outcomes=[_outcome(floor=2)],
    )

    assert ambiguous.samples[0]["trajectory_group_id"] is None
    assert ambiguous.samples[0]["outcome"]["join_status"] == "ambiguous"
    assert ambiguous.samples[0]["outcome"]["included_in_gate"] is False
    assert floor_inconsistent.samples[0]["trajectory_group_id"] is None
    assert floor_inconsistent.samples[0]["outcome"]["join_status"] == "floor_inconsistent"


def _qualification_sample(index, category, arm, *, victory=False):
    baseline_action_id = f"{category}:baseline:{index}"
    alternative_action_id = f"{category}:alternative:{index}"
    selected_action_id = (
        baseline_action_id if arm == "baseline" else alternative_action_id
    )
    selected_numerator = 9000 if arm == "baseline" else 1000
    return {
        "schema_version": CANONICAL_EXPLORATION_SCHEMA_VERSION,
        "sample_id": f"decision-{index}",
        "category": category,
        "trajectory_group_id": f"run:{index}",
        "behavior_policy_id": "known-propensity-epsilon-v1:test-session",
        "behavior_probability_status": "verified_known_propensity",
        "behavior_action_probability": selected_numerator / 10000,
        "selected_action_id": selected_action_id,
        "candidate_actions": [
            {
                "action_id": baseline_action_id,
                "available": True,
                "executable": True,
            },
            {
                "action_id": alternative_action_id,
                "available": True,
                "executable": True,
            }
        ],
        "exploration": {
            "decision_id": f"decision-{index}",
            "baseline_action_id": baseline_action_id,
            "alternative_action_id": alternative_action_id,
            "selected_arm": arm,
            "candidate_distribution": [
                {
                    "action_id": baseline_action_id,
                    "numerator": 9000,
                    "denominator": 10000,
                    "value": 0.9,
                },
                {
                    "action_id": alternative_action_id,
                    "numerator": 1000,
                    "denominator": 10000,
                    "value": 0.1,
                },
            ],
            "selected_probability": {
                "numerator": selected_numerator,
                "denominator": 10000,
                "value": selected_numerator / 10000,
            },
            "replay_status": "valid",
            "candidate_legality": "valid",
            "confirmation_status": "confirmed",
        },
        "outcome": {
            "join_status": "matched",
            "included_in_gate": True,
            "victory": victory,
            "floor_reached": 10 + (index % 5),
            "killed_by": "" if victory else "Gremlin Nob",
        },
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "distribution_total",
        "selected_probability",
        "selected_membership",
        "selected_arm",
        "behavior_float",
        "distribution_float_near_miss",
        "candidate_membership",
    ],
)
def test_behavior_evidence_status_revalidates_exact_export_fields(mutation):
    sample = _qualification_sample(1, "shop", "alternative")
    if mutation == "distribution_total":
        sample["exploration"]["candidate_distribution"][0]["numerator"] = 8000
    elif mutation == "selected_probability":
        sample["exploration"]["selected_probability"]["numerator"] = 999
    elif mutation == "selected_membership":
        sample["selected_action_id"] = "shop:not-in-distribution"
    elif mutation == "selected_arm":
        sample["exploration"]["selected_arm"] = "baseline"
    elif mutation == "behavior_float":
        sample["behavior_action_probability"] = 0.2
    elif mutation == "distribution_float_near_miss":
        sample["exploration"]["candidate_distribution"][0]["value"] += 5e-13
    elif mutation == "candidate_membership":
        sample["candidate_actions"].pop()

    assert behavior_evidence_status(sample)["verified"] is False


def test_behavior_evidence_allows_visible_nonexecutable_diagnostic_candidates():
    sample = _qualification_sample(1, "card_reward", "baseline")
    sample["candidate_actions"].append(
        {
            "action_id": "card_reward:take:diagnostic-only",
            "available": True,
            "executable": False,
        }
    )

    assert behavior_evidence_status(sample) == {
        "verified": True,
        "reason": "verified_known_propensity",
    }


def _qualification_samples():
    samples = []
    index = 0
    for category in ("card_reward", "shop"):
        for arm in ("baseline", "alternative"):
            for _ in range(5):
                samples.append(
                    _qualification_sample(
                        index,
                        category,
                        arm,
                        victory=index == 0,
                    )
                )
                index += 1
    for _ in range(5):
        samples.append(_qualification_sample(index, "card_reward", "baseline"))
        index += 1
    return samples


def _validation_summary(count=25):
    return {
        "enabled_categories": ["card_reward", "shop"],
        "eligible_proposals": count,
        "confirmed": count,
        "replay_valid": count,
        "candidate_legal": count,
        "shadow_only": 0,
    }


def test_qualification_gate_passes_only_structural_exploration_data_readiness():
    samples = _qualification_samples()

    result = evaluate_known_propensity_qualification(
        samples,
        validation_summary=_validation_summary(),
        isolation_verified=True,
        provenance_verified=True,
    )

    assert result["known_propensity_exploration_data_ready"] is True
    assert result["blocking_conditions"] == []
    assert result["metrics"]["unique_joined_trajectories"] == 25
    assert result["metrics"]["victories"] == 1
    assert result["metrics"]["category_arm_support"]["shop"] == {
        "baseline": 5,
        "alternative": 5,
    }
    assert result["ope_ready"] is False
    assert result["causal_uplift_ready"] is False
    assert result["formal_noncombat_rl_training_ready"] is False
    assert result["live_policy_promotion_ready"] is False


def test_qualification_counts_terminal_outcomes_once_per_trajectory():
    samples = _qualification_samples()
    duplicate = deepcopy(samples[0])
    duplicate["sample_id"] = "decision-duplicate"
    duplicate["exploration"]["decision_id"] = "decision-duplicate"
    samples.append(duplicate)

    result = evaluate_known_propensity_qualification(
        samples,
        validation_summary=_validation_summary(count=26),
        isolation_verified=True,
        provenance_verified=True,
    )

    assert result["known_propensity_exploration_data_ready"] is True
    assert result["metrics"]["outcome_matched_samples"] == 26
    assert result["metrics"]["unique_joined_trajectories"] == 25
    assert result["metrics"]["victories"] == 1


def test_unmatched_rows_cannot_satisfy_category_arm_support():
    samples = _qualification_samples()
    for sample in samples:
        if (
            sample["category"] == "shop"
            and sample["exploration"]["selected_arm"] == "alternative"
        ):
            exploration = sample["exploration"]
            baseline_action_id = exploration["baseline_action_id"]
            sample["selected_action_id"] = baseline_action_id
            sample["behavior_action_probability"] = 0.9
            exploration["selected_arm"] = "baseline"
            exploration["selected_probability"] = {
                "numerator": 9000,
                "denominator": 10000,
                "value": 0.9,
            }
    for index in range(5):
        unmatched = _qualification_sample(
            100 + index,
            "shop",
            "alternative",
        )
        unmatched["trajectory_group_id"] = None
        unmatched["outcome"] = {
            "join_status": "missing",
            "included_in_gate": False,
        }
        samples.append(unmatched)

    result = evaluate_known_propensity_qualification(
        samples,
        validation_summary=_validation_summary(count=30),
        isolation_verified=True,
        provenance_verified=True,
    )

    assert result["known_propensity_exploration_data_ready"] is False
    assert "insufficient_shop_alternative_support" in result[
        "blocking_conditions"
    ]
    assert result["metrics"]["unique_joined_trajectories"] == 25
    assert result["metrics"]["category_arm_support"]["shop"]["alternative"] == 0


def test_required_categories_cannot_be_removed_by_the_caller():
    for categories in ((), ("card_reward",)):
        with pytest.raises(ValueError, match="required categories"):
            evaluate_known_propensity_qualification(
                _qualification_samples(),
                validation_summary=_validation_summary(),
                isolation_verified=True,
                provenance_verified=True,
                required_categories=categories,
            )


@pytest.mark.parametrize(
    ("mutation", "expected_blocker"),
    [
        ("trajectory", "insufficient_unique_joined_trajectories"),
        ("confirmation", "confirmation_coverage_incomplete"),
        ("replay", "replay_coverage_incomplete"),
        ("legality", "candidate_legality_coverage_incomplete"),
        ("support", "insufficient_shop_alternative_support"),
        ("isolation", "isolation_not_verified"),
    ],
)
def test_qualification_gate_reports_each_blocking_dimension(mutation, expected_blocker):
    samples = _qualification_samples()
    summary = _validation_summary()
    isolation_verified = True
    if mutation == "trajectory":
        samples[-1]["trajectory_group_id"] = samples[-2]["trajectory_group_id"]
    elif mutation == "confirmation":
        summary["confirmed"] -= 1
    elif mutation == "replay":
        summary["replay_valid"] -= 1
    elif mutation == "legality":
        summary["candidate_legal"] -= 1
    elif mutation == "support":
        alternative = next(
            sample
            for sample in samples
            if sample["category"] == "shop"
            and sample["exploration"]["selected_arm"] == "alternative"
        )
        alternative["exploration"]["selected_arm"] = "baseline"
    elif mutation == "isolation":
        isolation_verified = False

    result = evaluate_known_propensity_qualification(
        samples,
        validation_summary=summary,
        isolation_verified=isolation_verified,
        provenance_verified=True,
    )

    assert result["known_propensity_exploration_data_ready"] is False
    assert expected_blocker in result["blocking_conditions"]
    assert result["ope_ready"] is False
    assert result["formal_noncombat_rl_training_ready"] is False


def test_isolation_comparison_requires_exact_path_metadata_and_hash_match():
    expected = {
        "config": {
            "exists": True,
            "is_file": True,
            "size": 12,
            "mtime_ns": 34,
            "sha256": "f" * 64,
        }
    }

    exact = compare_isolation_snapshots(expected, deepcopy(expected))
    changed = deepcopy(expected)
    changed["config"]["sha256"] = "0" * 64
    mismatch = compare_isolation_snapshots(expected, changed)

    assert exact == {"verified": True, "mismatches": []}
    assert mismatch["verified"] is False
    assert mismatch["mismatches"] == ["config:sha256_mismatch"]


def test_empty_isolation_snapshots_cannot_satisfy_the_gate():
    assert compare_isolation_snapshots({}, {}) == {
        "verified": False,
        "mismatches": ["pre_snapshot_empty"],
    }

    missing_file = {"config": {"exists": False}}
    assert compare_isolation_snapshots(missing_file, deepcopy(missing_file)) == {
        "verified": False,
        "mismatches": ["config:not_present_at_baseline"],
    }

    incomplete_file = {
        "config": {"exists": True, "is_file": True, "size": 12}
    }
    assert compare_isolation_snapshots(
        incomplete_file,
        deepcopy(incomplete_file),
    ) == {
        "verified": False,
        "mismatches": [
            "config:mtime_ns_missing_at_baseline",
            "config:sha256_missing_at_baseline",
        ],
    }


def test_qualification_report_separates_data_gate_from_all_policy_claims():
    result = evaluate_known_propensity_qualification(
        _qualification_samples(),
        validation_summary=_validation_summary(),
        isolation_verified=True,
        provenance_verified=True,
    )

    report = render_known_propensity_qualification_report(result)

    assert "Known-propensity exploration data ready: true" in report
    assert "Unique joined trajectories: 25" in report
    assert "Victories: 1" in report
    assert "Gremlin Nob" in report
    assert "OPE ready: false" in report
    assert "Causal uplift ready: false" in report
    assert "Formal non-combat RL training ready: false" in report
    assert "Live policy promotion ready: false" in report
