"""
手动更新基准图像
"""
import cv2
import os
import json
from config import CAMERA_CONFIGS, ALARM_CONFIG

def update_base_image(camera_config):
    """更新指定摄像头的基准图像"""
    print(f"正在更新摄像头 {camera_config['location']} 的基准图像...")
    
    # 尝试多种RTSP URL格式
    rtsp_urls = [
        f"rtsp://{camera_config['username']}:{camera_config['password']}@{camera_config['ip']}:{camera_config['port']}/Streaming/Channels/101",
        f"rtsp://{camera_config['username']}:{camera_config['password']}@{camera_config['ip']}/Streaming/Channels/101",
        f"rtsp://{camera_config['username']}:{camera_config['password']}@{camera_config['ip']}:554/Streaming/Channels/101",
        f"rtsp://{camera_config['username']}:{camera_config['password']}@{camera_config['ip']}:554/h264/ch1/main/av_stream",
        f"http://{camera_config['username']}:{camera_config['password']}@{camera_config['ip']}:{camera_config['port']}/video.cgi"
    ]
    
    # 打开摄像头 - 尝试多种URL格式
    cap = None
    for url in rtsp_urls:
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            print(f"成功连接: {url}")
            break
        else:
            print(f"尝试失败: {url}")
            cap.release()
    
    if not cap or not cap.isOpened():
        print(f"无法连接到摄像头: {camera_config['ip']}")
        return False
    
    print("摄像头连接成功，正在捕获基准图像...")
    
    # 等待摄像头稳定
    for _ in range(30):
        cap.read()
    
    # 捕获多帧取平均
    frames = []
    for _ in range(5):
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
    
    cap.release()
    
    if not frames:
        print("无法捕获图像")
        return False
    
    # 取中间帧作为基准图像
    base_frame = frames[len(frames) // 2]
    
    # 保存基准图像
    alarm_dir = ALARM_CONFIG['alarm_images_dir']
    location = camera_config['location']
    location_dir = os.path.join(alarm_dir, location)
    os.makedirs(location_dir, exist_ok=True)
    
    base_image_path = os.path.join(location_dir, 'base_image.jpg')
    cv2.imwrite(base_image_path, base_frame)
    print(f"基准图像已保存到: {base_image_path}")
    
    # 创建默认安全区域配置
    safe_zones_path = os.path.join(location_dir, 'safe_zones.json')
    if not os.path.exists(safe_zones_path):
        default_safe_zones = [
            {"x": 0, "y": 0, "width": 300, "height": 200, "name": "左上角安全区"},
            {"x": 0, "y": 400, "width": 200, "height": 400, "name": "左下角安全区"}
        ]
        with open(safe_zones_path, 'w', encoding='utf-8') as f:
            json.dump(default_safe_zones, f, ensure_ascii=False, indent=2)
        print(f"已创建默认安全区域配置: {safe_zones_path}")
    
    return True

if __name__ == '__main__':
    if CAMERA_CONFIGS:
        # 更新第一个摄像头
        camera_config = CAMERA_CONFIGS[0]
        success = update_base_image(camera_config)
        if success:
            print("基准图像更新成功！")
        else:
            print("基准图像更新失败！")
    else:
        print("未配置摄像头")
