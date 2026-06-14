import json
from pathlib import Path

from analysis_scripts.offline_decision_comparator import (
    DecisionSample,
    compare_samples,
    load_fixture_samples,
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
