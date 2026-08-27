# Replay distribution calibration r1 failure review

## Verdict

`technical_execution_failure_no_retry`

r1 passed source, replay, native, item, and parent identity validation, then
failed when the first frozen-parent action was requested. The network-only
`FrozenBehaviorPolicy` wrapper did not expose the `select_action` method used by
the existing collection path.

No report or staging directory was published, no optimizer was constructed or
updated, and no game or CommunicationMod process was started. Because an
environment had already been constructed, the exact accessed seed suffix is not
recoverable from a journal; the entire `180000..180127` range is conservatively
reserved and r1 will not be retried or resumed.

The permitted recovery is a narrow deterministic inference compatibility method
plus a focused regression, followed by a separately committed r2 registration
on a fresh disjoint cohort.
