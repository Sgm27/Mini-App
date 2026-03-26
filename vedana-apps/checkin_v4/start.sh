#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"

BACKEND_PORT=2701
FRONTEND_PORT=8386

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Done."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting backend on port $BACKEND_PORT..."
cd "$BACKEND_DIR"
uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on port $FRONTEND_PORT..."
cd "$FRONTEND_DIR"
python3 -m http.server $FRONTEND_PORT &
FRONTEND_PID=$!

echo ""
echo "========================================="
echo "  Backend:  http://localhost:$BACKEND_PORT"
echo "  API Docs: http://localhost:$BACKEND_PORT/docs"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "========================================="
echo "Press Ctrl+C to stop"
echo ""

wait
