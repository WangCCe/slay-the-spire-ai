"""
RL v2 components (action/observation spaces with embeddings).
"""

from importlib import import_module

_EXPORT_MODULES = {
    "RLAgentV2": ".agent",
    "create_agent_v2": ".agent",
}


def __getattr__(name):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name, __name__)
    for exported_name in _EXPORT_MODULES:
        if hasattr(module, exported_name):
            globals()[exported_name] = getattr(module, exported_name)
    return globals()[name]

__all__ = [
    "RLAgentV2",
    "create_agent_v2",
]
