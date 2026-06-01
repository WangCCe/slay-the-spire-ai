from spirecomm.ai.heuristics.simulation import HeuristicCombatPlanner
from spirecomm.spire.potion import Potion


def _potion(name):
    return Potion(
        potion_id=name.replace(" ", ""),
        name=name,
        can_use=True,
        can_discard=True,
        requires_target=False,
    )


def test_card_generating_potions_are_not_direct_damage():
    assert _potion("Attack Potion").effect_type == "card_choice_attack"
    assert _potion("Power Potion").effect_type == "card_choice_power"
    assert _potion("Skill Potion").effect_type == "card_choice_skill"
    assert _potion("Colorless Potion").effect_type == "card_choice_colorless"

    planner = HeuristicCombatPlanner()
    assert not planner._is_damage_potion(_potion("Attack Potion"))
    assert planner._is_damage_potion(_potion("Fire Potion"))


def test_potion_metadata_falls_back_to_potion_id():
    potion = Potion(
        potion_id="FirePotion",
        name=None,
        can_use=True,
        can_discard=True,
        requires_target=True,
    )

    assert potion.effect_type == "damage"
    assert potion.effect_value == 20
    assert potion.target_type == "monster"


def test_speed_and_swift_potions_have_distinct_mechanics():
    speed = _potion("Speed Potion")
    swift = _potion("Swift Potion")

    assert speed.effect_type == "temp_dexterity"
    assert speed.effect_value == 5
    assert swift.effect_type == "draw"
    assert swift.effect_value == 3


def test_defensive_buff_potions_match_exported_effects():
    essence = _potion("Essence of Steel")
    heart = _potion("Heart of Iron")
    bronze = _potion("Liquid Bronze")
    planner = HeuristicCombatPlanner()

    assert essence.effect_type == "plated_armor"
    assert essence.effect_value == 4
    assert heart.effect_type == "metallicize"
    assert heart.effect_value == 6
    assert bronze.effect_type == "thorns"
    assert bronze.effect_value == 3
    assert planner._is_block_potion(essence)
    assert planner._is_block_potion(heart)


def test_blood_potion_heals_percent_of_max_hp():
    blood = _potion("Blood Potion")

    assert blood.effect_type == "heal_percent"
    assert blood.effect_value == 0.2
