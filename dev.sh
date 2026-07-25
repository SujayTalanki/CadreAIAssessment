#!/usr/bin/env bash
# Start (or stop) the backend + frontend dev servers together.
# Usage: ./dev.sh          start both
#        ./dev.sh stop     stop both
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_LOG=/tmp/cadre-backend.log
FRONTEND_LOG=/tmp/cadre-frontend.log

stop_servers() {
  echo "Stopping anything on :$BACKEND_PORT and :$FRONTEND_PORT..."
  lsof -ti:$BACKEND_PORT -sTCP:LISTEN | xargs -r kill -9 || true
  lsof -ti:$FRONTEND_PORT -sTCP:LISTEN | xargs -r kill -9 || true
  echo "Stopped."
}

if [[ "${1:-}" == "stop" ]]; then
  stop_servers
  exit 0
fi

if [[ ! -d "$ROOT_DIR/backend/.venv" ]]; then
  echo "backend/.venv not found - run the backend setup steps in CLAUDE.md first."
  exit 1
fi

stop_servers

echo "Starting backend..."
cd "$ROOT_DIR/backend"
source .venv/bin/activate
nohup uvicorn app.main:app --port "$BACKEND_PORT" --reload > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo "Waiting for backend health check..."
timeout 20 bash -c "until curl -sf http://localhost:$BACKEND_PORT/api/health >/dev/null; do sleep 1; done" \
  || { echo "Backend didn't come up - check $BACKEND_LOG"; exit 1; }

echo "Starting frontend..."
cd "$ROOT_DIR/frontend"
nohup npm run dev -- --port "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:$BACKEND_PORT  (pid $BACKEND_PID, log: $BACKEND_LOG)"
echo "Frontend: http://localhost:$FRONTEND_PORT (pid $FRONTEND_PID, log: $FRONTEND_LOG)"
echo ""
echo "Tail logs:  tail -f $BACKEND_LOG $FRONTEND_LOG"
echo "Stop both:  ./dev.sh stop"
