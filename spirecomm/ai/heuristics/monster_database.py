"""
Monster characteristic database for enhanced AI decision-making.

This module provides a database of monster characteristics, including:
- Basic information (name, ID, HP range, attack type)
- Special abilities (summon, shield, debuff, etc.)
- Attack patterns (single target, AOE, multi-hit)
- Threat level
- Recommended strategies
"""

# Monster database mapping monster IDs to their characteristics
MONSTER_DATABASE = {
    # Common Act 1 monsters
    "Louse": {
        "threat_level": 1,
        "attacks": ["single_target"],
        "special_abilities": ["none"],
        "recommended_strategy": "focus_down"
    },
    "Gremlin": {
        "threat_level": 1,
        "attacks": ["single_target"],
        "special_abilities": ["none"],
        "recommended_strategy": "aggressive"
    },
    "Gremlin Looter": {
        "threat_level": 1,
        "attacks": ["single_target"],
        "special_abilities": ["steal_gold"],
        "recommended_strategy": "priority_aggressive"
    },
    "Gremlin Nob": {
        "threat_level": 3,
        "attacks": ["single_target", "heavy_damage"],
        "special_abilities": ["buff_self"],
        "recommended_strategy": "kill_quickly"
    },
    "Gremlin Leader": {
        "threat_level": 3,
        "attacks": ["single_target", "summon"],
        "special_abilities": ["summon_gremlins"],
        "recommended_strategy": "priority_target"
    },
    "Gremlin Wizard": {
        "threat_level": 2,
        "attacks": ["single_target", "AOE"],
        "special_abilities": ["debuff"],
        "recommended_strategy": "aggressive"
    },
    "Fungi Beast": {
        "threat_level": 2,
        "attacks": ["single_target", "buff_self"],
        "special_abilities": ["gain_strength"],
        "recommended_strategy": "apply_weak"
    },
    "Jaw Worm": {
        "threat_level": 2,
        "attacks": ["single_target", "multi_hit"],
        "special_abilities": ["none"],
        "recommended_strategy": "block_and_kill"
    },
    "Sentry": {
        "threat_level": 2,
        "attacks": ["single_target", "shield"],
        "special_abilities": ["gain_block"],
        "recommended_strategy": "ignore_shield"
    },
    "Slime Boss": {
        "threat_level": 3,
        "attacks": ["single_target", "split"],
        "special_abilities": ["split_on_death"],
        "recommended_strategy": "kill_all_small"
    },
    "Lagavulin": {
        "threat_level": 4,
        "attacks": ["single_target", "heavy_damage"],
        "special_abilities": ["delay_attack"],
        "recommended_strategy": "kill_quickly"  # 速战速决，避免蓄力后的高伤害
    },
    "Hexaghost": {
        "threat_level": 3,
        "attacks": ["single_target", "AOE"],
        "special_abilities": ["phase_change", "burning"],
        "recommended_strategy": "kill_quickly"  # 速战速决，烧伤不会自然消除，自身带力量加成
    },
    # Act 1 Elite monsters
    "Slaver Blue": {
        "threat_level": 4,
        "attacks": ["single_target", "buff"],
        "special_abilities": ["buff_allies"],
        "recommended_strategy": "priority_target"
    },
    "Slaver Red": {
        "threat_level": 4,
        "attacks": ["single_target", "heavy_damage"],
        "special_abilities": ["none"],
        "recommended_strategy": "priority_target"
    },
    "Centurion": {
        "threat_level": 4,
        "attacks": ["single_target", "shield"],
        "special_abilities": ["gain_block", "buff_self"],
        "recommended_strategy": "burst_damage"
    },
    "Champ": {
        "threat_level": 5,
        "attacks": ["single_target", "AOE", "heavy_damage"],
        "special_abilities": ["gain_strength", "gain_block"],
        "recommended_strategy": "kill_quickly"
    },
    "Gremlin Giant": {
        "threat_level": 4,
        "attacks": ["single_target", "AOE"],
        "special_abilities": ["none"],
        "recommended_strategy": "focus_down"
    },
    # Act 2 common monsters
    "Book of Stabbing": {
        "threat_level": 2,
        "attacks": ["single_target", "multi_hit"],
        "special_abilities": ["none"],
        "recommended_strategy": "aggressive"
    },
    "Cultist": {
        "threat_level": 2,
        "attacks": ["single_target", "summon"],
        "special_abilities": ["summon_cultists"],
        "recommended_strategy": "priority_target"
    },
    "Sneaky Gremlin": {
        "threat_level": 2,
        "attacks": ["single_target", "weak"],
        "special_abilities": ["apply_weak"],
        "recommended_strategy": "aggressive"
    },
    "Shield and Spear": {
        "threat_level": 3,
        "attacks": ["single_target", "shield"],
        "special_abilities": ["protect_ally"],
        "recommended_strategy": "focus_spear"
    },
    # Act 2 Elite monsters
    "Mugger": {
        "threat_level": 4,
        "attacks": ["single_target", "heavy_damage"],
        "special_abilities": ["steal_gold"],
        "recommended_strategy": "kill_quickly"
    },
    "Sentry Construct": {
        "threat_level": 4,
        "attacks": ["single_target", "AOE", "shield"],
        "special_abilities": ["gain_block", "summon_sentries"],
        "recommended_strategy": "burst_damage"
    },
    "Reptomancer": {
        "threat_level": 4,
        "attacks": ["single_target", "summon"],
        "special_abilities": ["summon_snakes"],
        "recommended_strategy": "priority_target"
    },
    # Act 3 common monsters
    "Spiker": {
        "threat_level": 3,
        "attacks": ["single_target", "AOE"],
        "special_abilities": ["none"],
        "recommended_strategy": "aggressive"
    },
    "Slag Slime": {
        "threat_level": 3,
        "attacks": ["single_target", "debuff"],
        "special_abilities": ["apply_vulnerable"],
        "recommended_strategy": "kill_quickly"
    },
    # Act 3 Elite monsters
    "Chosen": {
        "threat_level": 5,
        "attacks": ["single_target", "heavy_damage", "AOE"],
        "special_abilities": ["buff_self"],
        "recommended_strategy": "kill_quickly"
    },
    "Time Eater": {
        "threat_level": 5,
        "attacks": ["single_target", "heavy_damage"],
        "special_abilities": ["slow_player"],
        "recommended_strategy": "kill_quickly"
    },
    "Donu and Deca": {
        "threat_level": 5,
        "attacks": ["single_target", "AOE", "shield"],
        "special_abilities": ["protect_ally", "gain_block"],
        "recommended_strategy": "focus_deca"
    },
    # Bosses
    "The Guardian": {
        "threat_level": 4,
        "attacks": ["single_target", "AOE", "shield"],
        "special_abilities": ["phase_change"],
        "recommended_strategy": "kill_quickly"
    },
    "The Awakened One": {
        "threat_level": 5,
        "attacks": ["single_target", "AOE", "heavy_damage"],
        "special_abilities": ["phase_change", "buff_self"],
        "recommended_strategy": "kill_quickly"
    },
    "The Heart": {
        "threat_level": 6,
        "attacks": ["single_target", "AOE", "heavy_damage"],
        "special_abilities": ["buff_self", "heal"],
        "recommended_strategy": "kill_quickly"
    },
}


