"""Generate paired LightSTS action advantage labels over a guarded baseline."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    MappedCombatState,
    NativeCombatEnvironment,
    collect_provenance,
    load_native_module,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    _policy_action,
    apply_deployment_guard_proxy,
    calculate_native_reward,
    create_fresh_trainer,
    encounter_from_snapshot,
    initialize_trainer,
    initialization_failure_reason,
    load_initial_checkpoint,
    parameter_sha256,
    sha256_file,
    successor_disposition,
)
from spirecomm.ai.rl.v2 import action_space  # noqa: E402
from spirecomm.ai.rl.v2.id_mapping import IdMapper, build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2  # noqa: E402


SCHEMA_VERSION = 1
CORPUS_KIND = "combat_guard_advantage_corpus"
HAND_OFFSET = (
    StateEncoderV2.PLAYER_FEATURES
    + StateEncoderV2.MONSTER_SLOTS * StateEncoderV2.MONSTER_FEATURES
)
POSITIVE_ADVANTAGE_MARGIN = 0.5
MINIMUM_POSITIVE_TRAINING_STATES = 100
MINIMUM_POSITIVE_TARGET_IDENTITIES = 3


@dataclass(frozen=True)
class CorpusConfig:
    train_seeds: tuple[int, ...]
    evaluation_seeds: tuple[int, ...]
    battle_indices: tuple[int, ...] = (0, 3, 6, 9)
    ascension: int = 0
    max_source_decisions: int = 100
    max_actions_per_turn: int = 8
    max_states_per_profile: int = 2
    max_canonical_actions: int = 8
    continuation_decisions: int = 8
    return_discount: float = 0.99
    positive_advantage_margin: float = POSITIVE_ADVANTAGE_MARGIN

    def validate(self) -> None:
        if not self.train_seeds or not self.evaluation_seeds:
            raise ValueError("guard advantage corpus requires both seed partitions")
        if set(self.train_seeds) & set(self.evaluation_seeds):
            raise ValueError("guard advantage seed partitions overlap")
        if not self.battle_indices or any(value < 0 for value in self.battle_indices):
            raise ValueError("guard advantage battle indices are invalid")
        for name in (
            "max_source_decisions",
            "max_actions_per_turn",
            "max_states_per_profile",
            "max_canonical_actions",
            "continuation_decisions",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"guard advantage {name} must be positive")
        if not math.isfinite(self.return_discount) or not (
            0.0 < self.return_discount <= 1.0
        ):
            raise ValueError("guard advantage return discount is invalid")
        if not math.isfinite(self.positive_advantage_margin) or (
            self.positive_advantage_margin <= 0.0
        ):
            raise ValueError("guard advantage margin must be positive")


@dataclass(frozen=True)
class BranchResult:
    action_index: int
    total_return: float
    transition_count: int
    terminal: bool
    complete: bool
    exclusion_reason: str = ""


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ).encode("ascii") + b"\n"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _card_features(mapped: MappedCombatState, slot: int) -> tuple[float, ...]:
    start = HAND_OFFSET + slot * StateEncoderV2.HAND_FEATURES
    values = mapped.state.continuous[start : start + StateEncoderV2.HAND_FEATURES]
    return tuple(float(value) for value in values.tolist())


def canonical_action_key(
    action: Mapping[str, Any], mapped: MappedCombatState
) -> tuple[Any, ...]:
    index = int(action["rl_action_index"])
    if action_space.PLAY_CARD_OFFSET <= index < action_space.USE_POTION_OFFSET:
        offset = index - action_space.PLAY_CARD_OFFSET
        slot = offset // action_space.TARGET_SLOTS
        target = offset % action_space.TARGET_SLOTS
        return (
            "play_card",
            int(mapped.state.card_ids[slot]),
            _card_features(mapped, slot),
            target,
        )
    if action_space.USE_POTION_OFFSET <= index < action_space.END_TURN_ACTION:
        offset = index - action_space.USE_POTION_OFFSET
        slot = offset // action_space.TARGET_SLOTS
        target = offset % action_space.TARGET_SLOTS
        return ("use_potion", int(mapped.state.potion_ids[slot]), target)
    return (str(action.get("kind") or "other"), index)


def canonical_action_identity(key: tuple[Any, ...]) -> str:
    return hashlib.sha256(
        json.dumps(key, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()


def canonicalize_actions(
    actions: Sequence[Mapping[str, Any]], mapped: MappedCombatState
) -> tuple[list[dict[str, Any]], dict[int, int]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for raw in actions:
        action = dict(raw)
        if not bool(action.get("available", True)):
            continue
        groups.setdefault(canonical_action_key(action, mapped), []).append(action)
    representatives: list[dict[str, Any]] = []
    exact_to_representative: dict[int, int] = {}
    for grouped in groups.values():
        representative = min(grouped, key=lambda row: int(row["rl_action_index"]))
        representative_index = int(representative["rl_action_index"])
        representatives.append(representative)
        for action in grouped:
            exact_to_representative[int(action["rl_action_index"])] = (
                representative_index
            )
    representatives.sort(key=lambda row: int(row["rl_action_index"]))
    return representatives, exact_to_representative


def select_advantage_label(
    branch_results: Sequence[BranchResult],
    *,
    guard_action_index: int,
    positive_margin: float,
) -> dict[str, Any]:
    if not branch_results:
        raise ValueError("guard advantage label requires branch results")
    if any(not row.complete for row in branch_results):
        reason = next(
            row.exclusion_reason for row in branch_results if not row.complete
        )
        return {"complete": False, "exclusion_reason": reason}
    by_index = {row.action_index: row for row in branch_results}
    if len(by_index) != len(branch_results) or guard_action_index not in by_index:
        raise ValueError("guard advantage branch identity differs")
    baseline_return = by_index[guard_action_index].total_return
    target = max(
        branch_results,
        key=lambda row: (row.total_return, -row.action_index),
    )
    advantage = float(target.total_return - baseline_return)
    return {
        "complete": True,
        "guard_return": float(baseline_return),
        "target_action_index": int(target.action_index),
        "target_return": float(target.total_return),
        "target_advantage": advantage,
        "positive": advantage >= positive_margin,
    }


def rollout_branch(
    source_environment: NativeCombatEnvironment,
    first_action: Mapping[str, Any],
    *,
    source_actions_since_end_turn: int,
    continuation_selector: Callable[
        [NativeCombatEnvironment, int], Mapping[str, Any]
    ],
    continuation_decisions: int,
    discount: float,
    reward_fn: Callable[..., Mapping[str, float]] = calculate_native_reward,
) -> BranchResult:
    environment = source_environment.clone()
    total_return = 0.0
    transition_count = 0
    action = dict(first_action)
    actions_since_end_turn = source_actions_since_end_turn
    for offset in range(continuation_decisions + 1):
        if offset:
            status = environment.status()
            disposition, reason = successor_disposition(status)
            if disposition == "terminal":
                return BranchResult(
                    action_index=int(first_action["rl_action_index"]),
                    total_return=total_return,
                    transition_count=transition_count,
                    terminal=True,
                    complete=True,
                )
            if disposition == "exclude":
                return BranchResult(
                    action_index=int(first_action["rl_action_index"]),
                    total_return=total_return,
                    transition_count=transition_count,
                    terminal=False,
                    complete=False,
                    exclusion_reason=reason,
                )
            action = dict(continuation_selector(environment, actions_since_end_turn))
        before = environment.snapshot()
        environment.step(str(action["action_id"]))
        status = environment.status()
        after = environment.snapshot()
        disposition, reason = successor_disposition(status)
        if disposition == "exclude":
            return BranchResult(
                action_index=int(first_action["rl_action_index"]),
                total_return=total_return,
                transition_count=transition_count,
                terminal=False,
                complete=False,
                exclusion_reason=reason,
            )
        reward = reward_fn(
            before,
            after,
            action_kind=str(action["kind"]),
            outcome=str(status.get("outcome") or "undecided"),
        )
        total_return += (discount**offset) * float(reward["total"])
        transition_count += 1
        actions_since_end_turn = (
            0 if action["kind"] == "end_turn" else actions_since_end_turn + 1
        )
        if disposition == "terminal":
            return BranchResult(
                action_index=int(first_action["rl_action_index"]),
                total_return=total_return,
                transition_count=transition_count,
                terminal=True,
                complete=True,
            )
    return BranchResult(
        action_index=int(first_action["rl_action_index"]),
        total_return=total_return,
        transition_count=transition_count,
        terminal=False,
        complete=True,
    )


def corpus_sufficiency(
    train_summary: Mapping[str, Any], evaluation_summary: Mapping[str, Any]
) -> dict[str, Any]:
    conditions = {
        "train_contains_positive_and_negative": (
            int(train_summary["positive_count"]) > 0
            and int(train_summary["negative_count"]) > 0
        ),
        "evaluation_contains_positive_and_negative": (
            int(evaluation_summary["positive_count"]) > 0
            and int(evaluation_summary["negative_count"]) > 0
        ),
        "train_positive_count_at_least_minimum": int(
            train_summary["positive_count"]
        )
        >= MINIMUM_POSITIVE_TRAINING_STATES,
        "train_positive_target_identities_at_least_minimum": int(
            train_summary["positive_target_identity_count"]
        )
        >= MINIMUM_POSITIVE_TARGET_IDENTITIES,
    }
    return {
        "conditions": conditions,
        "all_conditions_passed": all(conditions.values()),
        "decision": (
            "corpus_sufficient_for_registered_residual_fit"
            if all(conditions.values())
            else "corpus_insufficient_stop_before_fit"
        ),
    }


def _continuation_selector(
    trainer: Any,
    id_mapper: IdMapper,
    *,
    max_actions_per_turn: int,
) -> Callable[[NativeCombatEnvironment, int], Mapping[str, Any]]:
    def select(
        environment: NativeCombatEnvironment, actions_since_end_turn: int
    ) -> Mapping[str, Any]:
        mapped = environment.mapped_state(id_mapper=id_mapper)
        before = environment.snapshot()
        legal = environment.legal_actions()
        raw = _policy_action(
            trainer,
            mapped,
            legal,
            actions_since_end_turn=actions_since_end_turn,
            max_actions_per_turn=max_actions_per_turn,
        )
        guarded, _ = apply_deployment_guard_proxy(
            environment,
            raw,
            legal,
            before,
            mode=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
            policy_selected=actions_since_end_turn < max_actions_per_turn,
        )
        return guarded

    return select


def _empty_tensors(trainer: Any) -> dict[str, torch.Tensor]:
    return {
        "continuous": torch.empty((0, trainer.continuous_dim), dtype=torch.float32),
        "card_ids": torch.empty((0, trainer.card_slots), dtype=torch.long),
        "potion_ids": torch.empty((0, trainer.potion_slots), dtype=torch.long),
        "relic_ids": torch.empty((0, trainer.relic_slots), dtype=torch.long),
        "action_masks": torch.empty((0, trainer.action_dim), dtype=torch.bool),
        "guard_actions": torch.empty(0, dtype=torch.long),
        "target_actions": torch.empty(0, dtype=torch.long),
        "advantages": torch.empty(0, dtype=torch.float32),
        "positive": torch.empty(0, dtype=torch.bool),
    }


def _stack_rows(rows: Sequence[Mapping[str, Any]], trainer: Any) -> dict[str, Any]:
    if not rows:
        return {"tensors": _empty_tensors(trainer), "metadata": []}
    tensor_names = (
        "continuous",
        "card_ids",
        "potion_ids",
        "relic_ids",
        "action_masks",
    )
    tensors = {
        name: torch.stack([row[name] for row in rows]) for name in tensor_names
    }
    tensors.update(
        {
            "guard_actions": torch.tensor(
                [row["guard_action_index"] for row in rows], dtype=torch.long
            ),
            "target_actions": torch.tensor(
                [row["target_action_index"] for row in rows], dtype=torch.long
            ),
            "advantages": torch.tensor(
                [row["target_advantage"] for row in rows], dtype=torch.float32
            ),
            "positive": torch.tensor(
                [row["positive"] for row in rows], dtype=torch.bool
            ),
        }
    )
    metadata = [
        {key: value for key, value in row.items() if key not in tensor_names}
        for row in rows
    ]
    return {"tensors": tensors, "metadata": metadata}


def _partition_summary(
    rows: Sequence[Mapping[str, Any]],
    *,
    profile_count_registered: int,
    profile_count_initialized: int,
    decisions: int,
    skip_reasons: Counter[str],
    exclusion_reasons: Counter[str],
    initialization_failures: Counter[str],
) -> dict[str, Any]:
    positive = [row for row in rows if row["positive"]]
    advantages = [float(row["target_advantage"]) for row in rows]
    targets = Counter(row["target_identity"] for row in positive)
    encounters = Counter(row["encounter"] for row in rows)
    branch_counts = [int(row["branch_count"]) for row in rows]
    return {
        "profile_count_registered": profile_count_registered,
        "profile_count_initialized": profile_count_initialized,
        "source_decision_count": decisions,
        "retained_state_count": len(rows),
        "positive_count": len(positive),
        "negative_count": len(rows) - len(positive),
        "positive_share": len(positive) / len(rows) if rows else None,
        "positive_target_identity_count": len(targets),
        "positive_target_identity_counts": dict(sorted(targets.items())),
        "encounter_counts": dict(sorted(encounters.items())),
        "skip_reason_counts": dict(sorted(skip_reasons.items())),
        "exclusion_reason_counts": dict(sorted(exclusion_reasons.items())),
        "initialization_failure_counts": dict(
            sorted(initialization_failures.items())
        ),
        "advantage": (
            {
                "minimum": min(advantages),
                "mean": statistics.fmean(advantages),
                "maximum": max(advantages),
            }
            if advantages
            else None
        ),
        "branch_count": (
            {
                "minimum": min(branch_counts),
                "mean": statistics.fmean(branch_counts),
                "maximum": max(branch_counts),
            }
            if branch_counts
            else None
        ),
    }


def collect_partition(
    native_module: ModuleType,
    *,
    id_mapper: IdMapper,
    trainer: Any,
    seeds: Sequence[int],
    config: CorpusConfig,
) -> tuple[dict[str, Any], dict[str, Any]]:
    config.validate()
    rows: list[dict[str, Any]] = []
    skip_reasons: Counter[str] = Counter()
    exclusion_reasons: Counter[str] = Counter()
    initialization_failures: Counter[str] = Counter()
    decisions = 0
    initialized = 0
    continuation = _continuation_selector(
        trainer,
        id_mapper,
        max_actions_per_turn=config.max_actions_per_turn,
    )
    was_training = trainer.online_network.training
    trainer.online_network.eval()
    try:
        for seed in seeds:
            for battle_index in config.battle_indices:
                try:
                    environment = NativeCombatEnvironment.reset(
                        native_module, seed, config.ascension, battle_index
                    )
                except Exception as exc:
                    initialization_failures[
                        initialization_failure_reason(exc)
                    ] += 1
                    continue
                initialized += 1
                actions_since_end_turn = 0
                retained_for_profile = 0
                for _ in range(config.max_source_decisions):
                    status = environment.status()
                    disposition, reason = successor_disposition(status)
                    if disposition != "supported":
                        if disposition == "exclude":
                            skip_reasons[f"source_unsupported:{reason}"] += 1
                        break
                    before = environment.snapshot()
                    mapped = environment.mapped_state(id_mapper=id_mapper)
                    legal = environment.legal_actions()
                    raw = _policy_action(
                        trainer,
                        mapped,
                        legal,
                        actions_since_end_turn=actions_since_end_turn,
                        max_actions_per_turn=config.max_actions_per_turn,
                    )
                    guarded, guard_telemetry = apply_deployment_guard_proxy(
                        environment,
                        raw,
                        legal,
                        before,
                        mode=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
                        policy_selected=(
                            actions_since_end_turn < config.max_actions_per_turn
                        ),
                    )
                    decisions += 1
                    if raw["kind"] != "end_turn":
                        skip_reasons["parent_not_end_turn"] += 1
                    elif not guard_telemetry["guard_proxy_replacement_count"]:
                        skip_reasons["guard_not_replaced"] += 1
                    else:
                        canonical, representatives = canonicalize_actions(
                            legal, mapped
                        )
                        guard_index = representatives[int(guarded["rl_action_index"])]
                        if len(canonical) <= 1:
                            skip_reasons["no_distinct_alternative"] += 1
                        elif len(canonical) > config.max_canonical_actions:
                            skip_reasons["too_many_canonical_actions"] += 1
                        else:
                            branches = [
                                rollout_branch(
                                    environment,
                                    action,
                                    source_actions_since_end_turn=(
                                        actions_since_end_turn
                                    ),
                                    continuation_selector=continuation,
                                    continuation_decisions=(
                                        config.continuation_decisions
                                    ),
                                    discount=config.return_discount,
                                )
                                for action in canonical
                            ]
                            label = select_advantage_label(
                                branches,
                                guard_action_index=guard_index,
                                positive_margin=(
                                    config.positive_advantage_margin
                                ),
                            )
                            if not label["complete"]:
                                exclusion_reasons[label["exclusion_reason"]] += 1
                            else:
                                target_index = int(label["target_action_index"])
                                target_action = next(
                                    action
                                    for action in canonical
                                    if int(action["rl_action_index"])
                                    == target_index
                                )
                                target_key = canonical_action_key(
                                    target_action, mapped
                                )
                                rows.append(
                                    {
                                        "continuous": torch.from_numpy(
                                            mapped.state.continuous.copy()
                                        ).float(),
                                        "card_ids": torch.from_numpy(
                                            mapped.state.card_ids.copy()
                                        ).long(),
                                        "potion_ids": torch.from_numpy(
                                            mapped.state.potion_ids.copy()
                                        ).long(),
                                        "relic_ids": torch.from_numpy(
                                            mapped.state.relic_ids.copy()
                                        ).long(),
                                        "action_masks": torch.from_numpy(
                                            mapped.action_mask.copy()
                                        ).bool(),
                                        "seed": int(seed),
                                        "battle_index": int(battle_index),
                                        "act": int(before["state"]["act"]),
                                        "floor": int(before["state"]["floor"]),
                                        "turn": int(before["state"]["turn"]),
                                        "encounter": encounter_from_snapshot(before),
                                        "raw_parent_action_index": int(
                                            raw["rl_action_index"]
                                        ),
                                        "guard_action_index": guard_index,
                                        "target_action_index": target_index,
                                        "target_identity": canonical_action_identity(
                                            target_key
                                        ),
                                        "guard_return": label["guard_return"],
                                        "target_return": label["target_return"],
                                        "target_advantage": label[
                                            "target_advantage"
                                        ],
                                        "positive": label["positive"],
                                        "branch_count": len(branches),
                                        "branch_returns": {
                                            str(branch.action_index): branch.total_return
                                            for branch in branches
                                        },
                                    }
                                )
                                retained_for_profile += 1
                    if retained_for_profile >= config.max_states_per_profile:
                        break
                    environment.step(str(guarded["action_id"]))
                    actions_since_end_turn = (
                        0
                        if guarded["kind"] == "end_turn"
                        else actions_since_end_turn + 1
                    )
    finally:
        trainer.online_network.train(was_training)
    corpus = _stack_rows(rows, trainer)
    summary = _partition_summary(
        rows,
        profile_count_registered=len(seeds) * len(config.battle_indices),
        profile_count_initialized=initialized,
        decisions=decisions,
        skip_reasons=skip_reasons,
        exclusion_reasons=exclusion_reasons,
        initialization_failures=initialization_failures,
    )
    return corpus, summary


def _parse_seeds(value: str) -> tuple[int, ...]:
    text = value.strip()
    if ".." in text:
        start_text, end_text = text.split("..", 1)
        start, end = int(start_text), int(end_text)
        if end < start:
            raise argparse.ArgumentTypeError("seed range end precedes start")
        return tuple(range(start, end + 1))
    return tuple(int(part.strip()) for part in text.split(",") if part.strip())


def _render_summary(report: Mapping[str, Any]) -> str:
    train = report["partitions"]["train"]
    evaluation = report["partitions"]["evaluation"]
    return "\n".join(
        (
            "# Combat Guard-Advantage Corpus",
            "",
            f"- Decision: `{report['sufficiency']['decision']}`",
            f"- Train states: `{train['retained_state_count']}`; positive: `{train['positive_count']}`",
            f"- Evaluation states: `{evaluation['retained_state_count']}`; positive: `{evaluation['positive_count']}`",
            f"- Positive train target identities: `{train['positive_target_identity_count']}`",
            "",
            "This is simulator-only corpus evidence. It grants no gameplay,",
            "qualification, promotion, or production authority.",
            "",
        )
    )


def run(
    *,
    repo_root: Path,
    simulator_repo: Path,
    module_path: Path,
    items_json: Path,
    initial_checkpoint_path: Path,
    initial_checkpoint_sha256: str,
    output_dir: Path,
    config: CorpusConfig,
) -> dict[str, Any]:
    config.validate()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"guard advantage output already exists: {output_dir}")
    native_module = load_native_module(module_path)
    id_mapper = build_id_mapper(items_json)
    initial = load_initial_checkpoint(
        initial_checkpoint_path,
        expected_sha256=initial_checkpoint_sha256,
    )
    trainer = create_fresh_trainer(
        id_mapper,
        seed=2026082845,
        batch_size=128,
        learning_starts=128,
    )
    parent_state, initialization = initialize_trainer(trainer, initial)
    train_corpus, train_summary = collect_partition(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        seeds=config.train_seeds,
        config=config,
    )
    evaluation_corpus, evaluation_summary = collect_partition(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        seeds=config.evaluation_seeds,
        config=config,
    )
    sufficiency = corpus_sufficiency(train_summary, evaluation_summary)
    provenance = collect_provenance(
        repo_root=repo_root,
        simulator_repo=simulator_repo,
        module_path=module_path,
        native_module=native_module,
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "corpus_kind": CORPUS_KIND,
        "source_commit": provenance["adapter_commit"],
        "config": asdict(config),
        "bindings": {
            "module": {
                "path": str(module_path.resolve()),
                "sha256": sha256_file(module_path),
            },
            "items_json": {
                "path": str(items_json.resolve()),
                "sha256": sha256_file(items_json),
            },
            "initial_checkpoint": {
                "path": str(initial_checkpoint_path.resolve()),
                "sha256": initial_checkpoint_sha256,
                "parameter_sha256": parameter_sha256(parent_state),
            },
            "runner": {
                "path": str(Path(__file__).resolve()),
                "sha256": sha256_file(Path(__file__)),
            },
        },
        "initialization": initialization,
        "partitions": {
            "train": train_summary,
            "evaluation": evaluation_summary,
        },
        "sufficiency": sufficiency,
        "provenance": provenance,
        "authority": {
            "cpu_corpus_generation": True,
            "native_loading": True,
            "model_fitting": False,
            "gameplay": False,
            "communication_mod": False,
            "production_checkpoint_loading": False,
            "qualification": False,
            "promotion": False,
        },
    }
    output_dir.mkdir(parents=True)
    torch.save(
        {
            "schema_version": SCHEMA_VERSION,
            "corpus_kind": CORPUS_KIND,
            "partition": "train",
            **train_corpus,
        },
        output_dir / "train_corpus.pt",
    )
    torch.save(
        {
            "schema_version": SCHEMA_VERSION,
            "corpus_kind": CORPUS_KIND,
            "partition": "evaluation",
            **evaluation_corpus,
        },
        output_dir / "evaluation_corpus.pt",
    )
    (output_dir / "report.json").write_bytes(_canonical_json_bytes(report))
    (output_dir / "summary.md").write_text(
        _render_summary(report), encoding="ascii", newline="\n"
    )
    report["artifacts"] = {
        name: {
            "sha256": _sha256(output_dir / name),
            "size_bytes": (output_dir / name).stat().st_size,
        }
        for name in (
            "train_corpus.pt",
            "evaluation_corpus.pt",
            "report.json",
            "summary.md",
        )
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--simulator-repo", type=Path, required=True)
    parser.add_argument("--module", type=Path, required=True)
    parser.add_argument("--items-json", type=Path, required=True)
    parser.add_argument("--initial-checkpoint", type=Path, required=True)
    parser.add_argument("--initial-checkpoint-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--train-seeds", type=_parse_seeds, required=True)
    parser.add_argument("--evaluation-seeds", type=_parse_seeds, required=True)
    parser.add_argument("--battle-indices", type=_parse_seeds, default="0,3,6,9")
    parser.add_argument("--max-states-per-profile", type=int, default=2)
    args = parser.parse_args()
    report = run(
        repo_root=args.repo_root,
        simulator_repo=args.simulator_repo,
        module_path=args.module,
        items_json=args.items_json,
        initial_checkpoint_path=args.initial_checkpoint,
        initial_checkpoint_sha256=args.initial_checkpoint_sha256,
        output_dir=args.output_dir,
        config=CorpusConfig(
            train_seeds=args.train_seeds,
            evaluation_seeds=args.evaluation_seeds,
            battle_indices=args.battle_indices,
            max_states_per_profile=args.max_states_per_profile,
        ),
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir.resolve()),
                "decision": report["sufficiency"]["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
