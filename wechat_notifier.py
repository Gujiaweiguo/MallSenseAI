import requests
import json
import base64
import hashlib
from config import WECHAT_CONFIG

class WechatNotifier:
    def __init__(self):
        self.webhook_url = WECHAT_CONFIG['webhook_url']
        self.enabled = WECHAT_CONFIG['enabled']
    
    def send_text(self, content):
        if not self.enabled:
            return False
        
        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            response = requests.post(self.webhook_url, json=payload)
            result = response.json()
            if result.get('errcode') == 0:
                print("企业微信消息发送成功")
                return True
            else:
                print(f"企业微信消息发送失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            print(f"发送企业微信消息异常: {str(e)}")
            return False
    
    def send_image(self, image_path):
        if not self.enabled:
            return False
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            base64_data = base64.b64encode(image_data).decode('utf-8')
            md5_hash = hashlib.md5(image_data).hexdigest()
            
            payload = {
                "msgtype": "image",
                "image": {
                    "base64": base64_data,
                    "md5": md5_hash
                }
            }
            response = requests.post(self.webhook_url, json=payload)
            result = response.json()
            if result.get('errcode') == 0:
                print("企业微信图片发送成功")
                return True
            else:
                print(f"企业微信图片发送失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            print(f"发送企业微信图片异常: {str(e)}")
            return False
    
    def send_alarm(self, message, image_path):
        if not self.enabled:
            return False
        
        success = self.send_text(message)
        if success and image_path:
            self.send_image(image_path)
        return success
    
    def send_report(self, report_content):
        if not self.enabled:
            return False
        
        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": report_content
                }
            }
            response = requests.post(self.webhook_url, json=payload)
            result = response.json()
            if result.get('errcode') == 0:
                print("企业微信检查报告发送成功")
                return True
            else:
                print(f"企业微信检查报告发送失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            print(f"发送企业微信检查报告异常: {str(e)}")
            return False