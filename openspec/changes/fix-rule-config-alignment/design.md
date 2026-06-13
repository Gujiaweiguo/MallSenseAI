## Context

The rule configuration system has a broken contract between frontend, API, and engine layers. Three independent drifts compound:

1. **Field name**: Frontend sends `threshold_config`; backend ORM column and Pydantic schema use `config`. The key is silently dropped on persist.
2. **Config keys**: Frontend uses generic keys (`threshold`, `min_area`, `max_count`, `duration_seconds`); engine reads type-specific keys (`min_stay_seconds`, `threshold_ratio`, `cooldown_seconds`, etc.).
3. **Fire/smoke bypass**: Pipeline runs `FireSmokeDetector` unconditionally for every camera. User-created `fire_smoke` rules have no effect — `CriticalAlertHandler` creates alerts regardless.

The engine also supports `forbidden_zone` mode (engine.py L199) that is absent from the `RuleType` enum and UI.

## Goals / Non-Goals

**Goals:**
- Rule thresholds configured in the UI must reach the engine and influence evaluation
- Each rule type shows only the config fields relevant to that type
- Fire/smoke detection respects per-camera rule enable/disable
- `forbidden_zone` rule type is available to users (engine already handles it)
- Dead enum values (`DetectorType.image_compare`, `blue_box`) removed

**Non-Goals:**
- Per-camera detector tuning beyond rule thresholds (confidence, classes) — deferred
- Rule versioning or audit history
- GUI for cooldown configuration (engine defaults are sufficient for v1)
- `CooldownTracker` wiring fix (separate concern, pipeline has its own working cooldown dict)

## Decisions

### D1: Rename frontend field `threshold_config` → `config`

**Rationale**: Backend already uses `config` in ORM, schema, and API. Changing the backend would require a DB migration column rename; changing the frontend only requires a type rename. The frontend already receives `config` from the API on GET — the drift only exists on the write path.

**Alternative**: Add a `threshold_config` alias in the Pydantic schema. Rejected — creates two names for one field, confusing forever.

### D2: Per-type config forms with engine-aligned keys

Each `RuleType` gets a dedicated config shape matching the engine's consumed keys:

| Rule Type | Config Keys | UI Fields |
|-----------|-------------|-----------|
| `obstruction_duration` | `threshold`, `min_stay_seconds`, `cooldown_seconds` | Threshold slider, stay-duration input, cooldown input |
| `obstruction_area` | `threshold_ratio`, `min_duration_seconds`, `cooldown_seconds` | Ratio input, duration input, cooldown input |
| `forbidden_zone` | `min_stay_seconds`, `cooldown_seconds` | Stay-duration input, cooldown input |
| `fire_smoke` | `confidence_threshold`, `min_area_ratio`, `cooldown_seconds` | Confidence input, area-ratio input, cooldown input |
| `litter` | `min_confidence`, `min_area_ratio`, `duration_seconds`, `cooldown_seconds` | Confidence, area-ratio, duration, cooldown |

The frontend `RuleConfigView` renders different form sections based on the selected `rule_type`.

### D3: Pipeline checks fire/smoke rules before detection

In `pipeline.py`, `_run_fire_smoke` currently runs unconditionally. Change it to:
1. Load enabled rules for the camera from context
2. If no enabled `fire_smoke` rule exists → skip detection
3. If enabled → run detector with config from the rule (not empty `{}`)

Same pattern applied to `_run_obstruction`: pass rule config to the detector instead of `{}`.

### D4: Add `forbidden_zone` to RuleType enum

Engine already handles it at `engine.py` L199. Adding to enum + frontend dropdown is a one-line change each. The `ForbiddenZoneConfig` TypedDict already exists.

### D5: Remove dead DetectorType values

`DetectorType.image_compare` and `DetectorType.blue_box` are never written by the pipeline. Remove from enum. Existing `detection_events` rows with these values are handled by SQLAlchemy string enum (no DB migration needed — old values simply won't be queried).

### D6: Default config for existing rules

Rules created before this fix have `config = {}`. The engine already has fallback defaults for all keys (e.g., `min_stay_seconds` defaults to 2.0 in engine). No data migration needed — empty config = engine defaults.

## Risks / Trade-offs

- **[Breaking frontend API]** Old frontend bundles cached in browser will still send `threshold_config` → Backend ignores unknown fields, rules persist with empty config → Engine uses defaults. Acceptable degradation — no crash, just defaults until page reload. → Mitigation: version bump in build.
- **[Fire/smoke no longer fires if no rule]** Currently fire/smoke always alerts. After fix, it requires a rule. → Mitigation: seed a default `fire_smoke` rule for all cameras during migration.
- **[`litter` rule type still engine-unhandled]** The engine only processes `obstruction_duration`, `obstruction_area`, `forbidden_zone`. `litter` rules will be configurable but not evaluated. → Mitigation: document as known limitation; litter detection runs via DebrisDetector in pipeline but doesn't use rule thresholds yet.
