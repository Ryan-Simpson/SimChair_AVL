# Marvin Teleoperation Sim Chair — Project Overview

## What This Project Is

A full bidirectional haptic teleoperation system for a go-kart called **Marvin**. An operator sits in a sim chair (Thrustmaster wheel/pedals + D-BOX motion chair) and drives Marvin remotely via a Tailscale VPN connection. Three ZED X cameras on the kart stream live video back to three monitors at the operator station.

## Goal

Give the operator a "human level of sight" and realistic physical feedback — camera quality good enough to drive confidently, and a motion chair that physically reacts to the kart's real-world G-forces via IMU data.

## Team

- Cal Poly Pomona — AVL (Autonomous Vehicles Lab)
- Team members: Kevin Xu, Yi-Szen Tang, Tyler Carrasco, Justin Dang
- Team Lead: Ryan Simpson
- This conversation primarily with: Ryan Simpson

## Hardware

### Operator Side (Windows PC — "sim-chair")
- Tailscale IP: `100.91.25.107`
- Thrustmaster racing wheel + pedals (SDL2 input)
- D-BOX motion chair (haptic feedback)
- 3 monitors in NVIDIA Surround layout (x offsets: 0, 1920, 3840)

### Kart Side (Jetson Orin — "dinosaur")
- Tailscale IP: `100.93.121.3`
- OS: Ubuntu 22.04, ROS2 Humble
- 3x ZED X GMSL cameras (front, left, right)
- Teensy 4.1 motor bridge (USB serial `/dev/ttyACM0`, 115200 baud)
- REV Spark MAX motor controllers
- Velodyne LiDAR
- Xsens IMU (MTI series)
- NTRIP GPS client

## Network

All communication over **Tailscale VPN** — the local router is not required (both machines have independent internet).

- UDP port 5006: Windows → Jetson (steering/throttle/brake/mode)
- UDP port 5007: Jetson → Windows (IMU haptics via `imu_bridge.py`)
- UDP port 5008: Jetson → Windows (vehicle controller status)
- UDP ports 9001/9002/9003: Jetson → Windows (chunked JPEG — **primary**)
- TCP ports 9001/9002/9003: legacy JPEG path
- RTSP/RTP H.264: experimental only

## Workspace layout (Windows)

See `LAUNCH.txt` and `docs/FILES_REFERENCE.md`.

- Launch apps from `C:\Users\VRX 226\cursor-test\windows\`
- Jetson script mirror: `C:\Users\VRX 226\cursor-test\jetson\`
- Live Jetson copies: `~/Documents/SimChair_Teleop/`
