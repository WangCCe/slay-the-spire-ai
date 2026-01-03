# A20 Ironclad 通关向：OptimizedAgent（Beam Search 出牌）优化技术文档（MD）

> 目标：显著提升 A20 战士（Ironclad）通关稳定性（尤其是精英/首领战），在不显著牺牲响应时间的前提下，提高决策质量与鲁棒性。  
> 背景：现有 OptimizedAgent 使用 Beam Search 规划 3–5 张卡的序列，配套 FastCombatSimulator + 评分函数 + 序列缓存。

---

## 1. 当前系统概览（现状复盘）

### 1.1 决策结构
- **决策协调层**：`OptimizedAgent`（带序列缓存，逐步执行）
- **搜索引擎**：`HeuristicCombatPlanner.plan_turn()`（beam search）
- **模拟器**：`FastCombatSimulator + SimulationState`（轻量状态克隆 + 预测伤害/格挡/减益）
- **评分函数**：以「伤害、击杀、生命保持、能量效率、组合加成」为主

### 1.2 当前参数（文档中的默认值）
- `beam_width=15`
- `max_depth=5 (energy=3, 单怪)`
- `min_depth=3 (energy=1 或 多怪)`

---

## 2. 关键问题（影响 A20 胜率的高优先级缺陷）

### 2.1 机制模拟偏差：Vulnerable / Weak / Frail 处理错误（必须修）
> 现有文档描述：`damage *= (1 + 0.5 * vulnerable_layers)`  
> 这与实际游戏机制不符，会导致 Beam Search 系统性高估/低估某些序列。

#### 正确机制（A20 必须对齐）
- **Vulnerable（易伤）**：持续 `n` 回合（层数=回合数），**只要 >0 就固定 ×1.5**（仅对攻击伤害）
- **Weak（虚弱）**：持续 `n` 回合，**只要 >0 就固定 ×0.75**（仅对攻击伤害）
- **Frail（脆弱）**：持续 `n` 回合，**只要 >0 就固定 ×0.75**（仅对获得格挡）

#### 修复建议（实现要点）
- 在模拟中将 “层数” 只作为 “duration” 使用：`if vulnerable > 0: mult = 1.5 else 1.0`
- Weak 同理、Frail 作用到 block gain
- 需要区分：
  - “对怪物施加的易伤/虚弱”影响本回合后续的伤害
  - “对玩家施加的脆弱”影响本回合后续的格挡

---

## 3. A20 核心优化方向：评分函数从“伤害优先”转为“生存约束优先”

### 3.1 为什么要改（核心直觉）
A20 决策的第一性原则是：  
> **在尽量少掉血/不死的前提下尽快赢**  
而不是 “本回合打出最大伤害”。

当前权重（伤害 1.0、击杀 1.5、生命 0.8）通常对 A20 不够“怕死”，会出现：
- 为了多打伤害，导致吃到明显可避免的重击
- 对多怪战，未优先完成“斩杀减少 incoming”
- 对 Boss/精英，忽视 debuff 风险和后续回合崩盘风险

### 3.2 引入 **Next-turn Survival**（强建议）
在 `evaluate_sequence()` 中显式估算 **敌方下一回合 incoming**，对 `hp_loss` 施加强惩罚：

#### 需要的指标
- `expected_incoming_damage`：基于敌方 intent 估计的下回合伤害（可先做近似）
- `hp_loss = max(0, expected_incoming_damage - player_block)`
- `death = (hp_loss >= player_hp)`

#### 建议评分结构（示例）
- 若 `death`: `score = -INF`
- 否则：`score -= hp_loss * W_DEATHRISK`
  - `W_DEATHRISK` 推荐 5~12（根据你现有 score 量级调）

#### 额外的“危险阈值”惩罚（A20 很有用）
- `if player_hp - hp_loss < danger_hp_threshold: score -= extra_penalty`
  - danger 阈值可随 Act 提升（Act3 更保守）

---

## 4. 序列缓存机制优化：智能失效（Replan Triggers）

### 4.1 问题
“规划一次，逐步执行”在以下情况会严重过时：
- 抽牌（Pommel Strike / Battle Trance / Offering / Dark Embrace 触发等）
- 生成牌（Anger / Infernal Blade / Discover 类）
- 目标变化（怪物死亡、意图变化、加入/消失）
- 能量变化（Bloodletting、Seeing Red、药水等）
- 随机结果（目标随机、抽牌堆洗切等）

继续执行旧序列 => 经常错过“抽到关键牌后的更优路线”，或执行已不合法的 action。

### 4.2 建议：缓存序列的失效条件
只要发生以下任一事件，立刻丢弃剩余序列并重新 plan：
- hand / energy / monsters_alive 变化超出预期
- 抽牌、生成牌、洗牌、随机目标发生
- 当前序列下一动作不再合法（目标死了、卡不在手、能量不足）

### 4.3 实现建议（轻量）
维护一个 `TurnPlanSignature`：
- `(hand_multiset, energy, monsters_state_signature, key_powers_flags, rng_sensitive_flag)`
每次执行前比对 signature，不一致则 replan。

---

## 5. Beam Search 工程级增强：Transposition + Dominance（省算力且提质量）

### 5.1 Transposition Table（状态去重合并）
不同动作序列可能到达相同/近似状态；不合并会浪费 beam 宽度。

#### 状态 Key 设计（建议）
`state_key` 包含：
- 玩家：`hp, block, energy, strength, vulnerable, weak, frail`
- 关键 power flags：`corruption, dark_embrace, feel_no_pain, rupture, barricade ...`
- 敌人集合：每只怪的 `hp, block, vulnerable, weak, intent_signature`
- 手牌：`multiset(card_id)`（或仅对关键牌做精细化，其他做粗粒度）

