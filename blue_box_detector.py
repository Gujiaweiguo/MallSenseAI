"""
蓝色箱子检测模块 - 使用YOLO
"""
import cv2
import numpy as np
import os
import json
from ultralytics import YOLO

class BlueBoxDetector:
    """使用YOLO检测箱子"""

    def __init__(self, model_name='yolov8n.pt', conf_threshold=0.1, min_area=5000):
        self.model = YOLO(model_name)
        self.conf_threshold = conf_threshold
        self.min_area = min_area

        # 箱子相关类别
        self.box_classes = [
            'box', 'package', 'crate', 'suitcase', 'backpack', 'handbag',
            'briefcase', 'bag', 'storage box', 'cardboard',
            'dining table', 'tv', 'laptop',
            'cell phone', 'book', 'bottle', 'cup', 'bowl', 'potted plant',
            'bench', 'basket',
            # 添加广告牌相关类别
            'sign', 'board', 'advertisement', 'billboard', 'signboard', 'display',
            # 添加筐子相关类别
            'cage', 'container', 'basket', 'bucket', 'trolley',
            # 添加更多箱子类型（覆盖图片中的各种箱子）
            'carton', 'case', 'trunk', 'chest',
            'bin', 'storage', 'pallet', 'container', 'tub',
            'styrofoam', 'icebox', 'cooler', 'insulated box',
            'plastic box', 'plastic crate', 'turnover box', 'logistics box',
            'shipping box', 'moving box', 'packaging', 'parcel',
            # 更多箱子类型（图片中的各种箱子）
            'paper box', 'cardboard box', 'wooden box', 'metal box',
            'plastic basket', 'wire basket', 'mesh basket', 'crates',
            'tote box', 'moving box', 'packing box', 'delivery box',
            'storage container', 'plastic tub', 'large bin', 'trash bin',
            'waste container', 'rubbish bin', 'garbage can', 'recycling bin',
            # 添加黑色筐子相关类型
            'black basket', 'black crate', 'dark basket', 'dark crate',
            'stackable crate', 'industrial crate', 'shipping crate',
            'warehouse crate', 'storage crate', 'heavy duty crate'
        ]
        
        # 需要排除的类别（动物、垃圾桶等，但不再排除人）
        self.exclude_classes = [
            'animal', 'cat', 'dog', 'bird',
            'trash can', 'trash', 'bin', 'garbage', 'waste bin', 'dustbin',
            'couch', 'chair', 'vase'
        ]

    def _load_detection_zones(self, image_path):
        """加载检测区域配置"""
        detection_zones = []
        try:
            base_dir = os.path.dirname(image_path)
            detection_zones_path = os.path.join(base_dir, 'safe_zones.json')
            if os.path.exists(detection_zones_path):
                with open(detection_zones_path, 'r', encoding='utf-8') as f:
                    detection_zones = json.load(f)
                print(f"加载检测区域：{len(detection_zones)} 个")
        except Exception as e:
            print(f"加载检测区域失败：{str(e)}")
        return detection_zones

    def _is_point_in_polygon(self, px, py, polygon):
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
    
    def _is_in_detection_zone(self, x, y, w, h, detection_zones):
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
                        # 检查物体中心点是否在多边形内
                        center_x = x + w // 2
                        center_y = y + h // 2
                        if self._is_point_in_polygon(center_x, center_y, polygon):
                            return True
                        # 检查四个角点是否有任一点在多边形内
                        corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
                        for cx, cy in corners:
                            if self._is_point_in_polygon(cx, cy, polygon):
                                return True
                    continue
                else:
                    # 矩形检测区域（新格式）
                    zx, zy, zw, zh = zone['data']
            elif isinstance(zone, list) and len(zone) == 4:
                # 矩形检测区域（旧格式）
                zx, zy, zw, zh = zone[0], zone[1], zone[2], zone[3]
            elif isinstance(zone, list) and len(zone) >= 3:
                # 多边形检测区域（简化格式）
                polygon = zone
                if len(polygon) >= 3:
                    center_x = x + w // 2
                    center_y = y + h // 2
                    if self._is_point_in_polygon(center_x, center_y, polygon):
                        return True
                    corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
                    for cx, cy in corners:
                        if self._is_point_in_polygon(cx, cy, polygon):
                            return True
                continue
            else:
                zx, zy, zw, zh = zone
            # 检查物体是否与检测区域重叠（不仅仅是中心点）
            overlap_x = max(0, min(x + w, zx + zw) - max(x, zx))
            overlap_y = max(0, min(y + h, zy + zh) - max(y, zy))
            overlap_area = overlap_x * overlap_y
            
            # 如果重叠面积超过物体面积的50%，认为在检测区域内
            if overlap_area > 0 and overlap_area > (w * h * 0.5):
                print(f"物体 ({x}, {y}, {w}, {h}) 在检测区域 ({zx}, {zy}, {zw}, {zh}) 内")
                return True
        return False

    def detect_blue_boxes(self, image_path):
        """
        使用YOLO检测箱子（排除人体、顶棚、垃圾桶、安全区域等干扰）
        :param image_path: 图像路径
        :return: (总差异面积, 边界框列表, 轮廓列表)
        """
        try:
            # 读取图像
            img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                print("图像读取失败")
                return 0, [], []

            h, w = img.shape[:2]
            image_area = h * w

            # 加载检测区域
            detection_zones = self._load_detection_zones(image_path)

            # 使用YOLO检测
            results = self.model(img, conf=self.conf_threshold)

            bounding_boxes = []
            contours_list = []
            total_diff_area = 0

            for result in results:
                for box in result.boxes:
                    # 获取类别名称
                    cls_name = result.names[int(box.cls[0])]
                    
                    # 排除人体、动物、垃圾桶等类别
                    if cls_name.lower() in self.exclude_classes:
                        print(f"排除类别: {cls_name}")
                        continue

                    # 获取边界框
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    x, y = int(x1), int(y1)
                    box_w, box_h = int(x2 - x1), int(y2 - y1)

                    # 计算面积
                    area = box_w * box_h

                    # 过滤过小的检测结果
                    if area < self.min_area:
                        continue

                    # 过滤过大的区域（超过图像的25%可能是误检）
                    if area > image_area * 0.25:
                        print(f"过滤大面积区域: {area} (超过图像25%)")
                        continue

                    # 过滤顶部区域（顶棚/灯光，占图像顶部15%）
                    if y < h * 0.15:
                        continue

                    # 过滤底部区域（地面，占图像底部10%）
                    if (y + box_h) > h * 0.95:
                        print(f"过滤底部区域: y={y}, h={h}")
                        continue

                    # 过滤右侧边缘区域（绿色垃圾桶区域，右侧 15%）
                    if x > w * 0.85:
                        print(f"过滤右侧边缘区域 (垃圾桶区域): x={x}, w={w}")
                        continue
                    
                    # 过滤右侧区域（垃圾桶常见区域，右侧 25% 且高度较大）
                    if x > w * 0.75 and box_h > h * 0.3:
                        print(f"过滤右侧大物体 (疑似垃圾桶): x={x}, h={box_h}")
                        continue

                    # 过滤左侧边缘区域（固定物体）
                    if x < w * 0.05 and y > h * 0.5:
                        continue

                    # 判断是否是人
                    is_person = cls_name.lower() == 'person'
                    
                    # 过滤人体形状的物体（宽高比 < 0.7 且高度较大）
                    # 但广告牌可能也是窄高的，需要特殊处理
                    # 躺着的人（睡觉）是宽大于高的，不应被过滤
                    is_sign_like = cls_name.lower() in ['sign', 'board', 'advertisement', 'billboard', 'signboard', 'display']
                    if box_h > box_w * 1.4 and box_h > h * 0.2 and not is_sign_like and not is_person:
                        continue

                    # 过滤非常窄高的物体（可能是人体局部）
                    # 广告牌可能是窄高的，放宽限制；人也不应被过滤
                    if box_w < box_h * 0.3 and not is_sign_like and not is_person:
                        continue

                    # 过滤非常宽矮的物体（可能是地面光影）
                    # 但躺着的人（睡觉）是宽大于高的，需要特殊处理
                    if box_h < box_w * 0.3 and not is_person:
                        print(f"过滤宽矮区域: w={box_w}, h={box_h}, 宽高比={box_w/box_h:.2f}")
                        continue

                    # 检查是否在检测区域内（只检测检测区域内的物体）
                    if not self._is_in_detection_zone(x, y, box_w, box_h, detection_zones):
                        print(f"物体 ({x}, {y}, {box_w}, {box_h}) 不在检测区域内，跳过")
                        continue

                    # 检查是否是箱子相关类别、广告牌类别或人（包括睡觉的人）
                    if cls_name.lower() in self.box_classes or cls_name.lower() == 'box' or cls_name.lower() == 'person':
                        bounding_boxes.append((x, y, box_w, box_h))
                        total_diff_area += area
                        print(f"检测到物体: {cls_name}, 位置: ({x}, {y}), 大小: {box_w}x{box_h}, 面积: {area}")

            print(f"YOLO检测找到 {len(bounding_boxes)} 个箱子区域")
            return total_diff_area, bounding_boxes, contours_list

        except Exception as e:
            print(f"YOLO检测异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0, [], []

if __name__ == '__main__':
    detector = BlueBoxDetector(model_name='yolov8s.pt', conf_threshold=0.1, min_area=5000)
    diff_area, boxes, contours = detector.detect_blue_boxes('alarm_images/L4021A铺后通道/alarm_20260529_092503.jpg')
    print(f"\n检测结果: 差异面积={diff_area}, 检测到{len(boxes)}个区域")
    for i, (x, y, w, h) in enumerate(boxes):
        print(f"  区域{i+1}: 位置({x}, {y}), 大小({w}x{h})")
