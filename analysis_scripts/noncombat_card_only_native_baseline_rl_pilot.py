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

import torch
import torch.nn.functional as functional

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as successor_runtime
from analysis_scripts.noncombat_card_acceptance_objective import (
    CardAcceptanceObjectiveError,
    build_card_acceptance_policy_terms,
)
from analysis_scripts.noncombat_card_acceptance_policy import (
    CardAcceptancePolicyError,
    build_family_features,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    SimulatorAdapterError,
    canonical_json_bytes,
    validate_candidates,
    validate_native_baseline_action,
    validate_provenance,
    validate_snapshot,
)
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    PolicyInputError,
    project_state_conditioned_policy_input,
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
WARM_START_MODEL_SEED = 0
WARM_START_SHUFFLE_SEED = 0
WARM_START_EPOCHS = 128
WARM_START_BATCH_SIZE = 32
WARM_START_LEARNING_RATE = 0.001
WARM_START_BETAS = (0.9, 0.999)
WARM_START_EPSILON = 1e-8
WARM_START_WEIGHT_DECAY = 0.0
WARM_START_MIN_FAMILY_AGREEMENT = 0.70
WARM_START_MIN_FAMILY_IMPROVEMENT = 0.10
WARM_START_MIN_EXACT_ACTION_AGREEMENT = 0.50
WARM_START_MIN_FAMILY_COVERAGE = 0.05
WARM_START_MAX_FAMILY_COVERAGE = 0.95


class CardOnlyPilotBlocked(RuntimeError):
    """Raised when the pilot must fail closed before training."""


class CardOracle(Protocol):
    def source_metadata(self) -> dict[str, Any]: ...

    def evaluate(self, sample: DecisionSample) -> Any: ...


@dataclass(frozen=True)
class BoundCardCorpus:
    source: dict[str, Any]
    rows: dict[str, tuple[dict[str, Any], ...]]


@dataclass(frozen=True)
class ProjectedCardLabel:
    cohort: str
    seed: int
    decision_index: int
    snapshot: dict[str, Any]
    candidates: tuple[dict[str, Any], ...]
    state_features: torch.Tensor
    candidate_features: torch.Tensor
    family_features: torch.Tensor
    family_order: tuple[str, ...]
    family_candidate_indices: tuple[tuple[int, ...], ...]
    target_action_id: str
    target_family: str
    source_adapter_api_version: str
    projection_adapter_api_version: str


@dataclass(frozen=True)
class CardWarmStartResult:
    bootstrap: Any
    configuration: dict[str, Any]
    zero_model: bytes
    final_model: bytes
    zero_validation: dict[str, Any]
    final_validation: dict[str, Any]
    gate: dict[str, Any]
    history: tuple[dict[str, Any], ...]
    optimizer_steps: int


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
                    "candidate_actions_sha256": row["candidate_actions_sha256"],
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


def _canonical_tensor(value: torch.Tensor) -> dict[str, Any]:
    tensor = value.detach().cpu().contiguous()
    if tensor.is_floating_point() and not torch.isfinite(tensor).all().item():
        raise CardOnlyPilotBlocked("model tensor must be finite")
    return {
        "dtype": str(tensor.dtype).removeprefix("torch."),
        "shape": list(tensor.shape),
        "values": tensor.reshape(-1).tolist(),
    }


def _canonical_module(value: torch.nn.Module) -> dict[str, Any]:
    if not isinstance(value, torch.nn.Module):
        raise CardOnlyPilotBlocked("model must be a torch module")
    return {
        name: _canonical_tensor(tensor)
        for name, tensor in sorted(value.state_dict().items())
    }


