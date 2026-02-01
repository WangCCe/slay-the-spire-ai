"""
Reinforcement Learning agents for Slay the Spire.

This module contains RL-based decision systems including DQN agents,
state/action encoders, replay buffers, and training infrastructure.
"""

# Try to import RL components, but don't fail if PyTorch is not installed
try:
    from .state_encoder import StateEncoder
    from .action_encoder import ActionEncoder
    from .reward import RewardCalculator
    from .replay_buffer import ReplayBuffer
    from .agent import RLAgent, create_agent, CombatRLAgent, MapRLAgent
    RL_AVAILABLE = True
except ImportError as e:
    # PyTorch or other dependencies not installed
    RL_AVAILABLE = False
    StateEncoder = None
    ActionEncoder = None
    RewardCalculator = None
    ReplayBuffer = None
    RLAgent = None
    create_agent = None
    CombatRLAgent = None
    MapRLAgent = None

try:
    from .v2.agent import RLAgentV2, create_agent_v2
    RL_V2_AVAILABLE = True
except ImportError:
    RL_V2_AVAILABLE = False
    RLAgentV2 = None
    create_agent_v2 = None

__all__ = [
    'StateEncoder',
    'ActionEncoder',
    'RewardCalculator',
    'ReplayBuffer',
    'RLAgent',
    'create_agent',
    'CombatRLAgent',
    'MapRLAgent',
    'RL_AVAILABLE',
    'RLAgentV2',
    'create_agent_v2',
    'RL_V2_AVAILABLE',
]
