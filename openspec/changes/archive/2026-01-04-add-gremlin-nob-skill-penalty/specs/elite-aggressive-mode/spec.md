## ADDED Requirements

### Requirement: Gremlin Nob SKILL Card Penalty

The system SHALL apply a scoring penalty when playing SKILL-type cards against Gremlin Nob to reflect its mechanic where it gains +1 Strength per SKILL played. This penalty SHALL:

1. Detect Gremlin Nob presence via `_has_gremlin_nob()`
2. Identify SKILL card type via `card.type == CardType.SKILL`
3. Exclude POWER-type cards (they have separate valuation logic)
4. Apply a -50 point penalty per SKILL card played
5. Log penalty application for debugging

The penalty SHALL discourage playing defensive SKILLs (Defend_R, True Grit, etc.) while preserving ATTACK card priority.

#### Scenario: SKILL card penalized against Gremlin Nob
- **GIVEN** combat with Gremlin Nob
- **AND** a sequence containing PlayCardAction for Defend_R (SKILL type)
- **WHEN** scoring the sequence
- **THEN** score SHALL include -50 penalty for SKILL type
- **AND** penalty SHALL be logged with "[SKILL_PENALTY]" tag

#### Scenario: ATTACK card unaffected by SKILL penalty
- **GIVEN** combat with Gremlin Nob
- **AND** a sequence containing PlayCardAction for Iron Wave (ATTACK type)
- **WHEN** scoring the sequence
- **THEN** score SHALL NOT include SKILL penalty
- **AND** damage bonus SHALL be applied normally

#### Scenario: POWER card excluded from SKILL penalty
- **GIVEN** combat with Gremlin Nob
- **AND** a sequence containing PlayCardAction for Demon Form (POWER type)
- **WHEN** scoring the sequence
- **THEN** score SHALL NOT include SKILL penalty
- **AND** existing +50 early turn bonus SHALL apply (if turn ≤ 3)

#### Scenario: Multiple SKILL cards each penalized
- **GIVEN** combat with Gremlin Nob
- **AND** a sequence: Defend_R, Battle Trance, Defend_R (3 SKILLs)
- **WHEN** scoring the sequence
- **THEN** score SHALL include -150 total penalty (-50 × 3 SKILLs)
- **AND** each SKILL SHALL be logged separately

#### Scenario: Non-Gremlin fight has no SKILL penalty
- **GIVEN** combat with regular monster (Cultist, Jaw Worm)
- **AND** a sequence containing PlayCardAction for Defend_R
- **WHEN** scoring the sequence
- **THEN** score SHALL NOT include SKILL penalty
- **AND** normal scoring SHALL apply

#### Scenario: Mixed ATTACK and SKILL cards
- **GIVEN** combat with Gremlin Nob
- **AND** a sequence: Strike_R (ATTACK), Defend_R (SKILL), Pommel Strike (ATTACK)
- **WHEN** scoring the sequence
- **THEN** Strike_R SHALL have no penalty
- **AND** Defend_R SHALL have -50 penalty
- **AND** Pommel Strike SHALL have no penalty
- **AND** total penalty SHALL be -50 (only 1 SKILL)

---
