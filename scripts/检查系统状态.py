#!/usr/bin/env python3
"""
系统状态检查脚本
"""
import requests
import time

def check_status():
    print("="*60)
    print("🔍 AI守护系统状态检查")
    print("="*60)
    print()
    
    # 检查后端
    print("[1/2] 检查后端服务 (http://localhost:8008)...")
    try:
        response = requests.get("http://localhost:8008/health", timeout=5)
        if response.ok:
            data = response.json()
            print("  ✅ 后端服务: 正常运行")
            print(f"  📊 状态: {data.get('status', 'unknown')}")
            print(f"  🤖 AI模型已加载: {data.get('models_loaded', 0)}")
            print(f"  🎯 准确率: {data.get('accuracy', 0)*100:.2f}%")
            print(f"  📈 训练数据: {data.get('training_data', 0)} 条")
            backend_ok = True
        else:
            print(f"  ❌ 后端服务异常: HTTP {response.status_code}")
            backend_ok = False
    except Exception as e:
        print(f"  ❌ 后端服务未运行: {str(e)[:50]}")
        backend_ok = False
    
    print()
    
    # 检查前端
    print("[2/2] 检查前端服务 (http://localhost:3000)...")
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.ok:
            print("  ✅ 前端服务: 正常运行")
            print(f"  📄 HTTP状态: {response.status_code}")
            frontend_ok = True
        else:
            print(f"  ❌ 前端服务异常: HTTP {response.status_code}")
            frontend_ok = False
    except Exception as e:
        print(f"  ❌ 前端服务未运行: {str(e)[:50]}")
        frontend_ok = False
    
    print()
    print("="*60)
    
    if backend_ok and frontend_ok:
        print("✅ 系统状态: 所有服务正常运行！")
        print()
        print("🌐 访问地址:")
        print("   - 主界面: http://localhost:3000/premium_frontend.html")
        print("   - 后端API: http://localhost:8008")
        print("   - API文档: http://localhost:8008/docs")
    elif backend_ok:
        print("⚠️  系统状态: 后端正常，前端需要启动")
        print()
        print("启动前端命令: python -m http.server 3000")
    elif frontend_ok:
        print("⚠️  系统状态: 前端正常，后端需要启动")
        print()
        print("启动后端命令: python working_backend.py")
    else:
        print("❌ 系统状态: 所有服务都未运行")
        print()
        print("启动系统命令: python start_production.py")
    
    print("="*60)
    return backend_ok and frontend_ok

if __name__ == "__main__":
    check_status()

