## 1. Target Preparation

- [x] 1.1 Add configuration and CLI validation for the opt-in frozen-parent n-step mode and positive horizon.
- [x] 1.2 Compute finite masked next-state values from the immutable initialized parent before optimizer work.
- [x] 1.3 Materialize terminal and nonterminal n-step replay targets with complete contiguous trajectory validation.
- [x] 1.4 Bind target horizon, discount, parent identity, bootstrap count, summaries, and transformed transition identity in reports and simulator-only checkpoints.

## 2. Regression Coverage

- [x] 2.1 Add deterministic tests for terminal tails, exact-horizon bootstrapping, invalid corpora, invalid configuration, and parent-value provenance.
- [x] 2.2 Prove existing one-step and discounted-episode-return behavior remains unchanged.

## 3. Verification And Experiment

- [x] 3.1 Validate the OpenSpec change and run the focused combat LightSTS training tests.
- [x] 3.2 Run the full pytest suite once at the implementation gate and record any infrastructure-only failures separately. (`6349 passed, 28 skipped, 230 failed`; failures were outside the changed LightSTS runner/test module and concentrated in stale evidence bindings, Windows qualification fixtures, and an existing Reaper fixture.)
- [ ] 3.3 Register and run fresh matched one-step, 3-step, and 5-step LightSTS training arms from the same parent and profiles.
- [ ] 3.4 Publish the held-out comparison and a simulator-only go/no-go conclusion without changing production gameplay or starting the game.
