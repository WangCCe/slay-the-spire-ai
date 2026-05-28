from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_combat_damage_paths_use_shared_intent_helper():
    paths = [
        ROOT / "spirecomm" / "ai" / "agent.py",
        ROOT / "spirecomm" / "ai" / "rl" / "agent.py",
        ROOT / "spirecomm" / "ai" / "heuristics" / "simulation.py",
    ]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "from spirecomm.ai.intent_utils import monster_intends_attack" in text
        assert "def _is_attack_intent" not in text
        assert "def _is_attack_intent_object" not in text


def test_timing_paths_use_shared_intent_helper():
    expectations = {
        ROOT / "spirecomm" / "ai" / "heuristics" / "timing" / "turn_classifier.py":
            "from spirecomm.ai.intent_utils import intent_is_attack",
        ROOT / "spirecomm" / "ai" / "heuristics" / "timing" / "balance_strategy.py":
            "from spirecomm.ai.intent_utils import monster_intends_attack",
    }

    for path, import_line in expectations.items():
        text = path.read_text(encoding="utf-8")
        assert import_line in text
        assert "def _is_attack_intent" not in text
        assert "def _is_attacking_intent" not in text
