#!/bin/bash

# 老人短视频虚假信息检测系统 - 启动脚本
# 使用方法: ./start.sh [dev|prod|test|stop|clean]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}  $1${NC}"
    echo -e "${PURPLE}========================================${NC}"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        log_info "安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        log_info "安装指南: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    log_info "Docker 和 Docker Compose 已安装 ✓"
}

# 检查端口是否被占用
check_ports() {
    local ports=(3000 8000 5432 6379)
    local occupied_ports=()
    
    for port in "${ports[@]}"; do
        if lsof -i :$port &> /dev/null; then
            occupied_ports+=($port)
        fi
    done
    
    if [ ${#occupied_ports[@]} -ne 0 ]; then
        log_warn "以下端口被占用: ${occupied_ports[*]}"
        log_warn "请确保这些端口可用或修改配置文件中的端口设置"
        read -p "是否继续启动? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "启动已取消"
            exit 0
        fi
    fi
}

# 创建必要的目录和文件
setup_directories() {
    log_info "创建必要的目录和文件..."
    
    # 创建目录
    mkdir -p backend/logs
    mkdir -p backend/data
    mkdir -p backend/models
    mkdir -p backend/uploads
    mkdir -p monitoring/prometheus
    mkdir -p monitoring/grafana/dashboards
    mkdir -p monitoring/grafana/datasources
    mkdir -p nginx/ssl
    
    # 创建环境配置文件（如果不存在）
    if [ ! -f .env ]; then
        log_info "创建默认环境配置文件 .env"
        cat > .env << EOF
# 基础配置
DEBUG=true
HOST=0.0.0.0
PORT=8000

# 数据库配置
DATABASE_URL=postgresql://elder_user:elder_password@postgres:5432/elder_safety
REDIS_URL=redis://redis:6379/0

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# 前端配置
REACT_APP_API_URL=http://localhost:8000
EOF
        log_info ".env 文件已创建，请根据需要修改配置"
    fi
    
    log_info "目录和文件设置完成 ✓"
}

# 开发环境启动
start_dev() {
    log_header "启动开发环境"
    
    log_info "构建并启动开发环境容器..."
    docker-compose -f docker-compose.yml up --build -d frontend backend postgres redis
    
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    check_service_health
    
    log_info "开发环境启动完成! 🎉"
    log_info "前端地址: http://localhost:3000"
    log_info "后端API: http://localhost:8000"
    log_info "API文档: http://localhost:8000/docs"
    log_info "数据库: localhost:5432 (用户名: elder_user)"
    log_info "Redis: localhost:6379"
    
    log_info "查看日志: docker-compose logs -f"
    log_info "停止服务: ./start.sh stop"
}

# 生产环境启动
start_prod() {
    log_header "启动生产环境"
    
    log_warn "确保已正确配置生产环境变量!"
    read -p "是否继续启动生产环境? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "启动已取消"
        exit 0
    fi
    
    # 修改环境变量为生产配置
    export DEBUG=false
    export NODE_ENV=production
    
    log_info "构建并启动生产环境容器..."
    docker-compose -f docker-compose.yml --profile production up --build -d
    
    log_info "等待服务启动..."
    sleep 15
    
    check_service_health
    
    log_info "生产环境启动完成! 🚀"
    log_info "应用地址: http://localhost"
    log_info "HTTPS地址: https://localhost (如果配置了SSL)"
    log_info "API地址: http://localhost/api"
    log_info "监控面板: http://localhost:9090 (Prometheus)"
    log_info "图形界面: http://localhost:3001 (Grafana)"
}

# 测试环境启动
start_test() {
    log_header "启动测试环境"
    
    log_info "构建测试环境容器..."
    docker-compose -f docker-compose.yml -f docker-compose.test.yml up --build -d
    
    log_info "运行测试套件..."
    docker-compose exec backend python -m pytest tests/ -v
    docker-compose exec frontend npm test -- --coverage --watchAll=false
    
    log_info "测试完成"
}

# 检查服务健康状态
check_service_health() {
    local services=("frontend:3000/health" "backend:8000/api/health")
    local max_attempts=30
    local attempt=1
    
    for service in "${services[@]}"; do
        local service_name=$(echo $service | cut -d':' -f1)
        local endpoint="http://localhost:$(echo $service | cut -d':' -f2-)"
        
        log_info "检查 $service_name 服务状态..."
        
        while [ $attempt -le $max_attempts ]; do
            if curl -f "$endpoint" &> /dev/null; then
                log_info "$service_name 服务正常 ✓"
                break
            fi
            
            if [ $attempt -eq $max_attempts ]; then
                log_error "$service_name 服务启动失败"
                log_info "请检查日志: docker-compose logs $service_name"
                return 1
            fi
            
            sleep 2
            ((attempt++))
        done
        
        attempt=1
    done
}

# 停止所有服务
stop_services() {
    log_header "停止所有服务"
    
    log_info "停止并移除容器..."
    docker-compose down
    
    log_info "移除孤立容器..."
    docker-compose down --remove-orphans
    
    log_info "所有服务已停止 ✓"
}

# 清理系统
clean_system() {
    log_header "清理系统"
    
    log_warn "这将删除所有容器、镜像和数据卷!"
    read -p "确定要继续吗? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "清理已取消"
        exit 0
    fi
    
    log_info "停止所有容器..."
    docker-compose down --remove-orphans
    
    log_info "删除相关镜像..."
    docker images | grep "fact-safe-elder" | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
    
    log_info "删除数据卷..."
    docker-compose down -v
    
    log_info "删除未使用的资源..."
    docker system prune -f
    
    log_info "系统清理完成 ✓"
}

# 显示帮助信息
show_help() {
    log_header "老人短视频虚假信息检测系统 - 启动脚本"
    
    echo -e "${CYAN}使用方法:${NC}"
    echo "  ./start.sh [命令]"
    echo
    echo -e "${CYAN}可用命令:${NC}"
    echo "  dev     - 启动开发环境 (默认)"
    echo "  prod    - 启动生产环境"
    echo "  test    - 运行测试套件"
    echo "  stop    - 停止所有服务"
    echo "  clean   - 清理系统资源"
    echo "  help    - 显示此帮助信息"
    echo
    echo -e "${CYAN}示例:${NC}"
    echo "  ./start.sh dev    # 启动开发环境"
    echo "  ./start.sh prod   # 启动生产环境"
    echo "  ./start.sh stop   # 停止所有服务"
    echo "  ./start.sh clean  # 清理系统"
    echo
    echo -e "${CYAN}服务地址:${NC}"
    echo "  前端应用: http://localhost:3000"
    echo "  后端API:  http://localhost:8000"
    echo "  API文档:  http://localhost:8000/docs"
    echo "  数据库:   localhost:5432"
    echo "  缓存:     localhost:6379"
}

# 主函数
main() {
    local command=${1:-dev}
    
    case $command in
        "dev"|"development")
            check_docker
            check_ports
            setup_directories
            start_dev
            ;;
        "prod"|"production")
            check_docker
            check_ports
            setup_directories
            start_prod
            ;;
        "test"|"testing")
            check_docker
            setup_directories
            start_test
            ;;
        "stop")
            stop_services
            ;;
        "clean")
            clean_system
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
