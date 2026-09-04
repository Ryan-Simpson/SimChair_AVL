# Target Architecture — Industry-Grade Teleoperation in 2 Weeks

Research date: July 18, 2026. Goal: all subsystems (video, control, haptics, ops)
working at demo quality by **August 6, 2026** (CARS + president's lab tour).

---

## Executive Summary

| Subsystem | Current state | Root problem | Recommended fix | Effort |
|---|---|---|---|---|
| Video | Chunked JPEG/UDP ~1280x720@30 (TCP JPEG legacy) | Still intra-frame JPEG → bandwidth heavy vs H.265 | **ZED SDK native streaming** (H.265 NVENC, RTP/UDP) | 1–2 days |
| Control | UDP CSV, no watchdog | No failsafe if link drops; no stale-packet rejection | Add sequence numbers + 3-layer watchdog (Jetson, Teensy, operator UI) | 1–2 days |
| Haptics | Not wired | IMU → D-BOX bridge missing | UDP telemetry bridge + classical washout filter (industry standard motion cueing) | 3–4 days |
| Motors | Degrades over time; tilts right | Suspected Teensy firmware / Spark MAX config | Structured A/B debug plan (below) | 2–3 days |
| Ops | Manual tmux launches, iptables lost on reboot | Nothing survives a reboot; demo fragility | systemd services + iptables-persistent | 1 day |

**The single biggest win (next):** move past JPEG (even UDP) to hardware H.265. The ZED SDK has a
built-in streaming module that does hardware H.264/H.265 encoding on the Orin's
NVENC and sends RTP over UDP. Your ROS2 wrapper can turn it on with one
parameter while still publishing topics for the IGVC stack. Reported real-world
latency: 80–130ms glass-to-glass. This gets you full 1920x1200 at higher fps
for *less* bandwidth than your current 960x600 JPEG.

---

## 1. How Industry Does Teleoperation (Reference Model)

Commercial remote-driving stacks (Ottopia, DriveU, Vay, Adamo) converge on the
same architecture:

1. **Video:** hardware-encoded H.264/H.265/AV1, transported as RTP over UDP
   (never TCP — a lost packet must cost one frame, not stall the stream).
   WebRTC-class congestion control with adaptive bitrate. Glass-to-glass
   targets: 100–200ms over 5G; ~40ms achievable on good links. Your <150ms
   goal is exactly the industry target.
2. **Control:** small fixed-rate UDP packets (30–100Hz) with sequence numbers
   and timestamps. Multi-layer watchdogs: vehicle performs a controlled stop
   within a bounded time (typically 250–500ms of link silence). ArduPilot's
   GCS failsafe is the canonical open-source pattern.
3. **Telemetry/haptics:** vehicle state streamed back at 50–100Hz. Motion
   platforms use **classical washout filtering**: high-pass filters pass
   transient accelerations (bumps, jolts) to the platform; low-pass "tilt
   coordination" converts sustained acceleration into platform tilt so gravity
   substitutes for G-force; the platform "washes out" back to center below
   perception threshold. D-BOX actuators respond 0–100Hz at ±1g — more than
   enough fidelity.
4. **Ops:** everything is a supervised service with auto-restart; the vehicle
   fails safe on any component crash.

Your Tailscale link is the one non-industry piece (they use bonded cellular
modems), but for a campus demo it's fine — it's WireGuard UDP underneath, which
transports RTP happily. One caveat: **Tailscale MTU is 1280 bytes** — keep
video chunk sizes under that (see §2).

---

## 2. Video: ZED SDK Native Streaming (Plan A)

### Why your current setup gets bad resolution
JPEG compresses each frame independently (~50–150KB/frame at 960x600). At
15fps x 3 cameras that's already 20–60 Mbps. H.265 uses inter-frame
compression: full 1920x1200@30 looks good at ~4–8 Mbps **per camera**. You're
spending ~5–10x the bandwidth for ~1/4 the pixels.

### What to change
The ZED ROS2 wrapper can start a **local streaming server** while continuing
to publish ROS2 topics (confirmed by Stereolabs staff on their forum). It
encodes on NVENC (near-zero CPU cost) and sends RTP.

**Jetson side** — in each camera's wrapper config (common_stereo.yaml or per-
camera yaml), enable the stream server with a unique port per camera:

