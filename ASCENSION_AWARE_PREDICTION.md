# Ascension-Aware Strength Prediction

## 问题发现

用户指出：**没有考虑高进阶情况下力量叠加得更快！**

这确实是一个严重的疏忽。原来的代码只使用了 `ritual_value.get('normal', 3)`，完全忽略了高进阶的调整。

## Cultist Ritual 增长机制

```json
"ritual_value": {
  "normal": 3,           // Ascension 0-1
  "ascension_2+": 4,     // Ascension 2-16
  "ascension_17+": 5     // Ascension 17+
}
```

## 实际伤害对比

| Ascension | Ritual/turn | Turn 2 | Turn 3 | Turn 4 | vs Normal |
|-----------|-------------|--------|--------|--------|-----------|
| **0-1** | +3 | 9 伤害 | 12 伤害 | 15 伤害 | baseline |
| **2-16** | **+4** | **10 伤害** | **14 伤害** | **18 伤害** | **+20%** |
| **17+** | **+5** | **11 伤害** | **16 伤害** | **21 伤害** | **+40%** |

**关键发现**：
- Ascension 17+ 的 Cultist 在 Turn 4 造成 **21 伤害**（vs Normal 的 15）
- 这是 **40% 的伤害增长**！
- 如果按 Normal 预测，会**严重低估**高进阶下的威胁

## 修复方案

### 1. 获取 Ascension Level

从 `context.game.ascension_level` 读取当前进阶等级：

```python
ascension_level = getattr(context, 'ascension_level', 0)
if hasattr(context, 'game') and hasattr(context.game, 'ascension_level'):
    ascension_level = context.game.ascension_level or 0
```

### 2. 根据 Ascension 选择 Ritual Value

```python
if isinstance(ritual_value_dict, dict):
    # Select ritual value based on ascension level
    if ascension_level >= 17:
        ritual_value = ritual_value_dict.get('ascension_17+', 5)
    elif ascension_level >= 2:
        ritual_value = ritual_value_dict.get('ascension_2+', 4)
    else:
        ritual_value = ritual_value_dict.get('normal', 3)
```

### 3. 传入 Ascension 参数

```python
predicted_strength = self._predict_future_strength(
    monster, current_turn, target_turn, current_strength, ascension_level
)
```

## 修改的文件

**spirecomm/ai/heuristics/timing/turn_classifier.py**
- `_predict_future_strength()` 添加 `ascension_level` 参数
- 根据 ascension_level 选择正确的 ritual_value
- `_calculate_damage_curve()` 获取并传递 ascension_level

## 验证结果

### Ascension 0 (Normal)
```
[RITUAL_PREDICTION] Cultist: ascension=0, ritual_value=3
Damage Curve: [9, 12, 15] ✅
```

### Ascension 10 (Mid)
```
[RITUAL_PREDICTION] Cultist: ascension=10, ritual_value=4
Damage Curve: [10, 14, 18] ✅
```

### Ascension 20 (High)
```
[RITUAL_PREDICTION] Cultist: ascension=20, ritual_value=5
Damage Curve: [11, 16, 21] ✅
```

## 影响范围

### ✅ 修复的怪物
1. **Cultist** (Act 1-3) - Ritual +3/4/5 Strength
2. **其他 Ritual 怪物**（如果有的话）

### ✅ 对 AI 决策的影响

**Ascension 0-1**：
- Cultist 威胁：中等
- 预期伤害增长：9→12→15

**Ascension 2-16**：
- Cultist 威胁：高（+20%）
- 预期伤害增长：10→14→18
- AI 会更积极进攻

**Ascension 17+**：
- Cultist 威胁：极高（+40%）
- 预期伤害增长：11→16→21
- AI 必须尽快击杀，拖延几乎等于死亡

## 游戏内测试

重启游戏后，在不同进阶下遇到 Cultist，期望看到：

### Ascension 0
```
[RITUAL_PREDICTION] Cultist: ascension=0, ritual_value=3
[TIMING_CLASSIFY] Future damage: ['9.0', '12.0', '15.0']
```

### Ascension 10
```
[RITUAL_PREDICTION] Cultist: ascension=10, ritual_value=4
[TIMING_CLASSIFY] Future damage: ['10.0', '14.0', '18.0']
```

### Ascension 20
```
[RITUAL_PREDICTION] Cultist: ascension=20, ritual_value=5
[TIMING_CLASSIFY] Future damage: ['11.0', '16.0', '21.0']
```

## 总结

感谢用户的细心发现！这个问题修复后：

1. ✅ **Normal 难度**：预测准确（9→12→15）
2. ✅ **高进阶**：预测准确（10→14→18 或 11→16→21）
3. ✅ **AI 适应性**：会根据进阶调整策略
4. ✅ **避免低估威胁**：不会因为用 A0 数据预测 A20 导致被高伤害击杀

这是一个**关键的改进**，因为高进阶下的战斗平衡完全不同！
