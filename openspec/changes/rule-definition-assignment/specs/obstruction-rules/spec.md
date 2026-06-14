## MODIFIED Requirements

### Requirement: Obstruction rule configuration
The platform MUST evaluate rules by resolving each camera's rule assignments to their referenced rule definitions, using the definition's type and config for threshold evaluation. The per-camera rule page MUST present a selection-based flow (choose existing definitions to apply) rather than creating rules from scratch.

#### Scenario: Pipeline resolves assignment to definition config
- **WHEN** the worker evaluates rules for camera 1 which has an assignment referencing definition "标准火灾检测" with config `{confidence_threshold: 0.6}`
- **THEN** the engine and detectors use config `{confidence_threshold: 0.6}` from the definition, not from the assignment record.

#### Scenario: Operator applies a definition to a camera
- **WHEN** an operator on the camera rule page selects definition "通道阻塞-严格" and binds it to ROI-5 with priority 1
- **THEN** a rule assignment is created linking the definition to the camera + ROI, and the rule is active on the next evaluation cycle.

#### Scenario: Operator changes ROI binding on an assignment
- **WHEN** an operator edits an assignment to change its ROI from ROI-3 to ROI-5
- **THEN** the definition's thresholds remain unchanged; only the spatial binding updates.

#### Scenario: Rule created with default config
- **WHEN** a definition is created without explicitly setting config values
- **THEN** the engine applies its built-in defaults for any missing keys.
