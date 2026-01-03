# 游戏统计和日志系统 - 维护指南

## 📍 文件位置（重要）

**关键信息**：Communication Mod 启动 Python 脚本时，工作目录是游戏安装目录，因此所有日志文件都生成在：

```
D:\SteamLibrary\steamapps\common\SlayTheSpire\
```

**项目代码目录**：
```
d:\PycharmProjects\slay-the-spire-ai\
```

## 📋 生成的日志文件

### 1. `ai_game_stats.csv`
- **格式**：CSV 表格
- **用途**：用 Excel/电子表格打开分析
- **内容**：每行一局游戏的统计数据
- **字段**：
  - game_id, player_class, ascension, victory, final_floor, final_act
  - death_cause, hp_pct
  - combats, elite_kills, boss_kills, avg_turns_per_combat, total_hp_lost
  - cards_obtained, cards_skipped
  - relics, potions_used
  - total_decisions, avg_confidence, fallback_count
  - timestamp

### 2. `ai_game_stats.jsonl`
- **格式**：JSONL（每行一个 JSON 对象）
- **用途**：程序化分析、数据导入
- **内容**：完整的游戏数据（包含嵌套的战斗详情）

### 3. `ai_debug.log`
- **格式**：纯文本日志
- **用途**：调试统计系统问题
- **内容**：
  - 统计保存过程的调试信息
  - 错误堆栈跟踪
  - 每局游戏的保存确认

## 🛠️ 分析工具

位置：`d:\PycharmProjects\slay-the-spire-ai\analyze_stats.py`

**使用前必须先 cd 到游戏目录**：
```bash
cd D:\SteamLibrary\steamapps\common\SlayTheSpire
python d:\PycharmProjects\slay-the-spire-ai\analyze_stats.py [选项]
```

**常用命令**：
```bash
# 最近 N 局统计
python d:\PycharmProjects\slay-the-spire-ai\analyze_stats.py --recent 10

# 胜率趋势
python d:\PycharmProjects\slay-the-spire-ai\analyze_stats.py --winrate-trend

# 死亡分布
python d:\PycharmProjects\slay-the-spire-ai\analyze_stats.py --death-distribution

# 平均层数
python d:\PycharmProjects\slay-the-spire-ai\analyze_stats.py --avg-floor

# 卡牌获取统计
python d:\PycharmProjects\slay-the-spire-ai\analyze_stats.py --cards

# 完整摘要
python d:\PycharmProjects\slay-the-spire-ai\analyze_stats.py --summary
```

## 🔧 核心代码文件

### 1. `spirecomm/ai/tracker.py`
**GameTracker 类** - 追踪单局游戏进度
- **初始化**：在 OptimizedAgent 创建时初始化
- **记录方法**：
  - `start_combat()` - 战斗开始
  - `end_combat()` - 战斗结束
  - `record_card_choice()` - 卡牌选择
  - `record_relic()` - 获得遗物
  - `record_game_over()` - 游戏结束
- **导出**：`to_dict()` 和 `to_csv_row()`

### 2. `spirecomm/ai/statistics.py`
**GameStatistics 类** - 跨局统计和存储
- **初始化**：在 main.py 中创建
- **存储方法**：
  - `record_game()` - 保存一局游戏到 JSONL 和 CSV
  - `_save_to_jsonl()` - 追加到 JSONL 文件
  - `_save_to_csv()` - 追加到 CSV 文件

