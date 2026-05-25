from types import SimpleNamespace

from spirecomm.ai.agent import SimpleAgent
from spirecomm.communication.action import ChooseAction
from spirecomm.spire.screen import EventOption, ScreenType


def _agent_for_event(event_id, screen_options, choice_list):
    agent = SimpleAgent.__new__(SimpleAgent)
    agent.game = SimpleNamespace(
        screen_type=ScreenType.EVENT,
        choice_available=True,
        choice_list=choice_list,
        available_commands=["choose"],
        screen=SimpleNamespace(
            event_id=event_id,
            event_name=event_id,
            options=screen_options,
        ),
    )
    return agent


def test_event_choice_uses_available_choice_count_before_screen_options():
    agent = _agent_for_event(
        "Golden Idol",
        [
            EventOption("Take", "Take"),
            EventOption("Leave", "Leave"),
        ],
        ["Leave"],
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


def test_event_choice_can_still_take_last_available_safe_option():
    agent = _agent_for_event(
        "Golden Idol",
        [
            EventOption("Take", "Take"),
            EventOption("Leave", "Leave"),
        ],
        ["Take", "Leave"],
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1
