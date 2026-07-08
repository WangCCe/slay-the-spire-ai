import json
import subprocess
from pathlib import Path

from analysis_scripts.offline_decision_comparator import DecisionSample


def _write_fake_bottled_checkout(root: Path) -> Path:
    for relative in [
        "rs",
        "rs/ai",
        "rs/ai/requested_strike",
        "rs/ai/requested_strike/handlers",
        "rs/common",
        "rs/common/handlers",
        "rs/game",
    ]:
        path = root / relative
        path.mkdir(parents=True, exist_ok=True)
        (path / "__init__.py").write_text("", encoding="utf-8")

    (root / "rs/ai/requested_strike/config.py").write_text(
        "\n".join(
            [
                "CARD_REMOVAL_PRIORITY_LIST = ['defend', 'strike']",
                "DESIRED_CARDS_FOR_DECK = {'sentinel': 1}",
                "HIGH_PRIORITY_UPGRADES = []",
                "DESIRED_POTIONS = []",
            ]
        ),
        encoding="utf-8",
    )
    (root / "rs/ai/requested_strike/handlers/shop_purchase_handler.py").write_text(
        "\n".join(
            [
                "class ShopPurchaseHandler:",
                "    def __init__(self):",
                "        self.relics = ['Oddly Smooth Stone']",
                "        self.cards = ['Wild Strike']",
            ]
        ),
        encoding="utf-8",
    )
    (root / "rs/ai/requested_strike/handlers/event_handler.py").write_text(
        "\n".join(
            [
                "from rs.game.event import Event",
                "class EventHandler:",
                "    def __init__(self, removal_priority_list, cards_desired_for_deck):",
                "        pass",
                "    def find_event_choice(self, state):",
                "        if state.get_event() == Event.FAKE_FORK:",
                "            return 'choose 1'",
                "        if state.get_event() == Event.FALLING:",
                "            options = state.get_falling_event_options()",
                "            if 'strike' in options:",
                "                return 'choose ' + str(options.index('strike'))",
                "        return None",
            ]
        ),
        encoding="utf-8",
    )
    (root / "rs/game/event.py").write_text(
        "\n".join(
            [
                "from enum import Enum",
                "class Event(Enum):",
                "    FAKE_FORK = 'Fake Fork'",
                "    FALLING = 'Falling'",
            ]
        ),
        encoding="utf-8",
    )
    (root / "rs/common/handlers/common_map_handler.py").write_text(
        "\n".join(
            [
                "class _Config:",
                "    hallway_fight_base_reward = 0",
                "    hallway_fight_prayer_wheel = 0",
                "    hallway_question_card_reward = 0",
                "    hallway_fight_gold = 0",
                "    elite_base_reward = 0",
                "    elite_question_card_reward = 0",
                "    elite_fight_gold = 0",
                "    relic_reward = 0",
                "    curse_reward_loss = 0",
                "    upgrade_reward = 0",
                "    event_value_reward = staticmethod(lambda state: 5)",
                "    gold_at_shop_reward = staticmethod(lambda state, gold_to_spend: 0)",
                "    gold_after_boss_reward = staticmethod(lambda state: 0)",
                "    survivability_reward_calculation = staticmethod(lambda reward, survivability: reward)",
                "default_config = _Config()",
            ]
        ),
        encoding="utf-8",
    )
    return root


def _init_git_repo(path: Path) -> str:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "fake bottled checkout",
        ],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_missing_bottled_checkout_returns_unsupported_without_high_confidence(tmp_path):
    from analysis_scripts.bottled_policy_oracle import BottledPolicyOracle

    oracle = BottledPolicyOracle(tmp_path / "missing")
    sample = DecisionSample(
        sample_id="card",
        category="card_reward",
        source="fixture",
        floor=1,
        act=1,
        evidence_quality="complete",
        our_choice={"kind": "skip", "name": "skip"},
        context={"offered": ["Sentinel"], "deck": [], "can_skip": True},
    )

    result = oracle.evaluate(sample)

    assert result.status == "unsupported"
    assert result.confidence == "low"
    assert result.label == "unknown"
    assert "missing" in " ".join(result.limitations).lower()


def test_adapter_uses_checkout_requested_strike_card_reward_config(tmp_path):
    from analysis_scripts.bottled_policy_oracle import BottledPolicyOracle

    checkout = _write_fake_bottled_checkout(tmp_path / "bottled_ai")
    commit = _init_git_repo(checkout)
    sample = DecisionSample(
        sample_id="card",
        category="card_reward",
        source="fixture",
        floor=1,
        act=1,
        evidence_quality="complete",
        our_choice={"kind": "skip", "name": "skip"},
        context={"offered": ["Sentinel"], "deck": [], "can_skip": True},
    )

    result = BottledPolicyOracle(checkout).evaluate(sample)

    assert result.status == "ok"
    assert result.label == "Sentinel"
    assert result.confidence == "high"
    assert result.source["strategy"] == "REQUESTED_STRIKE"
    assert result.source["commit"] == commit
    assert result.source["mode"] == "native_bottled"


