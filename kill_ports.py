#!/usr/bin/env python3
"""
端口清理脚本 - 清理占用的端口
"""

import subprocess
import sys
import platform

def kill_port_processes(port):
    """杀死占用指定端口的进程"""
    is_windows = platform.system() == "Windows"
    
    try:
        if is_windows:
            # Windows系统
            # 查找占用端口的进程
            result = subprocess.run(
                ["netstat", "-ano"], 
                capture_output=True, 
                text=True, 
                encoding='gbk'
            )
            
            lines = result.stdout.split('\n')
            pids = []
            
            for line in lines:
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        if pid.isdigit():
                            pids.append(pid)
            
            # 杀死进程
            for pid in pids:
                try:
                    subprocess.run(["taskkill", "/F", "/PID", pid], 
                                 capture_output=True, check=True)
                    print(f"[OK] 已杀死进程 PID: {pid}")
                except subprocess.CalledProcessError:
                    print(f"[WARN] 无法杀死进程 PID: {pid}")
                    
        else:
            # Linux/Mac系统
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], 
                capture_output=True, 
                text=True
            )
            
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        subprocess.run(["kill", "-9", pid], check=True)
                        print(f"[OK] 已杀死进程 PID: {pid}")
                    except subprocess.CalledProcessError:
                        print(f"[WARN] 无法杀死进程 PID: {pid}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 清理端口失败: {e}")
        return False

def main():
    """主函数"""
    print("[INFO] 开始清理端口...")
    
    # 清理常用端口
    ports = [8000, 3000, 8001]
    
    for port in ports:
        print(f"[INFO] 清理端口 {port}...")
        kill_port_processes(port)
    
    print("[OK] 端口清理完成")

if __name__ == "__main__":
    main()
