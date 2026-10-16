# HANDOFF GUIDE — Read This First

You are Claude Code running on the **sim chair Windows PC** ("sim-chair",
Tailscale 100.91.25.107). Your job over the next ~2 weeks: take the Marvin
teleoperation system from "every part roughly works" to **demo-grade, all
parts working simultaneously**, before **August 6, 2026** — the CARS symposium
and a lab tour by the university president. Hard deadline. Reliability beats
features.

Your operator is Ryan Simpson (team lead, undergrad, Cal Poly Pomona AVL).
Mentor: Dr. Behnam Bahr.

## Reading order

1. **This file** — mission, constraints, safety rules
2. `PROJECT_OVERVIEW.md` — what the system is
3. `SYSTEM_ARCHITECTURE.md` — current data flows + ROS env setup
4. `FILES_REFERENCE.md` — where every file lives, key code snippets
5. `KNOWN_ISSUES_AND_HISTORY.md` — bugs fixed, bugs open, decisions made. **Do
   not re-fight battles this file says are already lost/won**
6. `TARGET_ARCHITECTURE.md` — the researched plan you are implementing
   (industry practices, exact configs, 2-week schedule)
7. `NETWORK_OPTIONS.md` — Tailscale MTU rules + LAN fallback
8. `LAUNCH_PROCEDURE.md` — how the system starts today (you will replace this
   with something better in Phase 4)

## Your environment

