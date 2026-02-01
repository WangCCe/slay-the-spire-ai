# Slay the Spire RL Action Space Specification

本指南定义了基于 `Communication Mod` 的《杀戮尖塔》强化学习模型的动作空间（Action Space）。设计遵循原版游戏逻辑，总维度为 **133**。

## 1. 动作空间概览 (Summary)

| 模块分类 | 描述 | 维度 (Size) | 偏移量 (Offset) | 索引区间 (Index) |
| :--- | :--- | :---: | :---: | :---: |
| **PLAY_CARD** | 打出卡牌 (10张牌 × 6目标) | 60 | 0 | 0 – 59 |
| **USE_POTION** | 使用药水 (5槽位 × 6目标) | 30 | 60 | 60 – 89 |
| **END_TURN** | 结束回合 | 1 | 90 | 90 |
| **REWARD** | 选取奖励卡/战利品 | 5 | 91 | 91 – 95 |
| **MAP** | 选择地图路径 | 6 | 96 | 96 – 101 |
| **EVENT** | 事件选项选择 | 6 | 102 | 102 – 107 |
| **SHOP** | 商店购买动作 | 15 | 108 | 108 – 122 |
| **REST** | 休息处(篝火)选项 | 6 | 123 | 123 – 128 |
| **SYSTEM** | 系统控制 (Confirm/Leave等) | 4 | 129 | 129 – 132 |

**Total Dimension: 133**

---

## 2. 详细映射逻辑 (Mapping Logic)

### 2.1 战斗动作 (Combat Actions)
为了处理目标选择，我们对卡牌和药水使用统一的“目标偏移坐标系”。
- **Target Index 定义**:
  - `0`: 无目标、全体目标、或作用于自身。
  - `1 - 5`: 场上从左往右对应的怪物目标。

#### 打出卡牌 (Index: 0 - 59)
公式: `Index = (Card_Slot * 6) + Target_Index`
- *Card_Slot*: 0 – 9 (对应手牌上限 10 张)

#### 使用药水 (Index: 60 - 89)
公式: `Index = 60 + (Potion_Slot * 6) + Target_Index`
- *Potion_Slot*: 0 – 4 (对应药水腰带上限 5 槽)

### 2.2 休息处动作 (Rest Options)
对应 Index 123 – 128，索引固定如下：
- `123`: Rest (休息)
- `124`: Smith (锻造)
- `125`: Toke (除草 - 平和烟斗)
- `126`: Dig (挖掘 - 铁铲)
- `127`: Lift (举重 - 壶铃)
- `128`: Recall (回忆 - 红宝石钥匙)

### 2.3 系统动作 (System Actions)
对应 Index 129 – 132，用于处理界面跳转：
- `129`: Confirm (确认)
- `130`: Cancel (取消)
- `131`: Leave (离开界面)
- `132`: Proceed (继续/继续点击)

---

## 3. 实现指南 (Implementation Notes)

### 3.1 动作掩码 (Action Masking)
由于模型在绝大多数时刻只有少数动作合法，必须通过 `Communication Mod` 返回的 `available_commands` 生成布尔型掩码向量：
- 在计算验证层（Softmax）之前，将非法动作的 Logits 设为 -inf。
- 这对于在有限显存（如 3060 6GB）下加快模型收敛至关重要。

### 3.2 状态空间对齐 (Observation Alignment)
为了配合上述动作空间，状态空间（Observation Space）应采用 Padding 策略：
- **怪物信息**: 始终提供 5 个怪物的特征位，若怪不满 5 个，其余位置填 0。
- **手牌信息**: 始终提供 10 张卡牌的特征位。