def get_monster_info(monster_id):
    """
    Get monster information from the database.
    
    Args:
        monster_id: The monster ID to look up
    
    Returns:
        Dictionary of monster characteristics, or default if not found
    """
    return MONSTER_DATABASE.get(monster_id, {
        "threat_level": 2,
        "attacks": ["unknown"],
        "special_abilities": ["none"],
        "recommended_strategy": "balanced"
    })


def evaluate_monster_threat(monster, context):
    """
    Evaluate the threat level of a monster in current context.
    
    Args:
        monster: The monster object
        context: Current decision context
    
    Returns:
        Numeric threat score where higher is more dangerous
    """
    monster_info = get_monster_info(monster.monster_id)
    
    # Start with base threat level
    threat = monster_info["threat_level"]
    
    # Add threat based on current attack power
    if hasattr(monster, 'move_adjusted_damage') and monster.move_adjusted_damage > 15:
        threat += 2
    elif hasattr(monster, 'move_adjusted_damage') and monster.move_adjusted_damage > 10:
        threat += 1
    
    # Add threat based on special abilities
    if "summon" in monster_info["attacks"] or "summon" in monster_info["special_abilities"]:
        threat += 2
    if "buff_allies" in monster_info["special_abilities"]:
        threat += 2
    if "heavy_damage" in monster_info["attacks"]:
        threat += 1
    if "debuff" in monster_info["special_abilities"]:
        threat += 1
    
    # Add threat based on current HP percentage
    if context.player_hp_pct < 0.5:
        threat *= 1.5
    
    # Special handling for monsters with scaling damage
    # These monsters become more dangerous as the battle progresses
    
    # Cultist: threat increases with turn number
    # because Cultist's damage scales with Strength (gained from Ritual)
    if monster.monster_id == "Cultist" and hasattr(context, 'turn'):
        threat += context.turn
    
    # Gremlin Nob: threat increases with turn number
    # because Gremlin Nob gains Strength when using Bash
    if monster.monster_id == "Gremlin Nob" and hasattr(context, 'turn'):
        threat += context.turn * 1.5
    
    # Lagavulin: threat increases with turn number
    # because after hibernation it deals massive damage (18-22)
    if monster.monster_id == "Lagavulin" and hasattr(context, 'turn'):
        threat += context.turn * 2
    
    return threat