# Change: Refactor RL Training Pipeline

## Why
Recent Ironclad RL training records show a stable plateau rather than gradual learning: the latest 500 runs at Ascension 0 had 0 wins, an average floor near 9, and most deaths occurred against Act 1 elites. Continuing the same live-game loop will mostly collect repeated early-death samples while remaining limited by Slay the Spire UI speed and long-session slowdown.

## What Changes
- Add a supervised training-run orchestrator that can run bounded training batches, choose safer curriculum defaults, and report plateau metrics after each batch.
- Add curriculum controls for route risk, starting with conservative Act 1 elite routing before gradually enabling aggressive elite routes.
- Add live-game stability controls for long sessions, including bounded game counts, run/log maintenance hooks, and optional process restart points.
- Add an offline dataset pipeline that converts `.run` records and AI debug logs into reusable training/evaluation artifacts for imitation learning and replay analysis.
- Add a validation workflow that compares recent run buckets, death causes, action failures, and route choices before promoting a checkpoint.

## Impact
- Affected specs: `training-pipeline` (new)
- Related active changes: `redesign-rl-spaces`, `add-seed-pool-rotation`, `add-run-archive-maintenance`, `add-checkpoint-backup`, `add-training-checkpoint-restore`
- Affected code: `main.py`, `analysis_scripts/`, new training orchestration scripts, RL trainer/data utilities
- Runtime constraints: Keep Windows Python as the production gameplay path; avoid WSL for live Communication Mod gameplay.
