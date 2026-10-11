# SimChair Performance Measurements

Record before/after numbers for each upgrade phase. Use the phone-stopwatch
glass-to-glass method (10 samples, report median) unless noted.

**Measurement date (baseline):** 2026-07-27  
**Operator:** Ryan Simpson / AVL  
**Network profile:** Tailscale (Windows `100.91.25.107` ↔ Jetson `100.93.121.3`)

> **2026-10-10 update:** peer-relay control RTT (38 ms median vs 132 ms DERP),
> WebRTC 3-camera results and the cellular bitrate ladder are in
> [RELAY_TELEOP_2026-10-10.md](RELAY_TELEOP_2026-10-10.md). On campus ↔ cellular
> a direct path is impossible; the target is now **peer-relay**, not direct.

---

## Phase 0 — Baseline (JPEG/TCP, 2026-07-27 / 2026-08-04)

UDP JPEG primary path added 2026-08-07 — log new glass-to-glass / bandwidth under Phase 1 when measured.

### Network

| Metric | Value | Notes |
|--------|-------|-------|
| Tailscale path | **DERP relay (lax)** | Target: **direct** — relay adds ~50–100 ms |
| Tailscale ping RTT | **88–112 ms** (10 samples) | Measured 2026-07-27 from sim-chair |
| Direct connection | No | Fix firewall/NAT before demo |

### Video (JPEG over TCP, ports 9001/9002/9003)

| Metric | Value | Target (post Phase 1) |
|--------|-------|------------------------|
| Resolution | 960×600 | ≥1280×720 (target 1920×1200) |
| Frame rate | 15 fps | 30 fps |
| Codec / transport | JPEG / TCP | H.265 / RTP-UDP |
| Glass-to-glass latency | _TBD — run stopwatch test_ | <150 ms median |
| Total bandwidth (3 cams) | _TBD — Task Manager_ | <25 Mbps |

### Control (UDP port 5006)

| Metric | Value | Target (post Phase 2) |
|--------|-------|------------------------|
| Packet format | `steering,throttle,brake,mode` | `seq,timestamp_ms,...` |
| Send rate | ~20 Hz (SDL loop) | 50 Hz fixed |
| Jetson watchdog | 400 ms | 300 ms + latched STOPPED |
| Teensy watchdog | None | 250 ms serial silence → zero motors |
| Failsafe test | _TBD — pull cable on stands_ | Stop <300 ms, re-arm required |

### Haptics (pre Phase 3)

| Metric | Value | Target (post Phase 3) |
|--------|-------|------------------------|
| IMU topic | `/imu/data` (Xsens MTi-680G) | Same |
| IMU publish rate | _TBD — `ros2 topic hz /imu/data`_ | Bridge at 50 Hz |
| IMU → chair path | Not wired | UDP 5007 → washout → D-BOX |
| Chair packet-loss behavior | N/A | Ramp to neutral ≥1 s |

---

## Phase 1a — UDP JPEG (2026-08-07)

_Fill after measuring live UDP path (`orin_camera_sender_udp.py`)._

| Metric | TCP before | UDP after | Pass? |
|--------|------------|-----------|-------|
| Resolution | ~960×600 | 1280×720 target | ≥720p |
| Frame rate | 15 fps | 30 fps target | ≥30 fps |
| Glass-to-glass latency | | | record |
| Total bandwidth | | | record |
| Codec | JPEG/TCP | JPEG/UDP chunked | |

## Phase 1b — Video (ZED SDK H.265 streaming)

_Fill after enabling ZED stream_server on Jetson and running `windows_zed_stream_receiver.py`._

| Metric | Before (UDP JPEG) | After | Pass? |
|--------|-------------------|-------|-------|
| Resolution | 1280×720 | | ≥720p |
| Frame rate | ~30 fps | | ≥30 fps |
| Glass-to-glass latency | | | <150 ms |
| Total bandwidth | | | <25 Mbps |
| Codec | JPEG/UDP | H.265/RTP-UDP | |

---

## Phase 2 — Control Hardening

_Fill after deploying updated `orin_vehicle_controller.py` and Teensy watchdog._

| Metric | Before | After | Pass? |
|--------|--------|-------|-------|
| Watchdog trip time | 400 ms | | ≤300 ms |
| Latched STOPPED | No | | Yes |
| Stale packet rejection | No | | Yes (seq) |
| Cable-pull failsafe | | | Stop <300 ms |

---

## Phase 3 — Haptics

_Fill after `imu_bridge.py` + `ImuHapticReceiver` running._

| Metric | Before | After | Pass? |
|--------|--------|-------|-------|
| Bridge rate | N/A | | 50 Hz |
| Braking pitch felt | No | | Yes (stands test) |
| Cornering roll felt | No | | Yes |
| Bump heave felt | No | | Yes |
| Packet-loss ramp | N/A | | ≥1 s to neutral |

---

## Phase 5 — Final Integration

_Fill after full simultaneous soak test._

| Metric | Value | Pass? |
|--------|-------|-------|
| Soak duration | | ≥30 min |
| Motor degradation observed | | No (or documented) |
| Final glass-to-glass latency | | <150 ms |
| Cold-boot to operational | | Zero manual tmux |
| Full demo rehearsal | | Pass |

---

## How to Measure

### Glass-to-glass video latency
1. Open phone stopwatch app (ms display) in front of a ZED lens.
2. Photograph phone + operator monitor in one frame.
3. Subtract phone time from photo timestamp (or read both in one image).
4. Repeat 10×; report median.

### Tailscale path
```powershell
tailscale ping 100.93.121.3
tailscale status   # connection must say "direct", not relay
```

### IMU rate (Jetson)
```bash
source /home/dinosaur/IGVC/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
export ROS_DOMAIN_ID=42
ros2 topic hz /imu/data
```