### 3. `spirecomm/ai/agent.py`
**OptimizedAgent 集成** - 自动追踪游戏状态
- **战斗检测**：[agent.py:485-524](spirecomm/ai/agent.py#L485-L524)
  - 使用 `game_state.in_combat` 检测战斗状态变化
  - **重要**：不要使用 `ScreenType.COMBAT`（不存在）
- **卡牌选择追踪**：[agent.py:557-563](spirecomm/ai/agent.py#L557-L563)

### 4. `main.py`
**主循环** - 每局结束后保存统计
- **统计初始化**：[main.py:96-104](main.py#L96-L104)
- **统计保存**：[main.py:149-221](main.py#L149-L221)
- **调试日志**：写入 `ai_debug.log`

## 🐛 已知问题和修复

### Bug 1: 运算符优先级错误（已修复）
**位置**：[tracker.py:263](spirecomm/ai/tracker.py#L263)
**错误代码**：
```python
'duration_seconds': int((self.game_end_time or datetime.now() - self.game_start_time).total_seconds())
```
**问题**：`or` 优先级低于 `-`，导致运算顺序错误
**症状**：`AttributeError: 'datetime.datetime' object has no attribute 'total_seconds'`
**修复**：
```python
'duration_seconds': int(((self.game_end_time or datetime.now()) - self.game_start_time).total_seconds())
```

### Bug 2: 战斗检测错误（已修复）
**位置**：[agent.py:485-524](spirecomm/ai/agent.py#L485-L524)
**错误代码**：
```python
if game_state.screen_type == ScreenType.COMBAT:  # ScreenType.COMBAT 不存在！
```
**修复**：
```python
if hasattr(game_state, 'in_combat'):
    current_in_combat = game_state.in_combat
```

### Bug 3: 战斗决策数未记录（已修复）
**位置**：[agent.py:458-489](spirecomm/ai/agent.py#L458-L489)
**问题**：`OptimizedAgent` 在 `decision_history` 中记录决策，但没有调用 `game_tracker.record_decision()`
**症状**：统计中 `total_decisions` 和 `combat_decisions` 始终为 0
**修复**：在战斗规划和卡牌选择时调用 `game_tracker.record_decision()`
```python
# 记录到 game_tracker
if self.game_tracker:
    self.game_tracker.record_decision(
        decision_type='combat',  # 或 'reward'
        confidence=confidence,
        used_fallback=False
    )
```

## 📊 数据格式示例

### CSV 格式
```csv
game_id,player_class,ascension,victory,final_floor,final_act,death_cause,hp_pct,combats,elite_kills,boss_kills,avg_turns_per_combat,total_hp_lost,cards_obtained,cards_skipped,relics,potions_used,total_decisions,avg_confidence,fallback_count,timestamp
1,IRONCLAD,20,False,8,1,elite,0.25,6,1,0,2.3,45,"Bash;Strike",2,"Burning Blood",1,50,0.75,2,2025-12-29T00:00:00
```

### JSONL 格式
```json
{"game_id": 1, "player_class": "IRONCLAD", "ascension": 20, "victory": false, "final_floor": 8, "final_act": 1, "death_cause": "elite", "hp_pct": 0.25, "combats": 6, "elite_kills": 1, "boss_kills": 0, "avg_turns_per_combat": 2.3, "total_hp_lost": 45, "cards_obtained": ["Bash", "Strike"], "cards_skipped": 2, "relics": ["Burning Blood"], "potions_used": 1, "total_decisions": 50, "avg_confidence": 0.75, "fallback_count": 2, "timestamp": "2025-12-29T00:00:00"}
```

## 🔍 调试技巧

### 查看最新日志
```bash
# 实时监控调试日志
tail -f D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log

# 查看最近的游戏数据
tail -n 5 D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_game_stats.csv
```

### 快速检查是否正常工作
1. 查看 `ai_debug.log` 文件大小是否增长
2. 查看 `ai_game_stats.csv` 行数是否增加
3. 每局结束后会打印确认信息到 stderr：
   ```
   Game #N saved: WIN/LOSS at Act X Floor Y
   ```

### 如果数据没有保存
1. 检查 `ai_debug.log` 是否存在
2. 查看错误信息：
   ```bash
   cat D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log
   ```
3. 确认使用的是 OptimizedAgent（SimpleAgent 没有追踪功能）

## 📝 维护检查清单

- [ ] 定期检查日志文件大小，避免过大
- [ ] 归档旧数据（移动到其他目录）
- [ ] 使用 `analyze_stats.py` 定期分析性能趋势
- [ ] 如需修改追踪逻辑，更新 `tracker.py` 和 `agent.py`
- [ ] 如需添加新统计字段，更新 `to_dict()` 方法
- [ ] 修复 bug 时更新此文档的"已知问题"部分

## 🚀 快速开始

```bash
# 1. 启动游戏（Communication Mod 会自动运行 main.py）
# 游戏会自动开始运行 AI

# 2. 等待几局游戏完成

# 3. 查看统计（在游戏目录）
cd D:\SteamLibrary\steamapps\common\SlayTheSpire

# 4. 分析数据
python d:\PycharmProjects\slay-the-spire-ai\analyze_stats.py --summary
```

---

**最后更新**：2025-12-29
**状态**：✅ 系统已修复并正常运行
