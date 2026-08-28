## MODIFIED Requirements

### Requirement: Guard-relative late takeover with fixed safety veto

The candidate runtime SHALL evaluate only a raw parent EndTurn proposal that a
completed outer guard changed to a legal non-EndTurn action. It SHALL apply a
candidate only after the fixed source-bound safety veto passes and MUST retain
the guard action on abstention, veto, or error. When the completed guard action
is a legal attack that kills its selected living target, the safety veto MUST
retain it unless the candidate also kills a selected living target.

#### Scenario: Safe candidate clears the threshold
- **WHEN** the decision is eligible, the constrained candidate is legal and non-EndTurn, its predicted advantage reaches the registered artifact threshold, every safety-veto condition passes, and it does not replace a target-lethal guard with a nonlethal action
- **THEN** the candidate becomes the selected action before the ordinary final-action commit

#### Scenario: Candidate is ineligible or vetoed
- **WHEN** parent or guard support differs, the candidate abstains, or any legality or safety-veto condition fails
- **THEN** the completed guard action remains selected and gameplay continues without candidate takeover

#### Scenario: Candidate processing fails
- **WHEN** late inference, decoding, safety validation, tracing, or commit processing raises or produces inconsistent identity
- **THEN** candidate authority is disabled, the arm becomes ineligible, and the guard action is retained for recoverability

#### Scenario: Nonlethal candidate would replace target-lethal guard
- **WHEN** multiple monsters are alive, the completed guard attack legally kills its selected target, and the proposed candidate kills no selected living target
- **THEN** the fixed safety policy vetoes the takeover with `mandatory_guard:target_lethal` and retains the guard attack

#### Scenario: Candidate also kills its selected target
- **WHEN** the completed guard attack is target-lethal and the legal candidate also kills its selected living target
- **THEN** target-lethal preservation alone does not veto the candidate
