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
import tempfile
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Optional

from spirecomm.communication.action import (
    BuyCardAction,
    BuyPotionAction,
    BuyPurgeAction,
    BuyRelicAction,
    CancelAction,
    CardRewardAction,
    ChooseAction,
    ChooseMapNodeAction,
    LeaveAction,
    ProceedAction,
    WaitAction,
)
from spirecomm.spire.screen import ScreenType


CONFIG_ENV = "STS_NONCOMBAT_EXPLORATION_CONFIG"
CONFIG_SCHEMA_VERSION = "noncombat-exploration-config-v1"
EXECUTABLE_CATEGORIES = frozenset({"card_reward", "shop"})
MAX_CATEGORY_RATE_BPS = 1_000
MAX_ALTERNATIVE_ATTEMPTS_PER_RUN = 2
SELECTION_SCHEMA_VERSION = "noncombat-exploration-selection-v1"
RECORD_SCHEMA_VERSION = "noncombat-exploration-record-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-exploration-manifest-v1"
PROPOSAL_ROLLOUT_MODES = frozenset({"executable", "shadow", "ineligible"})
DRAW_BUCKET_COUNT = 10_000
RESOLUTION_STATUSES = frozenset(
    {"confirmed", "rejected", "superseded", "terminal_unresolved"}
)

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class ExplorationConfigurationError(ValueError):
    """Raised when an exploration configuration is incomplete or unsafe."""


class ExplorationProposalError(ValueError):
    """Raised when candidate identities or proposal mappings are ambiguous."""


class ExplorationSamplingError(ValueError):
    """Raised when an action distribution cannot be sampled safely."""


class ExplorationPersistenceError(RuntimeError):
    """Raised when append-only exploration evidence cannot be trusted."""


class ExplorationStateError(RuntimeError):
    """Raised when controller lifecycle calls are inconsistent."""


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

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "seed": self.seed,
            "enabled_categories": list(self.enabled_categories),
            "category_rates_bps": dict(self.category_rates_bps),
            "per_run_alternative_budget": self.per_run_alternative_budget,
            "trace_path": str(self.trace_path),
            "manifest_path": str(self.manifest_path),
            "source_commit": self.source_commit,
            "source_path": str(self.source_path) if self.source_path is not None else None,
        }


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

    def to_record(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "baseline_action_id": self.baseline_action_id,
            "alternative_action_id": self.alternative_action_id,
            "candidates": [candidate.to_record() for candidate in self.candidates],
            "state": _plain_json(self.state),
            "state_hash": self.state_hash,
            "execution_eligible": self.execution_eligible,
            "rollout_mode": self.rollout_mode,
            "ineligibility_reason": self.ineligibility_reason,
        }


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


@dataclass(frozen=True)
class ProposalAdapterResult:
    """Side-effect-free bridge from a Current action to an exploration proposal."""

    category: str
    current_action: Any = field(repr=False, compare=False)
    proposal: Optional[NonCombatProposal] = None
    ineligibility_reason: str = ""
    _alternative_action_factory: Optional[Callable[[], Any]] = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.category, str) or not self.category.strip():
            raise ExplorationProposalError("adapter category must be non-empty")
        object.__setattr__(self, "category", self.category.strip())
        if self.proposal is None:
            if not self.ineligibility_reason:
                raise ExplorationProposalError(
                    "adapter without proposal requires ineligibility_reason"
                )
            if self._alternative_action_factory is not None:
                raise ExplorationProposalError(
                    "ineligible adapter cannot materialize an alternative"
                )
            return
        if self.proposal.category != self.category:
            raise ExplorationProposalError("adapter and proposal categories differ")
        if self.proposal.execution_eligible:
            if self.ineligibility_reason:
                raise ExplorationProposalError(
                    "eligible adapter cannot have ineligibility_reason"
                )
            if self._alternative_action_factory is None:
                raise ExplorationProposalError(
                    "eligible adapter requires an alternative action factory"
                )
        else:
            if self._alternative_action_factory is not None:
                raise ExplorationProposalError(
                    "shadow adapter cannot materialize an alternative"
                )
            if self.ineligibility_reason != self.proposal.ineligibility_reason:
                raise ExplorationProposalError(
                    "shadow adapter reason must match its proposal"
                )

    @property
    def execution_eligible(self) -> bool:
        return bool(self.proposal and self.proposal.execution_eligible)

    def materialize_or_current(self, selected_action_id: str) -> Any:
        """Materialize a supported selection, failing closed to Current."""

        if self.proposal is None:
            return self.current_action
        if selected_action_id == self.proposal.baseline_action_id:
            return self.current_action
        if (
            self.proposal.execution_eligible
            and selected_action_id == self.proposal.alternative_action_id
            and self._alternative_action_factory is not None
        ):
            return self._alternative_action_factory()
        return self.current_action


