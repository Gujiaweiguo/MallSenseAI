## 1. Backend: RuleDefinition Model + API

- [ ] 1.1 Add `RuleDefinition` model to `entities.py` (id, name, rule_type, config, description, timestamps)
- [ ] 1.2 Add `definition_id` FK column to `Rule` table (nullable during migration, then required)
- [ ] 1.3 Create `schemas/rule_definition.py` (Create, Update, Response)
- [ ] 1.4 Create `api/rule_definitions.py` router with full CRUD
- [ ] 1.5 Register router in `main.py` at `/api/rule-definitions`
- [ ] 1.6 Update `schemas/rule.py` — RuleCreate/RuleUpdate use `definition_id` instead of `rule_type`+`config`
- [ ] 1.7 Update RuleResponse to include nested definition info (name, type, config)

## 2. Backend: Pipeline + Context Changes

- [ ] 2.1 `context.py`: JOIN RuleAssignment → RuleDefinition in `load_camera_context`
- [ ] 2.2 `context.py`: Extract `fire_smoke_config` from joined definition instead of flat rule config
- [ ] 2.3 `ActiveRule` struct: add `definition_name`, use definition's `rule_type` and `config`
- [ ] 2.4 `pipeline.py`: no direct changes needed (reads from context which now resolves definitions)

## 3. Backend: Data Migration

- [ ] 3.1 Write migration script: for each unique (rule_type, config) → create RuleDefinition → update Rule.definition_id
- [ ] 3.2 Auto-generate definition names (e.g., "火灾烟雾检测-默认", "阻塞时长-默认")
- [ ] 3.3 Test migration on dev DB

## 4. Frontend: RuleDefinitionView (New Page)

- [ ] 4.1 Create `RuleDefinitionView.vue` — table (name, type, description, config, assignment count) + create/edit form
- [ ] 4.2 Add route `/rule-definitions` in router
- [ ] 4.3 Add nav item "规则定义" in MainLayout
- [ ] 4.4 Add `RuleDefinition` type + API functions to `types.ts` and `resources.ts`
- [ ] 4.5 Add i18n keys for rule definition UI

## 5. Frontend: Refactor RuleConfigView (Assignment Flow)

- [ ] 5.1 Replace create-from-scratch form with "select definition → apply" flow
- [ ] 5.2 Table shows definition name + type instead of raw rule_type
- [ ] 5.3 Edit only allows ROI/priority/enabled changes (thresholds link to definition page)
- [ ] 5.4 Hide ROI selector for fire_smoke type assignments
- [ ] 5.5 Add link from assignment row to definition detail

## 6. Backend Tests

- [ ] 6.1 Test rule definition CRUD (create, list, update, delete)
- [ ] 6.2 Test delete rejection when assignments exist
- [ ] 6.3 Test rule assignment with definition_id
- [ ] 6.4 Test pipeline resolves definition config correctly

## 7. E2E Tests

- [ ] 7.1 Update existing rule config e2e tests for new assignment flow
- [ ] 7.2 Add rule definition page e2e test
- [ ] 7.3 Update dashboard/navigation mocks for new nav item

## 8. Verification

- [ ] 8.1 `python3 -m pytest backend/tests/ -q` — all pass
- [ ] 8.2 `npx vue-tsc --noEmit` — zero errors
- [ ] 8.3 `npm run build` — success
- [ ] 8.4 `npx playwright test` — all pass
