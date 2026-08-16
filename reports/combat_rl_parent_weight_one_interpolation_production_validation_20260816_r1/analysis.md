# Promoted alpha-0.20 production validation

The promoted production command completed its bounded five-game launch without runtime failures. Floors were `25, 27, 33, 16, 33`, for a mean of `26.8`; four games entered Act 2 and two reached the Act 2 boss. No victory was achieved.

The trace-enabled path worked, but the shared decision trace has grown to approximately 2.4 GB. Full traces are intentionally not copied into Git. Future production launches should use bounded trace rotation before this becomes a repeated disk and analysis bottleneck.

The production configuration was subsequently updated to truncate enabled trace files at the start of each bounded launch and to skip checkpoint backup, maintenance, and post-analysis work that is unnecessary for inference-only validation. The configuration hash in `report.json` remains the historical hash used for this five-game batch.

Using the launch time as a fresh cutoff, the simulator trace contains seven `monster_state_mismatch` events on floors 29, 31, and 33. These are evidence for a later focused mechanics audit, not grounds to roll back the promoted checkpoint.
