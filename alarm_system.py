import os
import json
import time
import sys
import logging
import gc
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from config import ALARM_CONFIG
from camera import DahuaCamera
from image_comparer import ImageComparer
from blue_box_detector import BlueBoxDetector
from yolo_detector import YoloDetector
from wechat_notifier import WechatNotifier

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_CONFIG_FILE = os.path.join(BASE_DIR, 'camera_configs.json')

def load_camera_configs():
    if os.path.exists(JSON_CONFIG_FILE):
        try:
            with open(JSON_CONFIG_FILE, 'r', encoding='utf-8') as f:
                configs = json.load(f)
            if configs:
                return configs
        except Exception as e:
            logger.error(f"读取JSON配置文件失败: {str(e)}")
    
    from config import CAMERA_CONFIGS
    return CAMERA_CONFIGS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(ALARM_CONFIG['log_file'], encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CameraMonitor:
    def __init__(self, camera_config):
        self.camera = DahuaCamera(**camera_config)
        self.location = camera_config['location']
        self.camera_name = f"{camera_config['location']} ({camera_config['ip']})"
        
        camera_dir = os.path.join(ALARM_CONFIG['alarm_images_dir'], camera_config['location'])
        os.makedirs(camera_dir, exist_ok=True)
        self.base_image_path = os.path.join(camera_dir, 'base_image.jpg')
        
        self.object_detected_count = 0
        self.last_diff_area = 0
        self.is_monitoring = False
        self.no_anomaly_count = 0
        
        self.object_first_detected_time = 0
        self.min_stay_seconds = ALARM_CONFIG.get('min_stay_frames', 2) * 1.5
        
        logger.info(f"摄像头监控器初始化: {self.camera_name}")

class AlarmSystem:
    def __init__(self):
        self.camera_monitors = []
        self.current_camera_index = 0
        self.threshold = ALARM_CONFIG['threshold']
        self.alarm_images_dir = ALARM_CONFIG['alarm_images_dir']
        self.static_wait_minutes = ALARM_CONFIG['static_wait_minutes']
        self.wechat_notifier = WechatNotifier()
        
        self.max_no_anomaly = 100
        self.base_image_cache = {}
        
        self.start_time = time.time()
        self.detection_count = 0
        self.alarm_count = 0
        
        # 初始化YOLO检测器 - 使用yolov8n模型，降低置信度阈值以检测更多物体
        self.yolo_detector = YoloDetector(model_name='yolov8n.pt', conf_threshold=0.05)
        
        # 初始化蓝色箱子检测器
        self.blue_box_detector = BlueBoxDetector(min_area=5000)
        
        self._init_cameras()
        logger.info("系统初始化完成")
    
    def _init_cameras(self):
        camera_configs = load_camera_configs()
        for config in camera_configs:
            monitor = CameraMonitor(config)
            self.camera_monitors.append(monitor)
        logger.info(f"已配置 {len(self.camera_monitors)} 个摄像头")
    
    def _log_performance(self, step, elapsed_time):
        logger.debug(f"性能监控 - {step}: {elapsed_time:.3f}秒")
    
    def _cleanup_memory(self):
        gc.collect()
        logger.debug("内存清理完成")
    
    def set_base_image(self, monitor):
        start_time = time.time()
        logger.info(f"正在为 {monitor.camera_name} 设置基准图像...")
        
        camera_dir = os.path.join(self.alarm_images_dir, monitor.location)
        os.makedirs(camera_dir, exist_ok=True)
        temp_path = os.path.join(camera_dir, 'temp_base.jpg')
        result = monitor.camera.capture_image(temp_path)
        
        if result:
            try:
                img = cv2.imdecode(np.fromfile(temp_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    raise Exception("无法读取图像文件")
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(img_rgb)
                draw = ImageDraw.Draw(pil_img)
                
                try:
                    font = ImageFont.truetype('simhei.ttf', 60)
                except:
                    font = ImageFont.truetype('msyh.ttc', 60)
                
                bbox = draw.textbbox((0, 0), '[标准]', font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                img_width, img_height = pil_img.size
                x = img_width - text_width - 10
                y = img_height - text_height - 10
                draw.text((x, y), '[标准]', fill=(0, 255, 0), font=font)
                
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                
                # 使用标准 JPEG 编码确保跨平台兼容
                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 95, int(cv2.IMWRITE_JPEG_OPTIMIZE), 1]
                _, buffer = cv2.imencode('.jpg', img, encode_params)
                if buffer is not None:
                    with open(monitor.base_image_path, 'wb') as f:
                        f.write(buffer)
                else:
                    raise Exception("图像编码失败")
                
                if monitor.camera_name in self.base_image_cache:
                    del self.base_image_cache[monitor.camera_name]
                
                os.remove(temp_path)
                
                elapsed = time.time() - start_time
                logger.info(f"基准图像已保存到: {monitor.base_image_path}")
                self._log_performance("设置基准图像", elapsed)
                return True
            except Exception as e:
                logger.error(f"处理基准图像失败: {str(e)}")
                return False
        else:
            logger.error(f"{monitor.camera_name} 基准图像设置失败")
            return False
    
    def save_raw_image(self, monitor, custom_path=None):
        if custom_path:
            save_path = custom_path
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            camera_dir = os.path.join(self.alarm_images_dir, monitor.location)
            os.makedirs(camera_dir, exist_ok=True)
            save_path = os.path.join(camera_dir, f'raw_{timestamp}.jpg')
        
        result = monitor.camera.capture_image(save_path)
        if result:
            logger.info(f"原始图像保存成功: {save_path}")
            return save_path
        else:
            logger.error(f"{monitor.camera_name} 原始图像保存失败")
            return None
    
    def _load_base_image(self, monitor):
        if monitor.camera_name not in self.base_image_cache:
            start_time = time.time()
            try:
                self.base_image_cache[monitor.camera_name] = cv2.imdecode(np.fromfile(monitor.base_image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            except Exception as e:
                logger.error(f"加载基准图像失败: {str(e)}")
                self.base_image_cache[monitor.camera_name] = None
            elapsed = time.time() - start_time
            self._log_performance("加载基准图像", elapsed)
        return self.base_image_cache[monitor.camera_name]
    
    def check_alarm(self, camera_index=None):
        if not self.camera_monitors:
            logger.error("未配置任何摄像头")
            return
        
        if camera_index is not None:
            self.current_camera_index = camera_index
        
        monitor = self.camera_monitors[self.current_camera_index]
        self.current_camera_index = (self.current_camera_index + 1) % len(self.camera_monitors)
        
        start_time = time.time()
        self.detection_count += 1
        
        logger.info(f"=== 第{self.detection_count}次检测开始 [{monitor.camera_name}] ===")
        
        camera_dir = os.path.join(self.alarm_images_dir, monitor.location)
        os.makedirs(camera_dir, exist_ok=True)
        temp_image_path = os.path.join(camera_dir, 'temp.jpg')
        
        # 创建单个摄像头的检测日志
        camera_log_path = os.path.join(camera_dir, 'detection.log')
        camera_logger = logging.getLogger(f'camera_{monitor.camera_name}')
        if not camera_logger.handlers:
            camera_logger.setLevel(logging.INFO)
            file_handler = logging.FileHandler(camera_log_path, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            camera_logger.addHandler(file_handler)
        
        logger.info("正在抓取监控图像...")
        capture_start = time.time()
        image_data = monitor.camera.capture_image(temp_image_path)
        self._log_performance("抓图", time.time() - capture_start)
        
        if not image_data:
            logger.error(f"{monitor.camera_name} 抓图失败，跳过本次检测")
            camera_logger.error(f"抓图失败，跳过本次检测")
            return
        
        camera_logger.info(f"=== 第{self.detection_count}次检测开始 ===")
        camera_logger.info("正在使用串行检测分析异常（图像对比优先 → YOLO补充）...")
        
        logger.info("正在使用串行检测分析异常（图像对比优先 → YOLO补充）...")
        compare_start = time.time()
        
        # 获取检测模式配置
        enable_yolo = ALARM_CONFIG.get('enable_yolo_detection', True)
        enable_image = ALARM_CONFIG.get('enable_image_comparison', True)
        
        yolo_diff_area = 0
        yolo_boxes = []
        yolo_contours = []
        image_diff_area = 0
        image_boxes = []
        image_contours = []
        image_found_objects = False
        
        # 方法1：基准图像对比（优先执行）
        if enable_image:
            base_image = self._load_base_image(monitor)
            if base_image is not None:
                # 保存基准图像用于对比
                base_temp_path = os.path.join(camera_dir, 'temp_base_for_compare.jpg')
                cv2.imwrite(base_temp_path, base_image)
                
                from image_comparer import ImageComparer
                image_diff_area, image_boxes, image_contours = ImageComparer.find_new_objects(base_temp_path, temp_image_path)
                if image_diff_area is None:
                    image_diff_area = 0
                print(f"【检测】图像对比完成，差异面积: {image_diff_area}, 轮廓数量: {len(image_contours) if image_contours else 0}")
                
                if os.path.exists(base_temp_path):
                    os.remove(base_temp_path)
                
                # 检查图像对比是否在检测区域内发现异常物品
                if image_boxes and image_diff_area > 0:
                    image_found_objects = True
                    camera_logger.info(f"图像对比在检测区域内发现异常物品，差异面积: {image_diff_area}，跳过YOLO检测")
                    print(f"【检测】图像对比在检测区域内发现异常物品，跳过YOLO检测")
                else:
                    camera_logger.info(f"图像对比未在检测区域内发现异常物品，差异面积: {image_diff_area}")
                    print(f"【检测】图像对比未在检测区域内发现异常物品，继续执行YOLO检测")
            else:
                camera_logger.info("无基准图像，跳过图像对比，继续执行YOLO检测")
                print(f"【检测】无基准图像，跳过图像对比，继续执行YOLO检测")
        else:
            camera_logger.info("图像对比已禁用，直接执行YOLO检测")
            print(f"【检测】图像对比已禁用，直接执行YOLO检测")
        
        # 方法2：YOLO物体检测（仅在图像对比未发现异常时执行）
        if enable_yolo and not image_found_objects:
            yolo_diff_area, yolo_boxes, yolo_contours = self.yolo_detector.detect_objects(temp_image_path)
            camera_logger.info(f"YOLO检测完成，差异面积: {yolo_diff_area}, 边界框数量: {len(yolo_boxes) if yolo_boxes else 0}")
            print(f"【检测】YOLO检测完成，差异面积: {yolo_diff_area}, 边界框数量: {len(yolo_boxes) if yolo_boxes else 0}")
        elif image_found_objects:
            camera_logger.info("图像对比已发现异常，YOLO检测已跳过")
            print(f"【检测】图像对比已发现异常，YOLO检测已跳过")
        else:
            camera_logger.info("YOLO检测已禁用")
            print(f"【检测】YOLO检测已禁用")
        
        # 合并检测结果（图像对比优先，若图像对比有结果则使用图像对比，否则使用YOLO）
        if image_found_objects:
            diff_area = image_diff_area
            camera_logger.info(f"使用图像对比结果: {diff_area}")
            print(f"【检测】使用图像对比结果: {diff_area}")
        else:
            diff_area = yolo_diff_area
            camera_logger.info(f"使用YOLO检测结果: {diff_area}")
            print(f"【检测】使用YOLO检测结果: {diff_area}")
        
        # 绘制检测到的物体边界框（红色）并保存
        img = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
        if img is not None:
            # 绘制YOLO检测框
            if yolo_boxes:
                print(f"【检测】绘制 {len(yolo_boxes)} 个YOLO边界框...")
                for (x, y, w, h) in yolo_boxes:
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2, lineType=cv2.LINE_AA)
            
            # 绘制图像对比检测框
            if image_boxes:
                print(f"【检测】绘制 {len(image_boxes)} 个图像对比边界框...")
                for (x, y, w, h) in image_boxes:
                    cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2, lineType=cv2.LINE_AA)
            
            if not yolo_boxes and not image_boxes:
                print("【检测】没有检测到任何物体")
            
            # 始终保存检测结果图像（只保留最后一张，覆盖保存）
            result_image_path = os.path.join(camera_dir, 'detection_result.jpg')
            cv2.imwrite(result_image_path, img)
            print(f"【检测】检测结果图像已保存（覆盖）: {result_image_path}")
        
        camera_logger.info(f"检测结果 - YOLO: {yolo_diff_area}, 图像对比: {image_diff_area}, 最终: {diff_area}")
        logger.info(f"双重检测结果 - YOLO: {yolo_diff_area}, 图像对比: {image_diff_area}, 最终: {diff_area}")
        
        self._log_performance("YOLO检测", time.time() - compare_start)
        
        required_checks = self.static_wait_minutes + 1
        current_time = time.time()
        
        if diff_area > self.threshold:
            monitor.no_anomaly_count = 0
            if not monitor.is_monitoring:
                monitor.object_detected_count = 1
                monitor.is_monitoring = True
                monitor.last_diff_area = diff_area
                monitor.object_first_detected_time = current_time
                camera_logger.info(f"检测到物体，开始监控，需连续检测 {required_checks} 次确认")
                logger.info(f"【检测到物体】开始监控，需连续检测 {required_checks} 次确认，物体需停留 {monitor.min_stay_seconds:.1f} 秒...")
            else:
                monitor.object_detected_count += 1
                
                elapsed_since_detection = current_time - monitor.object_first_detected_time
                camera_logger.info(f"监控中，物体已停留 {elapsed_since_detection:.1f} 秒，连续检测 {monitor.object_detected_count} 次")
                logger.info(f"【监控中】物体已停留 {elapsed_since_detection:.1f} 秒，连续检测 {monitor.object_detected_count} 次")
                
                if monitor.object_detected_count >= required_checks and elapsed_since_detection >= monitor.min_stay_seconds:
                    camera_logger.info(f"连续检测{monitor.object_detected_count}次确认，触发报警")
                    logger.info(f"【连续检测{monitor.object_detected_count}次确认，物体停留{elapsed_since_detection:.1f}秒】触发报警")
                    alarm_start = time.time()
                    self.trigger_alarm(monitor, image_data, diff_area)
                    self._log_performance("报警处理", time.time() - alarm_start)
                    self.alarm_count += 1
                    monitor.is_monitoring = False
                    monitor.object_detected_count = 0
                    monitor.object_first_detected_time = 0
                else:
                    remaining_checks = required_checks - monitor.object_detected_count
                    remaining_time = max(0, monitor.min_stay_seconds - elapsed_since_detection)
                    camera_logger.info(f"还需检测 {remaining_checks} 次，物体还需停留 {remaining_time:.1f} 秒")
                    logger.info(f"【监控中】还需检测 {remaining_checks} 次，物体还需停留 {remaining_time:.1f} 秒")
                    monitor.last_diff_area = diff_area
        else:
            monitor.no_anomaly_count += 1
            camera_logger.info(f"无异常，连续无异常次数: {monitor.no_anomaly_count}/{self.max_no_anomaly}")
            logger.info(f"【无异常】连续无异常次数: {monitor.no_anomaly_count}/{self.max_no_anomaly}")
            
            if monitor.no_anomaly_count >= self.max_no_anomaly:
                uptime = time.time() - self.start_time
                logger.info(f"【连续{self.max_no_anomaly}次无异常】程序自动退出")
                logger.info(f"系统运行统计 - 总检测次数: {self.detection_count}, 报警次数: {self.alarm_count}, 运行时间: {int(uptime/60)}分钟")
                print(f"\n连续{self.max_no_anomaly}次检测无异常，程序自动退出")
                sys.exit(0)
            
            if monitor.is_monitoring:
                logger.info("【物体已离开】重置监控状态")
            monitor.is_monitoring = False
            monitor.object_detected_count = 0
            monitor.last_diff_area = 0
        
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        
        elapsed = time.time() - start_time
        self._log_performance("单次检测总耗时", elapsed)
        logger.info(f"=== 第{self.detection_count}次检测结束 [{monitor.camera_name}] (耗时: {elapsed:.3f}秒) ===\n")
        
        if self.detection_count % 10 == 0:
            self._cleanup_memory()
            uptime = time.time() - self.start_time
            logger.info(f"系统运行统计 - 总检测次数: {self.detection_count}, 报警次数: {self.alarm_count}, 运行时间: {int(uptime/60)}分钟")
    
    def trigger_alarm(self, monitor, image_data, diff_area):
        camera_dir = os.path.join(self.alarm_images_dir, monitor.location)
        os.makedirs(camera_dir, exist_ok=True)
        # 只保留最后一张报警图片（覆盖保存）
        alarm_image_path = os.path.join(camera_dir, 'alarm_last.jpg')
        
        img = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
        
        if img is not None:
            camera_dir = os.path.join(self.alarm_images_dir, monitor.location)
            temp_current_path = os.path.join(camera_dir, 'temp_current_for_compare.jpg')
            
            try:
                # 保存当前图像用于检测
                _, buffer = cv2.imencode('.jpg', img)
                with open(temp_current_path, 'wb') as f:
                    f.write(buffer)
                
                print(f"【报警】开始串行检测（图像对比优先 → YOLO补充），图像路径: {temp_current_path}")
                
                # 方法1：基准图像对比（优先执行）
                image_diff_area = 0
                image_boxes = []
                image_contours = []
                image_found_objects = False
                
                base_image = self._load_base_image(monitor)
                if base_image is not None:
                    base_temp_path = os.path.join(camera_dir, 'temp_base_for_alarm.jpg')
                    cv2.imwrite(base_temp_path, base_image)
                    
                    from image_comparer import ImageComparer
                    image_diff_area, image_boxes, image_contours = ImageComparer.find_new_objects(base_temp_path, temp_current_path)
                    if image_diff_area is None:
                        image_diff_area = 0
                    print(f"【报警】图像对比完成，diff_area={image_diff_area}, 轮廓数量={len(image_contours) if image_contours else 0}")
                    
                    if os.path.exists(base_temp_path):
                        os.remove(base_temp_path)
                    
                    if image_boxes and image_diff_area > 0:
                        image_found_objects = True
                        print(f"【报警】图像对比已发现异常，跳过YOLO检测")
                    else:
                        print(f"【报警】图像对比未发现异常，继续执行YOLO检测")
                else:
                    print(f"【报警】无基准图像，跳过图像对比，继续执行YOLO检测")
                
                # 方法2：YOLO检测（仅在图像对比未发现异常时执行）
                yolo_diff_area = 0
                yolo_boxes = []
                yolo_contours = []
                
                if not image_found_objects:
                    yolo_diff_area, yolo_boxes, yolo_contours = self.yolo_detector.detect_objects(temp_current_path)
                    print(f"【报警】YOLO检测完成，diff_area={yolo_diff_area}, boxes数量={len(yolo_boxes) if yolo_boxes else 0}")
                else:
                    print(f"【报警】YOLO检测已跳过")
                
                # 合并检测结果（图像对比优先）
                bounding_boxes = []
                contours_list = []
                
                if image_found_objects:
                    bounding_boxes = image_boxes
                    contours_list = image_contours if image_contours else []
                    print(f"【报警】使用图像对比结果: {len(bounding_boxes)} 个边界框")
                elif yolo_boxes:
                    bounding_boxes = yolo_boxes
                    contours_list = yolo_contours if yolo_contours else []
                    print(f"【报警】使用YOLO检测结果: {len(bounding_boxes)} 个边界框")
                else:
                    print(f"【报警】两种方法均未检测到物体")
                
                print(f"【报警】综合检测结果: YOLO={yolo_diff_area}, 图像对比={image_diff_area}, 总边界框={len(bounding_boxes)}")
                
                # 绘制检测到的物体（使用红色矩形框）
                if bounding_boxes:
                    print(f"【报警】绘制 {len(bounding_boxes)} 个矩形框")
                    for (x, y, w, h) in bounding_boxes:
                        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2, lineType=cv2.LINE_AA)
                else:
                    print("【报警】没有边界框可绘制")
            finally:
                if os.path.exists(temp_current_path):
                    os.remove(temp_current_path)
    
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        location_name = monitor.location
        position_info = f"{location_name} ({monitor.camera.ip}:{monitor.camera.port})"
        
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(pil_img)
        
        try:
            font = ImageFont.truetype('simhei.ttf', 40)
        except:
            font = ImageFont.truetype('msyh.ttc', 40)
        
        draw.text((10, 10), '民盈国贸城AI巡检预警', fill=(255, 0, 0), font=font)
        draw.text((10, 60), f'时间: {current_time}', fill=(255, 0, 0), font=font)
        draw.text((10, 110), f'位置: {location_name}', fill=(255, 0, 0), font=font)
        
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        try:
            success = cv2.imwrite(alarm_image_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if not success:
                raise Exception("cv2.imwrite 返回失败")
        except:
            _, buffer = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if buffer is not None:
                with open(alarm_image_path, 'wb') as f:
                    f.write(buffer)
        
        alarm_message = f"【民盈国贸城AI巡检预警】\n时间: {current_time}\n位置: {location_name}"
        logger.error(alarm_message)
        
        print("\n" + "="*50)
        print(alarm_message)
        print("="*50 + "\n")
        
        self.wechat_notifier.send_alarm(alarm_message, alarm_image_path)
    
    def set_all_base_images(self):
        for monitor in self.camera_monitors:
            print(f"\n正在为 {monitor.camera_name} 设置基准图像...")
            self.set_base_image(monitor)
    
    def save_all_raw_images(self):
        for monitor in self.camera_monitors:
            print(f"\n正在为 {monitor.camera_name} 保存原始图像...")
            self.save_raw_image(monitor)
    
    def list_cameras(self):
        print("\n=== 已配置的摄像头列表 ===")
        for i, monitor in enumerate(self.camera_monitors, 1):
            base_exists = os.path.exists(monitor.base_image_path)
            status = "已设置基准图像" if base_exists else "未设置基准图像"
            print(f"  {i}. {monitor.camera_name} - {status}")
        print("=" * 40)
    
    def manual_capture_base_image(self, camera_index=None):
        if camera_index is None:
            self.list_cameras()
            print("\n请选择要设置基准图像的摄像头序号 (输入 0 取消):")
            try:
                camera_index = int(input().strip())
                if camera_index == 0:
                    print("操作已取消")
                    return False
                if camera_index < 1 or camera_index > len(self.camera_monitors):
                    print("无效的序号，请重新选择")
                    return False
            except ValueError:
                print("输入无效，请输入数字")
                return False
        
        monitor = self.camera_monitors[camera_index - 1]
        print(f"\n正在为 {monitor.camera_name} 抓拍基准图像...")
        
        camera_dir = os.path.join(self.alarm_images_dir, monitor.location)
        os.makedirs(camera_dir, exist_ok=True)
        temp_path = os.path.join(camera_dir, 'temp_base_preview.jpg')
        result = monitor.camera.capture_image(temp_path)
        
        if not result:
            print(f"抓图失败，请检查摄像头连接")
            return False
        
        print(f"\n图像已抓拍，保存路径: {temp_path}")
        print("是否确认将此图像设置为基准图像? (y/n):")
        choice = input().strip().lower()
        
        if choice == 'y':
            try:
                img = cv2.imdecode(np.fromfile(temp_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    raise Exception("无法读取图像文件")
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(img_rgb)
                draw = ImageDraw.Draw(pil_img)
                
                try:
                    font = ImageFont.truetype('simhei.ttf', 60)
                except:
                    font = ImageFont.truetype('msyh.ttc', 60)
                
                bbox = draw.textbbox((0, 0), '[标准]', font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                img_width, img_height = pil_img.size
                x = img_width - text_width - 10
                y = img_height - text_height - 10
                draw.text((x, y), '[标准]', fill=(0, 255, 0), font=font)
                
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                
                # 使用标准 JPEG 编码确保跨平台兼容
                encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 95, int(cv2.IMWRITE_JPEG_OPTIMIZE), 1]
                _, buffer = cv2.imencode('.jpg', img, encode_params)
                if buffer is not None:
                    with open(monitor.base_image_path, 'wb') as f:
                        f.write(buffer)
                else:
                    raise Exception("图像编码失败")
                
                if monitor.camera_name in self.base_image_cache:
                    del self.base_image_cache[monitor.camera_name]
                
                os.remove(temp_path)
                
                print(f"基准图像已成功设置: {monitor.base_image_path}")
                logger.info(f"{monitor.camera_name} 基准图像已手动更新")
                return True
            except Exception as e:
                print(f"处理基准图像失败: {str(e)}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False
        else:
            print("已取消设置基准图像")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
    
    def adjust_base_image_interactive(self):
        while True:
            print("\n=== 基准图像手动调整 ===")
            print("1. 查看摄像头列表")
            print("2. 为指定摄像头抓拍基准图像")
            print("3. 为所有摄像头重新抓拍基准图像")
            print("4. 返回主菜单")
            print("=" * 30)
            print("请输入操作序号:")
            
            try:
                choice = int(input().strip())
            except ValueError:
                print("输入无效，请输入数字")
                continue
            
            if choice == 1:
                self.list_cameras()
            elif choice == 2:
                self.manual_capture_base_image()
            elif choice == 3:
                print("确定要为所有摄像头重新抓拍基准图像吗? (y/n):")
                confirm = input().strip().lower()
                if confirm == 'y':
                    self.set_all_base_images()
                else:
                    print("操作已取消")
            elif choice == 4:
                print("返回主菜单")
                break
            else:
                print("无效的选择，请重新输入")