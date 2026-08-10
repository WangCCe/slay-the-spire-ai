## ADDED Requirements

### Requirement: R5 predecessor preflight is content-blind and hardening-bound
Before r5 build authority publication, the system SHALL independently review a
source/path preflight that binds pushed source commit `525c302df`, exact
verification-hardening module identities, current pushed tracked-clean
ancestry, deterministic isolated dispatch, compact-v4 and fixed byte ceilings,
tracked terminal r1-r4 evidence, generated/predecessor root exclusions, and
absence of every r5 output, staging, attempt, build receipt, verification
receipt, and registration path.

The preflight SHALL treat predecessor inventory roots only as preserved excluded
paths. It SHALL NOT open, stream, hash, parse, canonicalize, validate, convert,
delete, relocate, or register r3 or r4 unverified inventory content. Later r5
authority artifacts SHALL remain ineligible if source/path identity drifts or a
registered r5 write surface already exists.

#### Scenario: Terminal r4 is bound without inventory-content access
- **WHEN** r5 source/path preflight is rendered
- **THEN** it binds tracked r4 request, authority, launch, build receipt, completion, failure, review, and postmortem identities while observing r4 inventory only as a preserved excluded path

#### Scenario: Hardened source identity is exact
- **WHEN** the source commit is a pushed tracked-clean ancestor and current source inventory reproduces the hardened control, seed-inventory, and verifier identities
- **THEN** source identity may proceed to r5 authority rendering without granting build, verification, registration, or downstream authority

#### Scenario: R5 write surface already exists
- **WHEN** any r5 output, staging, attempt, build receipt, verification receipt, completion, or registration path exists before its preregistered owning stage
- **THEN** r5 remains NO-GO and no build or verification process is invoked

#### Scenario: Predecessor content access is attempted
- **WHEN** planning, preflight, authority rendering, build, verification, standalone validation, or registration attempts to read or derive evidence from r3 or r4 unverified inventory content
- **THEN** r5 fails closed, preserves the predecessor bytes, and grants no registration or downstream authority

#### Scenario: Source or ceiling drifts
- **WHEN** pushed ancestry, tracked cleanliness, dispatch, module identity, compact schema, 64 MiB inventory ceiling, 2,048-byte completion ceiling, exclusion policy, or candidate path identity differs
- **THEN** r5 remains pre-start NO-GO until a distinct reviewed successor plan binds the changed source
