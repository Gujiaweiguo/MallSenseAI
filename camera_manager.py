import os
import json
import time
import threading
import requests
import urllib3
from requests.auth import HTTPDigestAuth
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'camera_configs.json')
CONFIG_PY_FILE = os.path.join(BASE_DIR, 'config.py')
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

def test_camera_connection_thread(camera_config):
    ip = camera_config['ip']
    port = camera_config.get('port', 80)
    username = camera_config.get('username', 'admin')
    password = camera_config.get('password', '')
    
    base_url = f"http://{ip}:{port}"
    auth = HTTPDigestAuth(username, password)
    
    for path in SNAPSHOT_PATHS:
        try:
            url = f"{base_url}{path}"
            response = requests.get(url, auth=auth, verify=False, timeout=5)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                content_length = len(response.content)
                if content_type.startswith('image/') or (content_length > 1000 and content_length < 10000000):
                    return True, path
        except Exception as e:
            pass
    return False, None

def capture_image_thread(camera_config, save_path=None):
    ip = camera_config['ip']
    port = camera_config.get('port', 80)
    username = camera_config.get('username', 'admin')
    password = camera_config.get('password', '')
    
    base_url = f"http://{ip}:{port}"
    auth = HTTPDigestAuth(username, password)
    
    # 统一图像尺寸
    UNIFIED_WIDTH = 1600
    UNIFIED_HEIGHT = 1200
    
    for path in SNAPSHOT_PATHS:
        try:
            url = f"{base_url}{path}"
            response = requests.get(url, auth=auth, verify=False, timeout=3)
            
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
                            
                            return resized_content
        except Exception as e:
            pass
    
    return None

