"""Build deterministic offline non-combat OPE estimate artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any

from analysis_scripts.noncombat_ope_estimation import (
    BOOTSTRAP_DRAW_SCHEMA_VERSION,
    ESTIMATE_ARTIFACT_SCHEMA_VERSION,
    BootstrapResult,
    EstimatorBundle,
    EstimatorInputError,
    OutcomeEstimate,
    PercentileInterval,
    bootstrap_trajectory_estimates,
    build_estimator_diagnostics,
    estimate_outcome_channels,
    evaluate_policy_comparison,
    fraction_record,
    leave_one_trajectory_out,
    load_estimator_bundle,
)
from analysis_scripts.noncombat_ope_readiness import _replace_files_transactionally


PRODUCTION_BOOTSTRAP_REPLICATES = 10_000
PRODUCTION_CONFIDENCE_LEVEL = Fraction(95, 100)


def estimate_artifact_implementation_sha256() -> str:
    """Return the exact hash of estimate orchestration and rendering code."""

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def build_estimate_artifact(
    bundle: EstimatorBundle,
    *,
    seed: str,
    replicate_count: int = PRODUCTION_BOOTSTRAP_REPLICATES,
    confidence_level: Fraction = PRODUCTION_CONFIDENCE_LEVEL,
) -> dict[str, Any]:
    """Build a deterministic estimate artifact from one verified bundle."""

    estimates = estimate_outcome_channels(bundle.trajectories)
    estimator_diagnostics = build_estimator_diagnostics(
        bundle.trajectories,
        estimates,
    )
    bootstrap = bootstrap_trajectory_estimates(
        bundle.trajectories,
        seed=seed,
        replicate_count=replicate_count,
        confidence_level=confidence_level,
    )
    influence = leave_one_trajectory_out(bundle.trajectories)
    calibration_gates = bundle.calibration.get("gates", {})
    estimator_validation_ready = (
        isinstance(calibration_gates, Mapping)
        and calibration_gates.get("estimator_validation_ready") is True
    )
    dataset_estimation_ready = (
        bundle.readiness_audit.get("passed") is True
        and not bundle.readiness_audit.get("overlap_blockers")
        and bool(bundle.trajectories)
        and sum(
            (row.weight for row in bundle.trajectories),
            Fraction(0, 1),
        )
        > 0
    )
    production_bootstrap_contract = (
        replicate_count == PRODUCTION_BOOTSTRAP_REPLICATES
        and confidence_level == PRODUCTION_CONFIDENCE_LEVEL
    )
    blockers: list[str] = []
    if not estimator_validation_ready:
        blockers.append("estimator_validation_not_ready")
    if not dataset_estimation_ready:
        blockers.append("dataset_estimation_not_ready")
    blockers.extend(bootstrap.blockers)
    if not production_bootstrap_contract:
        blockers.append("production_bootstrap_contract_not_met")
    blockers = sorted(set(blockers))
    ope_estimate_ready = not blockers

    raw_comparison = evaluate_policy_comparison(
        estimator_validation_ready=estimator_validation_ready,
        dataset_estimation_ready=dataset_estimation_ready,
        estimates=estimates,
        bootstrap=bootstrap,
        influence=influence,
    )
    comparison_conditions = dict(raw_comparison.conditions)
    comparison_conditions["ope_estimate_ready"] = ope_estimate_ready
    comparison_blockers = list(raw_comparison.blockers)
    if not ope_estimate_ready:
        comparison_blockers.append("ope_estimate_not_ready")
    comparison_blockers = sorted(set(comparison_blockers))
    policy_comparison_ready = not comparison_blockers

    source = dict(bundle.hashes)
    source["estimate_artifact_implementation_sha256"] = (
        estimate_artifact_implementation_sha256()
    )
    victory_count = sum(int(row.victory) for row in bundle.trajectories)
    return {
        "accounting": {
            "decision_count": sum(
                len(row.sample_ids) for row in bundle.trajectories
            ),
            "effective_sample_size": dict(
                bundle.readiness_audit["effective_sample_size"]
            ),
            "ess_fraction": dict(bundle.readiness_audit["ess_fraction"]),
            "max_normalized_weight": dict(
                bundle.readiness_audit["max_normalized_weight"]
            ),
            "nonzero_weight_count": sum(
                row.weight > 0 for row in bundle.trajectories
            ),
            "trajectory_count": len(bundle.trajectories),
            "victory_count": victory_count,
            "zero_weight_count": sum(
                row.weight == 0 for row in bundle.trajectories
            ),
        },
        "blockers": blockers,
        "bootstrap": _bootstrap_record(bootstrap),
        "comparison": {
            "blockers": comparison_blockers,
            "conditions": comparison_conditions,
            "ready": policy_comparison_ready,
        },
        "contracts": {
            "bootstrap_draw_schema_version": BOOTSTRAP_DRAW_SCHEMA_VERSION,
            "confidence_level": fraction_record(confidence_level),
            "primary_estimator": "self_normalized_trajectory_is",
            "primary_outcome": "victory",
            "production_bootstrap_replicates": (
                PRODUCTION_BOOTSTRAP_REPLICATES
            ),
            "secondary_estimator": "ordinary_trajectory_is",
            "secondary_outcome": "floor_reached",
            "terminal_horizon": "complete_run",
        },
        "diagnostics": estimator_diagnostics,
        "estimates": _estimates_record(estimates),
        "gates": {
            "causal_uplift_ready": False,
            "dataset_estimation_ready": dataset_estimation_ready,
            "estimator_validation_ready": estimator_validation_ready,
            "formal_noncombat_rl_training_ready": False,
            "live_policy_promotion_ready": False,
            "ope_estimate_ready": ope_estimate_ready,
            "policy_comparison_ready": policy_comparison_ready,
        },
        "influence": _influence_record(influence),
        "limitations": [
            f"The source pool contains only {victory_count} observed victory.",
            "An OPE estimate is not a causal effect estimate.",
            "No estimate in this artifact authorizes training or live promotion.",
        ],
        "schema_version": ESTIMATE_ARTIFACT_SCHEMA_VERSION,
        "source": source,
    }


def render_estimate_json(artifact: Mapping[str, Any]) -> str:
    """Render stable LF-terminated estimate JSON."""

    _validate_artifact_shape(artifact)
    return json.dumps(
        artifact,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ) + "\n"


def render_estimate_markdown(artifact: Mapping[str, Any]) -> str:
    """Render a concise estimate and gate audit without downstream claims."""

    _validate_artifact_shape(artifact)
    gates = artifact["gates"]
    accounting = artifact["accounting"]
    estimates = artifact["estimates"]
    bootstrap = artifact["bootstrap"]
    lines = [
        "# Non-combat OPE estimate",
        "",
        "Status: "
        + ("ESTIMATE READY" if gates["ope_estimate_ready"] else "BLOCKED"),
        "",
        "## Readiness gates",
        "",
        "| Gate | Status |",
        "| --- | --- |",
    ]
    lines.extend(
        f"| {name} | {'PASS' if passed else 'BLOCKED'} |"
        for name, passed in sorted(gates.items())
    )
    lines.extend(
        [
            "",
            "## Accounting",
            "",
            f"- trajectories: {accounting['trajectory_count']}",
            f"- decisions: {accounting['decision_count']}",
            f"- observed victories: {accounting['victory_count']}",
            f"- bootstrap replicates: {bootstrap['effective_replicate_count']}",
            "",
            "## Victory estimates",
            "",
            "- behavior: " + str(estimates["victory"]["behavior"]["value"]),
            "- OIS target: "
            + str(estimates["victory"]["ordinary_is"]["value"]),
            "- SNIS target: "
            + str(estimates["victory"]["self_normalized_is"]["value"]),
            "- OIS uplift: "
            + str(estimates["victory"]["ordinary_uplift"]["value"]),
            "- SNIS uplift: "
            + str(estimates["victory"]["self_normalized_uplift"]["value"]),
            "",
            "## Blockers",
            "",
        ]
    )
    if artifact["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in artifact["blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in artifact["limitations"])
    return "\n".join(lines) + "\n"


def write_estimate_artifacts(
    artifact: Mapping[str, Any],
    *,
    json_path: Path | str,
    markdown_path: Path | str,
) -> None:
    """Atomically replace one complete estimate JSON/Markdown pair."""

    json_bytes = render_estimate_json(artifact).encode("utf-8")
    markdown_bytes = render_estimate_markdown(artifact).encode("utf-8")
    _replace_files_transactionally(
        (
            (Path(json_path), json_bytes),
            (Path(markdown_path), markdown_bytes),
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Estimate an offline non-combat target policy."
    )
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--target-manifest", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument(
        "--replicate-count",
        type=int,
        default=PRODUCTION_BOOTSTRAP_REPLICATES,
    )
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        bundle = load_estimator_bundle(
            sample_path=args.sample,
            target_manifest_path=args.target_manifest,
            readiness_path=args.readiness,
            calibration_path=args.calibration,
        )
        artifact = build_estimate_artifact(
            bundle,
            seed=args.seed,
            replicate_count=args.replicate_count,
        )
        write_estimate_artifacts(
            artifact,
            json_path=args.json_output,
            markdown_path=args.markdown_output,
        )
    except (EstimatorInputError, OSError, UnicodeError, ValueError) as exc:
        print(f"estimate blocked: {exc}", file=sys.stderr)
        return 2
    return 0 if artifact["gates"]["ope_estimate_ready"] else 2


def _bootstrap_record(bootstrap: BootstrapResult) -> dict[str, Any]:
    return {
        "blockers": list(bootstrap.blockers),
        "confidence_level": fraction_record(bootstrap.confidence_level),
        "draw_commitment_contract": "canonical-jsonl-replicate-draw-indices-v1",
        "draws_sha256": _draws_sha256(bootstrap),
        "effective_replicate_count": bootstrap.replicate_count,
        "intervals": {
            channel: {
                field: _interval_record(interval)
                for field, interval in sorted(fields.items())
            }
            for channel, fields in sorted(bootstrap.intervals.items())
        },
        "production_replicate_count": PRODUCTION_BOOTSTRAP_REPLICATES,
        "ready": bootstrap.ready,
        "replicate_estimate_commitment_contract": (
            "canonical-jsonl-exact-replicate-estimates-v1"
        ),
        "replicate_estimates_sha256": _replicate_estimates_sha256(bootstrap),
        "schema_version": bootstrap.schema_version,
        "seed": bootstrap.seed,
        "undefined_replicates": [
            {
                "draw_group_ids": list(row.draw_group_ids),
                "draw_indices": list(row.draw_indices),
                "reason": row.reason,
                "replicate_index": row.replicate_index,
            }
            for row in bootstrap.undefined_replicates
        ],
        "zero_victory_replicate_count": sum(
            row.estimates is not None
            and row.estimates["victory"].behavior == 0
            for row in bootstrap.replicates
        ),
    }


def _influence_record(influence: Any) -> dict[str, Any]:
    return {
        "max_absolute_changes": {
            channel: {
                field: fraction_record(value)
                for field, value in sorted(fields.items())
            }
            for channel, fields in sorted(
                influence.max_absolute_changes.items()
            )
        },
        "rows": [
            {
                "absolute_changes": {
                    channel: {
                        field: fraction_record(value)
                        for field, value in sorted(fields.items())
                    }
                    for channel, fields in sorted(
                        row.absolute_changes.items()
                    )
                },
                "blocker": row.blocker,
                "estimates": (
                    _estimates_record(row.estimates)
                    if row.estimates is not None
                    else None
                ),
                "excluded_group_id": row.excluded_group_id,
                "sign_changes": {
                    channel: dict(sorted(fields.items()))
                    for channel, fields in sorted(row.sign_changes.items())
                },
            }
            for row in influence.rows
        ],
        "undefined_group_ids": list(influence.undefined_group_ids),
    }


def _estimates_record(
    estimates: Mapping[str, OutcomeEstimate],
) -> dict[str, dict[str, dict[str, int | float]]]:
    fields = (
        "behavior",
        "ordinary_is",
        "ordinary_uplift",
        "self_normalized_is",
        "self_normalized_uplift",
    )
    return {
        channel: {
            field: fraction_record(getattr(estimate, field)) for field in fields
        }
        for channel, estimate in sorted(estimates.items())
    }


def _interval_record(interval: PercentileInterval) -> dict[str, Any]:
    return {
        "lower": fraction_record(interval.lower),
        "lower_index": interval.lower_index,
        "upper": fraction_record(interval.upper),
        "upper_index": interval.upper_index,
    }


def _draws_sha256(bootstrap: BootstrapResult) -> str:
    digest = hashlib.sha256()
    for row in bootstrap.replicates:
        _update_jsonl_digest(
            digest,
            {
                "draw_indices": list(row.draw_indices),
                "replicate_index": row.replicate_index,
            },
        )
    return digest.hexdigest()


def _replicate_estimates_sha256(bootstrap: BootstrapResult) -> str:
    digest = hashlib.sha256()
    for row in bootstrap.replicates:
        _update_jsonl_digest(
            digest,
            {
                "estimates": (
                    _exact_estimates_record(row.estimates)
                    if row.estimates is not None
                    else None
                ),
                "replicate_index": row.replicate_index,
            },
        )
    return digest.hexdigest()


def _exact_estimates_record(
    estimates: Mapping[str, OutcomeEstimate],
) -> dict[str, dict[str, dict[str, int]]]:
    return {
        channel: {
            field: {
                "denominator": getattr(estimate, field).denominator,
                "numerator": getattr(estimate, field).numerator,
            }
            for field in (
                "behavior",
                "ordinary_is",
                "ordinary_uplift",
                "self_normalized_is",
                "self_normalized_uplift",
            )
        }
        for channel, estimate in sorted(estimates.items())
    }


def _update_jsonl_digest(
    digest: Any,
    row: Mapping[str, Any],
) -> None:
    digest.update(
        (
            json.dumps(
                row,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )


def _validate_artifact_shape(artifact: Mapping[str, Any]) -> None:
    if artifact.get("schema_version") != ESTIMATE_ARTIFACT_SCHEMA_VERSION:
        raise ValueError("estimate artifact schema mismatch")
    for key in (
        "accounting",
        "blockers",
        "bootstrap",
        "comparison",
        "contracts",
        "diagnostics",
        "estimates",
        "gates",
        "influence",
        "limitations",
        "source",
    ):
        if key not in artifact:
            raise ValueError(f"estimate artifact missing {key}")
    gates = artifact["gates"]
    if not isinstance(gates, Mapping):
        raise ValueError("estimate artifact gates missing")
    for gate in (
        "causal_uplift_ready",
        "formal_noncombat_rl_training_ready",
        "live_policy_promotion_ready",
    ):
        if gates.get(gate) is not False:
            raise ValueError(f"downstream estimate gate opened: {gate}")


if __name__ == "__main__":
    raise SystemExit(main())
