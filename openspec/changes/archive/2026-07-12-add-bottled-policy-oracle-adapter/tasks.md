## 1. Proposal
- [x] 1.1 Inspect current non-combat RL decision loop spec and comparator implementation.
- [x] 1.2 Define the Bottled oracle adapter boundary and non-goals.
- [x] 1.3 Validate the OpenSpec change.
- [x] 1.4 Get approval before implementation.

## 2. Bottled Oracle Adapter
- [x] 2.1 Add an offline adapter module that resolves the Bottled repo path from CLI, environment, or local default.
- [x] 2.2 Capture Bottled source metadata: path, git commit when available, dirty status when cheap to determine, strategy, and adapter mode.
- [x] 2.3 Implement native oracle evaluation for card_reward using `REQUESTED_STRIKE` desired-card behavior.
- [x] 2.4 Implement native oracle evaluation for shop using `REQUESTED_STRIKE` shop priorities.
- [x] 2.5 Implement native oracle evaluation for event using `REQUESTED_STRIKE` event/common event behavior.
- [x] 2.6 Implement route oracle evaluation using Bottled route scoring where trace path context is sufficient.
- [x] 2.7 Return explicit unsupported or partial results when a sample cannot be represented faithfully.

## 3. Comparator And Report Integration
- [x] 3.1 Add a selectable reference mode for native Bottled oracle vs existing Bottled-style fallback.
- [x] 3.2 Include oracle metadata in trainable samples and report summaries.
- [x] 3.3 Map Bottled oracle labels to normalized candidate action ids.
- [x] 3.4 Rank repeated high-confidence current-vs-Bottled disagreements without applying gameplay fixes automatically.
- [x] 3.5 Add combat feasibility reporting without replacing combat policy.

## 4. Tests And Validation
- [x] 4.1 Add focused adapter tests for path resolution and source metadata.
- [x] 4.2 Add focused category tests for shop, card_reward, event, and route.
- [x] 4.3 Add report tests distinguishing native Bottled oracle output from Bottled-style fallback.
- [x] 4.4 Add guard tests proving live gameplay config and formal non-combat RL training behavior are unchanged.
- [x] 4.5 Run focused pytest for offline comparator and non-combat RL decision loop.
- [x] 4.6 Run full pytest with the repo pytest temp workaround.

## 5. Documentation And Handoff
- [x] 5.1 Document the adapter CLI usage and expected Bottled checkout path.
- [x] 5.2 Generate at least one bounded report from existing fixture or trace data.
- [x] 5.3 Summarize remaining unsupported Bottled surfaces and candidate policy fixes.
