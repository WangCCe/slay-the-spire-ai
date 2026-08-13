"""Deterministic bounded replay artifacts for card optimizer ablations."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import gzip
import hashlib
import io
import json
import math
from numbers import Integral, Real
from typing import Any, Mapping, Sequence

import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts.noncombat_card_acceptance_objective import (
    build_card_acceptance_policy_terms,
)
from analysis_scripts.noncombat_state_conditioned_policy_input import HASH_DIM


SCHEMA_VERSION = "noncombat-card-optimizer-replay-v1"
ENCODING = "deterministic-gzip-canonical-json-v1"
MAX_STORED_BYTES = 64 * 1024 * 1024
MAX_CANONICAL_BYTES = 512 * 1024 * 1024
GENERATOR_NAMES = (
    "candidate_card",
    "candidate_noncard",
    "control_card",
    "control_noncard",
)


class CardOptimizerReplayBlocked(RuntimeError):
    """Raised when replay data cannot satisfy the exact offline contract."""


@dataclass(frozen=True)
class EncodedReplay:
    stored: bytes
    binding: dict[str, Any]


@dataclass(frozen=True)
class DecodedReplay:
    episodes: tuple[runtime.ArmEpisodeRollout, ...]
    generator_states: dict[str, torch.Tensor]


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise CardOptimizerReplayBlocked("replay JSON is not canonical") from exc


def _gzip_bytes(value: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        fileobj=buffer, mode="wb", filename="", mtime=0
    ) as stream:
        stream.write(value)
    return buffer.getvalue()


def _binding(stored: bytes, canonical: bytes) -> dict[str, Any]:
    return {
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_size_bytes": len(canonical),
        "encoding": ENCODING,
        "schema_version": SCHEMA_VERSION,
        "stored_sha256": hashlib.sha256(stored).hexdigest(),
        "stored_size_bytes": len(stored),
    }


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise CardOptimizerReplayBlocked(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CardOptimizerReplayBlocked(f"{label} must be finite")
    return result


def _episode_object(value: runtime.ArmEpisodeRollout) -> dict[str, Any]:
    if (
        not isinstance(value, runtime.ArmEpisodeRollout)
        or value.arm != "candidate"
        or value.unsupported_reason is not None
        or value.final_snapshot.get("terminal") is not True
        or len(value.decisions) != len(value.rewards)
    ):
        raise CardOptimizerReplayBlocked("replay episode is not supported candidate data")
    decisions = []
    for index, decision in enumerate(value.decisions):
        expected_id = f"candidate:seed-{value.seed}:decision-{index}"
        if (
            not isinstance(decision, runtime.ArmRolloutDecision)
            or decision.arm != "candidate"
            or decision.decision_index != index
            or decision.decision_id != expected_id
        ):
            raise CardOptimizerReplayBlocked("replay decision order differs")
        if (
            not isinstance(decision.candidate_features, torch.Tensor)
            or not decision.candidates
            or decision.selected_action_id
            not in tuple(row.get("action_id") for row in decision.candidates)
        ):
            raise CardOptimizerReplayBlocked("replay candidate context differs")
        candidate_features = runtime._encode_tensor(decision.candidate_features)
        candidates = copy.deepcopy(list(decision.candidates))
        decisions.append(
            {
                "candidate_features": candidate_features,
                "candidates": candidates,
                "category": decision.category,
                "decision_id": decision.decision_id,
                "decision_index": decision.decision_index,
                "selected_action_id": decision.selected_action_id,
                "state_features": runtime._encode_tensor(decision.state_features),
            }
        )
    rewards = [_finite(item, "replay reward") for item in value.rewards]
    return {
        "decisions": decisions,
        "floor_progress": _finite(value.floor_progress, "replay floor progress"),
        "rewards": rewards,
        "seed": value.seed,
        "terminal_victory": value.terminal_victory,
        "trajectory_id": value.trajectory_id,
    }


def encode_replay(
    episodes: Sequence[runtime.ArmEpisodeRollout],
    *,
    generator_states: Mapping[str, torch.Tensor],
) -> EncodedReplay:
    source = tuple(episodes)
    seeds = tuple(episode.seed for episode in source)
    if (
        not source
        or seeds != tuple(sorted(set(seeds)))
        or set(generator_states) != set(GENERATOR_NAMES)
    ):
        raise CardOptimizerReplayBlocked("replay episode or generator identity differs")
    value = {
        "episodes": [_episode_object(episode) for episode in source],
        "generator_states": {
            name: runtime._encode_tensor(generator_states[name])
            for name in GENERATOR_NAMES
        },
        "schema_version": SCHEMA_VERSION,
    }
    canonical = _canonical_bytes(value)
    if len(canonical) > MAX_CANONICAL_BYTES:
        raise CardOptimizerReplayBlocked("replay canonical byte ceiling exceeded")
    stored = _gzip_bytes(canonical)
    if len(stored) > MAX_STORED_BYTES:
        raise CardOptimizerReplayBlocked("replay stored byte ceiling exceeded")
    return EncodedReplay(stored=stored, binding=_binding(stored, canonical))


def _validate_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "canonical_sha256",
        "canonical_size_bytes",
        "encoding",
        "schema_version",
        "stored_sha256",
        "stored_size_bytes",
    }
    binding = dict(value)
    if (
        set(binding) != expected
        or binding["encoding"] != ENCODING
        or binding["schema_version"] != SCHEMA_VERSION
    ):
        raise CardOptimizerReplayBlocked("replay binding fields differ")
    for name, ceiling in (
        ("stored_size_bytes", MAX_STORED_BYTES),
        ("canonical_size_bytes", MAX_CANONICAL_BYTES),
    ):
        item = binding[name]
        if isinstance(item, bool) or not isinstance(item, Integral) or not 0 < int(item) <= ceiling:
            raise CardOptimizerReplayBlocked(f"replay {name} is invalid")
    for name in ("stored_sha256", "canonical_sha256"):
        digest = binding[name]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise CardOptimizerReplayBlocked(f"replay {name} is invalid")
    return binding


def _bounded_gzip(stored: bytes, *, expected_size: int) -> bytes:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as stream:
            canonical = stream.read(MAX_CANONICAL_BYTES + 1)
    except (EOFError, OSError, gzip.BadGzipFile) as exc:
        raise CardOptimizerReplayBlocked("replay gzip is invalid") from exc
    if len(canonical) > MAX_CANONICAL_BYTES or len(canonical) != expected_size:
        raise CardOptimizerReplayBlocked("replay canonical size differs")
    return canonical


def _decode_episode(value: Any, position: int) -> runtime.ArmEpisodeRollout:
    if not isinstance(value, Mapping) or set(value) != {
        "decisions",
        "floor_progress",
        "rewards",
        "seed",
        "terminal_victory",
        "trajectory_id",
    }:
        raise CardOptimizerReplayBlocked("replay episode fields differ")
    seed = value["seed"]
    if isinstance(seed, bool) or not isinstance(seed, Integral):
        raise CardOptimizerReplayBlocked("replay seed is invalid")
    seed = int(seed)
    if position and seed <= 0:
        raise CardOptimizerReplayBlocked("replay seed is invalid")
    trajectory_id = value["trajectory_id"]
    if trajectory_id != f"candidate:seed-{seed}":
        raise CardOptimizerReplayBlocked("replay trajectory identity differs")
    raw_decisions = value["decisions"]
    raw_rewards = value["rewards"]
    if (
        isinstance(raw_decisions, (str, bytes))
        or not isinstance(raw_decisions, Sequence)
        or isinstance(raw_rewards, (str, bytes))
        or not isinstance(raw_rewards, Sequence)
        or not raw_decisions
        or len(raw_decisions) != len(raw_rewards)
    ):
        raise CardOptimizerReplayBlocked("replay decision/reward counts differ")
    decisions = []
    for index, raw in enumerate(raw_decisions):
        if not isinstance(raw, Mapping) or set(raw) != {
            "candidate_features",
            "candidates",
            "category",
            "decision_id",
            "decision_index",
            "selected_action_id",
            "state_features",
        }:
            raise CardOptimizerReplayBlocked("replay decision fields differ")
        if (
            raw["decision_index"] != index
            or raw["decision_id"] != f"candidate:seed-{seed}:decision-{index}"
        ):
            raise CardOptimizerReplayBlocked("replay decision order differs")
        state = runtime._decode_tensor(
            raw["state_features"], f"episodes[{position}].decisions[{index}].state"
        )
        if state.shape != (HASH_DIM,) or state.dtype != torch.float32:
            raise CardOptimizerReplayBlocked("replay state feature shape differs")
        candidates = raw["candidates"]
        if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
            raise CardOptimizerReplayBlocked("replay candidates differ")
        normalized_candidates = tuple(copy.deepcopy(list(candidates)))
        candidate_features = runtime._decode_tensor(
            raw["candidate_features"],
            f"episodes[{position}].decisions[{index}].candidates",
        )
        if (
            not normalized_candidates
            or candidate_features.dtype != torch.float32
            or candidate_features.shape != (len(normalized_candidates), HASH_DIM)
            or raw["selected_action_id"]
            not in tuple(row.get("action_id") for row in normalized_candidates)
        ):
            raise CardOptimizerReplayBlocked("replay candidate context differs")
        decisions.append(
            runtime.ArmRolloutDecision(
                arm="candidate",
                category=str(raw["category"]),
                decision_id=str(raw["decision_id"]),
                decision_index=index,
                selected_action_id=str(raw["selected_action_id"]),
                state_features=state,
                card_terms=None,
                diagnostic={},
                candidate_features=candidate_features,
                candidates=normalized_candidates,
            )
        )
    rewards = tuple(_finite(item, "replay reward") for item in raw_rewards)
    terminal_victory = value["terminal_victory"]
    if terminal_victory not in (0, 1):
        raise CardOptimizerReplayBlocked("replay victory differs")
    return runtime.ArmEpisodeRollout(
        arm="candidate",
        seed=seed,
        trajectory_id=trajectory_id,
        decisions=tuple(decisions),
        transitions=tuple({} for _ in decisions),
        rewards=rewards,
        final_snapshot={"terminal": True},
        floor_progress=_finite(value["floor_progress"], "replay floor progress"),
        terminal_victory=int(terminal_victory),
        unsupported_reason=None,
    )


def decode_replay(stored: bytes, binding: Mapping[str, Any]) -> DecodedReplay:
    normalized = _validate_binding(binding)
    if not isinstance(stored, bytes) or len(stored) != normalized["stored_size_bytes"]:
        raise CardOptimizerReplayBlocked("replay stored size differs")
    if hashlib.sha256(stored).hexdigest() != normalized["stored_sha256"]:
        raise CardOptimizerReplayBlocked("replay stored hash differs")
    canonical = _bounded_gzip(
        stored, expected_size=int(normalized["canonical_size_bytes"])
    )
    if hashlib.sha256(canonical).hexdigest() != normalized["canonical_sha256"]:
        raise CardOptimizerReplayBlocked("replay canonical hash differs")
    try:
        value = json.loads(canonical.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CardOptimizerReplayBlocked("replay canonical JSON is invalid") from exc
    if _canonical_bytes(value) != canonical or not isinstance(value, Mapping) or set(value) != {
        "episodes",
        "generator_states",
        "schema_version",
    } or value["schema_version"] != SCHEMA_VERSION:
        raise CardOptimizerReplayBlocked("replay canonical object differs")
    raw_episodes = value["episodes"]
    if isinstance(raw_episodes, (str, bytes)) or not isinstance(raw_episodes, Sequence):
        raise CardOptimizerReplayBlocked("replay episodes differ")
    episodes = tuple(
        _decode_episode(raw, position) for position, raw in enumerate(raw_episodes)
    )
    seeds = tuple(episode.seed for episode in episodes)
    if not episodes or seeds != tuple(sorted(set(seeds))):
        raise CardOptimizerReplayBlocked("replay episode order differs")
    raw_generators = value["generator_states"]
    if not isinstance(raw_generators, Mapping) or set(raw_generators) != set(GENERATOR_NAMES):
        raise CardOptimizerReplayBlocked("replay generator fields differ")
    generators = {
        name: runtime._decode_tensor(raw_generators[name], f"generator.{name}")
        for name in GENERATOR_NAMES
    }
    if _gzip_bytes(canonical) != stored:
        raise CardOptimizerReplayBlocked("replay deterministic gzip differs")
    decoded = DecodedReplay(episodes=episodes, generator_states=generators)
    reencoded = encode_replay(episodes, generator_states=generators)
    if reencoded.stored != stored or reencoded.binding != normalized:
        raise CardOptimizerReplayBlocked("replay round trip differs")
    return decoded


def apply_generator_states(
    bootstrap: runtime.PairedBootstrap,
    generator_states: Mapping[str, torch.Tensor],
) -> None:
    if set(generator_states) != set(GENERATOR_NAMES) or set(
        bootstrap.generators
    ) != set(GENERATOR_NAMES):
        raise CardOptimizerReplayBlocked("replay generator identity differs")
    try:
        for name in GENERATOR_NAMES:
            bootstrap.generators[name].set_state(generator_states[name].clone())
    except RuntimeError as exc:
        raise CardOptimizerReplayBlocked("replay generator state differs") from exc


def rebuild_episode_terms(
    bootstrap: runtime.PairedBootstrap,
    episodes: Sequence[runtime.ArmEpisodeRollout],
) -> tuple[runtime.ArmEpisodeRollout, ...]:
    rebuilt = []
    for episode in episodes:
        decisions = []
        for decision in episode.decisions:
            if decision.category == "card_reward":
                if decision.candidate_features is None or not decision.candidates:
                    raise CardOptimizerReplayBlocked("replay card context is unavailable")
                output = runtime.forward_card_policy(
                    bootstrap,
                    arm="candidate",
                    state_features=decision.state_features,
                    candidate_features=decision.candidate_features,
                    candidates=decision.candidates,
                )
                terms = build_card_acceptance_policy_terms(
                    output.family_logits,
                    output.conditional_logits,
                    decision.candidates,
                    decision.selected_action_id,
                    category="card_reward",
                )
            else:
                terms = None
            decisions.append(
                runtime.ArmRolloutDecision(
                    arm=decision.arm,
                    category=decision.category,
                    decision_id=decision.decision_id,
                    decision_index=decision.decision_index,
                    selected_action_id=decision.selected_action_id,
                    state_features=decision.state_features.detach().clone(),
                    card_terms=terms,
                    diagnostic={},
                    candidate_features=None
                    if decision.candidate_features is None
                    else decision.candidate_features.detach().clone(),
                    candidates=copy.deepcopy(decision.candidates),
                )
            )
        rebuilt.append(
            runtime.ArmEpisodeRollout(
                arm=episode.arm,
                seed=episode.seed,
                trajectory_id=episode.trajectory_id,
                decisions=tuple(decisions),
                transitions=copy.deepcopy(episode.transitions),
                rewards=episode.rewards,
                final_snapshot=copy.deepcopy(episode.final_snapshot),
                floor_progress=episode.floor_progress,
                terminal_victory=episode.terminal_victory,
                unsupported_reason=episode.unsupported_reason,
            )
        )
    return tuple(rebuilt)


__all__ = [
    "CardOptimizerReplayBlocked",
    "DecodedReplay",
    "EncodedReplay",
    "apply_generator_states",
    "decode_replay",
    "encode_replay",
    "rebuild_episode_terms",
]
