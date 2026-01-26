"""
Convert legacy RL checkpoints to the current state dimension.

Usage:
  python scripts/convert_rl_checkpoint.py --input old.pth --output new.pth
"""

import argparse
import logging
from typing import Dict, Tuple

import torch

from spirecomm.ai.rl.network import create_dqn


logger = logging.getLogger(__name__)


def align_state_dict_input(
    state_dict: Dict[str, torch.Tensor],
    model: torch.nn.Module,
) -> Tuple[Dict[str, torch.Tensor], bool]:
    model_state = model.state_dict()
    updated = False
    aligned = {}

    for name, tensor in state_dict.items():
        if name not in model_state:
            aligned[name] = tensor
            continue
        target = model_state[name]
        if tensor.shape == target.shape:
            aligned[name] = tensor
            continue

        if tensor.dim() == 2 and target.dim() == 2:
            new_tensor = torch.zeros(target.shape, dtype=tensor.dtype)
            out_min = min(tensor.shape[0], target.shape[0])
            in_min = min(tensor.shape[1], target.shape[1])
            new_tensor[:out_min, :in_min] = tensor[:out_min, :in_min]
            aligned[name] = new_tensor
            updated = True
        elif tensor.dim() == 1 and target.dim() == 1:
            new_tensor = torch.zeros(target.shape, dtype=tensor.dtype)
            out_min = min(tensor.shape[0], target.shape[0])
            new_tensor[:out_min] = tensor[:out_min]
            aligned[name] = new_tensor
            updated = True
        else:
            aligned[name] = tensor

    return aligned, updated


def convert_checkpoint(
    input_path: str,
    output_path: str,
    state_dim: int,
    action_dim: int,
    network_type: str,
    device: str,
) -> None:
    checkpoint = torch.load(input_path, map_location=device)
    model = create_dqn(network_type, state_dim=state_dim, action_dim=action_dim, device=device)

    updated = False
    if isinstance(checkpoint, dict) and "online_network_state_dict" in checkpoint:
        online_state, online_updated = align_state_dict_input(
            checkpoint["online_network_state_dict"], model
        )
        updated |= online_updated
        checkpoint["online_network_state_dict"] = online_state

        if "target_network_state_dict" in checkpoint:
            target_state, target_updated = align_state_dict_input(
                checkpoint["target_network_state_dict"], model
            )
            updated |= target_updated
            checkpoint["target_network_state_dict"] = target_state

        if updated and "optimizer_state_dict" in checkpoint:
            checkpoint.pop("optimizer_state_dict", None)

        checkpoint["converted_state_dim"] = state_dim
        checkpoint["conversion_applied"] = bool(updated)
        torch.save(checkpoint, output_path)
        return

    if isinstance(checkpoint, dict):
        state_dict, updated = align_state_dict_input(checkpoint, model)
        torch.save(state_dict, output_path)
        return

    raise ValueError("Unsupported checkpoint format.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert RL checkpoint to new state_dim.")
    parser.add_argument("--input", required=True, help="Path to legacy checkpoint .pth")
    parser.add_argument("--output", required=True, help="Path to save converted checkpoint .pth")
    parser.add_argument("--state-dim", type=int, default=781, help="Target state dimension")
    parser.add_argument("--action-dim", type=int, default=1000, help="Target action dimension")
    parser.add_argument("--network-type", default="dueling", help="Network type: standard or dueling")
    parser.add_argument("--device", default="cpu", help="Device for loading (cpu or cuda)")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    convert_checkpoint(
        input_path=args.input,
        output_path=args.output,
        state_dim=args.state_dim,
        action_dim=args.action_dim,
        network_type=args.network_type,
        device=args.device,
    )
    logger.info("Converted checkpoint saved to %s", args.output)


if __name__ == "__main__":
    main()
