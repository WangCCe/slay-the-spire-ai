"""
Reinforcement Learning agents for Slay the Spire.

This module contains RL-based decision systems including DQN agents,
state/action encoders, replay buffers, and training infrastructure.
"""

from importlib import import_module
from importlib.util import find_spec


def _optional_dependency_available(name: str) -> bool:
    return find_spec(name) is not None


RL_AVAILABLE = (
    _optional_dependency_available("numpy")
    and _optional_dependency_available("torch")
)
RL_V2_AVAILABLE = RL_AVAILABLE

_EXPORT_MODULES = {
    "StateEncoder": ".state_encoder",
    "ActionEncoder": ".action_encoder",
    "RewardCalculator": ".reward",
    "ReplayBuffer": ".replay_buffer",
    "RLAgent": ".agent",
    "create_agent": ".agent",
    "CombatRLAgent": ".agent",
    "MapRLAgent": ".agent",
    "RLAgentV2": ".v2.agent",
    "create_agent_v2": ".v2.agent",
}

_MODULE_EXPORTS = {}
for _name, _module_name in _EXPORT_MODULES.items():
    _MODULE_EXPORTS.setdefault(_module_name, []).append(_name)


def __getattr__(name):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    try:
        module = import_module(module_name, __name__)
    except ImportError:
        # Preserve the historical optional-dependency behavior: missing RL
        # dependencies make exported RL symbols resolve to None instead of
        # breaking non-RL imports.
        for exported_name in _MODULE_EXPORTS[module_name]:
            globals()[exported_name] = None
        if module_name == ".agent":
            globals()["RL_AVAILABLE"] = False
        if module_name == ".v2.agent":
            globals()["RL_V2_AVAILABLE"] = False
        return None

    for exported_name in _MODULE_EXPORTS[module_name]:
        if hasattr(module, exported_name):
            globals()[exported_name] = getattr(module, exported_name)

    return globals()[name]

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
