"""Bounded, replayable non-combat exploration primitives.

The default import path is inert. Live artifacts are only created by an explicit
controller after a validated experiment configuration is supplied.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Optional


CONFIG_ENV = "STS_NONCOMBAT_EXPLORATION_CONFIG"
CONFIG_SCHEMA_VERSION = "noncombat-exploration-config-v1"
EXECUTABLE_CATEGORIES = frozenset({"card_reward", "shop"})
MAX_CATEGORY_RATE_BPS = 1_000
MAX_ALTERNATIVE_ATTEMPTS_PER_RUN = 2
SELECTION_SCHEMA_VERSION = "noncombat-exploration-selection-v1"
PROPOSAL_ROLLOUT_MODES = frozenset({"executable", "shadow", "ineligible"})
DRAW_BUCKET_COUNT = 10_000

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class ExplorationConfigurationError(ValueError):
    """Raised when an exploration configuration is incomplete or unsafe."""


class ExplorationProposalError(ValueError):
    """Raised when candidate identities or proposal mappings are ambiguous."""


class ExplorationSamplingError(ValueError):
    """Raised when an action distribution cannot be sampled safely."""


@dataclass(frozen=True)
class ExplorationConfig:
    schema_version: str
    session_id: str
    seed: int
    enabled_categories: tuple[str, ...]
    category_rates_bps: Mapping[str, int]
    per_run_alternative_budget: int
    trace_path: Path
    manifest_path: Path
    source_commit: str
    source_path: Optional[Path] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "enabled_categories", tuple(self.enabled_categories))
        object.__setattr__(
            self,
            "category_rates_bps",
            MappingProxyType(
                {
                    category: int(self.category_rates_bps[category])
                    for category in sorted(self.category_rates_bps)
                }
            ),
        )

    def rate_bps(self, category: str) -> int:
        return self.category_rates_bps[category]


@dataclass(frozen=True)
class ExplorationCandidate:
    action_id: str
    kind: str
    label: str
    available: bool = True
    executable: bool = True
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, str) or not self.action_id.strip():
            raise ExplorationProposalError("candidate action_id must be non-empty")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ExplorationProposalError("candidate kind must be non-empty")
        if not isinstance(self.label, str):
            raise ExplorationProposalError("candidate label must be a string")
        if not isinstance(self.available, bool) or not isinstance(self.executable, bool):
            raise ExplorationProposalError(
                "candidate availability and executability must be booleans"
            )
        object.__setattr__(self, "action_id", self.action_id.strip())
        object.__setattr__(self, "kind", self.kind.strip())
        object.__setattr__(self, "raw", _freeze_json(self.raw))

    def to_record(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "kind": self.kind,
            "label": self.label,
            "available": self.available,
            "executable": self.executable,
            "raw": _plain_json(self.raw),
        }


@dataclass(frozen=True)
class NonCombatProposal:
    category: str
    baseline_action_id: str
    alternative_action_id: str
    candidates: tuple[ExplorationCandidate, ...]
    state: Mapping[str, Any]
    execution_eligible: bool
    rollout_mode: str
    ineligibility_reason: str = ""
    state_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.category, str) or not self.category.strip():
            raise ExplorationProposalError("proposal category must be non-empty")
        if self.rollout_mode not in PROPOSAL_ROLLOUT_MODES:
            raise ExplorationProposalError("unsupported proposal rollout_mode")
        if not isinstance(self.execution_eligible, bool):
            raise ExplorationProposalError("execution_eligible must be a boolean")
        if self.execution_eligible and self.rollout_mode != "executable":
            raise ExplorationProposalError(
                "execution-eligible proposal must use executable rollout_mode"
            )
        if not self.execution_eligible and self.rollout_mode == "executable":
            raise ExplorationProposalError(
                "ineligible proposal cannot use executable rollout_mode"
            )
        if not self.execution_eligible and not self.ineligibility_reason:
            raise ExplorationProposalError(
                "ineligible proposal requires ineligibility_reason"
            )

        frozen_candidates = tuple(self.candidates)
        if len(frozen_candidates) < 2:
            raise ExplorationProposalError(
                "proposal requires baseline and alternative candidates"
            )
        if not all(isinstance(candidate, ExplorationCandidate) for candidate in frozen_candidates):
            raise ExplorationProposalError(
                "proposal candidates must be ExplorationCandidate instances"
            )
        candidate_ids = tuple(candidate.action_id for candidate in frozen_candidates)
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ExplorationProposalError("duplicate candidate action_id")
        by_id = {candidate.action_id: candidate for candidate in frozen_candidates}
        if self.baseline_action_id not in by_id:
            raise ExplorationProposalError(
                "baseline_action_id does not map to a candidate"
            )
        if self.alternative_action_id not in by_id:
            raise ExplorationProposalError(
                "alternative_action_id does not map to a candidate"
            )
        if self.baseline_action_id == self.alternative_action_id:
            raise ExplorationProposalError(
                "baseline_action_id and alternative_action_id must differ"
            )
        if self.execution_eligible:
            for action_id in (self.baseline_action_id, self.alternative_action_id):
                candidate = by_id[action_id]
                if not candidate.available or not candidate.executable:
                    raise ExplorationProposalError(
                        f"execution candidate is unavailable: {action_id}"
                    )

        frozen_state = _freeze_json(self.state)
        object.__setattr__(self, "category", self.category.strip())
        object.__setattr__(self, "candidates", frozen_candidates)
        object.__setattr__(self, "state", frozen_state)
        object.__setattr__(
            self,
            "state_hash",
            _sha256_json(
                {
                    "category": self.category.strip(),
                    "state": _plain_json(frozen_state),
                    "candidates": [
                        candidate.to_record() for candidate in frozen_candidates
                    ],
                }
            ),
        )

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        return tuple(candidate.action_id for candidate in self.candidates)


@dataclass(frozen=True)
class ActionProbability:
    action_id: str
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, str) or not self.action_id:
            raise ExplorationSamplingError("probability action_id must be non-empty")
        if isinstance(self.numerator, bool) or not isinstance(self.numerator, int):
            raise ExplorationSamplingError("probability numerator must be an integer")
        if isinstance(self.denominator, bool) or not isinstance(self.denominator, int):
            raise ExplorationSamplingError("probability denominator must be an integer")
        if self.denominator <= 0 or not 0 <= self.numerator <= self.denominator:
            raise ExplorationSamplingError("invalid exact action probability")

    @property
    def value(self) -> float:
        return self.numerator / self.denominator

    def to_record(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "value": self.value,
        }


@dataclass(frozen=True)
class ExplorationSelection:
    schema_version: str
    session_id: str
    trajectory_session_id: str
    decision_index: int
    category: str
    state_hash: str
    distribution: tuple[ActionProbability, ...]
    distribution_hash: str
    draw_input_hash: str
    draw_counter: int
    draw_u64: int
    draw_bucket: int
    selected_action_id: str
    selected_probability_numerator: int
    selected_probability_denominator: int

    @property
    def selected_action_probability(self) -> float:
        return self.selected_probability_numerator / self.selected_probability_denominator

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "trajectory_session_id": self.trajectory_session_id,
            "decision_index": self.decision_index,
            "category": self.category,
            "state_hash": self.state_hash,
            "distribution": [entry.to_record() for entry in self.distribution],
            "distribution_hash": self.distribution_hash,
            "draw_input_hash": self.draw_input_hash,
            "draw_counter": self.draw_counter,
            "draw_u64": self.draw_u64,
            "draw_bucket": self.draw_bucket,
            "selected_action_id": self.selected_action_id,
            "selected_probability_numerator": self.selected_probability_numerator,
            "selected_probability_denominator": self.selected_probability_denominator,
            "selected_action_probability": self.selected_action_probability,
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.to_record())


@dataclass(frozen=True)
class ReplayValidation:
    valid: bool
    errors: tuple[str, ...] = ()


def sample_exploration(
    config: ExplorationConfig,
    proposal: NonCombatProposal,
    *,
    trajectory_session_id: str,
    decision_index: int,
) -> ExplorationSelection:
    """Sample one exact binary Current/abstention behavior distribution."""
    if proposal.category not in config.enabled_categories:
        raise ExplorationSamplingError(
            f"proposal category is not enabled: {proposal.category}"
        )
    if not proposal.execution_eligible or proposal.rollout_mode != "executable":
        raise ExplorationSamplingError(
            f"proposal is not execution eligible: {proposal.ineligibility_reason or proposal.rollout_mode}"
        )
    if not isinstance(trajectory_session_id, str) or not trajectory_session_id:
        raise ExplorationSamplingError("trajectory_session_id must be non-empty")
    if (
        isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index < 0
    ):
        raise ExplorationSamplingError("decision_index must be a non-negative integer")

    epsilon_bps = config.rate_bps(proposal.category)
    distribution = (
        ActionProbability(
            action_id=proposal.baseline_action_id,
            numerator=DRAW_BUCKET_COUNT - epsilon_bps,
            denominator=DRAW_BUCKET_COUNT,
        ),
        ActionProbability(
            action_id=proposal.alternative_action_id,
            numerator=epsilon_bps,
            denominator=DRAW_BUCKET_COUNT,
        ),
    )
    if sum(entry.numerator for entry in distribution) != DRAW_BUCKET_COUNT:
        raise ExplorationSamplingError("exact distribution does not sum to one")

    draw_input = {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "session_id": config.session_id,
        "seed": config.seed,
        "trajectory_session_id": trajectory_session_id,
        "decision_index": decision_index,
        "category": proposal.category,
        "state_hash": proposal.state_hash,
        "candidate_action_ids": list(proposal.candidate_ids),
        "baseline_action_id": proposal.baseline_action_id,
        "alternative_action_id": proposal.alternative_action_id,
        "epsilon_bps": epsilon_bps,
    }
    draw_input_json = _canonical_json(draw_input)
    draw_input_hash = hashlib.sha256(draw_input_json.encode("utf-8")).hexdigest()
    draw_counter, draw_u64, draw_bucket = _exact_uniform_bucket(
        draw_input_json.encode("utf-8")
    )
    selected_action_id = (
        proposal.alternative_action_id
        if draw_bucket < epsilon_bps
        else proposal.baseline_action_id
    )
    selected_probability = next(
        entry for entry in distribution if entry.action_id == selected_action_id
    )
    distribution_hash = _sha256_json(
        [entry.to_record() for entry in distribution]
    )
    return ExplorationSelection(
        schema_version=SELECTION_SCHEMA_VERSION,
        session_id=config.session_id,
        trajectory_session_id=trajectory_session_id,
        decision_index=decision_index,
        category=proposal.category,
        state_hash=proposal.state_hash,
        distribution=distribution,
        distribution_hash=distribution_hash,
        draw_input_hash=draw_input_hash,
        draw_counter=draw_counter,
        draw_u64=draw_u64,
        draw_bucket=draw_bucket,
        selected_action_id=selected_action_id,
        selected_probability_numerator=selected_probability.numerator,
        selected_probability_denominator=selected_probability.denominator,
    )


def verify_exploration_selection(
    config: ExplorationConfig,
    proposal: NonCombatProposal,
    selection: ExplorationSelection,
    *,
    trajectory_session_id: str,
    decision_index: int,
) -> ReplayValidation:
    """Recompute a selection and report every mismatched evidence field."""
    try:
        expected = sample_exploration(
            config,
            proposal,
            trajectory_session_id=trajectory_session_id,
            decision_index=decision_index,
        )
    except ExplorationSamplingError as exc:
        return ReplayValidation(False, (f"sampling_error:{exc}",))

    errors = []
    for item in fields(ExplorationSelection):
        name = item.name
        if getattr(selection, name) != getattr(expected, name):
            errors.append(f"{name}_mismatch")
    return ReplayValidation(not errors, tuple(errors))


def _exact_uniform_bucket(draw_input: bytes) -> tuple[int, int, int]:
    """Use deterministic rejection sampling for an exact 1/10,000 bucket."""
    population = 1 << 64
    acceptance_limit = population - (population % DRAW_BUCKET_COUNT)
    for counter in range(1_000_000):
        digest = hashlib.sha256(
            draw_input + b"\x00" + str(counter).encode("ascii")
        ).digest()
        draw_u64 = int.from_bytes(digest[:8], byteorder="big", signed=False)
        if draw_u64 < acceptance_limit:
            return counter, draw_u64, draw_u64 % DRAW_BUCKET_COUNT
    raise ExplorationSamplingError("unable to derive an exact exploration draw")


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        frozen = {
            str(key): _freeze_json(value[key]) for key in sorted(value, key=str)
        }
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ExplorationProposalError(
        f"value is not finite JSON-compatible data: {type(value).__name__}"
    )


def _plain_json(value: Any) -> Any:
    if is_dataclass(value):
        return {
            item.name: _plain_json(getattr(value, item.name)) for item in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(key): _plain_json(value[key]) for key in sorted(value, key=str)
        }
    if isinstance(value, (list, tuple)):
        return [_plain_json(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"value is not JSON-compatible: {type(value).__name__}")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _plain_json(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def parse_exploration_config(
    payload: Mapping[str, Any],
    *,
    config_path: Optional[Path] = None,
) -> ExplorationConfig:
    """Validate a JSON-compatible config without creating any live artifacts."""
    if not isinstance(payload, Mapping):
        raise ExplorationConfigurationError("configuration must be a JSON object")

    schema_version = _required_string(payload, "schema_version")
    if schema_version != CONFIG_SCHEMA_VERSION:
        raise ExplorationConfigurationError(
            f"schema_version must be {CONFIG_SCHEMA_VERSION!r}"
        )

    session_id = _required_string(payload, "session_id")
    if not _SESSION_ID_RE.fullmatch(session_id):
        raise ExplorationConfigurationError("session_id contains unsupported characters")

    seed = _bounded_integer(payload.get("seed"), "seed", minimum=0, maximum=2**63 - 1)

    raw_categories = payload.get("enabled_categories")
    if not isinstance(raw_categories, (list, tuple)) or not raw_categories:
        raise ExplorationConfigurationError(
            "enabled_categories must be a non-empty array"
        )
    if any(not isinstance(category, str) or not category for category in raw_categories):
        raise ExplorationConfigurationError(
            "enabled_categories entries must be non-empty strings"
        )
    categories = tuple(raw_categories)
    if len(set(categories)) != len(categories):
        raise ExplorationConfigurationError(
            "enabled_categories cannot contain duplicate entries"
        )
    unsupported = sorted(set(categories) - EXECUTABLE_CATEGORIES)
    if unsupported:
        raise ExplorationConfigurationError(
            "unsupported executable category: " + ", ".join(unsupported)
        )

    raw_rates = payload.get("category_rates_bps")
    if not isinstance(raw_rates, Mapping):
        raise ExplorationConfigurationError("category_rates_bps must be an object")
    rate_keys = {str(key) for key in raw_rates}
    if rate_keys != set(categories):
        raise ExplorationConfigurationError(
            "category_rates_bps keys must exactly match enabled_categories"
        )
    rates = {}
    for category in categories:
        rates[category] = _bounded_integer(
            raw_rates.get(category),
            f"category_rates_bps[{category!r}]",
            minimum=0,
            maximum=MAX_CATEGORY_RATE_BPS,
            maximum_label="1,000",
        )

    budget = _bounded_integer(
        payload.get("per_run_alternative_budget"),
        "per_run_alternative_budget",
        minimum=0,
        maximum=MAX_ALTERNATIVE_ATTEMPTS_PER_RUN,
    )
    trace_path = _required_absolute_path(payload, "trace_path")
    manifest_path = _required_absolute_path(payload, "manifest_path")
    if trace_path == manifest_path:
        raise ExplorationConfigurationError(
            "trace_path and manifest_path must be distinct"
        )

    source_commit = _required_string(payload, "source_commit")
    if not _COMMIT_RE.fullmatch(source_commit):
        raise ExplorationConfigurationError(
            "source_commit must be a full 40-character hexadecimal commit"
        )

    resolved_config_path = None
    if config_path is not None:
        resolved_config_path = Path(config_path).resolve()
        if resolved_config_path in {trace_path, manifest_path}:
            raise ExplorationConfigurationError(
                "configuration path must be distinct from output paths"
            )

    return ExplorationConfig(
        schema_version=schema_version,
        session_id=session_id,
        seed=seed,
        enabled_categories=categories,
        category_rates_bps=rates,
        per_run_alternative_budget=budget,
        trace_path=trace_path,
        manifest_path=manifest_path,
        source_commit=source_commit.lower(),
        source_path=resolved_config_path,
    )


def load_exploration_config(path: Path) -> ExplorationConfig:
    source_path = Path(path).resolve()
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ExplorationConfigurationError(
            f"cannot read exploration configuration {source_path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ExplorationConfigurationError(
            f"invalid exploration configuration JSON at {source_path}: {exc.msg}"
        ) from exc
    return parse_exploration_config(payload, config_path=source_path)


def load_exploration_config_from_env(
    environ: Optional[Mapping[str, str]] = None,
) -> Optional[ExplorationConfig]:
    environment = os.environ if environ is None else environ
    raw_path = environment.get(CONFIG_ENV)
    if raw_path is None or not str(raw_path).strip():
        return None
    return load_exploration_config(Path(str(raw_path).strip()))


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ExplorationConfigurationError(f"{key} must be a non-empty string")
    return value.strip()


def _required_absolute_path(payload: Mapping[str, Any], key: str) -> Path:
    value = _required_string(payload, key)
    path = Path(value)
    if not path.is_absolute():
        raise ExplorationConfigurationError(f"{key} must be an absolute path")
    return path.resolve()


def _bounded_integer(
    value: Any,
    name: str,
    *,
    minimum: int,
    maximum: int,
    maximum_label: Optional[str] = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExplorationConfigurationError(f"{name} must be an integer")
    if value < minimum or value > maximum:
        upper = maximum_label or str(maximum)
        raise ExplorationConfigurationError(
            f"{name} must be between {minimum} and {upper}"
        )
    return value
