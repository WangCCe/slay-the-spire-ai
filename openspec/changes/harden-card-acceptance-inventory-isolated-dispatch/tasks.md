## 1. Regression Boundary

- [x] 1.1 Add a RED subprocess regression for the exact `sys.executable -I <absolute-seed-inventory-script> check-dispatch` shape, requiring isolated mode and byte-identical canonical output across two invocations.
- [x] 1.2 Add a focused no-side-effect regression that blocks request/source reads, receipt creation, cohort materialization, and output publication while the dispatch check imports only the configured control module.

## 2. Isolated Dispatch

- [x] 2.1 Add a direct-script-only repository-root bootstrap derived from `__file__`, preserving normal package imports and Python isolated mode.
- [x] 2.2 Implement `check-dispatch` with no path or authority arguments, fixed control-module path validation, canonical contract digest output, and no inventory lifecycle access.

## 3. Verification

- [x] 3.1 Run the exact Windows isolated-dispatch regression, focused no-side-effect nodes, and the complete seed-inventory pytest file under the registered Windows pytest temp parent.
- [x] 3.2 Run the repository commit test gate, strict global OpenSpec validation, compile/import isolation, and diff checks; record that fresh gameplay validation is not applicable because no production gameplay path changed.
- [x] 3.3 Obtain independent code/spec review and resolve every actionable finding without invoking inventory or publishing r3 authority.

## 4. Closeout

- [ ] 4.1 Commit and push the isolated-dispatch repair as one source-only boundary.
- [ ] 4.2 Sync the delta spec, archive this change, strict-validate the global OpenSpec set, and push the completed closeout without creating an r3 request, registration, or training authority.
