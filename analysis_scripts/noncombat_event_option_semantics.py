"""Source-bound event-option observations for the offline simulator bridge."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    SimulatorAdapterError,
    canonical_json_bytes,
    validate_candidates,
    validate_provenance,
    validate_snapshot,
)


EVENT_OPTION_SEMANTICS_SCHEMA_VERSION = (
    "sts-lightspeed-event-option-observation-v2"
)
_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_RELATIVE_PATH = Path(
    "reports/noncombat_event_option_observation_contract_20260802/contract.json"
)
_CONTRACT_PATH = _REPO_ROOT / _CONTRACT_RELATIVE_PATH
_CONTRACT_SHA256 = (
    "785e5db26d4cecaa843c7ee3e9e276fdc98c4b77b6a61e88f4520824a50bf3fc"
)
_CONTRACT_SCHEMA_VERSION = "noncombat-event-option-observation-contract-v1"
_CONTRACT_REGISTRY_SHA256 = (
    "cb525f7d077dcdc09d8c302625ac00dcf2e30aa9a60dffc8bafbbfa50eec9bb0"
)
_EVENT_COUNT = 25
_ALIAS_COUNT = 47
_EXPECTED_RULE_KIND_COUNTS = {
    "cursed_tome_phase": 1,
    "nloth_relic": 1,
    "static": 23,
}
_SIMULATOR_COMMIT = "7476a81954020087da31d41d16fddf475746ec2d"
_SIMULATOR_SOURCE_SHA256 = (
    "a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a"
)
_EVENT_OPTION_SEMANTICS_IDENTITY = {
    "contract_id": "sts_lightspeed_total_event_observation_v2",
    "observation_contract": {
        "alias_count": _ALIAS_COUNT,
        "event_count": _EVENT_COUNT,
        "path": _CONTRACT_RELATIVE_PATH.as_posix(),
        "schema_version": _CONTRACT_SCHEMA_VERSION,
        "sha256": _CONTRACT_SHA256,
    },
    "schema_version": EVENT_OPTION_SEMANTICS_SCHEMA_VERSION,
    "simulator_commit": _SIMULATOR_COMMIT,
    "simulator_source_sha256": _SIMULATOR_SOURCE_SHA256,
}


class EventOptionSemanticsError(SimulatorAdapterError):
    """Raised when exact source-bound event semantics cannot be resolved."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EventOptionSemanticsError(
                "event_option_semantics_contract_duplicate_key", key
            )
        result[key] = value
    return result


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise EventOptionSemanticsError(
            "event_option_semantics_input_invalid", label
        )
    return dict(value)


def _sequence(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise EventOptionSemanticsError(
            "event_option_semantics_input_invalid", label
        )
    return list(value)


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str):
    actual = set(value)
    if actual != expected:
        raise EventOptionSemanticsError(
            "event_option_semantics_input_invalid",
            {
                "label": label,
                "missing": sorted(expected - actual),
                "unexpected": sorted(actual - expected),
            },
        )


def _read_contract() -> tuple[dict[str, Any], bytes]:
    try:
        contract_bytes = _CONTRACT_PATH.read_bytes()
    except OSError as exc:
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_missing", str(_CONTRACT_PATH)
        ) from exc
    actual_sha256 = hashlib.sha256(contract_bytes).hexdigest()
    if actual_sha256 != _CONTRACT_SHA256:
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_hash_mismatch",
            {"actual": actual_sha256, "expected": _CONTRACT_SHA256},
        )
    try:
        contract = json.loads(
            contract_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except EventOptionSemanticsError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_json_invalid", str(exc)
        ) from exc
    normalized = _validate_contract(contract)
    return normalized, contract_bytes


