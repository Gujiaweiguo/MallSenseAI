## Why

Rule configuration mixes "what a rule does" (type + thresholds) with "where it applies" (camera + ROI) in a single flat table. 21 cameras with the same fire_smoke config means 21 duplicated records — changing a threshold requires updating all 21. There is no central place to define reusable rule templates, and no way to see what rule configurations exist system-wide.

## What Changes

- **BREAKING**: Introduce `RuleDefinition` model — global, reusable rule templates (name, type, config, description)
- **BREAKING**: Existing `Rule` table becomes `RuleAssignment` — references a `RuleDefinition` and binds it to a camera + optional ROI
- New top-level nav item "规则定义" for CRUD on definitions
- Per-camera rule page becomes "apply definition to camera" flow (select from existing definitions, not create from scratch)
- Pipeline resolves assignment → definition → config at evaluation time
- Data migration: existing rules auto-split into one definition per unique (type, config) + assignments

## Capabilities

### New Capabilities

- `rule-definitions`: Global rule template management — create, edit, delete reusable rule definitions with type-specific thresholds

### Modified Capabilities

- `obstruction-rules`: Rule evaluation now resolves config from RuleDefinition via RuleAssignment; per-camera page changes from "create rule" to "apply definition"

## Impact

- **Backend**: New `RuleDefinition` model + API (`/api/rule-definitions`), `Rule` table gets `definition_id` FK, pipeline context loader joins definition
- **Database**: Migration to split existing rules into definitions + assignments
- **Frontend**: New `RuleDefinitionView` page + nav item, refactor `RuleConfigView` to selection-based flow
- **Tests**: Pipeline tests, API tests, e2e tests all need updates
