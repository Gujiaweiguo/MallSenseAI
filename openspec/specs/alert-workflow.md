# Spec Delta: Alert Workflow

## Added Requirements

### Requirement: Alert event lifecycle
The platform MUST persist alert events with a lifecycle that supports human handling and auditability.

#### Scenario: Alert moves through lifecycle states
- **WHEN** an anomaly is detected and later handled by an operator
- **THEN** the alert transitions through explicit states such as pending, acknowledged, processing, resolved, false_positive, and verified.

### Requirement: Work-order linkage
The platform MUST support linking alerts to work-order style handling records.

#### Scenario: Operator handles an alert
- **WHEN** an operator starts handling an alert
- **THEN** the platform records the handling status, assignee, notes, and closure trail.

### Requirement: Multi-channel notification
The platform MUST support enterprise WeCom and SMS as notification channels.

#### Scenario: Critical alert is escalated
- **WHEN** a high-priority alert is generated
- **THEN** the platform routes notifications through the configured escalation channels, including WeCom and SMS where required.

### Requirement: Alert cooldown and deduplication
The platform MUST support alert cooldown and deduplication behavior.

#### Scenario: Same rule keeps firing inside cooldown window
- **WHEN** the same camera and rule repeatedly trigger inside the configured cooldown period
- **THEN** the platform suppresses or aggregates duplicate alerts according to policy.
