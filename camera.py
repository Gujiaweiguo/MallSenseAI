import requests
import urllib3
import cv2
import numpy as np
from requests.auth import HTTPDigestAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 统一图像尺寸
UNIFIED_WIDTH = 1000
UNIFIED_HEIGHT = 750

class DahuaCamera:
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
    
    def __init__(self, ip, port=80, username='admin', password='admin', location='未知位置'):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.location = location
        self.base_url = f"http://{self.ip}:{self.port}"
        self.session = requests.Session()
    
    def capture_image(self, save_path=None):
        auth = HTTPDigestAuth(self.username, self.password)
        
        for path in self.SNAPSHOT_PATHS:
            try:
                url = f"{self.base_url}{path}"
                response = self.session.get(url, auth=auth, verify=False, timeout=30)
                
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
                                
                                print(f"成功使用API路径: {path}，图像已缩放至 {UNIFIED_WIDTH}x{UNIFIED_HEIGHT}")
                                return resized_content
            except Exception as e:
                pass
        
        print("所有API路径均尝试失败，请检查摄像头配置")
        return None