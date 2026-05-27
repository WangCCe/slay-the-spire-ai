from types import SimpleNamespace

from spirecomm.ai.heuristics.ironclad_archetype import IroncladArchetypeManager


def _card(card_id, upgrades=0):
    return SimpleNamespace(card_id=card_id, name=card_id, upgrades=upgrades)


def _context(deck):
    return SimpleNamespace(game=SimpleNamespace(deck=deck))


def test_ironclad_archetype_detects_upgraded_strength_core_cards():
    manager = IroncladArchetypeManager()
    context = _context([
        _card("Demon Form+1", upgrades=1),
        _card("Limit Break+1", upgrades=1),
        _card("Spot Weakness+1", upgrades=1),
        _card("Inflame+1", upgrades=1),
        _card("Reaper+1", upgrades=1),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Bash"),
    ])

    assert manager.detect_archetype(context) == "strength"


def test_ironclad_archetype_recommendations_treat_upgraded_cards_as_owned():
    manager = IroncladArchetypeManager()
    context = _context([
        _card("Demon Form+1", upgrades=1),
        _card("Inflame+1", upgrades=1),
        _card("Reaper+1", upgrades=1),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Bash"),
    ])

    recommendations = manager.get_recommended_cards("strength", context)

    assert "Demon Form" not in recommendations
    assert "Inflame" not in recommendations
    assert "Reaper" not in recommendations


def test_ironclad_archetype_accepts_upgraded_support_cards_for_established_archetype():
    manager = IroncladArchetypeManager()
    context = _context([
        _card("Demon Form+1", upgrades=1),
        _card("Limit Break+1", upgrades=1),
        _card("Spot Weakness+1", upgrades=1),
        _card("Inflame+1", upgrades=1),
        _card("Reaper+1", upgrades=1),
        _card("Strike_R"),
        _card("Defend_R"),
        _card("Bash"),
    ])

    should_accept, reason = manager.should_accept_card(_card("Heavy Blade+1", upgrades=1), context)

    assert should_accept
    assert "Support strength" in reason
