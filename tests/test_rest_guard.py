from types import SimpleNamespace

import spirecomm.ai.agent as agent_module
from spirecomm.ai.agent import SimpleAgent
from spirecomm.communication.action import RestAction
from spirecomm.spire.screen import RestOption, ScreenType


class _CampfireScoringRouter:
    def __init__(self, rest_score, smith_score):
        self.rest_score = rest_score
        self.smith_score = smith_score

    def _score_rest_option(self, context):
        return self.rest_score

    def _score_smith_option(self, context):
        return self.smith_score


def _agent_for_rest_choice(monkeypatch, hp, max_hp, floor, rest_score, smith_score, upgrade_score):
    monkeypatch.setattr(
        agent_module,
        "DecisionContext",
        lambda game: SimpleNamespace(
            player_hp_pct=game.current_hp / game.max_hp,
            floor=game.floor,
            game=game,
        ),
    )

    agent = SimpleAgent.__new__(SimpleAgent)
    agent.map_router = _CampfireScoringRouter(rest_score, smith_score)
    agent._best_upgrade_score = lambda context: upgrade_score
    agent.game = SimpleNamespace(
        screen_type=ScreenType.REST,
        current_hp=hp,
        max_hp=max_hp,
        act=1,
        floor=floor,
        screen=SimpleNamespace(
            has_rested=False,
            rest_options=[RestOption.REST, RestOption.SMITH],
        ),
    )
    return agent


def test_low_hp_rest_overrides_high_value_smith(monkeypatch):
    agent = _agent_for_rest_choice(
        monkeypatch,
        hp=31,
        max_hp=80,
        floor=7,
        rest_score=130,
        smith_score=170,
        upgrade_score=80,
    )

    action = agent.choose_rest_option()

    assert isinstance(action, RestAction)
    assert action.name == RestOption.REST.name


def test_pre_boss_rest_overrides_high_value_smith(monkeypatch):
    agent = _agent_for_rest_choice(
        monkeypatch,
        hp=59,
        max_hp=80,
        floor=15,
        rest_score=200,
        smith_score=190,
        upgrade_score=80,
    )

    action = agent.choose_rest_option()

    assert isinstance(action, RestAction)
    assert action.name == RestOption.REST.name


def test_pre_boss_high_hp_uses_scored_smith_when_only_slightly_damaged(monkeypatch):
    agent = _agent_for_rest_choice(
        monkeypatch,
        hp=72,
        max_hp=80,
        floor=15,
        rest_score=50,
        smith_score=190,
        upgrade_score=80,
    )

    action = agent.choose_rest_option()

    assert isinstance(action, RestAction)
    assert action.name == RestOption.SMITH.name