class CameraManager:
    def __init__(self, master):
        self.master = master
        self.master.title("摄像头管理系统")
        self.master.geometry("1350x900")
        
        self.cameras = self.load_configs()
        self.current_camera_index = -1
        self.is_streaming = False
        self.stream_thread = None
        self.is_busy = False
        
        self.is_mark_mode = False
        self.marks = []  # 存储标记区域，支持矩形和多边形
        self.mark_mode = 'rect'  # rect: 矩形, square: 正方形, polygon: 不规则多边形
        self.start_x = 0
        self.start_y = 0
        self.current_rect = None
        self.current_polygon = []  # 当前正在绘制的多边形点
        self.original_img = None
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_widgets()
        self.update_camera_list()
    
    def on_closing(self):
        if self.current_camera_index >= 0 and self.marks:
            camera = self.cameras[self.current_camera_index]
            self.save_marks(camera)
            print(f"退出时自动保存标记: {len(self.marks)} 个")
        self.master.destroy()
    
    def load_configs(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save_configs(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cameras, f, ensure_ascii=False, indent=2)
        
        self.update_config_py()
    
    def update_config_py(self):
        try:
            with open(CONFIG_PY_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            config_lines = []
            for camera in self.cameras:
                config_line = f"""    {{
        'ip': '{camera['ip']}',
        'port': {camera['port']},
        'username': '{camera['username']}',
        'password': '{camera['password']}',
        'location': '{camera['location']}'
    }}"""
                config_lines.append(config_line)
            
            config_content = ",\n".join(config_lines)
            
            import re
            content = re.sub(
                r"CAMERA_CONFIGS = \[.*?\]",
                f"CAMERA_CONFIGS = [\n{config_content}\n]",
                content,
                flags=re.DOTALL
            )
            
            with open(CONFIG_PY_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("config.py 已同步更新")
        except Exception as e:
            print(f"更新 config.py 失败: {str(e)}")
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        
        left_frame = ttk.Frame(main_frame, width=300)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=3)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=0)  # 控制按钮行不扩展
        
        ttk.Label(left_frame, text="摄像头列表", font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.camera_listbox = tk.Listbox(left_frame, width=40, height=20)
        self.camera_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.camera_listbox.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.camera_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.camera_listbox.bind('<<ListboxSelect>>', self.on_camera_select)
        
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        
        ttk.Button(button_frame, text="添加摄像头", command=self.add_camera).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="删除摄像头", command=self.delete_camera).grid(row=0, column=1, padx=(5, 5))
        ttk.Button(button_frame, text="测试连接", command=self.test_connection).grid(row=0, column=2, padx=(5, 5))
        
        # 图像容器，固定尺寸防止占满所有空间
        self.image_container = tk.Frame(right_frame, width=1000, height=750, bg='black')
        self.image_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 10))
        self.image_container.grid_propagate(False)  # 禁止子组件改变容器大小
        
        # 图像标签
        self.image_label = ttk.Label(self.image_container, text="摄像头画面", relief=tk.SUNKEN)
        self.image_label.place(relx=0.5, rely=0.5, anchor='center')
        
        control_frame = ttk.Frame(right_frame)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_label = ttk.Label(control_frame, text="状态: 未选择摄像头", foreground='gray')
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.stream_button = ttk.Button(control_frame, text="开始预览", command=self.toggle_stream)
        self.stream_button.grid(row=0, column=1, padx=(10, 5))
        
        self.set_base_button = ttk.Button(control_frame, text="设为基准图像", command=self.set_base_image, state=tk.DISABLED)
        self.set_base_button.grid(row=0, column=2, padx=(5, 0))
        
        self.mark_button = ttk.Button(control_frame, text="标记检测区域", command=self.toggle_mark_mode, state=tk.DISABLED)
        self.mark_button.grid(row=0, column=3, padx=(5, 0))
        
        # 绘制模式选择（仅保留多边形）
        self.mark_mode_var = tk.StringVar(value='polygon')
        self.mark_mode_frame = ttk.Frame(control_frame)
        self.mark_mode_frame.grid(row=0, column=4, padx=(5, 0))
        
        ttk.Radiobutton(self.mark_mode_frame, text="多边形", variable=self.mark_mode_var, value='polygon', command=self.on_mark_mode_change).grid(row=0, column=0, padx=(0, 3))
        
        self.clear_marks_button = ttk.Button(control_frame, text="清除标记", command=self.clear_marks, state=tk.DISABLED)
        self.clear_marks_button.grid(row=0, column=5, padx=(5, 0))
    
    def get_camera_dir(self, camera):
        camera_dir = os.path.join(ALARM_IMAGES_DIR, camera['location'])
        os.makedirs(camera_dir, exist_ok=True)
        return camera_dir
    
    def get_base_image_path(self, camera):
        camera_dir = self.get_camera_dir(camera)
        return os.path.join(camera_dir, 'base_image.jpg')
    
    def update_camera_list(self):
        self.camera_listbox.delete(0, tk.END)
        for i, camera in enumerate(self.cameras):
            base_image_path = self.get_base_image_path(camera)
            status = " ✓" if os.path.exists(base_image_path) else ""
            self.camera_listbox.insert(tk.END, f"{camera['location']} ({camera['ip']}){status}")
    
    def add_camera(self):
        dialog = AddCameraDialog(self.master)
        self.master.wait_window(dialog)
        if dialog.result:
            camera = dialog.result
            print(f"尝试添加摄像头: {camera}")
            self.cameras.append(camera)
            self.save_configs()
            self.update_camera_list()
            print(f"摄像头添加成功，当前列表: {len(self.cameras)} 个")
            messagebox.showinfo("成功", f"摄像头添加成功!\n位置: {camera['location']}\nIP: {camera['ip']}:{camera['port']}")
        else:
            print("用户取消添加摄像头")
    
    def delete_camera(self):
        selection = self.camera_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个摄像头")
            return
        
        index = selection[0]
        camera = self.cameras[index]
        
        if messagebox.askyesno("确认删除", f"确定要删除摄像头: {camera['location']} ({camera['ip']})?"):
            camera_dir = self.get_camera_dir(camera)
            if os.path.exists(camera_dir):
                import shutil
                shutil.rmtree(camera_dir)
            
            del self.cameras[index]
            self.save_configs()
            self.update_camera_list()
            self.current_camera_index = -1
            self.clear_image()
            self.status_label.config(text="状态: 未选择摄像头")
            self.set_base_button.config(state=tk.DISABLED)
    
    def test_connection(self):
        selection = self.camera_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个摄像头")
            return
        
        if self.is_busy:
            messagebox.showwarning("警告", "正在处理中，请稍候")
            return
        
        index = selection[0]
        camera = self.cameras[index]
        self.is_busy = True
        self.status_label.config(text=f"状态: 正在测试连接...", foreground='blue')
        
        def test_thread():
            success, path = test_camera_connection_thread(camera)
            self.master.after(0, lambda: self.on_test_complete(success, path, camera))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def on_test_complete(self, success, path, camera):
        self.is_busy = False
        if success:
            self.status_label.config(text=f"状态: 连接成功", foreground='green')
            messagebox.showinfo("成功", f"连接成功!\n使用API路径: {path}")
        else:
            self.status_label.config(text=f"状态: 连接失败", foreground='red')
            messagebox.showerror("失败", "无法连接到摄像头，请检查配置")
    
    def on_camera_select(self, event):
        selection = self.camera_listbox.curselection()
        if selection:
            if self.current_camera_index >= 0 and self.marks:
                old_camera = self.cameras[self.current_camera_index]
                self.save_marks(old_camera)
                print(f"切换摄像头时保存标记: {len(self.marks)} 个")
            
            self.current_camera_index = selection[0]
            camera = self.cameras[self.current_camera_index]
            self.status_label.config(text=f"状态: 已选择 {camera['location']}", foreground='gray')
            self.set_base_button.config(state=tk.NORMAL)
            
            self.marks = []
            self.clear_image()
    
    def capture_and_display_async(self):
        if self.current_camera_index < 0 or self.is_busy:
            return
        
        self.is_busy = True
        camera = self.cameras[self.current_camera_index]
        self.status_label.config(text=f"状态: 正在获取画面...", foreground='blue')
        
        def capture_thread():
            image_data = capture_image_thread(camera)
            self.master.after(0, lambda: self.on_capture_complete(image_data))
        
        threading.Thread(target=capture_thread, daemon=True).start()
    
    def on_capture_complete(self, image_data):
        self.is_busy = False
        
        if image_data:
            try:
                img_array = np.frombuffer(image_data, np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                # 图像已是 1000x750 统一尺寸，直接显示
                # 不再进行额外缩放，确保坐标一致
                
                self.image_scale = 1.0
                self.original_width = 1000  # 统一尺寸
                self.original_height = 750  # 统一尺寸
                self.display_width = 1000
                self.display_height = 750
                
                self.original_img = Image.fromarray(img)
                photo = ImageTk.PhotoImage(image=self.original_img)
                self.image_label.config(image=photo)
                self.image_label.image = photo
                
                self.last_image_data = image_data
                self.status_label.config(text=f"状态: 已连接", foreground='green')
                self.mark_button.config(state=tk.NORMAL)
                
                if self.current_camera_index >= 0:
                    camera = self.cameras[self.current_camera_index]
                    self.load_marks(camera)
                    if self.marks:
                        self.draw_marks()
            except Exception as e:
                self.status_label.config(text=f"状态: 图像处理失败 - {str(e)}", foreground='red')
        else:
            self.status_label.config(text=f"状态: 无法获取画面", foreground='red')
    
    def clear_image(self):
        self.image_label.config(image='')
        self.image_label.image = None
        self.last_image_data = None
    
    def toggle_stream(self):
        if self.is_streaming:
            self.stop_stream()
        else:
            self.start_stream()
    
    def start_stream(self):
        if self.current_camera_index < 0:
            messagebox.showwarning("警告", "请先选择一个摄像头")
            return
        
        self.is_streaming = True
        self.stream_button.config(text="停止预览")
        self.stream_thread = threading.Thread(target=self.stream_loop, daemon=True)
        self.stream_thread.start()
    
    def stop_stream(self):
        self.is_streaming = False
        self.stream_button.config(text="开始预览")
    
    def stream_loop(self):
        while self.is_streaming:
            if not self.is_busy:
                self.capture_and_display_async()
            time.sleep(0.1)
    
    def set_base_image(self):
        if self.current_camera_index < 0:
            messagebox.showwarning("警告", "请先选择一个摄像头")
            return
        
        if not hasattr(self, 'last_image_data') or self.last_image_data is None:
            messagebox.showwarning("警告", "请先获取摄像头画面")
            return
        
        camera = self.cameras[self.current_camera_index]
        base_image_path = self.get_base_image_path(camera)
        
        print(f"尝试保存基准图像到: {base_image_path}")
        
        try:
            img_array = np.frombuffer(self.last_image_data, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                print("图像解码失败")
                messagebox.showerror("失败", "图像解码失败")
                return
            
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            draw = ImageDraw.Draw(pil_img)
            
            try:
                font = ImageFont.truetype('simhei.ttf', 60)
            except:
                font = ImageFont.truetype('msyh.ttc', 60)
            
            bbox = draw.textbbox((0, 0), '[标准]', font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            img_width, img_height = pil_img.size
            x = img_width - text_width - 10
            y = img_height - text_height - 10
            draw.text((x, y), '[标准]', fill=(0, 255, 0), font=font)
            
            if self.marks:
                # 获取缩放比例用于坐标转换
                scale = getattr(self, 'image_scale', 1.0)
                
                for i, mark in enumerate(self.marks):
                    if isinstance(mark, dict):
                        if mark.get('type') == 'polygon':
                            # 多边形标记 - 转换坐标
                            points = mark['data']
                            if len(points) >= 3:
                                if scale >= 0.99:
                                    int_points = [(int(p[0]), int(p[1])) for p in points]
                                else:
                                    # 将缩放坐标转换回原始坐标
                                    int_points = [(int(p[0] / scale), int(p[1] / scale)) for p in points]
                                draw.polygon(int_points, outline=(255, 0, 0), width=5)
                                # 在第一个顶点附近绘制标签
                                mx, my = int_points[0]
                                draw.text((mx, my-20), f"检测区域 {i+1}", fill=(255, 0, 0), font=font)
                        elif mark.get('type') == 'rect':
                            # 矩形标记 - 转换坐标
                            x, y, w, h = mark['data']
                            if scale >= 0.99:
                                mx, my = int(x), int(y)
                                mw, mh = int(w), int(h)
                            else:
                                # 将缩放坐标转换回原始坐标
                                mx, my = int(x / scale), int(y / scale)
                                mw, mh = int(w / scale), int(h / scale)
                            draw.rectangle([mx, my, mx+mw, my+mh], outline=(255, 0, 0), width=5)
                            draw.text((mx, my-20), f"检测区域 {i+1}", fill=(255, 0, 0), font=font)
                    elif isinstance(mark, (tuple, list)) and len(mark) == 4:
                        # 旧格式：矩形 - 转换坐标
                        mx, my, mw, mh = int(mark[0]), int(mark[1]), int(mark[2]), int(mark[3])
                        if scale < 0.99:
                            mx, my = int(mx / scale), int(my / scale)
                            mw, mh = int(mw / scale), int(mh / scale)
                        draw.rectangle([mx, my, mx+mw, my+mh], outline=(255, 0, 0), width=5)
                        draw.text((mx, my-20), f"检测区域 {i+1}", fill=(255, 0, 0), font=font)
            
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            success = False
            try:
                success = cv2.imwrite(base_image_path, img)
                if not success:
                    raise Exception("cv2.imwrite 返回失败")
            except:
                print(f"尝试使用cv2.imwrite直接保存失败，尝试使用文件流方式")
                try:
                    _, buffer = cv2.imencode('.jpg', img)
                    if buffer is not None:
                        with open(base_image_path, 'wb') as f:
                            f.write(buffer)
                        success = True
                except Exception as e:
                    print(f"文件流方式也失败: {str(e)}")
            
            if success:
                self.save_marks(camera)
                print(f"基准图像保存成功: {base_image_path}")
                self.update_camera_list()
                messagebox.showinfo("成功", f"基准图像已设置!\n保存路径: {base_image_path}\n标记区域: {len(self.marks)} 个")
            else:
                print(f"基准图像保存失败")
                messagebox.showerror("失败", "无法保存基准图像")
                
        except Exception as e:
            print(f"保存基准图像时发生异常: {str(e)}")
            messagebox.showerror("失败", f"保存基准图像时发生异常: {str(e)}")
    
    def get_marks_path(self, camera):
        camera_dir = self.get_camera_dir(camera)
        return os.path.join(camera_dir, 'safe_zones.json')
    
    def save_marks(self, camera):
        marks_path = self.get_marks_path(camera)
        try:
            # 直接保存当前坐标（已经是 1000x750 统一尺寸）
            # 不再进行缩放转换，避免坐标被错误放大
            marks_to_save = []
            for mark in self.marks:
                if isinstance(mark, dict):
                    mark_copy = mark.copy()
                    if mark['type'] == 'polygon' and isinstance(mark.get('data'), list):
                        # 确保多边形坐标是整数
                        mark_copy['data'] = [
                            (int(p[0]), int(p[1])) 
                            for p in mark['data']
                        ]
                    elif mark['type'] == 'rect' and isinstance(mark.get('data'), (list, tuple)):
                        # 矩形坐标 (x, y, w, h)
                        x, y, w, h = mark['data']
                        mark_copy['data'] = (
                            int(x),
                            int(y),
                            int(w),
                            int(h)
                        )
                    marks_to_save.append(mark_copy)
                else:
                    marks_to_save.append(mark)
            
            with open(marks_path, 'w', encoding='utf-8') as f:
                json.dump(marks_to_save, f, ensure_ascii=False)
            print(f"检测区域保存成功：{marks_path}")
            print(f"保存坐标数量：{len(marks_to_save)} 个")
        except Exception as e:
            print(f"保存检测区域失败：{str(e)}")
    
    def load_marks(self, camera):
        marks_path = self.get_marks_path(camera)
        if os.path.exists(marks_path):
            try:
                with open(marks_path, 'r', encoding='utf-8') as f:
                    loaded_marks = json.load(f)
                
                # 转换旧格式为新格式
                self.marks = []
                for mark in loaded_marks:
                    if isinstance(mark, dict):
                        # 确保多边形坐标是整数
                        if mark.get('type') == 'polygon' and isinstance(mark.get('data'), list):
                            mark['data'] = [(int(p[0]), int(p[1])) for p in mark['data']]
                        elif mark.get('type') == 'rect' and isinstance(mark.get('data'), list):
                            mark['data'] = tuple(int(v) for v in mark['data'])
                        self.marks.append(mark)
                    elif isinstance(mark, (list, tuple)) and len(mark) == 4:
                        # 旧格式：矩形 [x, y, w, h]
                        self.marks.append({'type': 'rect', 'data': tuple(int(v) for v in mark)})
                    elif isinstance(mark, (list, tuple)) and len(mark) >= 3:
                        # 可能是多边形点列表
                        self.marks.append({'type': 'polygon', 'data': [(int(p[0]), int(p[1])) for p in mark]})
                
                print(f"加载检测区域成功：{len(self.marks)} 个")
            except Exception as e:
                print(f"加载检测区域失败：{str(e)}")
                self.marks = []
        else:
            self.marks = []
    
    def on_mark_mode_change(self):
        self.mark_mode = self.mark_mode_var.get()
        print(f"【标记】切换绘制模式: {self.mark_mode}")
        
    def toggle_mark_mode(self):
        if self.is_mark_mode:
            self.is_mark_mode = False
            self.mark_button.config(text="标记检测区域")
            self.clear_marks_button.config(state=tk.DISABLED)
            self.image_label.unbind('<ButtonPress-1>')
            self.image_label.unbind('<B1-Motion>')
            self.image_label.unbind('<ButtonRelease-1>')
            self.image_label.unbind('<Double-Button-1>')
            self.current_polygon = []
            self.draw_marks()
            print("【标记】退出标记模式")
        else:
            self.is_mark_mode = True
            self.mark_button.config(text="退出标记模式")
            self.clear_marks_button.config(state=tk.NORMAL if self.marks else tk.DISABLED)
            self.image_label.bind('<ButtonPress-1>', self.on_mouse_down)
            self.image_label.bind('<B1-Motion>', self.on_mouse_drag)
            self.image_label.bind('<ButtonRelease-1>', self.on_mouse_up)
            self.image_label.bind('<Double-Button-1>', self.on_double_click)
            print(f"【标记】开启标记模式，original_img 存在：{hasattr(self, 'original_img') and self.original_img is not None}")
            
            self.mark_mode = self.mark_mode_var.get()
            
            mode_desc = {
                'rect': '矩形',
                'square': '正方形',
                'polygon': '多边形（点击添加顶点，双击完成）'
            }
            messagebox.showinfo("提示", f"标记模式已开启\n当前模式：{mode_desc[self.mark_mode]}\n检测区域内的物体将被检测")
    
    def on_mouse_down(self, event):
        if not self.is_mark_mode or not hasattr(self, 'original_img') or self.original_img is None:
            print(f"【标记】鼠标按下 - 跳过: is_mark_mode={self.is_mark_mode}, original_img={hasattr(self, 'original_img') and self.original_img is not None}")
            return
        
        # 将鼠标事件坐标转换为图像坐标
        # event.x, event.y 是相对于 image_label 的坐标
        # 需要转换为相对于图像的坐标（1000x750）
        img_x, img_y = self._convert_to_image_coords(event.x, event.y)
        
        if self.mark_mode == 'polygon':
            # 多边形模式：点击添加顶点
            self.current_polygon.append((img_x, img_y))
            print(f"【标记】添加多边形顶点: ({img_x}, {img_y}), 当前顶点数: {len(self.current_polygon)}")
            self.draw_marks()
        else:
            # 矩形/正方形模式
            self.start_x = img_x
            self.start_y = img_y
            self.current_rect = (img_x, img_y, 0, 0)
            print(f"【标记】鼠标按下: ({img_x}, {img_y})")
    
    def _convert_to_image_coords(self, label_x, label_y):
        """将标签坐标转换为图像坐标（1000x750）"""
        # 获取图像在标签中的实际显示尺寸和偏移
        img_width, img_height = self.original_img.size  # 1000x750
        
        # 获取标签的实际尺寸
        label_width = self.image_label.winfo_width()
        label_height = self.image_label.winfo_height()
        
        # 计算图像在标签中的偏移（居中显示）
        offset_x = (label_width - img_width) / 2
        offset_y = (label_height - img_height) / 2
        
        # 转换为图像坐标
        img_x = int(label_x - offset_x)
        img_y = int(label_y - offset_y)
        
        # 确保坐标在图像范围内
        img_x = max(0, min(img_x, img_width))
        img_y = max(0, min(img_y, img_height))
        
        return img_x, img_y
    
    def on_mouse_drag(self, event):
        if not self.is_mark_mode:
            return
        
        if self.mark_mode == 'polygon':
            # 多边形模式不支持拖动
            return
        
        if self.current_rect is None:
            return
        
        # 将鼠标事件坐标转换为图像坐标
        img_x, img_y = self._convert_to_image_coords(event.x, event.y)
        w = img_x - self.start_x
        h = img_y - self.start_y
        
        if self.mark_mode == 'square':
            # 正方形模式：取宽高中较小的值
            min_dim = min(abs(w), abs(h))
            w = min_dim if w > 0 else -min_dim
            h = min_dim if h > 0 else -min_dim
        
        self.current_rect = (self.start_x, self.start_y, w, h)
        print(f"【标记】鼠标拖动: ({self.start_x}, {self.start_y}, {w}, {h})")
        self.draw_marks()
    
    def on_mouse_up(self, event):
        if not self.is_mark_mode:
            print(f"【标记】鼠标释放 - 跳过: is_mark_mode={self.is_mark_mode}")
            return
        
        if self.mark_mode == 'polygon':
            # 多边形模式在双击时完成
            return
        
        if self.current_rect is None:
            print(f"【标记】鼠标释放 - 跳过: current_rect={self.current_rect}")
            return
        
        x, y, w, h = self.current_rect
        print(f"【标记】鼠标释放: ({x}, {y}, {w}, {h})")
        
        if abs(w) > 10 and abs(h) > 10:
            if w < 0:
                x += w
                w = abs(w)
            if h < 0:
                y += h
                h = abs(h)
            
            # 矩形和正方形都存储为矩形格式
            self.marks.append({'type': 'rect', 'data': (x, y, w, h)})
            self.clear_marks_button.config(state=tk.NORMAL)
            print(f"添加标记区域: ({x}, {y}, {w}, {h})")
            # 自动保存
            if self.current_camera_index >= 0:
                camera = self.cameras[self.current_camera_index]
                self.save_marks(camera)
        
        self.current_rect = None
        self.draw_marks()
    
    def on_double_click(self, event):
        """双击完成多边形绘制"""
        if not self.is_mark_mode or self.mark_mode != 'polygon':
            return
        
        if len(self.current_polygon) >= 3:
            # 至少需要3个顶点才能形成多边形
            self.marks.append({'type': 'polygon', 'data': self.current_polygon})
            self.clear_marks_button.config(state=tk.NORMAL)
            print(f"【标记】完成多边形绘制，顶点数: {len(self.current_polygon)}")
            self.current_polygon = []
            self.draw_marks()
            # 自动保存
            if self.current_camera_index >= 0:
                camera = self.cameras[self.current_camera_index]
                self.save_marks(camera)
            messagebox.showinfo("提示", "多边形区域已添加并自动保存")
        elif len(self.current_polygon) > 0:
            messagebox.showwarning("警告", "多边形至少需要3个顶点，请继续添加")
    
    def draw_marks(self):
        if not hasattr(self, 'original_img') or self.original_img is None:
            return
        
        img = self.original_img.copy()
        draw = ImageDraw.Draw(img)
        
        # 检测区域用绿色框表示
        for mark in self.marks:
            if isinstance(mark, dict) and mark['type'] == 'polygon':
                # 多边形
                points = mark['data']
                if len(points) >= 3:
                    # 确保坐标是整数
                    int_points = [(int(p[0]), int(p[1])) for p in points]
                    draw.polygon(int_points, outline=(0, 255, 0), width=3)
                    # 绘制顶点
                    for i, (px, py) in enumerate(int_points):
                        draw.ellipse([px-5, py-5, px+5, py+5], fill=(0, 255, 0))
            elif isinstance(mark, dict) and mark['type'] == 'rect':
                # 矩形
                x, y, w, h = mark['data']
                x1, y1 = int(x), int(y)
                x2, y2 = int(x + w), int(y + h)
                draw.rectangle([x1, y1, x2, y2], outline=(0, 255, 0), width=3)
            elif isinstance(mark, (tuple, list)) and len(mark) == 4:
                # 旧格式：兼容之前的矩形
                x, y, w, h = mark
                x1, y1 = int(x), int(y)
                x2, y2 = int(x + w), int(y + h)
                draw.rectangle([x1, y1, x2, y2], outline=(0, 255, 0), width=3)
        
        # 绘制当前正在绘制的图形
        if self.mark_mode == 'polygon' and self.current_polygon:
            # 绘制已添加的顶点和连线
            if len(self.current_polygon) >= 2:
                draw.line(self.current_polygon, fill=(0, 255, 0), width=3)
            # 绘制顶点
            for i, (px, py) in enumerate(self.current_polygon):
                draw.ellipse([px-5, py-5, px+5, py+5], fill=(0, 255, 0))
        
        if self.current_rect and self.mark_mode != 'polygon':
            x, y, w, h = self.current_rect
            x1, y1 = min(x, x + w), min(y, y + h)
            x2, y2 = max(x, x + w), max(y, y + h)
            draw.rectangle([x1, y1, x2, y2], outline=(0, 255, 0), width=3)
        
        photo = ImageTk.PhotoImage(image=img)
        self.image_label.config(image=photo)
        self.image_label.image = photo
    
    def clear_marks(self):
        self.marks = []
        self.clear_marks_button.config(state=tk.DISABLED)
        self.draw_marks()
        
        # 清除标记后也需要保存到文件
        if self.current_camera_index >= 0:
            camera = self.cameras[self.current_camera_index]
            self.save_marks(camera)
            print("【标记】已清除所有检测区域并保存")
        
        messagebox.showinfo("提示", "已清除所有标记")

class AddCameraDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("添加摄像头")
        self.result = None
        
        frame = ttk.Frame(self, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(frame, text="位置名称:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.location_entry = ttk.Entry(frame, width=30)
        self.location_entry.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(frame, text="IP地址:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.ip_entry = ttk.Entry(frame, width=30)
        self.ip_entry.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(frame, text="端口:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.port_entry = ttk.Entry(frame, width=30)
        self.port_entry.insert(0, "80")
        self.port_entry.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(frame, text="用户名:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.username_entry = ttk.Entry(frame, width=30)
        self.username_entry.insert(0, "admin")
        self.username_entry.grid(row=3, column=1, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(frame, text="密码:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.password_entry = ttk.Entry(frame, width=30, show="*")
        self.password_entry.grid(row=4, column=1, sticky=tk.W, pady=(0, 5))
        
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="确定", command=self.ok).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="取消", command=self.cancel).grid(row=0, column=1)
        
        self.bind('<Return>', lambda e: self.ok())
    
    def ok(self):
        location = self.location_entry.get().strip()
        ip = self.ip_entry.get().strip()
        
        if not location or not ip:
            messagebox.showwarning("警告", "位置名称和IP地址不能为空")
            return
        
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            port = 80
        
        self.result = {
            'ip': ip,
            'port': port,
            'username': self.username_entry.get().strip(),
            'password': self.password_entry.get(),
            'location': location
        }
        self.destroy()
    
    def cancel(self):
        self.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = CameraManager(root)
    root.mainloop()