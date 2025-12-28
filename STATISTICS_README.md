# AI 游戏统计系统

## 概述

已成功实现完整的游戏进度追踪和统计系统，用于评估 AI 改进效果。

## 功能特性

### 自动记录（无需人工干预）
- ✅ 每局游戏自动保存到 JSONL 和 CSV 文件
- ✅ 详细记录战斗、卡牌选择、遗物、决策质量
- ✅ 控制台输出简洁确认信息
- ✅ 不影响 AI 决策速度

### 记录的数据

#### 基本信息
- 游戏ID、角色、进阶等级
- 胜负、最终层数、分数
- 游戏时间戳

#### 进度追踪
- 战斗次数、精英击杀数、Boss击杀数
- 平均战斗回合数
- 总HP损失

#### 死亡信息
- 死亡地点（层数、章节）
- 死亡原因（精英、Boss、普通怪物、事件）
- 死亡时HP百分比

#### 卡牌和遗物
- 获得的卡牌列表
- 跳过的卡牌数量
- 获得的遗物列表
- 使用的药剂数量

#### 决策质量
- 总决策次数
- 战斗决策次数
- 平均置信度
- Fallback次数

## 生成的文件

### 1. `ai_game_stats.jsonl`
**格式**: JSONL（每行一个JSON对象）
**用途**: 详细日志记录

示例：
```json
{
  "game_id": 1735372800,
  "player_class": "IRONCLAD",
  "ascension": 20,
  "victory": false,
  "final_floor": 8,
  "final_act": 1,
  "death_cause": "elite",
  "hp_pct": 0.25,
  "combats": 6,
  "elite_kills": 1,
  "boss_kills": 0,
  "avg_turns_per_combat": 2.3,
  "total_hp_lost": 45,
  "cards_obtained": ["Bash", "Strike"],
  "cards_skipped": 2,
  "relics": ["Burning Blood"],
  "potions_used": 1,
  "total_decisions": 50,
  "combat_decisions": 30,
  "avg_confidence": 0.75,
  "fallback_count": 2,
  "timestamp": "2025-12-28T22:00:00"
}
```

### 2. `ai_game_stats.csv`
**格式**: CSV（逗号分隔值）
**用途**: Excel/电子表格分析

列：
```
game_id, player_class, ascension, victory, final_floor, final_act,
death_cause, hp_pct, combats, elite_kills, boss_kills, avg_turns,
total_hp_lost, cards_obtained, cards_skipped, relics, potions_used,
total_decisions, avg_confidence, fallback_count, timestamp
```

## 使用分析工具

### 命令行工具：`analyze_stats.py`

#### 查看最近N局游戏
```bash
python analyze_stats.py --recent 20
```

输出示例：
```
================================================================================
RECENT 20 GAMES
================================================================================

Total Games: 20
Wins: 3
Win Rate: 15.0%
Avg Floor: 9.5

Game   Result   Act   Floor   Cause      HP%    Turns
--------------------------------------------------------------------------------
1      LOSS     1     8       elite      25%    2.3
2      LOSS     1     12      boss       0%     3.1
3      WIN      3     55      N/A        45%    2.8
...
```

#### 查看胜率趋势
```bash
python analyze_stats.py --winrate-trend
```

显示滚动平均胜率（默认10局窗口）

#### 查看死亡分布
```bash
python analyze_stats.py --death-distribution
```

输出示例：
```
================================================================================
DEATH DISTRIBUTION
================================================================================

Cause           Count      Percentage
--------------------------------------------------------------------------------
elite           8          40.0% ████████████
monster         6          30.0% ████████
boss            4          20.0% ██████
event           2          10.0% ██
```

#### 查看层数统计
```bash
python analyze_stats.py --avg-floor
```

显示：
- 平均到达层数
- 各章节到达率
- 死亡层数分布

#### 查看卡牌选择
```bash
python analyze_stats.py --cards
```

显示最常选择的卡牌

#### 查看完整统计摘要
```bash
python analyze_stats.py --summary
```

#### 指定日志文件
```bash
python analyze_stats.py --log-file custom_stats.jsonl --recent 10
```

## 控制台输出

### 游戏启动时
```
Using OptimizedAgent with enhanced AI
Statistics tracking enabled
  Logging to: ai_game_stats.jsonl
  CSV export: ai_game_stats.csv
```

