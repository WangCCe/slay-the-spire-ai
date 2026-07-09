#!/usr/bin/env python3
"""Compare non-combat mismatch stability across eval batches."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


DEFAULT_POLICY_CATEGORIES = {"shop", "card_reward", "event"}
CATEGORY_ORDER = {"shop": 0, "card_reward": 1, "event": 2, "route": 3}


def load_samples(path: Path) -> List[dict]:
    samples = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            samples.append(json.loads(line))
    return samples


def summarize_stability(
    batches: Sequence[Tuple[str, Sequence[dict]]],
    *,
    policy_categories=None,
) -> Dict[str, object]:
    policy_categories = set(policy_categories or DEFAULT_POLICY_CATEGORIES)
    batch_names = [name for name, _samples in batches]
    by_key = defaultdict(
        lambda: {"counts": Counter(), "matched_outcomes": Counter(), "sample_ids": []}
    )

    for batch_name, samples in batches:
        for sample in samples:
            key = _high_confidence_mismatch_key(sample)
            if key is None:
                continue
            entry = by_key[key]
            entry["counts"][batch_name] += 1
            if _has_matched_outcome(sample):
                entry["matched_outcomes"][batch_name] += 1
            sample_id = sample.get("sample_id")
            if sample_id:
                entry["sample_ids"].append(str(sample_id))

    stable = []
    for (category, current_id, bottled_id), entry in by_key.items():
        counts = {name: int(entry["counts"].get(name, 0)) for name in batch_names}
        if any(count == 0 for count in counts.values()):
            continue
        matched_outcome_counts = {
            name: int(entry["matched_outcomes"].get(name, 0)) for name in batch_names
        }
        policy_candidate = category in policy_categories and all(
            count > 0 for count in matched_outcome_counts.values()
        )
        total = sum(counts.values())
        stable.append(
            {
                "category": category,
                "current_action_id": current_id,
                "bottled_action_id": bottled_id,
                "batch_counts": counts,
                "matched_outcome_counts": matched_outcome_counts,
                "total_count": total,
                "policy_candidate": policy_candidate,
                "example_sample_ids": entry["sample_ids"][:8],
            }
        )

    stable.sort(key=_stable_sort_key)
    return {
        "batch_names": batch_names,
        "stable_mismatches": stable,
        "policy_candidate_count": sum(1 for item in stable if item["policy_candidate"]),
    }


def render_report(summary: Dict[str, object]) -> str:
    stable = summary.get("stable_mismatches", [])
    lines = [
        "# Non-Combat Mismatch Stability",
        "",
        f"- Batches: {', '.join(summary.get('batch_names', []))}",
        f"- Stable high-confidence mismatches: {len(stable)}",
        f"- Policy-ready stable mismatches: {summary.get('policy_candidate_count', 0)}",
        "",
        "## Stable Mismatches",
        "",
    ]

    if not stable:
        lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    for item in stable:
        counts = ", ".join(
            f"{name}={count}" for name, count in item["batch_counts"].items()
        )
        matched = ", ".join(
            f"{name}={count}"
            for name, count in item["matched_outcome_counts"].items()
        )
        policy = "policy-candidate" if item["policy_candidate"] else "diagnostic"
        lines.append(
            "- "
            f"{item['category']}: {item['current_action_id']} -> "
            f"{item['bottled_action_id']} "
            f"({counts}, matched_outcomes={matched}, "
            f"total={item['total_count']}, {policy})"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare high-confidence non-combat mismatches across batches."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    summary = summarize_stability(
        [
            ("baseline", load_samples(args.baseline)),
            ("candidate", load_samples(args.candidate)),
        ]
    )
    report = render_report(summary)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    return 0


def _high_confidence_mismatch_key(sample: dict):
    selected = sample.get("selected_action_id") or sample.get(
        "current_policy_label", {}
    ).get("action_id")
    bottled = sample.get("bottled_label", {}).get("action_id")
    if not selected or not bottled or selected == bottled:
        return None
    if sample.get("evidence_quality") != "complete":
        return None
    if sample.get("bottled_label", {}).get("confidence") != "high":
        return None
    return (sample.get("category"), selected, bottled)


def _has_matched_outcome(sample: dict) -> bool:
    outcome = sample.get("outcome") or {}
    return bool(outcome.get("included_in_gate")) and outcome.get("join_status") == "matched"


def _stable_sort_key(item: dict):
    return (
        not item["policy_candidate"],
        CATEGORY_ORDER.get(item["category"], 99),
        -item["total_count"],
        item["current_action_id"],
        item["bottled_action_id"],
    )


if __name__ == "__main__":
    raise SystemExit(main())
