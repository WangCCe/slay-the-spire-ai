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
    "Gremlin Looter": {
        "threat_level": 1,
        "attacks": ["single_target"],
        "special_abilities": ["steal_gold"],
        "recommended_strategy": "priority_target"
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
        "recommended_strategy": "prepare_defense"
    },
    "Hexaghost": {
        "threat_level": 3,
        "attacks": ["single_target", "AOE"],
        "special_abilities": ["phase_change"],
        "recommended_strategy": "kill_quickly"
    },
    # Elite monsters
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
    
    return threat