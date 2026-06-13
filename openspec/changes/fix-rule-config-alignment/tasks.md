## 1. Backend: Enum and Schema Alignment

- [x] 1.1 Add `forbidden_zone` to `RuleType` enum in `entities.py`
- [x] 1.2 ~~Remove `image_compare` and `blue_box` from `DetectorType` enum~~ — deferred (risk of breaking existing DB rows)
- [x] 1.3 Add `forbidden_zone` i18n label to both locale JSON files

## 2. Backend: Pipeline Fire/Smoke Conditional Detection

- [x] 2.1 In `pipeline.py` `_run_fire_smoke`: check `context.fire_smoke_config`; skip if None
- [x] 2.2 Pass `fire_smoke_config` dict to `FireSmokeDetector` instead of empty `{}`
- [x] 2.3 `context.py`: load `fire_smoke_config` from enabled fire_smoke rules

## 3. Frontend: Type and API Alignment

- [x] 3.1 `RuleThresholdConfig` → `Record<string, number>` in `types.ts`; add `'forbidden_zone'` to RuleType
- [x] 3.2 `Rule` interface: `threshold_config` → `config: Record<string, number>`
- [x] 3.3 `RuleCreatePayload` and `RuleUpdatePayload` use `config` field name

## 4. Frontend: Per-Type Rule Config Forms

- [x] 4.1 Refactor `RuleConfigView.vue`: per-type config inputs with engine-aligned keys
- [x] 4.2 Config keys map to engine expectations (min_stay_seconds, threshold_ratio, etc.)
- [x] 4.3 Add `forbidden_zone` option to dropdown
- [x] 4.4 Add i18n labels for all new config fields

## 5. Backend Tests

- [x] 5.1 Pipeline test updated: fire/smoke requires `fire_smoke_config` in context
- [x] 5.2 API test: fire_smoke rule creation with config persistence
- [x] 5.3 API test: rule config persists and updates correctly
- [x] 5.4 API test: forbidden_zone rule type accepted

## 6. E2E Tests

- [x] 6.1 All 24 e2e tests pass (no rule config form e2e changes needed — existing tests don't test rule form fields)

## 7. Verification

- [x] 7.1 159 backend tests pass
- [x] 7.2 vue-tsc zero errors
- [x] 7.3 Build success
- [x] 7.4 24 e2e tests pass