def build_card_reward_proposal(game: Any, current_action: Any) -> ProposalAdapterResult:
    """Expose only a uniquely mapped Current card and an immediate skip."""

    category = "card_reward"
    if not _screen_is(game, ScreenType.CARD_REWARD):
        return _ineligible_adapter(category, current_action, "not_card_reward_screen")
    if bool(getattr(game, "in_combat", False)):
        return _ineligible_adapter(category, current_action, "in_combat_card_reward")
    if isinstance(current_action, CancelAction) or (
        isinstance(current_action, CardRewardAction)
        and str(getattr(current_action, "name", "")).lower() == "bowl"
    ):
        return _ineligible_adapter(
            category,
            current_action,
            "current_action_already_abstention",
        )
    if not isinstance(current_action, CardRewardAction):
        return _ineligible_adapter(category, current_action, "unsupported_current_action")

    screen = getattr(game, "screen", None)
    cards = list(getattr(screen, "cards", []) or [])
    selected_name = str(getattr(current_action, "name", ""))
    matches = [
        index
        for index, card in enumerate(cards)
        if str(getattr(card, "name", "")) == selected_name
    ]
    if not matches:
        return _ineligible_adapter(category, current_action, "current_card_not_offered")
    if len(matches) != 1:
        return _ineligible_adapter(
            category,
            current_action,
            "current_card_mapping_ambiguous",
        )
    if not bool(getattr(screen, "can_skip", False)):
        return _ineligible_adapter(
            category,
            current_action,
            "card_reward_skip_not_available",
        )

    commands = _available_commands(game)
    if commands is not None and "choose" not in commands:
        return _ineligible_adapter(
            category,
            current_action,
            "current_card_not_immediately_legal",
        )
    if not _card_reward_skip_is_immediate(game, commands):
        return _ineligible_adapter(
            category,
            current_action,
            "card_reward_skip_not_immediately_legal",
        )

    selected_index = matches[0]
    base_ids = [
        f"card_reward:take:{_action_slug(getattr(card, 'name', ''))}"
        for card in cards
    ]
    action_ids = _disambiguate_ids(base_ids)
    candidates = [
        ExplorationCandidate(
            action_id=action_ids[index],
            kind="take",
            label=str(getattr(card, "name", "")),
            executable=index == selected_index,
            raw={"slot": index, **_item_summary(card)},
        )
        for index, card in enumerate(cards)
    ]
    if bool(getattr(screen, "can_bowl", False)):
        candidates.append(
            ExplorationCandidate(
                action_id="card_reward:bowl",
                kind="bowl",
                label="bowl",
                executable=False,
            )
        )
    candidates.append(
        ExplorationCandidate(
            action_id="card_reward:skip",
            kind="skip",
            label="skip",
        )
    )
    proposal = NonCombatProposal(
        category=category,
        baseline_action_id=action_ids[selected_index],
        alternative_action_id="card_reward:skip",
        candidates=tuple(candidates),
        state=_proposal_state(game, current_action),
        execution_eligible=True,
        rollout_mode="executable",
    )
    return ProposalAdapterResult(
        category=category,
        current_action=current_action,
        proposal=proposal,
        _alternative_action_factory=CancelAction,
    )


def build_shop_proposal(
    game: Any,
    current_action: Any,
    *,
    agent: Any = None,
) -> ProposalAdapterResult:
    """Expose a mapped Current shop action and a lazy immediate-exit action."""

    category = "shop"
    if not _screen_is(game, ScreenType.SHOP_SCREEN):
        return _ineligible_adapter(category, current_action, "not_shop_screen")
    if isinstance(current_action, WaitAction):
        return _ineligible_adapter(category, current_action, "shop_transition_in_progress")
    if isinstance(current_action, (LeaveAction, CancelAction, ProceedAction)):
        return _ineligible_adapter(
            category,
            current_action,
            "current_action_already_abstention",
        )
    if bool(getattr(agent, "_leaving_shop_room", False)):
        return _ineligible_adapter(category, current_action, "shop_transition_in_progress")

    exit_factory = _shop_exit_factory(game)
    if exit_factory is None:
        return _ineligible_adapter(
            category,
            current_action,
            "shop_leave_not_immediately_legal",
        )

    screen = getattr(game, "screen", None)
    inventory_kind = ""
    inventory = []
    action_prefix = ""
    if isinstance(current_action, BuyCardAction):
        inventory_kind = "card"
        inventory = list(getattr(screen, "cards", []) or [])
        action_prefix = "shop:buy_card"
    elif isinstance(current_action, BuyRelicAction):
        inventory_kind = "relic"
        inventory = list(getattr(screen, "relics", []) or [])
        action_prefix = "shop:buy_relic"
    elif isinstance(current_action, BuyPotionAction):
        inventory_kind = "potion"
        inventory = list(getattr(screen, "potions", []) or [])
        action_prefix = "shop:buy_potion"
    elif isinstance(current_action, BuyPurgeAction) or (
        isinstance(current_action, ChooseAction)
        and str(getattr(current_action, "name", "")).lower() == "purge"
    ):
        if not bool(getattr(screen, "purge_available", False)):
            return _ineligible_adapter(
                category,
                current_action,
                "shop_purge_not_available",
            )
        baseline_action_id = "shop:purge"
    else:
        return _ineligible_adapter(category, current_action, "unsupported_current_action")

    if inventory_kind:
        selected_name = str(getattr(current_action, "name", ""))
        matches = [
            index
            for index, item in enumerate(inventory)
            if str(getattr(item, "name", "")) == selected_name
        ]
        if not matches:
            return _ineligible_adapter(
                category,
                current_action,
                "current_shop_offer_not_found",
            )
        if len(matches) != 1:
            return _ineligible_adapter(
                category,
                current_action,
                "current_shop_offer_mapping_ambiguous",
            )
        base_ids = [
            f"{action_prefix}:{_action_slug(getattr(item, 'name', ''))}"
            for item in inventory
        ]
        baseline_action_id = _disambiguate_ids(base_ids)[matches[0]]

    commands = _available_commands(game)
    if commands is not None and "choose" not in commands:
        return _ineligible_adapter(category, current_action, "shop_transition_in_progress")

    candidates = _shop_candidates(screen, baseline_action_id)
    proposal = NonCombatProposal(
        category=category,
        baseline_action_id=baseline_action_id,
        alternative_action_id="shop:leave",
        candidates=tuple(candidates),
        state=_proposal_state(
            game,
            current_action,
            adapter_context={"shop_agent_state": _shop_agent_state(agent)},
        ),
        execution_eligible=True,
        rollout_mode="executable",
    )
    return ProposalAdapterResult(
        category=category,
        current_action=current_action,
        proposal=proposal,
        _alternative_action_factory=exit_factory,
    )


