# Potion effect metadata lookup table.
# Values are based on the local StSExporter potion export.
POTION_EFFECTS = {
    "Ancient Potion": {"effect_type": "artifact", "effect_value": 1, "target_type": "self"},
    "Attack Potion": {"effect_type": "card_choice_attack", "effect_value": 0, "target_type": "none"},
    "Blessing of the Forge": {"effect_type": "upgrade_hand", "effect_value": 0, "target_type": "self"},
    "Block Potion": {"effect_type": "block", "effect_value": 12, "target_type": "self"},
    "Blood Potion": {"effect_type": "heal_percent", "effect_value": 0.2, "target_type": "self"},
    "Bottled Miracle": {"effect_type": "add_miracle", "effect_value": 2, "target_type": "self"},
    "Colorless Potion": {"effect_type": "card_choice_colorless", "effect_value": 0, "target_type": "none"},
    "Cultist Potion": {"effect_type": "ritual", "effect_value": 1, "target_type": "self"},
    "Cunning Potion": {"effect_type": "add_shiv", "effect_value": 3, "target_type": "self"},
    "Dexterity Potion": {"effect_type": "buff_dexterity", "effect_value": 2, "target_type": "self"},
    "Distilled Chaos": {"effect_type": "play_top_cards", "effect_value": 3, "target_type": "self"},
    "Duplication Potion": {"effect_type": "duplicate_next_card", "effect_value": 1, "target_type": "self"},
    "Elixir": {"effect_type": "exhaust_hand_select", "effect_value": 0, "target_type": "self"},
    "Energy Potion": {"effect_type": "energy", "effect_value": 2, "target_type": "self"},
    "Entropic Brew": {"effect_type": "fill_potion_slots", "effect_value": 0, "target_type": "self"},
    "Essence of Steel": {"effect_type": "plated_armor", "effect_value": 4, "target_type": "self"},
    "Explosive Potion": {"effect_type": "damage", "effect_value": 10, "target_type": "all_monsters"},
    "Fairy in a Bottle": {"effect_type": "fairy", "effect_value": 0.3, "target_type": "self"},
    "Fear Potion": {"effect_type": "debuff_vulnerable", "effect_value": 3, "target_type": "monster"},
    "Fire Potion": {"effect_type": "damage", "effect_value": 20, "target_type": "monster"},
    "Flex Potion": {"effect_type": "temp_strength", "effect_value": 5, "target_type": "self"},
    "Focus Potion": {"effect_type": "buff_focus", "effect_value": 2, "target_type": "self"},
    "Fruit Juice": {"effect_type": "max_hp", "effect_value": 5, "target_type": "self"},
    "Gambler's Brew": {"effect_type": "discard_draw", "effect_value": 0, "target_type": "self"},
    "Ghost in a Jar": {"effect_type": "intangible", "effect_value": 1, "target_type": "self"},
    "Heart of Iron": {"effect_type": "metallicize", "effect_value": 6, "target_type": "self"},
    "Liquid Bronze": {"effect_type": "thorns", "effect_value": 3, "target_type": "self"},
    "Liquid Memories": {"effect_type": "return_discard_card", "effect_value": 1, "target_type": "self"},
    "Poison Potion": {"effect_type": "poison", "effect_value": 6, "target_type": "monster"},
    "Potion Of Capacity": {"effect_type": "orb_slots", "effect_value": 2, "target_type": "self"},
    "Power Potion": {"effect_type": "card_choice_power", "effect_value": 0, "target_type": "none"},
    "Regen Potion": {"effect_type": "regen", "effect_value": 5, "target_type": "self"},
    "Skill Potion": {"effect_type": "card_choice_skill", "effect_value": 0, "target_type": "none"},
    "Smoke Bomb": {"effect_type": "escape", "effect_value": 0, "target_type": "none"},
    "Snecko Oil": {"effect_type": "draw_randomize_cost", "effect_value": 5, "target_type": "self"},
    "Speed Potion": {"effect_type": "temp_dexterity", "effect_value": 5, "target_type": "self"},
    "Stance Potion": {"effect_type": "stance_choice", "effect_value": 0, "target_type": "self"},
    "Strength Potion": {"effect_type": "buff_strength", "effect_value": 2, "target_type": "self"},
    "Swift Potion": {"effect_type": "draw", "effect_value": 3, "target_type": "self"},
    "Weak Potion": {"effect_type": "debuff_weak", "effect_value": 3, "target_type": "monster"},
}


def _compact_identifier(value):
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


POTION_EFFECTS_BY_ID = {
    _compact_identifier(name): effects for name, effects in POTION_EFFECTS.items()
}


def _potion_effect_data(potion_id, name):
    for value in (name, potion_id):
        if value in POTION_EFFECTS:
            return POTION_EFFECTS[value]
        compact_value = _compact_identifier(value)
        if compact_value in POTION_EFFECTS_BY_ID:
            return POTION_EFFECTS_BY_ID[compact_value]
    return {"effect_type": "utility", "effect_value": 0, "target_type": "none"}


class Potion:

    def __init__(self, potion_id, name, can_use, can_discard, requires_target, price=0):
        self.potion_id = potion_id
        self.name = name
        self.can_use = can_use
        self.can_discard = can_discard
        self.requires_target = requires_target
        self.price = price

        # Look up effect metadata
        effect_data = _potion_effect_data(potion_id, name)
        self.effect_type = effect_data["effect_type"]
        self.effect_value = effect_data["effect_value"]
        self.target_type = effect_data["target_type"]

    def __eq__(self, other):
        # Handle case where other is not a Potion object (e.g., primitive type)
        if not hasattr(other, 'potion_id'):
            return False
        return other.potion_id == self.potion_id

    @classmethod
    def from_json(cls, json_object):
        return cls(
            potion_id=json_object.get("id"),
            name=json_object.get("name"),
            can_use=json_object.get("can_use", False),
            can_discard=json_object.get("can_discard", False),
            requires_target=json_object.get("requires_target", False),
            price=json_object.get("price", 0)
        )
