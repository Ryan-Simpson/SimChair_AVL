#!/bin/bash
# run_imu_bridge.sh — /imu/data -> UDP :5007 on the sim chair PC (44-byte packets)
# IMU_HZ (default 25): ~25 kbps uplink at 25 Hz over Tailscale, double at 50.
source "$(dirname "$0")/env.sh"
exec nice -n 10 /usr/bin/python3 "$(dirname "$0")/../imu_bridge.py" --topic /imu/data \
  --windows-ip "${CHAIR_IP:-100.91.25.107}" --hz "${IMU_HZ:-25}"