def build_event_shadow_proposal(game: Any, current_action: Any) -> ProposalAdapterResult:
    """Build event diagnostics without making any event alternative executable."""

    category = "event"
    if not _screen_is(game, ScreenType.EVENT):
        return _ineligible_adapter(category, current_action, "not_event_screen")
    if not isinstance(current_action, ChooseAction):
        return _ineligible_adapter(category, current_action, "unsupported_current_action")

    options = list(getattr(getattr(game, "screen", None), "options", []) or [])
    option_indices = [
        _coerce_choice_index(getattr(option, "choice_index", None), fallback)
        for fallback, option in enumerate(options)
    ]
    if len(set(option_indices)) != len(option_indices):
        return _ineligible_adapter(category, current_action, "event_choice_ids_ambiguous")
    selected_index = _coerce_choice_index(getattr(current_action, "choice_index", None), -1)
    matches = [index for index, choice in enumerate(option_indices) if choice == selected_index]
    if len(matches) != 1:
        return _ineligible_adapter(category, current_action, "current_event_choice_not_mapped")

    candidates = tuple(
        ExplorationCandidate(
            action_id=f"event:choice:{option_indices[index]}",
            kind="choose",
            label=str(getattr(option, "label", getattr(option, "text", ""))),
            available=not bool(getattr(option, "disabled", False)),
            executable=False,
            raw={
                "choice_index": option_indices[index],
                "text": str(getattr(option, "text", "")),
                "label": str(getattr(option, "label", "")),
                "disabled": bool(getattr(option, "disabled", False)),
            },
        )
        for index, option in enumerate(options)
    )
    baseline_id = f"event:choice:{selected_index}"
    alternative_id = _first_available_other(candidates, baseline_id)
    if alternative_id is None:
        return _ineligible_adapter(category, current_action, "event_has_no_shadow_alternative")
    proposal = NonCombatProposal(
        category=category,
        baseline_action_id=baseline_id,
        alternative_action_id=alternative_id,
        candidates=candidates,
        state=_proposal_state(game, current_action),
        execution_eligible=False,
        rollout_mode="shadow",
        ineligibility_reason="category_shadow_only",
    )
    return ProposalAdapterResult(
        category=category,
        current_action=current_action,
        proposal=proposal,
        ineligibility_reason="category_shadow_only",
    )


def build_route_shadow_proposal(game: Any, current_action: Any) -> ProposalAdapterResult:
    """Build route diagnostics without making any route alternative executable."""

    category = "route"
    if not _screen_is(game, ScreenType.MAP):
        return _ineligible_adapter(category, current_action, "not_map_screen")
    if not isinstance(current_action, ChooseMapNodeAction):
        return _ineligible_adapter(category, current_action, "unsupported_current_action")

    nodes = list(getattr(getattr(game, "screen", None), "next_nodes", []) or [])
    selected_node = getattr(current_action, "node", None)
    matches = [
        index for index, node in enumerate(nodes) if _same_map_node(node, selected_node)
    ]
    if len(matches) != 1:
        return _ineligible_adapter(category, current_action, "current_route_choice_not_mapped")
    baseline_index = matches[0]
    candidates = tuple(
        ExplorationCandidate(
            action_id=f"route:choice:{index}",
            kind="map_node",
            label=_map_node_label(node),
            executable=False,
            raw={
                "choice": index,
                "x": getattr(node, "x", None),
                "y": getattr(node, "y", None),
                "symbol": str(getattr(node, "symbol", "")),
            },
        )
        for index, node in enumerate(nodes)
    )
    baseline_id = f"route:choice:{baseline_index}"
    alternative_id = _first_available_other(candidates, baseline_id)
    if alternative_id is None:
        return _ineligible_adapter(category, current_action, "route_has_no_shadow_alternative")
    proposal = NonCombatProposal(
        category=category,
        baseline_action_id=baseline_id,
        alternative_action_id=alternative_id,
        candidates=candidates,
        state=_proposal_state(game, current_action),
        execution_eligible=False,
        rollout_mode="shadow",
        ineligibility_reason="category_shadow_only",
    )
    return ProposalAdapterResult(
        category=category,
        current_action=current_action,
        proposal=proposal,
        ineligibility_reason="category_shadow_only",
    )


def _ineligible_adapter(
    category: str,
    current_action: Any,
    reason: str,
) -> ProposalAdapterResult:
    return ProposalAdapterResult(
        category=category,
        current_action=current_action,
        ineligibility_reason=reason,
    )


def _screen_is(game: Any, expected: ScreenType) -> bool:
    actual = getattr(game, "screen_type", None)
    if actual == expected:
        return True
    actual_name = str(getattr(actual, "name", actual)).upper()
    return actual_name in {expected.name, f"SCREENTYPE.{expected.name}"}


def _available_commands(game: Any) -> Optional[frozenset[str]]:
    raw = getattr(game, "available_commands", None)
    if raw is None:
        return None
    return frozenset(str(command).strip().lower() for command in raw)


def _card_reward_skip_is_immediate(
    game: Any,
    commands: Optional[frozenset[str]],
) -> bool:
    if commands is not None:
        return bool(commands & {"cancel", "skip"})
    return bool(getattr(game, "cancel_available", False))


def _shop_exit_factory(game: Any) -> Optional[Callable[[], Any]]:
    commands = _available_commands(game)
    if commands is not None:
        if "leave" in commands:
            return LeaveAction
        if commands & {"proceed", "confirm"}:
            return ProceedAction
        if commands & {"cancel", "return"}:
            return CancelAction
        return None
    if bool(getattr(game, "proceed_available", False)):
        return ProceedAction
    if bool(getattr(game, "cancel_available", False)):
        return CancelAction
    return None


