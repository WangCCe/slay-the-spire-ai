## ADDED Requirements

### Requirement: R6 registration access is path-allowlisted and non-discovering
Before any r6 registration input is opened, the system SHALL publish and
independently review an exact allowlist containing only the current r5
inventory, build receipt, verification receipt, verification completion,
standalone verification result, verification review, and the bounded r6 output
paths. The registration driver SHALL NOT enumerate directories, expand globs,
search report roots, inspect predecessor roots, or infer substitute evidence.
The preflight SHALL also bind the pushed r5 incident and archive commits, absent
r5 registration, and unchanged incomplete parent tasks 6.2/6.3.
After that preflight is pushed, the system SHALL publish and review one
canonical self-digested driver request binding the preflight digest, exact six
evidence inputs, receipt/output paths, registration identity/schema,
implementation and inventory source commits, exact all-false downstream map,
and sole permitted CLI shape. The driver SHALL read the request as its only
caller-selected control path and SHALL NOT open the preflight file.

#### Scenario: Exact allowlist is used
- **WHEN** every input path and byte identity equals the pushed r5 evidence and every r6 receipt/output path is absent
- **THEN** the one-shot driver may claim its immutable receipt, open each allowlisted canonical input exactly once, and pass decoded mappings to the pure registration builder

#### Scenario: Driver request drifts
- **WHEN** the request bytes, self-digest, preflight binding, input set, source commit, receipt/output path, registration identity, downstream map, or command shape differs
- **THEN** the first invocation fails closed without substituting another request or retrying r6

#### Scenario: A report root is searched
- **WHEN** registration planning or execution enumerates, globs, or text-searches `reports` or another root containing protected predecessor inventories
- **THEN** r6 fails closed before registration publication and grants no downstream authority

#### Scenario: A predecessor path is supplied
- **WHEN** an r1-r4 inventory path, symlink, alias, wildcard, additional file, or unregistered substitute appears in the input set
- **THEN** the driver rejects the access set before opening candidate input bytes

#### Scenario: Directory discovery is attempted
- **WHEN** the driver invokes directory iteration, globbing, recursive search, or root enumeration instead of validating the exact supplied allowlist
- **THEN** r6 fails closed and the first invocation cannot be retried

#### Scenario: R5 terminal state drifts
- **WHEN** the r5 incident/archive commits, absent r5 registration, or parent 6.2/6.3 state differs from the preregistered boundary
- **THEN** r6 remains NO-GO before any registration input is opened

### Requirement: R6 records complete access isolation
The r6 publication review SHALL record that the observed input access set equals
the six-file evidence allowlist plus the single request control input,
predecessor content was not accessed, no unexpected process survived, the
immutable receipt plus registration are the exact driver outputs, and native, model,
environment, gameplay, training, evaluation, OPE, qualification, and promotion
operations were not performed.
Independent reviews SHALL receive exact bounded text only, SHALL have no tool or
path access, and SHALL NOT enumerate or search repository/report roots.

The later static review artifact is created by the owning task after the driver
has exited and is accounted separately from the driver's closed output set.

#### Scenario: Access accounting is exact
- **WHEN** registration construction and both validators finish with the exact allowlisted access set and no prohibited operation
- **THEN** the bounded review may accept the registration for parent task 6.2 only

#### Scenario: Access accounting is incomplete
- **WHEN** any opened path, process, output, or prohibited-operation observation is missing or ambiguous
- **THEN** r6 fails closed without registration acceptance or parent-task changes

#### Scenario: An allowlisted input is reopened
- **WHEN** the observed access ledger contains zero or more than one open for any registered input or contains an additional path
- **THEN** r6 fails closed without deleting evidence or reinvoking the driver

#### Scenario: A reviewer accesses an unregistered path
- **WHEN** implementation or registration review invokes a tool, searches a root, or reads a path outside its exact text input
- **THEN** r6 fails closed and no registration or parent-task change is accepted