```yaml
stream_server:
  stream_enabled: true
  codec: 'H265'        # H264 if decode issues on the Windows GPU
  bitrate: 6000        # kbps, per camera; tune 4000-12000
  gop_size: 15         # small GOP = faster recovery from packet loss
  adaptative_bitrate: false  # stable link → keep quality constant
  chunk_size: 1200     # CRITICAL: below Tailscale's 1280 MTU
  target_framerate: 30
```

Ports auto-assign from the base port (30000) incrementing by 2 per receiver
connection; give each camera an explicit distinct port (e.g., front 30000,
left 30004, right 30008) to keep them separated.

Alternatively enable at runtime without config changes:
```bash
ros2 service call /zed_front/zed_node/enable_streaming std_srvs/srv/SetBool "{data: true}"
```

**Windows side** — install the ZED SDK (Windows build; requires the NVIDIA GPU
you already have for Surround). Replace windows_camera_receiver.py with a small
script per camera (or one script, three sl.Camera objects):

```python
import pyzed.sl as sl
init = sl.InitParameters()
init.set_from_stream("100.93.121.3", 30000)   # Jetson Tailscale IP + camera port
init.depth_mode = sl.DEPTH_MODE.NONE           # video only — big perf saving
cam = sl.Camera()
cam.open(init)
mat = sl.Mat()
while True:
    if cam.grab() == sl.ERROR_CODE.SUCCESS:
        cam.retrieve_image(mat, sl.VIEW.LEFT)
        # mat.get_data() -> numpy BGRA; display via OpenCV as you do now
```

Keep your existing pattern of main-thread-only OpenCV display; you already
solved that. Window positions x=0/1920/3840 stay the same.

### Why this beats finishing the GStreamer RTSP work
- Zero custom encoder code to maintain; no GstRtspServer thread-safety pain
  (the exact thing that burned you).
- Encoder is NVENC either way — same hardware path, but Stereolabs maintains it.
- RTSP adds a negotiation layer you don't need between two known machines.

### Plan B (fallback if ZED streaming misbehaves over Tailscale)
Direct GStreamer RTP/UDP — **no RTSP server**, which removes your black-screen
failure mode entirely. Jetson (per camera, still fed from your existing ROS
appsrc sender, launched WITH the ROS env):

```
appsrc ! videoconvert ! nvvidconv ! 'video/x-raw(memory:NVMM),format=NV12' !
nvv4l2h264enc bitrate=6000000 maxperf-enable=1 insert-sps-pps=true
  iframeinterval=15 idrinterval=15 !
h264parse config-interval=1 ! rtph264pay mtu=1200 !
udpsink host=100.91.25.107 port=5600 sync=false async=false
```

Windows receiver (stock GStreamer, no ZED SDK needed):
```
udpsrc port=5600 caps="application/x-rtp,media=video,encoding-name=H264" !
rtpjitterbuffer latency=50 ! rtph264depay ! h264parse !
d3d11h264dec ! videoconvert ! autovideosink sync=false
```

Key flags you were missing per NVIDIA/RidgeRun guidance: `maxperf-enable=1`,
NVMM caps before the encoder, `sync=false async=false` on the sink, and
`mtu=1200` on the payloader (Tailscale MTU again).

### Acceptance test
- All 3 cameras at ≥1280x720@30 (target 1920x1200) with smooth motion.
- Glass-to-glass latency <150ms (measurement method in §6).
- Bandwidth: `tailscale status` / task manager shows <25 Mbps total.

---

## 3. Control Link: Add the Safety Layer

