#!/bin/bash
uv run python worker.py &
uv run uvicorn main:app --host 0.0.0.0 --port 5000 &
