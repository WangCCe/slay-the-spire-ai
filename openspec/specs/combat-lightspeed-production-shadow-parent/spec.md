# combat-lightspeed-production-shadow-parent Specification

## Purpose

Define the fail-closed conversion of an exact production RL v2 policy into a provenance-complete checkpoint that can be used only as a LightSTS simulator training parent.

## Requirements

### Requirement: Exact production source binding
The converter SHALL require a caller-supplied SHA-256 and SHALL refuse to load or publish from a production checkpoint whose resolved file, checkpoint kind, schema, RL v2 metadata, tensor state, or current item-vocabulary dimensions do not match the declared conversion contract.

#### Scenario: Exact production checkpoint is accepted
- **WHEN** a `weights` checkpoint with schema version 2, compatible RL v2 metadata, tensor-only state, current item vocabulary, and the expected file SHA-256 is supplied
- **THEN** the converter strictly loads its state into a fresh current RL v2 trainer before creating any published output

#### Scenario: Source identity or structure differs
- **WHEN** the file hash, checkpoint kind, schema, metadata, vocabulary, state keys, shapes, dtypes, or tensor values violate the conversion contract
- **THEN** the converter SHALL fail closed without publishing an output directory

### Requirement: Authority-reduced simulator shadow
The converter SHALL preserve the source network parameters exactly while exporting them only as a `simulator_training_smoke` checkpoint with `production_compatible=false`, explicit production-source provenance, and authority limited to LightSTS simulator-parent loading.

#### Scenario: Shadow is exported
- **WHEN** the source checkpoint passes all validation
- **THEN** the shadow contains cloned CPU tensors under `online_network_state_dict`, an unchanged canonical parameter SHA-256, the source file and parameter hashes, the item-vocabulary binding, and an authority record that allows LightSTS simulator-parent loading but grants no gameplay, production training, evaluation, promotion, CommunicationMod, or production RLAgent-loading authority

#### Scenario: Production agent rejects shadow
- **WHEN** a production RLAgent attempts to load the simulator-only shadow
- **THEN** the production metadata contract SHALL reject the shadow before gameplay use

#### Scenario: Production source remains unchanged
- **WHEN** conversion completes or fails
- **THEN** the converter SHALL not modify, replace, rename, or write beside the source production checkpoint

### Requirement: Deterministic reload equivalence
The converter SHALL reload the staged shadow and prove structural and functional equivalence to the bound production source before publication.

#### Scenario: Equivalent shadow passes
- **WHEN** independent source-loaded and shadow-loaded trainers are evaluated on fixed valid masked-action probes
- **THEN** the state-dict keys, shapes, dtypes, parameter hash, masked Q-values within the declared tolerance, and selected actions SHALL match

#### Scenario: Functional equivalence fails
- **WHEN** any probe produces a Q-value delta above tolerance or a different selected action
- **THEN** the converter SHALL fail without publishing the final output directory

### Requirement: Provenance-complete atomic publication
The converter SHALL publish a shadow checkpoint, machine-readable report, human-readable summary, and hash manifest only after every validation and equivalence check succeeds.

#### Scenario: Successful publication
- **WHEN** all validation and equivalence checks pass and the final output path is absent
- **THEN** the converter SHALL write the complete artifact set in staging, bind hashes and sizes in the manifest, and atomically rename staging to the final output directory

#### Scenario: Unsafe output boundary
- **WHEN** the final output path already exists or an artifact cannot be validated in staging
- **THEN** the converter SHALL fail without replacing existing output or publishing a partial final directory
