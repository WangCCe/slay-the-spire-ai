# Change: Back up latest training checkpoint at session start

## Why
The training loop keeps only the latest few checkpoints, which discards early states.
A session-start backup preserves a copy of the most recent checkpoint before rotation occurs.

## What Changes
- When training starts, copy the latest checkpoint into a backup location.
- Keep backups outside the rolling `checkpoints/` directory.
- Log the backup location and source checkpoint.

## Impact
- Affected specs: checkpoint-backup (new)
- Affected code: `main.py` (training startup)
