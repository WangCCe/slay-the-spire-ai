## ADDED Requirements

### Requirement: Immutable expanded paired-return cohort

The system SHALL generate one expanded combat paired-return corpus from the
registered native module, runner, r16 shadow, items export, seed partitions,
encounter profiles, bounds, and return recipe.

#### Scenario: Fixed cohort is generated

- **WHEN** all source and input hashes match and the output path is absent
- **THEN** training seeds `264000..265023` and evaluation seeds `266000..266255` execute with battle indices `0,3,6,9`, at most two retained states per profile, and the unchanged branch-return recipe

#### Scenario: Binding differs

- **WHEN** any module, runner, checkpoint, items, seed, profile, horizon, bound, reward, return, or output binding differs
- **THEN** generation stops before native environment construction

### Requirement: Expanded corpus provenance and sufficiency

The system SHALL publish tensor-aligned train and evaluation artifacts with
source, native, checkpoint, seed, action, target, branch-return, exclusion, and
sufficiency evidence.

#### Scenario: Corpus is sufficient

- **WHEN** train and evaluation contain both return classes and training has at least 100 positive states across at least three positive target identities
- **THEN** the exact artifact hashes may be bound into one expanded-corpus item-semantic fit

#### Scenario: Corpus is insufficient

- **WHEN** any class, identity, alignment, completion, legality, or provenance condition fails
- **THEN** fitting does not start and the cohort closes without seed or bound changes

#### Scenario: Infrastructure fails before publication

- **WHEN** generation fails without creating the registered output directory
- **THEN** an identical retry may occur after fixing only the infrastructure cause while preserving every experiment binding
