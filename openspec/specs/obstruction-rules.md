# Spec Delta: Obstruction Rules

## Added Requirements

### Requirement: Standardized ROI geometry engine
The platform MUST provide one shared ROI geometry engine for scene and obstruction evaluation.

#### Scenario: Geometry is evaluated consistently
- **WHEN** ROI inclusion, overlap, or effective-width logic is executed
- **THEN** all obstruction-related services use the same geometry rules.

### Requirement: Remaining-clear-width obstruction mode
The platform MUST support an obstruction rule mode based on remaining clear width inside a passable zone.

#### Scenario: Remaining width falls below threshold
- **WHEN** an obstruction reduces the effective clear width below the configured threshold for the configured duration
- **THEN** an obstruction alert candidate is generated.

### Requirement: Occupied-area-ratio obstruction mode
The platform MUST support an obstruction rule mode based on occupied area ratio inside a configured ROI.

#### Scenario: Occupied ratio exceeds threshold
- **WHEN** the occupied area ratio exceeds the configured threshold for the configured duration
- **THEN** an obstruction alert candidate is generated.

### Requirement: Forbidden-zone intrusion mode
The platform MUST support a high-priority obstruction mode for forbidden zones.

#### Scenario: Object enters forbidden zone
- **WHEN** a target object remains inside a forbidden zone beyond the configured minimum duration
- **THEN** a high-priority obstruction alert candidate is generated.

### Requirement: Per-ROI obstruction rule independence
The platform MUST allow different obstruction rule modes on different ROIs of the same camera.

#### Scenario: Multiple ROI modes coexist on one camera
- **WHEN** a camera has a passable zone and a forbidden zone configured
- **THEN** the system evaluates each ROI with its own rule mode and thresholds.

### Requirement: Obstruction rule configuration
The platform MUST persist rule thresholds using field names and config keys that the rule engine consumes at evaluation time. The UI MUST render type-specific config forms that map 1:1 to the engine's expected configuration schema.

#### Scenario: Operator configures a duration-based obstruction rule
- **WHEN** an operator creates an `obstruction_duration` rule with `threshold=3000`, `min_stay_seconds=30`, `cooldown_seconds=60`
- **THEN** the rule is persisted with those values in the `config` field, and the engine reads them during evaluation.

#### Scenario: Operator configures an area-ratio obstruction rule
- **WHEN** an operator creates an `obstruction_area` rule with `threshold_ratio=0.05`, `min_duration_seconds=10`, `cooldown_seconds=30`
- **THEN** the engine applies the ratio threshold and duration filter during evaluation.

#### Scenario: Operator configures a forbidden-zone rule
- **WHEN** an operator selects `forbidden_zone` from the rule type dropdown
- **THEN** the UI displays `min_stay_seconds` and `cooldown_seconds` fields, and the engine evaluates intrusion using those thresholds.

#### Scenario: Rule created with default config
- **WHEN** an operator creates a rule without explicitly setting config values
- **THEN** the engine applies its built-in defaults and the rule functions correctly without requiring a migration.

### Requirement: Forbidden-zone rule type
The platform MUST expose `forbidden_zone` as a selectable rule type in both the backend enum and the frontend configuration UI, backed by the existing engine evaluation path.

#### Scenario: Forbidden-zone rule type is available in the UI
- **WHEN** an operator opens the rule type dropdown
- **THEN** `forbidden_zone` appears alongside `obstruction_duration`, `obstruction_area`, and `fire_smoke`.
