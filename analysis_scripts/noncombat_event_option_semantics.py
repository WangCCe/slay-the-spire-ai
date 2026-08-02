"""Source-bound event-option semantics for the offline simulator bridge."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    SimulatorAdapterError,
    canonical_json_bytes,
    validate_candidates,
    validate_provenance,
    validate_snapshot,
)


EVENT_OPTION_SEMANTICS_SCHEMA_VERSION = (
    "sts-lightspeed-event-option-semantics-v1"
)

_EVENT_OPTION_SEMANTICS_IDENTITY = {
    "contract_id": "sts_lightspeed_liars_game_event_options_v1",
    "schema_version": EVENT_OPTION_SEMANTICS_SCHEMA_VERSION,
    "simulator_commit": "7476a81954020087da31d41d16fddf475746ec2d",
    "simulator_source_sha256": (
        "a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a"
    ),
    "source_bindings": {
        "effects": "src/game/GameContext.cpp:Event::THE_SSSSSERPENT",
        "event_identity": "include/constants/Events.h:Event::THE_SSSSSERPENT",
        "labels": "src/sim/ConsoleSimulator.cpp:Event::THE_SSSSSERPENT",
        "legal_indices": (
            "src/sim/search/GameAction.cpp:Event::THE_SSSSSERPENT"
        ),
    },
    "supported_event_states": [
        {
            "event_data": 0,
            "event_id": "Liars Game",
            "event_name": "The Ssssserpent",
            "legal_indices": [0, 1],
        }
    ],
}


class EventOptionSemanticsError(SimulatorAdapterError):
    """Raised when exact source-bound event semantics cannot be resolved."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise EventOptionSemanticsError(
            "event_option_semantics_input_invalid", label
        )
    return dict(value)


def event_option_semantics_identity() -> dict[str, Any]:
    """Return the immutable identity of the currently supported semantics."""

    return copy.deepcopy(_EVENT_OPTION_SEMANTICS_IDENTITY)


def resolve_event_option_semantics(
    *,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    simulator_provenance: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Resolve exact event semantics for the narrow registered source state."""

    before_snapshot = canonical_json_bytes(snapshot)
    before_candidates = canonical_json_bytes(candidates)
    before_provenance = canonical_json_bytes(simulator_provenance)

    try:
        normalized_snapshot = validate_snapshot(copy.deepcopy(dict(snapshot)))
        normalized_candidates = validate_candidates(
            copy.deepcopy(list(candidates)), category="event"
        )
        normalized_provenance = validate_provenance(
            copy.deepcopy(dict(simulator_provenance))
        )
    except (TypeError, ValueError) as exc:
        raise EventOptionSemanticsError(
            "event_option_semantics_input_invalid", str(exc)
        ) from exc

    identity = _EVENT_OPTION_SEMANTICS_IDENTITY
    actual_source_identity = {
        "simulator_commit": normalized_provenance["simulator_commit"],
        "simulator_source_sha256": normalized_provenance[
            "simulator_source_sha256"
        ],
    }
    expected_source_identity = {
        "simulator_commit": identity["simulator_commit"],
        "simulator_source_sha256": identity["simulator_source_sha256"],
    }
    if actual_source_identity != expected_source_identity:
        raise EventOptionSemanticsError(
            "event_option_semantics_provenance_mismatch",
            {"actual": actual_source_identity, "expected": expected_source_identity},
        )

    if normalized_snapshot.get("category") != "event":
        raise EventOptionSemanticsError(
            "event_option_semantics_category_mismatch",
            normalized_snapshot.get("category"),
        )
    state = _mapping(normalized_snapshot.get("state"), "snapshot.state")
    context = _mapping(
        state.get("decision_context"), "snapshot.state.decision_context"
    )
    event_id = context.get("event_id")
    if event_id != "Liars Game":
        raise EventOptionSemanticsError(
            "event_option_semantics_event_unsupported", event_id
        )
    if context.get("event_name") != "The Ssssserpent":
        raise EventOptionSemanticsError(
            "event_option_semantics_event_identity_mismatch",
            context.get("event_name"),
        )
    if context.get("event_data") != 0:
        raise EventOptionSemanticsError(
            "event_option_semantics_phase_unsupported", context.get("event_data")
        )

    candidate_indices = []
    for index, candidate in enumerate(normalized_candidates):
        if candidate.get("kind") != "event_option":
            raise EventOptionSemanticsError(
                "event_option_semantics_candidate_kind_mismatch",
                candidate.get("action_id"),
            )
        raw = _mapping(candidate.get("raw"), f"candidate[{index}].raw")
        if raw.get("event_id") != event_id:
            raise EventOptionSemanticsError(
                "event_option_semantics_candidate_event_mismatch",
                candidate.get("action_id"),
            )
        choice_index = raw.get("idx1")
        if isinstance(choice_index, bool) or not isinstance(choice_index, int):
            raise EventOptionSemanticsError(
                "event_option_semantics_candidate_index_invalid",
                candidate.get("action_id"),
            )
        if choice_index in candidate_indices:
            raise EventOptionSemanticsError(
                "event_option_semantics_candidate_index_duplicate", choice_index
            )
        candidate_indices.append(choice_index)
    candidate_indices.sort()
    if candidate_indices != [0, 1]:
        raise EventOptionSemanticsError(
            "event_option_semantics_candidate_indices_mismatch",
            {"actual": candidate_indices, "expected": [0, 1]},
        )

    ascension = state.get("ascension")
    if isinstance(ascension, bool) or not isinstance(ascension, int) or ascension < 0:
        raise EventOptionSemanticsError(
            "event_option_semantics_ascension_invalid", ascension
        )
    gold = 150 if ascension >= 15 else 175
    semantics = [
        {
            "choice_index": 0,
            "label": "Agree",
            "text": f"Gain {gold} Gold. Become Cursed - Doubt.",
        },
        {
            "choice_index": 1,
            "label": "Disagree",
            "text": "Nothing happens.",
        },
    ]

    if canonical_json_bytes(snapshot) != before_snapshot:
        raise EventOptionSemanticsError("event_option_semantics_snapshot_mutated")
    if canonical_json_bytes(candidates) != before_candidates:
        raise EventOptionSemanticsError("event_option_semantics_candidates_mutated")
    if canonical_json_bytes(simulator_provenance) != before_provenance:
        raise EventOptionSemanticsError("event_option_semantics_provenance_mutated")
    return semantics
