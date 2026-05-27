from types import SimpleNamespace

from spirecomm.ai.priorities import IroncladPriority


def _card(card_id, upgrades=0):
    return SimpleNamespace(card_id=card_id, name=card_id, upgrades=upgrades)


def test_priority_order_treats_counted_upgraded_cards_as_base_cards():
    priority = IroncladPriority()

    best = priority.get_best_card([
        _card("Demon Form+1", upgrades=1),
        _card("Strike_R"),
    ])

    assert best.card_id == "Demon Form+1"


def test_priority_traits_treat_counted_upgraded_cards_as_base_cards():
    priority = IroncladPriority()

    assert priority.is_card_aoe(_card("Cleave+1", upgrades=1)) is True
    assert priority.is_card_defensive(_card("Flame Barrier+1", upgrades=1)) is True


def test_ironclad_group_copy_limit_counts_upgraded_transition_attacks():
    priority = IroncladPriority()
    deck = [
        _card("Bash+1", upgrades=1),
        _card("Cleave+1", upgrades=1),
    ]

    needs_more = priority.needs_more_copies(
        _card("Thunderclap+1", upgrades=1),
        num_copies=0,
        deck=deck,
    )

    assert needs_more is False
