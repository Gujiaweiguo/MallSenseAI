## MODIFIED Requirements

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
- **THEN** the engine applies its built-in defaults (e.g., `min_stay_seconds=2.0`, `cooldown_seconds=0`) and the rule functions correctly without requiring a migration.

### Requirement: Forbidden-zone rule type
The platform MUST expose `forbidden_zone` as a selectable rule type in both the backend enum and the frontend configuration UI, backed by the existing engine evaluation path.

#### Scenario: Forbidden-zone rule type is available in the UI
- **WHEN** an operator opens the rule type dropdown
- **THEN** `forbidden_zone` appears alongside `obstruction_duration`, `obstruction_area`, and `fire_smoke`.