def _validate_contract(value: object) -> dict[str, Any]:
    contract = _mapping(value, "contract")
    if contract.get("schema_version") != _CONTRACT_SCHEMA_VERSION:
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_schema_mismatch"
        )
    if (
        contract.get("event_count") != _EVENT_COUNT
        or contract.get("alias_count") != _ALIAS_COUNT
        or contract.get("unaccounted_surface_count") != 0
        or contract.get("rule_kind_counts") != _EXPECTED_RULE_KIND_COUNTS
        or contract.get("registry_sha256") != _CONTRACT_REGISTRY_SHA256
    ):
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_counts_mismatch"
        )
    authority = _mapping(contract.get("authority"), "contract.authority")
    if not authority or any(value is not False for value in authority.values()):
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_authority_invalid"
        )
    if contract.get("resolver_ready") is not False or contract.get(
        "adapter_ready"
    ) is not False:
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_readiness_invalid"
        )

    events = _sequence(contract.get("events"), "contract.events")
    if len(events) != _EVENT_COUNT:
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_counts_mismatch"
        )
    canonical_ids = []
    upstream_ids = []
    aliases = []
    kind_counts: dict[str, int] = {}
    for index, raw_rule in enumerate(events):
        rule = _mapping(raw_rule, f"contract.events[{index}]")
        canonical_id = rule.get("canonical_id")
        upstream_id = rule.get("upstream_event_id")
        event_name = rule.get("event_game_name")
        current_id = rule.get("current_event_id")
        kind = rule.get("kind")
        if not all(
            isinstance(field, str) and field
            for field in (canonical_id, upstream_id, event_name, current_id, kind)
        ):
            raise EventOptionSemanticsError(
                "event_option_semantics_contract_rule_invalid", index
            )
        canonical_ids.append(canonical_id)
        upstream_ids.append(upstream_id)
        rule_aliases = _sequence(rule.get("aliases"), f"rule[{index}].aliases")
        if not rule_aliases or not all(
            isinstance(alias, str) and alias for alias in rule_aliases
        ):
            raise EventOptionSemanticsError(
                "event_option_semantics_contract_rule_invalid", canonical_id
            )
        aliases.extend(rule_aliases)
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    if (
        len(canonical_ids) != len(set(canonical_ids))
        or len(upstream_ids) != len(set(upstream_ids))
        or len(aliases) != _ALIAS_COUNT
        or len(aliases) != len(set(aliases))
        or kind_counts != _EXPECTED_RULE_KIND_COUNTS
    ):
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_identity_ambiguous"
        )
    return contract


def event_option_semantics_identity() -> dict[str, Any]:
    """Return the immutable identity of the total observation resolver."""

    return copy.deepcopy(_EVENT_OPTION_SEMANTICS_IDENTITY)


def _validate_provenance(
    simulator_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        normalized = validate_provenance(
            copy.deepcopy(dict(simulator_provenance))
        )
    except (TypeError, ValueError) as exc:
        raise EventOptionSemanticsError(
            "event_option_semantics_input_invalid", str(exc)
        ) from exc
    actual = {
        "simulator_commit": normalized["simulator_commit"],
        "simulator_source_sha256": normalized["simulator_source_sha256"],
    }
    expected = {
        "simulator_commit": _SIMULATOR_COMMIT,
        "simulator_source_sha256": _SIMULATOR_SOURCE_SHA256,
    }
    if actual != expected:
        raise EventOptionSemanticsError(
            "event_option_semantics_provenance_mismatch",
            {"actual": actual, "expected": expected},
        )
    return normalized


def _candidate_indices(
    candidates: Sequence[Mapping[str, Any]], event_id: str
) -> list[int]:
    indices = []
    for position, candidate in enumerate(candidates):
        if candidate.get("kind") != "event_option":
            raise EventOptionSemanticsError(
                "event_option_semantics_candidate_kind_mismatch",
                candidate.get("action_id"),
            )
        raw = _mapping(candidate.get("raw"), f"candidate[{position}].raw")
        if raw.get("event_id") != event_id:
            raise EventOptionSemanticsError(
                "event_option_semantics_candidate_event_mismatch",
                candidate.get("action_id"),
            )
        choice_index = raw.get("idx1")
        if (
            isinstance(choice_index, bool)
            or not isinstance(choice_index, int)
            or choice_index < 0
        ):
            raise EventOptionSemanticsError(
                "event_option_semantics_candidate_index_invalid",
                candidate.get("action_id"),
            )
        if choice_index in indices:
            raise EventOptionSemanticsError(
                "event_option_semantics_candidate_index_duplicate", choice_index
            )
        indices.append(choice_index)
    if indices != sorted(indices):
        raise EventOptionSemanticsError(
            "event_option_semantics_candidate_order_invalid", indices
        )
    return indices


def _static_labels(rule: Mapping[str, Any]) -> dict[int, str]:
    labels = {}
    for raw_option in _sequence(rule.get("options"), "rule.options"):
        option = _mapping(raw_option, "rule.option")
        index = option.get("simulator_choice_index")
        label = option.get("label")
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or index < 0
            or not isinstance(label, str)
            or not label
            or index in labels
        ):
            raise EventOptionSemanticsError(
                "event_option_semantics_contract_rule_invalid",
                rule.get("canonical_id"),
            )
        labels[index] = label
    return labels


