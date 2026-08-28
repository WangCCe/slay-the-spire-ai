## ADDED Requirements

### Requirement: Expanded-corpus item-semantic evaluation

The system SHALL fit one item-semantic selective classifier on expanded fit
seeds `264000..264767`, calibrate only on seeds `264768..265023`, and evaluate
only after both stages on fresh seeds `266000..266255`.

#### Scenario: Fresh offline gates pass

- **WHEN** fresh interventions are at least 30, precision is at least `0.65`, mean selected advantage exceeds `0.18881003558635712`, mean regret is below `3.1811342239379883`, and severe, illegal, and forbidden selections are zero
- **THEN** the artifact may proceed only to a separately proposed fresh matched LightSTS policy gate

#### Scenario: Fresh offline gate fails

- **WHEN** any coverage, precision, value, regret, severe-risk, legality, artifact, split, or provenance condition fails
- **THEN** the expanded item-semantic recipe closes without retraining, seed changes, threshold changes, tuning, sweep, gameplay, or promotion
