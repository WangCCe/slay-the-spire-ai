"""Bound inputs for the card-only native-baseline RL pilot."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from analysis_scripts.noncombat_simulator_adapter import (
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    SimulatorAdapterError,
    canonical_json_bytes,
    validate_candidates,
    validate_native_baseline_action,
    validate_provenance,
    validate_snapshot,
)
from analysis_scripts.offline_decision_comparator import DecisionSample


CORPUS_ARTIFACT_SCHEMA_VERSION = (
    "noncombat-simulator-baseline-demonstrations-artifact-v1"
)
DATASET_SCHEMA_VERSION = "noncombat-simulator-native-demonstration-dataset-v1"
DEMONSTRATION_SCHEMA_VERSION = "noncombat-simulator-native-demonstration-v1"
LABEL_ARTIFACT_SCHEMA_VERSION = "noncombat-card-only-bottled-labels-v1"
BOUND_CORPUS_PATH = Path(
    "reports/noncombat_simulator_baseline_warm_start_20260802/demonstrations.json"
)
BOUND_CORPUS_SHA256 = (
    "6b549ad2f54cea6e08f4399e9ec5cda12d20b3bb3f18fa5349cdb544d48050c6"
)
BOUND_CORPUS_SIZE_BYTES = 320_965_025
BOUND_REGISTRATION_SHA256 = (
    "2815274e61c7d4ad8e553190ca234d6303457d9543cd63def541637729340a7a"
)
BOUND_CARD_ROW_COUNTS = {"train": 302, "validation": 175}
ALLOWED_CORPUS_COHORTS = ("train", "validation")


class CardOnlyPilotBlocked(RuntimeError):
    """Raised when the pilot must fail closed before training."""


class CardOracle(Protocol):
    def source_metadata(self) -> dict[str, Any]: ...

    def evaluate(self, sample: DecisionSample) -> Any: ...


@dataclass(frozen=True)
class BoundCardCorpus:
    source: dict[str, Any]
    rows: dict[str, tuple[dict[str, Any], ...]]


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CardOnlyPilotBlocked(f"{label} must be an object")
    return dict(value)


def _stream_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_requested_cohorts(cohorts: Sequence[str]) -> tuple[str, ...]:
    if isinstance(cohorts, (str, bytes)):
        raise CardOnlyPilotBlocked("corpus cohorts must be a sequence")
    normalized = tuple(cohorts)
    if not normalized or len(set(normalized)) != len(normalized):
        raise CardOnlyPilotBlocked("corpus cohorts must be nonempty and unique")
    denied = sorted(set(normalized) - set(ALLOWED_CORPUS_COHORTS))
    if denied:
        raise CardOnlyPilotBlocked(
            "protected corpus cohort access denied: " + ", ".join(denied)
        )
    return normalized


def _validate_card_context(
    state: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> None:
    context = _mapping(state.get("decision_context"), "card decision_context")
    cards = context.get("cards")
    if not isinstance(cards, list) or not cards:
        raise CardOnlyPilotBlocked("card decision_context.cards must be nonempty")
    deck = state.get("deck")
    if not isinstance(deck, list):
        raise CardOnlyPilotBlocked("card source deck must be a list")
    for index, card in enumerate(deck):
        value = _mapping(card, f"deck[{index}]")
        if not isinstance(value.get("name"), str) or not value["name"]:
            raise CardOnlyPilotBlocked(f"deck[{index}].name is required")

    take_candidates = [candidate for candidate in candidates if candidate["kind"] == "take"]
    if len(take_candidates) != len(cards):
        raise CardOnlyPilotBlocked("offered cards and take candidates do not align")
    for index, (offered, candidate) in enumerate(zip(cards, take_candidates, strict=True)):
        offered_value = _mapping(offered, f"offered card[{index}]")
        raw = _mapping(candidate.get("raw"), f"take candidate[{index}].raw")
        for field in ("id", "name", "slot", "upgrade_count", "upgraded"):
            if offered_value.get(field) != raw.get(field):
                raise CardOnlyPilotBlocked(
                    f"offered card[{index}] and take candidate disagree on {field}"
                )

    kinds = [candidate["kind"] for candidate in candidates]
    if any(kind not in {"take", "skip", "bowl"} for kind in kinds):
        raise CardOnlyPilotBlocked("card candidates contain an unsupported family")
    alternatives = kinds.count("skip") + kinds.count("bowl")
    if alternatives != 1:
        raise CardOnlyPilotBlocked("card reward must contain one non-take candidate")
    has_bowl = context.get("has_singing_bowl")
    if not isinstance(has_bowl, bool):
        raise CardOnlyPilotBlocked("card decision_context.has_singing_bowl is required")
    if has_bowl != (kinds.count("bowl") == 1):
        raise CardOnlyPilotBlocked("Singing Bowl context and candidates disagree")


def _validate_card_row(row: object, *, cohort: str) -> dict[str, Any]:
    value = copy.deepcopy(_mapping(row, "demonstration row"))
    if value.get("schema_version") != DEMONSTRATION_SCHEMA_VERSION:
        raise CardOnlyPilotBlocked("demonstration row schema mismatch")
    if value.get("source_type") != SOURCE_TYPE:
        raise CardOnlyPilotBlocked("demonstration row source_type mismatch")
    if value.get("cohort") != cohort or value.get("category") != "card_reward":
        raise CardOnlyPilotBlocked("demonstration row cohort/category mismatch")
    seed = value.get("seed")
    decision_index = value.get("decision_index")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise CardOnlyPilotBlocked("demonstration seed must be an integer")
    if (
        isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index < 0
    ):
        raise CardOnlyPilotBlocked("demonstration decision_index is invalid")

    try:
        snapshot = validate_snapshot(value.get("source_snapshot"))
        if snapshot["terminal"] or snapshot["category"] != "card_reward":
            raise CardOnlyPilotBlocked("card demonstration source is not active")
        if value.get("source_snapshot_sha256") != hashlib.sha256(
            canonical_json_bytes(snapshot)
        ).hexdigest():
            raise CardOnlyPilotBlocked("card source snapshot hash mismatch")
        candidates = validate_candidates(
            value.get("candidate_actions"), category="card_reward"
        )
        if value.get("candidate_actions_sha256") != hashlib.sha256(
            canonical_json_bytes(candidates)
        ).hexdigest():
            raise CardOnlyPilotBlocked("card candidates hash mismatch")
        teacher = validate_native_baseline_action(
            value.get("teacher"), category="card_reward", candidates=candidates
        )
        validate_provenance(value.get("provenance"))
    except SimulatorAdapterError as exc:
        raise CardOnlyPilotBlocked(f"invalid card demonstration row: {exc}") from exc
    _validate_card_context(snapshot["state"], candidates)
    value["source_snapshot"] = snapshot
    value["candidate_actions"] = candidates
    value["teacher"] = teacher
    return value


def load_bound_card_corpus(
    corpus_path: Path | str,
    *,
    expected_sha256: str = BOUND_CORPUS_SHA256,
    expected_size_bytes: int = BOUND_CORPUS_SIZE_BYTES,
    expected_registration_sha256: str = BOUND_REGISTRATION_SHA256,
    expected_card_row_counts: Mapping[str, int] = BOUND_CARD_ROW_COUNTS,
    cohorts: Sequence[str] = ALLOWED_CORPUS_COHORTS,
) -> BoundCardCorpus:
    """Load only bound train/validation card rows from the archived corpus."""
    requested = _validate_requested_cohorts(cohorts)
    path = Path(corpus_path).resolve()
    if not path.is_file():
        raise CardOnlyPilotBlocked(f"bound corpus is missing: {path}")
    if path.stat().st_size != expected_size_bytes:
        raise CardOnlyPilotBlocked("bound corpus size drift")
    actual_sha256 = _stream_sha256(path)
    if actual_sha256 != expected_sha256:
        raise CardOnlyPilotBlocked("bound corpus sha256 drift")

    with path.open("r", encoding="utf-8") as source:
        artifact = json.load(source)
    root = _mapping(artifact, "demonstration artifact")
    if set(root) != {"datasets", "registration_sha256", "schema_version"}:
        raise CardOnlyPilotBlocked("demonstration artifact fields mismatch")
    if root.get("schema_version") != CORPUS_ARTIFACT_SCHEMA_VERSION:
        raise CardOnlyPilotBlocked("demonstration artifact schema mismatch")
    if root.get("registration_sha256") != expected_registration_sha256:
        raise CardOnlyPilotBlocked("demonstration registration drift")
    datasets = _mapping(root.get("datasets"), "demonstration datasets")
    if set(datasets) != {"final_test", "train", "validation"}:
        raise CardOnlyPilotBlocked("demonstration cohort fields mismatch")
    if datasets["final_test"] is not None:
        raise CardOnlyPilotBlocked("protected final_test corpus must remain absent")

    rows_by_cohort: dict[str, tuple[dict[str, Any], ...]] = {}
    for cohort in requested:
        dataset = _mapping(datasets.get(cohort), f"{cohort} dataset")
        if dataset.get("schema_version") != DATASET_SCHEMA_VERSION:
            raise CardOnlyPilotBlocked(f"{cohort} dataset schema mismatch")
        if dataset.get("cohort") != cohort:
            raise CardOnlyPilotBlocked(f"{cohort} dataset cohort mismatch")
        if dataset.get("source_type") != SOURCE_TYPE:
            raise CardOnlyPilotBlocked(f"{cohort} dataset source_type mismatch")
        if dataset.get("teacher_policy_id") != NATIVE_TARGET_POLICY_ID:
            raise CardOnlyPilotBlocked(f"{cohort} dataset teacher mismatch")
        rows = dataset.get("rows")
        if not isinstance(rows, list) or dataset.get("row_count") != len(rows):
            raise CardOnlyPilotBlocked(f"{cohort} dataset row count mismatch")
        card_rows = tuple(
            _validate_card_row(row, cohort=cohort)
            for row in rows
            if isinstance(row, Mapping) and row.get("category") == "card_reward"
        )
        expected_count = expected_card_row_counts.get(cohort)
        if expected_count is None or len(card_rows) != expected_count:
            raise CardOnlyPilotBlocked(f"{cohort} card row count mismatch")
        ordering = [(row["seed"], row["decision_index"]) for row in card_rows]
        if ordering != sorted(ordering):
            raise CardOnlyPilotBlocked(f"{cohort} card rows are not ordered")
        rows_by_cohort[cohort] = card_rows

    return BoundCardCorpus(
        source={
            "path": str(path),
            "registration_sha256": expected_registration_sha256,
            "sha256": actual_sha256,
            "size_bytes": expected_size_bytes,
        },
        rows=rows_by_cohort,
    )


def _normalize_label(value: object) -> str:
    return "".join(char for char in str(value).lower() if char.isalnum())


def _candidate_for_bottled_label(
    label: str, candidates: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    normalized = _normalize_label(label)
    if normalized in {"skip", "bowl"}:
        matches = [candidate for candidate in candidates if candidate["kind"] == normalized]
    else:
        matches = [
            candidate
            for candidate in candidates
            if candidate["kind"] == "take"
            and normalized
            in {
                _normalize_label(candidate.get("label")),
                _normalize_label(_mapping(candidate.get("raw"), "card candidate raw").get("name")),
            }
        ]
    if len(matches) != 1:
        raise CardOnlyPilotBlocked(
            f"Bottled label {label!r} maps to {len(matches)} legal candidates"
        )
    return copy.deepcopy(dict(matches[0]))


def _oracle_sample(row: Mapping[str, Any], *, corpus_path: str) -> DecisionSample:
    snapshot = row["source_snapshot"]
    state = snapshot["state"]
    context = state["decision_context"]
    candidates = row["candidate_actions"]
    teacher_id = row["teacher"]["action_id"]
    teacher = next(candidate for candidate in candidates if candidate["action_id"] == teacher_id)
    return DecisionSample(
        sample_id=f"{row['cohort']}:{row['seed']}:{row['decision_index']}",
        category="card_reward",
        source=corpus_path,
        floor=state.get("floor"),
        act=state.get("act"),
        evidence_quality="complete",
        our_choice={"kind": teacher["kind"], "name": teacher["label"]},
        context={
            "can_bowl": context["has_singing_bowl"],
            "can_skip": any(candidate["kind"] == "skip" for candidate in candidates),
            "deck": [card["name"] for card in state["deck"]],
            "offered": [card["name"] for card in context["cards"]],
        },
    )


def label_bound_card_corpus(
    corpus: BoundCardCorpus,
    oracle: CardOracle,
    *,
    expected_bottled_commit: str,
) -> dict[str, Any]:
    """Map a clean, bound Bottled result to one legal action for every card row."""
    source = _mapping(oracle.source_metadata(), "Bottled source metadata")
    if source.get("mode") != "native_bottled":
        raise CardOnlyPilotBlocked("Bottled source mode mismatch")
    if source.get("strategy") != "REQUESTED_STRIKE":
        raise CardOnlyPilotBlocked("Bottled strategy mismatch")
    if source.get("dirty") is not False:
        raise CardOnlyPilotBlocked("Bottled checkout must be clean")
    if not expected_bottled_commit or source.get("commit") != expected_bottled_commit:
        raise CardOnlyPilotBlocked("Bottled commit mismatch")

    rows_by_cohort: dict[str, list[dict[str, Any]]] = {}
    label_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    disagreement_counts: Counter[str] = Counter()
    for cohort, rows in corpus.rows.items():
        labeled_rows: list[dict[str, Any]] = []
        for raw_row in rows:
            row = _validate_card_row(raw_row, cohort=cohort)
            candidates = row["candidate_actions"]
            result = oracle.evaluate(
                _oracle_sample(row, corpus_path=corpus.source["path"])
            )
            if getattr(result, "status", None) != "ok":
                raise CardOnlyPilotBlocked("Bottled card result is not supported")
            if getattr(result, "confidence", None) not in {"high", "medium"}:
                raise CardOnlyPilotBlocked("Bottled card confidence is not usable")
            result_source = _mapping(getattr(result, "source", None), "Bottled result source")
            if result_source != source:
                raise CardOnlyPilotBlocked("Bottled result source drift")
            selected = _candidate_for_bottled_label(result.label, candidates)
            teacher_id = row["teacher"]["action_id"]
            teacher = next(
                candidate for candidate in candidates if candidate["action_id"] == teacher_id
            )
            disagrees = selected["action_id"] != teacher_id
            label_counts[selected["kind"]] += 1
            confidence_counts[result.confidence] += 1
            disagreement_counts["disagree" if disagrees else "agree"] += 1
            labeled_rows.append(
                {
                    "bottled_action_id": selected["action_id"],
                    "bottled_confidence": result.confidence,
                    "bottled_family": selected["kind"],
                    "bottled_label": result.label,
                    "candidate_actions": copy.deepcopy(candidates),
                    "cohort": cohort,
                    "decision_index": row["decision_index"],
                    "seed": row["seed"],
                    "simple_agent_action_id": teacher_id,
                    "simple_agent_family": teacher["kind"],
                    "simple_agent_disagrees": disagrees,
                    "source_snapshot": copy.deepcopy(row["source_snapshot"]),
                    "source_snapshot_sha256": row["source_snapshot_sha256"],
                }
            )
        rows_by_cohort[cohort] = labeled_rows

    return {
        "bottled_source": source,
        "corpus_source": copy.deepcopy(corpus.source),
        "counts": {
            "confidence": dict(sorted(confidence_counts.items())),
            "label_family": dict(sorted(label_counts.items())),
            "simple_agent_agreement": dict(sorted(disagreement_counts.items())),
            "total": sum(label_counts.values()),
        },
        "rows": rows_by_cohort,
        "schema_version": LABEL_ARTIFACT_SCHEMA_VERSION,
    }


__all__ = [
    "ALLOWED_CORPUS_COHORTS",
    "BOUND_CARD_ROW_COUNTS",
    "BOUND_CORPUS_PATH",
    "BOUND_CORPUS_SHA256",
    "BOUND_CORPUS_SIZE_BYTES",
    "BOUND_REGISTRATION_SHA256",
    "BoundCardCorpus",
    "CardOnlyPilotBlocked",
    "label_bound_card_corpus",
    "load_bound_card_corpus",
]
