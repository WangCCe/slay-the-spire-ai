import json
import subprocess
import sys
from pathlib import Path

from analysis_scripts.offline_decision_comparator import (
    DecisionSample,
    compare_samples,
    load_fixture_samples,
    load_jsonl_samples,
    load_run_samples,
    rank_issues,
    render_markdown_report,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "offline_decision_samples.json"


def test_fixture_loader_returns_all_operating_decision_categories():
    samples = load_fixture_samples(FIXTURE_PATH)

    assert {sample.category for sample in samples} == {
        "shop",
        "event",
        "route",
        "card_reward",
    }
    assert all(sample.evidence_quality == "complete" for sample in samples)


def test_bottled_style_adapters_find_high_confidence_fixture_differences():
    rows = compare_samples(load_fixture_samples(FIXTURE_PATH))
    by_id = {row.sample_id: row for row in rows}

    assert by_id["fixture-shop-purge-over-anger"].reference_choice == "purge"
    assert by_id["fixture-shop-purge-over-anger"].match is False
    assert by_id["fixture-shop-purge-over-anger"].confidence == "high"
    assert "starter removal" in by_id["fixture-shop-purge-over-anger"].reason

    assert by_id["fixture-event-shining-light-low-hp"].reference_choice == "choose 1: Leave"
    assert by_id["fixture-event-shining-light-low-hp"].confidence == "high"

    assert by_id["fixture-route-avoid-elite-chain"].reference_choice == "choice 1"
    assert by_id["fixture-route-avoid-elite-chain"].confidence == "high"
    assert "survivability" in by_id["fixture-route-avoid-elite-chain"].reason

    assert by_id["fixture-card-reward-offering-skipped"].reference_choice == "Offering"
    assert by_id["fixture-card-reward-offering-skipped"].confidence == "high"


def test_run_loader_marks_shop_purchases_as_partial_evidence(tmp_path):
    run_path = tmp_path / "sample.run"
    run_path.write_text(
        json.dumps(
            {
                "character_chosen": "IRONCLAD",
                "floor_reached": 8,
                "path_taken": ["M", "$", "R"],
                "items_purchased": ["Anger"],
                "item_purchase_floors": [2],
                "items_purged": ["Strike_R"],
                "items_purged_floors": [2],
                "card_choices": [
                    {
                        "floor": 1,
                        "picked": "SKIP",
                        "not_picked": ["Offering", "Flex"],
                    }
                ],
                "event_choices": [
                    {
                        "floor": 3,
                        "event_name": "Shining Light",
                        "player_choice": "Entered",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    samples = load_run_samples(run_path)
    shop_samples = [sample for sample in samples if sample.category == "shop"]

    assert shop_samples
    assert all(sample.evidence_quality == "partial" for sample in shop_samples)
    assert all("missing full shop offer" in sample.limitations for sample in shop_samples)


def test_event_reference_does_not_invent_unavailable_single_option_choice():
    sample = DecisionSample(
        sample_id="trace-wing-statue-forced-leave",
        category="event",
        source="decision_trace",
        floor=12,
        act=1,
        evidence_quality="complete",
        our_choice={"kind": "choose", "index": 0, "label": "Leave"},
        context={
            "event_name": "Wing Statue",
            "choices": ["Leave"],
            "current_hp": 20,
            "max_hp": 80,
            "relics": [],
        },
    )

    [row] = compare_samples([sample])

    assert row.reference_choice == "choose 0: Leave"
    assert row.confidence == "low"
    assert row.match is True
    assert "single available event option" in row.reason


def test_event_trace_ignores_disabled_options_when_labeling_choices(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    row = {
        "floor": 5,
        "act": 1,
        "screen_type": "ScreenType.EVENT",
        "source": "combat_rl",
        "action": {"type": "ChooseAction", "choice_index": 1},
        "player": {"current_hp": 44, "max_hp": 80},
        "relics": [{"name": "Burning Blood"}],
        "screen": {
            "type": "ScreenType.EVENT",
            "event_name": "Wing Statue",
            "options": [
                {"label": "Pray", "text": "[Pray] Remove a card.", "disabled": False, "choice_index": 0},
                {"label": "Locked", "text": "[Locked] Requires: Card with 10 or more damage.", "disabled": True},
                {"label": "Leave", "text": "[Leave]", "disabled": False, "choice_index": 1},
            ],
        },
    }
    trace_path.write_text(json.dumps(row), encoding="utf-8")

    [sample] = load_jsonl_samples(trace_path)
    [comparison] = compare_samples([sample])

    assert sample.context["choices"] == ["Pray", "Leave"]
    assert sample.our_choice == {"kind": "choose", "index": 1, "label": "Leave"}
    assert comparison.reference_choice == "choose 1: Leave"
    assert comparison.match is True


def test_fixture_only_differences_do_not_become_repair_candidates():
    rows = compare_samples(load_fixture_samples(FIXTURE_PATH))
    issues = rank_issues(rows)
    report = render_markdown_report(rows, issues)

    assert issues == []
    assert "Current Choice" in report
    assert "Bottled Reference" in report
    assert "Most Worth Fixing" in report
    assert "No repeated high-confidence" in report
    assert "No gameplay-code fix is applied" in report


def test_rank_issues_requires_repeated_non_fixture_evidence():
    samples = [
        DecisionSample(
            sample_id=f"trace-shop-{index}",
            category="shop",
            source="decision_trace",
            floor=5 + index,
            act=1,
            evidence_quality="complete",
            our_choice={"kind": "buy_card", "name": "Anger"},
            context={
                "gold": 180,
                "purge_available": True,
                "purge_cost": 75,
                "deck": ["Strike_R", "Defend_R", "Bash"],
                "cards": [{"id": "Anger", "name": "Anger", "price": 55}],
                "relics": [],
            },
        )
        for index in range(2)
    ]

    issues = rank_issues(compare_samples(samples))

    assert len(issues) == 1
    assert issues[0].reference_choice == "purge"
    assert issues[0].confidence == "high"
    assert "Repeated 2x" in issues[0].reason
    assert "Repair is justified" in render_markdown_report(compare_samples(samples), issues)


def test_rank_issues_deduplicates_same_trace_decision_retries():
    duplicate_samples = [
        DecisionSample(
            sample_id=f"trace-shop-retry-{index}",
            category="shop",
            source="decision_trace",
            floor=5,
            act=1,
            evidence_quality="complete",
            our_choice={"kind": "buy_card", "name": "Anger"},
            context={
                "gold": 180,
                "purge_available": True,
                "purge_cost": 75,
                "deck": ["Strike_R", "Defend_R", "Bash"],
                "cards": [{"id": "Anger", "name": "Anger", "price": 55}],
                "relics": [],
            },
        )
        for index in range(2)
    ]

    assert rank_issues(compare_samples(duplicate_samples)) == []

    repeated_real_sample = DecisionSample(
        sample_id="trace-shop-next-floor",
        category="shop",
        source="decision_trace",
        floor=6,
        act=1,
        evidence_quality="complete",
        our_choice={"kind": "buy_card", "name": "Anger"},
        context={
            "gold": 180,
            "purge_available": True,
            "purge_cost": 75,
            "deck": ["Strike_R", "Defend_R", "Bash"],
            "cards": [{"id": "Anger", "name": "Anger", "price": 55}],
            "relics": [],
        },
    )

    issues = rank_issues(compare_samples(duplicate_samples + [repeated_real_sample]))

    assert len(issues) == 1
    assert "Repeated 2x" in issues[0].reason


def test_event_reference_matches_bottled_golden_shrine_and_mausoleum():
    rows = compare_samples(
        [
            DecisionSample(
                sample_id="golden-shrine-no-omamori",
                category="event",
                source="fixture:event",
                floor=6,
                act=1,
                evidence_quality="complete",
                our_choice={"kind": "choose", "index": 1, "label": "Pray"},
                context={
                    "event_name": "Golden Shrine",
                    "current_hp": 70,
                    "max_hp": 80,
                    "choices": ["Pray", "Desecrate"],
                    "relics": [],
                },
            ),
            DecisionSample(
                sample_id="golden-shrine-omamori",
                category="event",
                source="fixture:event",
                floor=6,
                act=1,
                evidence_quality="complete",
                our_choice={"kind": "choose", "index": 0, "label": "Pray"},
                context={
                    "event_name": "Golden Shrine",
                    "current_hp": 70,
                    "max_hp": 80,
                    "choices": ["Pray", "Desecrate"],
                    "relics": ["Omamori"],
                },
            ),
            DecisionSample(
                sample_id="mausoleum-omamori",
                category="event",
                source="fixture:event",
                floor=18,
                act=2,
                evidence_quality="complete",
                our_choice={"kind": "choose", "index": 1, "label": "Leave"},
                context={
                    "event_name": "The Mausoleum",
                    "current_hp": 60,
                    "max_hp": 80,
                    "choices": ["Open Coffin", "Leave"],
                    "relics": ["Omamori"],
                },
            ),
        ]
    )
    by_id = {row.sample_id: row for row in rows}

    assert by_id["golden-shrine-no-omamori"].reference_choice == "choose 0: Pray"
    assert by_id["golden-shrine-omamori"].reference_choice == "choose 1: Desecrate"
    assert by_id["mausoleum-omamori"].reference_choice == "choose 0: Open Coffin"


def test_compare_samples_native_bottled_mode_includes_oracle_metadata(tmp_path):
    from analysis_scripts.offline_decision_comparator import compare_samples
    from tests.test_bottled_policy_oracle import _write_fake_bottled_checkout

    checkout = _write_fake_bottled_checkout(tmp_path / "bottled_ai")
    sample = DecisionSample(
        sample_id="native-card",
        category="card_reward",
        source="fixture:card_reward",
        floor=3,
        act=1,
        evidence_quality="complete",
        our_choice={"kind": "skip", "name": "skip"},
        context={"deck": [], "offered": ["Sentinel"], "can_skip": True},
    )

    [row] = compare_samples(
        [sample],
        reference_mode="native_bottled",
        bottled_repo_path=checkout,
    )

    assert row.reference_choice == "Sentinel"
    assert row.oracle_mode == "native_bottled"
    assert row.oracle_source["strategy"] == "REQUESTED_STRIKE"
    assert row.match is False


def test_direct_script_native_bottled_mode_writes_report(tmp_path):
    from tests.test_bottled_policy_oracle import _write_fake_bottled_checkout

    checkout = _write_fake_bottled_checkout(tmp_path / "bottled_ai")
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "id": "native-card",
                        "category": "card_reward",
                        "source": "fixture:card_reward",
                        "floor": 3,
                        "act": 1,
                        "evidence_quality": "complete",
                        "our_choice": {"kind": "skip", "name": "skip"},
                        "context": {"deck": [], "offered": ["Sentinel"], "can_skip": True},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "report.md"
    script_path = (
        Path(__file__).resolve().parents[1]
        / "analysis_scripts"
        / "offline_decision_comparator.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--fixture",
            str(fixture_path),
            "--reference-mode",
            "native-bottled",
            "--bottled-repo",
            str(checkout),
            "--output",
            str(report_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "native Bottled" in report_path.read_text(encoding="utf-8")


def test_enriched_trace_rows_become_complete_operating_samples(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    rows = [
        {
            "floor": 10,
            "act": 1,
            "screen_type": "ScreenType.CARD_REWARD",
            "source": "combat_rl",
            "action": {"type": "CardRewardAction", "name": "Flex"},
            "deck": [{"name": "Strike_R"}, {"name": "Bash"}],
            "screen": {
                "type": "ScreenType.CARD_REWARD",
                "cards": [{"name": "Offering", "id": "Offering"}, {"name": "Flex", "id": "Flex"}],
                "can_skip": True,
                "can_bowl": False,
            },
        },
        {
            "floor": 11,
            "act": 1,
            "screen_type": "ScreenType.SHOP_SCREEN",
            "source": "combat_rl",
            "action": {"type": "BuyCardAction", "name": "Anger"},
            "gold": 180,
            "deck": [{"name": "Strike_R"}, {"name": "Defend_R"}, {"name": "Bash"}],
            "screen": {
                "type": "ScreenType.SHOP_SCREEN",
                "cards": [{"name": "Anger", "id": "Anger", "price": 55}],
                "relics": [],
                "potions": [],
                "purge_available": True,
                "purge_cost": 75,
            },
        },
        {
            "floor": 12,
            "act": 1,
            "screen_type": "ScreenType.EVENT",
            "source": "combat_rl",
            "action": {"type": "ChooseAction", "choice_index": 0},
            "player": {"current_hp": 20, "max_hp": 80},
            "relics": [],
            "screen": {
                "type": "ScreenType.EVENT",
                "event_name": "Shining Light",
                "options": [
                    {"label": "Enter", "text": "Enter", "disabled": False, "choice_index": 0},
                    {"label": "Leave", "text": "Leave", "disabled": False, "choice_index": 1},
                ],
            },
        },
        {
            "floor": 13,
            "act": 1,
            "screen_type": "ScreenType.MAP",
            "source": "combat_rl",
            "action": {"type": "ChooseMapNodeAction", "choice_index": 0},
            "player": {"current_hp": 24, "max_hp": 80},
            "gold": 100,
            "relics": [{"name": "Burning Blood"}],
            "screen": {
                "type": "ScreenType.MAP",
                "paths": [
                    {"choice": 0, "label": "elite chain", "nodes": ["E", "E"]},
                    {"choice": 1, "label": "safe shop rest", "nodes": ["?", "$", "R"]},
                ],
            },
        },
    ]
    trace_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    samples = load_jsonl_samples(trace_path)

    assert [sample.category for sample in samples] == ["card_reward", "shop", "event", "route"]
    assert all(sample.evidence_quality == "complete" for sample in samples)
    assert samples[0].our_choice == {"kind": "take", "name": "Flex"}
    assert samples[0].context["offered"] == ["Offering", "Flex"]
    assert samples[1].context["gold"] == 180
    assert samples[1].context["purge_available"] is True
    assert samples[2].our_choice == {"kind": "choose", "index": 0, "label": "Enter"}
    assert samples[2].context["current_hp"] == 20
    assert samples[3].our_choice == {"kind": "map_node", "choice": 0}
    assert samples[3].context["paths"][1]["label"] == "safe shop rest"

    rows = compare_samples(samples)
    by_category = {row.category: row for row in rows}

    assert by_category["card_reward"].reference_choice == "Offering"
    assert by_category["card_reward"].confidence == "high"
    assert by_category["shop"].reference_choice == "purge"
    assert by_category["shop"].confidence == "high"
    assert by_category["event"].reference_choice == "choose 1: Leave"
    assert by_category["event"].confidence == "high"
    assert by_category["route"].reference_choice == "choice 1"
    assert by_category["route"].confidence == "high"


def test_trace_loader_can_filter_by_unix_time(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    base_row = {
        "floor": 10,
        "act": 1,
        "screen_type": "ScreenType.CARD_REWARD",
        "source": "combat_rl",
        "action": {"type": "CardRewardAction", "name": "Flex"},
        "deck": [{"name": "Strike_R"}, {"name": "Bash"}],
        "screen": {
            "type": "ScreenType.CARD_REWARD",
            "cards": [{"name": "Offering", "id": "Offering"}, {"name": "Flex", "id": "Flex"}],
            "can_skip": True,
            "can_bowl": False,
        },
    }
    stale = dict(base_row, unix_time=100.0)
    fresh = dict(base_row, unix_time=200.0, floor=11)
    trace_path.write_text("\n".join(json.dumps(row) for row in [stale, fresh]), encoding="utf-8")

    samples = load_jsonl_samples(trace_path, since_unix=150.0)

    assert len(samples) == 1
    assert samples[0].floor == 11


def test_route_trace_reconstructs_paths_from_map_snapshot(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    row = {
        "floor": 2,
        "act": 1,
        "screen_type": "ScreenType.MAP",
        "source": "combat_rl",
        "action": {"type": "ChooseMapNodeAction", "choice_index": 0},
        "player": {"current_hp": 80, "max_hp": 80},
        "gold": 120,
        "relics": [{"name": "Burning Blood"}],
        "screen": {
            "type": "ScreenType.MAP",
            "next_nodes": [
                {"x": 1, "y": 1, "symbol": "R"},
                {"x": 2, "y": 1, "symbol": "E"},
            ],
            "map": {
                "nodes": [
                    {"x": 1, "y": 1, "symbol": "R", "children": [{"x": 1, "y": 2}]},
                    {"x": 2, "y": 1, "symbol": "E", "children": [{"x": 2, "y": 2}]},
                    {"x": 1, "y": 2, "symbol": "$", "children": []},
                    {"x": 2, "y": 2, "symbol": "E", "children": []},
                ]
            },
            "paths": [
                {"choice": 0, "label": "R@1,1", "nodes": ["R"]},
                {"choice": 1, "label": "E@2,1", "nodes": ["E"]},
            ],
        },
    }
    trace_path.write_text(json.dumps(row), encoding="utf-8")

    samples = load_jsonl_samples(trace_path)

    assert len(samples) == 1
    assert samples[0].evidence_quality == "complete"
    assert samples[0].context["paths"] == [
        {"choice": 0, "label": "R@1,1 -> $@1,2", "nodes": ["R", "$"]},
        {"choice": 1, "label": "E@2,1 -> E@2,2", "nodes": ["E", "E"]},
    ]
