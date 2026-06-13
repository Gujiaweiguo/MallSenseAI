## Why

The rule configuration UI is cosmetic — thresholds entered by operators never reach the detection engine. A schema drift between frontend (`threshold_config` with keys `threshold/min_area/max_count/duration_seconds`) and backend (`config` with keys `min_stay_seconds/threshold_ratio/cooldown_seconds`) means all user-configured rule parameters are silently dropped. Additionally, fire/smoke detection runs unconditionally for all cameras regardless of whether a rule exists, and the engine-supported `forbidden_zone` mode is invisible in the UI.

## What Changes

- **BREAKING**: Align frontend field name `threshold_config` → `config` to match backend ORM column and schema
- Replace the single generic threshold form with per-rule-type config forms that map 1:1 to engine-consumed keys
- Make fire/smoke detection conditional on an enabled `fire_smoke` rule for that camera (currently unconditional)
- Add `forbidden_zone` to `RuleType` enum and frontend dropdown (engine already supports it)
- Remove unused `DetectorType.image_compare` and `blue_box` enum values (dead code from early design)
- Wire `DebrisConfig` / `FireSmokeConfig` TypedDicts into pipeline detector calls (currently passed `{}`)

## Capabilities

### New Capabilities

_(none — all changes modify existing capabilities)_

### Modified Capabilities

- `obstruction-rules`: Rule config schema aligned between frontend and engine; per-type config forms; `forbidden_zone` rule type exposed
- `advanced-detectors`: Fire/smoke detection now conditional on enabled rules instead of unconditional; detector config wired from rule thresholds

## Impact

- **Frontend**: `RuleConfigView.vue` (per-type form refactor), `types.ts` (field rename + new config shapes), `resources.ts` (API field alignment)
- **Backend**: `entities.py` (RuleType enum), `pipeline.py` (fire/smoke rule check + detector config wiring), `schemas/rule.py` (no structural change, but frontend alignment)
- **Database**: Existing rules may have empty `config` — migration to populate sensible defaults
- **Tests**: Rule engine tests, pipeline tests, e2e rule config tests all need updates
