# Change: Add seed pool rotation for training runs

## Why
Training on a single fixed seed overfits and hides regressions. A small seed pool rotation keeps variance manageable while improving generalization.

## What Changes
- Add CLI support to rotate through a seed pool during training runs.
- Add a simple runner script that uses a seed pool file.
- Add a sample seed pool file for quick start (editable).

## Impact
- Affected specs: training-run-control
- Affected code: main.py, new seed pool runner script, new seed pool config file