Your UDP CSV link works; what's missing is what industry never ships without —
**bounded-time failsafe**. Three layers:

1. **Jetson watchdog** (orin_vehicle_controller.py): one already exists at
   0.4s (WATCHDOG_S) — tighten to **300ms** and add a latched STOPPED state:
   after a trip, require a fresh mode=1 packet to resume rather than silently
   resuming when packets return. ~15 lines of change.
2. **Teensy watchdog** (firmware): if no serial command for **250ms** → zero
   both motors. This protects against the Python layer dying. (Do this while
   you're in the firmware for the degradation bug anyway.)
3. **Operator feedback**: sim chair UI shows link state (last-ack age). Add a
   1Hz status packet Jetson→Windows (echo of seq + kart state). Optional but
   cheap and makes demos confident.

Packet upgrades (keep CSV if you like, just add fields):
`seq,timestamp_ms,steering,throttle,brake,mode\n`
- Receiver drops any packet with seq ≤ last-seen (out-of-order/stale UDP).
- Send rate: fix at **50Hz** (20ms) — industry sweet spot; don't tie the send
  loop to the SDL poll rate.

### Motor degradation debug plan (the demo-killer bug)
Structured A/B, one variable at a time:
1. Reproduce with **phone-joystick Teensy code** (your team's known-good).
   - Degrades too → electrical/thermal: check Spark MAX current limit +
     thermal throttling in REV Hardware Client logs; check battery sag under
     sustained load; check brushed/brushless config match.
   - Stays smooth → diff the two Teensy firmwares' serial handling: look for
     missing input buffer flush (input backlog grows → commands lag → "feels
     dead"), integer counters that saturate, or a rate limiter with
     accumulated state.
2. Log timestamps: at the Jetson (command sent) and Teensy (command executed,
   blink/serial-echo). If commands are executed late, it's buffering; if
   executed on time but the kart is weak, it's power/motor-side.
3. Right-tilt: swap left/right Spark MAX controllers (just the controllers,
   not motors). Tilt follows the controller → config mismatch; stays with the
   side → motor/mechanical. Verify identical firmware + current limits via
   REV Hardware Client while you're in there.

---

## 4. Haptics: IMU → D-BOX in 4 Days

Everything on the D-BOX side already works (DBoxManager, async streaming).
What's missing is the telemetry bridge and the motion-cueing math.

### Architecture
```
Xsens MTi-680G (ROS2 topic, up to 400Hz)
        ↓
imu_bridge.py (NEW, Jetson)                    ← Day 1
  - subscribes /imu/data (verify topic name)
  - downsamples to 50Hz
  - UDP binary packet → Windows port 5007:
    seq, t_ms, accel_xyz, gyro_xyz, roll, pitch
        ↓  Tailscale UDP
        ↓
DBoxManager (Windows, existing)                ← Days 2-3
  - washout filter (below)
  - feeds MotionData{Roll, Pitch, Heave} at 50Hz
```

50Hz matches DBoxManager's existing streaming period (StartPeriodicStreaming
at 20ms) — keep the whole haptic chain at one rate rather than redesigning
the working D-BOX side. (D-BOX actuators handle 0–100Hz, ±1g, so 50Hz update
with the SDK's interpolation is plenty for vehicle motion cues.)

### The washout filter (industry-standard motion cueing)
Raw IMU → chair position must NOT be a direct mapping (the chair would slam
into its travel limits on sustained acceleration). Classical washout, per
axis, at 50Hz:

```
sustained (tilt coordination):
  a_low  = LPF(a_long, fc≈0.8Hz)
  pitch_cmd = clamp(k_p * a_low)          # brake → pitch forward
  roll_cmd  = clamp(k_r * LPF(a_lat))    # corner → roll into turn
  rate-limit tilt to <3°/s so the operator feels force, not rotation

transient (road feel):
  heave_cmd = HPF(a_vert, fc≈1.5Hz) * k_h  # bumps/vibration pass through
  
all axes: washout — commands decay to center with ~2-5s time constant
          (HPF on the output achieves this implicitly)
```

Start with single-pole filters (`y += alpha*(x-y)`) — genuinely sufficient for
a demo; tune the three gains (k_p, k_r, k_h) with the kart on stands. Xsens
MTi-680G already outputs gravity-compensated free acceleration and fused
roll/pitch — use those directly rather than integrating raw accel yourself.

Map EngineRpm/EngineTorque in MotionData from your commanded RPM values —
free realism (D-BOX renders it as vibration texture).

### Safety
Same watchdog pattern: no IMU packet for 500ms → chair ramps to neutral over
1s (never snaps). Clamp all outputs to a "comfort envelope" at 50% of chair
limits until tuning is done.

---

## 5. Operations: Survive a Reboot, Survive a Demo

Current fragility: manual tmux launches, env vars per terminal, iptables gone
on reboot, 25s camera stagger by hand. Industry rule: *if it isn't a
supervised service, it doesn't exist.*

**Jetson — systemd units** (template):
```ini
# /etc/systemd/system/marvin-cam-front.service
[Unit]
Description=Marvin ZED front camera
After=network-online.target

[Service]
User=dinosaur
# env exactly as your docs require; DISPLAY deliberately unset
Environment=RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
Environment=CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
Environment=ROS_DOMAIN_ID=42
ExecStart=/usr/bin/bash -lc 'source /home/dinosaur/IGVC/install/setup.bash && exec /usr/bin/python3 <launch cmd>'
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```
- Camera stagger: `marvin-cam-left` gets `After=marvin-cam-front.service` +
  `ExecStartPre=/bin/sleep 25` (your proven value), left→right likewise.
  Note systemd `After=` waits for start, not readiness — the sleep stays.
- One unit each: 3 cameras, vehicle controller, imu_bridge, camera streaming.
- `Restart=on-failure` = auto-recovery mid-demo.
- These units live in /etc/systemd/system — **no files inside ~/IGVC touched**.

**iptables:** `sudo apt install iptables-persistent` then
`sudo netfilter-persistent save` once rules are right. Rule gone forever from
your launch checklist.

**Windows:** put receiver + DBoxManager + sender behind a single `start_all.bat`
(or NSSM services if you want auto-start on boot).

**Rewrite LAUNCH_PROCEDURE.md** at the end to: "power on both machines; run
start_all.bat; wait for green". That's the industry bar — and it's what you
want with a president watching.

---

## 6. Latency: Measure Before and After

- **Glass-to-glass:** phone stopwatch app (ms display) in front of a ZED lens;
  photograph phone + operator monitor in one frame; subtract. 10 samples,
  report median. Free and industry-accepted for demos.
- **Network RTT:** `tailscale ping 100.93.121.3` — confirm direct (not DERP-
  relayed) connection; direct should be ~1–10ms on campus. If relayed, fix
  firewall/NAT first (that alone can add 50ms+).
- **Control loop:** timestamp in packet, echo back, halve the round trip.
- Record numbers before switching video stacks — a measured "JPEG 220ms →
  H.265 95ms" line is exactly the kind of result that belongs on the CARS
  poster.

---

## 7. Two-Week Plan

**Week 1 — video + control hardening**
- Day 1: Baseline latency measurements. Install ZED SDK on Windows PC.
- Day 2: Enable stream server on front camera; Windows receiver for one
  stream. Tune bitrate/chunk_size over Tailscale.
- Day 3: All 3 cameras streaming; 3-monitor layout; measure latency again.
- Day 4: Control packet seq/timestamp + Jetson watchdog + 50Hz fixed rate.
- Day 5: Motor degradation A/B test (phone joystick firmware); Spark MAX
  config audit via REV Hardware Client; controller-swap test for right-tilt.
- Weekend buffer: whatever slipped.

**Week 2 — haptics + ops + integration**
- Day 6: imu_bridge.py; verify MTi-680G topic rates; UDP telemetry flowing.
- Day 7: Washout filter into DBoxManager; kart on stands; tune gains.
- Day 8: Teensy watchdog + serial fixes from Day 5 findings.
- Day 9: systemd units + iptables-persistent + start_all.bat; reboot test:
  both machines cold-boot to fully operational with no manual steps.
- Day 10: Full integration: cameras + control + chair simultaneously, kart on
  stands, then driving. Measure final latency.
- Days 11–12: Soak test (find the degradation before the president does),
  demo script, rehearsal, updated LAUNCH_PROCEDURE.md.

**Scope discipline:** if Week 1 slips, cut Plan B GStreamer work (Plan A is
enough), never cut watchdogs or the reboot test — reliability is what
"industry grade" means in a live demo.

---

## Sources

- [ZED SDK Local Video Streaming docs](https://www.stereolabs.com/docs/video/streaming) — H.264/H.265 NVENC, RTP, bitrate control
- [ZED local network streaming (API detail)](https://docs.stereolabs.com/docs/development/zed-sdk/modules/camera/local-network-streaming) — enable_streaming(), ports, receiver requirements
- [Stereolabs forum: local streaming latency](https://community.stereolabs.com/t/local-streaming-latency/11444) — 80–130ms measured, GOP/bitrate tuning advice
- [Stereolabs forum: ROS2 wrapper + streaming simultaneously](https://community.stereolabs.com/t/is-the-ros2-wrapper-and-streaming-mutually-exclusive-and-or-working/11314) — staff-confirmed
- [ZED Hardware Encoding Bridge for ROS 2](https://docs.stereolabs.com/docs/integrations/ros-2/hardware-encoding-bridge.md) — codec/GOP/chunk-size parameters
- [ZED GStreamer package (ZED X support)](https://www.stereolabs.com/blog/introducing-the-updated-zed-gstreamer-package)
- [NVIDIA Accelerated GStreamer guide](https://docs.nvidia.com/jetson/archives/r36.2/DeveloperGuide/SD/Multimedia/AcceleratedGstreamer.html) — NVMM, nvv4l2h264enc
- [RidgeRun: GStreamer encoding latency on Jetson](https://developer.ridgerun.com/wiki/index.php/GStreamer_Encoding_Latency_in_NVIDIA_Jetson_Platforms) — maxperf-enable
- [RidgeRun: Jetson Orin H264 pipelines](https://developer.ridgerun.com/wiki/index.php/NVIDIA_Jetson_Orin/GStreamer_Pipelines/H264)
- [Ottopia: Teleoperation — Not Your Typical Video Stream](https://www.ottopia.tech/blog-posts/teleoperation-not-your-typical-video-stream)
- [DriveU: teleoperation connectivity platform](https://driveu.auto/teleoperation/teleoperation-connectivity-platform/)
- [Adamo: low-latency remote operation](https://adamohq.com/blog/remote-operation-for-autonomous-vehicles-at-low-latency) — 40ms glass-to-glass claim
- [5G teleoperated driving evaluation (arXiv)](https://arxiv.org/pdf/2503.14186) — 202ms average glass-to-glass over 5G
- [ArduPilot Rover failsafes](https://ardupilot.org/rover/docs/rover-failsafes.html) — canonical watchdog/failsafe pattern
- [Classical washout motion cueing (VT thesis)](https://vtechworks.lib.vt.edu/items/c29f560e-a521-408f-b81e-d85601c0ec78)
- [Motion simulator washout overview (Wikipedia)](https://en.wikipedia.org/wiki/Motion_simulator)
- [D-BOX LiveMotion SDK](https://www.d-box.com/en/license-live-motion-sdk) · [D-BOX actuator specs via AXSIM](https://axsim.racing/d-box/) — 0–100Hz, ±1g
