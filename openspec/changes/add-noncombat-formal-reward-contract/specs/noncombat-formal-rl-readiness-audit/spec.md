## MODIFIED Requirements

### Requirement: Independent readiness domains
The analyzer SHALL evaluate state/action, reference isolation, formal reward, baseline policy, outcome support, and evaluation readiness as separate deterministic domains without averaging or allowing one domain to override another. A validated formal reward artifact SHALL pass only the reward domain and SHALL NOT override another domain or authorize training.

#### Scenario: State and action evidence closes
- **WHEN** frozen evidence has exact teacher reconstruction without adapter gaps, includes multi-candidate route and card-reward rows, and reports legal candidates across route, shop, event, and card reward
- **THEN** the state/action domain SHALL pass without claiming that the reconstructed teacher is a policy-quality target

#### Scenario: Formal reward evidence is absent
- **WHEN** only a simulator-smoke reward or a descriptive reward-readiness record is available and no separately tested formal reward contract is registered
- **THEN** the reward domain SHALL fail with an explicit formal-reward-contract prerequisite

#### Scenario: Formal reward evidence is validated
- **WHEN** a registered `noncombat-formal-rl-reward-contract-v1` artifact passes terminal-victory priority, bounded secondary floor shaping, scalarization, reference-exclusion, provenance, source-identity, and deterministic-reproduction checks
- **THEN** the reward domain SHALL pass
- **AND** every other readiness domain and the overall verdict SHALL be evaluated independently from its own frozen evidence

#### Scenario: Reward passes while other domains fail
- **WHEN** formal reward evidence is valid but the baseline-policy or outcome-support domain remains blocked
- **THEN** the overall verdict SHALL remain `not_ready_for_bounded_training_proposal`
- **AND** formal RL and every execution or promotion authority SHALL remain false

#### Scenario: Baseline floor is not demonstrated
- **WHEN** a warm-start validation, independent rollout, final, or deterministic reproduction gate does not demonstrate the preregistered baseline policy floor
- **THEN** the baseline domain SHALL fail regardless of training loss, teacher agreement, or improvement over a weaker initialization

#### Scenario: Outcome support is not demonstrated
- **WHEN** evidence is source-incomparable, target-supported victories are below the registered minimum, or the registered feasibility pass probability is below its floor
- **THEN** the outcome-support domain SHALL fail without counting raw unsupported victories

#### Scenario: Evaluation isolation is preserved
- **WHEN** registered train and evaluation cohorts are disjoint, deterministic replays match, final-test access obeys its stop gate, frozen evaluation performs no update, and downstream authority remains false
- **THEN** the evaluation domain SHALL pass independently of policy quality
