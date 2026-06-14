## Context

Rules are currently flat records combining definition (type + thresholds) and assignment (camera + ROI) in one table. This couples "what" with "where", preventing reuse and central management.

## Goals / Non-Goals

**Goals:**
- Separate rule definition from rule assignment
- Define reusable rule templates once, apply to many cameras
- Change thresholds in one place, all assignments update
- Support multiple definitions of the same type (e.g., "火灾-高灵敏度" and "火灾-标准")
- ROI binding stays at assignment level (Q1: yes)
- Multiple assignments of same type on one camera allowed (Q2: yes)
- Thresholds are definition-level only, no per-assignment override (Q3: pure definition)

**Non-Goals:**
- Rule inheritance or composition
- Per-assignment threshold override
- Rule versioning/history
- Rule definition sharing across tenants

## Decisions

### D1: Two-table split — RuleDefinition + RuleAssignment (renamed from Rule)

**RuleDefinition** (new table `rule_definitions`):
- `id`, `name` (unique, max 128), `rule_type` (enum), `config` (JSON dict), `description` (text, nullable)
- Timestamps

**RuleAssignment** (rename existing `rules` table, add FK):
- `id`, `definition_id` (FK → rule_definitions), `camera_id` (FK → cameras), `roi_id` (FK → rois, nullable)
- `priority` (int), `enabled` (bool)
- Timestamps

**Alternative**: Keep Rule as-is, add rule_definitions with a soft link. Rejected — FK enforcement is important for data integrity.

### D2: Pipeline resolves definition config via join

`context.py` `load_camera_context` currently loads `Rule` records directly. After change:
- Query `RuleAssignment` joined with `RuleDefinition` for enabled assignments on this camera
- `ActiveRule` struct gains `definition_name`, `definition_description` (for logging)
- `config` comes from the joined `RuleDefinition`, not the assignment
- `fire_smoke_config` extraction now reads from definitions

### D3: Data migration — auto-split existing rules

For each unique `(rule_type, config)` pair in existing `rules` table:
1. Create a `RuleDefinition` with auto-generated name (e.g., "火灾烟雾检测-默认")
2. Update all matching `rules` rows: set `definition_id`, clear `rule_type` and `config` (now on definition)

This is a one-time migration. The `RuleType` and `config` columns on `rules` table are dropped after migration.

### D4: API design

**Rule Definitions** (`/api/rule-definitions`):
- `GET /` — list all definitions
- `GET /{id}` — single definition
- `POST /` — create definition (name, rule_type, config, description)
- `PUT /{id}` — update definition (name, config, description — type immutable after creation)
- `DELETE /{id}` — delete (fails if assignments exist)

**Rule Assignments** (`/api/rules` — existing prefix, restructured):
- `GET /?camera_id=X` — list assignments for camera
- `POST /` — create assignment (definition_id, camera_id, roi_id, priority, enabled)
- `PUT /{id}` — update assignment (roi_id, priority, enabled — definition_id immutable)
- `DELETE /{id}` — delete assignment

### D5: Frontend — new RuleDefinitionView + refactor RuleConfigView

**New page: 规则定义** (`/rule-definitions`):
- Table: name, type, description, config summary, assignment count
- Create/edit form: name, type selector (card-style), per-type config fields, description
- Delete with confirmation (warns if assignments exist)

**Refactored: 摄像头规则** (`/cameras/:id/rules`):
- Table: definition name, type, ROI, priority, enabled, actions
- Apply flow: "添加规则" → select from definition dropdown → optional ROI → priority → confirm
- Edit: only ROI/priority/enabled editable (thresholds are on definition)
- Link to rule definition page for threshold editing

### D6: Type immutable after definition creation

Changing rule_type after creation would invalidate the config shape. Definitions are create-with-type, config-editable, type-locked.

## Risks / Trade-offs

- **[Migration complexity]** Existing rules need splitting into definitions + assignments. → Mitigation: idempotent migration script, tested on dev DB first.
- **[DELETE cascade]** Deleting a definition with assignments could break pipeline. → Mitigation: API rejects DELETE when assignments exist; frontend warns.
- **[Extra query per evaluation]** Pipeline now joins definition + assignment. → Mitigation: single JOIN query, cached in CameraContextCache (60s TTL).
- **[Breaking API]** Rules API response shape changes (now includes definition info). → Mitigation: version bump, frontend updated in same release.
