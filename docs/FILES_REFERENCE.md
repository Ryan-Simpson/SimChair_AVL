# Files Reference

**Updated:** 2026-10-16

Where things live:

| Where | Path |
|---|---|
| Git working copy (sim chair PC) | `C:\Users\VRX 226\simchair_teleop` (GitHub `Ryan-Simpson/SimChair_AVL`) |
| Marvin copy (scp-deployed, not git) | `~/SimChair_AVL/` (same layout; only `jetson/` and `windows/multicam_viewer.html`) |
| WebRTC encoder package | `~/IGVC_webrtc` on Marvin (`avros_webrtc`, branch `feature/avros-webrtc` of IGVC_ROS2) |
| Team code (don't edit) | `~/IGVC` on Marvin |

## Marvin (`jetson/`)

| File | Purpose |
|---|---|
| `relay_teleop/start_all.sh` | Starts everything in tmux `simchair`. Options: `FRONT_ONLY`, `START_SCALE`, `MAX_SCALE`, `NO_IMU`, `DRIVE_MODE`, `VIDEO_ONLY`, `FIXED_BITRATE` |
| `relay_teleop/stop_all.sh` | Kills the `simchair` tmux session |
| `relay_teleop/env.sh` | Shared ROS environment (conda off, Cyclone, domain 0) |
| `relay_teleop/run_mediamtx.sh` | Stock MediaMTX: RTSP in :8554, WebRTC/WHEP out :8889 |
| `relay_teleop/run_viewer.sh` | Serves `multicam_viewer.html` on :8090 |
| `relay_teleop/run_zed.sh` | One ZED X wrapper by serial (front 42569280, left 49910017, right 43779087) |
| `relay_teleop/run_webrtc_cam.sh` | One avros_webrtc encoder (NVENC H.264 CBR) → MediaMTX |
| `relay_teleop/run_rate_controller.sh` | Adaptive bitrate from ping delay to the chair PC; pauses side cameras when clogged |
| `relay_teleop/run_actuator.sh` | actuator_node (Teensy owner) |
| `relay_teleop/run_bridge_live.sh`, `run_bridge_dry.sh` | Drive bridge live / print-only |
| `relay_teleop/run_xsens.sh`, `run_imu_bridge.sh` | Xsens driver; IMU bridge at 25 Hz |
| `relay_teleop/run_rsp.sh` | robot_state_publisher (TF for the ZEDs) |
| `relay_teleop/drive_log.py` | Optional 1 Hz log: GPS, eno1 kbps, ping (start commands in its header) |
| `orin_simchair_ros_bridge.py` | UDP 5006 → `/avros/actuator_command`; gear mode, arm with park |
| `simchair_ackermann.py` | Car-feel mapping for the diff-drive kart (pure Python, self-test with `python3 simchair_ackermann.py`) |
| `imu_bridge.py` | Xsens + wheel odom → 44-byte cue packets on UDP 5007 |

## Sim chair PC (`windows/`)

| File | Purpose |
|---|---|
| `start_chair.bat` | Starts the sender (`--no-dbox`), IMU Chair and the viewer |
| `simchair_sender_dbox.exe` | Wheel/pedals → UDP 5006 (source `dbox/sender`) |
| `imu_haptic_receiver.exe` | UDP 5007 → washout → D-BOX; writes `logs\imu_owd_*.csv` (source `dbox/imu_receiver`, flags in `dbox/README.md`) |
| `multicam_viewer.html` | 3-camera WHEP viewer with stats, auto-cutoff, **Save stats**; `?clock=1` adds the glass-to-glass clock |
| `dbox/` | C++ sources and CMake for both exes |
| `latency/analyze_latency.py` | Joins the delay log, viewer stats, drive log and router log into one timeline |
| `latency/router_poll.js` | Polls the AirLink router's RSRP/SINR from the logged-in ACEmanager tab |
| `dbxLive64.dll`, `SDL2.dll` | Required next to the exes; not in git |

## Packet formats

| Port | Direction | Format |
|---|---|---|
| UDP 5006 | chair → Marvin | `steering,throttle,brake,mode\n` (mode = gear: 0 park/off, 1 diff, 2 Ackermann, 3 off); v2 adds `seq,timestamp_ms,` in front |
| UDP 5007 | Marvin → chair | 44 bytes little-endian: `seq:u32, t_ms:u64, ax,ay,az,gx,gy,gz,roll,pitch:f32`. `t_ms` = Jetson wall clock at send. `ax`/`ay` are motion cues, not raw accel |
| TCP 8889 | chair → Marvin | WHEP (WebRTC) per camera: `/zed_front/whep`, `/zed_left/whep`, `/zed_right/whep` |
| TCP 8090 | chair → Marvin | Viewer page |

Old scripts: [../legacy/README.md](../legacy/README.md).
