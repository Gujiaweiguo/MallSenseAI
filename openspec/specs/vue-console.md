# Spec Delta: Vue Console

## Added Requirements

### Requirement: Web management console
The platform MUST provide a web management console for multi-user operation.

#### Scenario: Operator manages the platform through browser
- **WHEN** an operator signs in to the platform
- **THEN** the operator can access the platform through a browser instead of relying on CLI or desktop-only tools.

### Requirement: Baseline image and ROI maintenance UI
The platform MUST provide UI flows to manually maintain baseline images and ROIs.

#### Scenario: Operator updates a scene baseline and ROI
- **WHEN** an operator captures or uploads a new baseline image and edits ROI geometry
- **THEN** the updated scene configuration is saved through the platform UI.

### Requirement: Rule configuration UI
The platform MUST provide UI flows to configure obstruction rules per ROI.

#### Scenario: Different ROI rule modes are configured
- **WHEN** an operator configures a passable-zone rule and a forbidden-zone rule on the same camera
- **THEN** the UI supports storing and reviewing both rule modes independently.

### Requirement: Alert and work-order handling UI
The platform MUST provide UI flows to review alerts and process work-order status transitions.

#### Scenario: Operator handles an alert from the console
- **WHEN** an operator opens a new alert in the console
- **THEN** the operator can review evidence, change status, and record handling notes.