def _shop_candidates(screen: Any, baseline_action_id: str) -> list[ExplorationCandidate]:
    candidates: list[ExplorationCandidate] = []
    for inventory_name, kind, prefix in (
        ("cards", "buy_card", "shop:buy_card"),
        ("relics", "buy_relic", "shop:buy_relic"),
        ("potions", "buy_potion", "shop:buy_potion"),
    ):
        items = list(getattr(screen, inventory_name, []) or [])
        base_ids = [
            f"{prefix}:{_action_slug(getattr(item, 'name', ''))}" for item in items
        ]
        action_ids = _disambiguate_ids(base_ids)
        for slot, (item, action_id) in enumerate(zip(items, action_ids)):
            candidates.append(
                ExplorationCandidate(
                    action_id=action_id,
                    kind=kind,
                    label=str(getattr(item, "name", "")),
                    executable=action_id == baseline_action_id,
                    raw={
                        "shop_inventory": inventory_name[:-1],
                        "shop_slot": slot,
                        **_item_summary(item),
                    },
                )
            )
    if bool(getattr(screen, "purge_available", False)):
        candidates.append(
            ExplorationCandidate(
                action_id="shop:purge",
                kind="purge",
                label="purge",
                executable=baseline_action_id == "shop:purge",
                raw={"cost": getattr(screen, "purge_cost", None)},
            )
        )
    candidates.append(
        ExplorationCandidate(
            action_id="shop:leave",
            kind="leave",
            label="leave",
        )
    )
    return candidates


