from types import SimpleNamespace

from spirecomm.ai.agent import SimpleAgent
from spirecomm.communication.action import ChooseAction
from spirecomm.spire.screen import EventOption, ScreenType


def _agent_for_event(
    event_id,
    screen_options,
    choice_list,
    floor=1,
    act=1,
    hp=80,
    max_hp=80,
):
    agent = SimpleAgent.__new__(SimpleAgent)
    agent.game = SimpleNamespace(
        screen_type=ScreenType.EVENT,
        choice_available=True,
        choice_list=choice_list,
        available_commands=["choose"],
        floor=floor,
        act=act,
        current_hp=hp,
        max_hp=max_hp,
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


def test_golden_shrine_avoids_result_page_that_stops_callbacks():
    agent = _agent_for_event(
        "Golden Shrine",
        [
            EventOption("Pray", "Pray"),
            EventOption("Desecrate", "Desecrate"),
            EventOption("Leave", "Leave"),
        ],
        ["Pray", "Desecrate", "Leave"],
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 2


def test_dead_adventurer_leaves_instead_of_searching_for_elite_fight():
    agent = _agent_for_event(
        "Dead Adventurer",
        [
            EventOption("Search", "Search"),
            EventOption("Leave", "Leave"),
        ],
        ["Search", "Leave"],
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_mushrooms_event_leaves_instead_of_fighting_before_boss():
    agent = _agent_for_event(
        "Mushrooms",
        [
            EventOption("Fight", "Fight"),
            EventOption("Leave", "Leave"),
        ],
        ["Fight", "Leave"],
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_mushrooms_event_fights_instead_of_taking_parasite_heal_when_no_leave():
    agent = _agent_for_event(
        "Mushrooms",
        [
            EventOption("Stomp", "Fight"),
            EventOption("Eat", "Heal"),
        ],
        ["Fight", "Heal"],
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


def test_mushrooms_event_takes_parasite_heal_when_low_hp_before_act1_boss():
    agent = _agent_for_event(
        "Mushrooms",
        [
            EventOption("Stomp", "Fight"),
            EventOption("Eat", "Heal"),
        ],
        ["Stomp", "Eat"],
        floor=12,
        act=1,
        hp=28,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_masked_bandits_pays_instead_of_taking_fight():
    agent = _agent_for_event(
        "Masked Bandits",
        [
            EventOption("Pay", "Pay"),
            EventOption("Fight", "Fight"),
        ],
        ["Pay", "Fight"],
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


def test_note_for_yourself_leaves_instead_of_taking_starter_card():
    agent = _agent_for_event(
        "NoteForYourself",
        [
            EventOption("Take Card", "Strike_R"),
            EventOption("Leave", "Leave"),
        ],
        ["Take Card", "Leave"],
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1
