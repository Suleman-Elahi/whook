#!/bin/bash
uv run python worker.py &
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app &
