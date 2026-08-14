"""Checkpoint I/O helpers shared by RL agents and trainers."""

import os
import tempfile
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


def save_torch_checkpoint(checkpoint: Any, path: str) -> None:
    """Atomically replace a checkpoint after writing it beside the target."""
    target = os.path.abspath(path)
    descriptor, temporary = tempfile.mkstemp(
        dir=os.path.dirname(target),
        prefix=f"{os.path.basename(target)}.tmp_",
    )
    os.close(descriptor)
    try:
        torch.save(checkpoint, temporary)
        os.replace(temporary, target)
    except Exception:
        try:
            os.remove(temporary)
        except FileNotFoundError:
            pass
        raise
