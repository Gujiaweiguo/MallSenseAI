## Added Requirements

### Requirement: Reusable rule definitions
The platform MUST provide a global rule definition system where operators create named, typed rule templates with type-specific threshold configurations, independent of any camera assignment.

#### Scenario: Operator creates a fire/smoke rule definition
- **WHEN** an operator creates a definition with name "标准火灾检测", type `fire_smoke`, config `{confidence_threshold: 0.5, min_area_ratio: 0.01, cooldown_seconds: 30}`
- **THEN** the definition is persisted and available for assignment to any camera.

#### Scenario: Operator updates a definition threshold
- **WHEN** an operator changes the `confidence_threshold` from 0.5 to 0.6 on an existing definition
- **THEN** all cameras with assignments referencing this definition use the new threshold on the next evaluation cycle.

#### Scenario: Multiple definitions of the same type coexist
- **WHEN** an operator creates both "火灾-高灵敏度" and "火灾-标准" definitions of type `fire_smoke`
- **THEN** both definitions can be assigned to different cameras (or the same camera with different ROIs).

### Requirement: Rule definition CRUD
The platform MUST provide API endpoints for creating, reading, updating, and deleting rule definitions.

#### Scenario: Operator lists all definitions
- **WHEN** an operator requests the definition list
- **THEN** all definitions are returned with name, type, config summary, description, and assignment count.

#### Scenario: Deleting a definition with existing assignments is rejected
- **WHEN** an operator attempts to delete a definition that has active assignments
- **THEN** the deletion is rejected with a clear error message indicating which cameras use it.

### Requirement: Rule definition type immutability
The platform MUST prevent changing the `rule_type` of an existing definition, as it would invalidate the config schema.

#### Scenario: Operator attempts to change rule type
- **WHEN** an operator submits an update changing `rule_type` from `fire_smoke` to `obstruction_duration`
- **THEN** the update is rejected; only name, config, and description are editable.
