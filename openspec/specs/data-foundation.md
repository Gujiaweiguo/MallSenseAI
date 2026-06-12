# Spec Delta: Data Foundation

## Added Requirements

### Requirement: Unified platform data model
The platform MUST define a normalized domain model for Camera, Scene, ROI, Rule, Alert, WorkOrder, User, and NotificationGroup.

#### Scenario: Core entities are modeled consistently
- **WHEN** the platform stores camera, scene, ROI, rule, alert, and workflow data
- **THEN** it uses one consistent schema rather than splitting state across JSON files and ad-hoc image folders.

### Requirement: PostgreSQL with pgvector as primary database
The platform MUST use PostgreSQL with pgvector as the primary database for business state.

#### Scenario: Platform persists core business entities
- **WHEN** cameras, scenes, ROIs, rules, alerts, or work orders are created or updated
- **THEN** the authoritative business state is persisted in PostgreSQL with pgvector support available for future vector-backed features.

### Requirement: Stable camera identity
The platform MUST use a stable camera identifier that does not depend on mutable location text.

#### Scenario: Camera location changes or collides
- **WHEN** two cameras have similar or changing location labels
- **THEN** the platform still stores and migrates them as distinct camera records using stable identifiers.

### Requirement: Legacy state migration
The platform MUST provide a deterministic migration mapping from `camera_configs.json`, `config.py`, and `alarm_images/` into the new data model.

#### Scenario: Legacy configuration is imported
- **WHEN** an operator runs the migration workflow
- **THEN** cameras, baseline images, ROI definitions, and relevant alert context are mapped into the new model without deleting the legacy source data.

### Requirement: Legacy system directory isolation
The platform MUST isolate the legacy application code and legacy configuration into a dedicated `legacy/` directory during the migration period.

#### Scenario: New and legacy systems coexist
- **WHEN** the new platform and the legacy system operate in parallel during migration
- **THEN** the legacy code and configuration live under `legacy/`, while shared assets such as `alarm_images/` and model weights remain accessible from the repository root.

### Requirement: Canonical asset path strategy
The platform MUST define one canonical strategy for baseline image, ROI, and evidence asset storage.

#### Scenario: Baseline assets are addressed consistently
- **WHEN** any service stores or reads a baseline image or evidence image
- **THEN** it uses the canonical path strategy instead of multiple incompatible path conventions.

### Requirement: Database as business source of truth
The platform MUST move business state from file-based configuration into database-backed entities.

#### Scenario: Platform reads current camera and rule state
- **WHEN** backend services or the frontend query operational state
- **THEN** they read the authoritative business state from the platform database rather than from legacy JSON or Python config files.

### Requirement: Standardized ROI coordinates
The platform MUST store ROI geometry in one normalized coordinate format.

#### Scenario: ROI is reused across services
- **WHEN** the API, worker, and frontend read the same ROI
- **THEN** they interpret the geometry consistently without depending on legacy pixel-space assumptions.

### Requirement: Cutover and rollback safety
The platform MUST define a cutover strategy that allows the legacy system and the new platform to coexist during migration.

#### Scenario: New platform cutover fails
- **WHEN** a rollout or migration step fails during cutover
- **THEN** operators can revert to the legacy runtime path without losing the original configuration or image assets.
