#!/bin/bash

# Temu/Amazon 数据管理平台启动脚本
# 同时启动前端和后端服务

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "正在停止服务..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "  ✓ 后端已停止 (PID: $BACKEND_PID)"
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "  ✓ 前端已停止 (PID: $FRONTEND_PID)"
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "=============================================="
echo "  Temu/Amazon 数据管理平台"
echo "=============================================="
echo ""

# 检查依赖
echo "[1/3] 检查依赖..."
if ! command -v python &> /dev/null; then
    echo "  ✗ 未找到 python"
    exit 1
fi
if ! command -v npm &> /dev/null; then
    echo "  ✗ 未找到 npm"
    exit 1
fi
echo "  ✓ 依赖检查通过"

# 启动后端
echo ""
echo "[2/3] 启动后端服务..."
cd "$PROJECT_DIR"
source py3env/bin/activate 2>/dev/null || true
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "  ✓ 后端已启动 (PID: $BACKEND_PID)"
echo "        地址: http://localhost:8000"
echo "        API文档: http://localhost:8000/docs"

# 等待后端启动
sleep 2

# 启动前端
echo ""
echo "[3/3] 启动前端服务..."
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "  ✓ 前端已启动 (PID: $FRONTEND_PID)"
echo "        地址: http://localhost:5173"

echo ""
echo "=============================================="
echo "  所有服务已启动！"
echo ""
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:8000"
echo "  API:  http://localhost:8000/docs"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "=============================================="
echo ""

# 等待用户中断
wait
