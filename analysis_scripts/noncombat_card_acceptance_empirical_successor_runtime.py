"""Torch runtime primitives for the card-acceptance empirical successor."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import math
from numbers import Integral, Real
from typing import Any, Literal

import torch

from analysis_scripts.noncombat_card_acceptance_objective import (
    CardAcceptancePolicyTerms,
)
from analysis_scripts.noncombat_card_acceptance_policy import (
    CardAcceptancePolicy,
    CardAcceptancePolicyOutput,
    build_family_features,
)
from analysis_scripts.noncombat_state_conditioned_policy_input import HASH_DIM
from analysis_scripts.noncombat_state_conditioned_ranker import (
    DEFAULT_HIDDEN_DIM,
    StateConditionedCandidateRanker,
)


BOOTSTRAP_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-bootstrap-v1"
)
RUNTIME_METADATA_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-runtime-metadata-v1"
)
MODEL_SEED = 0
CARD_GENERATOR_SEED = 0
NONCARD_GENERATOR_SEED = 1
ENTROPY_COEFFICIENT = 0.01
LEARNING_RATE = 0.001
MAX_BOOTSTRAP_BYTES = 64 * 1024 * 1024
GRADIENT_RECONSTRUCTION_RTOL = 1e-6
GRADIENT_RECONSTRUCTION_ATOL = 1e-7
ArmName = Literal["candidate", "control"]

_REGISTERED_ADAM_OPTIONS: dict[str, Any] = {
    "amsgrad": False,
    "betas": (0.9, 0.999),
    "capturable": False,
    "differentiable": False,
    "eps": 1e-8,
    "foreach": False,
    "fused": False,
    "lr": LEARNING_RATE,
    "maximize": False,
    "weight_decay": 0.0,
}


class SuccessorRuntimeError(ValueError):
    """Raised when the empirical-successor runtime contract is invalid."""


@dataclass(frozen=True)
class CandidateArm:
    card_policy: CardAcceptancePolicy
    frozen_noncard_ranker: StateConditionedCandidateRanker


@dataclass(frozen=True)
class ControlArm:
    shared_card_ranker: StateConditionedCandidateRanker
    frozen_noncard_ranker: StateConditionedCandidateRanker


@dataclass(frozen=True)
class PairedBootstrap:
    candidate: CandidateArm
    control: ControlArm
    generators: dict[str, torch.Generator]


@dataclass(frozen=True)
class ArmOptimizers:
    candidate: torch.optim.Adam
    control: torch.optim.Adam


@dataclass(frozen=True)
class ArmCardRewardObjective:
    card_decision_count: int
    family_policy_loss: torch.Tensor
    conditional_policy_loss: torch.Tensor
    family_entropy_loss: torch.Tensor
    conditional_entropy_loss: torch.Tensor
    total_loss: torch.Tensor


@dataclass(frozen=True)
class ArmOptimizerStepEvidence:
    component_order: tuple[str, ...]
    component_gradients: tuple[tuple[torch.Tensor | None, ...], ...]
    combined_gradients: tuple[torch.Tensor, ...]
    applied_gradients: tuple[torch.Tensor, ...]
    preclip_global_norm: float
    postclip_global_norm: float
    optimizer_state_before: dict[str, Any]
    optimizer_state_after: dict[str, Any]


_DTYPES: dict[str, torch.dtype] = {
    "bool": torch.bool,
    "float32": torch.float32,
    "float64": torch.float64,
    "int32": torch.int32,
    "int64": torch.int64,
    "uint8": torch.uint8,
}


def runtime_metadata() -> dict[str, Any]:
    """Return fresh runtime-owned metadata matching the source-only contract."""
    return {
        "algorithm": {
            "conditional_entropy_coefficient": ENTROPY_COEFFICIENT,
            "discount": 1.0,
            "family_entropy_coefficient": ENTROPY_COEFFICIENT,
            "gradient_norm_ceiling": 1.0,
            "learning_rate": LEARNING_RATE,
            "model_seed": MODEL_SEED,
            "optimizer": "adam",
            "optimizer_amsgrad": False,
            "optimizer_betas": [0.9, 0.999],
            "optimizer_eps": 1e-8,
            "optimizer_weight_decay": 0.0,
        },
        "architecture": {
            "candidate": "disjoint-family-and-conditional-heads",
            "control": "shared-card-ranker",
            "frozen_noncard_rankers": 2,
            "matched_rankers": 5,
        },
        "authority": {
            name: False
            for name in (
                "causal",
                "communication_mod",
                "environment_construction",
                "evaluation",
                "execution",
                "formal_rl",
                "gameplay",
                "model_fitting",
                "native_loading",
                "ope",
                "production_model_loading",
                "promotion",
                "qualification",
                "seed_access",
                "training",
            )
        },
        "device": "cpu",
        "dtype": "float32",
        "environment": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "ascension": 0,
            "device": "cpu",
        },
        "optimizer": {
            "amsgrad": False,
            "betas": [0.9, 0.999],
            "eps": 1e-8,
            "learning_rate": LEARNING_RATE,
            "name": "adam",
            "weight_decay": 0.0,
        },
        "schema_version": RUNTIME_METADATA_SCHEMA_VERSION,
    }


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SuccessorRuntimeError(f"duplicate checkpoint field: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise SuccessorRuntimeError(f"checkpoint constant is invalid: {value}")


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise SuccessorRuntimeError("checkpoint is not canonical JSON") from exc


def _rankers(bootstrap: PairedBootstrap) -> tuple[StateConditionedCandidateRanker, ...]:
    return (
        bootstrap.candidate.card_policy.family_head,
        bootstrap.candidate.card_policy.conditional_ranker,
        bootstrap.candidate.frozen_noncard_ranker,
        bootstrap.control.shared_card_ranker,
        bootstrap.control.frozen_noncard_ranker,
    )


def _new_ranker() -> StateConditionedCandidateRanker:
    return StateConditionedCandidateRanker(HASH_DIM, DEFAULT_HIDDEN_DIM)


def _new_generator(seed: int) -> torch.Generator:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    return generator


def build_matched_bootstrap() -> PairedBootstrap:
    """Build five storage-disjoint rankers copied from one seed-zero base."""
    ambient_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float32)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(MODEL_SEED)
            base = _new_ranker()
            base_state = {
                name: value.detach().clone()
                for name, value in base.state_dict().items()
            }
            bootstrap = PairedBootstrap(
                candidate=CandidateArm(
                    card_policy=CardAcceptancePolicy(HASH_DIM, DEFAULT_HIDDEN_DIM),
                    frozen_noncard_ranker=_new_ranker(),
                ),
                control=ControlArm(
                    shared_card_ranker=_new_ranker(),
                    frozen_noncard_ranker=_new_ranker(),
                ),
                generators={
                    "candidate_card": _new_generator(CARD_GENERATOR_SEED),
                    "candidate_noncard": _new_generator(NONCARD_GENERATOR_SEED),
                    "control_card": _new_generator(CARD_GENERATOR_SEED),
                    "control_noncard": _new_generator(NONCARD_GENERATOR_SEED),
                },
            )
    finally:
        torch.set_default_dtype(ambient_dtype)

    for ranker in _rankers(bootstrap):
        ranker.load_state_dict(base_state, strict=True)
    for ranker in (
        bootstrap.candidate.frozen_noncard_ranker,
        bootstrap.control.frozen_noncard_ranker,
    ):
        ranker.requires_grad_(False)
        ranker.eval()
    return bootstrap


def _encode_tensor(value: torch.Tensor) -> dict[str, Any]:
    if not isinstance(value, torch.Tensor):
        raise SuccessorRuntimeError("tensor encoding requires a tensor")
    tensor = value.detach().cpu().contiguous()
    dtype_name = str(tensor.dtype).removeprefix("torch.")
    if dtype_name not in _DTYPES:
        raise SuccessorRuntimeError(f"unsupported tensor dtype: {dtype_name}")
    if tensor.is_floating_point() and not torch.isfinite(tensor).all().item():
        raise SuccessorRuntimeError("checkpoint tensors must be finite")
    return {
        "dtype": dtype_name,
        "shape": list(tensor.shape),
        "values": tensor.reshape(-1).tolist(),
    }


def _decode_tensor(value: object, label: str) -> torch.Tensor:
    if not isinstance(value, Mapping) or set(value) != {"dtype", "shape", "values"}:
        raise SuccessorRuntimeError(f"{label} tensor fields differ")
    dtype_name = value["dtype"]
    if not isinstance(dtype_name, str) or dtype_name not in _DTYPES:
        raise SuccessorRuntimeError(f"{label} tensor dtype is unsupported")
    raw_shape = value["shape"]
    if isinstance(raw_shape, (str, bytes)) or not isinstance(raw_shape, Sequence):
        raise SuccessorRuntimeError(f"{label} tensor shape is invalid")
    shape: list[int] = []
    for index, dimension in enumerate(raw_shape):
        if (
            isinstance(dimension, bool)
            or not isinstance(dimension, Integral)
            or int(dimension) < 0
        ):
            raise SuccessorRuntimeError(
                f"{label} tensor shape[{index}] is invalid"
            )
        shape.append(int(dimension))
    raw_values = value["values"]
    if isinstance(raw_values, (str, bytes)) or not isinstance(raw_values, Sequence):
        raise SuccessorRuntimeError(f"{label} tensor values are invalid")
    expected_count = math.prod(shape) if shape else 1
    if len(raw_values) != expected_count:
        raise SuccessorRuntimeError(f"{label} tensor value count differs")
    try:
        tensor = torch.tensor(
            list(raw_values), dtype=_DTYPES[dtype_name], device="cpu"
        ).reshape(tuple(shape))
    except (TypeError, ValueError, RuntimeError) as exc:
        raise SuccessorRuntimeError(f"{label} tensor decode failed") from exc
    if tensor.is_floating_point() and not torch.isfinite(tensor).all().item():
        raise SuccessorRuntimeError(f"{label} tensor must be finite")
    return tensor


def _encode_model_state(model: torch.nn.Module) -> dict[str, Any]:
    return {
        name: _encode_tensor(tensor)
        for name, tensor in sorted(model.state_dict().items())
    }


def _restore_model_state(
    model: torch.nn.Module, value: object, label: str
) -> None:
    if not isinstance(value, Mapping):
        raise SuccessorRuntimeError(f"{label} must be a mapping")
    expected = tuple(sorted(model.state_dict()))
    if tuple(sorted(value)) != expected:
        raise SuccessorRuntimeError(f"{label} state keys differ")
    expected_state = model.state_dict()
    state: dict[str, torch.Tensor] = {}
    for name in expected:
        tensor = _decode_tensor(value[name], f"{label}.{name}")
        registered = expected_state[name]
        if tensor.dtype != registered.dtype:
            raise SuccessorRuntimeError(
                f"{label}.{name} dtype must equal {registered.dtype}"
            )
        if tensor.shape != registered.shape:
            raise SuccessorRuntimeError(f"{label}.{name} shape differs")
        if tensor.device != registered.device:
            raise SuccessorRuntimeError(f"{label}.{name} device differs")
        state[name] = tensor
    try:
        model.load_state_dict(state, strict=True)
    except RuntimeError as exc:
        raise SuccessorRuntimeError(f"{label} state is incompatible") from exc


def _paired_bootstrap_object(bootstrap: PairedBootstrap) -> dict[str, Any]:
    """Build the canonical plain-object representation of paired state."""
    if not isinstance(bootstrap, PairedBootstrap):
        raise SuccessorRuntimeError("paired bootstrap has an invalid type")
    expected_generators = (
        "candidate_card",
        "candidate_noncard",
        "control_card",
        "control_noncard",
    )
    if tuple(bootstrap.generators) != expected_generators:
        raise SuccessorRuntimeError("paired bootstrap generators differ")
    return {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "architecture": {
            "hidden_dim": DEFAULT_HIDDEN_DIM,
            "input_dim": HASH_DIM,
            "model_seed": MODEL_SEED,
        },
        "models": {
            "candidate": {
                "conditional_ranker": _encode_model_state(
                    bootstrap.candidate.card_policy.conditional_ranker
                ),
                "family_head": _encode_model_state(
                    bootstrap.candidate.card_policy.family_head
                ),
                "frozen_noncard_ranker": _encode_model_state(
                    bootstrap.candidate.frozen_noncard_ranker
                ),
            },
            "control": {
                "frozen_noncard_ranker": _encode_model_state(
                    bootstrap.control.frozen_noncard_ranker
                ),
                "shared_card_ranker": _encode_model_state(
                    bootstrap.control.shared_card_ranker
                ),
            },
        },
        "generators": {
            name: _encode_tensor(bootstrap.generators[name].get_state())
            for name in expected_generators
        },
    }


def encode_paired_bootstrap(bootstrap: PairedBootstrap) -> bytes:
    """Encode all model and generator state as bounded canonical bytes."""
    payload = _canonical_json_bytes(_paired_bootstrap_object(bootstrap))
    if len(payload) > MAX_BOOTSTRAP_BYTES:
        raise SuccessorRuntimeError("paired bootstrap exceeds its byte ceiling")
    return payload


def restore_paired_bootstrap(value: object) -> PairedBootstrap:
    """Restore the exact inverse of :func:`encode_paired_bootstrap`."""
    if not isinstance(value, bytes) or not value or len(value) > MAX_BOOTSTRAP_BYTES:
        raise SuccessorRuntimeError("paired bootstrap bytes are invalid")
    try:
        decoded_text = value.decode("ascii")
        parsed = json.loads(
            decoded_text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SuccessorRuntimeError("paired bootstrap JSON is invalid") from exc
    if _canonical_json_bytes(parsed) != value:
        raise SuccessorRuntimeError("paired bootstrap bytes are not canonical")
    if not isinstance(parsed, Mapping) or set(parsed) != {
        "schema_version",
        "architecture",
        "models",
        "generators",
    }:
        raise SuccessorRuntimeError("paired bootstrap fields differ")
    value = parsed
    if value["schema_version"] != BOOTSTRAP_SCHEMA_VERSION:
        raise SuccessorRuntimeError("paired bootstrap schema differs")
    if value["architecture"] != {
        "hidden_dim": DEFAULT_HIDDEN_DIM,
        "input_dim": HASH_DIM,
        "model_seed": MODEL_SEED,
    }:
        raise SuccessorRuntimeError("paired bootstrap architecture differs")
    models = value["models"]
    generators = value["generators"]
    if not isinstance(models, Mapping) or set(models) != {"candidate", "control"}:
        raise SuccessorRuntimeError("paired bootstrap model fields differ")
    candidate_models = models["candidate"]
    control_models = models["control"]
    if not isinstance(candidate_models, Mapping) or set(candidate_models) != {
        "conditional_ranker",
        "family_head",
        "frozen_noncard_ranker",
    }:
        raise SuccessorRuntimeError("candidate model fields differ")
    if not isinstance(control_models, Mapping) or set(control_models) != {
        "frozen_noncard_ranker",
        "shared_card_ranker",
    }:
        raise SuccessorRuntimeError("control model fields differ")
    expected_generators = {
        "candidate_card",
        "candidate_noncard",
        "control_card",
        "control_noncard",
    }
    if not isinstance(generators, Mapping) or set(generators) != expected_generators:
        raise SuccessorRuntimeError("paired bootstrap generator fields differ")

    bootstrap = build_matched_bootstrap()
    _restore_model_state(
        bootstrap.candidate.card_policy.family_head,
        candidate_models["family_head"],
        "candidate.family_head",
    )
    _restore_model_state(
        bootstrap.candidate.card_policy.conditional_ranker,
        candidate_models["conditional_ranker"],
        "candidate.conditional_ranker",
    )
    _restore_model_state(
        bootstrap.candidate.frozen_noncard_ranker,
        candidate_models["frozen_noncard_ranker"],
        "candidate.frozen_noncard_ranker",
    )
    _restore_model_state(
        bootstrap.control.shared_card_ranker,
        control_models["shared_card_ranker"],
        "control.shared_card_ranker",
    )
    _restore_model_state(
        bootstrap.control.frozen_noncard_ranker,
        control_models["frozen_noncard_ranker"],
        "control.frozen_noncard_ranker",
    )
    for name in bootstrap.generators:
        state = _decode_tensor(generators[name], f"generators.{name}")
        if state.dtype != torch.uint8 or state.ndim != 1:
            raise SuccessorRuntimeError(f"generator {name} state is invalid")
        try:
            bootstrap.generators[name].set_state(state)
        except RuntimeError as exc:
            raise SuccessorRuntimeError(f"generator {name} state is invalid") from exc
    return bootstrap


def _validated_arm(value: object) -> ArmName:
    if value not in {"candidate", "control"}:
        raise SuccessorRuntimeError("arm must equal candidate or control")
    return value  # type: ignore[return-value]


def _control_card_output(
    ranker: StateConditionedCandidateRanker,
    state_features: torch.Tensor,
    candidate_features: torch.Tensor,
    candidates: Sequence[Mapping[str, Any]],
) -> CardAcceptancePolicyOutput:
    family_batch = build_family_features(
        candidate_features, candidates, category="card_reward"
    )
    conditional_logits = ranker(state_features, candidate_features)
    family_logits = ranker(state_features, family_batch.family_features)
    if family_batch.family_order == ("take",):
        acceptance_active = False
        acceptance_coordinate = None
    else:
        take_index = family_batch.family_order.index("take")
        non_take_indices = torch.tensor(
            [
                index
                for index in range(len(family_batch.family_order))
                if index != take_index
            ],
            dtype=torch.long,
            device="cpu",
        )
        logits64 = family_logits.to(dtype=torch.float64)
        acceptance_active = True
        acceptance_coordinate = logits64[take_index] - torch.logsumexp(
            logits64.index_select(0, non_take_indices), dim=0
        )
    return CardAcceptancePolicyOutput(
        family_batch=family_batch,
        conditional_logits=conditional_logits,
        family_logits=family_logits,
        acceptance_active=acceptance_active,
        acceptance_coordinate=acceptance_coordinate,
    )


def forward_card_policy(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    state_features: torch.Tensor,
    candidate_features: torch.Tensor,
    candidates: Sequence[Mapping[str, Any]],
) -> CardAcceptancePolicyOutput:
    """Route card rewards through candidate dual heads or the control shared head."""
    normalized_arm = _validated_arm(arm)
    if normalized_arm == "candidate":
        return bootstrap.candidate.card_policy(
            state_features,
            candidate_features,
            candidates,
            category="card_reward",
        )
    return _control_card_output(
        bootstrap.control.shared_card_ranker,
        state_features,
        candidate_features,
        candidates,
    )


def build_arm_card_reward_objective(
    rows: Sequence[tuple[CardAcceptancePolicyTerms, Real]],
) -> ArmCardRewardObjective:
    """Build the registered four-component, decision-mean card objective."""
    normalized_rows = tuple(rows)
    if not normalized_rows:
        raise SuccessorRuntimeError("card reward objective requires decisions")
    for index, (terms, advantage) in enumerate(normalized_rows):
        if not isinstance(terms, CardAcceptancePolicyTerms):
            raise SuccessorRuntimeError(f"row {index} policy terms are invalid")
        if (
            isinstance(advantage, bool)
            or not isinstance(advantage, Real)
            or not math.isfinite(float(advantage))
        ):
            raise SuccessorRuntimeError(f"row {index} advantage must be finite")

    family_policy_loss = torch.stack(
        [
            -advantage * terms.selected_family_log_probability
            for terms, advantage in normalized_rows
        ]
    ).mean()
    conditional_policy_loss = torch.stack(
        [
            -advantage * terms.selected_conditional_log_probability
            for terms, advantage in normalized_rows
        ]
    ).mean()
    family_entropy_loss = -ENTROPY_COEFFICIENT * torch.stack(
        [terms.family_entropy for terms, _ in normalized_rows]
    ).mean()
    conditional_entropy_loss = -ENTROPY_COEFFICIENT * torch.stack(
        [
            terms.per_family_conditional_entropies.mean()
            for terms, _ in normalized_rows
        ]
    ).mean()
    total_loss = (
        family_policy_loss
        + conditional_policy_loss
        + family_entropy_loss
        + conditional_entropy_loss
    )
    return ArmCardRewardObjective(
        card_decision_count=len(normalized_rows),
        family_policy_loss=family_policy_loss,
        conditional_policy_loss=conditional_policy_loss,
        family_entropy_loss=family_entropy_loss,
        conditional_entropy_loss=conditional_entropy_loss,
        total_loss=total_loss,
    )


def build_arm_optimizers(bootstrap: PairedBootstrap) -> ArmOptimizers:
    """Build one fixed Adam group for each arm's trainable card parameters."""
    candidate_parameters = tuple(
        bootstrap.candidate.card_policy.family_head.parameters()
    ) + tuple(bootstrap.candidate.card_policy.conditional_ranker.parameters())
    control_parameters = tuple(bootstrap.control.shared_card_ranker.parameters())
    return ArmOptimizers(
        candidate=torch.optim.Adam(candidate_parameters, **_REGISTERED_ADAM_OPTIONS),
        control=torch.optim.Adam(control_parameters, **_REGISTERED_ADAM_OPTIONS),
    )


