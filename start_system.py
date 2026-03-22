#!/usr/bin/env python3
"""
AI虚假信息检测系统 - 启动脚本

功能:
1. 启动后端API服务
2. 启动前端静态文件服务
3. 自动打开浏览器

使用方法:
    python start_system.py

训练模型:
    1. 上传 Colab_Training.py 到 Google Colab
    2. 使用GPU运行训练代码
    3. 下载 fraud_detector_final.pth 到 models/ 目录
    4. 重启系统以使用新模型
"""

import os
import sys
import time
import signal
import subprocess
import threading
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

# 项目路径
PROJECT_ROOT = Path(__file__).parent

# 配置
BACKEND_PORT = 8008
FRONTEND_PORT = 3000


def kill_port(port):
    """清理端口占用"""
    if sys.platform == 'win32':
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        if pid.isdigit():
                            subprocess.run(f'taskkill /F /PID {pid}', 
                                         shell=True, capture_output=True)
        except:
            pass
    else:
        try:
            subprocess.run(f'lsof -ti:{port} | xargs kill -9', 
                          shell=True, capture_output=True)
        except:
            pass


def start_backend():
    """启动后端服务"""
    print("[INFO] 正在启动后端服务...")
    
    backend_script = PROJECT_ROOT / "enhanced_backend.py"
    if not backend_script.exists():
        print("[ERROR] enhanced_backend.py 不存在！")
        return None
    
    process = subprocess.Popen(
        [sys.executable, str(backend_script)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # 等待启动
    time.sleep(3)
    
    if process.poll() is None:
        print(f"[OK] 后端服务已启动 - http://localhost:{BACKEND_PORT}")
        return process
    else:
        print("[ERROR] 后端服务启动失败")
        return None


def start_frontend():
    """启动前端服务"""
    print("[INFO] 正在启动前端服务...")
    
    class CORSRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)
        
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            super().end_headers()
        
        def log_message(self, format, *args):
            pass  # 禁用日志
    
    server = HTTPServer(('0.0.0.0', FRONTEND_PORT), CORSRequestHandler)
    
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    
    print(f"[OK] 前端服务已启动 - http://localhost:{FRONTEND_PORT}")
    return server


def main():
    """主函数"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║     🛡️  AI虚假信息检测系统 v2.0                                    ║
║                                                                    ║
║     基于BERT+Attention的中文诈骗/谣言检测                           ║
║                                                                    ║
║     参考文献:                                                       ║
║     • Zhang et al. "AnswerFact" (EMNLP 2020)                       ║
║     • Ma et al. "Attention-based Rumor Detection" (TIST 2020)      ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
    """)
    
    # 清理端口
    print("[INFO] 清理端口...")
    kill_port(BACKEND_PORT)
    kill_port(FRONTEND_PORT)
    time.sleep(1)
    
    # 启动服务
    backend_process = start_backend()
    frontend_server = start_frontend()
    
    if not backend_process:
        print("[ERROR] 系统启动失败！")
        return
    
    # 等待服务就绪
    time.sleep(2)
    
    # 打开浏览器
    url = f"http://localhost:{FRONTEND_PORT}/index.html"
    print(f"\n[OK] 系统已启动！")
    print(f"\n    🌐 前端页面: http://localhost:{FRONTEND_PORT}")
    print(f"    🔧 后端API:  http://localhost:{BACKEND_PORT}")
    print(f"    📚 API文档:  http://localhost:{BACKEND_PORT}/docs")
    print(f"\n[INFO] 正在打开浏览器...")
    
    try:
        webbrowser.open(url)
    except:
        print("[WARN] 无法自动打开浏览器，请手动访问上述地址")
    
    print("\n" + "="*60)
    print("按 Ctrl+C 停止服务")
    print("="*60 + "\n")
    
    # 等待中断
    try:
        while True:
            time.sleep(1)
            if backend_process.poll() is not None:
                print("[WARN] 后端服务已停止")
                break
    except KeyboardInterrupt:
        print("\n[INFO] 正在停止服务...")
    
    # 清理
    if backend_process:
        backend_process.terminate()
    if frontend_server:
        frontend_server.shutdown()
    
    print("[OK] 服务已停止")


if __name__ == "__main__":
    main()









