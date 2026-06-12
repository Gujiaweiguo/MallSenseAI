import os
import json
import glob

# 目标图像分辨率
UNIFIED_WIDTH = 1000
UNIFIED_HEIGHT = 750

# 可能的原始分辨率（按优先级排序）
POSSIBLE_ORIGINS = [
    (1600, 1200, "1600x1200"),  # 最近使用的尺寸，优先尝试
    (8000, 6000, "8000x6000"),  # 原始摄像头分辨率
]

print(f"目标分辨率: {UNIFIED_WIDTH}x{UNIFIED_HEIGHT}")
print("=" * 60)

def detect_original_resolution(zones):
    """检测坐标的原始分辨率"""
    max_x = 0
    max_y = 0
    
    for zone in zones:
        if zone['type'] == 'polygon':
            for point in zone['data']:
                x, y = point[0], point[1]
                max_x = max(max_x, x)
                max_y = max(max_y, y)
        elif zone['type'] == 'rect':
            x, y, w, h = zone['data']
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)
    
    # 如果坐标已经在目标范围内，不需要转换
    if max_x <= UNIFIED_WIDTH and max_y <= UNIFIED_HEIGHT:
        return None, None, "已转换或过小"
    
    # 尝试匹配可能的原始分辨率
    for orig_w, orig_h, name in POSSIBLE_ORIGINS:
        # 检查坐标是否在该分辨率的合理范围内（允许 10% 误差）
        if max_x <= orig_w * 1.1 and max_y <= orig_h * 1.1:
            return orig_w, orig_h, name
    
    # 如果都不匹配，默认使用 1600x1200
    return 1600, 1200, "1600x1200 (默认)"

def is_already_converted(zones):
    """检查坐标是否已经转换过（在 1000x750 范围内）"""
    orig_w, orig_h, resolution = detect_original_resolution(zones)
    return resolution == "已转换或过小"

# 查找所有 safe_zones.json 文件
alarm_images_dir = os.path.join(os.path.dirname(__file__), 'alarm_images')
safe_zones_files = glob.glob(os.path.join(alarm_images_dir, '**', 'safe_zones.json'), recursive=True)

print(f"找到 {len(safe_zones_files)} 个 safe_zones.json 文件")
print("=" * 60)

for file_path in safe_zones_files:
    relative_path = os.path.relpath(file_path, alarm_images_dir)
    print(f"\n处理: {relative_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            zones = json.load(f)
        
        # 检测原始分辨率
        orig_w, orig_h, resolution = detect_original_resolution(zones)
        
        # 检查是否已经转换过
        if is_already_converted(zones):
            print(f"  ⏭️  坐标已在 {UNIFIED_WIDTH}x{UNIFIED_HEIGHT} 范围内，跳过转换")
            continue
        
        # 计算缩放比例
        scale_x = UNIFIED_WIDTH / orig_w
        scale_y = UNIFIED_HEIGHT / orig_h
        print(f"  检测到原始分辨率: {resolution}，缩放比例: X={scale_x:.4f}, Y={scale_y:.4f}")
        
        converted_zones = []
        for zone in zones:
            converted_zone = {'type': zone['type']}
            
            if zone['type'] == 'polygon':
                # 转换多边形坐标
                converted_points = []
                for point in zone['data']:
                    new_x = int(point[0] * scale_x)
                    new_y = int(point[1] * scale_y)
                    converted_points.append([new_x, new_y])
                converted_zone['data'] = converted_points
                
                # 打印转换示例
                if len(zone['data']) > 0:
                    old_point = zone['data'][0]
                    new_point = converted_points[0]
                    print(f"  多边形坐标转换: {old_point} → {new_point}")
            
            elif zone['type'] == 'rect':
                # 转换矩形坐标
                x, y, w, h = zone['data']
                new_x = int(x * scale_x)
                new_y = int(y * scale_y)
                new_w = int(w * scale_x)
                new_h = int(h * scale_y)
                converted_zone['data'] = [new_x, new_y, new_w, new_h]
                print(f"  矩形坐标转换: {zone['data']} → {converted_zone['data']}")
            
            converted_zones.append(converted_zone)
        
        # 保存转换后的坐标
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(converted_zones, f, ensure_ascii=False)
        
        print(f"  ✅ 转换完成")
        
    except Exception as e:
        print(f"   转换失败: {str(e)}")

print("\n" + "=" * 60)
print("所有坐标转换完成！")
print("请重启系统并重新设置基准图像。")
