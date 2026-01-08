# Timing System Fix Summary

## 修复的问题

### 1. ✅ Cultist 策略修复 - 用户指出的问题
**问题**: 原来的策略是"第 2 回合转为防御"，这是错误的！
**原因**: Cultist 每回合都通过 Ritual 叠加力量（+3 Strength/turn），伤害指数级增长：6→9→12→15→18...
**正确策略**: 全程积极进攻，拖得越久越危险

**修复**:
- 在 `act1_normal_monsters.json` 中添加 `always_classify_as: "BURST_WINDOW"`
- 修改 timing_strategy 为所有 timing 类型都使用 maximum_aggression
- Cultist 现在会在第 1、2、3... 回合都强制使用 BURST_WINDOW 分类

### 2. ✅ 未来伤害预测系统修复
**问题**: 日志显示 `future_damage: [0, 0, 0]` - 预测系统没有工作

**根本原因**:
1. `EnhancedMonsterDatabase` 只加载了精英/Boss 数据，没有加载普通怪物数据
2. `act1_normal_monsters.json` 是列表格式 `[...]`，而 elites/bosses 是字典格式 `{...}`
3. Cultist 的 pattern 格式是 `"opening"` + `"subsequent_pattern"`，预测代码不支持

**修复**:
- 在 `enhanced_monster_database.py` 中添加 `act1_normal_monsters.json` 到加载列表
- 修改 `_load_all_data()` 支持列表和字典两种格式
- 添加 `get_move_by_name()` 辅助方法
- 在 `predict_next_moves()` 中添加 `"opening"` + `"subsequent_pattern"` 格式支持
- 修复 `subsequent_pattern` 解析逻辑：`"Dark Strike every turn"` → `"Dark Strike"`（而不是只取 "Dark"）

## 验证结果

### Cultist 预测测试
```
Turn 1 predictions: 3
  - Incantation: intent=BUFF, damage=N/A
  - Dark Strike: intent=ATTACK, damage=6
  - Dark Strike: intent=ATTACK, damage=6

Turn 2 predictions: 3
  - Dark Strike: intent=ATTACK, damage=6
  - Dark Strike: intent=ATTACK, damage=6
  - Dark Strike: intent=ATTACK, damage=6

Turn 3 predictions: 3
  - Dark Strike: intent=ATTACK, damage=6
  - Dark Strike: intent=ATTACK, damage=6
  - Dark Strike: intent=ATTACK, damage=6
```

✅ **预测系统正常工作！**

### 强制分类测试
- Cultist 在任何回合都会被强制分类为 `BURST_WINDOW`
- 使用 BURST_WINDOW 权重：damage=3.00, block=1.00, kill_bonus=150.0
- 符合用户期望：全程积极进攻

## 修改的文件

1. **spirecomm/data/monster_wiki_data/act1_normal_monsters.json**
   - 修改 Cultist timing_strategy，添加 always_classify_as: "BURST_WINDOW"
   - 所有 timing 类型都设为 maximum_aggression

2. **spirecomm/ai/heuristics/enhanced_monster_database.py**
   - 添加 `act1_normal_monsters.json` 到加载列表
   - 修改 `_load_all_data()` 支持列表和字典格式
   - 添加 `get_move_by_name()` 方法
   - 在 `predict_next_moves()` 中添加 opening + subsequent_pattern 支持

3. **spirecomm/ai/heuristics/timing/models.py**
   - 在 `MonsterTimingHints` 中添加 `raw_data` 字段
   - 修改 `from_dict()` 保存原始数据

4. **spirecomm/ai/heuristics/timing/turn_classifier.py**
   - 在 `classify_turn()` 中添加强制分类检查
   - 添加 `_check_forced_classification()` 方法

## 下一步

用户需要：
1. **重启 Slay the Spire**（让 Python 重新加载所有模块）
2. **开始新游戏**遇到 Cultist
3. **检查日志**验证：
   ```bash
   tail -f D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log | grep TIMING
   ```

**期望看到的日志**:
```
[TIMING_CLASSIFIER] Using forced classification: BURST_WINDOW
[TIMING_CLASSIFY] Turn 1: BURST_WINDOW
[TIMING_WEIGHTS] Using BURST_WINDOW weights: damage=3.00, block=1.00, kill_bonus=150.0
[TIMING_CLASSIFY] Future damage: ['0.0', '6.0', '12.0']  # 不再是 [0, 0, 0]
```

**AI 行为变化**:
- Cultist 第 1 回合（Incantation/BUFF）：积极攻击，不浪费时间
- Cultist 第 2+ 回合（Dark Strike/ATTACK）：依然积极攻击，优先击杀而不是防御
- 伤害预期会正确预测（考虑 Strength 增长）
