"""
DQN Network implementation for Slay the Spire RL agent.

PyTorch neural network for Q-value estimation.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


class DQNetwork(nn.Module):
    """
    Deep Q-Network for estimating action values.

    Architecture:
        Input (570) → Hidden (512) → Hidden (256) → Hidden (128) → Output (1000)

    Outputs Q-values for all possible actions (0-999).
    """

    def __init__(self, state_dim: int = 570, action_dim: int = 1000, hidden_dims: list = [512, 256, 128]):
        """
        Initialize DQN network.

        Args:
            state_dim: Dimension of state vector (default 570)
            action_dim: Dimension of action space (default 1000)
            hidden_dims: List of hidden layer dimensions
        """
        super(DQNetwork, self).__init__()

        self.state_dim = state_dim
        self.action_dim = action_dim

        # Build hidden layers
        layers = []
        input_dim = state_dim
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.1))
            input_dim = hidden_dim

        self.hidden_layers = nn.Sequential(*layers)

        # Output layer
        self.output_layer = nn.Linear(hidden_dims[-1], action_dim)

        # Initialize weights
        self._initialize_weights()

    def _initialize_weights(self):
        """Initialize network weights using Kaiming initialization."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, state: torch.Tensor, action_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass through network.

        Args:
            state: Input state tensor of shape (batch_size, state_dim)
            action_mask: Boolean mask of invalid actions (batch_size, action_dim)
                        Invalid actions will have Q-value set to -inf

        Returns:
            Q-values tensor of shape (batch_size, action_dim)
        """
        # Pass through hidden layers
        x = self.hidden_layers(state)

        # Compute Q-values
        q_values = self.output_layer(x)

        # Apply action mask if provided
        if action_mask is not None:
            # Set Q-values of invalid actions to -inf
            q_values = q_values.masked_fill(action_mask == False, float('-inf'))

        return q_values

    def get_best_action(self, state: torch.Tensor, action_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Get action with highest Q-value for given state.

        Args:
            state: Input state tensor of shape (batch_size, state_dim) or (state_dim,)
            action_mask: Boolean mask of invalid actions

        Returns:
            Action indices tensor of shape (batch_size,) or scalar
        """
        with torch.no_grad():
            if state.dim() == 1:
                # Single state
                state = state.unsqueeze(0)
                q_values = self.forward(state, action_mask)
                return q_values.argmax(dim=1).squeeze(0)
            else:
                # Batch of states
                q_values = self.forward(state, action_mask)
                return q_values.argmax(dim=1)


class DuelingDQNetwork(nn.Module):
    """
    Dueling DQN architecture (optional enhancement).

    Separates value and advantage streams for better learning.
    Not used in current implementation but available for future experiments.
    """

    def __init__(self, state_dim: int = 570, action_dim: int = 1000, hidden_dims: list = [256, 256]):
        """Initialize dueling network."""
        super(DuelingDQNetwork, self).__init__()

        # Shared feature layers
        self.feature_layers = nn.Sequential(
            nn.Linear(state_dim, hidden_dims[0]),
            nn.ReLU(),
            nn.Dropout(0.1),
        )

        # Value stream
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dims[0], hidden_dims[1]),
            nn.ReLU(),
            nn.Linear(hidden_dims[1], 1)
        )

        # Advantage stream
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dims[0], hidden_dims[1]),
            nn.ReLU(),
            nn.Linear(hidden_dims[1], action_dim)
        )

        self._initialize_weights()

    def _initialize_weights(self):
        """Initialize weights."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, state: torch.Tensor, action_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Forward pass with dueling architecture."""
        features = self.feature_layers(state)

        values = self.value_stream(features)
        advantages = self.advantage_stream(features)

        # Combine value and advantage: Q = V + (A - mean(A))
        q_values = values + (advantages - advantages.mean(dim=1, keepdim=True))

        if action_mask is not None:
            q_values = q_values.masked_fill(action_mask == False, float('-inf'))

        return q_values


# Convenience function for creating networks
def create_dqn(network_type: str = "standard", state_dim: int = 570,
               action_dim: int = 1000, device: str = "cpu") -> nn.Module:
    """
    Create DQN network of specified type.

    Args:
        network_type: "standard" or "dueling"
        state_dim: State dimension
        action_dim: Action dimension
        device: Device to place network on ("cpu" or "cuda")

    Returns:
        Initialized network on specified device
    """
    if network_type == "standard":
        network = DQNetwork(state_dim, action_dim)
    elif network_type == "dueling":
        network = DuelingDQNetwork(state_dim, action_dim)
    else:
        raise ValueError(f"Unknown network type: {network_type}")

    network = network.to(device)
    return network


if __name__ == "__main__":
    # Test network creation
    print("Testing DQNetwork...")

    # Create network
    net = create_dqn("standard", device="cpu")
    print(f"✓ Network created: {net}")
    print(f"  Parameters: {sum(p.numel() for p in net.parameters())}")

    # Test forward pass
    batch_size = 4
    state = torch.randn(batch_size, 570)
    action_mask = torch.ones(batch_size, 1000, dtype=torch.bool)
    action_mask[:, 500:] = False  # Mask some actions

    q_values = net(state, action_mask)
    print(f"✓ Forward pass: input {state.shape} → output {q_values.shape}")

    # Test best action selection
    actions = net.get_best_action(state[0], action_mask[0])
    print(f"✓ Best action: {actions}")

    # Test with CUDA if available
    if torch.cuda.is_available():
        print("\nTesting with CUDA...")
        net_cuda = create_dqn("standard", device="cuda")
        state_cuda = state.to("cuda")
        mask_cuda = action_mask.to("cuda")
        q_cuda = net_cuda(state_cuda, mask_cuda)
        print(f"✓ CUDA forward pass: {q_cuda.shape}")
        print(f"  Device: {next(net_cuda.parameters()).device}")

    print("\n✓ All tests passed!")
