#!/bin/bash
# Wrapper: run loker scraper with clean env (avoid Hermes PYTHONPATH leak)
cd "$(dirname "$0")"
exec env -u PYTHONPATH .venv/bin/python3 main.py "$@"