---
alwaysApply: true
description: "本项目为 摄像头智能检测报警系统，遵循四层架构、多策略融合检测、企业微信推送；所有生成/修改代码必须严格遵守本规则。"
---

# 项目规则：摄像头智能检测报警系统（强制遵守）

## 1. 项目定位与架构
- 项目名称：摄像头智能检测报警系统
- 整体架构：**前端界面层 → 核心检测层 → 数据存储层 → 通知推送层**，分层明确、单向依赖。
- 检测策略：**YOLO（蓝色箱子/通用物体） + 背景差分法（image_comparer） + 检测区域过滤器**，多策略融合，降低误报。
- 所有代码必须符合此架构，不得跨层直接调用、不得新增架构层级。

## 2. 技术栈约束（严格）
- 语言：Python 3.10+
- 核心库：OpenCV、YOLOv8（yolov8s.pt）、NumPy、Pillow
- 界面：PyQt / Tkinter（camera_manager.py、alarm_system.py）
- 推送：企业微信 Webhook（wechat_notifier.py）
- 配置：统一写在 config.py，不得硬编码参数。

## 3. 目录与文件规范（必须严格对齐）
### 3.1 整体结构
项目根目录 /
├── .trae/rules/project_rules.md # 本规则文件
├── camera_manager.py # 摄像头管理界面层
├── alarm_system.py # 报警系统界面层
├── blue_box_detector.py # 核心检测层：蓝色箱子（YOLO）
├── yolo_detector.py # 核心检测层：通用物体（YOLO）
├── image_comparer.py # 核心检测层：背景差分
├── region_filter.py # 核心检测层：检测区域过滤器
├── wechat_notifier.py # 通知推送层：企业微信
├── config.py # 全局配置
└── alarm_images/ # 数据存储层：报警图片 / 基准图 / 配置

### 3.2 各层职责（禁止越权）
- **前端界面层（camera_manager.py / alarm_system.py）**
  - 只负责：界面渲染、实时预览、区域标记、报警记录展示。
  - 不得写检测逻辑、不得直接操作摄像头底层、不得直接调用推送。

- **核心检测层（detector / comparer / filter）**
  - 输入：摄像头帧、基准图、检测区域配置。
  - 输出：是否报警、报警类型、报警截图。
  - 必须通过 **region_filter** 过滤：只在标记区域内检测。
  - 多策略融合逻辑：
    1. blue_box_detector：颜色+空间过滤，检测蓝色箱子。
    2. yolo_detector：检测人体/关键物体，过滤无效目标。
    3. image_comparer：背景差分，检测变化区域，过滤光影干扰。
    4. 任意策略触发 + 区域内有效 → 判定报警。

- **数据存储层（alarm_images/）**
  - 结构：`alarm_images/{摄像头ID}/`
    - `base_image.jpg`：基准背景图
    - `safe_zones.json`：检测区域坐标（JSON 格式）
    - `alarm_YYYYMMDD_HHMMSS.jpg`：报警截图
  - 所有文件读写必须走此目录，不得散落其他位置。

- **通知推送层（wechat_notifier.py）**
  - 只负责：企业微信 Webhook 推送、报警信息格式化。
  - 推送内容：时间、摄像头ID、报警类型、截图链接/附件。
  - 从 config.py 读取 WECHAT_CONFIG，不得硬编码 Webhook URL。

## 4. 关键配置项（统一在 config.py）
- 灵敏度：`sensitivity = 35`
- 最小轮廓面积：`min_contour_area = 5000`
- 差分阈值：`diff_threshold = 20`
- YOLO 模型路径：`yolov8s.pt`
- 企业微信配置：`WECHAT_CONFIG = {webhook_url, ...}`
- 新增/修改配置必须在 config.py，不得分散在业务代码。

## 5. 命名规范
- 文件名：`snake_case.py`（如 camera_manager.py）
- 类名：`PascalCase`（如 BlueBoxDetector、ImageComparer）
- 函数/变量：`camelCase`（如 detectBlueBox、currentFrame）
- 常量：全大写（如 MIN_CONTOUR_AREA）

## 6. 代码质量与注释
- 所有公共函数/类必须有**中文文档字符串**（功能、参数、返回值）。
- 关键逻辑（检测判定、区域过滤、报警触发）必须加**行内中文注释**。
- 禁止：
  - 硬编码路径、阈值、密钥；
  - 提交代码保留 print/调试日志；
  - 跨层直接调用（如界面层直接调用 wechat_notifier）。

## 7. 核心流程强制规范
### 7.1 报警触发流程
1. camera_manager → 读取摄像头帧 → 传给核心检测层。
2. 核心检测层：
   - 并行/串行执行 blue_box_detector、yolo_detector、image_comparer。
   - 所有结果经 region_filter 校验（是否在标记区域内）。
3. 满足报警条件 → 保存截图到 alarm_images/。
4. 调用 wechat_notifier → 推送报警消息。
5. alarm_system 展示最新报警记录。

### 7.2 检测区域标记格式
- 存储：`alarm_images/{摄像头ID}/safe_zones.json`
- 格式：JSON 数组，每个区域为 `[[x1,y1],[x2,y2],...]`（多边形坐标）
- 界面层负责绘制/编辑，检测层负责读取并过滤。

## 8. 错误处理与日志
- 摄像头读取失败：打印错误、重试 3 次、退出当前摄像头，不崩溃。
- 检测异常：记录日志、跳过当前帧、继续运行。
- 推送失败：重试 2 次、记录日志、不阻塞检测流程。

## 9. 安全与性能
- 不得在代码中暴露 Webhook URL、摄像头地址等敏感信息（统一在 config.py，可加 .gitignore）。
- 检测循环控制帧率，避免 CPU 占用过高。
- 报警截图只保留最近 30 天，可自动清理。

## 10. 回答与生成要求
- 所有回复用**中文**，简洁专业。
- 生成代码必须**严格对齐上述架构、文件、命名、配置规范**。
- 新增功能必须说明属于哪一层、如何与现有模块交互。