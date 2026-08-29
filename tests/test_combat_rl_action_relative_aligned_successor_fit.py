from __future__ import annotations

from pathlib import Path

import pytest

from analysis_scripts import combat_rl_action_relative_aligned_successor_fit as aligned
from analysis_scripts import combat_rl_action_relative_successor_delta_ablation as predecessor


def test_conditional_fit_stops_before_optimizer_when_support_fails() -> None:
    called = False

    def fit():
        nonlocal called
        called = True
        raise AssertionError("fit must not be called")

    result = aligned.run_if_supported(
        {"gate": {"passed": False, "decision": "corpus_support_insufficient_close_without_fit"}},
        fit,
    )

    assert called is False
    assert result == {
        "fit_executed": False,
        "fit_result": None,
        "decision": "aligned_support_insufficient_close_without_fit",
    }


def test_conditional_fit_executes_exactly_once_after_support_pass() -> None:
    calls = []

    result = aligned.run_if_supported(
        {"gate": {"passed": True, "decision": "corpus_support_ready_for_fit"}},
        lambda: calls.append("fit") or {"decision": "paired_fit_complete"},
    )

    assert calls == ["fit"]
    assert result["fit_executed"] is True
    assert result["fit_result"] == {"decision": "paired_fit_complete"}


def test_fit_registration_binds_target_corpora_recipe_and_offline_authority(
    tmp_path: Path,
) -> None:
    inputs = {}
    for name in aligned.INPUT_NAMES:
        path = tmp_path / name
        path.write_bytes(name.encode("ascii"))
        inputs[name] = aligned.file_binding(path)

    registration = aligned.build_fit_registration(
        "a" * 40,
        inputs=inputs,
    )
    validated = aligned.validate_fit_registration(registration)

    assert validated["inputs"] == inputs
    assert validated["recipe"] == predecessor.FIXED_ABLATION_RECIPE
    assert validated["offline_gates"] == predecessor.FIXED_OFFLINE_GATES
    assert validated["authority"]["model_fitting"] is True
    assert validated["authority"]["training"] is True
    assert validated["authority"]["gameplay"] is False
    assert validated["authority"]["candidate_action_takeover"] is False
    assert validated["authority"]["promotion"] is False

    registration["recipe"]["updates"] += 1
    with pytest.raises(ValueError, match="registration payload"):
        aligned.validate_fit_registration(registration)
