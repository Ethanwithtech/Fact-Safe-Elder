#!/usr/bin/env python3
"""
AI守护系统 - 增强版启动脚本
支持视频检测、AI模型训练、多模态分析
"""

import os
import sys
import time
import subprocess
import webbrowser
import threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

class EnhancedGuardHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            # 返回增强版前端
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            try:
                with open('enhanced_frontend.html', 'r', encoding='utf-8') as f:
                    content = f.read()
                self.wfile.write(content.encode('utf-8'))
            except FileNotFoundError:
                self.send_error(404, "enhanced_frontend.html not found")
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        return  # 禁用日志

def install_dependencies():
    """安装必要的依赖包"""
    print("[INFO] 检查并安装依赖包...")
    
    required_packages = [
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "torch",
        "transformers",
        "scikit-learn",
        "datasets",
        "opencv-python",
        "numpy",
        "loguru"
    ]
    
    for package in required_packages:
        try:
            print(f"[INFO] 安装 {package}...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", package, "--quiet"
            ], check=True)
        except subprocess.CalledProcessError:
            print(f"[WARN] {package} 安装失败，跳过")
    
    print("[OK] 依赖包检查完成")

def start_enhanced_backend():
    """启动增强版后端服务"""
    print("[INFO] 启动AI检测后端（增强版）...")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "enhanced_backend.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print(f"[OK] 增强版后端服务启动 (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"[ERROR] 增强版后端启动失败: {e}")
        return None

def start_enhanced_frontend():
    """启动增强版前端服务"""
    print("[INFO] 启动增强版前端界面...")
    
    try:
        server = HTTPServer(("", 3000), EnhancedGuardHandler)
        print("[OK] 增强版前端服务启动: http://localhost:3000")
        
        # 在后台线程运行服务器
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        
        return server
    except Exception as e:
        print(f"[ERROR] 增强版前端启动失败: {e}")
        return None

def check_enhanced_services():
    """检查增强版服务状态"""
    print("[INFO] 检查增强版服务状态...")
    
    # 检查后端
    try:
        import requests
        response = requests.get("http://localhost:8008/health", timeout=10)
        if response.ok:
            data = response.json()
            print(f"[OK] 增强版后端API正常 (训练数据: {data.get('training_data', 0)}条)")
        else:
            print("[WARN] 增强版后端API异常")
    except:
        print("[WARN] 增强版后端API无响应")
    
    # 检查前端
    try:
        import requests
        response = requests.get("http://localhost:3000", timeout=5)
        if response.ok:
            print("[OK] 增强版前端页面正常")
        else:
            print("[WARN] 增强版前端页面异常")
    except:
        print("[WARN] 增强版前端页面无响应")

def create_sample_data():
    """创建示例数据"""
    print("[INFO] 创建示例数据...")
    
    # 创建必要目录
    os.makedirs("data/uploads", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("models/trained", exist_ok=True)
    os.makedirs("logs/training", exist_ok=True)
    
    print("[OK] 示例数据创建完成")

def main():
    """主函数"""
    print("""
🛡️ ==========================================
   AI守护系统 2.0 - 增强版
   视频检测 + AI训练 + 多模态分析
========================================== 🛡️
    """)
    
    # 创建示例数据
    create_sample_data()
    
    # 清理端口
    try:
        subprocess.run([sys.executable, "kill_ports.py"], capture_output=True, timeout=10)
        print("[OK] 端口清理完成")
    except:
        print("[WARN] 端口清理跳过")
    
    # 检查依赖
    print("[INFO] 检查Python依赖...")
    try:
        import fastapi, uvicorn
        print("[OK] FastAPI依赖可用")
    except ImportError:
        print("[WARN] FastAPI未安装，正在安装...")
        install_dependencies()
    
    # 启动增强版后端
    backend_process = start_enhanced_backend()
    time.sleep(5)  # 等待后端启动
    
    # 启动增强版前端
    frontend_server = start_enhanced_frontend()
    time.sleep(2)
    
    # 检查服务
    check_enhanced_services()
    
    # 打开浏览器
    try:
        webbrowser.open("http://localhost:3000")
        print("[OK] 浏览器已打开")
    except:
        print("[WARN] 请手动打开: http://localhost:3000")
    
    print("""
🎉 AI守护系统 2.0 启动完成！
==========================================

🌐 访问地址:
   增强版界面: http://localhost:3000
   后端API: http://localhost:8008
   API文档: http://localhost:8008/docs
   统计数据: http://localhost:8008/stats
   模型状态: http://localhost:8008/models/status

🚀 新增功能:
   📹 视频上传检测 - 支持MP4/AVI/MOV格式
   🎓 AI模型训练 - BERT/ChatGLM/LLaMA微调
   📊 多模态分析 - 文本+视觉+音频综合检测
   📈 实时统计 - 检测准确率和性能指标
   🔧 模型管理 - 训练进度监控和模型部署

🎯 核心特性:
   📱 手机视频模拟器 (左侧)
   🛡️ AI智能检测浮窗 (实时预警)
   📊 增强数据统计面板 (右侧)
   🔊 危险内容声音警告
   📹 拖拽上传视频检测
   🎓 在线AI模型训练

🎮 操作方式:
   ⬆️⬇️ 方向键或鼠标拖拽切换视频
   📹 拖拽视频文件到上传区域
   🎓 配置参数后点击"开始训练"
   🔍 自动AI检测每个视频内容

⏹️ 停止服务: 按 Ctrl+C
==========================================
    """)
    
    # 等待用户中断
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] 正在停止增强版服务...")
        
        if backend_process:
            backend_process.terminate()
            print("[OK] 增强版后端服务已停止")
        
        if frontend_server:
            frontend_server.shutdown()
            print("[OK] 增强版前端服务已停止")
        
        print("[SUCCESS] AI守护系统 2.0 已安全关闭")

if __name__ == "__main__":
    main()
