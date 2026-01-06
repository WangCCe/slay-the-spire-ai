# ai-combat Specification Delta

## ADDED Requirements

### Requirement: Target Exploration in Beam Search

The beam search combat planner SHALL explore target choices for single-target attack and debuff cards, not just card sequences. Target exploration SHALL be applied conditionally to balance search quality with performance constraints.

#### Scenario: Target exploration enabled

- **GIVEN** 3 monsters alive [Boss(20HP), MinionA(10HP), MinionB(10HP)]
- **AND** hand has 3 playable cards
- **AND** beam search time budget < 60ms
- **WHEN** planning turn with Iron Wave (5 dmg) and Heavy Blade (14 dmg)
- **THEN** beam search SHALL explore both:
  - Sequence 1: Iron Wave→MinionA, Heavy Blade→MinionB (kills both)
  - Sequence 2: Iron Wave→Boss, Heavy Blade→Boss (leaves minions alive)
- **AND** SHALL select the sequence with higher outcome score

#### Scenario: Target exploration disabled (too many monsters)

- **GIVEN** 5 monsters alive
- **WHEN** planning turn
- **THEN** beam search SHALL use deterministic `_find_best_target()` for each card
- **AND** SHALL NOT explore multiple targets per card

#### Scenario: Target exploration disabled (timeout risk)

- **GIVEN** 3 monsters alive
- **AND** beam search has already taken 65ms
- **WHEN** planning the next action sequence
- **THEN** beam search SHALL disable target exploration
- **AND** SHALL fall back to deterministic targeting to avoid timeout

---

### Requirement: Target Space Pruning

Before exploring targets, the planner SHALL prune the target space to limit the number of targets evaluated per card. Pruning logic SHALL differ between attack and debuff cards.

**For attack cards**:
1. Identify all **killable targets** (damage >= monster HP + block)
2. If killable targets exist: Keep only killable targets, sorted by threat
3. If no killable targets: Keep only the highest threat target
4. Maximum targets: 2-3 (or all if fewer killable targets)

**For debuff cards** (Vulnerable, Weak, etc.):
1. Rank all targets by threat score
2. Keep top 2 threat targets
3. Maximum targets: 2

**Skip pruning** (use deterministic targeting) when:
- More than 4 monsters alive (too complex)
- All monsters at low HP (< 8 HP) → use greedy lowest-HP targeting

#### Scenario: Attack target pruning with killable targets

- **GIVEN** monsters: [Boss(15HP), MinionA(8HP), MinionB(6HP)]
- **AND** playing Bash for 10 damage
- **WHEN** pruning targets
- **THEN** returned targets SHALL be: [MinionB(6HP), MinionA(8HP)]
- **AND** Boss SHALL NOT be included (not killable, wasting damage)

#### Scenario: Attack target pruning without killable targets

- **GIVEN** monsters: [Boss(20HP), MinionA(15HP), MinionB(12HP)]
- **AND** playing Heavy Blade for 10 damage
- **WHEN** pruning targets
- **THEN** returned targets SHALL be: [highest_threat_monster]
- **AND** SHALL contain only 1 target (fallback)

#### Scenario: Debuff target pruning

- **GIVEN** monsters: [Boss(threat=30), MinionA(threat=15), MinionB(threat=12), MinionC(threat=10)]
- **AND** playing Vulnerable card
- **WHEN** pruning targets
- **THEN** returned targets SHALL be: [Boss, MinionA] (top 2 by threat)
- **AND** MinionB and MinionC SHALL NOT be included

#### Scenario: Skip pruning with many monsters

- **GIVEN** 5 monsters alive
- **WHEN** pruning targets for any card
- **THEN** the system SHALL skip pruning
- **AND** SHALL use deterministic `_find_best_target()` (current behavior)

#### Scenario: Cleanup phase greedy targeting

- **GIVEN** all monsters at < 8 HP
- **AND** playing an attack card
- **WHEN** selecting targets
- **THEN** the system SHALL use greedy lowest-HP targeting (no pruning needed)
- **AND** SHALL target the monster with lowest HP

---

### Requirement: Progressive Target Expansion