#### 策略
同一 `state_key` 只保留最高分那条路径（或保留 top2 以防评分噪声）。

### 5.2 Dominance Pruning（支配剪枝）
如果 stateA 在关键维度上全面不差于 stateB：
- `hp ≥, block ≥, energy ≥`
- 敌方总有效血量更低 / debuff 更好
- 手牌不更差（可先用近似：手牌张数+关键牌存在）
则 B 直接删。

---

## 6. 动作空间控制：两段式评分 + Progressive Widening

### 6.1 现状问题
每层扩展“所有可打牌”，在 0 费多、抽牌多时爆炸，导致：
- 深度上不去
- beam 被噪声动作挤占
- 真正强序列被淹没

### 6.2 建议：FastScore 预筛 + FullSim 精评
对每个节点的可行动作做：
1) **FastScore**：轻量估值（不 clone 全 state 或只算局部收益）
2) 只扩展前 `M` 个动作（按 FastScore 排序）
3) 对这 `M` 个动作做完整模拟 + 终评分

### 6.3 Progressive Widening（随深度收缩 M）
示例（可调）：
- depth1: `M=12`
- depth2: `M=10`
- depth3: `M=7`
- depth4: `M=5`
- depth5: `M=4`

---

## 7. 从“硬编码组合”升级为“引擎触发量化”（更稳、更泛化）

### 7.1 问题
硬编码：
- `if LimitBreak and strength>=5: +50`
- `if DemonForm: +30*count`
容易出现：
- 过拟合某些组合，忽视生存
- 在不合适的战斗/回合强行追 combo

### 7.2 建议：在模拟中记录引擎事件计数并入评分
建议 simulator 维护计数器：
- `exhaust_events`
- `cards_drawn`
- `skills_played`
- `attacks_played`
- `damage_instances`（多段触发相关）
- `energy_gained / energy_saved`

评分中加入：
- `+ exhaust_events * (FNP_value + DE_value)`
- `+ cards_drawn * draw_value`
- `+ energy_saved * energy_value`
- `+ free_skill_played * (tempo_value)`

> 这样 Second Wind / Burning Pact / Fiend Fire / Corruption 等会自然被 beam 推到正确位置。

---

## 8. 目标选择改进：从“最低 HP”转向“威胁最小化 + 斩杀收益”

### 8.1 现状问题
“单体打最低 HP”在 A20 常错，尤其多怪战：
- 应优先减少 incoming（击杀/控威胁）
- 应优先处理高威胁目标（高伤、强 debuff、成长型）

### 8.2 建议：Threat + Kill Bonus
对每只怪定义：
- `threat = expected_damage_next + debuff_threat + scaling_threat`
- `kill_bonus = big_value if can_kill_this_turn else 0`
- `effective_hp = hp + block`

选择目标优先级：
1) 能斩杀且显著降低 incoming 的目标
2) threat 最大目标
3) 再按 effective_hp 最低

---

## 9. 参数与自适应策略建议（可参考基线）

### 9.1 建议参数（配合剪枝后）
- `beam_width`：
  - Act1：12–15
  - Act2/3：18–25（有去重后可承受）
- `max_depth`：
  - 不建议仅按 “能量=3 → depth=5”
  - 建议结合：手牌可打张数、0费数量、抽牌潜力
  - 例：`depth = min(playable_count, base + extra_energy + extra_zero_cost)`

### 9.2 运行期保护（避免卡死）
- 若某回合分支爆炸：
  - 降 `M`（扩展动作数）
  - 降 depth
  - 或启用时间预算（如 80ms 超时即返回当前 best）

---

## 10. 实施路线图（推荐按收益排序）

### Phase 1（高收益 / 低风险 / 先做）
1. 修正 Vulnerable/Weak/Frail（机制对齐）
2. 评分加入 next-turn incoming / hp_loss 强惩罚（防猝死）
3. 序列缓存添加 replan triggers（抽牌/随机/目标变化即重算）

### Phase 2（胜率与性能一起涨）
4. Transposition table（状态去重）
5. 两段式动作扩展（FastScore → FullSim）+ Progressive widening

### Phase 3（更接近“真正强”的战士引擎打法）
6. 引擎事件计数（exhaust/draw/energy saved）驱动评分
7. 目标选择 threat/kill 模型

---

## 11. 建议的“验收指标”（你可以用来量化迭代）
- **A20 通关率**（主指标）
- **精英战胜率**（尤其 Act2/3）
- **平均掉血 / 每层掉血分布**（生存改动是否奏效）
- **每回合平均 plan 次数**（replan triggers 会增加次数，但应换来更稳）
- **平均决策耗时**（ms）与 99p 延迟

---

## 12. 附：建议你在代码中新增/调整的关键接口（清单）

- `SimulationState.state_key()`：用于 transposition 去重
- `Simulator.estimate_incoming_damage_next_turn()`：用于生存评分
- `Planner.fast_score_action(action, state)`：用于两段式扩展
- `Planner.should_replan(prev_signature, current_signature)`：用于缓存失效
- `Targeting.compute_threat(monster, state)`：用于目标选择

---

## 结语
这套优化的核心思想是：
- **A20 的“最优回合”不等于“最大伤害回合”**
- **正确的机制模拟 + 生存约束评分 + 合理剪枝**，能让 Beam Search 真正像高胜率玩家那样“先稳住，再赢”。

如果你把以下代码片段贴出来（不需要全文件）：
- `apply_damage / apply_block / apply_debuff`
- `evaluate_sequence`
- `get_playable_actions`（动作枚举）
我可以进一步给你出一份“按你工程结构的改动补丁草案”（函数级别、可直接抄改）。
