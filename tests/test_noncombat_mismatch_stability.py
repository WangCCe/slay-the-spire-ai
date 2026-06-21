import json


def _sample(
    category,
    selected,
    bottled,
    *,
    confidence="high",
    evidence_quality="complete",
    sample_id=None,
):
    return {
        "sample_id": sample_id or f"{category}:{selected}:{bottled}",
        "category": category,
        "evidence_quality": evidence_quality,
        "selected_action_id": selected,
        "current_policy_label": {"action_id": selected, "label": selected},
        "bottled_label": {
            "action_id": bottled,
            "label": bottled,
            "confidence": confidence,
        },
    }


def test_stability_summary_requires_high_confidence_complete_mismatch_in_both_batches():
    from analysis_scripts.noncombat_mismatch_stability import summarize_stability

    baseline = [
        _sample("shop", "shop:leave", "shop:buy_card:offering", sample_id="old-shop"),
        _sample("shop", "shop:buy_card:anger", "shop:buy_card:anger"),
        _sample(
            "card_reward",
            "card_reward:take:anger",
            "card_reward:take:twin_strike",
            confidence="low",
        ),
    ]
    fresh = [
        _sample("shop", "shop:leave", "shop:buy_card:offering", sample_id="new-shop-1"),
        _sample("shop", "shop:leave", "shop:buy_card:offering", sample_id="new-shop-2"),
        _sample(
            "card_reward",
            "card_reward:take:anger",
            "card_reward:take:twin_strike",
            evidence_quality="partial",
        ),
    ]

    summary = summarize_stability(
        [("baseline", baseline), ("fresh", fresh)],
        policy_categories={"shop", "card_reward", "event"},
    )

    assert summary["batch_names"] == ["baseline", "fresh"]
    assert summary["policy_candidate_count"] == 1
    assert summary["stable_mismatches"] == [
        {
            "category": "shop",
            "current_action_id": "shop:leave",
            "bottled_action_id": "shop:buy_card:offering",
            "batch_counts": {"baseline": 1, "fresh": 2},
            "total_count": 3,
            "policy_candidate": True,
            "example_sample_ids": ["old-shop", "new-shop-1", "new-shop-2"],
        }
    ]


def test_cli_renders_stability_report(tmp_path):
    from analysis_scripts.noncombat_mismatch_stability import main

    baseline_path = tmp_path / "baseline.jsonl"
    fresh_path = tmp_path / "fresh.jsonl"
    output_path = tmp_path / "report.md"
    baseline_path.write_text(
        json.dumps(_sample("shop", "shop:leave", "shop:buy_card:offering")) + "\n",
        encoding="utf-8",
    )
    fresh_path.write_text(
        json.dumps(_sample("shop", "shop:leave", "shop:buy_card:offering")) + "\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--baseline",
            str(baseline_path),
            "--candidate",
            str(fresh_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    report = output_path.read_text(encoding="utf-8")
    assert "# Non-Combat Mismatch Stability" in report
    assert "Policy-ready stable mismatches: 1" in report
    assert "shop:leave -> shop:buy_card:offering" in report
