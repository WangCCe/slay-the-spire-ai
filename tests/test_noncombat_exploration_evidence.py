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


def _build_session(tmp_path, *, arm="baseline", resolution="confirmed"):
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
    manifest = create_exploration_session_manifest(
        config,
        source_clean=True,
        python_executable=r"D:\anaconda\envs\stsai\python.exe",
        command=["python", "main.py", "--agent", "optimized"],
        isolation_hashes={
            "communication_mod_config": {
                "exists": True,
                "is_file": True,
                "size": 12,
                "mtime_ns": 34,
                "sha256": "f" * 64,
            }
        },
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
        post_isolation_hashes=manifest["pre_session_isolation_hashes"],
    )

    assert result.exclusions == ()
    assert result.isolation_verified is True
    [sample] = result.samples
    assert sample["schema_version"] == CANONICAL_EXPLORATION_SCHEMA_VERSION
    assert sample["sample_id"] == selected.decision_id
    assert sample["trajectory_group_id"] == "run:1780000000"
    assert sample["behavior_policy_id"] == "known-propensity-epsilon-v1:evidence-session"
    assert sample["behavior_policy_commit"] == SOURCE_COMMIT
    assert sample["behavior_probability_status"] == "verified_known_propensity"
    assert sample["behavior_action_probability"] == pytest.approx(0.1)
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
    return {
        "schema_version": CANONICAL_EXPLORATION_SCHEMA_VERSION,
        "sample_id": f"decision-{index}",
        "category": category,
        "trajectory_group_id": f"run:{index}",
        "behavior_probability_status": "verified_known_propensity",
        "behavior_action_probability": 0.9 if arm == "baseline" else 0.1,
        "selected_action_id": f"{category}:{arm}:{index}",
        "candidate_actions": [
            {
                "action_id": f"{category}:{arm}:{index}",
                "available": True,
                "executable": True,
            }
        ],
        "exploration": {
            "selected_arm": arm,
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
    samples.append(duplicate)

    result = evaluate_known_propensity_qualification(
        samples,
        validation_summary=_validation_summary(count=26),
        isolation_verified=True,
    )

    assert result["known_propensity_exploration_data_ready"] is True
    assert result["metrics"]["outcome_matched_samples"] == 26
    assert result["metrics"]["unique_joined_trajectories"] == 25
    assert result["metrics"]["victories"] == 1


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