def encode_candidate_card_policy(bootstrap: Any) -> bytes:
    """Canonically encode only the candidate's hierarchical card policy."""
    try:
        policy = bootstrap.candidate.card_policy
        payload = {
            "conditional_ranker": _canonical_module(policy.conditional_ranker),
            "family_head": _canonical_module(policy.family_head),
            "schema_version": "noncombat-card-only-warm-start-model-v1",
        }
    except (AttributeError, TypeError) as exc:
        raise CardOnlyPilotBlocked("candidate card policy is invalid") from exc
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _warm_start_guard_bytes(bootstrap: Any) -> bytes:
    try:
        payload = {
            "candidate_frozen_noncard": _canonical_module(
                bootstrap.candidate.frozen_noncard_ranker
            ),
            "control_frozen_noncard": _canonical_module(
                bootstrap.control.frozen_noncard_ranker
            ),
            "control_shared_card": _canonical_module(
                bootstrap.control.shared_card_ranker
            ),
            "generators": {
                name: bytes(generator.get_state().tolist()).hex()
                for name, generator in sorted(bootstrap.generators.items())
            },
        }
    except (AttributeError, TypeError, ValueError) as exc:
        raise CardOnlyPilotBlocked("warm-start guard state is invalid") from exc
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def project_bottled_card_labels(
    label_artifact: Mapping[str, Any], *, cohort: str
) -> tuple[ProjectedCardLabel, ...]:
    """Project one labeled cohort through the current card feature bridge."""
    if cohort not in ALLOWED_CORPUS_COHORTS:
        raise CardOnlyPilotBlocked(f"protected or unsupported label cohort: {cohort}")
    artifact = _mapping(label_artifact, "Bottled label artifact")
    if artifact.get("schema_version") != LABEL_ARTIFACT_SCHEMA_VERSION:
        raise CardOnlyPilotBlocked("Bottled label artifact schema mismatch")
    rows_by_cohort = _mapping(artifact.get("rows"), "Bottled label rows")
    if set(rows_by_cohort) != set(ALLOWED_CORPUS_COHORTS):
        raise CardOnlyPilotBlocked("Bottled label cohorts mismatch")
    rows = rows_by_cohort.get(cohort)
    if not isinstance(rows, list) or not rows:
        raise CardOnlyPilotBlocked(f"{cohort} Bottled label rows must be nonempty")

    projected: list[ProjectedCardLabel] = []
    for index, raw_row in enumerate(rows):
        row = _mapping(raw_row, f"{cohort} labeled row[{index}]")
        if row.get("cohort") != cohort:
            raise CardOnlyPilotBlocked("Bottled labeled row cohort mismatch")
        snapshot = copy.deepcopy(
            _mapping(row.get("source_snapshot"), "Bottled labeled snapshot")
        )
        if row.get("source_snapshot_sha256") != hashlib.sha256(
            canonical_json_bytes(snapshot)
        ).hexdigest():
            raise CardOnlyPilotBlocked("Bottled labeled snapshot hash mismatch")
        source_adapter_api_version = snapshot.get("adapter_api_version")
        if source_adapter_api_version not in {
            "sts-lightspeed-noncombat-adapter-v2",
            ADAPTER_API_VERSION,
        }:
            raise CardOnlyPilotBlocked("card projection source API mismatch")
        if snapshot.get("category") != "card_reward":
            raise CardOnlyPilotBlocked("card projection category mismatch")
        if snapshot.get("decision_count") != row.get("decision_index"):
            raise CardOnlyPilotBlocked(
                "card projection decision_count and decision_index differ"
            )
        projection_snapshot = copy.deepcopy(snapshot)
        projection_snapshot["adapter_api_version"] = ADAPTER_API_VERSION
        source_round_trip = copy.deepcopy(projection_snapshot)
        source_round_trip["adapter_api_version"] = source_adapter_api_version
        if canonical_json_bytes(source_round_trip) != canonical_json_bytes(snapshot):
            raise CardOnlyPilotBlocked("card API projection changed non-version fields")
        candidates_value = row.get("candidate_actions")
        if not isinstance(candidates_value, list):
            raise CardOnlyPilotBlocked("Bottled labeled candidates must be a list")
        candidates = copy.deepcopy(candidates_value)
        if row.get("candidate_actions_sha256") != hashlib.sha256(
            canonical_json_bytes(candidates)
        ).hexdigest():
            raise CardOnlyPilotBlocked("Bottled labeled candidates hash mismatch")
        target_action_id = row.get("bottled_action_id")
        matches = [
            candidate
            for candidate in candidates
            if candidate.get("action_id") == target_action_id
        ]
        if len(matches) != 1:
            raise CardOnlyPilotBlocked(
                "Bottled target must map to exactly one labeled candidate"
            )
        target_family = matches[0].get("kind")
        if target_family != row.get("bottled_family"):
            raise CardOnlyPilotBlocked("Bottled target family mismatch")
        try:
            policy_input = project_state_conditioned_policy_input(
                projection_snapshot, candidates
            )
            family_batch = build_family_features(
                policy_input.candidate_features,
                candidates,
                category="card_reward",
            )
        except (PolicyInputError, CardAcceptancePolicyError) as exc:
            raise CardOnlyPilotBlocked(str(exc)) from exc
        projected.append(
            ProjectedCardLabel(
                cohort=cohort,
                seed=int(row["seed"]),
                decision_index=int(row["decision_index"]),
                snapshot=snapshot,
                candidates=tuple(candidates),
                state_features=policy_input.state_features.detach().clone(),
                candidate_features=policy_input.candidate_features.detach().clone(),
                family_features=family_batch.family_features.detach().clone(),
                family_order=family_batch.family_order,
                family_candidate_indices=family_batch.family_candidate_indices,
                target_action_id=str(target_action_id),
                target_family=str(target_family),
                source_adapter_api_version=str(source_adapter_api_version),
                projection_adapter_api_version=ADAPTER_API_VERSION,
            )
        )
    ordering = [(row.seed, row.decision_index) for row in projected]
    if ordering != sorted(ordering):
        raise CardOnlyPilotBlocked(f"{cohort} Bottled label rows are not ordered")
    return tuple(projected)