def _proposal_state(
    game: Any,
    current_action: Any,
    *,
    adapter_context: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    from spirecomm.ai.decision_trace import build_decision_trace_event

    event = build_decision_trace_event(
        current_action,
        game,
        source="noncombat_exploration",
    )
    for volatile_key in ("timestamp", "unix_time", "source", "decision_path"):
        event.pop(volatile_key, None)
    screen = getattr(game, "screen", None)
    event["transition_fields"] = {
        "for_purge": bool(getattr(screen, "for_purge", False)),
        "purge_available": bool(getattr(screen, "purge_available", False)),
    }
    if adapter_context:
        event["adapter_context"] = dict(adapter_context)
    return event


def _shop_agent_state(agent: Any) -> dict[str, Any]:
    if agent is None:
        return {}
    return {
        "visited_shop": bool(getattr(agent, "visited_shop", False)),
        "shop_purchase_made": bool(getattr(agent, "shop_purchase_made", False)),
        "shop_purchase_signature": _plain_json(
            getattr(agent, "_shop_purchase_signature", None)
        ),
        "shop_bought_card_this_shop": bool(
            getattr(agent, "_shop_bought_card_this_shop", False)
        ),
        "shop_purged_this_shop": bool(
            getattr(agent, "_shop_purged_this_shop", False)
        ),
        "leaving_shop_room": bool(getattr(agent, "_leaving_shop_room", False)),
        "shop_exit_waits": getattr(agent, "_shop_exit_waits", 0),
    }


def _item_summary(item: Any) -> dict[str, Any]:
    return {
        "name": str(getattr(item, "name", "")),
        "id": str(
            getattr(
                item,
                "card_id",
                getattr(item, "relic_id", getattr(item, "potion_id", "")),
            )
        ),
        "price": getattr(item, "price", None),
        "upgrades": getattr(item, "upgrades", 0),
    }


def _action_slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\+\d*$", "", text)
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def _disambiguate_ids(base_ids: list[str]) -> list[str]:
    counts = {action_id: base_ids.count(action_id) for action_id in set(base_ids)}
    return [
        f"{action_id}:slot:{slot}" if counts[action_id] > 1 else action_id
        for slot, action_id in enumerate(base_ids)
    ]


def _coerce_choice_index(value: Any, fallback: int) -> int:
    try:
        return int(value) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _first_available_other(
    candidates: tuple[ExplorationCandidate, ...],
    baseline_action_id: str,
) -> Optional[str]:
    for candidate in candidates:
        if candidate.action_id != baseline_action_id and candidate.available:
            return candidate.action_id
    return None


def _same_map_node(first: Any, second: Any) -> bool:
    if first is second:
        return True
    if first is None or second is None:
        return False
    return (
        getattr(first, "x", None),
        getattr(first, "y", None),
    ) == (
        getattr(second, "x", None),
        getattr(second, "y", None),
    )


def _map_node_label(node: Any) -> str:
    return "{}@{},{}".format(
        getattr(node, "symbol", ""),
        getattr(node, "x", "?"),
        getattr(node, "y", "?"),
    )


class ExplorationRecordStore:
    """Strict append-only JSONL storage with duplicate and partial-line guards."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._records: list[dict[str, Any]] = []
        self._proposed_ids: set[str] = set()
        self._resolved_ids: set[str] = set()
        self._load_existing()

    def _load_existing(self) -> None:
        if not self.path.exists():
            return
        if not self.path.is_file():
            raise ExplorationPersistenceError(
                f"exploration trace is not a file: {self.path}"
            )
        try:
            payload = self.path.read_bytes()
        except OSError as exc:
            raise ExplorationPersistenceError(
                f"unable to read exploration trace: {exc}"
            ) from exc
        if payload and not payload.endswith(b"\n"):
            raise ExplorationPersistenceError(
                f"partial JSONL record at end of exploration trace: {self.path}"
            )
        for line_number, raw_line in enumerate(payload.splitlines(), start=1):
            if not raw_line.strip():
                raise ExplorationPersistenceError(
                    f"blank JSONL record at line {line_number}"
                )
            try:
                record = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ExplorationPersistenceError(
                    f"invalid JSONL record at line {line_number}: {exc}"
                ) from exc
            self._validate_record(record)
            self._index_record(record)

    def append_proposed(self, record: Mapping[str, Any]) -> None:
        self._append(record, expected_type="proposed")

    def append_resolution(self, record: Mapping[str, Any]) -> None:
        self._append(record, expected_type="resolution")

    def _append(self, record: Mapping[str, Any], *, expected_type: str) -> None:
        try:
            plain_record = _plain_json(_freeze_json(record))
        except (ExplorationProposalError, TypeError) as exc:
            raise ExplorationPersistenceError(
                f"record is not canonical JSON data: {exc}"
            ) from exc
        if plain_record.get("record_type") != expected_type:
            raise ExplorationPersistenceError(
                f"expected {expected_type} record, got {plain_record.get('record_type')}"
            )
        self._validate_record(plain_record)
        encoded = (_canonical_json(plain_record) + "\n").encode("utf-8")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_BINARY", 0)
            descriptor = os.open(str(self.path), flags, 0o600)
            try:
                written = os.write(descriptor, encoded)
                if written != len(encoded):
                    raise ExplorationPersistenceError(
                        f"partial exploration record write: {written}/{len(encoded)} bytes"
                    )
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except ExplorationPersistenceError:
            raise
        except OSError as exc:
            raise ExplorationPersistenceError(
                f"unable to append exploration record: {exc}"
            ) from exc
        self._index_record(plain_record)

    def _validate_record(self, record: Any) -> None:
        if not isinstance(record, Mapping):
            raise ExplorationPersistenceError("exploration record must be an object")
        if record.get("schema_version") != RECORD_SCHEMA_VERSION:
            raise ExplorationPersistenceError("unsupported exploration record schema")
        record_type = record.get("record_type")
        if record_type not in {"proposed", "resolution"}:
            raise ExplorationPersistenceError("unsupported exploration record type")
        decision_id = record.get("decision_id")
        if not isinstance(decision_id, str) or not decision_id:
            raise ExplorationPersistenceError("record decision_id must be non-empty")
        if record_type == "proposed":
            if decision_id in self._proposed_ids:
                raise ExplorationPersistenceError(
                    f"duplicate decision_id: {decision_id}"
                )
            required = (
                "session_id",
                "trajectory_session_id",
                "decision_index",
                "category",
                "proposal",
                "selection",
            )
            missing = [key for key in required if key not in record]
            if missing:
                raise ExplorationPersistenceError(
                    f"proposed record missing fields: {', '.join(missing)}"
                )
            return
        if decision_id not in self._proposed_ids:
            raise ExplorationPersistenceError(
                f"resolution references unknown decision_id: {decision_id}"
            )
        if decision_id in self._resolved_ids:
            raise ExplorationPersistenceError(
                f"duplicate resolution for decision_id: {decision_id}"
            )
        if record.get("status") not in RESOLUTION_STATUSES:
            raise ExplorationPersistenceError("unsupported resolution status")

    def _index_record(self, record: Mapping[str, Any]) -> None:
        plain_record = _plain_json(record)
        self._records.append(plain_record)
        decision_id = str(record["decision_id"])
        if record["record_type"] == "proposed":
            self._proposed_ids.add(decision_id)
        else:
            self._resolved_ids.add(decision_id)

    def read_records(self) -> tuple[dict[str, Any], ...]:
        return tuple(_plain_json(record) for record in self._records)


@dataclass(frozen=True)
class ExplorationDecisionResult:
    action: Any = field(repr=False, compare=False)
    known_propensity: bool
    decision_id: str = ""
    selected_action_id: str = ""
    selection: Optional[ExplorationSelection] = None
    fallback_reason: str = ""


@dataclass(frozen=True)
class _PendingExplorationDecision:
    decision_id: str
    proposal: NonCombatProposal
    selection: ExplorationSelection
    selected_candidate: ExplorationCandidate


@dataclass(frozen=True)
class _TransitionAssessment:
    status: str
    reason: str
    evidence: Mapping[str, Any] = field(default_factory=dict)


class NonCombatExplorationController:
    """Persist, return, and later confirm one bounded exploration decision."""

    def __init__(
        self,
        config: ExplorationConfig,
        *,
        record_store: Optional[ExplorationRecordStore] = None,
    ):
        self.config = config
        self.record_store = record_store or ExplorationRecordStore(config.trace_path)
        self._trajectory_session_id: Optional[str] = None
        self._decision_index = 0
        self._alternative_attempts = 0
        self._pending: Optional[_PendingExplorationDecision] = None

    @property
    def trajectory_session_id(self) -> Optional[str]:
        return self._trajectory_session_id

    @property
    def pending_decision_id(self) -> Optional[str]:
        return self._pending.decision_id if self._pending is not None else None

    @property
    def alternative_attempts(self) -> int:
        return self._alternative_attempts

    def begin_trajectory(self, run_token: str) -> str:
        if self._pending is not None:
            raise ExplorationStateError(
                "cannot begin a trajectory while a decision is unresolved"
            )
        self._trajectory_session_id = make_trajectory_session_id(
            self.config.session_id,
            run_token,
        )
        self._decision_index = 0
        self._alternative_attempts = 0
        return self._trajectory_session_id

    def consider(
        self,
        adapter: ProposalAdapterResult,
        game: Any,
    ) -> ExplorationDecisionResult:
        if self._trajectory_session_id is None:
            raise ExplorationStateError("begin_trajectory must be called before consider")
        if self._pending is not None:
            try:
                self.resolve_pending(game, superseded=True)
            except ExplorationPersistenceError as exc:
                return self._fallback(
                    adapter,
                    f"superseded_resolution_persistence_failed:{exc}",
                )
        proposal = adapter.proposal
        if proposal is None or not proposal.execution_eligible:
            return self._fallback(
                adapter,
                adapter.ineligibility_reason or "proposal_not_execution_eligible",
            )
        if proposal.category not in self.config.enabled_categories:
            return self._fallback(adapter, "category_not_enabled")
        if self.config.rate_bps(proposal.category) == 0:
            return self._fallback(adapter, "category_rate_zero")
        if self._alternative_attempts >= self.config.per_run_alternative_budget:
            return self._fallback(adapter, "alternative_attempt_budget_exhausted")

        decision_index = self._decision_index
        self._decision_index += 1
        try:
            selection = sample_exploration(
                self.config,
                proposal,
                trajectory_session_id=self._trajectory_session_id,
                decision_index=decision_index,
            )
        except ExplorationSamplingError as exc:
            return self._fallback(adapter, f"sampling_failed:{exc}")
        replay = verify_exploration_selection(
            self.config,
            proposal,
            selection,
            trajectory_session_id=self._trajectory_session_id,
            decision_index=decision_index,
        )
        if not replay.valid:
            return self._fallback(
                adapter,
                f"selection_replay_failed:{','.join(replay.errors)}",
            )

        selected_candidate = _candidate_for_id(
            proposal,
            selection.selected_action_id,
        )
        if selected_candidate is None or not selected_candidate.available:
            return self._fallback(adapter, "selected_candidate_not_available")
        decision_id = make_decision_id(
            self.config.session_id,
            self._trajectory_session_id,
            decision_index,
            proposal.state_hash,
        )
        selected_alternative = (
            selection.selected_action_id == proposal.alternative_action_id
        )
        record = {
            "schema_version": RECORD_SCHEMA_VERSION,
            "record_type": "proposed",
            "session_id": self.config.session_id,
            "trajectory_session_id": self._trajectory_session_id,
            "decision_index": decision_index,
            "decision_id": decision_id,
            "category": proposal.category,
            "behavior_policy_id": (
                f"known-propensity-epsilon-v1:{self.config.session_id}"
            ),
            "proposal": proposal.to_record(),
            "selection": selection.to_record(),
            "selected_candidate": selected_candidate.to_record(),
            "alternative_attempt_budget": {
                "limit": self.config.per_run_alternative_budget,
                "used_before": self._alternative_attempts,
                "selected_alternative": selected_alternative,
            },
        }
        try:
            self.record_store.append_proposed(record)
        except ExplorationPersistenceError as exc:
            return self._fallback(
                adapter,
                f"proposal_persistence_failed:{exc}",
            )

        self._pending = _PendingExplorationDecision(
            decision_id=decision_id,
            proposal=proposal,
            selection=selection,
            selected_candidate=selected_candidate,
        )
        if selected_alternative:
            self._alternative_attempts += 1
        try:
            action = adapter.materialize_or_current(selection.selected_action_id)
            if selected_alternative and action is adapter.current_action:
                raise ExplorationStateError("alternative action did not materialize")
        except Exception as exc:
            try:
                self._resolve_with_status(
                    status="rejected",
                    reason=f"action_materialization_failed:{exc}",
                    after_state={},
                    evidence={},
                )
            except ExplorationPersistenceError:
                pass
            return ExplorationDecisionResult(
                action=adapter.current_action,
                known_propensity=False,
                decision_id=decision_id,
                selected_action_id=selection.selected_action_id,
                selection=selection,
                fallback_reason=f"action_materialization_failed:{exc}",
            )
        return ExplorationDecisionResult(
            action=action,
            known_propensity=True,
            decision_id=decision_id,
            selected_action_id=selection.selected_action_id,
            selection=selection,
        )

    def resolve_pending(
        self,
        game: Any = None,
        *,
        terminal: bool = False,
        superseded: bool = False,
    ) -> Optional[dict[str, Any]]:
        if self._pending is None:
            return None
        after_state = _proposal_state(game, None) if game is not None else {}
        if terminal:
            assessment = _TransitionAssessment(
                "terminal_unresolved",
                "trajectory_ended_before_unique_confirmation",
            )
        elif superseded:
            assessment = _TransitionAssessment(
                "superseded",
                "new_decision_before_unique_confirmation",
            )
        elif game is None:
            return None
        else:
            assessment = _assess_transition(self._pending, after_state)
            if assessment.status == "pending":
                return None
        return self._resolve_with_status(
            status=assessment.status,
            reason=assessment.reason,
            after_state=after_state,
            evidence=assessment.evidence,
        )

    def _resolve_with_status(
        self,
        *,
        status: str,
        reason: str,
        after_state: Mapping[str, Any],
        evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        if self._pending is None:
            raise ExplorationStateError("no pending decision to resolve")
        record = {
            "schema_version": RECORD_SCHEMA_VERSION,
            "record_type": "resolution",
            "session_id": self.config.session_id,
            "trajectory_session_id": self._trajectory_session_id,
            "decision_id": self._pending.decision_id,
            "category": self._pending.proposal.category,
            "selected_action_id": self._pending.selection.selected_action_id,
            "status": status,
            "reason": reason,
            "after_state_hash": _sha256_json(after_state),
            "evidence": _plain_json(_freeze_json(evidence)),
            "executed_known_propensity": status == "confirmed",
        }
        self.record_store.append_resolution(record)
        self._pending = None
        return record

    def end_trajectory(self, game: Any = None) -> Optional[dict[str, Any]]:
        resolution = self.resolve_pending(game, terminal=True)
        self._trajectory_session_id = None
        return resolution

    @staticmethod
    def _fallback(
        adapter: ProposalAdapterResult,
        reason: str,
    ) -> ExplorationDecisionResult:
        return ExplorationDecisionResult(
            action=adapter.current_action,
            known_propensity=False,
            fallback_reason=reason,
        )


def make_trajectory_session_id(session_id: str, run_token: str) -> str:
    if not isinstance(session_id, str) or not session_id:
        raise ExplorationStateError("session_id must be non-empty")
    if not isinstance(run_token, str) or not run_token:
        raise ExplorationStateError("run_token must be non-empty")
    digest = _sha256_json(
        {
            "namespace": "noncombat-exploration-trajectory-v1",
            "session_id": session_id,
            "run_token": run_token,
        }
    )
    return f"trajectory-{digest[:32]}"


def make_decision_id(
    session_id: str,
    trajectory_session_id: str,
    decision_index: int,
    state_hash: str,
) -> str:
    if not isinstance(decision_index, int) or isinstance(decision_index, bool):
        raise ExplorationStateError("decision_index must be an integer")
    if decision_index < 0:
        raise ExplorationStateError("decision_index must be non-negative")
    if not all(
        isinstance(value, str) and value
        for value in (session_id, trajectory_session_id, state_hash)
    ):
        raise ExplorationStateError("decision ID inputs must be non-empty strings")
    digest = _sha256_json(
        {
            "namespace": "noncombat-exploration-decision-v1",
            "session_id": session_id,
            "trajectory_session_id": trajectory_session_id,
            "decision_index": decision_index,
            "state_hash": state_hash,
        }
    )
    return f"decision-{digest[:32]}"


def create_exploration_session_manifest(
    config: ExplorationConfig,
    *,
    source_clean: bool,
    python_executable: str,
    command: list[str] | tuple[str, ...],
    isolation_hashes: Mapping[str, Any],
) -> dict[str, Any]:
    """Atomically publish one immutable session manifest without overwriting."""

    if not source_clean:
        raise ExplorationPersistenceError(
            "tracked source must be clean before creating an exploration manifest"
        )
    target = Path(config.manifest_path)
    if target.exists():
        raise ExplorationPersistenceError(f"manifest already exists: {target}")
    effective_config = config.to_record()
    config_file_sha256 = None
    if config.source_path is not None:
        try:
            config_file_sha256 = hashlib.sha256(
                Path(config.source_path).read_bytes()
            ).hexdigest()
        except OSError as exc:
            raise ExplorationPersistenceError(
                f"unable to hash exploration config: {exc}"
            ) from exc
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "session_id": config.session_id,
        "effective_config": effective_config,
        "effective_config_hash": _sha256_json(effective_config),
        "config_file_sha256": config_file_sha256,
        "source": {
            "commit": config.source_commit,
            "tracked_clean": True,
        },
        "python_executable": str(python_executable),
        "command": [str(part) for part in command],
        "trace_path": str(config.trace_path),
        "manifest_path": str(config.manifest_path),
        "pre_session_isolation_hashes": _plain_json(
            _freeze_json(isolation_hashes)
        ),
    }
    manifest["manifest_hash"] = _sha256_json(manifest)
    _atomic_publish_json(target, manifest)
    return manifest


def _atomic_publish_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (_canonical_json(payload) + "\n").encode("utf-8")
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_name, path)
        except FileExistsError as exc:
            raise ExplorationPersistenceError(
                f"manifest already exists: {path}"
            ) from exc
        except OSError as exc:
            raise ExplorationPersistenceError(
                f"unable to atomically publish manifest: {exc}"
            ) from exc
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def confirmed_exploration_decisions(path: Path) -> tuple[dict[str, Any], ...]:
    store = ExplorationRecordStore(path)
    proposals: dict[str, dict[str, Any]] = {}
    confirmed: dict[str, dict[str, Any]] = {}
    for record in store.read_records():
        decision_id = record["decision_id"]
        if record["record_type"] == "proposed":
            proposals[decision_id] = record
        elif record.get("status") == "confirmed":
            confirmed[decision_id] = record
    rows = []
    for decision_id, proposal in proposals.items():
        resolution = confirmed.get(decision_id)
        if resolution is None:
            continue
        rows.append(
            {
                "decision_id": decision_id,
                "executed_known_propensity": True,
                "proposal": proposal,
                "resolution": resolution,
            }
        )
    return tuple(rows)


def _candidate_for_id(
    proposal: NonCombatProposal,
    action_id: str,
) -> Optional[ExplorationCandidate]:
    return next(
        (candidate for candidate in proposal.candidates if candidate.action_id == action_id),
        None,
    )


def _assess_transition(
    pending: _PendingExplorationDecision,
    after_state: Mapping[str, Any],
) -> _TransitionAssessment:
    if pending.proposal.category == "card_reward":
        return _assess_card_reward_transition(pending, after_state)
    if pending.proposal.category == "shop":
        return _assess_shop_transition(pending, after_state)
    return _TransitionAssessment(
        "rejected",
        "unsupported_confirmation_category",
    )


def _assess_card_reward_transition(
    pending: _PendingExplorationDecision,
    after_state: Mapping[str, Any],
) -> _TransitionAssessment:
    before_state = pending.proposal.state
    candidate = pending.selected_candidate
    reward_still_open = _state_screen_is(after_state, ScreenType.CARD_REWARD)
    before_signature = _deck_signature(before_state)
    after_signature = _deck_signature(after_state)
    evidence = {
        "reward_still_open": reward_still_open,
        "before_deck_size": sum(before_signature.values()),
        "after_deck_size": sum(after_signature.values()),
    }
    if candidate.kind == "take":
        before_count = _matching_item_count(
            before_state.get("deck", ()),
            candidate.raw,
        )
        after_count = _matching_item_count(
            after_state.get("deck", ()),
            candidate.raw,
        )
        evidence.update(
            {
                "selected_card_before_count": before_count,
                "selected_card_after_count": after_count,
            }
        )
        delta = after_count - before_count
        if delta == 1:
            return _TransitionAssessment(
                "confirmed",
                "selected_card_added_once",
                evidence,
            )
        if delta not in {0, 1}:
            return _TransitionAssessment(
                "rejected",
                "selected_card_count_transition_ambiguous",
                evidence,
            )
        if reward_still_open:
            return _TransitionAssessment("pending", "reward_transition_pending", evidence)
        return _TransitionAssessment(
            "rejected",
            "reward_exited_without_selected_card",
            evidence,
        )
    if candidate.kind == "skip":
        if reward_still_open and before_signature == after_signature:
            return _TransitionAssessment("pending", "reward_transition_pending", evidence)
        if before_signature == after_signature and not reward_still_open:
            return _TransitionAssessment(
                "confirmed",
                "reward_exited_without_deck_change",
                evidence,
            )
        return _TransitionAssessment(
            "rejected",
            "skip_transition_changed_deck",
            evidence,
        )
    return _TransitionAssessment(
        "rejected",
        "unsupported_card_reward_selection",
        evidence,
    )


def _assess_shop_transition(
    pending: _PendingExplorationDecision,
    after_state: Mapping[str, Any],
) -> _TransitionAssessment:
    before_state = pending.proposal.state
    candidate = pending.selected_candidate
    shop_still_open = _state_screen_is(after_state, ScreenType.SHOP_SCREEN)
    evidence: dict[str, Any] = {"shop_screen_still_open": shop_still_open}
    if candidate.kind == "leave":
        if shop_still_open:
            return _TransitionAssessment("pending", "shop_exit_pending", evidence)
        return _TransitionAssessment(
            "confirmed",
            "shop_screen_exited",
            evidence,
        )
    if candidate.kind == "purge":
        transition = after_state.get("transition_fields", {})
        purge_grid_opened = (
            _state_screen_is(after_state, ScreenType.GRID)
            and bool(transition.get("for_purge", False))
        )
        before_gold = _optional_int(before_state.get("gold"))
        after_gold = _optional_int(after_state.get("gold"))
        purge_cost = _optional_int(candidate.raw.get("cost"))
        gold_delta = _gold_delta(before_gold, after_gold)
        deck_delta = sum(_deck_signature(after_state).values()) - sum(
            _deck_signature(before_state).values()
        )
        evidence.update(
            {
                "purge_grid_opened": purge_grid_opened,
                "gold_delta": gold_delta,
                "purge_cost": purge_cost,
                "deck_delta": deck_delta,
            }
        )
        if purge_grid_opened:
            return _TransitionAssessment("confirmed", "purge_grid_opened", evidence)
        if purge_cost is not None and purge_cost > 0 and gold_delta == purge_cost:
            return _TransitionAssessment(
                "confirmed",
                "purge_cost_uniquely_observed",
                evidence,
            )
        if deck_delta == -1:
            return _TransitionAssessment(
                "confirmed",
                "purged_card_uniquely_removed",
                evidence,
            )
        if shop_still_open or _state_screen_is(after_state, ScreenType.GRID):
            return _TransitionAssessment("pending", "purge_transition_pending", evidence)
        return _TransitionAssessment(
            "rejected",
            "purge_transition_not_observed",
            evidence,
        )
    if candidate.kind in {"buy_card", "buy_relic", "buy_potion"}:
        inventory_key = {
            "buy_card": "cards",
            "buy_relic": "relics",
            "buy_potion": "potions",
        }[candidate.kind]
        before_items = before_state.get("screen", {}).get(inventory_key, ())
        after_items = after_state.get("screen", {}).get(inventory_key, ())
        before_count = _matching_item_count(before_items, candidate.raw)
        after_count = _matching_item_count(after_items, candidate.raw)
        inventory_delta = before_count - after_count
        before_gold = _optional_int(before_state.get("gold"))
        after_gold = _optional_int(after_state.get("gold"))
        expected_price = _optional_int(candidate.raw.get("price"))
        gold_delta = _gold_delta(before_gold, after_gold)
        inventory_matches = inventory_delta == 1
        gold_matches = (
            expected_price is not None
            and expected_price > 0
            and gold_delta == expected_price
        )
        evidence.update(
            {
                "before_offer_count": before_count,
                "after_offer_count": after_count,
                "inventory_delta": inventory_delta,
                "gold_delta": gold_delta,
                "expected_price": expected_price,
                "inventory_matches": inventory_matches,
                "gold_matches": gold_matches,
            }
        )
        unexpected_gold = (
            gold_delta is not None
            and gold_delta != 0
            and not gold_matches
        )
        if inventory_delta not in {0, 1} or unexpected_gold:
            return _TransitionAssessment(
                "rejected",
                "shop_purchase_transition_ambiguous",
                evidence,
            )
        if inventory_matches or gold_matches:
            return _TransitionAssessment(
                "confirmed",
                "shop_purchase_uniquely_observed",
                evidence,
            )
        if shop_still_open:
            return _TransitionAssessment("pending", "shop_purchase_pending", evidence)
        return _TransitionAssessment(
            "rejected",
            "shop_exited_without_purchase_evidence",
            evidence,
        )
    return _TransitionAssessment(
        "rejected",
        "unsupported_shop_selection",
        evidence,
    )


def _state_screen_is(state: Mapping[str, Any], expected: ScreenType) -> bool:
    actual = str(state.get("screen_type", "")).upper()
    return actual in {expected.name, f"SCREENTYPE.{expected.name}"}


def _deck_signature(state: Mapping[str, Any]) -> Counter[tuple[str, str]]:
    return Counter(
        (
            str(card.get("id", "")),
            str(card.get("name", "")),
        )
        for card in state.get("deck", ())
        if isinstance(card, Mapping)
    )


def _matching_item_count(items: Any, expected: Mapping[str, Any]) -> int:
    expected_id = str(expected.get("id", ""))
    expected_name = str(expected.get("name", ""))
    count = 0
    for item in items or ():
        if not isinstance(item, Mapping):
            continue
        item_id = str(item.get("id", ""))
        item_name = str(item.get("name", ""))
        if expected_id and item_id:
            matches = item_id == expected_id
        else:
            matches = item_name == expected_name
        if matches:
            count += 1
    return count


def _optional_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _gold_delta(before_gold: Optional[int], after_gold: Optional[int]) -> Optional[int]:
    if before_gold is None or after_gold is None:
        return None
    return before_gold - after_gold


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