- **This machine (Windows):** working dir `C:\Users\VRX 226\cursor-test\windows\`
  (legacy: `C:\Users\VRX 226\test\`). NVIDIA GPU, 3 monitors in NVIDIA Surround
  (x offsets 0/1920/3840), Thrustmaster wheel/pedals, D-BOX chair. C++ D-BOX
  code in `C:\Users\VRX 226\Test Workspace\2026_Sim_Chair\`.
- **The kart (Jetson Orin, "dinosaur", 100.93.121.3):** teleop scripts in
  `~/Documents/SimChair_Teleop/` (mirrored at `cursor-test\jetson\`). Prefer
  Tailscale HTTP file transfer if SSH keys are missing.
- Both machines talk **only over Tailscale**. Prefer `tailscale ping` "direct"
  (DERP works but hurts video).

## ⛔ Non-negotiable constraints (violating these breaks things or trust)

1. **NEVER modify anything inside `/home/dinosaur/IGVC/`** — shared IGVC
   competition code. Read/source it; never write.
2. Every Jetson ROS2 terminal needs the exact env block from
   `SYSTEM_ARCHITECTURE.md` (source IGVC setup.bash, CycloneDDS, DOMAIN_ID 42).
3. `unset DISPLAY` on its **own line** before ZED work — do **not** use
   `export DISPLAY=` (empty string still breaks Argus). Also launch ZEDs with
   `publish_tf:=true` `publish_urdf:=true` or they hang without publishing images.
4. Use `/usr/bin/python3`, never bare `python3` (conda hijacks it on Jetson).
5. ZED cameras launch **one at a time, 25s apart** — simultaneous launch has
   crashed the Argus daemon, and all readiness-detection approaches failed
   (see KNOWN_ISSUES). Caveat: this is an empirical workaround, not a
   verified constraint — ZED X GMSL2 is designed for simultaneous multi-cam,
   so the crash may have been an SDK bug or a side effect of the DISPLAY/EGL
   issue. You MAY retest once, early, timeboxed (~30 min): check the
   installed ZED SDK version and its release notes for multi-camera fixes,
   try a parallel launch, and if Argus crashes, restart the daemon
   (`sudo systemctl restart nvargus-daemon`), revert to the 25s stagger, and
   never revisit. Do not burn sprint time on this.
6. OpenCV display calls on Windows must run on the **main thread**.
7. iptables rules do not persist across Jetson reboots (until Phase 4 fixes
   this, re-add them each session).
8. Correct ZED topic pattern: `/zed_{name}/zed_node/rgb/color/rect/image`
   (+`/compressed`). Older docs/scripts had wrong names.

## 🛑 Safety rules for YOU (an AI operating a physical vehicle)

- **Never send drive commands (mode=1) on your own initiative.** Ryan decides
  when the kart moves. Your testing ceiling without explicit human go-ahead:
  mode=0 packets, kart on stands, or motors unpowered.
- Default assumption for any motor-related test: **kart on stands**.
- When editing `orin_vehicle_controller.py` or Teensy firmware, preserve the
  watchdog and the mode=0 stop path in every revision. If you touch the
  serial protocol, test the stop command first.
- The chair moves a human. New motion code: clamp outputs to ≤50% of chair
  range until Ryan approves tuning; ramp to neutral (≥1s), never snap.

## What already works — DO NOT rebuild

- Wheel/pedal → UDP → Jetson → Teensy → motors (full control path)
- `orin_vehicle_controller.py` **already has a 0.4s watchdog** and mode gate
- 3-camera JPEG streaming (UDP primary; TCP legacy). Next upgrade is H.265;
  keep JPEG launchable as fallback
- D-BOX SDK integration: `DBoxManager` class streams at 50Hz (20ms period),
  sine-wave test harness exists (`DBoxManagerTest.cpp`)
- ZED launch procedure with 25s stagger

## Implementation phases (details in TARGET_ARCHITECTURE.md)

Work them in order; each has a "done" gate. Don't start a phase until the
previous one's gate passes, except where marked parallel-safe.

### Phase 0 — Baseline (half day)
Measure before changing: glass-to-glass video latency (phone-stopwatch
method, §6 of TARGET_ARCHITECTURE), `tailscale ping`, current fps/resolution.
Record numbers in a new `MEASUREMENTS.md`. These become poster material.
**Gate:** numbers written down.

### Phase 1 — Video upgrade (2–3 days) ← biggest win
Replace JPEG-over-TCP with **ZED SDK native streaming** (H.265, NVENC, RTP).
- Jetson: `stream_server` params in the zed_wrapper config (or
  `enable_streaming` service). **`chunk_size: 1200`** — Tailscale MTU 1280.
  Distinct port per camera (30000/30004/30008).
- Windows: install ZED SDK; new receiver script per §2 of TARGET_ARCHITECTURE
  (`sl.InitParameters().set_from_stream(...)`, `depth_mode = NONE`, display
  on main thread like the current receiver).
- Firewall: new iptables rules for the stream ports (UDP).
- Plan B if ZED streaming fights you >1 day: direct GStreamer RTP/UDP (NO
  RTSP server) — exact pipelines in TARGET_ARCHITECTURE §2.
**Gate:** 3 cameras ≥720p30 on the 3 monitors, glass-to-glass <150ms,
measured and logged.

### Phase 2 — Control hardening (1–2 days, parallel-safe with Phase 1)
- Add `seq,timestamp_ms` to the control packet; drop stale/out-of-order.
- Fix send rate at 50Hz.
- Tighten Jetson watchdog 0.4s → 0.3s; on trip, require fresh mode=1 to
  resume (STOPPED state).
- Teensy firmware watchdog: zero motors after 250ms serial silence.
- Motor bugs (the real demo risk — needs Ryan/team in the loop for hardware):
  A/B with phone-joystick firmware, Spark MAX audit via REV Hardware Client,
  left/right controller swap for the right-tilt. Full plan: §3.
**Gate:** pull the network cable mid-drive (on stands) → motors stop <300ms;
replug → no motion until operator re-arms mode.

### Phase 3 — Haptics (3–4 days)
The missing piece the president will sit in.
- New `imu_bridge.py` on Jetson: subscribe Xsens MTi-680G topic (verify name:
  `ros2 topic list | grep -i imu`; sensors.launch.py starts the driver),
  downsample, UDP → Windows port 5007. **50Hz** (matches DBoxManager's
  existing 20ms streaming period — do not redesign that).
- Windows: washout filter → `DBoxManager` (classical: LPF tilt coordination
  for sustained accel → roll/pitch; HPF → heave; decay to center; full spec
  §4). Use MTi-680G's fused free-acceleration + roll/pitch outputs directly.
- Chair safety: 500ms packet-loss → ramp to neutral; 50% clamp until tuned.
- Tune gains with kart on stands, then Ryan driving.
**Gate:** operator in chair feels braking pitch, cornering roll, bump heave
with kart on stands being pushed/tilted by hand; no violent motion on packet
loss (test by killing imu_bridge mid-run).

### Phase 4 — Ops hardening (1 day)
- systemd units on Jetson for: 3 cameras (staggered via After= + 25s
  ExecStartPre sleeps), vehicle controller, camera streaming, imu_bridge.
  Template in §5. Units live in /etc/systemd/system — IGVC untouched.
- `iptables-persistent` (`netfilter-persistent save`).
- Windows `start_all.bat` for receiver(s) + sender + D-BOX.
- Rewrite `LAUNCH_PROCEDURE.md` to match the new reality.
**Gate:** cold-boot both machines → fully operational with zero manual
terminal work. Then kill any single process → it self-restarts.

### Phase 5 — Integration + soak (2 days)
- Everything running at once: cameras + control + chair.
- 30+ minute soak drive — this is where the motor degradation bug will show
  if unfixed. Log everything.
- Final latency measurements → `MEASUREMENTS.md`.
- Demo script: exact steps, who stands where, what to say, fallback plan
  (JPEG receiver) if anything dies.
**Gate:** one full rehearsal, cold boot to demo, no manual intervention.

## Working style expected

- One variable at a time; keep the working JPEG path launchable until Phase 1
  gate passes. Same pattern for every replacement: build alongside, verify,
  then switch.
- Log measurements in `MEASUREMENTS.md` as you go (before/after per phase).
- Update `KNOWN_ISSUES_AND_HISTORY.md` when you fix or discover something —
  it's the team's institutional memory.
- If a subsystem resists >1 day beyond its budget, take the documented
  fallback and move on. The demo needs all parts working, not any part
  perfect. Ship reliability.