def _warm_start_losses(
    policy: Any, rows: Sequence[ProjectedCardLabel]
) -> tuple[torch.Tensor, torch.Tensor]:
    if not rows:
        raise CardOnlyPilotBlocked("warm-start loss rows must be nonempty")

    groups: dict[
        tuple[tuple[str, ...], str], list[ProjectedCardLabel]
    ] = {}
    for row in rows:
        key = (tuple(candidate["kind"] for candidate in row.candidates), row.target_family)
        groups.setdefault(key, []).append(row)

    family_losses: list[torch.Tensor] = []
    conditional_losses: list[torch.Tensor] = []
    for group_rows in groups.values():
        first = group_rows[0]
        if first.target_family not in first.family_order:
            raise CardOnlyPilotBlocked("target family is absent from policy output")
        if any(
            row.family_order != first.family_order
            or row.family_candidate_indices != first.family_candidate_indices
            or len(row.candidates) != len(first.candidates)
            for row in group_rows
        ):
            raise CardOnlyPilotBlocked("warm-start batch group shape differs")
        state_features = torch.stack([row.state_features for row in group_rows])
        candidate_features = torch.stack(
            [row.candidate_features for row in group_rows]
        )
        family_features = torch.stack([row.family_features for row in group_rows])
        conditional_logits = _batched_ranker_logits(
            policy.conditional_ranker, state_features, candidate_features
        )
        family_logits = _batched_ranker_logits(
            policy.family_head, state_features, family_features
        )
        family_index = first.family_order.index(first.target_family)
        family_targets = torch.full(
            (len(group_rows),), family_index, dtype=torch.long, device="cpu"
        )
        family_losses.extend(
            functional.cross_entropy(
                family_logits, family_targets, reduction="none"
            ).unbind()
        )

        family_candidate_indices = first.family_candidate_indices[family_index]
        index_tensor = torch.tensor(
            family_candidate_indices, dtype=torch.long, device="cpu"
        )
        selected_logits = conditional_logits.index_select(1, index_tensor)
        within_family_targets = []
        for row in group_rows:
            action_ids = tuple(candidate["action_id"] for candidate in row.candidates)
            target_index = action_ids.index(row.target_action_id)
            if target_index not in family_candidate_indices:
                raise CardOnlyPilotBlocked(
                    "target action is outside its target family"
                )
            within_family_targets.append(
                family_candidate_indices.index(target_index)
            )
        conditional_losses.extend(
            functional.cross_entropy(
                selected_logits,
                torch.tensor(within_family_targets, dtype=torch.long, device="cpu"),
                reduction="none",
            ).unbind()
        )
    return torch.stack(family_losses).mean(), torch.stack(conditional_losses).mean()


