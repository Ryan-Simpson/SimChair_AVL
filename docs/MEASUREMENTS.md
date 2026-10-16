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
| IMU publish rate | 100 Hz (measured 2026-10-14) | Bridge at 50 Hz (25 Hz in use) |
| IMU → chair path | Not wired → working 2026-10-14 (see Phase 3) | UDP 5007 → washout → D-BOX |
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

Measured 2026-10-14, Marvin outdoors at night over cellular, driver in the chair.

| Metric | Before | After | Pass? |
|--------|--------|-------|-------|
| Bridge rate | N/A | 25 Hz, 0 of 4,496 packets lost over 180 s, max gap 0.14 s | Yes (25 Hz chosen to save uplink; target was 50) |
| Xsens `/imu/data` rate | TBD | 100 Hz | Yes |
| Yaw rate vs command (diff mode) | N/A | steer +0.24 → +0.39 rad/s (expected 0.36); −0.2 → −0.35 to −0.43 | Yes |
| Braking / speed-up pitch felt | No | Yes, from wheel-encoder accel (raw accel was random) | Yes (driver approved) |
| Cornering / pivot roll felt | No | Yes, speed × yaw rate + yaw rate | Yes (driver approved) |
| Bump heave | No | Turned off on purpose: track judder made it a constant buzz | n/a |
| Packet-loss ramp | N/A | Ramps to neutral within ~1 s after 500 ms with no packets | Yes |
| Accel noise, parked / driving | — | 0.04 / 0.8 m/s² (peaks 3–5), real speed changes ~0.3 m/s² | — |

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

## Relay teleop video latency study (started 2026-10-15)

Goal: find where the video lag comes from before changing anything (Step 1),
then A/B each fix against these numbers (Steps 2–3). Video path: 3× ZED X →
avros_webrtc NVENC H.264 → MediaMTX → Chrome WHEP, over the Tailscale peer
relay on Marvin's AT&T cellular. Tools are in `windows/latency/`.

### What each run records

| Signal | Source | Tells us |
|---|---|---|
| Glass-to-glass | Viewer `?clock=1` clock filmed by the front ZED; Chrome tab screenshots, live − filmed time | Total delay you see |
| Upload queue | `imu_haptic_receiver.exe` → `windows\logs\imu_owd_*.csv` (arrival − Jetson send time of each 25 Hz IMU packet, minus the run's minimum) | The cellular upload queue the video shares, with no clock sync |
| Per-camera fps, kbps, freezes, jitter buffer | Viewer **Save stats** → `marvin_video_stats_*.json` | What the viewer actually got |
| Upload rate, ping, GPS | Marvin `jetson/relay_teleop/drive_log.py` → `/tmp/drivelog/marvin_1hz.csv` (start commands in its header); rate controller and encoder logs via `tmux pipe-pane` | What Marvin sent, controller decisions |
| RSRP / SINR / cell ID | `windows/latency/router_poll.js` in the logged-in ACEmanager tab, every 5 s | Signal vs congestion |

Combine: `python windows/latency/analyze_latency.py --owd … --viewer … --marvin … --router … --g2g …`

### Procedure

1. Start Marvin (`start_all.sh`) and the chair side (`start_chair.bat`); the IMU
   receiver writes its delay log automatically.
2. Open the viewer in Chrome as `http://100.93.121.3:8090/?clock=1` (the only viewer).
3. Log into ACEmanager through the SSH tunnel and start `router_poll.js`.
4. Glass-to-glass: Marvin parked facing the monitor, front ZED filming the
   clock box. Take ≥ 20 Chrome screenshots a few seconds apart; read live and
   filmed `SS.mmm` from each into `g2g.csv` (`sample,live,filmed`).
5. Then drive the usual route (lab → outside → back) for the queue/signal log.
6. Save stats in the viewer, stop everything, collect the logs, run the analysis.

Run once at night and once in the daytime; note the time of day and weather.

### Results

| Run | Time | Glass-to-glass median / p90 | Queue median / p90 / p99 / max | >500 ms | Front fps / freezes | RSRP / SINR range | Cell IDs | Notes |
|---|---|---|---|---|---|---|---|---|
| Baseline night | | | | | | | | |
| Baseline day (A, 3 cams) | 10-15 16:47–16:56, sunny, campus busy, parked outside | not measured (parked outside) | 23 / 188 / 3,439 / 6,509 ms (startup spike; after 2 min: 22 / 102 / 519 / 1,492) | 4.6% | front 7.3 fps, 179 kbps, 37 freezes; sides 4 fps avg but < 3 fps 75% of seconds | not logged | not logged | Controller sawtooth: climbs to 0.8–1.3 Mbps, queue spikes, sides paused. eno1 tx is inflated by ~1 Mbps of local DDS multicast (239.255.0.1); real cellular = tailscale0 (~250 kbps) |
| Baseline day (B, front only, MAX_SCALE 0.8) | 10-15 16:57–17:03 | not measured | 22 / 352 / 6,008 / 36,342 ms; without the outage 17–23 / 40–141 / 274–569 / 857 | 8.8% | 6.6 fps, 226 kbps, 35 freezes, jb 223 ms; viewer auto-cutoff fired | not logged | not logged | One 59 s cell outage at the 125 kbps floor (queue peaked at 36 s): the cell, not our rate |

| Day (10-16, 3 cams, 90 min) | 10-16 10:59–12:30, outdoors, driving | not measured | Per 5 min: median +20–40 ms over that stretch's floor, p99 mostly < 1 s, a few 2–5 s spikes (whole-run stats unusable: ~2.95 s Jetson clock step ~25 min in, after a reboot) | — | front 7.4 fps, 404 kbps, 90 freezes; sides 13.7 fps, ~250 kbps, ~320 freezes each, < 3 fps 1–8% of seconds | not logged | not logged | Sides paused in 90 of 1,100 controller ticks. Driver: "the test went amazing" |
| Indoors (10-15 17:04–17:15, front only) | lab, Marvin moved toward the chair | ~4.2 s (1 reading, link clogged) | Clean (~20 ms) while parked; 1–2 min stalls up to 26–32 s each time Marvin moved; near the chair it can't hold 125 kbps | — | viewer auto-cutoff 3× | not logged | not logged | Cellular dead spot near the chair: measure glass-to-glass outdoors |

### A/B (Step 2–3 changes, each against the baseline of the same time of day)

| Change | Run | Glass-to-glass | Queue p90 / max | Front fps / freezes | Keep? |
|---|---|---|---|---|---|
| | | | | | |

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
