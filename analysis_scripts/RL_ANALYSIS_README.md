# RL训练分析脚本

这些脚本用于监控和分析纯RL训练的进度。

## 脚本列表

### 0. `diagnose_live_batch.py` / `diagnose_run.py` - 实战批次诊断

**功能：**
- 汇总最近一批 `.run` 文件：胜利数、最佳楼层、平均楼层、死因、卡牌奖励选择/跳过
- 扫描 `ai_debug.log` 和 `communication_mod_errors.log` 的危险信号
- 对单局输出 deck、relic、boss relic、campfire、card reward、damage taken 和末局日志窗口
- 自动匹配 `runs/ai_games.txt` 的 AI 标记；单局诊断会回退搜索 `logs_archive`

**用法：**
```bash
python analysis_scripts/diagnose_live_batch.py --game-dir D:\SteamLibrary\steamapps\common\SlayTheSpire --since 1779896308 --tail-lines 120
python analysis_scripts/diagnose_run.py 1779896509 --game-dir D:\SteamLibrary\steamapps\common\SlayTheSpire --before-seconds 90 --after-seconds 10
```

**何时使用：**
- 每次验证批次结束后，先用 `diagnose_live_batch.py` 找最佳楼层和重复死因
- 选中具体失败局后，用 `diagnose_run.py` 快速拿到这一局的可读证据包
- 机制修复前，用这两个脚本把 `.run` 证据和日志证据对齐

---

### 1. `analyze_rl_card_choices.py` - 卡牌选择分析

**功能：**
- 统计选择vs跳过的比例
- 按稀有度分析被选中的卡牌
- 显示最常被选中的卡牌TOP 10
- 分析跳过决策（是否跳过了好卡）
- 时间趋势分析（前后半段对比）

**用法：**
```bash
python analysis_scripts/analyze_rl_card_choices.py
```

**何时使用：**
- 训练过程中定期查看卡牌选择模式
- 检查是否陷入了固定策略
- 观察学习曲线

**示例输出：**
```
【选择 vs 跳过】
  选择卡牌: 9 (60.0%)
  跳过所有: 6 (40.0%)

【被选卡牌的稀有度分布】
  UNCOMMON: 5 (55.6%)
  COMMON: 3 (33.3%)
  POWER: 1 (11.1%)

【最常被选中的卡牌 TOP 10】
  1. Combust: 2次 (22.2%)
  2. Inflame: 1次 (11.1%)
  ...
```

---

### 2. `analyze_rl_training_progress.py` - 训练进度分析

**功能：**
- 统计总游戏数和胜率
- 计算平均层数和最远层数
- 显示checkpoint信息
- 战斗表现统计（回合数、伤害）
- 死因分析

**用法：**
```bash
python analysis_scripts/analyze_rl_training_progress.py
```

**何时使用：**
- 每天查看一次训练进度
- 评估整体性能提升
- 检查checkpoint是否正常生成

**示例输出：**
```
【游戏统计】
  总游戏数: 15
  胜利: 3 (20.0%)
  失败: 12
  平均层数: 8.5
  最远层数: 15

【Checkpoint信息】
  Checkpoint数量: 3
  最新: rl_combat_model_ep15.pth
  更新时间: 2026-01-30 22:45:30
  文件大小: 9.1 MB
```

---

### 3. `monitor_rl_live.py` - 实时监控

**功能：**
- 每30秒刷新一次显示
- 实时显示最新的卡牌选择
- 实时显示最近的游戏结果
- 无限循环运行，Ctrl+C停止

**用法：**
```bash
python analysis_scripts/monitor_rl_live.py
```

**何时使用：**
- 挂机训练时开着，实时了解训练状态
- 观察AI的最新决策
- 检查训练是否正常运行

**示例输出：**
```
📊 实时训练监控
================================================================================

【最近 5 次卡牌选择】
  1. ✅ Combust (UNCOMMON)
  2. ⏭️ SKIP (SKIPPED)
  3. ✅ Inflame (UNCOMMON)
  ...

选择率: 3/5 = 60.0%

【最近 2 局游戏】
  1. Floor 12 - 💀 失败
  2. Floor 8 - 💀 失败

胜率: 0/2 = 0.0%
平均层数: 10.0
```

---

## 使用建议

### 每日监控流程

1. **开启实时监控**（挂机时）
   ```bash
   python analysis_scripts/monitor_rl_live.py
   ```

2. **每天检查一次**（晚上或早晨）
   ```bash
   python analysis_scripts/analyze_rl_training_progress.py
   python analysis_scripts/analyze_rl_card_choices.py
   ```

3. **周末详细分析**
   - 查看一周的训练趋势
   - 对比不同时期的选择策略
   - 决定是否需要调整参数

### 关键指标关注

**Episode 1-100（探索期）：**
- ✅ 选择多样化，不固定模式
- ✅ 跳过率在30-60%之间
- ⚠️ 如果跳过率>80%或<20%可能需要调整

**Episode 100-500（学习期）：**
- ✅ 某些卡牌开始重复出现
- ✅ 跳过率可能趋于稳定
- ⚠️ 平均层数应该逐步提升

**Episode 500+（成熟期）：**
- ✅ 胜率应该稳定在30%以上
- ✅ 平均层数应该达到15+
- ✅ 卡牌选择有明确偏好

### 问题诊断

**问题1：跳过率过高（>80%）**
- 可能原因：奖励信号太弱
- 解决：增加`CARD_REWARD_BASE`

**问题2：选择率过高（<20%）**
- 可能原因：探索不足，过度贪婪
- 解决：增加epsilon探索率

**问题3：没有改善趋势**
- 可能原因：学习率太低
- 解决：检查训练配置，考虑调整

---

## 输出文件位置

所有分析结果直接输出到终端（stdout）。

如需保存：
```bash
python analysis_scripts/analyze_rl_card_choices.py > card_analysis.txt
```

---

## 依赖

所有脚本使用Python标准库，无需额外安装依赖。

支持Python 3.6+

---

## 日志路径配置

如果日志路径不同，修改脚本中的 `LOG_PATH` 变量：

```python
LOG_PATH = r"你的路径\ai_debug.log"
```

默认路径：
```
D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log
```
