# Spec Delta: Inspection Engine

## Added Requirements

### Requirement: Decoupled inspection execution
The platform MUST run inspection scheduling and detection execution independently from the web management API.

#### Scenario: Inspection continues while API stays responsive
- **WHEN** the system is scheduling and executing inspections for many cameras
- **THEN** the management API remains responsive and is not blocked by detection work.

### Requirement: Camera adapter abstraction
The platform MUST provide a camera source abstraction instead of binding the runtime directly to one camera implementation.

#### Scenario: Snapshot service uses a unified camera contract
- **WHEN** the worker captures a snapshot or updates baseline data
- **THEN** it does so through a unified adapter contract rather than duplicating vendor-specific logic.

### Requirement: Concurrent inspection scheduling
The platform MUST support a scheduling model suitable for 100+ cameras with failure isolation and priority handling.

#### Scenario: One camera fails during a sweep
- **WHEN** one camera is offline, slow, or returns an error
- **THEN** the worker marks that camera state appropriately and continues processing other cameras.

### Requirement: Camera health observability
The platform MUST report camera health and worker execution state.

#### Scenario: Camera becomes degraded
- **WHEN** repeated capture failures occur
- **THEN** the platform records the degraded or offline state and exposes it for operator visibility.