def _batched_ranker_logits(
    ranker: Any,
    state_features: torch.Tensor,
    candidate_features: torch.Tensor,
) -> torch.Tensor:
    if (
        state_features.ndim != 2
        or candidate_features.ndim != 3
        or state_features.shape[0] != candidate_features.shape[0]
        or state_features.shape[1] != candidate_features.shape[2]
    ):
        raise CardOnlyPilotBlocked("batched ranker feature shapes differ")
    if (
        state_features.device.type != "cpu"
        or candidate_features.device.type != "cpu"
        or state_features.dtype != torch.float32
        or candidate_features.dtype != torch.float32
    ):
        raise CardOnlyPilotBlocked("batched ranker features must be CPU float32")
    repeated_state = state_features.unsqueeze(1).expand(
        -1, candidate_features.shape[1], -1
    )
    combined = torch.cat((repeated_state, candidate_features), dim=2)
    logits = ranker.scorer(torch.relu(ranker.hidden(combined))).squeeze(-1)
    if logits.shape != candidate_features.shape[:2] or not torch.isfinite(
        logits
    ).all().item():
        raise CardOnlyPilotBlocked("batched ranker logits are invalid")
    return logits


def evaluate_card_warm_start(
    bootstrap: Any, rows: Sequence[ProjectedCardLabel]
) -> dict[str, Any]:
    """Evaluate one frozen candidate card model on already-projected labels."""
    if not rows:
        raise CardOnlyPilotBlocked("warm-start evaluation rows must be nonempty")
    before = encode_candidate_card_policy(bootstrap)
    policy = bootstrap.candidate.card_policy
    policy.eval()
    family_correct = 0
    action_correct = 0
    take_count = 0
    predictions: list[dict[str, Any]] = []
    with torch.no_grad():
        for row in rows:
            try:
                output = policy(
                    row.state_features,
                    row.candidate_features,
                    row.candidates,
                    category="card_reward",
                )
                provisional = build_card_acceptance_policy_terms(
                    output.family_logits,
                    output.conditional_logits,
                    row.candidates,
                    row.candidates[0]["action_id"],
                    category="card_reward",
                )
                selected_action_id = successor_runtime.select_two_stage_action(
                    provisional, greedy=True
                )
                terms = build_card_acceptance_policy_terms(
                    output.family_logits,
                    output.conditional_logits,
                    row.candidates,
                    selected_action_id,
                    category="card_reward",
                )
            except (
                CardAcceptanceObjectiveError,
                CardAcceptancePolicyError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                raise CardOnlyPilotBlocked(str(exc)) from exc
            selected_family = terms.selected_family
            family_correct += int(selected_family == row.target_family)
            action_correct += int(selected_action_id == row.target_action_id)
            take_count += int(selected_family == "take")
            predictions.append(
                {
                    "decision_index": row.decision_index,
                    "predicted_action_id": selected_action_id,
                    "predicted_family": selected_family,
                    "seed": row.seed,
                    "target_action_id": row.target_action_id,
                    "target_family": row.target_family,
                }
            )
    if encode_candidate_card_policy(bootstrap) != before:
        raise CardOnlyPilotBlocked("warm-start evaluation mutated the model")
    row_count = len(rows)
    take_rate = take_count / row_count
    return {
        "action_agreement": action_correct / row_count,
        "action_correct": action_correct,
        "family_agreement": family_correct / row_count,
        "family_correct": family_correct,
        "non_take_rate": 1.0 - take_rate,
        "predictions": predictions,
        "row_count": row_count,
        "take_rate": take_rate,
    }


def classify_card_warm_start_gate(
    zero_validation: Mapping[str, Any], final_validation: Mapping[str, Any]
) -> dict[str, Any]:
    zero = _mapping(zero_validation, "zero-step validation")
    final = _mapping(final_validation, "final validation")
    if zero.get("row_count") != final.get("row_count") or not isinstance(
        final.get("row_count"), int
    ):
        raise CardOnlyPilotBlocked("warm-start validation row counts differ")
    family_improvement = float(final["family_agreement"]) - float(
        zero["family_agreement"]
    )
    checks = {
        "exact_action_agreement": float(final["action_agreement"])
        >= WARM_START_MIN_EXACT_ACTION_AGREEMENT,
        "family_agreement": float(final["family_agreement"])
        >= WARM_START_MIN_FAMILY_AGREEMENT,
        "family_improvement": family_improvement
        >= WARM_START_MIN_FAMILY_IMPROVEMENT,
        "non_take_coverage": WARM_START_MIN_FAMILY_COVERAGE
        <= float(final["non_take_rate"])
        <= WARM_START_MAX_FAMILY_COVERAGE,
        "take_coverage": WARM_START_MIN_FAMILY_COVERAGE
        <= float(final["take_rate"])
        <= WARM_START_MAX_FAMILY_COVERAGE,
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "family_improvement": family_improvement,
        "passed": passed,
        "thresholds": {
            "maximum_family_coverage": WARM_START_MAX_FAMILY_COVERAGE,
            "minimum_exact_action_agreement": WARM_START_MIN_EXACT_ACTION_AGREEMENT,
            "minimum_family_agreement": WARM_START_MIN_FAMILY_AGREEMENT,
            "minimum_family_coverage": WARM_START_MIN_FAMILY_COVERAGE,
            "minimum_family_improvement": WARM_START_MIN_FAMILY_IMPROVEMENT,
        },
        "verdict": (
            "card_warm_start_gate_passed"
            if passed
            else "card_warm_start_gate_failed"
        ),
    }


def card_warm_start_configuration() -> dict[str, Any]:
    return {
        "batch_size": WARM_START_BATCH_SIZE,
        "betas": list(WARM_START_BETAS),
        "epochs": WARM_START_EPOCHS,
        "epsilon": WARM_START_EPSILON,
        "learning_rate": WARM_START_LEARNING_RATE,
        "loss": "mean-family-ce-plus-mean-selected-family-conditional-ce-v1",
        "model_seed": WARM_START_MODEL_SEED,
        "optimizer": "adam",
        "shuffle_seed": WARM_START_SHUFFLE_SEED,
        "weight_decay": WARM_START_WEIGHT_DECAY,
    }


def run_fixed_card_warm_start(
    bootstrap: Any, label_artifact: Mapping[str, Any]
) -> CardWarmStartResult:
    """Run the preregistered Bottled-supervised card-head warm start once."""
    train_rows = project_bottled_card_labels(label_artifact, cohort="train")
    validation_rows = project_bottled_card_labels(
        label_artifact, cohort="validation"
    )
    zero_model = encode_candidate_card_policy(bootstrap)
    expected_zero = successor_runtime.build_matched_bootstrap()
    if successor_runtime.encode_paired_bootstrap(bootstrap) != (
        successor_runtime.encode_paired_bootstrap(expected_zero)
    ):
        raise CardOnlyPilotBlocked(
            "warm-start bootstrap must equal the registered seed-zero state"
        )
    guard_before = _warm_start_guard_bytes(bootstrap)
    zero_validation = evaluate_card_warm_start(bootstrap, validation_rows)
    policy = bootstrap.candidate.card_policy
    parameters = tuple(policy.parameters())
    if not parameters or any(
        parameter.device.type != "cpu" or parameter.dtype != torch.float32
        for parameter in parameters
    ):
        raise CardOnlyPilotBlocked("warm-start parameters must be CPU float32")
    optimizer = torch.optim.Adam(
        parameters,
        lr=WARM_START_LEARNING_RATE,
        betas=WARM_START_BETAS,
        eps=WARM_START_EPSILON,
        weight_decay=WARM_START_WEIGHT_DECAY,
    )
    shuffle = torch.Generator(device="cpu")
    shuffle.manual_seed(WARM_START_SHUFFLE_SEED)
    history: list[dict[str, Any]] = []
    optimizer_steps = 0
    policy.train()
    for epoch in range(1, WARM_START_EPOCHS + 1):
        permutation = torch.randperm(len(train_rows), generator=shuffle).tolist()
        family_weighted_sum = 0.0
        conditional_weighted_sum = 0.0
        for start in range(0, len(permutation), WARM_START_BATCH_SIZE):
            batch_indices = permutation[start : start + WARM_START_BATCH_SIZE]
            batch = tuple(train_rows[index] for index in batch_indices)
            optimizer.zero_grad(set_to_none=True)
            family_loss, conditional_loss = _warm_start_losses(policy, batch)
            total_loss = family_loss + conditional_loss
            if not torch.isfinite(total_loss).item():
                raise CardOnlyPilotBlocked("warm-start loss must be finite")
            total_loss.backward()
            if any(
                parameter.grad is None
                or not torch.isfinite(parameter.grad).all().item()
                for parameter in parameters
            ):
                raise CardOnlyPilotBlocked("warm-start gradients must be complete and finite")
            optimizer.step()
            optimizer_steps += 1
            family_weighted_sum += float(family_loss.detach().item()) * len(batch)
            conditional_weighted_sum += float(
                conditional_loss.detach().item()
            ) * len(batch)
        family_mean = family_weighted_sum / len(train_rows)
        conditional_mean = conditional_weighted_sum / len(train_rows)
        history.append(
            {
                "conditional_cross_entropy": conditional_mean,
                "epoch": epoch,
                "family_cross_entropy": family_mean,
                "total_cross_entropy": family_mean + conditional_mean,
            }
        )
    policy.eval()
    final_model = encode_candidate_card_policy(bootstrap)
    if final_model == zero_model:
        raise CardOnlyPilotBlocked("warm-start did not change the candidate card model")
    if _warm_start_guard_bytes(bootstrap) != guard_before:
        raise CardOnlyPilotBlocked("warm-start changed guarded control or non-card state")
    final_validation = evaluate_card_warm_start(bootstrap, validation_rows)
    gate = classify_card_warm_start_gate(zero_validation, final_validation)
    return CardWarmStartResult(
        bootstrap=bootstrap,
        configuration=card_warm_start_configuration(),
        zero_model=zero_model,
        final_model=final_model,
        zero_validation=zero_validation,
        final_validation=final_validation,
        gate=gate,
        history=tuple(history),
        optimizer_steps=optimizer_steps,
    )


def require_card_warm_start_gate(result: CardWarmStartResult) -> Any:
    """Return the gated bootstrap or block before any residual RL access."""
    if not isinstance(result, CardWarmStartResult):
        raise CardOnlyPilotBlocked("warm-start result type mismatch")
    if result.gate.get("verdict") != "card_warm_start_gate_passed":
        raise CardOnlyPilotBlocked(
            "card warm-start gate failed; residual RL is not authorized"
        )
    return result.bootstrap


__all__ = [
    "ALLOWED_CORPUS_COHORTS",
    "BOUND_CARD_ROW_COUNTS",
    "BOUND_CORPUS_PATH",
    "BOUND_CORPUS_SHA256",
    "BOUND_CORPUS_SIZE_BYTES",
    "BOUND_REGISTRATION_SHA256",
    "BoundCardCorpus",
    "CardWarmStartResult",
    "CardOnlyPilotBlocked",
    "ProjectedCardLabel",
    "card_warm_start_configuration",
    "classify_card_warm_start_gate",
    "encode_candidate_card_policy",
    "evaluate_card_warm_start",
    "label_bound_card_corpus",
    "load_bound_card_corpus",
    "project_bottled_card_labels",
    "require_card_warm_start_gate",
    "run_fixed_card_warm_start",
]
