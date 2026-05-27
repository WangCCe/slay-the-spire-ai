from types import SimpleNamespace

from spirecomm.ai.heuristics.card_names import canonical_card_name, card_data_key


def test_canonical_card_name_strips_upgrade_suffix_with_count():
    card = SimpleNamespace(card_id="Searing Blow", name="Searing Blow+2")

    assert canonical_card_name(card) == "Searing Blow"


def test_canonical_card_name_falls_back_to_basic_card_id():
    card = SimpleNamespace(card_id="Strike_R", name="")

    assert canonical_card_name(card) == "Strike"


def test_card_data_key_normalizes_for_loader_lookup():
    card = SimpleNamespace(card_id="Shrug It Off", name="Shrug It Off+")

    assert card_data_key(card) == "shrug it off"
