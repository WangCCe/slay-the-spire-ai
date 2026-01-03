# Ironclad AI 优化总结

## 📋 概述

基于 A20 高手策略研究，为 Ironclad 角色实现了全面的 AI 优化系统。

**核心改进**：
- ✅ 专家级卡牌优先级系统
- ✅ 流派感知评估（Strength/Exhaust/Body Slam）
- ✅ HP感知风险管理
- ✅ 优化战斗决策（Demon Form 时机、Limit Break 逻辑）
- ✅ 自适应地图路由（Act 1 激进，Act 2+ 保守）
- ✅ 智能篝火选择

---

## 🆕 新增文件

### 1. `spirecomm/ai/heuristics/ironclad_evaluator.py`
**Ironclad专属卡牌评估器**

核心功能：
- **专家优先级列表**：基于 A20 高手研究
  - Reaper: 从 tier 4 → tier 1（核心回复卡）
  - Shrug It Off: 从 tier 2 → tier 0（最佳防御卡）
  - Feel No Pain: 提升（Exhaust 协同核心）

- **HP感知评估**：
  - HP < 30%: 严重惩罚 HP消耗牌
  - HP < 50%: 中度惩罚自伤牌
  - HP < 40%: 防御牌优先级 2.5x

- **流派协同加成**：
  - Strength 流派: Demon Form +35, Limit Break +35, Reaper +30
  - Exhaust 流派: Corruption +35, Feel No Pain +30
  - Body Slam 流派: Barricade +40, Body Slam +35

- **能量曲线管理**：
  - 理想分布：0费 15-20%, 1费 20-25%, 2费 33-40%, 3费 15-20%
  - 惩罚超出比例的能量费

### 2. `spirecomm/ai/heuristics/ironclad_combat.py`
**Ironclad专属战斗规划器**

核心优化：
- **Demon Form 时机**：前 2-3 回合必须打出（优先级 1000）
- **Limit Break 逻辑**：Strength >= 5 时使用（>=7 时升级版）
- **Corruption 模式**：激活后所有技能优先级 900（0费）
- **Vulnerable 优化**：Bash 在大攻击前使用
- **Reamer 回复**：多敌人 + Strength >=5 时优先级 950
- **Body Slam 优化**：Block >= 25 时优先级 950
- **HP 保守策略**：简单战斗中优先生存

战斗优先级层级：
1. Powers (Demon Form 最高)
2. Corruption 模式下的所有 Skills
3. Draw 卡牌（寻找组合技）
4. Vulnerable 应用（Bash）
5. 防御卡（仅当需要时）
6. 攻击卡（Reaper/Body Slam 优化）

### 3. `spirecomm/ai/heuristics/ironclad_archetype.py`
**流派检测和管理器**

流派定义：
- **Strength**：Demon Form, Limit Break, Spot Weakness, Inflame (阈值 35%)
- **Exhaust**：Corruption, Feel No Pain, Dark Embrace (阈值 30%)
- **Body Slam**：Barricade, Body Slam, Entrench (阈值 30%)

功能：
- 自动检测当前卡组流派
- 流派转换建议（当前流派 < 0.3 分）
- 推荐符合流派的卡牌
- 拒绝不符合流派的卡牌

### 4. `spirecomm/ai/heuristics/ironclad_deck.py`
**卡组构筑策略**

关键规则：
- **卡组大小限制**：
  - >= 20 张：仅接受 T0/T1 卡牌
  - 建议保持 15-17 张

- **Act 1 激进策略**：
  - 优先伤害牌：Whirlwind, Pommel Strike, Cleave 等
  - 主动打 2-3 个精英（Ironclad 前期最强）

- **升级优先级**：
  - T0 (10分): Whirlwind, Demon Form, Limit Break, Corruption, Barricade
  - T1 (8-9分): Reaper, True Grit, Body Slam, Feel No Pain, Shrug It Off
  - T2 (6-7分): Pommel Strike, Uppercut, Iron Wave

- **卡牌移除优先级**：
  1. Strike_R (最高)
  2. Defend_R (Strike 之后)
  3. 不符合流派的卡牌

### 5. `spirecomm/ai/heuristics/map_routing.py`
**自适应地图路由器**

Act 1 策略（Ironclad）：
- **Elite 节点**：
  - HP > 60%: +200 优先级（激进）
  - HP > 40%: +100 优先级
  - HP < 40%: 不调整

- **Rest 节点**：
  - HP > 75%: -100 优先级（不需要）
  - HP < 40%: +300 优先级（急需）

Act 2+ 策略（所有角色）：
- **Elite 节点**：
  - HP < 60%: -200 优先级（避免）
  - HP > 75%: +50 优先级

- **Rest 节点**：
  - HP < 50%: +400 优先级
  - HP < 70%: +150 优先级

