from types import SimpleNamespace

from spirecomm.spire.identifiers import potion_id, relic_id


def test_potion_id_accepts_objects_and_strings():
    assert potion_id(SimpleNamespace(potion_id="FirePotion", name="Fire Potion")) == "FirePotion"
    assert potion_id(SimpleNamespace(name="Fire Potion")) == "Fire Potion"
    assert potion_id(SimpleNamespace(id="FirePotion")) == "FirePotion"
    assert potion_id("Potion Slot") == "Potion Slot"


def test_relic_id_accepts_objects_and_strings():
    assert relic_id(SimpleNamespace(relic_id="Potion Belt", name="Potion Belt")) == "Potion Belt"
    assert relic_id(SimpleNamespace(name="Sozu")) == "Sozu"
    assert relic_id(SimpleNamespace(id="Burning Blood")) == "Burning Blood"
    assert relic_id("Sozu") == "Sozu"
