# Spec Delta: Advanced Detectors

## Added Requirements

### Requirement: Independent debris detector
The platform MUST support a detector path dedicated to floor debris or litter anomalies.

#### Scenario: Debris is detected only in floor zone
- **WHEN** a debris rule is configured for a floor zone
- **THEN** the detector evaluates only that zone and generates alert candidates according to area and duration thresholds.

### Requirement: Independent fire and smoke detector
The platform MUST support a dedicated fire and smoke detector path that is conditional on a per-camera enabled `fire_smoke` rule. The detector MUST receive threshold configuration from the rule's `config` field rather than hardcoded defaults.

#### Scenario: Fire/smoke detection runs when a rule is enabled
- **WHEN** a camera has an enabled `fire_smoke` rule with `confidence_threshold=0.5` and `min_area_ratio=0.01`
- **THEN** the pipeline runs the FireSmokeDetector with those thresholds and generates critical alerts on qualifying detections.

#### Scenario: Fire/smoke detection is skipped when no rule exists
- **WHEN** a camera has no enabled `fire_smoke` rule
- **THEN** the pipeline skips fire/smoke detection entirely and no fire/smoke alerts are generated for that camera.

### Requirement: Shared detector integration contract
The platform MUST integrate advanced detectors through the same platform detector contract used by other anomaly types, with detector configuration sourced from persisted rules.

#### Scenario: Detector config is sourced from rules
- **WHEN** the worker runs a fire/smoke detector for a camera
- **THEN** the detector receives the `config` dict from the camera's matching enabled rule, falling back to constructor defaults for missing keys.