def _cursed_tome_labels(
    rule: Mapping[str, Any], event_data: object, indices: list[int]
) -> dict[int, str]:
    if isinstance(event_data, bool) or not isinstance(event_data, int):
        raise EventOptionSemanticsError(
            "event_option_semantics_phase_invalid", event_data
        )
    matching = [
        _mapping(raw, "rule.phase")
        for raw in _sequence(rule.get("phases"), "rule.phases")
        if isinstance(raw, Mapping) and raw.get("event_data") == event_data
    ]
    if len(matching) != 1:
        raise EventOptionSemanticsError(
            "event_option_semantics_phase_unsupported", event_data
        )
    expected_indices = matching[0].get("simulator_choice_indices")
    if indices != expected_indices:
        raise EventOptionSemanticsError(
            "event_option_semantics_phase_candidates_mismatch",
            {"actual": indices, "expected": expected_indices},
        )
    return _static_labels(rule)


def _nloth_labels(
    *,
    snapshot_api_version: str,
    state: Mapping[str, Any],
    context: Mapping[str, Any],
    indices: list[int],
) -> dict[int, str]:
    if indices != [0, 1, 2]:
        raise EventOptionSemanticsError(
            "event_option_semantics_nloth_candidate_indices_mismatch", indices
        )
    relics_value = state.get("relics")
    offered_value = context.get("offered_relics")
    if not isinstance(relics_value, list) or not isinstance(offered_value, list):
        raise EventOptionSemanticsError(
            "event_option_semantics_nloth_context_missing"
        )
    if snapshot_api_version != ADAPTER_API_VERSION:
        raise EventOptionSemanticsError(
            "event_option_semantics_nloth_snapshot_api_unsupported",
            snapshot_api_version,
        )
    if len(offered_value) != 2:
        raise EventOptionSemanticsError(
            "event_option_semantics_nloth_offer_count_mismatch"
        )
    labels = {2: "Leave"}
    slots = []
    expected_keys = {
        "relic_id",
        "relic_name",
        "relic_slot",
        "simulator_choice_index",
    }
    for expected_index, raw_record in enumerate(offered_value):
        record = _mapping(raw_record, f"offered_relics[{expected_index}]")
        _require_exact_keys(record, expected_keys, f"offered_relics[{expected_index}]")
        if record.get("simulator_choice_index") != expected_index:
            raise EventOptionSemanticsError(
                "event_option_semantics_nloth_choice_index_mismatch",
                expected_index,
            )
        slot = record.get("relic_slot")
        if (
            isinstance(slot, bool)
            or not isinstance(slot, int)
            or not 0 <= slot < len(relics_value)
        ):
            raise EventOptionSemanticsError(
                "event_option_semantics_nloth_relic_slot_invalid", slot
            )
        relic = _mapping(relics_value[slot], f"state.relics[{slot}]")
        relic_id = record.get("relic_id")
        relic_name = record.get("relic_name")
        if (
            not isinstance(relic_id, str)
            or not relic_id
            or not isinstance(relic_name, str)
            or not relic_name
            or relic_id != relic.get("id")
            or relic_name != relic.get("name")
        ):
            raise EventOptionSemanticsError(
                "event_option_semantics_nloth_relic_mismatch", expected_index
            )
        slots.append(slot)
        labels[expected_index] = f"Offer {relic_name}"
    if len(slots) != len(set(slots)):
        raise EventOptionSemanticsError(
            "event_option_semantics_nloth_relic_slot_duplicate"
        )
    return labels


