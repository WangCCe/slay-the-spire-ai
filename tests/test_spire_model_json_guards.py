from spirecomm.spire.power import Power


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
