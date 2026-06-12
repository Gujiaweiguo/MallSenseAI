import cv2
import numpy as np
import os
import json
from ultralytics import YOLO

class YoloDetector:
    # 箱子相关类别 - 扩展更多可能的类别（去重后）
    BOX_CLASSES = ['box', 'package', 'crate', 'suitcase', 'handbag', 
                   'briefcase', 'storage box', 'cardboard', 'carton', 
                   'case', 'trunk', 'chest', 'basket', 
                   'trolley', 'handcart', 'cart', 'wheelbarrow', 'pallet', 'styrofoam', 'cage', 'barrel', 'bucket',
                   'stool', 'chair', 'bench', 'table', 'dining table', 'desk',
                   'sofa', 'couch',
                   'plastic bag', 'garbage bag', 'trash bag', 
                   'blue basket', 'blue crate', 'blue bin', 'blue container',
                   'black bag', 'black plastic', 'wrap', 'cover',
                   'red stool', 'red chair', 'plastic stool', 'plastic chair',
                   'red plastic stool', 'red plastic chair', 'red seat',
                   'red basket', 'red crate', 'red box', 'red container',
                   'black trolley', 'black cart', 'metal cart', 'metal trolley',
                   'bag', 'cloth', 'fabric', 'cloth bag', 'towel', 'rag',
                   'seat', 'furniture',
                   'ladder', 'step ladder', 'stair', 'stairs', 'scaffold',
                   'poster', 'banner', 'advertisement', 'menu',
                   'stand', 'display', 'rack', 'holder', 'hanger', 'standee',
                   'basin', 'pot', 'pan', 'kettle', 'jar',
                   'trash', 'object', 'item',
                   'scrap', 'trash pile', 'waste pile',
                   'waste', 'garbage', 'junk',
                   'cargo', 'goods', 'merchandise', 'material', 'supply', 'stock']
    
    # 需要排除的类别（只排除植物、电器和门，不排除人）
    EXCLUDE_CLASSES = ['plant', 'potted plant', 'vase', 'umbrella',
                       # 通用类别（YOLO可能返回的未明确类别）
                       'object', 'item', 'thing', 'stuff', 'unknown',
                       # 基本COCO类别 - 建筑和设施
                       'building', 'architecture', 'structure',
                       'stairs', 'staircase', 'steps', 'escalator', 'moving walkway',
                       'bench', 'counter', 'shelf', 'rack', 'shelving',
                       'carpet', 'rug', 'mat', 'floor mat', 'doormat',
                       'curtain', 'blind', 'shade', 'window blind',
                       'picture', 'painting', 'frame', 'photo frame',
                       'clock', 'mirror', 'mirror frame',
                       # 家具类（可能被误检测为异常）
                       'cabinet', 'drawer', 'wardrobe', 'bookshelf',
                       'tv', 'laptop', 'cell phone', 'book', 'bottle', 'cup',
                       'door', 'door handle', 'gate', 'window', 'fire door', 'safety door', 'exit door',
                       'elevator', 'lift', 'elevator door', 'lift door', 'elevator panel', 'lift panel',
                       'elevator cabin', 'lift cabin', 'elevator frame', 'lift frame',
                       'mirror', 'glass', 'wall', 'floor', 'ceiling', 'wall panel', 'floor tile',
                       'door frame', 'drawer', 'frame', 'cabinet', 'cabinet door',
                       'switch', 'socket', 'panel', 'control box', 'electric box', 'electrical box', 
                       'power box', 'meter box', 'junction box',
                       'appliance', 'fixture', 'equipment', 'machine', 'device',
                       'text', 'letter', 'number', 'label', 'logo', 'symbol', 'timestamp', 'date', 'time',
                       'vent', 'ventilation', 'grille', 'air vent', 'exhaust', 'air conditioner', 'ac',
                       'light', 'lamp', 'bulb', 'indicator', 'exit sign', 'emergency light',
                       'pipe', 'pipeline', 'tube', 'valve', 'faucet', 'tap', 'pipe fitting',
                       'metal', 'steel', 'iron', 'concrete', 'stone', 'marble',
                       'fire cabinet', 'fire extinguisher', 'fire equipment', 'fire box', 'fire station',
                       'trash can', 'trash bin', 'garbage can', 'waste bin', 'dustbin',
                       'signage', 'notice board', 'bulletin board', 'poster board', 'information board',
                       'distribution box', 'distribution panel', 'breaker box', 'fuse box',
                       'emergency exit', 'escape door', 'evacuation door',
                       'handrail', 'railing', 'guardrail', 'banister',
                       # 电梯厅场景专用长尾词
                       'elevator lobby', 'lift lobby', 'elevator area', 'lift area',
                       'elevator hall', 'lift hall', 'elevator waiting area', 'lift waiting area',
                       'elevator door frame', 'lift door frame', 'metal door frame', 'steel door frame',
                       'elevator button', 'lift button', 'elevator control', 'lift control',
                       'elevator panel', 'lift panel', 'call button', 'floor button',
                       'fire door frame', 'emergency exit frame', 'double door frame', 'twin door frame',
                       'wall vent', 'wall grille', 'return air grille', 'supply air grille',
                       'wall opening', 'wall panel opening', 'vent opening', 'grille opening',
                       'metal panel', 'steel panel', 'metal surface', 'steel surface',
                       'corner wall', 'wall corner', 'wall edge', 'edge wall',
                       'tile', 'floor tile', 'ceramic tile', 'marble tile',
                       'pillar', 'column', 'post', 'support', 'beam', 'structural',
                       'ceiling light', 'downlight', 'spotlight', 'recessed light',
                       'floor drain', 'drain', 'drainage', 'sewer',
                       'corner', 'edge', 'trim', 'molding', 'baseboard',
                       'duct', 'air duct', 'ventilation duct', 'exhaust duct',
                       'hose', 'fire hose', 'water hose', 'pipe',
                       'conduit', 'cable tray', 'wireway', 'raceway',
                       'window frame', 'window sill', 'window ledge',
                       'elevator hall', 'lift hall', 'elevator lobby', 'lift lobby',
                       'floor number', 'floor sign', 'level sign', 'floor indicator',
                       'emergency light', 'safety light', 'guide light',
                       'wall sign', 'wall label', 'room number', 'room sign',
                       'helmet', 'hard hat', 'safety helmet', 'construction helmet',
                       'worker', 'staff', 'employee', 'person', 'human',
                       'backpack', 'tool bag', 'toolbox', 'tool kit',
                       'uniform', 'work clothes', 'safety vest', 'reflective vest', 'orange vest',
                       'door closer', 'door hinge', 'door lock', 'door knob', 'handle',
                       'window glass', 'window pane', 'glass panel', 'glass window',
                       'exit light', 'exit indicator', 'safety exit', 'fire exit',
                       'threshold', 'doorstep', 'door sill', 'door jamb',
                       # 墙壁和瓷砖相关长尾词
                       'wall tile', 'tile wall', 'wall tiles', 'tiles wall',
                       'corner tile', 'tile corner', 'wall corner', 'corner wall',
                       'wall edge', 'edge wall', 'floor edge', 'edge floor',
                       'wall section', 'wall paneling', 'wall cladding', 'wall covering',
                       # 玻璃相关长尾词
                       'glass door', 'glass wall', 'glass panel', 'glass partition',
                       'glass window', 'glass surface', 'glass area', 'transparent glass',
                       # 栏杆相关长尾词
                       'metal railing', 'glass railing', 'stainless steel railing',
                       'handrail bracket', 'railing post', 'railing support',
                       # 地面相关长尾词
                       'floor tile', 'tile floor', 'floor tiles', 'tiles floor',
                       'marble floor', 'ceramic floor', 'polished floor',
                       # 天花板相关长尾词
                       'ceiling tile', 'tile ceiling', 'ceiling panel', 'suspended ceiling',
                       # 边缘和角落相关
                       'wall trim', 'wall molding', 'floor trim', 'base molding',
                       'corner trim', 'edge trim', 'trim piece', 'molding piece',
                       # 时间戳和水印相关
                       'timestamp', 'datetime', 'date time', 'time stamp', 'watermark',
                       'video timestamp', 'camera timestamp', 'recording time',
                       # 消防设施相关
                       'fire cabinet', 'fire equipment cabinet', 'fire hose cabinet',
                       'fire extinguisher cabinet', 'fire station cabinet',
                       'fire control cabinet', 'emergency cabinet',
                       # 门上窗户相关
                       'door window', 'door glass', 'small window', 'door panel window',
                       'glass insert', 'window insert', 'door light', 'transom',
                       # 管道相关
                       'pipe', 'pipe rack', 'pipe support', 'conduit pipe', 'electrical pipe',
                       'water pipe', 'drain pipe', 'gas pipe', 'pipe clamp',
                       # 紧急出口指示灯相关
                       'exit light', 'emergency light', 'green exit light', 'floor exit light',
                       'ground light', 'floor indicator', 'exit indicator', 'safety indicator',
                       'emergency exit light', 'escape light', 'evacuation light',
                       # 楼层标识相关
                       'floor number', 'floor sign', 'level sign', 'building level',
                       'floor indicator', 'level indicator', 'l4', 'l5', 'floor label',
                       # 电梯厅相关
                       'elevator door', 'lift door', 'elevator entrance', 'lift entrance',
                       'elevator lobby', 'lift lobby', 'elevator area', 'lift area',
                       # 门禁和开关相关
                       'access control', 'card reader', 'door reader', 'rfid reader',
                       'security reader', 'door sensor', 'door switch', 'light switch',
                       'power switch', 'control panel', 'wall switch', 'button panel',
                       # 门框和门边缘相关
                       'door frame', 'door edge', 'door corner', 'door opening',
                       'door jamb', 'door trim', 'door casing', 'door surround',
                       'door edge trim', 'frame edge', 'frame corner',
                       # 展示架相关
                       'display stand', 'sign stand', 'menu stand', 'poster stand',
                       'advertising stand', 'promotional stand', 'information stand',
                       # 玻璃门和门框相关
                       'glass door', 'glass panel door', 'framed glass door', 'sliding glass door',
                       'glass entrance', 'glass partition', 'glass wall section', 'glass area',
                       # 墙壁边缘和角落相关
                       'wall edge', 'wall corner', 'wall section', 'wall area',
                       'corner wall', 'edge wall', 'wall surface', 'wall texture',
                       'concrete wall', 'painted wall', 'plaster wall', 'drywall',
                       # 位置标识和水印相关
                       'location sign', 'position marker', 'area label', 'zone label',
                       'camera label', 'camera id', 'channel label', 'site label',
                       'watermark text', 'overlay text', 'screen text', 'video overlay',
                       # 电梯门和电梯区域相关
                       'elevator door panel', 'lift door panel', 'metal elevator door',
                       'elevator cabin door', 'lift cabin door', 'elevator entrance door',
                       'elevator frame', 'lift frame', 'elevator surround',
                       # 消防门和紧急出口门相关
                       'fire exit door', 'emergency exit door', 'double door', 'safety door',
                       'exit door', 'emergency door', 'fire door assembly',
                       'glass panel door', 'door with glass', 'framed door',
                       # 通风口和排风口相关
                       'air vent', 'ventilation grille', 'return air grille', 'supply air grille',
                       'exhaust vent', 'duct opening', 'wall vent', 'ceiling vent',
                       'vent cover', 'grille cover', 'metal grille', 'air diffuser',
                       # 配电箱和电气箱相关
                       'electrical box', 'power box', 'distribution box', 'circuit breaker box',
                       'control panel', 'switch box', 'junction box', 'meter box',
                       'electric panel', 'utility box', 'service box', 'equipment box',
                       # 管道和水管相关
                       'water pipe', 'gas pipe', 'yellow pipe', 'metal pipe',
                       'pipe fitting', 'pipe valve', 'pipe connector', 'pipe clamp',
                       'pipe bracket', 'pipe support', 'exposed pipe', 'wall pipe',
                       # 管道阀门和配件相关
                       'valve', 'gate valve', 'ball valve', 'check valve',
                       'pipe valve', 'water valve', 'gas valve', 'control valve',
                       # 广告牌和指示牌相关
                       'signboard', 'billboard', 'advertising board', 'display board',
                       'sign stand', 'advertising stand', 'promotional stand', 'info stand',
                       'directional sign', 'wayfinding sign', 'information sign', 'guide sign',
                       'store sign', 'shop sign', 'business sign', 'company sign',
                       'yellow sign', 'yellow board', 'yellow stand', 'yellow display',
                       # 墙壁角落和踢脚线相关
                       'wall corner', 'corner joint', 'wall junction', 'wall seam',
                       'baseboard', 'wall base', 'floor trim', 'floor edge trim',
                       'wall corner trim', 'corner molding', 'corner bead',
                       # 标识文字相关
                       'location text', 'position text', 'address text', 'area text',
                       'camera text', 'channel text', 'site text', 'zone text',
                       'timestamp text', 'date text', 'time text', 'datetime text',
                       # 双开门相关
                       'double door', 'twin door', 'pair of doors', 'side by side doors',
                       'double entry door', 'double swing door', 'double hinged door',
                       # 标识牌和宣传栏相关
                       'bulletin board', 'notice board', 'information board', 'message board',
                       'display board', 'poster board', 'wall display', 'wall poster',
                       # 消防柜相关
                       'fire cabinet', 'fire equipment cabinet', 'red cabinet', 'emergency cabinet',
                       # 摄像头相关
                       'security camera', 'surveillance camera', 'ip camera', 'camera',
                       'camera mount', 'camera bracket', 'wall camera', 'ceiling camera',
                       # 窗户和玻璃墙相关
                       'window', 'glass window', 'window pane', 'window frame',
                       'glass wall', 'glass partition', 'glass facade', 'glass panel',
                       # 垃圾桶相关
                       'trash bin', 'garbage bin', 'waste bin', 'rubbish bin',
                       'recycle bin', 'green bin', 'waste container', 'trash container',
                       # 标识牌和广告牌相关
                       'advertising sign', 'promotional sign', 'brand sign', 'logo sign',
                       'red sign', 'red board', 'sign panel', 'advertisement panel',
                       # 墙壁角落和边缘相关
                       'corner wall', 'wall corner', 'wall edge', 'edge wall',
                       'corner area', 'wall section', 'edge section',
                       # 门框和门相关
                       'door frame', 'door edge', 'door corner', 'door opening',
                       'double door', 'twin door', 'pair of doors',
                       # 栏杆和扶手相关
                       'railing', 'handrail', 'metal railing', 'glass railing',
                       'stainless steel railing', 'railing post', 'railing support',
                       # 玻璃门和橱窗相关
                       'storefront', 'shop window', 'glass door', 'glass entrance',
                       'display window', 'showcase', 'commercial door',
                       # 电梯相关
                       'elevator', 'lift', 'elevator door', 'lift door', 'elevator panel',
                       'lift panel', 'elevator cabin', 'lift cabin', 'elevator frame',
                       'metal door', 'metal panel', 'steel door', 'steel panel',
                       # 消防门相关
                       'fire door', 'emergency exit', 'double door', 'twin door',
                       'exit door', 'safety door', 'fire exit', 'escape door',
                       # 通风口相关
                       'vent', 'air vent', 'ventilation', 'grille', 'air grille',
                       'return air grille', 'supply air grille', 'duct opening',
                       # 时间戳和水印相关
                       'timestamp', 'datetime', 'date time', 'watermark', 'video timestamp']
    
    def __init__(self, model_name='yolov8s.pt', conf_threshold=0.1, iou_threshold=0.45):
        """
        初始化YOLO检测器
        :param model_name: 模型名称或路径
        :param conf_threshold: 置信度阈值
        :param iou_threshold: IOU阈值
        """
        print(f"正在加载YOLO模型: {model_name}")
        try:
            self.model = YOLO(model_name)
            self.conf_threshold = conf_threshold
            self.iou_threshold = iou_threshold
            # 检查模型信息
            if hasattr(self.model, 'names'):
                print(f"YOLO模型 {model_name} 加载完成，包含 {len(self.model.names)} 个类别")
            else:
                print(f"YOLO模型 {model_name} 加载完成 (置信度阈值: {conf_threshold})")
        except Exception as e:
            print(f"YOLO模型加载失败: {str(e)}")
            raise
    
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
    
    def _is_in_detection_zone(self, x, y, w, h, detection_zones):
        """检查物体是否在检测区域内（支持矩形和多边形）"""
        if not detection_zones:
            return True  # 如果没有配置检测区域，则检测整个画面
        
        for zone in detection_zones:
            if isinstance(zone, dict):
                if zone.get('type') == 'polygon':
                    polygon = zone['data']
                    if len(polygon) >= 3:
                        # 检查中心点是否在多边形内
                        center_x = x + w // 2
                        center_y = y + h // 2
                        if self._is_point_in_polygon(center_x, center_y, polygon):
                            return True
                        # 检查四个角是否在多边形内
                        corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
                        for cx, cy in corners:
                            if self._is_point_in_polygon(cx, cy, polygon):
                                return True
                        # 检查物体边界框是否与多边形边界有交点（只要有重叠就认为在区域内）
                        # 检查多边形的每条边是否与物体边界框相交
                        n = len(polygon)
                        for i in range(n):
                            x1, y1 = polygon[i]
                            x2, y2 = polygon[(i + 1) % n]
                            # 检查多边形边是否与矩形边界框相交
                            if self._line_rect_intersect(x1, y1, x2, y2, x, y, x + w, y + h):
                                return True
                        # 检查矩形是否包含多边形的任何顶点
                        for px, py in polygon:
                            if x <= px <= x + w and y <= py <= y + h:
                                return True
                    continue
                else:
                    zx, zy, zw, zh = zone['data']
            elif isinstance(zone, list) and len(zone) == 4:
                zx, zy, zw, zh = zone[0], zone[1], zone[2], zone[3]
            elif isinstance(zone, list) and len(zone) >= 3:
                polygon = zone
                if len(polygon) >= 3:
                    # 检查中心点是否在多边形内
                    center_x = x + w // 2
                    center_y = y + h // 2
                    if self._is_point_in_polygon(center_x, center_y, polygon):
                        return True
                    # 检查四个角是否在多边形内
                    corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
                    for cx, cy in corners:
                        if self._is_point_in_polygon(cx, cy, polygon):
                            return True
                    # 检查物体边界框是否与多边形边界有交点
                    n = len(polygon)
                    for i in range(n):
                        x1, y1 = polygon[i]
                        x2, y2 = polygon[(i + 1) % n]
                        if self._line_rect_intersect(x1, y1, x2, y2, x, y, x + w, y + h):
                            return True
                    for px, py in polygon:
                        if x <= px <= x + w and y <= py <= y + h:
                            return True
                continue
            else:
                zx, zy, zw, zh = zone
            
            overlap_x = max(0, min(x + w, zx + zw) - max(x, zx))
            overlap_y = max(0, min(y + h, zy + zh) - max(y, zy))
            overlap_area = overlap_x * overlap_y
            
            if overlap_area > 0:  # 只要有重叠就认为在区域内
                print(f"物体 ({x}, {y}, {w}, {h}) 在检测区域 ({zx}, {zy}, {zw}, {zh}) 内")
                return True
        
        return False
    
    def _line_rect_intersect(self, x1, y1, x2, y2, rx, ry, rw, rh):
        """检查线段是否与矩形相交"""
        # 检查线段的两个端点是否在矩形内
        if rx <= x1 <= rw and ry <= y1 <= rh:
            return True
        if rx <= x2 <= rw and ry <= y2 <= rh:
            return True
        
        # 将矩形的四条边作为线段，检查是否与输入线段相交
        rect_lines = [
            (rx, ry, rw, ry),    # 上边
            (rw, ry, rw, rh),    # 右边
            (rx, rh, rw, rh),    # 下边
            (rx, ry, rx, rh)     # 左边
        ]
        
        for rlx1, rly1, rlx2, rly2 in rect_lines:
            if self._line_intersect(x1, y1, x2, y2, rlx1, rly1, rlx2, rly2):
                return True
        
        return False
    
    def _line_intersect(self, x1, y1, x2, y2, x3, y3, x4, y4):
        """检查两条线段是否相交"""
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:
            return False  # 平行或重合
        
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        
        return 0 <= ua <= 1 and 0 <= ub <= 1
    
    def _detect_by_color(self, img):
        """使用颜色检测识别异常物体（备用方案）"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 定义颜色范围（针对广告牌、箱子等常见异常物体）
        color_ranges = [
            # 红色
            ((0, 50, 50), (10, 255, 255)),
            ((170, 50, 50), (180, 255, 255)),
            # 黄色
            ((20, 50, 50), (40, 255, 255)),
            # 蓝色
            ((90, 50, 50), (130, 255, 255)),
            # 黑色（垃圾袋、箱子）
            ((0, 0, 0), (180, 255, 50)),
            # 灰色（箱子）
            ((0, 0, 50), (180, 50, 180)),
            # 橙色
            ((10, 50, 50), (25, 255, 255)),
        ]
        
        boxes = []
        for (lower, upper) in color_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            # 形态学操作去除噪声
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 500:  # 过滤小面积噪声
                    x, y, w, h = cv2.boundingRect(contour)
                    # 检查是否是有效的矩形（排除细长条）
                    if w > 20 and h > 20 and w < img.shape[1] - 20 and h < img.shape[0] - 20:
                        # 检查宽高比，避免检测到墙壁等大面积区域
                        aspect_ratio = max(w, h) / min(w, h)
                        if aspect_ratio < 10:
                            boxes.append((x, y, w, h))
        
        # 去重（合并重叠的框）
        if len(boxes) > 1:
            boxes = self._merge_overlapping_boxes(boxes)
        
        return boxes
    
    def _merge_overlapping_boxes(self, boxes):
        """合并重叠的边界框"""
        if not boxes:
            return []
        
        # 按面积排序
        boxes.sort(key=lambda b: b[2] * b[3], reverse=True)
        merged = []
        
        for box in boxes:
            x1, y1, w1, h1 = box
            overlap = False
            for i, (mx1, my1, mw1, mh1) in enumerate(merged):
                # 检查是否重叠
                if (x1 < mx1 + mw1 and x1 + w1 > mx1 and
                    y1 < my1 + mh1 and y1 + h1 > my1):
                    # 合并
                    new_x = min(x1, mx1)
                    new_y = min(y1, my1)
                    new_w = max(x1 + w1, mx1 + mw1) - new_x
                    new_h = max(y1 + h1, my1 + mh1) - new_y
                    merged[i] = (new_x, new_y, new_w, new_h)
                    overlap = True
                    break
            if not overlap:
                merged.append(box)
        
        return merged
        
    def detect_objects(self, image_path):
        """
        检测图像中的物体（排除人体和植物）
        :param image_path: 图像路径
        :return: (总差异面积, 边界框列表, 轮廓列表)
        """
        try:
            # 加载图像
            img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                print(f"图像加载失败: {image_path}")
                return 0, [], []
            
            img_height, img_width = img.shape[:2]
            image_area = img_height * img_width
            
            # 加载检测区域
            detection_zones = self._load_detection_zones(image_path)
            print(f"检测区域数量: {len(detection_zones) if detection_zones else 0}")
            print(f"图像尺寸: {img_width}x{img_height}")
            if detection_zones:
                for i, zone in enumerate(detection_zones):
                    if isinstance(zone, dict) and 'data' in zone:
                        print(f"  区域{i+1}: {zone.get('type', 'unknown')}, 点数: {len(zone['data'])}")
                        # 打印多边形的边界范围
                        if zone.get('type') == 'polygon':
                            points = zone['data']
                            xs = [p[0] for p in points]
                            ys = [p[1] for p in points]
                            print(f"    边界: x=[{min(xs)}-{max(xs)}], y=[{min(ys)}-{max(ys)}]")
                            print(f"    边界: x=[{min(xs)}-{max(xs)}], y=[{min(ys)}-{max(ys)}]")
            
            # 使用YOLO进行检测
            print(f"开始YOLO检测，阈值: {self.conf_threshold}")
            print(f"图像路径: {image_path}")
            print(f"图像尺寸: {img_width}x{img_height}")
            # 打印模型支持的类别（调试用）
            if hasattr(self.model, 'names') and self.model.names:
                print(f"模型类别数量: {len(self.model.names)}")
                # 打印前20个类别
                first_20_classes = list(self.model.names.values())[:20]
                print(f"部分类别: {first_20_classes}")
            results = self.model.predict(
                source=image_path,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False
            )
            print(f"YOLO检测完成，结果数量: {len(results)}")
            
            bounding_boxes = []
            contours_list = []
            total_diff_area = 0
            
            # 统计YOLO原始检测结果
            total_boxes = 0
            for i, result in enumerate(results):
                print(f"  结果{i}: type={type(result)}, boxes={getattr(result, 'boxes', 'None')}")
                if hasattr(result, 'boxes') and result.boxes is not None:
                    box_count = len(result.boxes)
                    total_boxes += box_count
                    print(f"    检测到 {box_count} 个边界框")
                    # 打印每个边界框的详细信息
                    for j, box in enumerate(result.boxes):
                        class_id = int(box.cls[0]) if box.cls is not None else -1
                        conf = float(box.conf[0]) if box.conf is not None else 0.0
                        print(f"      框{j}: class_id={class_id}, conf={conf:.4f}")
            print(f"YOLO原始检测到 {total_boxes} 个物体")
            
            # 如果YOLO没有检测到任何物体，使用颜色检测作为备用方案
            if total_boxes == 0:
                print("YOLO未检测到物体，使用颜色检测作为备用...")
                color_boxes = self._detect_by_color(img)
                if color_boxes:
                    print(f"颜色检测发现 {len(color_boxes)} 个物体")
                    # 为颜色检测结果添加过滤（与YOLO检测相同的过滤逻辑）
                    for (x, y, w, h) in color_boxes:
                        area = w * h
                        
                        # 过滤小物体
                        if area < 500:
                            print(f"  -> 颜色检测：面积 {area} 小于500，跳过")
                            continue
                        
                        # 过滤过大的物体（可能是墙壁、电梯门等正常设施）
                        max_area = image_area * 0.3
                        if area > max_area:
                            print(f"  -> 颜色检测：面积 {area} 过大（超过图像的30%），可能是墙壁或电梯门，跳过")
                            continue
                        
                        # 过滤顶部区域（灯光）
                        if y < img_height * 0.08 and h < img_height * 0.15:
                            print(f"  -> 颜色检测：在顶部区域且高度较小（可能是灯光），跳过")
                            continue
                        
                        # 检查是否在检测区域内（如果有配置的话）
                        if detection_zones:
                            if not self._is_in_detection_zone(x, y, w, h, detection_zones):
                                print(f"  -> 颜色检测：不在检测区域内，跳过")
                                continue
                        
                        # 添加到结果列表
                        bounding_boxes.append((x, y, w, h))
                        total_diff_area += w * h
            
            for result in results:
                for box in result.boxes:
                    # 获取边界框坐标
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    w = x2 - x1
                    h = y2 - y1
                    area = w * h
                    
                    # 获取类别信息
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    conf = float(box.conf[0])
                    
                    # 打印所有检测到的物体（调试用）- 显示完整信息
                    print(f"YOLO检测到: class_id={class_id}, class_name='{class_name}' (置信度: {conf:.3f}), 位置: ({x1}, {y1}, {w}, {h}), 面积: {area}")
                    
                    # 检查类别是否在BOX_CLASSES和EXCLUDE_CLASSES中（支持部分匹配）
                    class_name_lower = class_name.lower()
                    
                    # 检查排除类别（支持部分匹配）
                    is_in_exclude_classes = False
                    if class_name_lower in YoloDetector.EXCLUDE_CLASSES:
                        is_in_exclude_classes = True
                    else:
                        # 检查部分匹配（如 "door" 匹配 "fire door", "glass door"）
                        for exclude_class in YoloDetector.EXCLUDE_CLASSES:
                            if class_name_lower in exclude_class or exclude_class in class_name_lower:
                                is_in_exclude_classes = True
                                break
                    
                    # 支持部分匹配：检查BOX_CLASSES中是否包含该类别或被该类别包含
                    is_in_box_classes = False
                    if class_name_lower in YoloDetector.BOX_CLASSES:
                        is_in_box_classes = True
                    else:
                        # 检查部分匹配（如 "chair" 匹配 "red chair", "plastic chair"）
                        for box_class in YoloDetector.BOX_CLASSES:
                            if class_name_lower in box_class or box_class in class_name_lower:
                                is_in_box_classes = True
                                break
                    
                    print(f"  -> 是否在BOX_CLASSES: {is_in_box_classes}, 是否在EXCLUDE_CLASSES: {is_in_exclude_classes}")
                    
                    # 【优化】先检查检测区域（提高效率，避免对区域外物体做不必要的处理）
                    if detection_zones:
                        if not self._is_in_detection_zone(x1, y1, w, h, detection_zones):
                            print(f"  -> 不在检测区域内，跳过")
                            continue
                    else:
                        print(f"  -> 未配置检测区域，检测整个画面")
                    
                    # 过滤掉排除类别
                    if is_in_exclude_classes:
                        print(f"  -> 被排除类别过滤")
                        continue
                    
                    # 【新增】过滤掉既不在BOX_CLASSES也不在EXCLUDE_CLASSES的类别（未知类别）
                    # 只有明确在BOX_CLASSES中的物体才视为异常
                    if not is_in_box_classes:
                        print(f"  -> 类别 '{class_name}' 不在异常物体清单中，跳过")
                        continue
                    
                    # 降低面积要求以检测更多物体
                    if is_in_box_classes:
                        min_area = 500  # 适当提高最小面积要求，减少噪声
                        print(f"  -> 是箱子类，最小面积: {min_area}")
                    else:
                        min_area = 800  # 提高非箱子类物体的面积要求
                        print(f"  -> 非箱子类，最小面积: {min_area}")
                    
                    # 过滤掉小物体
                    if area < min_area:
                        print(f"  -> 面积 {area} 小于最小要求 {min_area}，跳过")
                        continue
                    
                    # 过滤过大的物体（可能是墙壁、电梯门等正常设施）
                    max_area = image_area * 0.3  # 超过图像30%面积的物体视为异常大面积
                    if area > max_area:
                        print(f"  -> 面积 {area} 过大（超过图像的30%），可能是墙壁或电梯门，跳过")
                        continue
                    
                    # 过滤顶部区域（灯光）
                    if y1 < img_height * 0.08 and h < img_height * 0.15:
                        print(f"  -> 在顶部区域且高度较小（可能是灯光），跳过")
                        continue
                    
                    # 【新增】宽高比过滤（过滤细长或扁平的物体，如管道、线条等）
                    aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
                    if aspect_ratio > 8:  # 宽高比超过8:1的物体视为细长物体
                        print(f"  -> 宽高比 {aspect_ratio:.2f} 过大（超过8:1），可能是管道或线条，跳过")
                        continue
                    
                    # 打印检测到箱子的信息（使用部分匹配）
                    if is_in_box_classes:
                        print(f"🔵 检测到箱子: {class_name} ({conf:.2f})")
                    
                    # 添加到结果列表
                    bounding_boxes.append((x1, y1, w, h))
                    total_diff_area += area
                    
                    # 创建轮廓数据
                    contour = np.array([
                        [[x1, y1]],
                        [[x2, y1]],
                        [[x2, y2]],
                        [[x1, y2]]
                    ], dtype=np.int32)
                    contours_list.append(contour)
                    
                    print(f"检测到物体: {class_name} ({conf:.2f}), 位置: ({x1}, {y1}, {w}, {h}), 面积: {area}")
            
            print(f"总共检测到 {len(bounding_boxes)} 个物体")
            return total_diff_area, bounding_boxes, contours_list
            
        except Exception as e:
            print(f"YOLO检测异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0, [], []
    
    @staticmethod
    def draw_detection(img, contours_list):
        """
        在图像上绘制检测结果
        :param img: 图像
        :param contours_list: 轮廓列表
        """
        if contours_list:
            cv2.drawContours(img, contours_list, -1, (0, 0, 255), 2, lineType=cv2.LINE_AA)
        return img

# 测试代码
if __name__ == '__main__':
    detector = YoloDetector()
    
    # 测试检测
    test_image = r'f:\GMweb\alarm_images\L4009B铺后通道\alarm_20260526_132158.jpg'
    if os.path.exists(test_image):
        area, boxes, contours = detector.detect_objects(test_image)
        print(f"\n检测结果:")
        print(f"总差异面积: {area}")
        print(f"边界框数量: {len(boxes)}")
    else:
        print(f"测试图像不存在: {test_image}")
