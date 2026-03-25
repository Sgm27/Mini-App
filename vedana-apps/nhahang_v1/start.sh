#!/bin/bash

# start.sh - Khởi động Backend + Frontend cho nhà hàng v1

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

BACKEND_PORT=2701
FRONTEND_PORT=8386

cleanup() {
    echo ""
    echo "Đang tắt các service..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Đã tắt tất cả."
    exit 0
}

trap cleanup SIGINT SIGTERM

# --- Backend ---
echo "=== Khởi động Backend (FastAPI) ==="
cd "$PROJECT_DIR/backend"
uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!

echo "Backend:  http://localhost:$BACKEND_PORT"
echo "API Docs: http://localhost:$BACKEND_PORT/docs"

# --- Frontend ---
echo ""
echo "=== Khởi động Frontend ==="
cd "$PROJECT_DIR/frontend"
python3 -m http.server $FRONTEND_PORT &
FRONTEND_PID=$!

echo "Frontend: http://localhost:$FRONTEND_PORT"

echo ""
echo "=== Tất cả service đã khởi động ==="
echo "Nhấn Ctrl+C để tắt."
echo ""

wait
