from spirecomm.spire.power import Power
from spirecomm.spire.potion import Potion
from spirecomm.spire.relic import Relic


def test_power_from_json_coerces_decimal_string_numeric_fields():
    power = Power.from_json(
        {
            "id": "Strength",
            "name": "Strength",
            "amount": "2.0",
            "damage": "3.0",
            "misc": "4.0",
        }
    )

    assert power.amount == 2
    assert power.damage == 3
    assert power.misc == 4


def test_potion_from_json_coerces_decimal_string_price():
    potion = Potion.from_json(
        {
            "id": "Fire Potion",
            "name": "Fire Potion",
            "can_use": True,
            "can_discard": True,
            "requires_target": True,
            "price": "50.0",
        }
    )

    assert potion.price == 50


def test_relic_from_json_coerces_decimal_string_numeric_fields():
    relic = Relic.from_json(
        {
            "id": "Pen Nib",
            "name": "Pen Nib",
            "counter": "9.0",
            "price": "150.0",
        }
    )

    assert relic.counter == 9
    assert relic.price == 150
