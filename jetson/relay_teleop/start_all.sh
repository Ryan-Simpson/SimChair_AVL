#!/bin/bash
# start_all.sh — bring up drive + 3-camera video in tmux session "simchair"
#
# Usage:  bash start_all.sh            # drive + video
#         VIDEO_ONLY=1 bash start_all.sh
# Stop:   bash stop_all.sh   (or: tmux kill-session -t simchair)
# Watch:  tmux attach -t simchair
#
# Bitrates: 1.2 Mbps total is what held up on cellular indoors (2026-10-10);
# 1.8 Mbps collapsed. Override per camera with FRONT_BPS / SIDE_BPS.
# These are the scale-1.0 rates: run_rate_controller.sh scales all three
# live (0.25x-1.5x) from ping delay to the sim chair. FIXED_BITRATE=1 skips it.
# Encoders start 4 s apart: starting all three at once caused a ~20 s
# lag spike (simultaneous keyframe bursts).
D="$(cd "$(dirname "$0")" && pwd)"
FRONT_BPS="${FRONT_BPS:-500000}"
SIDE_BPS="${SIDE_BPS:-350000}"

if tmux has-session -t simchair 2>/dev/null; then
    echo "tmux session 'simchair' already exists — run stop_all.sh first"; exit 1
fi

tmux new-session -d -s simchair -n mediamtx "$D/run_mediamtx.sh"
tmux new-window -t simchair -n viewer "$D/run_viewer.sh"
tmux new-window -t simchair -n rsp "$D/run_rsp.sh"
if [[ -z "$VIDEO_ONLY" ]]; then
    tmux new-window -t simchair -n actuator "$D/run_actuator.sh"
    sleep 6
    tmux new-window -t simchair -n bridge "$D/run_bridge_live.sh"
fi
tmux new-window -t simchair -n zed_front "$D/run_zed.sh zed_front 42569280"; sleep 20
tmux new-window -t simchair -n zed_left  "$D/run_zed.sh zed_left 43779087";  sleep 20
tmux new-window -t simchair -n zed_right "$D/run_zed.sh zed_right 49910017"; sleep 25
[[ -z "$FIXED_BITRATE" ]] && tmux new-window -t simchair -n rate "$D/run_rate_controller.sh $((FRONT_BPS + 2 * SIDE_BPS)) $FRONT_BPS"
tmux new-window -t simchair -n webrtc_front "$D/run_webrtc_cam.sh zed_front 7.5 $FRONT_BPS"; sleep 4
tmux new-window -t simchair -n webrtc_left  "$D/run_webrtc_cam.sh zed_left 15.0 $SIDE_BPS side";  sleep 4
tmux new-window -t simchair -n webrtc_right "$D/run_webrtc_cam.sh zed_right 15.0 $SIDE_BPS side"
tmux list-windows -t simchair -F '#W'
TS_IP="$(tailscale ip -4 2>/dev/null || echo 100.93.121.3)"
echo "Video: open http://$TS_IP:8090/ on the sim chair (ONE viewer only)."
[[ -z "$VIDEO_ONLY" ]] && echo "Drive: put the chair in park (0) once to arm the bridge."
