# Spec Delta: Advanced Detectors

## Added Requirements

### Requirement: Independent debris detector
The platform MUST support a detector path dedicated to floor debris or litter anomalies.

#### Scenario: Debris is detected only in floor zone
- **WHEN** a debris rule is configured for a floor zone
- **THEN** the detector evaluates only that zone and generates alert candidates according to area and duration thresholds.

### Requirement: Independent fire and smoke detector
The platform MUST support a dedicated fire and smoke detector path.

#### Scenario: Fire or smoke condition is detected
- **WHEN** the fire/smoke detector triggers a qualifying event
- **THEN** the platform routes it through a high-priority alert path distinct from standard obstruction alerts.

### Requirement: Shared detector integration contract
The platform MUST integrate advanced detectors through the same platform detector contract used by other anomaly types.

#### Scenario: Detector is enabled for a camera scene
- **WHEN** the worker runs a configured anomaly detector
- **THEN** the detector receives standardized scene and rule inputs and returns standardized alert candidate outputs.
