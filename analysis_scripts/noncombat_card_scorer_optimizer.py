"""Exact scorer-only Adam slicing for card-policy optimizer ablations."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime


SCORER_PARAMETER_NAMES = (
    "family_head.scorer.weight",
    "family_head.scorer.bias",
    "conditional_ranker.scorer.weight",
    "conditional_ranker.scorer.bias",
)


class ScorerOptimizerBlocked(RuntimeError):
    """Raised when a full Adam cannot be reduced without changing its state."""


@dataclass(frozen=True)
class ScorerOptimizer:
    optimizer: torch.optim.Adam
    parameter_names: tuple[str, ...]
    parameters: tuple[torch.nn.Parameter, ...]


def candidate_hidden_parameter_bytes(bootstrap: runtime.PairedBootstrap) -> bytes:
    """Return canonical bytes for candidate hidden parameters only."""
    rows = runtime._arm_named_trainable_parameters(bootstrap, arm="candidate")
    value = {
        name: runtime._encode_tensor(parameter)
        for name, parameter in rows
        if ".hidden." in name
    }
    if len(value) != 4:
        raise ScorerOptimizerBlocked("candidate hidden parameter identity differs")
    try:
        return runtime._canonical_json_bytes(value)
    except runtime.SuccessorRuntimeError as exc:
        raise ScorerOptimizerBlocked(str(exc)) from exc


def candidate_guarded_model_bytes(bootstrap: runtime.PairedBootstrap) -> bytes:
    """Return canonical bytes for models outside the candidate card policy."""
    value = {
        "candidate_frozen_noncard": runtime._encode_model_state(
            bootstrap.candidate.frozen_noncard_ranker
        ),
        "control_frozen_noncard": runtime._encode_model_state(
            bootstrap.control.frozen_noncard_ranker
        ),
        "control_shared_card": runtime._encode_model_state(
            bootstrap.control.shared_card_ranker
        ),
    }
    try:
        return runtime._canonical_json_bytes(value)
    except runtime.SuccessorRuntimeError as exc:
        raise ScorerOptimizerBlocked(str(exc)) from exc


def build_scorer_optimizer(
    bootstrap: runtime.PairedBootstrap,
    full_optimizer: torch.optim.Optimizer,
) -> ScorerOptimizer:
    """Slice exact registered Adam moments for the four scorer parameters."""
    try:
        named = runtime._arm_named_trainable_parameters(bootstrap, arm="candidate")
        full_parameters = runtime._validated_registered_adam(full_optimizer)
    except runtime.SuccessorRuntimeError as exc:
        raise ScorerOptimizerBlocked(str(exc)) from exc
    expected_parameters = tuple(parameter for _, parameter in named)
    if len(full_parameters) != len(expected_parameters) or any(
        actual is not expected
        for actual, expected in zip(full_parameters, expected_parameters, strict=True)
    ):
        raise ScorerOptimizerBlocked("full Adam candidate parameter ownership differs")

    selected = tuple((name, parameter) for name, parameter in named if ".scorer." in name)
    names = tuple(name for name, _ in selected)
    if names != SCORER_PARAMETER_NAMES:
        raise ScorerOptimizerBlocked("scorer parameter names or order differ")
    parameters = tuple(parameter for _, parameter in selected)
    optimizer = torch.optim.Adam(parameters, **runtime._REGISTERED_ADAM_OPTIONS)

    source = full_optimizer.state_dict()
    target = optimizer.state_dict()
    source_group = source["param_groups"][0]
    target_group = target["param_groups"][0]
    if {
        key: value for key, value in source_group.items() if key != "params"
    } != {
        key: value for key, value in target_group.items() if key != "params"
    }:
        raise ScorerOptimizerBlocked("full and scorer Adam options differ")

    source_ids = tuple(source_group["params"])
    target_ids = tuple(target_group["params"])
    source_id_by_parameter = {
        id(parameter): state_id
        for parameter, state_id in zip(full_parameters, source_ids, strict=True)
    }
    if len(target_ids) != len(parameters):
        raise ScorerOptimizerBlocked("scorer Adam parameter identifiers differ")
    sliced_state: dict[Any, Any] = {}
    for parameter, target_id in zip(parameters, target_ids, strict=True):
        source_id = source_id_by_parameter[id(parameter)]
        if source_id not in source["state"]:
            raise ScorerOptimizerBlocked("full Adam scorer moment is missing")
        sliced_state[target_id] = copy.deepcopy(source["state"][source_id])
    target["state"] = sliced_state
    try:
        runtime._validate_decoded_adam_state(optimizer, target)
        optimizer.load_state_dict(target)
        runtime._validated_registered_adam(optimizer)
    except (KeyError, TypeError, ValueError, RuntimeError, runtime.SuccessorRuntimeError) as exc:
        raise ScorerOptimizerBlocked("scorer Adam state slice is incompatible") from exc

    restored = optimizer.state_dict()
    for parameter, target_id in zip(parameters, target_ids, strict=True):
        source_id = source_id_by_parameter[id(parameter)]
        source_entry = source["state"][source_id]
        target_entry = restored["state"][target_id]
        if set(source_entry) != set(target_entry) or any(
            not torch.equal(source_entry[key], target_entry[key])
            for key in source_entry
        ):
            raise ScorerOptimizerBlocked("scorer Adam moment bytes differ")
    return ScorerOptimizer(
        optimizer=optimizer,
        parameter_names=names,
        parameters=parameters,
    )


__all__ = [
    "SCORER_PARAMETER_NAMES",
    "ScorerOptimizer",
    "ScorerOptimizerBlocked",
    "build_scorer_optimizer",
    "candidate_guarded_model_bytes",
    "candidate_hidden_parameter_bytes",
]
