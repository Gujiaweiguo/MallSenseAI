import cv2
import numpy as np
from config import ALARM_CONFIG

class ImageComparer:
    @staticmethod
    def detect_base_objects(image_path):
        """检测基准图像中的物体（视为异常）"""
        try:
            img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                return []
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            kernel = np.ones((7, 7), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            base_objects = []
            min_area = ALARM_CONFIG.get('base_object_min_area', 5000)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > min_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else float('inf')
                    
                    if aspect_ratio < 20:
                        roi = gray[y:y+h, x:x+w]
                        mean_val = np.mean(roi)
                        std_val = np.std(roi)
                        
                        if mean_val > 30 and mean_val < 230 and std_val > 5:
                            base_objects.append((x, y, w, h, area))
            
            return base_objects
        except Exception as e:
            print(f"检测基准图像物体异常: {str(e)}")
            return []
    
    @staticmethod
    def calculate_difference(image1_path, image2_path):
        try:
            img1 = cv2.imdecode(np.fromfile(image1_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            img2 = cv2.imdecode(np.fromfile(image2_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            if img1 is None or img2 is None:
                return None
            
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
            img_height, img_width = img2.shape[:2]
            image_area = img_height * img_width
            
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
            
            sensitivity = ALARM_CONFIG.get('sensitivity', 35)
            
            diff_gray = cv2.absdiff(gray2, gray1)
            
            # 调试：检查灰度差异图像的统计信息
            gray_diff_mean = np.mean(diff_gray)
            gray_diff_max = np.max(diff_gray)
            gray_diff_min = np.min(diff_gray)
            print(f"灰度差异统计 - 均值: {gray_diff_mean:.2f}, 最大值: {gray_diff_max}, 最小值: {gray_diff_min}")
            
            # 使用固定阈值直接对灰度差异进行二值化
            threshold_value = ALARM_CONFIG.get('diff_threshold', 20)
            _, thresh = cv2.threshold(diff_gray, threshold_value, 255, cv2.THRESH_BINARY)
            
            # 调试：检查二值化后的白色像素数量
            white_pixels = cv2.countNonZero(thresh)
            print(f"二值化后白色像素数: {white_pixels}, 阈值: {threshold_value}")
            
            # 添加腐蚀操作分离连接的物体，避免形成超大轮廓
            erosion_kernel = np.ones((3, 3), np.uint8)
            thresh = cv2.erode(thresh, erosion_kernel, iterations=1)
            
            # 调试：检查二值化后的白色像素数量
            white_pixels = cv2.countNonZero(thresh)
            print(f"二值化后白色像素数: {white_pixels}, 使用自适应阈值")
            
            kernel_size = int(5 + (sensitivity / 100) * 3)
            if kernel_size % 2 == 0:
                kernel_size += 1
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 调试：检查轮廓数量
            print(f"检测到轮廓数量: {len(contours)}")
            
            total_diff_area = 0
            
            human_filter_enabled = ALARM_CONFIG.get('human_filter_enabled', True)
            small_object_filter = ALARM_CONFIG.get('small_object_filter', True)
            detection_zone = ALARM_CONFIG.get('detection_zone', 'ground_only')
            
            # 加载检测区域
            detection_zones = []
            try:
                import os
                import json
                base_dir = os.path.dirname(image1_path)
                detection_zones_path = os.path.join(base_dir, 'safe_zones.json')
                if os.path.exists(detection_zones_path):
                    with open(detection_zones_path, 'r', encoding='utf-8') as f:
                        detection_zones = json.load(f)
                    print(f"加载检测区域：{len(detection_zones)} 个")
            except Exception as e:
                print(f"加载检测区域失败：{str(e)}")
                detection_zones = []
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > ALARM_CONFIG['min_contour_area']:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else float('inf')
                    
                    # 检查是否在检测区域内（只检测检测区域内的物体）
                    if not ImageComparer._is_in_detection_zone(x, y, w, h, detection_zones):
                        print(f"物体 ({x}, {y}, {w}, {h}) 不在检测区域内，跳过")
                        continue
                    
                    # 人体过滤
                    if human_filter_enabled and ImageComparer._is_human_like(w, h, area, contour):
                        continue
                    
                    # 简化：只检查宽高比，移除其他过滤条件
                    if aspect_ratio < 20:
                        roi2 = gray2[y:y+h, x:x+w]
                        mean2 = np.mean(roi2)
                        std2 = np.std(roi2)
                        
                        if mean2 > 20 and mean2 < 240 and std2 > 5:
                            total_diff_area += area
            
            if ALARM_CONFIG.get('detect_base_object', False):
                base_objects = ImageComparer.detect_base_objects(image1_path)
                for _, _, _, _, area in base_objects:
                    total_diff_area += area
            
            return total_diff_area
        except Exception as e:
            print(f"图像对比异常: {str(e)}")
            return None
    
    @staticmethod
    def find_new_objects(image1_path, image2_path):
        try:
            img1 = cv2.imdecode(np.fromfile(image1_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            img2 = cv2.imdecode(np.fromfile(image2_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            if img1 is None or img2 is None:
                print(f"图像读取失败 - img1: {img1 is not None}, img2: {img2 is not None}")
                return None, []
            
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
            img_height, img_width = img2.shape[:2]
            image_area = img_height * img_width
            
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
            
            sensitivity = ALARM_CONFIG.get('sensitivity', 35)
            
            diff_gray = cv2.absdiff(gray2, gray1)
            
            # 调试：检查灰度差异图像的统计信息
            gray_diff_mean = np.mean(diff_gray)
            gray_diff_max = np.max(diff_gray)
            gray_diff_min = np.min(diff_gray)
            print(f"灰度差异统计 - 均值: {gray_diff_mean:.2f}, 最大值: {gray_diff_max}, 最小值: {gray_diff_min}")
            
            # 使用固定阈值直接对灰度差异进行二值化
            threshold_value = ALARM_CONFIG.get('diff_threshold', 20)
            _, thresh = cv2.threshold(diff_gray, threshold_value, 255, cv2.THRESH_BINARY)
            
            # 调试：检查二值化后的白色像素数量
            white_pixels = cv2.countNonZero(thresh)
            print(f"二值化后白色像素数: {white_pixels}, 阈值: {threshold_value}")
            
            # 添加腐蚀操作分离连接的物体，避免形成超大轮廓
            erosion_kernel = np.ones((3, 3), np.uint8)
            thresh = cv2.erode(thresh, erosion_kernel, iterations=1)
            
            # 调试：检查二值化后的白色像素数量
            white_pixels = cv2.countNonZero(thresh)
            print(f"二值化后白色像素数: {white_pixels}, 使用自适应阈值")
            
            kernel_size = int(5 + (sensitivity / 100) * 3)
            if kernel_size % 2 == 0:
                kernel_size += 1
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 调试：检查轮廓数量
            print(f"检测到轮廓数量: {len(contours)}")
            
            total_diff_area = 0
            bounding_boxes = []
            contours_list = []  # 存储轮廓数据
            min_area = ALARM_CONFIG['min_contour_area']
            
            human_filter_enabled = ALARM_CONFIG.get('human_filter_enabled', True)
            small_object_filter = ALARM_CONFIG.get('small_object_filter', True)
            detection_zone = ALARM_CONFIG.get('detection_zone', 'ground_only')
            
            # 加载检测区域
            detection_zones = []
            try:
                import os
                import json
                # 从基准图像所在目录加载检测区域
                base_dir = os.path.dirname(image1_path)
                detection_zones_path = os.path.join(base_dir, 'safe_zones.json')
                if os.path.exists(detection_zones_path):
                    with open(detection_zones_path, 'r', encoding='utf-8') as f:
                        detection_zones = json.load(f)
                    print(f"加载检测区域：{len(detection_zones)} 个")
            except Exception as e:
                print(f"加载检测区域失败：{str(e)}")
                detection_zones = []
            
            print(f"检测到轮廓数量：{len(contours)}, 最小面积阈值：{min_area}")
            print(f"灵敏度：{sensitivity}, 阈值：{threshold_value}, 核大小：{kernel_size}")
            print(f"人体过滤：{human_filter_enabled}, 小物体过滤：{small_object_filter}, 检测区域：{detection_zone}")
            
            # 检测基准图像中的轮廓（用于过滤固定物体）
            base_contours = []
            try:
                gray1_blur = cv2.GaussianBlur(gray1, (7, 7), 0)
                _, thresh1 = cv2.threshold(gray1_blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                base_contours, _ = cv2.findContours(thresh1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                print(f"基准图像检测到 {len(base_contours)} 个轮廓")
            except Exception as e:
                print(f"检测基准图像轮廓失败：{str(e)}")
                base_contours = []
            
            # 过滤掉过大的轮廓（通常是图像边界或背景）
            filtered_base_contours = []
            max_base_area = image_area * 0.8  # 最大允许的基准物体面积（80%图像面积）
            for contour in base_contours:
                area = cv2.contourArea(contour)
                if area < max_base_area and area > 100:  # 排除过大和过小的轮廓
                    filtered_base_contours.append(contour)
            print(f"过滤后有效基准轮廓数量：{len(filtered_base_contours)}")
            
            def is_fixed_object(x, y, w, h):
                """检查物体是否是基准图像中已存在的固定物体"""
                if not filtered_base_contours:
                    return False
                
                object_center_x = x + w // 2
                object_center_y = y + h // 2
                object_area = w * h
                object_width = w
                object_height = h
                
                for base_contour in filtered_base_contours:
                    bx, by, bw, bh = cv2.boundingRect(base_contour)
                    bcx = bx + bw // 2
                    bcy = by + bh // 2
                    base_area = bw * bh
                    base_width = bw
                    base_height = bh
                    
                    # 检查两个矩形是否有较大重叠
                    overlap_x = max(0, min(x + w, bx + bw) - max(x, bx))
                    overlap_y = max(0, min(y + h, by + bh) - max(y, by))
                    overlap_area = overlap_x * overlap_y
                    
                    # 严格条件：重叠面积需要同时满足两个条件
                    # 1. 重叠面积占当前物体面积的85%以上
                    # 2. 重叠面积占基准物体面积的85%以上
                    overlap_ratio_obj = overlap_area / object_area if object_area > 0 else 0
                    overlap_ratio_base = overlap_area / base_area if base_area > 0 else 0
                    
                    if overlap_ratio_obj > 0.85 and overlap_ratio_base > 0.85:
                        # 同时检查宽高比是否接近
                        obj_aspect = object_width / object_height if object_height > 0 else float('inf')
                        base_aspect = base_width / base_height if base_height > 0 else float('inf')
                        if abs(obj_aspect - base_aspect) < 0.3:  # 宽高比差异小于30%
                            return True
                
                return False
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > min_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else float('inf')
                    
                    # 过滤固定物体（基准图像中已存在的物体）
                    filter_fixed = ALARM_CONFIG.get('filter_fixed_objects', True)
                    if filter_fixed and is_fixed_object(x, y, w, h):
                        continue
                    
                    # 检查是否在检测区域内（只检测检测区域内的物体）
                    if not ImageComparer._is_in_detection_zone(x, y, w, h, detection_zones):
                        print(f"物体 ({x}, {y}, {w}, {h}) 不在检测区域内，跳过")
                        continue
                    
                    # 人体过滤
                    if human_filter_enabled:
                        if ImageComparer._is_human_like(w, h, area, contour):
                            continue
                    
                    # 检查宽高比
                    if aspect_ratio >= 20:
                        continue
                    
                    # 检查最大面积限制
                    max_single_area = ALARM_CONFIG.get('max_single_object_area', 200000)
                    if area > max_single_area:
                        continue
                    
                    # 过滤门区域（高而窄的物体可能是门）
                    filter_door = ALARM_CONFIG.get('filter_door_region', True)
                    if filter_door and h > img_height * 0.5 and w < img_width * 0.3:
                        continue
                    
                    # 检查灰度和标准差
                    roi2 = gray2[y:y+h, x:x+w]
                    mean2 = np.mean(roi2)
                    std2 = np.std(roi2)
                    
                    # 从配置读取过滤阈值
                    max_brightness = ALARM_CONFIG.get('max_brightness', 230)
                    min_saturation = ALARM_CONFIG.get('min_saturation', 20)
                    min_std = ALARM_CONFIG.get('min_std', 4)
                    min_edge_ratio = ALARM_CONFIG.get('min_edge_ratio', 0.015)
                    top_exclude_ratio = ALARM_CONFIG.get('detection_zone_top', 0.18)
                    bottom_exclude_ratio = ALARM_CONFIG.get('detection_zone_bottom', 0.08)
                    
                    # 计算位置比例
                    top_ratio = y / img_height
                    bottom_ratio = (y + h) / img_height
                    left_ratio = x / img_width
                    right_ratio = (x + w) / img_width
                    
                    # 提前计算HSV颜色特征（用于垃圾桶过滤）
                    hsv = cv2.cvtColor(img2[y:y+h, x:x+w], cv2.COLOR_BGR2HSV)
                    hue = np.mean(hsv[:, :, 0])
                    saturation = np.mean(hsv[:, :, 1])
                    value = np.mean(hsv[:, :, 2])
                    
                    # 过滤垃圾桶及其内部物体（精确定位，不过滤周围物体）
                    # 垃圾桶特征：绿色 + 特定尺寸范围 + 中右区域
                    # 只过滤垃圾桶本身和内部小物体，保留周围物体
                    
                    # 1. 过滤垃圾桶本身（绿色 + 中右区域 + 中等大小）
                    # 放宽右侧位置要求，支持通道中间的垃圾桶
                    is_trash_bin_itself = (
                        right_ratio > 0.50 and   # 放宽到中右区域（原 0.65）
                        right_ratio < 0.95 and   # 限制右边界，避免过滤更右侧的物体
                        top_ratio > 0.35 and     # 垃圾桶在中下部（原 0.40）
                        top_ratio < 0.85 and     # 不会太靠下（原 0.80）
                        35 <= hue <= 85 and      # 绿色特征
                        saturation > 15 and      # 有一定饱和度（原 20）
                        area > 12000 and         # 垃圾桶本身较大（原 15000）
                        area < 100000 and        # 但不会太大（原 80000）
                        0.25 <= aspect_ratio <= 2.0  # 接近正方形或稍高/宽（原 0.3-1.5）
                    )
                    
                    if is_trash_bin_itself:
                        print(f"过滤垃圾桶本身: x={x}, y={y}, w={w}, h={h}, area={area}, hue={hue:.1f}, right_ratio={right_ratio:.2f}")
                        continue
                    
                    # 2. 过滤垃圾桶内部的小物体（在垃圾桶区域内 + 很小）
                    is_inside_trash_bin = (
                        right_ratio > 0.55 and   # 中右区域（原 0.70）
                        top_ratio > 0.40 and     # 在垃圾桶开口下方（原 0.45）
                        top_ratio < 0.80 and     # 不会太低（原 0.75）
                        area < 20000 and         # 内部物体较小（原 15000）
                        h < img_height * 0.20    # 高度较小（原 0.15）
                    )
                    
                    if is_inside_trash_bin:
                        print(f"过滤垃圾桶内物体: x={x}, y={y}, w={w}, h={h}, area={area}")
                        continue
                    
                    # 1. 颜色特征过滤（针对绿色指示灯）
                    # 绿色范围：Hue 40-80（安全出口指示灯）
                    if 40 <= hue <= 80 and saturation > 30 and value > 50:
                        continue
                    
                    # 绿色垃圾桶过滤（绿色 + 较大面积 + 右侧区域）
                    if 35 <= hue <= 85 and saturation > 25 and area > 10000 and right_ratio > 0.6:
                        print(f"过滤绿色垃圾桶：hue={hue:.1f}, area={area}, right_ratio={right_ratio:.2f}")
                        continue
                    
                    # 2. 亮度+饱和度组合过滤（核心灯光过滤）
                    # 极高亮度区域（强光源）
                    if mean2 >= max_brightness:
                        continue
                    
                    # 低饱和度高亮度（典型灯光特征）- 放宽条件，避免误杀箱子
                    if saturation < min_saturation and mean2 >= 180:
                        continue
                    
                    # 3. 空间位置过滤
                    # 顶部区域（天花板灯光）
                    if top_ratio < top_exclude_ratio and mean2 >= 165:
                        continue
                    
                    # 底部区域（文字水印）
                    if bottom_ratio > (1 - bottom_exclude_ratio) and h < 60:
                        continue
                    
                    # 左上角灯光区域（常见误报区域）
                    if top_ratio < 0.30 and left_ratio < 0.30 and mean2 >= 160:
                        continue
                    
                    # 4. 纹理特征过滤
                    # 纹理均匀区域（光影纹理单一）- 放宽条件，避免误杀箱子
                    if std2 <= min_std and mean2 >= 200:
                        continue
                    
                    # 边缘稀疏区域（光影边缘少）- 放宽条件
                    edges = cv2.Canny(roi2, 50, 150)
                    edge_ratio = cv2.countNonZero(edges) / (w * h) if (w * h) > 0 else 0
                    if edge_ratio < min_edge_ratio and mean2 >= 190:
                        continue
                    
                    # 5. 尺寸与形状过滤
                    # 小区域高亮度（灯光反光点）
                    if area < 6000 and mean2 >= 190:
                        continue
                    
                    # 大面积高亮度背景区域
                    if area > 50000 and mean2 >= 170 and std2 <= 10:
                        continue
                    
                    # 长条形高亮度区域（走廊光影）
                    if aspect_ratio >= 5 and mean2 >= 150 and area > 20000:
                        continue
                    
                    # 通过所有过滤条件
                    total_diff_area += area
                    bounding_boxes.append((x, y, w, h))
                    contours_list.append(contour)  # 保存轮廓数据
            
            detect_base = ALARM_CONFIG.get('detect_base_object', False)
            print(f"是否检测基准图像物体: {detect_base}")
            
            if detect_base:
                base_objects = ImageComparer.detect_base_objects(image1_path)
                print(f"从基准图像检测到 {len(base_objects)} 个物体")
                for x, y, w, h, area in base_objects:
                    total_diff_area += area
                    bounding_boxes.append((x, y, w, h))
                    print(f"添加基准图像物体: ({x}, {y}, {w}, {h}), 面积={area}")
            
            print(f"总共找到 {len(bounding_boxes)} 个边界框，总差异面积={total_diff_area}")
            return total_diff_area, bounding_boxes, contours_list
        except Exception as e:
            print(f"查找新物体异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, [], []
    
    @staticmethod
    def _is_human_like(width, height, area, contour=None):
        # 人体检测逻辑 - 检测人体及人体局部（如腿、手臂等）
        
        # 极小的物体不是人
        if width < 20 or height < 30:
            return False
        
        # 太大的物体也不是人（通道场景下）
        if width > 500 or height > 700:
            return False
        
        aspect_ratio = width / height if height > 0 else float('inf')
        inverse_ratio = height / width if width > 0 else float('inf')
        
        # 人体面积范围（通道场景下合理的人体大小）
        if area < 1500 or area > 120000:
            return False
        
        # 站立的人：高度明显大于宽度
        if height > width * 1.5 and area > 5000:
            return True
        
        # 坐着的人：宽高比较接近
        if 0.4 <= aspect_ratio <= 0.8:
            # 检查是否有类似人体的形状特征
            if contour is not None:
                # 计算轮廓的各种特征
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    # 紧凑度：面积/周长的平方
                    compactness = (4 * np.pi * area) / (perimeter * perimeter)
                    # 人体轮廓通常不太紧凑（有凹凸）
                    if 0.2 < compactness < 0.7:
                        return True
            return True
        
        # 腿部/脚部检测：较小的区域，宽高比较大（站立的腿）
        if 0.3 <= aspect_ratio <= 0.6 and height > 100 and area > 3000:
            return True
        
        # 脚部检测：非常小的区域，接近正方形或稍窄
        if 0.5 <= aspect_ratio <= 1.2 and area >= 1500 and area <= 10000:
            # 脚部通常是较小的、接近地面的区域
            return True
        
        # 人的腿：细长形状，高度远大于宽度
        if inverse_ratio > 2.5 and width < 100 and height > 150:
            return True
        
        # 人的脚：较小，宽高比接近1
        if 0.7 <= aspect_ratio <= 1.3 and area < 8000 and height < 150:
            return True
        
        # 人的手臂：细长形状
        if inverse_ratio > 3.0 and width < 60 and height > 100:
            return True
        
        return False
    
    @staticmethod
    def _is_point_in_polygon(px, py, polygon):
        """检查点是否在多边形内部（射线法）"""
        n = len(polygon)
        inside = False
        
        for i in range(n):
            j = (i + 1) % n
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            
            if ((yi > py) != (yj > py)):
                x_intersect = (py - yi) * (xj - xi) / (yj - yi) + xi
                if px < x_intersect:
                    inside = not inside
        
        return inside
    
    @staticmethod
    def _is_in_detection_zone(x, y, w, h, detection_zones):
        """检查物体是否在检测区域内（支持矩形和多边形）"""
        if not detection_zones:
            return True  # 如果没有配置检测区域，则检测整个画面
        
        for zone in detection_zones:
            # 支持字典格式（新格式）
            if isinstance(zone, dict):
                if zone.get('type') == 'polygon':
                    # 多边形检测区域
                    polygon = zone['data']
                    if len(polygon) >= 3:
                        center_x = x + w // 2
                        center_y = y + h // 2
                        if ImageComparer._is_point_in_polygon(center_x, center_y, polygon):
                            return True
                        corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
                        for cx, cy in corners:
                            if ImageComparer._is_point_in_polygon(cx, cy, polygon):
                                return True
                    continue
                else:
                    zx, zy, zw, zh = zone['data']
            elif isinstance(zone, list) and len(zone) == 4:
                zx, zy, zw, zh = zone[0], zone[1], zone[2], zone[3]
            elif isinstance(zone, list) and len(zone) >= 3:
                # 多边形检测区域（简化格式）
                polygon = zone
                if len(polygon) >= 3:
                    center_x = x + w // 2
                    center_y = y + h // 2
                    if ImageComparer._is_point_in_polygon(center_x, center_y, polygon):
                        return True
                    corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
                    for cx, cy in corners:
                        if ImageComparer._is_point_in_polygon(cx, cy, polygon):
                            return True
                continue
            else:
                zx, zy, zw, zh = zone
            
            # 检查物体是否与检测区域重叠
            overlap_x = max(0, min(x + w, zx + zw) - max(x, zx))
            overlap_y = max(0, min(y + h, zy + zh) - max(y, zy))
            overlap_area = overlap_x * overlap_y
            
            if overlap_area > 0 and overlap_area > (w * h * 0.5):
                print(f"物体 ({x}, {y}, {w}, {h}) 在检测区域 ({zx}, {zy}, {zw}, {zh}) 内")
                return True
        
        return False
    
    @staticmethod
    def _is_valid_size(x, y, w, h, img_height, img_width):
        min_ratio = ALARM_CONFIG.get('min_area_ratio', 0.10)
        max_ratio = ALARM_CONFIG.get('max_area_ratio', 0.15)
        
        object_area = w * h
        image_area = img_height * img_width
        
        if image_area == 0:
            return False
        
        area_ratio = object_area / image_area
        
        return min_ratio <= area_ratio <= max_ratio