import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imports_from_intent_utils(path: Path, name: str) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "spirecomm.ai.intent_utils"
        and any(alias.name == name for alias in node.names)
        for node in ast.walk(tree)
    )


def test_combat_damage_paths_use_shared_intent_helper():
    paths = [
        ROOT / "spirecomm" / "ai" / "agent.py",
        ROOT / "spirecomm" / "ai" / "rl" / "agent.py",
        ROOT / "spirecomm" / "ai" / "heuristics" / "simulation.py",
    ]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert _imports_from_intent_utils(path, "monster_intends_attack")
        assert "def _is_attack_intent" not in text
        assert "def _is_attack_intent_object" not in text


def test_timing_paths_use_shared_intent_helper():
    expectations = {
        ROOT / "spirecomm" / "ai" / "heuristics" / "timing" / "turn_classifier.py":
            "intent_is_attack",
        ROOT / "spirecomm" / "ai" / "heuristics" / "timing" / "balance_strategy.py":
            "monster_intends_attack",
    }

    for path, imported_name in expectations.items():
        text = path.read_text(encoding="utf-8")
        assert _imports_from_intent_utils(path, imported_name)
        assert "def _is_attack_intent" not in text
        assert "def _is_attacking_intent" not in text
