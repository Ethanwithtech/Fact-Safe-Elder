#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
酮伴妈妈问卷 - 局域网访问服务器
启动后可在同一网络的其他设备访问问卷页面
"""

import os
import sys
import socket
import http.server
import socketserver
from pathlib import Path

# 配置
PORT = 8080
HTML_FILE = "keto-mom-interactive-quiz.html"

def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        # 创建一个UDP socket来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def check_file_exists():
    """检查HTML文件是否存在"""
    if not os.path.exists(HTML_FILE):
        print(f"❌ 错误: 找不到 {HTML_FILE}")
        print(f"当前目录: {os.getcwd()}")
        return False
    return True

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """自定义HTTP处理器，减少日志输出"""
    
    def log_message(self, format, *args):
        """只记录重要的请求"""
        if self.command == "GET" and HTML_FILE in self.path:
            print(f"📱 访问来自: {self.client_address[0]} - {self.path}")
    
    def end_headers(self):
        """添加CORS头，允许跨域"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def main():
    print("\n" + "="*60)
    print("🏡 酮伴妈妈问卷 - 局域网服务器")
    print("="*60 + "\n")
    
    # 切换到脚本所在目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # 检查文件
    if not check_file_exists():
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    # 获取本机IP
    local_ip = get_local_ip()
    
    # 创建服务器
    Handler = QuietHandler
    
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
            print(f"✅ 服务器已启动！")
            print(f"📍 本机访问: http://localhost:{PORT}/{HTML_FILE}")
            print(f"🌐 局域网访问: http://{local_ip}:{PORT}/{HTML_FILE}")
            print("\n" + "-"*60)
            print("📱 同一 Wi-Fi/局域网的其他设备可以访问上面的局域网地址")
            print("-"*60)
            print("\n💡 提示:")
            print(f"   - 确保所有设备连接同一网络")
            print(f"   - 如果无法访问，请检查防火墙设置")
            print(f"   - 按 Ctrl + C 停止服务器")
            print("\n" + "="*60 + "\n")
            
            httpd.serve_forever()
            
    except PermissionError:
        print(f"❌ 错误: 端口 {PORT} 需要管理员权限")
        print(f"💡 解决方案: 以管理员身份运行，或更换端口（如 8090）")
        input("\n按 Enter 键退出...")
        sys.exit(1)
        
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ 错误: 端口 {PORT} 已被占用")
            print(f"💡 解决方案:")
            print(f"   1. 关闭占用端口的程序")
            print(f"   2. 或修改脚本中的 PORT 变量（如改为 8090）")
        else:
            print(f"❌ 错误: {e}")
        input("\n按 Enter 键退出...")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  服务器已停止")
        print("感谢使用！")
        sys.exit(0)

if __name__ == "__main__":
    main()

