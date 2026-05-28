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