def resolve_event_option_observation(
    *,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    simulator_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve one exact Current-facing event observation and reverse mapping."""

    before_snapshot = canonical_json_bytes(snapshot)
    before_candidates = canonical_json_bytes(candidates)
    before_provenance = canonical_json_bytes(simulator_provenance)
    contract, contract_bytes = _read_contract()

    try:
        normalized_snapshot = validate_snapshot(copy.deepcopy(dict(snapshot)))
        normalized_candidates = validate_candidates(
            copy.deepcopy(list(candidates)), category="event"
        )
    except (TypeError, ValueError) as exc:
        raise EventOptionSemanticsError(
            "event_option_semantics_input_invalid", str(exc)
        ) from exc
    _validate_provenance(simulator_provenance)

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
    matching_rules = [
        _mapping(raw_rule, "contract.event")
        for raw_rule in contract["events"]
        if isinstance(raw_rule, Mapping)
        and raw_rule.get("upstream_event_id") == event_id
    ]
    if len(matching_rules) != 1:
        raise EventOptionSemanticsError(
            "event_option_semantics_event_unsupported", event_id
        )
    rule = matching_rules[0]
    if context.get("event_name") != rule.get("event_game_name"):
        raise EventOptionSemanticsError(
            "event_option_semantics_event_identity_mismatch",
            {
                "actual": context.get("event_name"),
                "expected": rule.get("event_game_name"),
            },
        )
    event_data = context.get("event_data")
    if isinstance(event_data, bool) or not isinstance(event_data, int):
        raise EventOptionSemanticsError(
            "event_option_semantics_phase_invalid", event_data
        )
    indices = _candidate_indices(normalized_candidates, event_id)

    kind = rule.get("kind")
    if kind == "static":
        labels = _static_labels(rule)
    elif kind == "cursed_tome_phase":
        labels = _cursed_tome_labels(rule, event_data, indices)
    elif kind == "nloth_relic":
        labels = _nloth_labels(
            snapshot_api_version=normalized_snapshot["adapter_api_version"],
            state=state,
            context=context,
            indices=indices,
        )
    else:
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_rule_invalid", kind
        )
    unknown_indices = [index for index in indices if index not in labels]
    if unknown_indices:
        raise EventOptionSemanticsError(
            "event_option_semantics_candidate_index_unsupported", unknown_indices
        )

    options = []
    for current_position, simulator_choice_index in enumerate(indices):
        label = labels[simulator_choice_index]
        options.append(
            {
                "choice_index": current_position,
                "current_position": current_position,
                "label": label,
                "simulator_choice_index": simulator_choice_index,
                "text": label,
            }
        )
    observation = {
        "canonical_id": rule["canonical_id"],
        "current_event_id": rule["current_event_id"],
        "event_data": event_data,
        "options": options,
    }

    if canonical_json_bytes(snapshot) != before_snapshot:
        raise EventOptionSemanticsError("event_option_semantics_snapshot_mutated")
    if canonical_json_bytes(candidates) != before_candidates:
        raise EventOptionSemanticsError("event_option_semantics_candidates_mutated")
    if canonical_json_bytes(simulator_provenance) != before_provenance:
        raise EventOptionSemanticsError("event_option_semantics_provenance_mutated")
    try:
        after_contract = _CONTRACT_PATH.read_bytes()
    except OSError as exc:
        raise EventOptionSemanticsError(
            "event_option_semantics_contract_mutated"
        ) from exc
    if after_contract != contract_bytes:
        raise EventOptionSemanticsError("event_option_semantics_contract_mutated")
    return observation


def resolve_event_option_semantics(
    *,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    simulator_provenance: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Compatibility wrapper returning the versioned observation rows."""

    return resolve_event_option_observation(
        snapshot=snapshot,
        candidates=candidates,
        simulator_provenance=simulator_provenance,
    )["options"]
