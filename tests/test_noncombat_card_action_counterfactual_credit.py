from __future__ import annotations

import pytest

from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    build_transition,
)


def _provenance() -> dict[str, object]:
    return {
        "adapter_commit": "adapter",
        "adapter_source_sha256": "adapter-source",
        "build": {
            "adapter_api_version": ADAPTER_API_VERSION,
            "compiler": "test",
            "cpp_standard": 201703,
            "python": "3.10",
        },
        "module_sha256": "module",
        "simulator_commit": "simulator",
        "simulator_source_sha256": "simulator-source",
        "submodules": {"json": "json", "pybind11": "pybind11"},
    }


def _candidate(category: str, action_id: str) -> dict[str, object]:
    return {
        "action_id": action_id,
        "available": True,
        "category": category,
        "kind": action_id.split(":")[-1],
        "label": action_id,
        "raw": {"action_id": action_id},
    }


class _CreditEnvironment:
    def __init__(
        self,
        seed: int,
        *,
        stage: int = 0,
        selected_card: str | None = None,
        shared: dict[str, object] | None = None,
        fail_native: bool = False,
    ) -> None:
        self.seed = seed
        self.stage = stage
        self.selected_card = selected_card
        self.shared = shared if shared is not None else {"native_calls": []}
        self.fail_native = fail_native

    def snapshot(self) -> dict[str, object]:
        terminal = self.stage == 2
        floors = {None: 0, "card:take-a": 1, "card:take-b": 3, "card:skip": 0}
        floor = floors[self.selected_card] if terminal else 0
        return {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_control": {
                "history": [],
                "policy_id": "test-native-simple-agent",
            },
            "category": None if terminal else ("card_reward" if self.stage == 0 else "route"),
            "decision_count": self.stage,
            "schema_version": STATE_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "state": {
                "floor": floor,
                "outcome": "player_loss" if terminal else "undecided",
                "seed": str(self.seed),
            },
            "terminal": terminal,
        }

    def legal_actions(self) -> list[dict[str, object]]:
        if self.stage == 0:
            return [
                _candidate("card_reward", "card:take-a"),
                _candidate("card_reward", "card:take-b"),
                _candidate("card_reward", "card:skip"),
            ]
        if self.stage == 1:
            return [_candidate("route", "route:continue")]
        return []

    def clone(self):
        return type(self)(
            self.seed,
            stage=self.stage,
            selected_card=self.selected_card,
            shared=self.shared,
            fail_native=self.fail_native,
        )

    def step(self, action_id: str) -> dict[str, object]:
        before = self.snapshot()
        candidates = self.legal_actions()
        if action_id not in {candidate["action_id"] for candidate in candidates}:
            raise RuntimeError("illegal action")
        if self.stage == 0:
            self.selected_card = action_id
            self.stage = 1
        else:
            self.stage = 2
        return build_transition(
            before=before,
            candidates=candidates,
            selected_action_id=action_id,
            after=self.snapshot(),
            provenance=_provenance(),
        )

    def step_native_baseline(self) -> dict[str, object]:
        if self.fail_native:
            raise RuntimeError("unsupported native transition")
        action_id = "card:take-a" if self.stage == 0 else "route:continue"
        self.shared["native_calls"].append((self.seed, self.stage, action_id))
        return self.step(action_id)


class _MutatingCloneEnvironment(_CreditEnvironment):
    def clone(self):
        clone = super().clone()
        self.stage += 1
        return clone


class _DriftingReplayEnvironment(_CreditEnvironment):
    def clone(self):
        clone = super().clone()
        clone.__class__ = _DriftingReplayEnvironment
        return clone

    def step(self, action_id: str) -> dict[str, object]:
        if self.stage == 0:
            counts = self.shared.setdefault("forced_counts", {})
            counts[action_id] = counts.get(action_id, 0) + 1
            if action_id == "card:take-a" and counts[action_id] > 1:
                self.selected_card = "card:take-b"
                before = self.snapshot()
                candidates = self.legal_actions()
                self.stage = 1
                return build_transition(
                    before=before,
                    candidates=candidates,
                    selected_action_id=action_id,
                    after=self.snapshot(),
                    provenance=_provenance(),
                )
        return super().step(action_id)


