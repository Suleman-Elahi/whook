#!/bin/bash
./home/ilfs/Public/whook/.venv/bin/python/gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
