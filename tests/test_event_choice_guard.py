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


def test_mausoleum_leaves_instead_of_taking_writhe_curse():
    agent = _agent_for_event(
        "The Mausoleum",
        [
            EventOption("Open Coffin", "Open Coffin"),
            EventOption("Leave", "Leave"),
        ],
        ["Open Coffin", "Leave"],
        floor=29,
        act=2,
        hp=42,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_forgotten_altar_avoids_lethal_sacrifice_at_critical_hp():
    agent = _agent_for_event(
        "Forgotten Altar",
        [
            EventOption("Locked", "Locked"),
            EventOption("Sacrifice", "Sacrifice"),
            EventOption("Desecrate", "Desecrate"),
        ],
        ["Sacrifice", "Desecrate"],
        floor=20,
        act=2,
        hp=10,
        max_hp=85,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_forgotten_altar_sacrifices_at_mid_hp_to_avoid_decay_curse():
    agent = _agent_for_event(
        "Forgotten Altar",
        [
            EventOption("Locked", "Locked"),
            EventOption("Sacrifice", "Sacrifice"),
            EventOption("Desecrate", "Desecrate"),
        ],
        ["Sacrifice", "Desecrate"],
        floor=21,
        act=2,
        hp=67,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


def test_forgotten_altar_sacrifices_when_act2_hp_margin_stays_safe():
    agent = _agent_for_event(
        "Forgotten Altar",
        [
            EventOption("Locked", "Locked"),
            EventOption("Sacrifice", "Sacrifice"),
            EventOption("Desecrate", "Desecrate"),
        ],
        ["Sacrifice", "Desecrate"],
        floor=21,
        act=2,
        hp=80,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


def test_shining_light_leaves_when_hp_is_below_requested_strike_threshold():
    agent = _agent_for_event(
        "Shining Light",
        [
            EventOption("Enter", "Enter"),
            EventOption("Leave", "Leave"),
        ],
        ["Enter", "Leave"],
        floor=10,
        act=1,
        hp=35,
        max_hp=75,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_shining_light_enters_when_hp_matches_bottled_threshold():
    agent = _agent_for_event(
        "Shining Light",
        [
            EventOption("Enter", "Enter"),
            EventOption("Leave", "Leave"),
        ],
        ["Enter", "Leave"],
        floor=5,
        act=1,
        hp=54,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


def test_shining_light_enters_when_hp_margin_stays_safe():
    agent = _agent_for_event(
        "Shining Light",
        [
            EventOption("Enter", "Enter"),
            EventOption("Leave", "Leave"),
        ],
        ["Enter", "Leave"],
        floor=4,
        act=1,
        hp=80,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


def test_cursed_tome_leaves_when_reading_breaks_act2_hp_margin():
    agent = _agent_for_event(
        "Cursed Tome",
        [
            EventOption("Read", "Read"),
            EventOption("Leave", "Leave"),
        ],
        ["Read", "Leave"],
        floor=19,
        act=2,
        hp=61,
        max_hp=85,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_cursed_tome_reads_when_hp_margin_stays_safe():
    agent = _agent_for_event(
        "Cursed Tome",
        [
            EventOption("Read", "Read"),
            EventOption("Leave", "Leave"),
        ],
        ["Read", "Leave"],
        floor=19,
        act=2,
        hp=85,
        max_hp=85,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


def test_mind_bloom_avoids_boss_fight_when_low_hp():
    agent = _agent_for_event(
        "MindBloom",
        [
            EventOption("I am War", "I am War"),
            EventOption("I am Awake", "I am Awake"),
            EventOption("I am Rich", "I am Rich"),
        ],
        ["I am War", "I am Awake", "I am Rich"],
        floor=38,
        act=3,
        hp=21,
        max_hp=95,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_mind_bloom_takes_boss_fight_when_hp_margin_is_healthy():
    agent = _agent_for_event(
        "MindBloom",
        [
            EventOption("I am War", "I am War"),
            EventOption("I am Awake", "I am Awake"),
            EventOption("I am Rich", "I am Rich"),
        ],
        ["I am War", "I am Awake", "I am Rich"],
        floor=38,
        act=3,
        hp=95,
        max_hp=95,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


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


def test_mushrooms_event_fights_when_hp_is_above_bottled_threshold():
    agent = _agent_for_event(
        "Mushrooms",
        [
            EventOption("Stomp", "Fight"),
            EventOption("Eat", "Heal"),
        ],
        ["Stomp", "Eat"],
        floor=8,
        act=1,
        hp=62,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


def test_mushrooms_event_still_fights_when_full_hp_after_act1_route_setup():
    agent = _agent_for_event(
        "Mushrooms",
        [
            EventOption("Stomp", "Fight"),
            EventOption("Eat", "Heal"),
        ],
        ["Stomp", "Eat"],
        floor=8,
        act=1,
        hp=80,
        max_hp=80,
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


def test_nloth_offers_non_core_relic_instead_of_burning_blood():
    agent = _agent_for_event(
        "N'loth",
        [
            EventOption("Offer: Burning Blood", "Offer: Burning Blood"),
            EventOption("Offer: Runic Cube", "Offer: Runic Cube"),
            EventOption("Leave", "Leave"),
        ],
        ["Offer: Burning Blood", "Offer: Runic Cube", "Leave"],
        floor=19,
        act=2,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_nloth_leaves_when_only_core_relic_offer_is_available():
    agent = _agent_for_event(
        "N'loth",
        [
            EventOption("Offer: Burning Blood", "Offer: Burning Blood"),
            EventOption("Leave", "Leave"),
        ],
        ["Offer: Burning Blood", "Leave"],
        floor=19,
        act=2,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


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


def test_living_wall_grows_to_upgrade_a_card():
    agent = _agent_for_event(
        "Living Wall",
        [
            EventOption("Forget", "Forget"),
            EventOption("Change", "Change"),
            EventOption("Grow", "Grow"),
        ],
        ["Forget", "Change", "Grow"],
        floor=6,
        act=1,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 2


def test_cleric_purifies_instead_of_healing_when_hp_margin_is_healthy():
    agent = _agent_for_event(
        "The Cleric",
        [
            EventOption("Heal", "Heal"),
            EventOption("Purify", "Purify"),
            EventOption("Leave", "Leave"),
        ],
        ["Heal", "Purify", "Leave"],
        floor=8,
        act=1,
        hp=63,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_cleric_heals_when_hp_margin_is_low():
    agent = _agent_for_event(
        "The Cleric",
        [
            EventOption("Heal", "Heal"),
            EventOption("Purify", "Purify"),
            EventOption("Leave", "Leave"),
        ],
        ["Heal", "Purify", "Leave"],
        floor=14,
        act=1,
        hp=52,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0


def test_big_fish_takes_max_hp_when_not_low_hp():
    agent = _agent_for_event(
        "Big Fish",
        [
            EventOption("Banana", "Banana"),
            EventOption("Donut", "Donut"),
            EventOption("Box", "Box"),
        ],
        ["Banana", "Donut", "Box"],
        floor=3,
        act=1,
        hp=46,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 1


def test_big_fish_takes_heal_when_hp_is_critical():
    agent = _agent_for_event(
        "Big Fish",
        [
            EventOption("Banana", "Banana"),
            EventOption("Donut", "Donut"),
            EventOption("Box", "Box"),
        ],
        ["Banana", "Donut", "Box"],
        floor=3,
        act=1,
        hp=20,
        max_hp=80,
    )

    action = agent.handle_screen()

    assert isinstance(action, ChooseAction)
    assert action.choice_index == 0