### 每局结束后
```
Game #10 saved: LOSS at Act 1 Floor 8

Game Summary:
  Total Decisions: 50
  Combat Decisions: 30
  Card Rewards: 5
  Avg Confidence: 0.75

Deck Statistics:
  Size: 12
  Archetype: strength
  Quality: 0.68
  Upgrade Rate: 25.00%
```

## 工作原理

### 集成点

1. **OptimizedAgent 初始化**
   - 创建 `GameTracker` 实例
   - 初始化追踪状态变量

2. **战斗检测** (`get_next_action_in_game`)
   - 检测 COMBAT 屏幕转换 → 记录战斗开始
   - 检测离开 COMBAT 屏幕 → 记录战斗结束
   - 追踪遗物获得

3. **卡牌选择** (`choose_card_reward`)
   - 记录选择的卡牌
   - 记录跳过的数量

4. **药剂使用** (`use_next_potion`)
   - 记录药剂使用次数

5. **游戏结束** (`main.py` 主循环)
   - 记录胜负状态
   - 保存到 JSONL 和 CSV
   - 输出确认信息

## 文件结构

```
slay-the-spire-ai/
├── spirecomm/
│   └── ai/
│       ├── tracker.py          # GameTracker 类（~260 行）
│       ├── statistics.py       # GameStatistics 类（~280 行）
│       └── agent.py            # 集成 tracker（修改 ~60 行）
├── analyze_stats.py            # 分析工具（~290 行）
├── main.py                     # 主循环集成（修改 ~30 行）
├── ai_game_stats.jsonl         # 自动生成
└── ai_game_stats.csv           # 自动生成
```

## 性能影响

- **CPU**: 可忽略（异步保存）
- **内存**: ~1KB/游戏（仅在内存中保留游戏进行中的数据）
- **磁盘**: ~500 bytes/游戏（JSONL格式）

## 故障排除

### 问题：统计数据未保存

**检查**：
1. 确认使用 `--optimized` 参数启动
2. 检查 stderr 是否有 "Statistics tracking enabled"
3. 确认没有导入错误

### 问题：CSV 文件乱码

**解决**：使用 UTF-8 编码打开

### 问题：分析工具报错

**检查**：
1. 确认 `ai_game_stats.jsonl` 存在
2. 确认文件格式正确（每行一个JSON对象）
3. 运行 `python analyze_stats.py --summary` 测试

## 下一步建议

1. **运行10-20局游戏** 收集初始数据
2. **使用分析工具** 识别薄弱环节
3. **针对性改进** AI 策略
4. **对比数据** 验证改进效果

## 示例工作流

```bash
# 1. 启动游戏（Communication Mod 会自动运行）
# 配置: command=python "d:\\PycharmProjects\\slay-the-spire-ai\\main.py" --optimized -a 20

# 2. 等待10-20局完成...

# 3. 分析数据
python analyze_stats.py --summary        # 总体统计
python analyze_stats.py --recent 20      # 最近20局
python analyze_stats.py --death-distribution  # 死亡分布
python analyze_stats.py --winrate-trend  # 胜率趋势
python analyze_stats.py --cards          # 卡牌选择

# 4. 在 Excel 中打开 CSV 进行深入分析
# 文件: ai_game_stats.csv
```

## 技术细节

### GameTracker 类

**关键方法**：
- `start_combat(floor, act, room_type)` - 记录战斗开始
- `end_combat(hp_remaining, max_hp)` - 记录战斗结束
- `record_card_choice(chosen, skipped, available)` - 记录卡牌选择
- `record_relic(relic_id)` - 记录遗物
- `record_potion_use()` - 记录药剂使用
- `record_game_over(victory, final_state)` - 记录游戏结束
- `to_dict()` - 导出为字典
- `to_csv_row()` - 导出为CSV行

### GameStatistics 类

**关键方法**：
- `record_game(tracker)` - 记录一局游戏
- `get_recent_games(n)` - 获取最近N局
- `get_win_rate(n)` - 计算胜率
- `get_death_distribution()` - 获取死亡分布
- `get_summary()` - 获取统计摘要

## 数据完整性保证

- ✅ 所有写入操作都有异常处理
- ✅ 写入失败不影响游戏进行
- ✅ CSV 和 JSONL 同步更新
- ✅ 自动创建文件和表头

---

**系统已准备就绪！** 🎮📊

启动游戏即可开始自动收集统计数据。