def test_source_evaluation_covers_all_actions_and_uses_native_continuation():
    environment = _CreditEnvironment(1000)

    source, replay = credit.evaluate_source_state(
        environment,
        seed=1000,
        decision_index=0,
        repeat_first_branch=True,
    )

    assert environment.stage == 0
    assert [row["action_id"] for row in source["actions"]] == [
        "card:take-a",
        "card:take-b",
        "card:skip",
    ]
    assert source["best_action_id"] == "card:take-b"
    assert source["informative_unique_best"] is True
    assert source["return_spread"] == pytest.approx(3.0 / 57.0)
    assert replay["passed"] is True
    assert len(environment.shared["native_calls"]) == 4


def test_branch_accumulates_formal_reward_and_exact_action_sequence():
    trace = credit.evaluate_action_branch(
        _CreditEnvironment(1000), action_id="card:take-b"
    )

    assert trace.action_sequence == ("card:take-b", "route:continue")
    assert trace.floor_progress == pytest.approx(3.0 / 57.0)
    assert trace.total_return == pytest.approx(3.0 / 57.0)
    assert trace.terminal_summary["outcome"] == "player_loss"


def test_source_mutation_and_unsupported_native_transition_fail_closed():
    with pytest.raises(credit.CounterfactualCreditBlocked, match="mutated"):
        credit.evaluate_source_state(
            _MutatingCloneEnvironment(1000),
            seed=1000,
            decision_index=0,
            repeat_first_branch=False,
        )

    with pytest.raises(credit.CounterfactualCreditBlocked, match="native continuation"):
        credit.evaluate_action_branch(
            _CreditEnvironment(1000, fail_native=True),
            action_id="card:take-a",
        )


def test_fixed_branch_replay_drift_is_reported_without_authority():
    source, replay = credit.evaluate_source_state(
        _DriftingReplayEnvironment(1000),
        seed=1000,
        decision_index=0,
        repeat_first_branch=True,
    )

    assert source["action_count"] == 3
    assert replay["passed"] is False


def test_poc_passes_only_fixed_complete_informative_and_deterministic_gates():
    report = credit.run_counterfactual_credit_poc(
        _CreditEnvironment,
        seeds=tuple(range(8)),
        max_card_states_per_seed=1,
        max_action_branches=25,
    )

    assert report["verdict"] == "card_action_counterfactual_credit_viable"
    assert report["summary"] == {
        "action_branch_continuations": 25,
        "budget_exhausted": False,
        "complete_source_states": 8,
        "determinism_passed": True,
        "informative_unique_best_states": 8,
        "root_native_transitions": 16,
        "terminal_seed_count": 8,
    }
    assert set(report["downstream_authority"].values()) == {False}


def test_branch_budget_stops_before_partial_source_state():
    report = credit.run_counterfactual_credit_poc(
        _CreditEnvironment,
        seeds=(1,),
        max_card_states_per_seed=1,
        max_action_branches=3,
        min_complete_source_states=1,
        min_informative_source_states=1,
    )

    assert report["summary"]["action_branch_continuations"] == 0
    assert report["summary"]["complete_source_states"] == 0
    assert report["summary"]["budget_exhausted"] is True
    assert report["verdict"] == "card_action_counterfactual_credit_not_ready"


def test_complete_sources_can_pass_when_next_whole_source_exceeds_budget():
    report = credit.run_counterfactual_credit_poc(
        _CreditEnvironment,
        seeds=tuple(range(8)),
        max_card_states_per_seed=1,
        max_action_branches=13,
        min_complete_source_states=4,
        min_informative_source_states=4,
    )

    assert report["summary"]["action_branch_continuations"] == 13
    assert report["summary"]["complete_source_states"] == 4
    assert report["summary"]["budget_exhausted"] is True
    assert report["verdict"] == "card_action_counterfactual_credit_viable"
