## 1. Historical Corpus And Cross-Validation

- [x] 1.1 Add exact-hash loading, compatibility checks, source deduplication, cohort labels, and deterministic five-fold assignment for the four registered shop datasets.
- [x] 1.2 Implement multi-seed Current-relative training, centered-score ensemble inference, OOF metric aggregation, and bounded epoch/threshold selection.
- [x] 1.3 Add focused regressions for identity failures, fold isolation, deterministic selection, ensemble round trip, and no-eligible-configuration behavior.

## 2. Frozen Training And Evaluation

- [x] 2.1 Implement full-corpus ensemble fitting, model serialization, and selection-only preflight that performs no fresh source access.
- [x] 2.2 Implement bounded collection and one-shot evaluation of 32 new shop source states with frozen gate checks.
- [x] 2.3 Emit corpus audit, OOF metrics, model, fresh dataset, final metrics, report, and verified artifact manifest.

## 3. Verification And Publication

- [x] 3.1 Run OpenSpec validation and the focused test module using an isolated system-temp pytest directory.
- [x] 3.2 Commit the source-bound runner, run the 112-source selection-only preflight, and either freeze an eligible configuration before fresh access or persist the terminal OOF no-go.
- [x] 3.3 Execute the fresh experiment once when OOF-eligible; otherwise verify no-go artifact hashes and operation disclosures, record the terminal verdict without fresh access, and archive the completed change.
