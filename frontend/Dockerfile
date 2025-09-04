# 前端 Dockerfile - 适用于开发和生产环境

# 构建阶段
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apk add --no-cache \
    python3 \
    make \
    g++

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production --silent && \
    npm cache clean --force

# 复制源代码
COPY . .

# 设置环境变量
ARG REACT_APP_API_URL=http://localhost:8000
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
ENV GENERATE_SOURCEMAP=false
ENV DISABLE_ESLINT_PLUGIN=true

# 构建应用
RUN npm run build

# 生产阶段 - 使用Nginx提供静态文件
FROM nginx:alpine AS production

# 安装系统工具
RUN apk add --no-cache curl

# 复制构建产物
COPY --from=builder /app/build /usr/share/nginx/html

# 复制Nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 创建非root用户
RUN addgroup -g 1001 -S nginx-user && \
    adduser -S nginx-user -u 1001 -G nginx-user

# 设置权限
RUN chown -R nginx-user:nginx-user /usr/share/nginx/html && \
    chown -R nginx-user:nginx-user /var/cache/nginx && \
    chown -R nginx-user:nginx-user /var/log/nginx && \
    chown -R nginx-user:nginx-user /etc/nginx/conf.d

# 切换到非root用户
USER nginx-user

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["nginx", "-g", "daemon off;"]

# 开发阶段
FROM node:18-alpine AS development

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    curl

# 复制package文件
COPY package*.json ./

# 安装所有依赖（包括开发依赖）
RUN npm ci --silent

# 复制源代码
COPY . .

# 创建非root用户
RUN addgroup -g 1001 -S node-user && \
    adduser -S node-user -u 1001 -G node-user

# 设置文件权限
RUN chown -R node-user:node-user /app

# 切换到非root用户
USER node-user

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# 开发环境启动命令
CMD ["npm", "start"]
