"""Audit a latent-gated candidate against the deployed guarded action baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    create_fresh_trainer,
    initialize_trainer,
    load_initial_checkpoint,
    parameter_sha256,
    sha256_file,
)
from analysis_scripts.combat_rl_latent_gated_candidate_fit import (  # noqa: E402
    _adapter_metadata,
    _load_replay_corpus,
    _trainer_metadata,
)
from spirecomm.ai.rl.v2 import action_space  # noqa: E402
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.latent_gated_adapter import (  # noqa: E402
    load_development_artifact,
)
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2  # noqa: E402


SCHEMA_VERSION = 1
AUDIT_ID = "combat-rl-guard-aware-counterfactual-audit-20260828-r1"
DEFAULT_THRESHOLDS = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.99)
HAND_OFFSET = (
    StateEncoderV2.PLAYER_FEATURES
    + StateEncoderV2.MONSTER_SLOTS * StateEncoderV2.MONSTER_FEATURES
)


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


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _card_features(continuous: torch.Tensor, slots: torch.Tensor) -> torch.Tensor:
    rows = torch.arange(slots.numel())
    offsets = HAND_OFFSET + slots * StateEncoderV2.HAND_FEATURES
    feature_offsets = torch.arange(StateEncoderV2.HAND_FEATURES)
    return continuous[rows[:, None], offsets[:, None] + feature_offsets[None, :]]


def behavior_equivalent_actions(
    left: torch.Tensor,
    right: torch.Tensor,
    *,
    continuous: torch.Tensor,
    card_ids: torch.Tensor,
    potion_ids: torch.Tensor,
) -> torch.Tensor:
    """Treat identical card or potion copies in different slots as equivalent."""
    left = left.detach().cpu().long().reshape(-1)
    right = right.detach().cpu().long().reshape(-1)
    continuous = continuous.detach().cpu().float()
    card_ids = card_ids.detach().cpu().long()
    potion_ids = potion_ids.detach().cpu().long()
    row_count = left.numel()
    if right.numel() != row_count or any(
        value.shape[0] != row_count
        for value in (continuous, card_ids, potion_ids)
    ):
        raise ValueError("behavior-equivalence row count differs")

    equivalent = left.eq(right)
    card_rows = (
        left.ge(action_space.PLAY_CARD_OFFSET)
        & left.lt(action_space.USE_POTION_OFFSET)
        & right.ge(action_space.PLAY_CARD_OFFSET)
        & right.lt(action_space.USE_POTION_OFFSET)
    )
    if bool(card_rows.any()):
        indices = torch.where(card_rows)[0]
        left_offsets = left[indices] - action_space.PLAY_CARD_OFFSET
        right_offsets = right[indices] - action_space.PLAY_CARD_OFFSET
        left_slots = torch.div(
            left_offsets, action_space.TARGET_SLOTS, rounding_mode="floor"
        )
        right_slots = torch.div(
            right_offsets, action_space.TARGET_SLOTS, rounding_mode="floor"
        )
        same_target = left_offsets.remainder(action_space.TARGET_SLOTS).eq(
            right_offsets.remainder(action_space.TARGET_SLOTS)
        )
        same_id = card_ids[indices, left_slots].eq(
            card_ids[indices, right_slots]
        )
        same_features = _card_features(
            continuous[indices], left_slots
        ).eq(_card_features(continuous[indices], right_slots)).all(dim=1)
        equivalent[indices] = same_target & same_id & same_features

    potion_rows = (
        left.ge(action_space.USE_POTION_OFFSET)
        & left.lt(action_space.END_TURN_ACTION)
        & right.ge(action_space.USE_POTION_OFFSET)
        & right.lt(action_space.END_TURN_ACTION)
    )
    if bool(potion_rows.any()):
        indices = torch.where(potion_rows)[0]
        left_offsets = left[indices] - action_space.USE_POTION_OFFSET
        right_offsets = right[indices] - action_space.USE_POTION_OFFSET
        left_slots = torch.div(
            left_offsets, action_space.TARGET_SLOTS, rounding_mode="floor"
        )
        right_slots = torch.div(
            right_offsets, action_space.TARGET_SLOTS, rounding_mode="floor"
        )
        same_target = left_offsets.remainder(action_space.TARGET_SLOTS).eq(
            right_offsets.remainder(action_space.TARGET_SLOTS)
        )
        equivalent[indices] = same_target & potion_ids[
            indices, left_slots
        ].eq(potion_ids[indices, right_slots])
    return equivalent


def _count(mask: torch.Tensor) -> int:
    return int(mask.sum().item())


def _stratum_metrics(
    *,
    selected: torch.Tensor,
    baseline: torch.Tensor,
    changed: torch.Tensor,
    open_mask: torch.Tensor,
    equivalent: torch.Tensor,
) -> dict[str, Any]:
    exact = selected.eq(baseline)
    changed_open = changed & open_mask
    direct = ~changed
    return {
        "row_count": int(changed.numel()),
        "changed_row_count": _count(changed),
        "direct_row_count": _count(direct),
        "changed_open_count": _count(changed_open),
        "changed_open_share": _ratio(_count(changed_open), _count(changed)),
        "changed_open_exact_precision": _ratio(
            _count(exact & changed_open), _count(changed_open)
        ),
        "changed_open_behavior_precision": _ratio(
            _count(equivalent & changed_open), _count(changed_open)
        ),
        "changed_exact_agreement": _ratio(
            _count(exact & changed), _count(changed)
        ),
        "changed_behavior_agreement": _ratio(
            _count(equivalent & changed), _count(changed)
        ),
        "direct_exact_preservation": _ratio(
            _count(exact & direct), _count(direct)
        ),
        "direct_behavior_preservation": _ratio(
            _count(equivalent & direct), _count(direct)
        ),
    }


def evaluate_replay(
    adapter: Any,
    raw: Mapping[str, torch.Tensor],
    *,
    thresholds: Sequence[float],
) -> dict[str, Any]:
    inputs = {
        name: raw[name]
        for name in (
            "continuous",
            "card_ids",
            "potion_ids",
            "relic_ids",
            "action_masks",
        )
    }
    with torch.no_grad():
        selected = adapter.select_actions(**inputs)
    baseline = raw["executed_actions"].detach().cpu().long()
    changed = raw["changed"].detach().cpu().bool()
    proposals = selected.parent_actions.detach().cpu()
    if not bool(changed.eq(proposals.ne(baseline)).all()):
        raise ValueError("audit changed label differs from guarded baseline")

    correction = selected.correction_actions.detach().cpu()
    configured = selected.actions.detach().cpu()
    gate_scores = selected.gate_probabilities.detach().cpu()
    correction_equivalent = behavior_equivalent_actions(
        correction,
        baseline,
        continuous=raw["continuous"],
        card_ids=raw["card_ids"],
        potion_ids=raw["potion_ids"],
    )
    configured_equivalent = behavior_equivalent_actions(
        configured,
        baseline,
        continuous=raw["continuous"],
        card_ids=raw["card_ids"],
        potion_ids=raw["potion_ids"],
    )
    configured_metrics = _stratum_metrics(
        selected=configured,
        baseline=baseline,
        changed=changed,
        open_mask=selected.gate_open.detach().cpu(),
        equivalent=configured_equivalent,
    )
    correction_exact = correction.eq(baseline)
    parent_end_turn = proposals.eq(action_space.END_TURN_ACTION)
    configured_metrics.update(
        {
            "changed_parent_end_turn_count": _count(changed & parent_end_turn),
            "changed_parent_end_turn_share": _ratio(
                _count(changed & parent_end_turn), _count(changed)
            ),
            "changed_correction_exact_agreement": _ratio(
                _count(correction_exact & changed), _count(changed)
            ),
            "changed_correction_behavior_agreement": _ratio(
                _count(correction_equivalent & changed), _count(changed)
            ),
        }
    )

    threshold_reports: dict[str, Any] = {}
    for threshold in sorted(set(float(value) for value in thresholds)):
        open_mask = gate_scores.ge(threshold)
        actions = torch.where(open_mask, correction, selected.parent_actions.cpu())
        equivalent = behavior_equivalent_actions(
            actions,
            baseline,
            continuous=raw["continuous"],
            card_ids=raw["card_ids"],
            potion_ids=raw["potion_ids"],
        )
        threshold_reports[f"{threshold:.9f}"] = _stratum_metrics(
            selected=actions,
            baseline=baseline,
            changed=changed,
            open_mask=open_mask,
            equivalent=equivalent,
        )
    return {
        "configured_threshold": float(adapter.config.gate_threshold),
        "configured": configured_metrics,
        "threshold_sensitivity": threshold_reports,
    }


def _concat_raw(corpora: Sequence[Mapping[str, Any]]) -> dict[str, torch.Tensor]:
    fields = (
        "continuous",
        "card_ids",
        "potion_ids",
        "relic_ids",
        "action_masks",
        "executed_actions",
        "changed",
    )
    return {
        field: torch.cat([corpus["raw"][field] for corpus in corpora], dim=0)
        for field in fields
    }


def _current_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()


def _render_analysis(report: Mapping[str, Any]) -> str:
    aggregate = report["evaluation_aggregate"]["configured"]
    sensitivity = report["evaluation_aggregate"]["threshold_sensitivity"]
    behavior = aggregate["changed_behavior_agreement"]
    exact = aggregate["changed_exact_agreement"]
    ordinary_thresholds = [
        value
        for key, value in sensitivity.items()
        if 0.50 <= float(key) <= 0.95
    ]
    precision_min = min(
        value["changed_open_behavior_precision"] for value in ordinary_thresholds
    )
    precision_max = max(
        value["changed_open_behavior_precision"] for value in ordinary_thresholds
    )
    return "\n".join(
        (
            "# Guard-Aware Counterfactual Audit",
            "",
            "## Result",
            "",
            "The current latent-gated candidate is not a reliable replacement for the",
            "deployed guarded baseline on fresh replay states.",
            "",
            "## Evaluation Aggregate",
            "",
            f"- Changed states: {aggregate['changed_row_count']}",
            f"- Raw-parent EndTurn share: {aggregate['changed_parent_end_turn_share']:.2%}",
            f"- Configured exact agreement with guarded action: {exact:.2%}",
            f"- Configured behavior-equivalent agreement: {behavior:.2%}",
            f"- Gate-open behavior precision: {aggregate['changed_open_behavior_precision']:.2%}",
            "- Gate-open behavior precision over thresholds 0.50-0.95: "
            f"{precision_min:.2%}-{precision_max:.2%}",
            "",
            "Duplicate card or potion slots are counted as equivalent only when item",
            "identity, target, and encoded card features agree. This avoids treating",
            "identical Strike copies as a policy difference.",
            "",
            "## Decision",
            "",
            "Do not tune the existing gate threshold or repeat its live gate. The next",
            "training recipe must estimate advantage over the deployed guarded action,",
            "rather than behavior-cloning that action and replacing the guard with an",
            "imperfect imitation.",
            "",
        )
    )


def run(candidate_report_path: Path, output_dir: Path) -> dict[str, Any]:
    candidate_report_path = candidate_report_path.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"audit output already exists: {output_dir}")
    report = json.loads(candidate_report_path.read_text(encoding="utf-8"))
    bindings = report["bindings"]
    artifact_path = candidate_report_path.parent / report["artifact"]["path"]
    if _sha256(artifact_path) != report["artifact"]["sha256"]:
        raise ValueError("candidate artifact hash differs")

    items_path = Path(bindings["items_json"]["path"])
    parent_path = Path(bindings["parent_checkpoint"]["path"])
    if sha256_file(items_path) != bindings["items_json"]["sha256"]:
        raise ValueError("audit item metadata hash differs")
    id_mapper = build_id_mapper(items_path)
    initial = load_initial_checkpoint(
        parent_path,
        expected_sha256=bindings["parent_checkpoint"]["sha256"],
    )
    recipe = report["recipe"]
    trainer = create_fresh_trainer(
        id_mapper,
        seed=int(recipe["classifier_seed"]),
        batch_size=int(recipe["batch_size"]),
        learning_starts=int(recipe["batch_size"]),
    )
    parent_state, _ = initialize_trainer(trainer, initial)
    if parameter_sha256(parent_state) != report["parent"]["parameter_sha256"]:
        raise ValueError("audit parent parameter identity differs")
    metadata = _trainer_metadata(trainer)
    artifact = torch.load(artifact_path, map_location="cpu", weights_only=True)
    adapter = load_development_artifact(
        trainer.online_network,
        metadata,
        artifact,
        expected_parent_checkpoint_sha256=bindings["parent_checkpoint"]["sha256"],
    )
    configured_threshold = float(adapter.config.gate_threshold)
    thresholds = (*DEFAULT_THRESHOLDS, configured_threshold)

    corpus_bindings = [
        ("development", bindings["development_replay"]),
        *[(value["id"], value) for value in bindings["evaluation_replays"]],
    ]
    corpora: dict[str, Any] = {}
    replay_reports: dict[str, Any] = {}
    for name, binding in corpus_bindings:
        path = Path(binding["path"])
        if sha256_file(path) != binding["sha256"]:
            raise ValueError(f"audit replay hash differs: {name}")
        corpus = _load_replay_corpus(
            path=path,
            expected_transition_count=int(binding["transition_count"]),
            parent=trainer.online_network,
            expected_parent_sha256=report["parent"]["parameter_sha256"],
        )
        if _adapter_metadata(trainer.online_network, corpus["metadata"]) != (
            _adapter_metadata(trainer.online_network, metadata)
        ):
            raise ValueError(f"audit replay metadata differs: {name}")
        corpora[name] = corpus
        replay_reports[name] = evaluate_replay(
            adapter, corpus["raw"], thresholds=thresholds
        )

    evaluation_corpora = [
        corpora[binding["id"]] for binding in bindings["evaluation_replays"]
    ]
    result = {
        "schema_version": SCHEMA_VERSION,
        "audit_id": AUDIT_ID,
        "source_commit": _current_commit(),
        "candidate_report": {
            "path": str(candidate_report_path),
            "sha256": _sha256(candidate_report_path),
        },
        "candidate_artifact": {
            "path": str(artifact_path),
            "sha256": report["artifact"]["sha256"],
        },
        "replays": replay_reports,
        "evaluation_aggregate": evaluate_replay(
            adapter, _concat_raw(evaluation_corpora), thresholds=thresholds
        ),
        "authority": {
            "read_only": True,
            "model_loading": True,
            "gameplay": False,
            "training": False,
            "qualification": False,
            "promotion": False,
        },
        "limitations": [
            "Agreement with the guarded action is not a counterfactual return estimate.",
            "The audit cannot establish that a differing candidate action is better.",
            "Threshold sensitivity is descriptive and grants no tuning authority.",
        ],
    }
    output_dir.mkdir(parents=True)
    (output_dir / "report.json").write_bytes(_canonical_json_bytes(result))
    (output_dir / "analysis.md").write_text(
        _render_analysis(result), encoding="ascii", newline="\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.candidate_report, args.output_dir)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
