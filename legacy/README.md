# MallSenseAI Legacy Isolation Plan

This directory is reserved for the existing Flask/Tkinter/CLI camera alarm system during the platform migration. T01 does **not** move files; it records the isolation boundary so a later cutover can move them safely without deleting source data.

## File classification

| File / path | Classification | Notes |
|---|---|---|
| `blue_box_detector.py` | move to `legacy/` | Dead/legacy detector compatibility code. |
| `convert_coordinates.py` | move to `legacy/` | One-off coordinate conversion helper. |
| `debug_image_compare.py` | move to `legacy/` | Local debug script with non-production paths. |
| `safe_zones.json` | move to `legacy/` | Root-level legacy ROI artifact; camera-specific ROI source remains under `alarm_images/`. |
| `main.py` | new-platform-replace | Current CLI entry point; later copied/moved as `legacy/main.py` for minimum viable legacy runtime. |
| `web_server.py` | new-platform-replace | Current Flask API; not reused by new FastAPI platform. |
| `camera_manager.py` | new-platform-replace | Current Tkinter manager; contains 1600x1200 preview behavior. |
| `alarm_system.py` | new-platform-replace | Legacy orchestration layer. |
| `camera.py` | new-platform-replace | Legacy Dahua camera integration. |
| `image_comparer.py` | new-platform-replace | Legacy image comparison detector. |
| `yolo_detector.py` | new-platform-replace | Legacy YOLO detector wrapper. |
| `wechat_notifier.py` | new-platform-replace | Legacy WeCom webhook notifier. |
| `update_base_image.py` | new-platform-replace | Legacy base-image update utility. |
| `config.py` | keep in root during migration | Shared legacy source; do not edit until cutover. |
| `camera_configs.json` | keep in root during migration | Primary legacy camera source; contains duplicate location collision. |
| `requirements.txt` | keep in root during migration | Legacy dependency record. |
| `alarm_images/` | shared asset | Remains accessible to both legacy and platform migration jobs. |
| `yolov8n.pt`, `yolov8s.pt`, `yolov8x.pt` | shared asset | Model weights remain in root during coexistence. |

## Move plan

1. Create `legacy/` package and copy legacy runtime files into it without deleting root originals.
2. Adjust copied legacy imports to prefer `legacy.*` modules while allowing root shared assets via `../alarm_images` and `../yolov8*.pt`.
3. Preserve root `config.py` and `camera_configs.json` as read-only migration inputs until the database is authoritative.
4. After platform parity is verified, freeze root legacy entry points and document final deletion in the T13 cutover plan.

## Shared assets that remain in root

- `alarm_images/` including `base_image.jpg`, `safe_zones.json`, `detection.log`, and evidence images.
- `yolov8*.pt` model weights.
- `camera_configs.json` and `config.py` until migration is complete and audited.

## Minimum viable legacy entry point

The target runtime after physical isolation is `legacy/main.py`. It should keep the current CLI behavior and resolve shared assets relative to the repository root. Until the move is executed, root `main.py` remains the operational fallback.
