# Slay the Spire RL Reward Function Specification

本着重定义了基于 **Ironclad (铁甲战士)** 的强化学习奖励函数。设计目标是防止 Agent 陷入“刷伤害”或“无脑出牌”的局部最优解，同时引导其学习高效的杀敌与防御策略。

## 1. 核心奖励配置 (Configuration)

### 1.1 战斗奖励 (Combat Rewards)
| 奖励项 | 数值/公式 | 说明 |
| :--- | :--- | :--- |
| **有效伤害 (Effective Dmg)** | `dmg * 0.05` | **关键修改**：只计算不超过怪物剩余血量的伤害。防止刷分。 |
| **击杀怪物 (Kill)** | `base / (1 + kill_index)` | `base=10`，每场战斗内递减。 |
| **战斗胜利 (All Cleared)** | `+20.0` | 战斗结束的额外奖励。 |
| **HP 损失 (HP Loss)** | `-50.0 * (loss / max_hp)` | 高权重惩罚。鼓励保持血线。 |
| **回合消耗 (Time Step)** | `-0.05` | 轻微惩罚，避免无意义拖延。 |

### 1.2 行为引导 (Action Shaping) - 已精简
| 奖励项 | 数值 | 说明 |
| :--- | :--- | :--- |
| **打出卡牌** | `0.0` | **已移除**：避免“为了出牌而出牌” (如打出自燃、乱吃药)。 |
| **使用药水** | `0.0` | **已移除**：同上。 |
| **空过惩罚** | `0.0` | **已移除**：允许 Agent 在需要时空过 (Skip) 以保留手牌或避免反伤。 |
| **敌方成长惩罚** | `-1.0 * str_gained` | 针对邪教徒/拜人，迫使优先击杀。 |

### 1.3 铁甲战士特有奖励 (Ironclad Specifics)
| 奖励项 | 数值 | 说明 |
| :--- | :--- | :--- |
| **力量成长 (Strength)** | `+0.5 * str_gained` | 引导学习《活动肌肉》、《观察弱点》等成长体系。 |
| **易伤利用 (Vulnerable)** | `dmg * 0.08` | 若目标有易伤，伤害奖励系数由 0.05 提升至 0.08。引导连招。 |

### 1.4 全局/终局奖励 (Global/Terminal)
| 奖励项 | 数值 | 说明 |
| :--- | :--- | :--- |
| **胜利 (Win Run)** | `+500.0` | 最高优先级。 |
| **失败 (Death)** | `-200.0` | |
| **楼层推进 (Floor)** | `+3.0` | |
| **精英击杀 (Elite)** | `+20.0` | |
| **Boss 击杀** | `+72.0` | |

---

## 2. 逻辑实现伪代码 (Implementation Logic)

```python
def calculate_reward(prev_state, curr_state, action_type):
    reward = 0.0
    
    # --- 1. 生存惩罚 ---
    hp_loss = prev_state.hp - curr_state.hp
    if hp_loss > 0:
        reward -= 50.0 * (hp_loss / prev_state.max_hp)
        
    # --- 2. 进攻收益 (防刷分逻辑) ---
    # 基于怪物血量变化计算有效伤害 (不计溢出)
    total_dmg = 0
    vuln_dmg = 0
    for monster in prev_state.monsters:
        last_hp = monster.current_hp
        curr_hp = curr_state.get_hp(monster.monster_index)
        if curr_hp < last_hp:
            dmg = last_hp - curr_hp
            total_dmg += dmg
            if monster.has_vulnerable:
                vuln_dmg += dmg
    if total_dmg > 0:
        reward += total_dmg * 0.05
        reward += vuln_dmg * 0.03

    # --- 4. 击杀与通关 ---
    monsters_killed = prev_state.killed_monsters_in_step(curr_state)
    for i in range(monsters_killed):
        reward += 10.0 / (1 + i)

    if curr_state.combat_won:
        reward += 20.0
        
    # --- 5. 终局奖励 ---
    if curr_state.game_over:
        reward += 500.0 if curr_state.run_victory else -200.0

    # --- 6. 铁甲战士特色 ---
    str_gain = curr_state.player_strength - prev_state.player_strength
    if str_gain > 0:
        reward += 0.5 * str_gain

    # --- 7. 敌方力量成长惩罚 ---
    enemy_str_gain = curr_state.total_enemy_strength - prev_state.total_enemy_strength
    if enemy_str_gain > 0:
        reward -= 1.0 * enemy_str_gain

    # --- 8. 步长惩罚 ---
    if curr_state.turn > prev_state.turn:
        reward -= 0.05

    return reward
```

---

## 3. 风险回避指南 (Pitfalls Avoidance)

1.  **刷伤害 (Damage Farming)**:
    * **现象**: 面对无威胁怪物不杀，故意拖回合数刷伤害分。
    * **对策**: 使用较小 `回合惩罚 (-0.05)` 作为轻微约束；若发现拖延，可逐步上调。

2.  **多动症 (Action Bias)**:
    * **现象**: 满血时乱吃药，满能量时打出无意义的卡。
    * **对策**: 坚决不给“Play Card”和“Use Potion”固定正向奖励。

3.  **自杀式进攻 (Suicide Attack)**:
    * **现象**: 为了拿击杀奖励(+10)而不顾自己死活。
    * **对策**: 提高 HP Loss 的权重。在进阶模式中，保血比杀怪更重要。
