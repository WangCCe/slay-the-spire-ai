## 1. Canary Runtime

- [x] 1.1 Add a source-bound three-game canary configuration and mutual-exclusion startup check
- [x] 1.2 Add exact live action mapping, substitution rows, and fail-closed disabling
- [x] 1.3 Expose the opt-in canary through `main.py` and the bounded batch launcher

## 2. Verification

- [x] 2.1 Add regressions for agreement, substitution, ineligibility fallback, error disabling, limits, and mode conflicts
- [x] 2.2 Run focused canary/main/batch tests and strict OpenSpec validation
- [x] 2.3 Run tiered protocol and gameplay gates; waive the 42-minute full gate under the approved iteration-time budget

## 3. Live Canary

- [ ] 3.1 Commit and push the tested runtime, then create one source-bound canary configuration
- [ ] 3.2 Run exactly three fresh Ironclad games with Windows Python and restore the prior CommunicationMod command
- [ ] 3.3 Publish canonical rows, run records, errors, latency, substitutions, outcomes, and the fixed operational verdict
- [ ] 3.4 Archive the change, commit the evidence, and push `master`
