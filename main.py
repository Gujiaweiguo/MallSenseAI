import os
import json
import schedule
import time
import signal
import sys
import logging
from datetime import datetime
from alarm_system import AlarmSystem
from config import ALARM_CONFIG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_CONFIG_FILE = os.path.join(BASE_DIR, 'camera_configs.json')

def load_camera_configs():
    if os.path.exists(JSON_CONFIG_FILE):
        try:
            with open(JSON_CONFIG_FILE, 'r', encoding='utf-8') as f:
                configs = json.load(f)
            if configs:
                return configs
        except Exception as e:
            print(f"读取JSON配置文件失败: {str(e)}")
    
    from config import CAMERA_CONFIGS
    return CAMERA_CONFIGS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(ALARM_CONFIG['log_file'], encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    print("\n正在退出系统...")
    logger.info("用户手动退出系统")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def show_main_menu():
    print("\n" + "="*50)
    print("       占道报警系统 - 主菜单")
    print("="*50)
    print("1. 监控测试")
    print("2. 循环检查（每轮推送报告）")
    print("3. 基准图像手动调整")
    print("4. 退出系统")
    print("="*50)
    print("请输入操作序号:")

def start_monitoring(alarm_system):
    camera_configs = load_camera_configs()
    num_cameras = len(camera_configs)
    
    if num_cameras == 0:
        print("未配置任何摄像头，请先添加摄像头")
        return
    
    print("\n监控测试模式...")
    print(f"已配置 {num_cameras} 个摄像头:")
    for i, config in enumerate(camera_configs, 1):
        print(f"  {i}. {config['location']} ({config['ip']}:{config['port']})")
    
    print("\n请输入要测试的摄像头序号（输入0测试所有摄像头）:")
    try:
        camera_num = int(input().strip())
    except ValueError:
        print("输入无效，默认测试所有摄像头")
        camera_num = 0
    
    if camera_num == 0:
        # 测试所有摄像头
        print("\n开始依次检测所有摄像头...")
        required_checks = ALARM_CONFIG['static_wait_minutes'] + 1
        print(f"需要连续检测 {required_checks} 次确认异常")
        
        for camera_index in range(num_cameras):
            print(f"\n--- 正在检测第 {camera_index + 1}/{num_cameras} 个摄像头 ---")
            
            for check_round in range(required_checks):
                print(f"\n--- 第 {check_round + 1}/{required_checks} 次检测 ---")
                alarm_system.check_alarm(camera_index)
                
                if check_round < required_checks - 1:
                    print(f"\n等待 {ALARM_CONFIG['interval_minutes']} 分钟后进行第 {check_round + 2} 次检测...")
                    time.sleep(ALARM_CONFIG['interval_minutes'] * 60)
        
        print(f"\n=== 所有 {num_cameras} 个摄像头检测完成 ===")
    elif 1 <= camera_num <= num_cameras:
        # 测试单个摄像头
        camera_index = camera_num - 1
        config = camera_configs[camera_index]
        print(f"\n--- 正在检测摄像头 {camera_num}: {config['location']} ---")
        required_checks = ALARM_CONFIG['static_wait_minutes'] + 1
        print(f"需要连续检测 {required_checks} 次确认异常")
        
        for check_round in range(required_checks):
            print(f"\n--- 第 {check_round + 1}/{required_checks} 次检测 ---")
            alarm_system.check_alarm(camera_index)
            
            if check_round < required_checks - 1:
                print(f"\n等待 {ALARM_CONFIG['interval_minutes']} 分钟后进行第 {check_round + 2} 次检测...")
                time.sleep(ALARM_CONFIG['interval_minutes'] * 60)
        
        print(f"\n=== 摄像头 {camera_num} 检测完成 ===")
    else:
        print(f"无效的摄像头序号，请输入1-{num_cameras}之间的数字")
    
    print("返回主菜单...")

def start_loop_check(alarm_system):
    camera_configs = load_camera_configs()
    num_cameras = len(camera_configs)
    
    if num_cameras == 0:
        print("未配置任何摄像头，请先添加摄像头")
        return
    
    print("\n循环检查模式启动...")
    print(f"定时检测间隔: {ALARM_CONFIG['interval_minutes']}分钟")
    print(f"静止等待时间: {ALARM_CONFIG['static_wait_minutes']}分钟")
    print(f"差异阈值: {ALARM_CONFIG['threshold']}")
    print(f"\n已配置 {num_cameras} 个摄像头:")
    for i, config in enumerate(camera_configs, 1):
        print(f"  {i}. {config['location']} ({config['ip']}:{config['port']})")
    
    loop_count = 0
    try:
        while True:
            loop_count += 1
            start_time = time.time()
            loop_alarm_count = 0
            
            print(f"\n{'='*60}")
            print(f"          第 {loop_count} 轮检查开始")
            print(f"{'='*60}")
            
            for camera_index in range(num_cameras):
                print(f"\n--- 正在检测第 {camera_index + 1}/{num_cameras} 个摄像头 ---")
                
                required_checks = ALARM_CONFIG['static_wait_minutes'] + 1
                camera_alarm = False
                
                for check_round in range(required_checks):
                    alarm_before = alarm_system.alarm_count
                    alarm_system.check_alarm(camera_index)
                    alarm_after = alarm_system.alarm_count
                    
                    if alarm_after > alarm_before:
                        camera_alarm = True
                        loop_alarm_count += 1
                    
                    if check_round < required_checks - 1:
                        time.sleep(ALARM_CONFIG['interval_minutes'] * 60)
            
            loop_elapsed = time.time() - start_time
            
            print(f"\n{'='*60}")
            print(f"          第 {loop_count} 轮检查完成")
            print(f"{'='*60}")
            print(f"本轮检测耗时: {loop_elapsed:.2f}秒")
            print(f"本轮报警次数: {loop_alarm_count}次")
            print(f"累计检测轮数: {loop_count}轮")
            print(f"累计报警次数: {alarm_system.alarm_count}次")
            print(f"{'='*60}")
            
            report_content = f"""【占道报警系统 - 检查报告】
📅 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 检查轮次: 第 {loop_count} 轮
⏱️ 本轮耗时: {loop_elapsed:.2f}秒
📡 监控摄像头: {num_cameras} 个
🚨 本轮报警: {loop_alarm_count} 次
📊 累计报警: {alarm_system.alarm_count} 次
"""

            print("\n检查报告:")
            print(report_content)
            
            print(f"\n等待 {ALARM_CONFIG['interval_minutes']} 分钟后开始下一轮检查...")
            time.sleep(ALARM_CONFIG['interval_minutes'] * 60)
            
    except KeyboardInterrupt:
        print("\n用户手动退出循环检查模式")
        logger.info("用户手动退出循环检查模式")

def main():
    alarm_system = AlarmSystem()
    
    while True:
        show_main_menu()
        try:
            choice = int(input().strip())
        except ValueError:
            print("输入无效，请输入数字")
            continue
        
        if choice == 1:
            start_monitoring(alarm_system)
        elif choice == 2:
            start_loop_check(alarm_system)
        elif choice == 3:
            alarm_system.adjust_base_image_interactive()
        elif choice == 4:
            print("退出系统...")
            sys.exit(0)
        else:
            print("无效的选择，请重新输入")

if __name__ == '__main__':
    main()