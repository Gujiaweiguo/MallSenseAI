# Spec Delta: API Foundation

## Added Requirements

### Requirement: Authenticated management API
The platform MUST expose an authenticated management API for core platform resources.

#### Scenario: Authorized operator manages core resources
- **WHEN** an authenticated operator accesses the management API
- **THEN** the operator can read and modify only the resources allowed by role.

### Requirement: FastAPI backend baseline
The platform MUST implement the management API on FastAPI.

#### Scenario: Backend API stack is instantiated
- **WHEN** the platform backend is created or extended
- **THEN** FastAPI is the API framework used for route definition, schema publication, and request handling.

### Requirement: uv-managed Python workflow
The platform MUST use uv for Python environment and dependency management.

#### Scenario: Backend environment is bootstrapped
- **WHEN** developers or automation set up the Python backend environment
- **THEN** dependency installation and environment execution are performed through uv-managed workflows.

### Requirement: Environment runtime convention
The platform MUST distinguish local development runtime from production container runtime.

#### Scenario: Developer runs the stack locally
- **WHEN** the development environment is started
- **THEN** the frontend and backend run locally, while PostgreSQL and Redis are provided through docker compose.

#### Scenario: Production stack is deployed
- **WHEN** the production environment is deployed
- **THEN** the frontend, backend, PostgreSQL, and Redis are all deployed through docker compose.

### Requirement: Core resource CRUD
The platform MUST provide CRUD endpoints for Camera, Scene, ROI, Rule, Alert, and WorkOrder resources.

#### Scenario: Camera and rule lifecycle is managed through API
- **WHEN** an admin creates a camera, scene, ROI, and rule through API calls
- **THEN** the full resource chain is persisted and queryable through the same API surface.

### Requirement: Snapshot and baseline access contract
The platform MUST define API contracts for camera snapshot retrieval and baseline image management.

#### Scenario: Baseline image is managed by API
- **WHEN** a client requests a new snapshot or updates a baseline image
- **THEN** the API returns or stores the asset through a documented, authenticated endpoint.

### Requirement: API discoverability
The platform MUST publish its API contract in an auto-generated schema.

#### Scenario: Frontend consumes API contract
- **WHEN** the frontend or another client needs the platform contract
- **THEN** an OpenAPI-compatible schema is available.
