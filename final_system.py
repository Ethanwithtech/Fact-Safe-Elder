#!/usr/bin/env python3
"""
AI守护系统 - 最终完整版本
确保前端可以正常打开
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

class AIGuardHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            # 直接返回index.html内容
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            try:
                with open('index.html', 'r', encoding='utf-8') as f:
                    content = f.read()
                self.wfile.write(content.encode('utf-8'))
            except FileNotFoundError:
                self.send_error(404, "index.html not found")
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        return  # 禁用日志

def start_backend():
    """启动后端服务"""
    print("[INFO] 启动AI检测后端...")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "test_backend.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print(f"[OK] 后端服务启动 (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"[ERROR] 后端启动失败: {e}")
        return None

def start_frontend():
    """启动前端服务"""
    print("[INFO] 启动前端界面...")
    
    try:
        server = HTTPServer(("", 3000), AIGuardHandler)
        print("[OK] 前端服务启动: http://localhost:3000")
        
        # 在后台线程运行服务器
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        
        return server
    except Exception as e:
        print(f"[ERROR] 前端启动失败: {e}")
        return None

def check_services():
    """检查服务状态"""
    print("[INFO] 检查服务状态...")
    
    # 检查后端
    try:
        import requests
        response = requests.get("http://localhost:8008/health", timeout=5)
        if response.ok:
            print("[OK] 后端API正常")
        else:
            print("[WARN] 后端API异常")
    except:
        print("[WARN] 后端API无响应")
    
    # 检查前端
    try:
        import requests
        response = requests.get("http://localhost:3000", timeout=5)
        if response.ok:
            print("[OK] 前端页面正常")
        else:
            print("[WARN] 前端页面异常")
    except:
        print("[WARN] 前端页面无响应")

def main():
    """主函数"""
    print("""
🛡️ ========================================
   AI守护系统 - 老人短视频安全检测
   手机模拟器 + 实时AI检测 + 数据面板
======================================== 🛡️
    """)
    
    # 清理端口
    try:
        subprocess.run([sys.executable, "kill_ports.py"], capture_output=True, timeout=10)
        print("[OK] 端口清理完成")
    except:
        print("[WARN] 端口清理跳过")
    
    # 启动后端
    backend_process = start_backend()
    time.sleep(3)
    
    # 启动前端
    frontend_server = start_frontend()
    time.sleep(2)
    
    # 检查服务
    check_services()
    
    # 打开浏览器
    try:
        webbrowser.open("http://localhost:3000")
        print("[OK] 浏览器已打开")
    except:
        print("[WARN] 请手动打开: http://localhost:3000")
    
    print("""
🎉 AI守护系统启动完成！
========================================

🌐 访问地址:
   前端界面: http://localhost:3000
   后端API: http://localhost:8008
   API文档: http://localhost:8008/docs

🎯 核心功能:
   📱 手机视频模拟器 (左侧)
   🛡️ AI智能检测浮窗
   📊 实时数据统计面板 (右侧)
   🔊 危险内容声音警告

🎮 操作方式:
   ⬆️⬇️ 方向键或鼠标拖拽切换视频
   ❤️ 点击右侧按钮进行互动
   🔍 自动AI检测每个视频内容

⏹️ 停止服务: 按 Ctrl+C
========================================
    """)
    
    # 等待用户中断
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] 正在停止服务...")
        
        if backend_process:
            backend_process.terminate()
            print("[OK] 后端服务已停止")
        
        if frontend_server:
            frontend_server.shutdown()
            print("[OK] 前端服务已停止")
        
        print("[SUCCESS] AI守护系统已安全关闭")

if __name__ == "__main__":
    main()