def _validated_registered_adam(
    optimizer: torch.optim.Optimizer,
) -> tuple[torch.nn.Parameter, ...]:
    if type(optimizer) is not torch.optim.Adam:
        raise SuccessorRuntimeError("optimizer must be the registered Adam type")
    if len(optimizer.param_groups) != 1:
        raise SuccessorRuntimeError("registered Adam must have one parameter group")
    group = optimizer.param_groups[0]
    for key, expected in _REGISTERED_ADAM_OPTIONS.items():
        if group.get(key) != expected or optimizer.defaults.get(key) != expected:
            raise SuccessorRuntimeError(f"registered Adam option {key} differs")
    parameters = tuple(group.get("params", ()))
    if not parameters or any(
        not isinstance(parameter, torch.nn.Parameter) for parameter in parameters
    ):
        raise SuccessorRuntimeError("registered Adam parameters are invalid")
    if len({id(parameter) for parameter in parameters}) != len(parameters):
        raise SuccessorRuntimeError("registered Adam parameter order is not unique")
    for parameter in parameters:
        if parameter.device.type != "cpu" or parameter.dtype != torch.float32:
            raise SuccessorRuntimeError(
                "registered Adam parameters must remain CPU float32"
            )
        if not parameter.requires_grad:
            raise SuccessorRuntimeError(
                "registered Adam cannot own a frozen parameter"
            )
    return parameters


