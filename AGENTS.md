# AGENTS.md

## Repo identity
- Python camera alarm system for corridor obstruction detection. Main runnable surfaces are `main.py` (interactive CLI alarm loop), `web_server.py` (Flask API on port 5000), and `camera_manager.py` (Tkinter desktop tool).
- There is no root `README`, CI workflow, or test suite. Verify changes with focused manual runs.

## Highest-value source files
- `rules/project_rules.md` is the main repo instruction file. Follow it, but trust runtime code when rules and implementation disagree.
- `config.py` is the central config file for alarm thresholds, storage paths, webhook settings, and the fallback `CAMERA_CONFIGS` list.
- `camera_configs.json` is the runtime camera list actually loaded by `main.py` and `alarm_system.py` when present.

## Entry points and boundaries
- `main.py`: menu-driven CLI for monitoring tests, loop checks, and base image adjustment.
- `web_server.py`: camera CRUD, snapshot, and base-image API. Runs with `python web_server.py` and binds `0.0.0.0:5000`.
- `camera_manager.py`: Tkinter GUI for camera management, preview, and polygon zone marking.
- `alarm_system.py`: orchestration layer that wires `DahuaCamera`, `ImageComparer`, `YoloDetector`, and `WechatNotifier` together.

## Commands you can actually run
- Install baseline deps: `pip install -r requirements.txt`
- Run CLI: `python main.py`
- Run web server: `python web_server.py`
- Run desktop manager: `python camera_manager.py`
- There is no repo-defined lint, typecheck, or test command.

## Dependency / environment gotchas
- `requirements.txt` is incomplete relative to imports. Runtime code also needs `flask`, `flask_cors`, and `ultralytics`.
- `tkinter` is used by `camera_manager.py`; on some Linux environments it requires an OS package, not just pip.
- YOLO weights live in repo root (`yolov8n.pt`, `yolov8s.pt`, `yolov8x.pt`) and detection code imports them directly from there.

## Config and data flow quirks
- Camera config has two sources: `camera_configs.json` and `config.py`. `main.py` / `alarm_system.py` prefer JSON when it exists, then fall back to `config.py`.
- `camera_manager.py` writes both files: it saves JSON and then regex-rewrites the `CAMERA_CONFIGS` block in `config.py`. Be careful editing camera config logic; drift between the two files is a real repo-specific failure mode.
- Alarm artifacts are stored under `alarm_images/<camera location>/`, including `base_image.jpg`, `safe_zones.json`, and per-camera logs.

## Detection-specific facts worth knowing
- Detection is not a single model call. `alarm_system.py` combines image comparison and YOLO-based detection under `ALARM_CONFIG['detection_mode']`.
- Zone filtering is implemented by loading `safe_zones.json` beside each camera’s images. The rules mention `region_filter.py`, but that file does not exist in the repo.
- `BlueBoxDetector` is instantiated in `alarm_system.py`; verify actual call sites before assuming blue-box detection is part of the active path.

## Known mismatches and stale artifacts
- Unified image size is `1000x750` in `camera.py` and `web_server.py`, but `camera_manager.py` still resizes preview captures to `1600x1200`. Treat image-size changes as cross-entrypoint work.
- `debug_image_compare.py` and some inline test/demo paths reference Windows paths like `f:\GMweb\...`; treat them as local debug artifacts, not production workflow.
- `rules/project_rules.md` says functions/variables should use camelCase, but the real codebase heavily uses Python snake_case. Match surrounding file style instead of forcing the rule literally.

## OpenCode / OpenSpec context
- OpenSpec is present under `openspec/`, but `openspec/config.yaml` is still the default scaffold with no project-specific context.
- `.opencode/` exists for local OpenCode tooling; do not treat `.opencode/node_modules/` as application code.

## Practical verification guidance
- Because there is no automated suite, prefer the smallest runnable check for the surface you changed: launch the specific entrypoint or exercise the exact code path you touched.
- For camera/config changes, verify both file persistence (`camera_configs.json` and, if relevant, `config.py`) and the resulting files under `alarm_images/`.
