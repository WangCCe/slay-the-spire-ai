# Potion effect metadata lookup table
# Maps potion IDs to their effect types and values
POTION_EFFECTS = {
    "Fire Potion": {"effect_type": "damage", "effect_value": 20, "target_type": "monster"},
    "Explosive Potion": {"effect_type": "damage", "effect_value": 10, "target_type": "all_monsters"},  # Actually deals 10 to all
    "Poison Potion": {"effect_type": "damage", "effect_value": 6, "target_type": "monster"},  # Applies 6 poison
    "Bottle Lightning": {"effect_type": "damage", "effect_value": 15, "target_type": "monster"},
    "Bottle Flame": {"effect_type": "damage", "effect_value": 15, "target_type": "monster"},
    "Bottle Tornado": {"effect_type": "damage", "effect_value": 6, "target_type": "monster"},  # 6 damage + vulnerable
    "Attack Potion": {"effect_type": "damage", "effect_value": 15, "target_type": "monster"},
    "Gambler's Bottle": {"effect_type": "utility", "effect_value": 0, "target_type": "none"},  # Generates random attack
    "Ghost in a Jar": {"effect_type": "damage", "effect_value": 20, "target_type": "monster"},  # Ethereal deals 20 twice
    "Liquid Memories": {"effect_type": "utility", "effect_value": 0, "target_type": "none"},  # Returns a card to hand

    # Healing potions
    "Healing Potion": {"effect_type": "heal", "effect_value": 10, "target_type": "self"},
    "Fruit Juice": {"effect_type": "heal", "effect_value": 5, "target_type": "self"},
    "Strawberry": {"effect_type": "heal", "effect_value": 10, "target_type": "self"},
    "Apple": {"effect_type": "heal", "effect_value": 5, "target_type": "self"},
    "Bottled Miracle": {"effect_type": "heal", "effect_value": 20, "target_type": "self"},  # Actually 20% max HP

    # Block potions
    "Block Potion": {"effect_type": "block", "effect_value": 12, "target_type": "self"},
    "Bottled Spirit": {"effect_type": "block", "effect_value": 12, "target_type": "self"},  # Ethereal block

    # Buff potions
    "Strength Potion": {"effect_type": "buff_strength", "effect_value": 2, "target_type": "self"},
    "Dexterity Potion": {"effect_type": "buff_dexterity", "effect_value": 2, "target_type": "self"},
    "Berserk": {"effect_type": "buff_strength", "effect_value": 2, "target_type": "self"},  # +2 Strength, -1 HP per turn
    "Essence of Steel": {"effect_type": "buff_thorns", "effect_value": 3, "target_type": "self"},  # Actually gains 3 artifact
    "Artifact Potion": {"effect_type": "buff_artifact", "effect_value": 1, "target_type": "self"},

    # Debuff potions
    "Weak Potion": {"effect_type": "debuff_weak", "effect_value": 3, "target_type": "monster"},
    "Vulnerability Potion": {"effect_type": "debuff_vulnerable", "effect_value": 2, "target_type": "monster"},

    # Utility potions
    "Energy Potion": {"effect_type": "energy", "effect_value": 2, "target_type": "self"},
    "Entropic Brew": {"effect_type": "utility", "effect_value": 0, "target_type": "none"},  # Random effect
    "Smoking Bowl": {"effect_type": "utility", "effect_value": 0, "target_type": "none"},  # Exhaust all curses
    "Fear Potion": {"effect_type": "debuff_weak", "effect_value": 3, "target_type": "monster"},  # Vulnerable+Weak+Frail
    "Regen Potion": {"effect_type": "heal", "effect_value": 5, "target_type": "self"},  # 5 HP at end of turn for 3 turns
    "Fairy Potion": {"effect_type": "heal", "effect_value": 10, "target_type": "self"},  # Prevents death, heals 10
    "SnP Potion": {"effect_type": "utility", "effect_value": 0, "target_type": "none"},  # Smoke Bomb and Dagger
    "Speed Potion": {"effect_type": "draw", "effect_value": 3, "target_type": "self"},  # Draw 3, cost 0
    "Distilled Chaos": {"effect_type": "utility", "effect_value": 0, "target_type": "none"},  # Random colorless card
    "Snecko Oil": {"effect_type": "utility", "effect_value": 0, "target_type": "none"},  # Random cost change
    "Chaos Potion": {"effect_type": "damage", "effect_value": 0, "target_type": "random"},  # Random effect
}


class Potion:

    def __init__(self, potion_id, name, can_use, can_discard, requires_target, price=0):
        self.potion_id = potion_id
        self.name = name
        self.can_use = can_use
        self.can_discard = can_discard
        self.requires_target = requires_target
        self.price = price

        # Look up effect metadata
        effect_data = POTION_EFFECTS.get(name, {"effect_type": "utility", "effect_value": 0, "target_type": "none"})
        self.effect_type = effect_data["effect_type"]
        self.effect_value = effect_data["effect_value"]
        self.target_type = effect_data["target_type"]

    def __eq__(self, other):
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
