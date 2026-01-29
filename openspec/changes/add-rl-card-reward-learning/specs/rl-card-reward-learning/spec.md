## ADDED Requirements
### Requirement: Encode card reward options in RL state
The RL state encoder SHALL include features for available card reward options when the screen is CARD_REWARD, using reserved feature slots without changing the overall state dimension.

#### Scenario: Card reward features present
- **GIVEN** the current screen is CARD_REWARD
- **WHEN** the state encoder runs
- **THEN** the encoded state SHALL include per-card features (cost, type, rarity, damage, block, upgrades)
- **AND** missing card slots SHALL be zero-filled

#### Scenario: No card reward screen
- **GIVEN** the current screen is not CARD_REWARD
- **WHEN** the state encoder runs
- **THEN** the card reward feature slots SHALL be zero-filled

### Requirement: Stronger card choice reward shaping
The reward calculator SHALL score card choices relative to the available options to provide a stronger learning signal.

#### Scenario: Reward positive for strong pick
- **GIVEN** a card reward was chosen
- **AND** candidate cards can be scored
- **WHEN** the reward is computed
- **THEN** the chosen card SHALL receive a higher reward when its score is near the best candidate

#### Scenario: Penalize weak or missed pick
- **GIVEN** a card reward was chosen or skipped
- **AND** candidate cards can be scored
- **WHEN** the reward is computed
- **THEN** the reward SHALL be lower when the chosen card scores below the median candidate