def _encode_state_value(value: Any) -> dict[str, Any]:
    if isinstance(value, torch.Tensor):
        return {"type": "tensor", "value": _encode_tensor(value)}
    if isinstance(value, tuple):
        return {
            "type": "tuple",
            "items": [_encode_state_value(item) for item in value],
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "items": [_encode_state_value(item) for item in value],
        }
    if isinstance(value, Mapping):
        items = [
            {"key": _encode_state_value(key), "value": _encode_state_value(item)}
            for key, item in value.items()
        ]
        items.sort(
            key=lambda item: json.dumps(
                item["key"],
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return {"type": "mapping", "items": items}
    if value is None or isinstance(value, (bool, int, str)):
        return {"type": "scalar", "value": value}
    if isinstance(value, Real):
        converted = float(value)
        if not math.isfinite(converted):
            raise SuccessorRuntimeError("optimizer scalar must be finite")
        return {"type": "scalar", "value": converted}
    raise SuccessorRuntimeError(
        f"unsupported optimizer state type: {type(value).__name__}"
    )


def _decode_state_value(value: object, label: str) -> Any:
    if not isinstance(value, Mapping):
        raise SuccessorRuntimeError(f"{label} must be a mapping")
    state_type = value.get("type")
    if state_type == "tensor" and set(value) == {"type", "value"}:
        return _decode_tensor(value["value"], f"{label}.value")
    if state_type in {"tuple", "list"} and set(value) == {"type", "items"}:
        items = value["items"]
        if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
            raise SuccessorRuntimeError(f"{label}.items must be a sequence")
        decoded = [
            _decode_state_value(item, f"{label}.items[{index}]")
            for index, item in enumerate(items)
        ]
        return tuple(decoded) if state_type == "tuple" else decoded
    if state_type == "mapping" and set(value) == {"type", "items"}:
        items = value["items"]
        if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
            raise SuccessorRuntimeError(f"{label}.items must be a sequence")
        decoded_mapping: dict[Any, Any] = {}
        for index, item in enumerate(items):
            item_label = f"{label}.items[{index}]"
            if not isinstance(item, Mapping) or set(item) != {"key", "value"}:
                raise SuccessorRuntimeError(f"{item_label} fields differ")
            key = _decode_state_value(item["key"], f"{item_label}.key")
            if key in decoded_mapping:
                raise SuccessorRuntimeError(f"{label} contains a duplicate key")
            decoded_mapping[key] = _decode_state_value(
                item["value"], f"{item_label}.value"
            )
        return decoded_mapping
    if state_type == "scalar" and set(value) == {"type", "value"}:
        scalar = value["value"]
        if scalar is not None and not isinstance(scalar, (bool, int, float, str)):
            raise SuccessorRuntimeError(f"{label} scalar is invalid")
        if isinstance(scalar, float) and not math.isfinite(scalar):
            raise SuccessorRuntimeError(f"{label} scalar must be finite")
        return scalar
    raise SuccessorRuntimeError(f"{label} state fields differ")


def encode_optimizer_state(optimizer: torch.optim.Optimizer) -> dict[str, Any]:
    """Encode Adam state without pickle while preserving tuple and key types."""
    _validated_registered_adam(optimizer)
    return _encode_state_value(optimizer.state_dict())


def _validate_decoded_adam_state(
    optimizer: torch.optim.Adam,
    decoded: dict[str, Any],
) -> None:
    expected = optimizer.state_dict()
    if decoded["param_groups"] != expected["param_groups"]:
        raise SuccessorRuntimeError(
            "optimizer parameter order or registered option differs"
        )
    state = decoded["state"]
    if not isinstance(state, dict):
        raise SuccessorRuntimeError("optimizer state entries must be a mapping")

    parameters = _validated_registered_adam(optimizer)
    parameter_indexes = tuple(expected["param_groups"][0]["params"])
    if len(parameter_indexes) != len(parameters):
        raise SuccessorRuntimeError("optimizer parameter order differs")
    parameter_by_index = dict(zip(parameter_indexes, parameters, strict=True))
    if any(
        isinstance(index, bool)
        or not isinstance(index, int)
        or index not in parameter_by_index
        for index in state
    ):
        raise SuccessorRuntimeError("optimizer state parameter index differs")

    expected_state_keys = {"step", "exp_avg", "exp_avg_sq"}
    for index, entry in state.items():
        if not isinstance(entry, dict) or set(entry) != expected_state_keys:
            raise SuccessorRuntimeError("optimizer Adam moment fields differ")
        parameter = parameter_by_index[index]
        step = entry["step"]
        if (
            not isinstance(step, torch.Tensor)
            or step.device.type != "cpu"
            or step.dtype != torch.float32
            or step.shape != torch.Size([])
            or not bool(torch.isfinite(step).item())
        ):
            raise SuccessorRuntimeError("optimizer Adam step tensor differs")
        for name in ("exp_avg", "exp_avg_sq"):
            moment = entry[name]
            if (
                not isinstance(moment, torch.Tensor)
                or moment.device != parameter.device
                or moment.dtype != parameter.dtype
                or moment.shape != parameter.shape
                or not bool(torch.isfinite(moment).all().item())
            ):
                raise SuccessorRuntimeError(
                    f"optimizer Adam {name} tensor differs"
                )


def restore_optimizer_state(
    optimizer: torch.optim.Optimizer, value: object
) -> torch.optim.Optimizer:
    """Restore optimizer moments encoded by :func:`encode_optimizer_state`."""
    _validated_registered_adam(optimizer)
    decoded = _decode_state_value(value, "optimizer state")
    if not isinstance(decoded, dict) or set(decoded) != {"param_groups", "state"}:
        raise SuccessorRuntimeError("optimizer state keys differ")
    _validate_decoded_adam_state(optimizer, decoded)
    try:
        optimizer.load_state_dict(decoded)
    except (TypeError, ValueError, RuntimeError) as exc:
        raise SuccessorRuntimeError("optimizer state is incompatible") from exc
    _validated_registered_adam(optimizer)
    return optimizer


def _global_gradient_norm(gradients: Sequence[torch.Tensor]) -> float:
    if not gradients:
        raise SuccessorRuntimeError("optimizer step requires gradients")
    norm = torch.linalg.vector_norm(
        torch.stack(
            [torch.linalg.vector_norm(gradient.detach(), 2) for gradient in gradients]
        ),
        2,
    )
    if not bool(torch.isfinite(norm).item()):
        raise SuccessorRuntimeError("optimizer gradient norm must be finite")
    return float(norm.item())


def apply_arm_optimizer_step(
    optimizer: torch.optim.Optimizer,
    objective: ArmCardRewardObjective,
    *,
    parameters: Sequence[torch.nn.Parameter],
) -> ArmOptimizerStepEvidence:
    """Validate, reconstruct, globally clip, and apply one registered arm step."""
    registered_parameters = _validated_registered_adam(optimizer)
    supplied_parameters = tuple(parameters)
    if len(supplied_parameters) != len(registered_parameters) or any(
        supplied is not registered
        for supplied, registered in zip(
            supplied_parameters, registered_parameters, strict=True
        )
    ):
        raise SuccessorRuntimeError("optimizer parameter order differs")
    if not isinstance(objective, ArmCardRewardObjective):
        raise SuccessorRuntimeError("optimizer objective type differs")
    if objective.card_decision_count <= 0:
        raise SuccessorRuntimeError("optimizer objective has no card decisions")

    component_order = (
        "family_policy",
        "conditional_policy",
        "family_entropy",
        "conditional_entropy",
    )
    components = (
        objective.family_policy_loss,
        objective.conditional_policy_loss,
        objective.family_entropy_loss,
        objective.conditional_entropy_loss,
    )
    losses = components + (objective.total_loss,)
    for loss in losses:
        if (
            not isinstance(loss, torch.Tensor)
            or loss.device.type != "cpu"
            or not loss.is_floating_point()
            or loss.shape != torch.Size([])
            or not bool(torch.isfinite(loss).item())
        ):
            raise SuccessorRuntimeError(
                "optimizer objective scalars must be finite CPU floating point"
            )
    reconstructed_loss = components[0]
    for component in components[1:]:
        reconstructed_loss = reconstructed_loss + component
    if not torch.equal(reconstructed_loss, objective.total_loss):
        raise SuccessorRuntimeError("optimizer objective reconstruction differs")

    raw_component_gradients = tuple(
        torch.autograd.grad(
            component,
            registered_parameters,
            allow_unused=True,
            retain_graph=True,
        )
        for component in components
    )
    total_gradients = torch.autograd.grad(
        objective.total_loss,
        registered_parameters,
        allow_unused=True,
    )
    component_gradients = tuple(
        tuple(
            None
            if gradient is None
            else gradient.detach().to(dtype=torch.float64).clone()
            for gradient in gradients
        )
        for gradients in raw_component_gradients
    )
    combined_gradients: list[torch.Tensor] = []
    for parameter_index, parameter in enumerate(registered_parameters):
        combined = torch.zeros_like(parameter, dtype=torch.float64)
        for raw_gradients, evidence_gradients in zip(
            raw_component_gradients, component_gradients, strict=True
        ):
            gradient = raw_gradients[parameter_index]
            if gradient is not None:
                if (
                    gradient.device != parameter.device
                    or gradient.dtype != parameter.dtype
                    or gradient.shape != parameter.shape
                    or not bool(torch.isfinite(gradient).all().item())
                ):
                    raise SuccessorRuntimeError(
                        "optimizer component gradient contract differs"
                    )
                evidence_gradient = evidence_gradients[parameter_index]
                if evidence_gradient is None:
                    raise SuccessorRuntimeError(
                        "optimizer component gradient evidence differs"
                    )
                combined = combined + evidence_gradient
        total = total_gradients[parameter_index]
        if total is None or not torch.allclose(
            combined,
            total.detach().to(dtype=torch.float64),
            rtol=GRADIENT_RECONSTRUCTION_RTOL,
            atol=GRADIENT_RECONSTRUCTION_ATOL,
        ):
            raise SuccessorRuntimeError(
                "optimizer total gradient reconstruction differs"
            )
        combined_gradients.append(combined.detach().clone())

    optimizer_state_before = encode_optimizer_state(optimizer)
    optimizer.zero_grad(set_to_none=True)
    for parameter, gradient in zip(
        registered_parameters, combined_gradients, strict=True
    ):
        parameter.grad = gradient.to(dtype=parameter.dtype).clone()
    preclip_global_norm = float(
        torch.nn.utils.clip_grad_norm_(registered_parameters, 1.0).item()
    )
    if not math.isfinite(preclip_global_norm):
        raise SuccessorRuntimeError("optimizer preclip gradient norm must be finite")
    applied_gradients = tuple(
        parameter.grad.detach().clone()
        for parameter in registered_parameters
        if parameter.grad is not None
    )
    if len(applied_gradients) != len(registered_parameters):
        raise SuccessorRuntimeError("optimizer clipped gradient coverage differs")
    postclip_global_norm = _global_gradient_norm(applied_gradients)
    if postclip_global_norm > 1.0 + 1e-6:
        raise SuccessorRuntimeError("optimizer gradient clipping ceiling exceeded")
    optimizer.step()
    optimizer_state_after = encode_optimizer_state(optimizer)

    return ArmOptimizerStepEvidence(
        component_order=component_order,
        component_gradients=component_gradients,
        combined_gradients=tuple(combined_gradients),
        applied_gradients=applied_gradients,
        preclip_global_norm=preclip_global_norm,
        postclip_global_norm=postclip_global_norm,
        optimizer_state_before=optimizer_state_before,
        optimizer_state_after=optimizer_state_after,
    )


def select_two_stage_action(
    terms: CardAcceptancePolicyTerms,
    *,
    generator: torch.Generator | None = None,
    greedy: bool,
) -> str:
    """Select a family first, then one candidate within that family."""
    if not isinstance(terms, CardAcceptancePolicyTerms):
        raise SuccessorRuntimeError("card policy terms are invalid")
    if not isinstance(greedy, bool):
        raise SuccessorRuntimeError("greedy must be boolean")

    if greedy:
        selected_family = terms.unique_greedy_family_id
        if selected_family is None:
            raise SuccessorRuntimeError("family maximum tie has no unique choice")
        action_ids = dict(terms.greedy_action_ids_by_family)[selected_family]
        if len(action_ids) != 1:
            raise SuccessorRuntimeError(
                "conditional maximum tie has no unique choice"
            )
        return action_ids[0]

    if not isinstance(generator, torch.Generator) or generator.device.type != "cpu":
        raise SuccessorRuntimeError("card generator must remain on CPU")
    family_index = int(
        torch.multinomial(
            terms.family_probabilities,
            1,
            generator=generator,
        ).item()
    )
    selected_family = terms.family_order[family_index]
    candidate_indices = tuple(
        index
        for index, family in enumerate(terms.candidate_families)
        if family == selected_family
    )
    index_tensor = torch.tensor(candidate_indices, dtype=torch.long, device="cpu")
    local_probabilities = terms.conditional_probabilities.index_select(
        0, index_tensor
    )
    local_index = int(
        torch.multinomial(
            local_probabilities,
            1,
            generator=generator,
        ).item()
    )
    return terms.action_ids[candidate_indices[local_index]]


def score_noncard_candidates(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    category: str,
    state_features: torch.Tensor,
    candidate_features: torch.Tensor,
) -> torch.Tensor:
    """Route non-card categories only through the selected arm's frozen ranker."""
    normalized_arm = _validated_arm(arm)
    if category == "card_reward":
        raise SuccessorRuntimeError("card_reward must use the card policy")
    if not isinstance(category, str) or not category:
        raise SuccessorRuntimeError("non-card category must be nonempty")
    ranker = (
        bootstrap.candidate.frozen_noncard_ranker
        if normalized_arm == "candidate"
        else bootstrap.control.frozen_noncard_ranker
    )
    return ranker(state_features, candidate_features)


__all__ = [
    "ArmCardRewardObjective",
    "ArmOptimizerStepEvidence",
    "ArmOptimizers",
    "CandidateArm",
    "ControlArm",
    "PairedBootstrap",
    "SuccessorRuntimeError",
    "apply_arm_optimizer_step",
    "build_arm_card_reward_objective",
    "build_arm_optimizers",
    "build_matched_bootstrap",
    "encode_optimizer_state",
    "encode_paired_bootstrap",
    "forward_card_policy",
    "restore_optimizer_state",
    "restore_paired_bootstrap",
    "runtime_metadata",
    "score_noncard_candidates",
    "select_two_stage_action",
]