The beam search algorithm SHALL use progressive (lazy) target expansion similar to progressive card expansion. The number of targets explored per card SHALL decrease with search depth:

- **Depth 0** (first action): Explore up to 2 targets
- **Depth 1** (second action): Explore up to 1-2 targets (adaptive)
- **Depth 2+** (third action onwards): Use deterministic targeting (1 target)

This focuses computational budget on the first action (most impactful) while avoiding search space explosion.

#### Scenario: Depth 0 explores 2 targets

- **GIVEN** beam search at depth 0 (first card to play)
- **AND** 3 pruned targets available for Bash card
- **WHEN** expanding action candidates
- **THEN** the system SHALL create 2 action candidates (Bash→Target1, Bash→Target2)
- **AND** SHALL explore both in subsequent beam search iterations

#### Scenario: Depth 2 uses deterministic targeting

- **GIVEN** beam search at depth 2 (third card to play)
- **AND** 2 pruned targets available for Iron Wave
- **WHEN** expanding action candidates
- **THEN** the system SHALL create 1 action candidate only
- **AND** SHALL use the highest-ranked target from `_find_best_target()`

#### Scenario: Adaptive target count at depth 1

- **GIVEN** beam search at depth 1
- **AND** beam is narrow (only 5 candidates)
- **WHEN** expanding actions
- **THEN** the system MAY explore 2 targets (has budget)
- **AND** IF beam is wide (15+ candidates), SHALL explore only 1 target

---

### Requirement: Target Exploration Performance

Target exploration SHALL NOT significantly degrade beam search performance. The planner SHALL:

1. Complete beam search with target exploration within 100ms timeout
2. Add < 20% overhead compared to deterministic targeting
3. Abort target exploration if elapsed time > 60ms before expansion
4. Log target exploration decisions and performance metrics

#### Scenario: Performance within budget

- **GIVEN** baseline beam search time: 50ms (deterministic targeting)
- **WHEN** enabling target exploration
- **THEN** beam search time SHALL be < 60ms (target: < 20% overhead)
- **AND** SHALL remain under 100ms timeout

#### Scenario: Timeout protection

- **GIVEN** beam search has taken 65ms so far
- **WHEN** preparing to expand next action candidates
- **THEN** the system SHALL disable target exploration
- **AND** SHALL use deterministic targeting
- **AND** SHALL log "Target exploration disabled: timeout risk"

#### Scenario: Performance logging

- **WHEN** beam search completes with target exploration
- **THEN** the system SHALL log:
  - Whether target exploration was enabled/disabled and why
  - Number of targets explored per card
  - Total beam search time
  - Number of candidates evaluated

---

### Requirement: Conditional Target Exploration

Target exploration SHALL be enabled only when beneficial and disabled otherwise. Enable conditions:

**Enable when ALL of**:
1. 2-3 monsters alive (not overwhelming)
2. Hand size <= 5 cards (manageable complexity)
3. At least one single-target attack or debuff card in hand
4. Beam search elapsed time < 60ms (not approaching timeout)
5. NOT in cleanup phase (not all monsters < 8 HP)

**Disable when ANY of**:
- More than 3 monsters alive
- Hand size > 5 cards
- No single-target cards
- Beam search time > 60ms
- All monsters at low HP (< 8 HP)

#### Scenario: All conditions met - exploration enabled

- **GIVEN** 2 monsters alive
- **AND** hand has 3 cards including Bash
- **AND** beam search time: 40ms
- **AND** monsters at [30HP, 25HP] (not cleanup phase)
- **WHEN** planning turn
- **THEN** target exploration SHALL be enabled

#### Scenario: Too many cards - exploration disabled

- **GIVEN** 2 monsters alive
- **AND** hand has 7 cards
- **WHEN** planning turn
- **THEN** target exploration SHALL be disabled
- **AND** deterministic targeting SHALL be used

#### Scenario: No single-target cards - exploration disabled

- **GIVEN** 2 monsters alive
- **AND** hand has only AOE cards [Cleave, Whirlwind]
- **WHEN** planning turn
- **THEN** target exploration SHALL be disabled (no targets to explore)