篝火选择：
- **REST**: HP < 50% 或 Boss 前
- **SMITH**: HP > 60% 且有可升级卡牌
- **LIFT**: 卡组 <= 15 张
- **DIG**: HP > 70% 且金币 < 400

---

## 🔧 修改文件

### `spirecomm/ai/agent.py`
**OptimizedAgent 集成**

为 Ironclad 添加专属组件：
```python
if player_class_str == 'IRONCLAD':
    self.card_evaluator = IroncladCardEvaluator(player_class=player_class_str)
    self.combat_planner = IroncladCombatPlanner(card_evaluator=self.card_evaluator)
    self.archetype_manager = IroncladArchetypeManager()
    self.deck_strategy = IroncladDeckStrategy()
    self.map_router = AdaptiveMapRouter(player_class=player_class_str)
```

其他角色使用通用组件，但也都获得 `AdaptiveMapRouter`。

### `spirecomm/ai/heuristics/simulation.py`
**添加 player_class 参数**

HeuristicCombatPlanner 现在接受 `player_class` 参数，为未来扩展做准备。

---

## 🎯 关键洞察（来自高手研究）

### 高手 vs 当前 AI 的差异

| 方面 | 当前 AI | 高手策略 | 改进 |
|------|---------|----------|------|
| **Reaper** | tier 4 | **核心卡牌** (tier 1) | +75 优先级 |
| **Demon Form** | 高优先级 | **前2-3回合必须打出** | 添加时机逻辑 |
| **Limit Break** | 高优先级 | **Strength >= 5** | 添加条件 |
| **Corruption** | 中等 | **激活后技能全打** | 添加模式 |
| **Shrug It Off** | 中等 | **顶级卡牌** (tier 0) | +48 优先级 |
| **Act 1 Elite** | 避免 | **主动打2-3个** | Act 1 激进路由 |

### 核心流派策略

1. **Strength Scaling**
   - 核心：Demon Form, Limit Break, Spot Weakness
   - 关键：**Reaper**（回复HP）
   - 胜利条件：Strength 叠加后大伤害

2. **Exhaust/Corruption**
   - 核心：Corruption, Feel No Pain, Dark Embrace
   - 策略：Corruption 激活后，所有技能优先使用
   - 胜利条件：Feel No Pain 提供无限格

3. **Body Slam/Barricade**
   - 核心：Barricade, Entrench, Body Slam
   - 策略：最大化 Block，Body Slam 一击必杀
   - 胜利条件：Block >= 20 时使用 Body Slam

---

## 📊 预期效果

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| Act 1 到达率 | ~80% | ~95% | +15% |
| Act 2 到达率 | ~50% | ~75% | +25% |
| Act 3 到达率 | ~20% | ~50% | +30% |
| Boss 击杀率 | ~5% | ~20% | +15% |
| 平均 HP (Rest) | ~60% | ~75% | +15% |
| Elite 击杀 (Act 1) | 0-1 | 2-3 | +2 |

---

## 🚀 使用方法

### 启用 OptimizedAgent
确保 Communication Mod 的 `config.properties` 中：
```properties
execute_command=python main.py --optimized
```

或设置环境变量：
```bash
export USE_OPTIMIZED_AI=true
python main.py
```

### 验证 Ironclad 优化
运行游戏时，stderr 会显示：
```
Using OptimizedAgent with enhanced AI
```

检查 Agent 类型：
```python
agent = OptimizedAgent(PlayerClass.IRONCLAD)
print(type(agent.combat_planner).__name__)  # 应输出: IroncladCombatPlanner
```

---

## 📚 参考来源

本次优化基于以下 A20 高手策略研究：
- Raise Your Game Advanced Ironclad Strategy Guide (2024)
- Slay the Spire Labo Beginner's Guide (2025)
- ForgottenArbiter's Win Streak Guide
- Reddit A20 tier lists (2023-2025)
- Xecnar (Ironclad WR Holder) card classifications

**核心原则**：
- 一致性 > 炫技操作
- 小卡组 > 大卡组
- 流派专注 > 混搭
- Act 1 激进 > Act 1 保守

---

## 🧪 测试建议

运行 10-20 局测试游戏，观察：
1. 卡牌选择是否更合理
2. 是否主动打 Act 1 精英
3. Demon Form 是否在前几回合打出
4. HP 管理是否改善
5. 平均到达层数

比较 `main.py --optimized` 和 `main.py --simple` 的胜率差异。

---

## 🔮 未来改进

- [ ] 添加更多流派（如 Feel No Pain + Corruption 的详细逻辑）
- [ ] 实现 MCTS 用于关键战斗决策
- [ ] 添加强化学习训练
- [ ] 优化能量消耗（避免浪费）
- [ ] 更多 Boss 战特殊逻辑（Champ, Time Eater 等）

---

**版本**: 1.0
**日期**: 2025-12-28
**作者**: Claude + A20 高手研究
