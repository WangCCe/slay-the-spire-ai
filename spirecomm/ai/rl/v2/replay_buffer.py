"""
Replay buffer for RL v2 with embedding inputs.
"""

import random
from typing import Tuple
import numpy as np
import torch


class ReplayBufferV2:
    def __init__(
        self,
        buffer_size: int,
        continuous_dim: int,
        action_dim: int,
        card_slots: int,
        potion_slots: int,
        relic_slots: int,
    ):
        self.buffer_size = buffer_size
        self.continuous_dim = continuous_dim
        self.action_dim = action_dim
        self.card_slots = card_slots
        self.potion_slots = potion_slots
        self.relic_slots = relic_slots
        self.buffer = []
        self.position = 0

    def add(
        self,
        continuous: np.ndarray,
        card_ids: np.ndarray,
        potion_ids: np.ndarray,
        relic_ids: np.ndarray,
        action: int,
        reward: float,
        next_continuous: np.ndarray,
        next_card_ids: np.ndarray,
        next_potion_ids: np.ndarray,
        next_relic_ids: np.ndarray,
        done: bool,
        action_mask: np.ndarray = None,
        next_action_mask: np.ndarray = None,
        anchor_to_executed_action: bool = False,
    ) -> bool:
        if continuous is not None and len(continuous) != self.continuous_dim:
            return False
        if next_continuous is not None and len(next_continuous) != self.continuous_dim:
            return False
        if card_ids is not None and len(card_ids) != self.card_slots:
            return False
        if potion_ids is not None and len(potion_ids) != self.potion_slots:
            return False
        if relic_ids is not None and len(relic_ids) != self.relic_slots:
            return False
        if action_mask is not None and len(action_mask) != self.action_dim:
            return False
        if next_action_mask is not None and len(next_action_mask) != self.action_dim:
            return False

        transition = (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action,
            reward,
            next_continuous,
            next_card_ids,
            next_potion_ids,
            next_relic_ids,
            done,
            action_mask,
            next_action_mask,
            bool(anchor_to_executed_action),
        )

        if len(self.buffer) < self.buffer_size:
            self.buffer.append(transition)
        else:
            self.buffer[self.position] = transition

        self.position = (self.position + 1) % self.buffer_size
        return True

    def __len__(self) -> int:
        return len(self.buffer)

    def state_dict(self, max_transitions: int = None) -> dict:
        """Return a weights-only-safe, chronological replay snapshot."""
        transitions = self._ordered_transitions()
        if max_transitions is not None:
            if max_transitions <= 0:
                raise ValueError("max_transitions must be positive")
            transitions = transitions[-max_transitions:]

        count = len(transitions)

        def stacked(index, shape, dtype, default):
            if not transitions:
                return np.empty((0, *shape), dtype=dtype)
            return np.stack(
                [
                    np.asarray(
                        default if transition[index] is None else transition[index],
                        dtype=dtype,
                    )
                    for transition in transitions
                ]
            )

        return {
            "schema_version": 2,
            "buffer_size": self.buffer_size,
            "continuous_dim": self.continuous_dim,
            "action_dim": self.action_dim,
            "card_slots": self.card_slots,
            "potion_slots": self.potion_slots,
            "relic_slots": self.relic_slots,
            "transition_count": count,
            "source_transition_count": len(self.buffer),
            "truncated": count < len(self.buffer),
            "continuous": torch.from_numpy(
                stacked(0, (self.continuous_dim,), np.float32, np.zeros(self.continuous_dim))
            ),
            "card_ids": torch.from_numpy(
                stacked(1, (self.card_slots,), np.int64, np.zeros(self.card_slots))
            ),
            "potion_ids": torch.from_numpy(
                stacked(2, (self.potion_slots,), np.int64, np.zeros(self.potion_slots))
            ),
            "relic_ids": torch.from_numpy(
                stacked(3, (self.relic_slots,), np.int64, np.zeros(self.relic_slots))
            ),
            "actions": torch.tensor(
                [transition[4] for transition in transitions], dtype=torch.int64
            ),
            "rewards": torch.tensor(
                [transition[5] for transition in transitions], dtype=torch.float32
            ),
            "next_continuous": torch.from_numpy(
                stacked(6, (self.continuous_dim,), np.float32, np.zeros(self.continuous_dim))
            ),
            "next_card_ids": torch.from_numpy(
                stacked(7, (self.card_slots,), np.int64, np.zeros(self.card_slots))
            ),
            "next_potion_ids": torch.from_numpy(
                stacked(8, (self.potion_slots,), np.int64, np.zeros(self.potion_slots))
            ),
            "next_relic_ids": torch.from_numpy(
                stacked(9, (self.relic_slots,), np.int64, np.zeros(self.relic_slots))
            ),
            "dones": torch.tensor(
                [transition[10] for transition in transitions], dtype=torch.bool
            ),
            "action_masks": torch.from_numpy(
                stacked(11, (self.action_dim,), np.bool_, np.ones(self.action_dim, dtype=bool))
            ),
            "next_action_masks": torch.from_numpy(
                stacked(12, (self.action_dim,), np.bool_, np.ones(self.action_dim, dtype=bool))
            ),
            "anchor_to_executed_action": torch.tensor(
                [transition[13] for transition in transitions], dtype=torch.bool
            ),
        }

    def load_state_dict(self, state: dict) -> None:
        """Replace replay contents from a validated chronological snapshot."""
        if not isinstance(state, dict) or state.get("schema_version") not in {1, 2}:
            raise ValueError("Unsupported replay checkpoint schema")
        schema_version = int(state["schema_version"])

        expected_metadata = {
            "continuous_dim": self.continuous_dim,
            "action_dim": self.action_dim,
            "card_slots": self.card_slots,
            "potion_slots": self.potion_slots,
            "relic_slots": self.relic_slots,
        }
        for key, expected in expected_metadata.items():
            if int(state.get(key, -1)) != expected:
                raise ValueError(
                    f"Replay checkpoint {key} mismatch: expected {expected}, got {state.get(key)}"
                )

        count = int(state.get("transition_count", -1))
        if count < 0 or count > self.buffer_size:
            raise ValueError(
                f"Replay checkpoint transition_count out of range: {count}"
            )

        shapes_and_dtypes = {
            "continuous": ((count, self.continuous_dim), torch.float32),
            "card_ids": ((count, self.card_slots), torch.int64),
            "potion_ids": ((count, self.potion_slots), torch.int64),
            "relic_ids": ((count, self.relic_slots), torch.int64),
            "actions": ((count,), torch.int64),
            "rewards": ((count,), torch.float32),
            "next_continuous": ((count, self.continuous_dim), torch.float32),
            "next_card_ids": ((count, self.card_slots), torch.int64),
            "next_potion_ids": ((count, self.potion_slots), torch.int64),
            "next_relic_ids": ((count, self.relic_slots), torch.int64),
            "dones": ((count,), torch.bool),
            "action_masks": ((count, self.action_dim), torch.bool),
            "next_action_masks": ((count, self.action_dim), torch.bool),
        }
        if schema_version >= 2:
            shapes_and_dtypes["anchor_to_executed_action"] = (
                (count,),
                torch.bool,
            )
        arrays = {}
        for key, (expected_shape, expected_dtype) in shapes_and_dtypes.items():
            value = state.get(key)
            if not isinstance(value, torch.Tensor):
                raise ValueError(f"Replay checkpoint field is not a tensor: {key}")
            if tuple(value.shape) != expected_shape:
                raise ValueError(
                    f"Replay checkpoint {key} shape mismatch: "
                    f"expected {expected_shape}, got {tuple(value.shape)}"
                )
            if value.dtype != expected_dtype:
                raise ValueError(
                    f"Replay checkpoint {key} dtype mismatch: "
                    f"expected {expected_dtype}, got {value.dtype}"
                )
            arrays[key] = value.detach().cpu().numpy()

        transitions = []
        for index in range(count):
            done = bool(arrays["dones"][index])
            action = int(arrays["actions"][index])
            if action < 0 or action >= self.action_dim:
                raise ValueError(f"Replay checkpoint action out of range: {action}")
            transitions.append(
                (
                    arrays["continuous"][index].astype(np.float32, copy=True),
                    arrays["card_ids"][index].astype(np.int64, copy=True),
                    arrays["potion_ids"][index].astype(np.int64, copy=True),
                    arrays["relic_ids"][index].astype(np.int64, copy=True),
                    action,
                    float(arrays["rewards"][index]),
                    None
                    if done
                    else arrays["next_continuous"][index].astype(np.float32, copy=True),
                    None
                    if done
                    else arrays["next_card_ids"][index].astype(np.int64, copy=True),
                    None
                    if done
                    else arrays["next_potion_ids"][index].astype(np.int64, copy=True),
                    None
                    if done
                    else arrays["next_relic_ids"][index].astype(np.int64, copy=True),
                    done,
                    arrays["action_masks"][index].astype(bool, copy=True),
                    arrays["next_action_masks"][index].astype(bool, copy=True),
                    bool(arrays["anchor_to_executed_action"][index])
                    if schema_version >= 2
                    else False,
                )
            )

        self.buffer = transitions
        self.position = len(self.buffer) % self.buffer_size

    def clear(self) -> None:
        self.buffer = []
        self.position = 0

    def _ordered_transitions(self):
        if len(self.buffer) < self.buffer_size or self.position == 0:
            return list(self.buffer)
        return list(self.buffer[self.position :] + self.buffer[: self.position])

    def sample(self, batch_size: int) -> Tuple[np.ndarray, ...]:
        if len(self.buffer) < batch_size:
            raise ValueError("Not enough transitions in buffer.")

        transitions = random.sample(self.buffer, batch_size)
        continuous = np.array([t[0] for t in transitions], dtype=np.float32)
        card_ids = np.array([t[1] for t in transitions], dtype=np.int64)
        potion_ids = np.array([t[2] for t in transitions], dtype=np.int64)
        relic_ids = np.array([t[3] for t in transitions], dtype=np.int64)
        actions = np.array([t[4] for t in transitions], dtype=np.int64)
        rewards = np.array([t[5] for t in transitions], dtype=np.float32)
        next_continuous = np.array(
            [t[6] if t[6] is not None else np.zeros(self.continuous_dim) for t in transitions],
            dtype=np.float32,
        )
        next_card_ids = np.array(
            [t[7] if t[7] is not None else np.zeros(self.card_slots) for t in transitions],
            dtype=np.int64,
        )
        next_potion_ids = np.array(
            [t[8] if t[8] is not None else np.zeros(self.potion_slots) for t in transitions],
            dtype=np.int64,
        )
        next_relic_ids = np.array(
            [t[9] if t[9] is not None else np.zeros(self.relic_slots) for t in transitions],
            dtype=np.int64,
        )
        dones = np.array([t[10] for t in transitions], dtype=np.float32)
        action_masks = np.array(
            [t[11] if t[11] is not None else np.ones(self.action_dim, dtype=bool) for t in transitions],
            dtype=bool,
        )
        next_action_masks = np.array(
            [t[12] if t[12] is not None else np.ones(self.action_dim, dtype=bool) for t in transitions],
            dtype=bool,
        )
        anchor_to_executed_action = np.array(
            [t[13] for t in transitions],
            dtype=bool,
        )

        return (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            actions,
            rewards,
            next_continuous,
            next_card_ids,
            next_potion_ids,
            next_relic_ids,
            dones,
            action_masks,
            next_action_masks,
            anchor_to_executed_action,
        )

    def is_ready(self, batch_size: int) -> bool:
        return len(self.buffer) >= batch_size
