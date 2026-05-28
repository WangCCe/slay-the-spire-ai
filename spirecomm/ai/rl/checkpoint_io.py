"""Checkpoint loading helpers shared by RL agents and trainers."""

from typing import Any

import torch


def load_torch_checkpoint(path: str, map_location=None) -> Any:
    """Load a torch checkpoint without enabling arbitrary object loading."""
    try:
        return torch.load(path, map_location=map_location, weights_only=True)
    except TypeError as exc:
        if "weights_only" not in str(exc):
            raise
        return torch.load(path, map_location=map_location)

