## ADDED Requirements
### Requirement: Multi-Turn Enemy Lookahead
The system SHALL support an enemy-only lookahead of 1-2 turns after simulating a candidate player sequence, including Weak/Frail/Vulnerable effects from predicted moves.

#### Scenario: Two-turn lookahead with wiki prediction
- **GIVEN** a post-sequence state with 1 Blue Slaver alive
- **AND** enhanced data predicts next moves [Stab, Rake]
- **WHEN** lookahead depth is 2
- **THEN** the system SHALL apply both attacks to estimate follow-on damage
- **AND** SHALL include the damage in the outcome score penalty

#### Scenario: Prediction unavailable
- **GIVEN** a monster without enhanced data
- **WHEN** lookahead is requested
- **THEN** the system SHALL fall back to current intent damage only
- **AND** SHALL NOT raise an exception

#### Scenario: Lookahead applies debuffs
- **GIVEN** a post-sequence state with 1 monster that applies Weak next turn
- **AND** predicted moves include an ATTACK_DEBUFF that applies 2 Weak
- **WHEN** lookahead depth is 1
- **THEN** the system SHALL apply the Weak stacks to the simulated player state
- **AND** SHALL use the debuffed state when estimating follow-on damage penalties

## MODIFIED Requirements
### Requirement: Future Damage in Beam Search Scoring
The beam search scoring function SHALL incorporate future monster damage estimates with multi-turn lookahead when available, including penalties derived from Weak/Frail/Vulnerable applied during the lookahead window.

**Integration:**
```python
def _score_sequence(state, context):
    # ... existing scoring ...

    # NEW: Include multi-turn future damage
    future_damage = simulate_enemy_lookahead(new_state, context, turns=2)
    score -= future_damage * W_DEATHRISK * 0.5
```

#### Scenario: Multi-turn penalty favors lower total damage
- **GIVEN** current incoming damage: 12
- **AND** predicted next 2 turns: [8, 8]
- **AND** W_DEATHRISK = 10.0
- **WHEN** scoring two sequences
- **THEN** the sequence that blocks or reduces the next-turn damage SHALL score higher
- **AND** the system SHALL apply penalties for both future turns
