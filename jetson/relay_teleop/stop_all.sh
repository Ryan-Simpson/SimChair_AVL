#!/bin/bash
# stop_all.sh — stop everything start_all.sh started (only the "simchair" session)
tmux kill-session -t simchair 2>/dev/null && echo "stopped simchair session" || echo "no simchair session"
