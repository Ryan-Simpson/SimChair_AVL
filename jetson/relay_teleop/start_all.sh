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
# Encoders start 4 s apart: starting all three at once caused a ~20 s
# lag spike (simultaneous keyframe bursts).
D="$(cd "$(dirname "$0")" && pwd)"
FRONT_BPS="${FRONT_BPS:-500000}"
SIDE_BPS="${SIDE_BPS:-350000}"

if tmux has-session -t simchair 2>/dev/null; then
    echo "tmux session 'simchair' already exists — run stop_all.sh first"; exit 1
fi

tmux new-session -d -s simchair -n mediamtx "$D/run_mediamtx.sh"
tmux new-window -t simchair -n rsp "$D/run_rsp.sh"
if [[ -z "$VIDEO_ONLY" ]]; then
    tmux new-window -t simchair -n actuator "$D/run_actuator.sh"
    sleep 6
    tmux new-window -t simchair -n bridge "$D/run_bridge_live.sh"
fi
tmux new-window -t simchair -n zed_front "$D/run_zed.sh zed_front 42569280"; sleep 20
tmux new-window -t simchair -n zed_left  "$D/run_zed.sh zed_left 43779087";  sleep 20
tmux new-window -t simchair -n zed_right "$D/run_zed.sh zed_right 49910017"; sleep 25
tmux new-window -t simchair -n webrtc_front "$D/run_webrtc_cam.sh zed_front 7.5 $FRONT_BPS"; sleep 4
tmux new-window -t simchair -n webrtc_left  "$D/run_webrtc_cam.sh zed_left 15.0 $SIDE_BPS";  sleep 4
tmux new-window -t simchair -n webrtc_right "$D/run_webrtc_cam.sh zed_right 15.0 $SIDE_BPS"
tmux list-windows -t simchair -F '#W'
echo "Video: open windows/multicam_viewer.html on the sim chair (ONE viewer only)."
[[ -z "$VIDEO_ONLY" ]] && echo "Drive: put the chair in park (0) once to arm the bridge."
