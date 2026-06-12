import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import urllib3
from requests.auth import HTTPDigestAuth
import cv2
import numpy as np

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 统一图像尺寸
UNIFIED_WIDTH = 1000
UNIFIED_HEIGHT = 750

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'camera_configs.json')
ALARM_IMAGES_DIR = os.path.join(BASE_DIR, 'alarm_images')

os.makedirs(ALARM_IMAGES_DIR, exist_ok=True)

SNAPSHOT_PATHS = [
    '/cgi-bin/snapshot.cgi',
    '/cgi-bin/api.cgi?cmd=Snap&channel=0&rs=wuuPhkmUCeI9WG7C',
    '/cgi-bin/api.cgi?cmd=Snap&channel=1&rs=wuuPhkmUCeI9WG7C',
    '/snapshot.jpg',
    '/cgi-bin/snapshot.cgi?channel=1',
    '/cgi-bin/snapshot.cgi?channel=0',
    '/cgi-bin/webgrab.cgi',
    '/cgi-bin/encoder/snapshot.cgi',
    '/cgi-bin/encoder/snapshot.cgi?channel=0'
]

def load_configs():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_configs(configs):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(configs, f, ensure_ascii=False, indent=2)

def test_camera_connection(camera_config):
    ip = camera_config['ip']
    port = camera_config.get('port', 80)
    username = camera_config.get('username', 'admin')
    password = camera_config.get('password', '')
    
    base_url = f"http://{ip}:{port}"
    auth = HTTPDigestAuth(username, password)
    
    for path in SNAPSHOT_PATHS:
        try:
            url = f"{base_url}{path}"
            response = requests.get(url, auth=auth, verify=False, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                content_length = len(response.content)
                if content_type.startswith('image/') or (content_length > 1000 and content_length < 10000000):
                    return True, path
        except Exception as e:
            pass
    return False, None

def capture_image(camera_config, save_path=None):
    ip = camera_config['ip']
    port = camera_config.get('port', 80)
    username = camera_config.get('username', 'admin')
    password = camera_config.get('password', '')
    
    base_url = f"http://{ip}:{port}"
    auth = HTTPDigestAuth(username, password)
    
    for path in SNAPSHOT_PATHS:
        try:
            url = f"{base_url}{path}"
            response = requests.get(url, auth=auth, verify=False, timeout=30)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                content_length = len(response.content)
                
                if content_type.startswith('image/') or (content_length > 1000 and content_length < 10000000):
                    # 解码图像并缩放到统一尺寸
                    img = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)
                    if img is not None:
                        # 缩放到 1920x1080
                        img_resized = cv2.resize(img, (UNIFIED_WIDTH, UNIFIED_HEIGHT), interpolation=cv2.INTER_AREA)
                        
                        # 编码为 JPEG
                        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 95, int(cv2.IMWRITE_JPEG_OPTIMIZE), 1]
                        _, buffer = cv2.imencode('.jpg', img_resized, encode_params)
                        
                        if buffer is not None:
                            resized_content = buffer.tobytes()
                            
                            if save_path:
                                with open(save_path, 'wb') as f:
                                    f.write(resized_content)
                            
                            return resized_content, path
        except Exception as e:
            pass
    
    return None, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    cameras = load_configs()
    for camera in cameras:
        base_image_path = os.path.join(ALARM_IMAGES_DIR, f'base_{camera["ip"].replace(".", "_")}.jpg')
        camera['has_base_image'] = os.path.exists(base_image_path)
    return jsonify(cameras)

@app.route('/api/cameras', methods=['POST'])
def add_camera():
    data = request.json
    required_fields = ['ip', 'location']
    
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'message': f'缺少必填字段: {field}'}), 400
    
    camera_config = {
        'ip': data['ip'],
        'port': data.get('port', 80),
        'username': data.get('username', 'admin'),
        'password': data.get('password', ''),
        'location': data['location']
    }
    
    success, path = test_camera_connection(camera_config)
    
    if success:
        cameras = load_configs()
        cameras.append(camera_config)
        save_configs(cameras)
        return jsonify({
            'success': True,
            'message': f'摄像头添加成功，使用API路径: {path}',
            'camera': camera_config
        })
    else:
        return jsonify({'success': False, 'message': '无法连接到摄像头，请检查配置'}), 400

@app.route('/api/cameras/<int:index>', methods=['DELETE'])
def delete_camera(index):
    cameras = load_configs()
    if index < 0 or index >= len(cameras):
        return jsonify({'success': False, 'message': '摄像头不存在'}), 404
    
    camera = cameras.pop(index)
    
    base_image_path = os.path.join(ALARM_IMAGES_DIR, f'base_{camera["ip"].replace(".", "_")}.jpg')
    if os.path.exists(base_image_path):
        os.remove(base_image_path)
    
    save_configs(cameras)
    return jsonify({'success': True, 'message': '摄像头已删除'})

@app.route('/api/cameras/<int:index>/test', methods=['GET'])
def test_camera(index):
    cameras = load_configs()
    if index < 0 or index >= len(cameras):
        return jsonify({'success': False, 'message': '摄像头不存在'}), 404
    
    success, path = test_camera_connection(cameras[index])
    if success:
        return jsonify({'success': True, 'message': f'连接成功，使用API路径: {path}'})
    else:
        return jsonify({'success': False, 'message': '连接失败，请检查配置'}), 400

@app.route('/api/cameras/<int:index>/snapshot', methods=['GET'])
def get_snapshot(index):
    cameras = load_configs()
    if index < 0 or index >= len(cameras):
        return jsonify({'success': False, 'message': '摄像头不存在'}), 404
    
    image_data, path = capture_image(cameras[index])
    if image_data:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_path = os.path.join(ALARM_IMAGES_DIR, f'temp_snapshot_{cameras[index]["ip"].replace(".", "_")}_{timestamp}.jpg')
        with open(temp_path, 'wb') as f:
            f.write(image_data)
        return jsonify({'success': True, 'image_path': f'/images/temp_snapshot_{cameras[index]["ip"].replace(".", "_")}_{timestamp}.jpg'})
    else:
        return jsonify({'success': False, 'message': '无法获取画面'}), 400

@app.route('/api/cameras/<int:index>/set_base', methods=['POST'])
def set_base_image(index):
    cameras = load_configs()
    if index < 0 or index >= len(cameras):
        return jsonify({'success': False, 'message': '摄像头不存在'}), 404
    
    camera = cameras[index]
    base_image_path = os.path.join(ALARM_IMAGES_DIR, f'base_{camera["ip"].replace(".", "_")}.jpg')
    
    image_data, path = capture_image(camera, base_image_path)
    
    if image_data:
        return jsonify({
            'success': True,
            'message': '基准图像已设置',
            'base_image_path': f'/images/base_{camera["ip"].replace(".", "_")}.jpg'
        })
    else:
        return jsonify({'success': False, 'message': '无法获取画面设置基准图像'}), 400

@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(ALARM_IMAGES_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)