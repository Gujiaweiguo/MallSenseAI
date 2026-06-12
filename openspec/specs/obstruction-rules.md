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
