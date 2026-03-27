#!/bin/bash

# Start both frontend and backend for khobep_v1
# Usage: ./start.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
    echo "Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# Start backend (FastAPI on port 2701)
echo "Starting backend on http://localhost:2701 ..."
cd "$SCRIPT_DIR/backend"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 2701 --reload &
BACKEND_PID=$!

# Start frontend (simple HTTP server on port 8386)
echo "Starting frontend on http://localhost:8386 ..."
cd "$SCRIPT_DIR/frontend"
python3 -m http.server 8386 &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:2701"
echo "Frontend: http://localhost:8386"
echo "API docs: http://localhost:2701/docs"
echo ""
echo "Press Ctrl+C to stop all services."

wait
