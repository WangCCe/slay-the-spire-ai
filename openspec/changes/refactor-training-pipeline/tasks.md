## 1. Baseline and Diagnostics
- [x] 1.1 Add a reproducible recent-runs analysis command that reports bucketed average floor, win rate, death causes, route risk, and action failure hints.
- [x] 1.2 Add a training plateau detector using recent bucket trends and elite-death concentration.
- [x] 1.3 Document the current baseline from the March 2026 Ironclad runs.

## 2. Live Training Orchestration
- [x] 2.1 Add a batch runner script that invokes Windows Python with bounded `--max-games` sessions.
- [x] 2.2 Default batch training to `--agent combat_rl --train --rl-version v2 --elite-route conservative`.
- [x] 2.3 Add curriculum configuration for conservative, mixed, and aggressive route phases.
- [x] 2.4 Add hooks for run archiving, checkpoint backup, and log rotation between batches.
- [x] 2.5 Add optional long-session restart guidance or automation guarded by explicit configuration.

## 3. Offline Data Pipeline
- [ ] 3.1 Add an extractor that converts `.run` records into JSONL/CSV episode summaries.
- [ ] 3.2 Add an extractor that parses `ai_debug.log` into decision/action/reward traces when available.
- [ ] 3.3 Add dataset validation checks for missing fields, duplicate runs, malformed actions, and train/eval splits.
- [ ] 3.4 Add documentation for using extracted data for imitation learning or replay analysis.

## 4. Checkpoint Evaluation
- [ ] 4.1 Add a checkpoint evaluation script that runs a fixed seed pool with bounded games.
- [ ] 4.2 Define checkpoint promotion thresholds for average floor, boss reach rate, elite death rate, and action failure rate.
- [ ] 4.3 Save evaluation summaries next to checkpoint metadata.

## 5. Verification
- [x] 5.1 Add unit or script-level tests for run parsing and dataset extraction.
- [x] 5.2 Run startup tests with `D:\anaconda\envs\stsai\python.exe`.
- [x] 5.3 Run one short dry-run analysis against existing Ironclad records.
