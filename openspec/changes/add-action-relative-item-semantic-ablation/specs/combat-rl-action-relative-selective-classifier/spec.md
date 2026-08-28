## ADDED Requirements

### Requirement: Optional direct item-semantic features

The development selective classifier SHALL optionally append direct candidate
and guard item embeddings, local card features, action family, and target
identity while preserving the existing feature contract when the option is
disabled.

#### Scenario: Item semantics are enabled

- **WHEN** a supported card or potion pair is scored with the item-semantic option enabled
- **THEN** candidate and guard slots map to their exact frozen item embedding, card-local features, family, and target without changing the frozen parent

#### Scenario: Existing artifact omits item semantics

- **WHEN** an existing selective-classifier artifact is loaded without the new config field
- **THEN** the option defaults to disabled and logits, evidence, selection, and abstention retain the original feature shape and behavior

### Requirement: Consumed-holdout development ablation

The system SHALL run at most one fixed item-semantic CPU ablation and SHALL
treat seeds `263000..263127` only as an already-consumed development
comparison.

#### Scenario: Fixed comparison passes

- **WHEN** interventions are at least 30, precision is at least `0.55`, severe harms are at most 5, mean selected advantage exceeds `0.17321939766407013`, mean regret is below `3.1967246532440186`, and integrity conditions pass
- **THEN** the result may justify a separately proposed fresh corpus but grants no evaluation, qualification, gameplay, or promotion authority

#### Scenario: Fixed comparison fails

- **WHEN** any registered comparison or integrity condition fails
- **THEN** the item-semantic recipe closes without retraining, tuning, native loading, fresh corpus generation, LightSTS execution, or gameplay
