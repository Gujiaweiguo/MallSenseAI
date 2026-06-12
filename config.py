import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CAMERA_CONFIGS = [
    {
        'ip': '10.25.4.59',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': 'L4009B铺后通道'
    },
    {
        'ip': '10.25.4.50',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': 'L4021A铺后通道'
    },
    {
        'ip': '10.25.4.40',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': 'L4016铺后通道'
    },
    {
        'ip': '10.25.4.6',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层影城旁通道'
    },
    {
        'ip': '10.25.4.76',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层东山4038铺旁4号消防梯'
    },
    {
        'ip': '10.25.4.66',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层东山4035铺后通道'
    },
    {
        'ip': '10.25.4.7',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层西山4013后通道1号消防梯'
    },
    {
        'ip': '10.25.4.125',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层西山4014铺旁通道'
    },
    {
        'ip': '10.25.4.117',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层西山4021B铺外围'
    },
    {
        'ip': '10.25.4.60',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层东山4009B铺后通道2'
    },
    {
        'ip': '10.25.4.83',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层东山4004B铺旁通道2'
    },
    {
        'ip': '10.25.4.41',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层西山4018铺后通道'
    },
    {
        'ip': '10.25.4.47',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层西山4021A-H18H19货梯厅'
    },
    {
        'ip': '10.25.4.27',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层西山4022铺旁'
    },
    {
        'ip': '10.25.4.96',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层东山4001铺旁11号货梯厅'
    },
    {
        'ip': '10.25.4.128',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层西山4014铺旁通道'
    },
    {
        'ip': '10.25.4.119',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层西山4021B铺内通道'
    },
    {
        'ip': '10.25.4.111',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层东山4007铺旁通道'
    },
    {
        'ip': '10.25.4.129',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层西山4014铺旁通道3'
    },
    {
        'ip': '10.25.4.97',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层西山4001铺旁通道3'
    },
    {
        'ip': '10.25.4.65',
        'port': 80,
        'username': 'admin',
        'password': 'admin123',
        'location': '4层东山4035铺后通道1'
    }
]

ALARM_CONFIG = {
    'threshold': 3000,                # 触发阈值
    'interval_minutes': 1,
    'static_wait_minutes': 1,         # 调整为 1 次，总共检测 2 次
    'diff_threshold': 18,             # 降低差分阈值，提高对箱子的检测灵敏度
    'filter_fixed_objects': False,     # 关闭固定物体过滤
    'min_contour_area': 4000,         # 最小轮廓面积
    'base_image_path': os.path.join(BASE_DIR, 'base_image.jpg'),
    'alarm_images_dir': os.path.join(BASE_DIR, 'alarm_images'),
    'log_file': os.path.join(BASE_DIR, 'alarm_system.log'),
    
    'min_area_ratio': 0.02,           # 最小占比要求 (2%)
    'max_area_ratio': 0.25,           # 物体占画面最大比例 (25%)
    'min_stay_frames': 2,             # 物体停留帧数 (2 帧)
    'sensitivity': 85,                # 灵敏度 (85)
    'detection_zone': 'full',         # 全图检测
    'human_filter_enabled': True,     # 人体过滤
    'small_object_filter': False,     # 关闭小物体过滤
    'area_ratio_threshold': 0.02,     # 区域占比触发阈值 (2%)
    'detection_zone_top': 0.18,       # 检测区域顶部排除比例 (18%) - 天花板灯光
    'detection_zone_bottom': 0.08,    # 检测区域底部排除比例 (8%) - 底部水印
    'max_single_object_area': 200000, # 单个物体最大面积限制
    
    # 灯光过滤专用参数
    'max_brightness': 230,            # 最大亮度阈值
    'min_saturation': 20,             # 最小饱和度阈值（过滤低饱和度灯光）
    'min_std': 4,                     # 最小标准差（纹理丰富度）
    'min_edge_ratio': 0.015,          # 最小边缘比例
    'filter_door_region': True,       # 启用门区域过滤
    'max_brightness': 230,            # 最大亮度过滤阈值
    'min_brightness': 20,             # 最小亮度过滤阈值
    'min_std': 5,                     # 最小标准差过滤阈值
    
    # 双重检测配置
    'enable_yolo_detection': True,    # 启用YOLO检测
    'enable_image_comparison': True,  # 启用图像对比检测
    'detection_mode': 'max',          # 合并模式: 'max'(取最大值), 'sum'(求和), 'yolo_only'(仅YOLO), 'image_only'(仅图像对比)
    'yolo_weight': 1.0,               # YOLO检测权重
    'image_weight': 1.0,              # 图像对比权重
}

WECHAT_CONFIG = {
    'webhook_url': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=84dca394-25b4-48b2-b108-0c7fbce8f656',
    'enabled': True
}

os.makedirs(ALARM_CONFIG['alarm_images_dir'], exist_ok=True)