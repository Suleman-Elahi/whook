#!/bin/bash

cleanup() {
    echo "Stopping services..."
    kill $WORKER_PID $SERVER_PID 2>/dev/null
    wait $WORKER_PID $SERVER_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Initialize database tables
echo "Initializing database..."
uv run python init_db.py
if [ $? -ne 0 ]; then
    echo "Database initialization failed!"
    exit 1
fi

uv run python worker.py &
WORKER_PID=$!

uv run uvicorn main:app --host 0.0.0.0 --port 5000 &
SERVER_PID=$!

echo "Worker PID: $WORKER_PID, Server PID: $SERVER_PID"
echo "Press Ctrl+C to stop"

wait