def test_adapter_uses_checkout_shop_handler_priorities(tmp_path):
    from analysis_scripts.bottled_policy_oracle import BottledPolicyOracle

    checkout = _write_fake_bottled_checkout(tmp_path / "bottled_ai")
    sample = DecisionSample(
        sample_id="shop",
        category="shop",
        source="fixture",
        floor=4,
        act=1,
        evidence_quality="complete",
        our_choice={"kind": "leave", "name": "leave"},
        context={
            "gold": 200,
            "purge_available": False,
            "purge_cost": 75,
            "deck": ["Bash"],
            "cards": [{"id": "Wild Strike", "name": "Wild Strike", "price": 80}],
            "relics": [],
            "potions": [],
        },
    )

    result = BottledPolicyOracle(checkout).evaluate(sample)

    assert result.status == "ok"
    assert result.label == "Wild Strike"
    assert result.raw["command"] == "choose 0"
    assert "shop" in result.reason.lower()


def test_adapter_uses_checkout_event_handler_command(tmp_path):
    from analysis_scripts.bottled_policy_oracle import BottledPolicyOracle

    checkout = _write_fake_bottled_checkout(tmp_path / "bottled_ai")
    sample = DecisionSample(
        sample_id="event",
        category="event",
        source="fixture",
        floor=7,
        act=1,
        evidence_quality="complete",
        our_choice={"kind": "choose", "index": 0, "label": "Take"},
        context={
            "event_name": "Fake Fork",
            "current_hp": 70,
            "max_hp": 80,
            "choices": ["Take", "Leave"],
            "relics": [],
        },
    )

    result = BottledPolicyOracle(checkout).evaluate(sample)

    assert result.status == "ok"
    assert result.label == "choose 1: Leave"
    assert result.raw["command"] == "choose 1"


def test_adapter_exposes_falling_event_options_to_checkout_handler(tmp_path):
    from analysis_scripts.bottled_policy_oracle import BottledPolicyOracle

    checkout = _write_fake_bottled_checkout(tmp_path / "bottled_ai")
    sample = DecisionSample(
        sample_id="falling",
        category="event",
        source="fixture",
        floor=42,
        act=3,
        evidence_quality="complete",
        our_choice={"kind": "choose", "index": 0, "label": "Lose Bash"},
        context={
            "event_name": "Falling",
            "current_hp": 70,
            "max_hp": 80,
            "choices": ["Lose Bash", "Lose Strike+", "Lose Anger"],
            "relics": [],
        },
    )

    result = BottledPolicyOracle(checkout).evaluate(sample)

    assert result.status == "ok"
    assert result.label == "choose 1: Lose Strike+"
    assert result.raw["command"] == "choose 1"


def test_adapter_uses_checkout_route_config_when_scoring_paths(tmp_path):
    from analysis_scripts.bottled_policy_oracle import BottledPolicyOracle

    checkout = _write_fake_bottled_checkout(tmp_path / "bottled_ai")
    sample = DecisionSample(
        sample_id="route",
        category="route",
        source="fixture",
        floor=1,
        act=1,
        evidence_quality="complete",
        our_choice={"kind": "map_node", "choice": 0},
        context={
            "current_hp": 80,
            "max_hp": 80,
            "gold": 0,
            "relics": [],
            "paths": [
                {"choice": 0, "label": "monster", "nodes": ["M"]},
                {"choice": 1, "label": "event", "nodes": ["?"]},
            ],
        },
    )

    result = BottledPolicyOracle(checkout).evaluate(sample)

    assert result.status == "ok"
    assert result.label == "choice 1"
    assert "reward-to-survivability" in result.reason


def test_adapter_reports_combat_as_feasibility_only(tmp_path):
    from analysis_scripts.bottled_policy_oracle import BottledPolicyOracle

    checkout = _write_fake_bottled_checkout(tmp_path / "bottled_ai")
    result = BottledPolicyOracle(checkout).evaluate(
        DecisionSample(
            sample_id="combat",
            category="combat",
            source="fixture",
            floor=1,
            act=1,
            evidence_quality="complete",
            our_choice={"kind": "play", "name": "Strike"},
            context={},
        )
    )

    assert result.status == "unsupported"
    assert result.label == "unknown"
    assert "feasibility" in " ".join(result.limitations).lower()
