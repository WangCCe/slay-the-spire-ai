"""Heuristic implementations for decision making."""

__all__ = [
    'SynergyCardEvaluator',
    'FastCombatSimulator',
    'HeuristicCombatPlanner',
    'DeckAnalyzer',
]


def __getattr__(name):
    if name == 'SynergyCardEvaluator':
        from .card import SynergyCardEvaluator

        return SynergyCardEvaluator
    if name in ('FastCombatSimulator', 'HeuristicCombatPlanner'):
        from .simulation import FastCombatSimulator, HeuristicCombatPlanner

        return {
            'FastCombatSimulator': FastCombatSimulator,
            'HeuristicCombatPlanner': HeuristicCombatPlanner,
        }[name]
    if name == 'DeckAnalyzer':
        from .deck import DeckAnalyzer

        return DeckAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
