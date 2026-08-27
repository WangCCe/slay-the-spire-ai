"""Audit RL v2 inventory identities against exact real decision traces."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Callable, Mapping, Sequence
import zipfile

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    POTION_SLOTS,
    RELIC_SLOTS,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.combat_lightspeed_replay_distribution_calibration import (  # noqa: E402
    FLOOR_STRATA,
    RealReplayBinding,
    TransitionBatch,
    combat_action_family,
    floor_stratum,
    load_real_replay_bindings,
)
from spirecomm.ai.rl.v2.id_mapping import (  # noqa: E402
    IdMapper,
    build_id_mapper_from_payload,
)


REPORT_SCHEMA_VERSION = "combat-rl-inventory-identity-correction-v1"
TRACE_MEMBER = "ai_decision_trace_clean.jsonl"
TRACE_ACTION_FAMILIES = {
    "PlayCardAction": "play_card",
    "PotionAction": "use_potion",
    "EndTurnAction": "end_turn",
    "ProceedAction": "system",
    "CancelAction": "system",
}
AUTHORITY = {
    "evaluation": False,
    "formal_rl": False,
    "gameplay": False,
    "mechanics_equivalence": False,
    "policy_quality": False,
    "promotion": False,
    "qualification": False,
    "training": False,
}


@dataclass(frozen=True)
class SourceBinding:
    label: str
    checkpoint_path: Path
    checkpoint_sha256: str
    trace_archive_path: Path
    trace_archive_sha256: str


@dataclass(frozen=True)
class SourceAudit:
    report: dict[str, Any]
    original_potion_occupancy: np.ndarray
    corrected_potion_occupancy: np.ndarray
    trace_potion_occupancy: np.ndarray
    original_relic_occupancy: np.ndarray
    corrected_relic_occupancy: np.ndarray
    trace_relic_occupancy: np.ndarray
    floors: np.ndarray
    identities: Counter[tuple[str, str, str, str, int]]


def _normalized_sha256(value: str, *, label: str) -> str:
    result = str(value).lower()
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise ValueError(f"{label} SHA-256 must be 64 lowercase hexadecimal characters")
    return result


def verify_file(path: Path, expected_sha256: str, *, label: str) -> dict[str, Any]:
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise ValueError(f"{label} is missing: {resolved}")
    expected = _normalized_sha256(expected_sha256, label=label)
    actual = sha256_file(resolved)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch: {actual} != {expected}")
    return {
        "path": resolved.as_posix(),
        "sha256": actual,
        "size_bytes": resolved.stat().st_size,
    }


def load_trace_rows(path: Path, expected_sha256: str, *, label: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    identity = verify_file(path, expected_sha256, label=f"{label} trace archive")
    with zipfile.ZipFile(Path(path).resolve()) as archive:
        matches = [name for name in archive.namelist() if name == TRACE_MEMBER]
        if matches != [TRACE_MEMBER]:
            raise ValueError(f"{label} trace archive must contain exactly one {TRACE_MEMBER}")
        raw_lines = archive.read(TRACE_MEMBER).decode("utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw_lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} trace line {line_number} is invalid JSON") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{label} trace line {line_number} is not a mapping")
        action_type = str(row.get("action", {}).get("type", ""))
        if bool(row.get("in_combat")) and action_type in TRACE_ACTION_FAMILIES:
            rows.append(row)
    if not rows:
        raise ValueError(f"{label} trace contains no joinable combat decisions")
    identity["filtered_transition_count"] = len(rows)
    identity["member"] = TRACE_MEMBER
    return rows, identity


def _trace_floor(row: Mapping[str, Any], *, label: str, index: int) -> int:
    value = row.get("floor")
    if isinstance(value, bool):
        raise ValueError(f"{label} trace floor is invalid at index {index}")
    try:
        floor = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} trace floor is invalid at index {index}") from exc
    if floor != value:
        raise ValueError(f"{label} trace floor is non-integral at index {index}")
    return floor


def _replay_floor(value: float, *, label: str, index: int) -> int:
    floor_stratum(float(value))
    scaled = float(value) * 50.0
    floor = int(round(scaled))
    if abs(scaled - floor) > 1e-4:
        raise ValueError(f"{label} replay floor is non-integral at index {index}")
    return floor


def _inventory_resolution(
    raw: object,
    lookup: Callable[[str | None], int],
    *,
    empty_potion: bool,
) -> tuple[int, str, str, str, bool]:
    if not isinstance(raw, Mapping):
        raise ValueError("trace inventory entry is not a mapping")
    preferred = str(raw.get("id") or "")
    display_name = str(raw.get("name") or "")
    if empty_potion and (preferred == "Potion Slot" or display_name == "Potion Slot"):
        return 0, "empty", preferred, display_name, False
    preferred_value = lookup(preferred)
    if preferred_value > 0:
        return preferred_value, "preferred_id", preferred, display_name, True
    display_value = lookup(display_name)
    if display_value > 0:
        return display_value, "display_name_fallback", preferred, display_name, True
    return 0, "unresolved", preferred, display_name, True


def _trace_inventory_ids(
    values: object,
    lookup: Callable[[str | None], int],
    *,
    slots: int,
    kind: str,
    identities: Counter[tuple[str, str, str, str, int]],
) -> tuple[np.ndarray, int, Counter[str]]:
    if not isinstance(values, list):
        raise ValueError(f"trace {kind} inventory is not a list")
    if len(values) > slots:
        raise ValueError(f"trace {kind} inventory exceeds {slots} slots")
    ids = np.zeros(slots, dtype=np.int64)
    occupied = 0
    resolutions: Counter[str] = Counter()
    for index, raw in enumerate(values):
        value, resolution, preferred, display_name, is_occupied = _inventory_resolution(
            raw,
            lookup,
            empty_potion=kind == "potion",
        )
        ids[index] = value
        resolutions[resolution] += 1
        if is_occupied:
            occupied += 1
            identities[(kind, preferred, display_name, resolution, value)] += 1
    return ids, occupied, resolutions


def _summary(values: np.ndarray) -> dict[str, float | int]:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise ValueError("summary requires one finite non-empty vector")
    return {
        "count": int(array.size),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
        "minimum": float(np.min(array)),
        "standard_deviation": float(np.std(array, ddof=0)),
    }


def audit_source(
    label: str,
    batch: TransitionBatch,
    trace_rows: Sequence[Mapping[str, Any]],
    mapper: IdMapper,
) -> SourceAudit:
    batch.validate(label=label)
    rows = list(trace_rows)
    if len(rows) != batch.transition_count:
        raise ValueError(
            f"{label} trace/replay count mismatch: {len(rows)} != {batch.transition_count}"
        )
    corrected_potions = np.zeros_like(batch.potion_ids, dtype=np.int64)
    corrected_relics = np.zeros_like(batch.relic_ids, dtype=np.int64)
    trace_potion_occupancy = np.zeros(batch.transition_count, dtype=np.int64)
    trace_relic_occupancy = np.zeros(batch.transition_count, dtype=np.int64)
    floors = np.zeros(batch.transition_count, dtype=np.int64)
    resolutions: Counter[str] = Counter()
    identities: Counter[tuple[str, str, str, str, int]] = Counter()

    for index, row in enumerate(rows):
        replay_floor = _replay_floor(batch.continuous[index, 3], label=label, index=index)
        trace_floor = _trace_floor(row, label=label, index=index)
        if trace_floor != replay_floor:
            raise ValueError(
                f"{label} trace/replay floor mismatch at index {index}: "
                f"{trace_floor} != {replay_floor}"
            )
        action_type = str(row.get("action", {}).get("type", ""))
        trace_family = TRACE_ACTION_FAMILIES.get(action_type)
        replay_family = combat_action_family(int(batch.actions[index]))
        if trace_family != replay_family:
            raise ValueError(
                f"{label} trace/replay action-family mismatch at index {index}: "
                f"{trace_family} != {replay_family}"
            )
        potion_ids, potion_occupied, potion_resolutions = _trace_inventory_ids(
            row.get("potions"),
            mapper.potion_id,
            slots=POTION_SLOTS,
            kind="potion",
            identities=identities,
        )
        relic_ids, relic_occupied, relic_resolutions = _trace_inventory_ids(
            row.get("relics"),
            mapper.relic_id,
            slots=RELIC_SLOTS,
            kind="relic",
            identities=identities,
        )
        corrected_potions[index] = potion_ids
        corrected_relics[index] = relic_ids
        trace_potion_occupancy[index] = potion_occupied
        trace_relic_occupancy[index] = relic_occupied
        floors[index] = replay_floor
        resolutions.update({f"potion_{key}": value for key, value in potion_resolutions.items()})
        resolutions.update({f"relic_{key}": value for key, value in relic_resolutions.items()})

    original_potion_occupancy = np.sum(batch.potion_ids != 0, axis=1)
    original_relic_occupancy = np.sum(batch.relic_ids != 0, axis=1)
    corrected_potion_occupancy = np.sum(corrected_potions != 0, axis=1)
    corrected_relic_occupancy = np.sum(corrected_relics != 0, axis=1)

    def field_report(
        original_ids: np.ndarray,
        corrected_ids: np.ndarray,
        original_occupancy: np.ndarray,
        corrected_occupancy: np.ndarray,
        trace_occupancy: np.ndarray,
    ) -> dict[str, Any]:
        return {
            "corrected_occupancy": _summary(corrected_occupancy),
            "encoded_zero_recovered_occurrences": int(
                np.sum((original_ids == 0) & (corrected_ids != 0))
            ),
            "mismatched_transition_count": int(
                np.sum(np.any(original_ids != corrected_ids, axis=1))
            ),
            "nonzero_changed_occurrences": int(
                np.sum((original_ids != 0) & (original_ids != corrected_ids))
            ),
            "original_occupancy": _summary(original_occupancy),
            "trace_occupancy": _summary(trace_occupancy),
            "unresolved_occupied_occurrences": int(
                np.sum(trace_occupancy - corrected_occupancy)
            ),
        }

    report = {
        "inventory": {
            "potion": field_report(
                batch.potion_ids,
                corrected_potions,
                original_potion_occupancy,
                corrected_potion_occupancy,
                trace_potion_occupancy,
            ),
            "relic": field_report(
                batch.relic_ids,
                corrected_relics,
                original_relic_occupancy,
                corrected_relic_occupancy,
                trace_relic_occupancy,
            ),
        },
        "resolution_counts": dict(sorted(resolutions.items())),
        "transition_count": batch.transition_count,
    }
    return SourceAudit(
        report=report,
        original_potion_occupancy=original_potion_occupancy,
        corrected_potion_occupancy=corrected_potion_occupancy,
        trace_potion_occupancy=trace_potion_occupancy,
        original_relic_occupancy=original_relic_occupancy,
        corrected_relic_occupancy=corrected_relic_occupancy,
        trace_relic_occupancy=trace_relic_occupancy,
        floors=floors,
        identities=identities,
    )


def _combined(values: Sequence[np.ndarray]) -> np.ndarray:
    return np.concatenate([np.asarray(value) for value in values], axis=0)


def build_report(
    audits: Mapping[str, SourceAudit],
    *,
    source_bindings: Sequence[Mapping[str, Any]],
    items_binding: Mapping[str, Any],
    calibration_binding: Mapping[str, Any],
    calibration_report: Mapping[str, Any],
) -> dict[str, Any]:
    if not audits:
        raise ValueError("at least one source audit is required")
    labels = sorted(audits)
    floors = _combined([audits[label].floors for label in labels])
    arrays = {
        "potion": {
            "original": _combined([audits[label].original_potion_occupancy for label in labels]),
            "corrected": _combined([audits[label].corrected_potion_occupancy for label in labels]),
            "trace": _combined([audits[label].trace_potion_occupancy for label in labels]),
        },
        "relic": {
            "original": _combined([audits[label].original_relic_occupancy for label in labels]),
            "corrected": _combined([audits[label].corrected_relic_occupancy for label in labels]),
            "trace": _combined([audits[label].trace_relic_occupancy for label in labels]),
        },
    }
    identities: Counter[tuple[str, str, str, str, int]] = Counter()
    for label in labels:
        identities.update(audits[label].identities)
    identity_rows = [
        {
            "display_name": display_name,
            "kind": kind,
            "mapped_id": mapped_id,
            "occurrences": count,
            "preferred_id": preferred,
            "resolution": resolution,
        }
        for (kind, preferred, display_name, resolution, mapped_id), count in sorted(
            identities.items()
        )
    ]
    strata: dict[str, Any] = {}
    real_summary = calibration_report.get("real", {}).get("summary", {})
    simulator_summary = calibration_report.get("simulator", {}).get("summary", {})
    for name, start, end in FLOOR_STRATA:
        indices = np.flatnonzero((floors >= start) & (floors <= end))
        if not indices.size:
            continue
        entry: dict[str, Any] = {"transition_count": int(indices.size), "inventory": {}}
        for kind in ("potion", "relic"):
            original = _summary(arrays[kind]["original"][indices])
            corrected = _summary(arrays[kind]["corrected"][indices])
            trace = _summary(arrays[kind]["trace"][indices])
            metric = f"{kind}_occupied_slots"
            calibration_original = (
                real_summary.get("strata", {}).get(name, {}).get("semantic", {}).get(metric)
            )
            simulator = (
                simulator_summary.get("strata", {}).get(name, {}).get("semantic", {}).get(metric)
            )
            if calibration_original is not None and abs(
                float(calibration_original["mean"]) - float(original["mean"])
            ) > 1e-12:
                raise ValueError(f"calibration real {name} {metric} does not match replay")
            entry["inventory"][kind] = {
                "corrected_real": corrected,
                "original_real": original,
                "simulator": simulator,
                "simulator_minus_corrected_real_mean": (
                    None
                    if simulator is None
                    else float(simulator["mean"]) - float(corrected["mean"])
                ),
                "trace_real": trace,
            }
        strata[name] = entry

    aggregate = {
        kind: {
            "corrected_occupancy": _summary(values["corrected"]),
            "original_occupancy": _summary(values["original"]),
            "recovered_occupied_occurrences": int(
                np.sum(values["corrected"] - values["original"])
            ),
            "trace_occupancy": _summary(values["trace"]),
            "unresolved_occupied_occurrences": int(
                np.sum(values["trace"] - values["corrected"])
            ),
        }
        for kind, values in arrays.items()
    }
    unresolved = sum(
        row["occurrences"] for row in identity_rows if row["resolution"] == "unresolved"
    )
    return {
        "authority": dict(AUTHORITY),
        "calibration_binding": dict(calibration_binding),
        "correction": {
            "aggregate": aggregate,
            "identities": identity_rows,
            "strata": strata,
        },
        "items_binding": dict(items_binding),
        "limitations": [
            "The correction is descriptive and does not mutate historical replay checkpoints.",
            "Residual simulator differences are not mechanics or causal attribution.",
            "Existing r16 remains shape-compatible but corrected IDs may expose weakly trained embeddings.",
        ],
        "schema_version": REPORT_SCHEMA_VERSION,
        "source_bindings": list(source_bindings),
        "sources": {label: audits[label].report for label in labels},
        "transition_count": int(floors.size),
        "verdict": (
            "inventory_identity_correction_complete"
            if unresolved == 0
            else "inventory_identity_correction_incomplete"
        ),
    }


def _markdown(report: Mapping[str, Any]) -> bytes:
    aggregate = report["correction"]["aggregate"]
    lines = [
        "# Combat RL Inventory Identity Correction",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Joined transitions: {report['transition_count']}",
        f"- Potion occupied occurrences recovered: {aggregate['potion']['recovered_occupied_occurrences']}",
        f"- Relic occupied occurrences recovered: {aggregate['relic']['recovered_occupied_occurrences']}",
        f"- Unresolved potion occurrences: {aggregate['potion']['unresolved_occupied_occurrences']}",
        f"- Unresolved relic occurrences: {aggregate['relic']['unresolved_occupied_occurrences']}",
        "- Historical replay checkpoints were not modified.",
        "- This corrects source-encoder attribution only; residual LightSTS differences remain descriptive.",
        "",
        "## Floor Strata",
        "",
        "| Stratum | N | Potion original | Potion corrected | Potion simulator | Relic original | Relic corrected | Relic simulator |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, entry in report["correction"]["strata"].items():
        potion = entry["inventory"]["potion"]
        relic = entry["inventory"]["relic"]
        potion_sim = potion["simulator"]
        relic_sim = relic["simulator"]
        lines.append(
            "| {name} | {count} | {po:.3f} | {pc:.3f} | {ps} | {ro:.3f} | {rc:.3f} | {rs} |".format(
                name=name,
                count=entry["transition_count"],
                po=potion["original_real"]["mean"],
                pc=potion["corrected_real"]["mean"],
                ps="n/a" if potion_sim is None else f"{potion_sim['mean']:.3f}",
                ro=relic["original_real"]["mean"],
                rc=relic["corrected_real"]["mean"],
                rs="n/a" if relic_sim is None else f"{relic_sim['mean']:.3f}",
            )
        )
    lines.extend(["", "## Interpretation", "", "The initial calibration's largest inventory mismatch mixed real replay encoder undercount with simulator progression differences. Display-name fallback explains every occupied alias observed in the joined traces; any remaining cross-source delta must be evaluated after this correction and is not by itself evidence of a simulator mechanics bug.", ""])
    return "\n".join(lines).encode("utf-8")


def publish_report(output_dir: Path, report: Mapping[str, Any], *, max_report_bytes: int) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    staging = output.with_name(f".{output.name}.staging")
    if output.exists() or staging.exists():
        raise ValueError("output and staging paths must be absent")
    report_bytes = canonical_json_bytes(report)
    if len(report_bytes) > max_report_bytes:
        raise ValueError("report exceeds configured byte limit")
    summary_bytes = _markdown(report)
    manifest = {
        "artifacts": {
            "report.json": {
                "sha256": sha256_bytes(report_bytes),
                "size_bytes": len(report_bytes),
            },
            "summary.md": {
                "sha256": sha256_bytes(summary_bytes),
                "size_bytes": len(summary_bytes),
            },
        },
        "schema_version": "combat-rl-inventory-identity-correction-manifest-v1",
    }
    staging.mkdir(parents=False)
    try:
        (staging / "report.json").write_bytes(report_bytes)
        (staging / "summary.md").write_bytes(summary_bytes)
        (staging / "manifest.json").write_bytes(canonical_json_bytes(manifest))
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def _parse_labeled(values: Sequence[str], *, option: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"{option} values must use LABEL=VALUE")
        label, value = raw.split("=", 1)
        if not label or not value or label in result:
            raise ValueError(f"{option} labels must be non-empty and unique")
        result[label] = value
    return result


def _source_bindings(args: argparse.Namespace) -> tuple[SourceBinding, ...]:
    checkpoints = _parse_labeled(args.checkpoint, option="--checkpoint")
    checkpoint_hashes = _parse_labeled(args.checkpoint_sha256, option="--checkpoint-sha256")
    traces = _parse_labeled(args.trace_archive, option="--trace-archive")
    trace_hashes = _parse_labeled(args.trace_archive_sha256, option="--trace-archive-sha256")
    labels = set(checkpoints)
    if not labels or any(set(values) != labels for values in (checkpoint_hashes, traces, trace_hashes)):
        raise ValueError("checkpoint and trace labels must match exactly")
    return tuple(
        SourceBinding(
            label=label,
            checkpoint_path=Path(checkpoints[label]),
            checkpoint_sha256=checkpoint_hashes[label],
            trace_archive_path=Path(traces[label]),
            trace_archive_sha256=trace_hashes[label],
        )
        for label in sorted(labels)
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items-json", type=Path, required=True)
    parser.add_argument("--items-sha256", required=True)
    parser.add_argument("--calibration-report", type=Path, required=True)
    parser.add_argument("--calibration-report-sha256", required=True)
    parser.add_argument("--checkpoint", action="append", default=[], required=True)
    parser.add_argument("--checkpoint-sha256", action="append", default=[], required=True)
    parser.add_argument("--trace-archive", action="append", default=[], required=True)
    parser.add_argument("--trace-archive-sha256", action="append", default=[], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-report-bytes", type=int, default=4_194_304)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    items_binding = verify_file(args.items_json, args.items_sha256, label="items JSON")
    calibration_binding = verify_file(
        args.calibration_report,
        args.calibration_report_sha256,
        label="calibration report",
    )
    payload = json.loads(Path(args.items_json).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("items JSON root must be a mapping")
    mapper = build_id_mapper_from_payload(payload)
    calibration_report = json.loads(Path(args.calibration_report).read_text(encoding="utf-8"))
    if calibration_report.get("verdict") != "replay_distribution_calibration_ready":
        raise ValueError("calibration report is not ready")

    audits: dict[str, SourceAudit] = {}
    evidence: list[dict[str, Any]] = []
    for binding in _source_bindings(args):
        batch, checkpoint_evidence = load_real_replay_bindings(
            (
                RealReplayBinding(
                    binding.label,
                    binding.checkpoint_path,
                    binding.checkpoint_sha256,
                ),
            )
        )
        rows, trace_evidence = load_trace_rows(
            binding.trace_archive_path,
            binding.trace_archive_sha256,
            label=binding.label,
        )
        audits[binding.label] = audit_source(binding.label, batch, rows, mapper)
        evidence.append(
            {
                "checkpoint": checkpoint_evidence[0],
                "label": binding.label,
                "trace_archive": trace_evidence,
            }
        )

    report = build_report(
        audits,
        source_bindings=evidence,
        items_binding=items_binding,
        calibration_binding=calibration_binding,
        calibration_report=calibration_report,
    )
    manifest = publish_report(
        args.output_dir,
        report,
        max_report_bytes=args.max_report_bytes,
    )
    print(
        canonical_json_bytes(
            {
                "manifest": manifest,
                "output_dir": Path(args.output_dir).resolve().as_posix(),
                "report_sha256": manifest["artifacts"]["report.json"]["sha256"],
                "verdict": report["verdict"],
            }
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
