import cv2
import numpy as np
import json
import os

# 路径
base_path = r"f:\GMweb\alarm_images\L4009B铺后通道\base_image.jpg"
alarm_path = r"f:\GMweb\alarm_images\L4009B铺后通道\alarm_last.jpg"
zones_path = r"f:\GMweb\alarm_images\L4009B铺后通道\safe_zones.json"

# 读取图像
img1 = cv2.imdecode(np.fromfile(base_path, dtype=np.uint8), cv2.IMREAD_COLOR)
img2 = cv2.imdecode(np.fromfile(alarm_path, dtype=np.uint8), cv2.IMREAD_COLOR)

print(f"基准图尺寸: {img1.shape}")
print(f"报警图尺寸: {img2.shape}")

# 调整尺寸
if img1.shape != img2.shape:
    img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

img_height, img_width = img2.shape[:2]
print(f"图像尺寸: {img_width}x{img_height}, 总面积: {img_width * img_height}")

# 灰度图
gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

# 灰度差异
diff_gray = cv2.absdiff(gray2, gray1)
print(f"\n灰度差异统计:")
print(f"  均值: {np.mean(diff_gray):.2f}")
print(f"  最大值: {np.max(diff_gray)}")
print(f"  最小值: {np.min(diff_gray)}")
print(f"  标准差: {np.std(diff_gray):.2f}")

# 二值化
threshold_value = 20
_, thresh = cv2.threshold(diff_gray, threshold_value, 255, cv2.THRESH_BINARY)
white_pixels = cv2.countNonZero(thresh)
print(f"\n二值化后 (阈值={threshold_value}):")
print(f"  白色像素数: {white_pixels}")
print(f"  白色像素占比: {white_pixels / (img_width * img_height) * 100:.2f}%")

# 腐蚀
erosion_kernel = np.ones((3, 3), np.uint8)
thresh_eroded = cv2.erode(thresh, erosion_kernel, iterations=1)
white_pixels_eroded = cv2.countNonZero(thresh_eroded)
print(f"\n腐蚀后:")
print(f"  白色像素数: {white_pixels_eroded}")

# 形态学操作
kernel_size = 5
kernel = np.ones((kernel_size, kernel_size), np.uint8)
thresh_morph = cv2.morphologyEx(thresh_eroded, cv2.MORPH_CLOSE, kernel)
thresh_morph = cv2.morphologyEx(thresh_morph, cv2.MORPH_OPEN, kernel)
white_pixels_morph = cv2.countNonZero(thresh_morph)
print(f"\n形态学操作后 (核大小={kernel_size}):")
print(f"  白色像素数: {white_pixels_morph}")

# 查找轮廓
contours, _ = cv2.findContours(thresh_morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"\n检测到轮廓数量: {len(contours)}")

# 加载检测区域
with open(zones_path, 'r', encoding='utf-8') as f:
    detection_zones = json.load(f)
print(f"检测区域数量: {len(detection_zones)}")

def is_in_zone(x, y, w, h, zones):
    """检查物体是否在检测区域内"""
    cx, cy = x + w // 2, y + h // 2
    for zone in zones:
        if zone['type'] == 'polygon':
            pts = np.array(zone['data'], dtype=np.int32).reshape((-1, 1, 2))
            if cv2.pointPolygonTest(pts, (float(cx), float(cy)), False) >= 0:
                return True
    return False

# 分析每个轮廓
min_area = 500
print(f"\n轮廓分析 (最小面积={min_area}):")
print("-" * 80)

valid_count = 0
filtered_count = 0

for i, contour in enumerate(contours):
    area = cv2.contourArea(contour)
    if area <= min_area:
        continue
    
    x, y, w, h = cv2.boundingRect(contour)
    
    # 检查检测区域
    in_zone = is_in_zone(x, y, w, h, detection_zones)
    
    # 检查固定物体过滤
    is_fixed = False  # 简化，跳过这个检查
    
    # 计算位置比例
    top_ratio = y / img_height
    right_ratio = (x + w) / img_width
    
    # 检查各种过滤条件
    roi = gray2[y:y+h, x:x+w]
    mean_val = np.mean(roi)
    std_val = np.std(roi)
    
    # 颜色检查
    roi_color = img2[y:y+h, x:x+w]
    hsv_roi = cv2.cvtColor(roi_color, cv2.COLOR_BGR2HSV)
    hue = np.mean(hsv_roi[:, :, 0])
    saturation = np.mean(hsv_roi[:, :, 1])
    
    reason = "通过"
    if not in_zone:
        reason = "不在检测区域内"
    elif right_ratio > 0.75 and h > img_height * 0.25:
        reason = "右侧大物体过滤"
    elif 40 <= hue <= 80 and saturation > 30:
        reason = "绿色指示灯过滤"
    elif mean_val >= 230:
        reason = "高亮度过滤"
    elif saturation < 20 and mean_val >= 180:
        reason = "低饱和度高亮度过滤"
    elif top_ratio < 0.18 and mean_val >= 165:
        reason = "顶部区域过滤"
    elif std_val <= 4 and mean_val >= 200:
        reason = "纹理均匀过滤"
    
    if reason == "通过":
        valid_count += 1
    else:
        filtered_count += 1
    
    print(f"轮廓#{i}: 位置({x},{y}) 大小({w}x{h}) 面积={area:.0f}")
    print(f"  均值={mean_val:.1f} 标准差={std_val:.1f} Hue={hue:.1f} Sat={saturation:.1f}")
    print(f"  检测区域={'是' if in_zone else '否'} 右侧比例={right_ratio:.2f}")
    print(f"  结果: {reason}")
    print()

print("=" * 80)
print(f"总结: 有效轮廓={valid_count}, 被过滤={filtered_count}")

# 保存差异图用于可视化
cv2.imwrite(r"f:\GMweb\debug_diff.jpg", diff_gray)
cv2.imwrite(r"f:\GMweb\debug_thresh.jpg", thresh_morph)
print(f"\n已保存差异图: debug_diff.jpg, debug_thresh.jpg")
