## MODIFIED Requirements

### Requirement: Independent fire and smoke detector
The platform MUST support a dedicated fire and smoke detector path that is conditional on a per-camera enabled `fire_smoke` rule. The detector MUST receive threshold configuration from the rule's `config` field rather than hardcoded defaults.

#### Scenario: Fire/smoke detection runs when a rule is enabled
- **WHEN** a camera has an enabled `fire_smoke` rule with `confidence_threshold=0.5` and `min_area_ratio=0.01`
- **THEN** the pipeline runs the FireSmokeDetector with those thresholds and generates critical alerts on qualifying detections.

#### Scenario: Fire/smoke detection is skipped when no rule exists
- **WHEN** a camera has no enabled `fire_smoke` rule
- **THEN** the pipeline skips fire/smoke detection entirely and no fire/smoke alerts are generated for that camera.

#### Scenario: Fire/smoke detector uses rule config instead of empty defaults
- **WHEN** the pipeline calls the FireSmokeDetector
- **THEN** the detector receives `config` from the matching rule (containing `confidence_threshold`, `min_area_ratio`, `cooldown_seconds`) instead of an empty `{}` dictionary.

### Requirement: Shared detector integration contract
The platform MUST integrate advanced detectors through the same platform detector contract used by other anomaly types, with detector configuration sourced from persisted rules.

#### Scenario: Detector config is sourced from rules
- **WHEN** the worker runs a debris or fire/smoke detector for a camera
- **THEN** the detector receives the `config` dict from the camera's matching enabled rule, falling back to constructor defaults for missing keys.
