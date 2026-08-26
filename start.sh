#!/bin/bash
# Agent-Worlds (夸父 AI_OS) 启动脚本
# 由 systemd (agent-worlds.service) 调用，或手动 bash start.sh
cd "$(dirname "$0")"
exec ./venv/bin/python main.py
