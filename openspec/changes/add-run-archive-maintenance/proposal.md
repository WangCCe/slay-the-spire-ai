# Change: Add automated run archiving during training

## Why
Long training sessions accumulate thousands of `.run` files, and post-run screen delays increase over time.
Automated archiving keeps the active `runs/` directory small to improve end-of-run responsiveness.

## What Changes
- Archive older run records after every 200 training games.
- Keep only the most recent 1000 run files per character in `runs/<CHARACTER>`.
- Move archived files into `runs_archive/<CHARACTER>`.

## Impact
- Affected specs: run-archive-maintenance (new)
- Affected code: `main.py`
