"""
Migrate a standard DQN checkpoint to dueling DQN.

Strategy:
  - Copy shared feature layer from standard hidden_layers[0] -> dueling feature_layers[0]
  - Initialize advantage stream using standard output_layer
  - Initialize value stream with zeros

Usage:
  python scripts/migrate_checkpoint_standard_to_dueling.py --input old.pth --output new.pth
"""

import argparse
import logging
from typing import Dict, Any

import torch

from spirecomm.ai.rl.network import create_dqn, align_state_dict_input


logger = logging.getLogger(__name__)


def migrate_state_dict(
    src_state: Dict[str, torch.Tensor],
    dst_model: torch.nn.Module,
) -> Dict[str, torch.Tensor]:
    dst_state = dst_model.state_dict()

    # Copy feature layer weights/biases from standard hidden layer 0.
    if "hidden_layers.0.weight" in src_state and "feature_layers.0.weight" in dst_state:
        dst_state["feature_layers.0.weight"] = src_state["hidden_layers.0.weight"].clone()
    if "hidden_layers.0.bias" in src_state and "feature_layers.0.bias" in dst_state:
        dst_state["feature_layers.0.bias"] = src_state["hidden_layers.0.bias"].clone()

    # Advantage stream init from standard output layer (pad/truncate to match).
    if "output_layer.weight" in src_state and "advantage_stream.2.weight" in dst_state:
        out_w = src_state["output_layer.weight"]
        adv_w = torch.zeros_like(dst_state["advantage_stream.2.weight"])
        out_min = min(adv_w.shape[0], out_w.shape[0])
        in_min = min(adv_w.shape[1], out_w.shape[1])
        adv_w[:out_min, :in_min] = out_w[:out_min, :in_min]
        dst_state["advantage_stream.2.weight"] = adv_w
    if "output_layer.bias" in src_state and "advantage_stream.2.bias" in dst_state:
        out_b = src_state["output_layer.bias"]
        adv_b = torch.zeros_like(dst_state["advantage_stream.2.bias"])
        out_min = min(adv_b.shape[0], out_b.shape[0])
        adv_b[:out_min] = out_b[:out_min]
        dst_state["advantage_stream.2.bias"] = adv_b

    # Value stream stays zero-initialized (already zeros in dst_state after init).
    return dst_state


def convert_checkpoint(input_path: str, output_path: str, state_dim: int, action_dim: int) -> None:
    checkpoint = torch.load(input_path, map_location="cpu")

    # Extract source state dict.
    if isinstance(checkpoint, dict) and "online_network_state_dict" in checkpoint:
        src_state = checkpoint["online_network_state_dict"]
        has_target = "target_network_state_dict" in checkpoint
    elif isinstance(checkpoint, dict):
        src_state = checkpoint
        has_target = False
    else:
        raise ValueError("Unsupported checkpoint format.")

    dueling = create_dqn("dueling", state_dim=state_dim, action_dim=action_dim, device="cpu")
    dst_state = migrate_state_dict(src_state, dueling)
    dst_state, _ = align_state_dict_input(dst_state, dueling)
    dueling.load_state_dict(dst_state)

    if isinstance(checkpoint, dict) and "online_network_state_dict" in checkpoint:
        checkpoint["online_network_state_dict"] = dueling.state_dict()
        if has_target:
            checkpoint["target_network_state_dict"] = dueling.state_dict()
        checkpoint["network_type"] = "dueling"
        checkpoint["migrated_from"] = "standard"
        torch.save(checkpoint, output_path)
    else:
        torch.save(dueling.state_dict(), output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate standard DQN checkpoint to dueling.")
    parser.add_argument("--input", required=True, help="Path to standard checkpoint .pth")
    parser.add_argument("--output", required=True, help="Path to save dueling checkpoint .pth")
    parser.add_argument("--state-dim", type=int, default=781, help="Target state dimension")
    parser.add_argument("--action-dim", type=int, default=1000, help="Target action dimension")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    convert_checkpoint(args.input, args.output, args.state_dim, args.action_dim)
    logger.info("Migrated checkpoint saved to %s", args.output)


if __name__ == "__main__":
    main()
