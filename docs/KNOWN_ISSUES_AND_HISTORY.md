# Known Issues, History, and Lessons Learned

## What's Working

| Feature | Status | Notes |
|---------|--------|-------|
| Sim chair wheel/pedal input | ✅ Working | simchair_sender_dbox.exe via SDL2, `--no-dbox` |
| Drive via ROS bridge | ✅ Working | UDP 5006 → `orin_simchair_ros_bridge.py` → actuator_node (the only Teensy owner) |
| D-BOX SDK integration | ✅ Working | DBoxManager class, async streaming |
| Relay teleop video (3× WebRTC) | ✅ Working (2026-10) | NVENC H.264 → MediaMTX, Tailscale peer relay, adaptive bitrate; `relay_teleop/start_all.sh` |
| Ackermann / gear select | ✅ Working (2026-10-13) | Paddles: 1 = diff, 2 = Ackermann, 0/3 = off; bridge clips to actuator max 0.40 m/s |
| IMU → D-BOX chair | ✅ Working (2026-10-14) | Encoder accel + gyro yaw cues → `imu_haptic_receiver.exe`; `windows/start_chair.bat` |

## What's In Progress

| Feature | Status | Blocker |
|---------|--------|---------|
| Cellular capacity | 🔄 Open | Night 10–13 Mbps up. Busy daytime (10-15 ~16:45): fine ~90% of the time, but 3 cameras sawtooth and there was one 59 s stall even at the 125 kbps floor. 10-16 late morning: 3 cameras held for 90 min. Dead spots inside the building (1–2 min stalls each time Marvin moved). Router RSRP/SINR not logged yet. Numbers in MEASUREMENTS.md |
| Latency study Steps 2–3 | 🔄 Open | Encoder vbv-size / intra-refresh, viewer jitterBufferTarget, faster rate controller. Glass-to-glass still unmeasured |
| Closed-loop velocity drive | 🔄 Open | `--velocity` often Sparks purple; use duty / WebUI path |

---

## Persistent Issues

### Motor Degradation Over Time
**Symptom:** Kart drives fine on first launch, then after sustained use becomes very hard to move or stops responding.  
**Ruled out:** Mechanical (moves fine when pushed manually), software nodes (clean `ros2 node list`), serial buffer (reset_input_buffer didn't fix it).  
**Suspected:** Teensy firmware — possibly a timer, rate limiter, or counter that changes behavior over time, or the Spark Max hitting a configured current limit.  
**Next step:** Test with phone joystick Teensy code. If phone joystick also degrades → electrical. If phone joystick stays smooth → compare Teensy serial protocol differences.

### Kart Tilts Right
**Symptom:** When driving forward, kart drifts/tilts right regardless of steering input.  
**Ruled out:** Software (commands show symmetric L/R RPM values).  
**Suspected:** Hardware — one motor is weaker or Spark MAX configs are mismatched between left and right.

### ZED left/right serials swapped in avros sensors.launch.py (2026-10-14)
**Symptom:** the left camera's picture shows up as right and vice versa.  
**Cause:** `avros_bringup/launch/sensors.launch.py` assigns left = 43779087, right = 49910017 (its right serial is marked TODO). Checked from the chair: **left = 49910017, right = 43779087** (front 42569280).  
**Fix:** `relay_teleop/start_all.sh` uses the corrected serials. The IGVC file is unchanged (team code) — the team still needs to fix it.

### ZED won't open after a power cut (2026-10-14)
**Symptom:** `CAMERA MOTION SENSORS NOT DETECTED` / `CAMERA STREAM FAILED TO START` for one camera; the kernel still detects it at boot.  
**Fix order:** `stop_all.sh` + `sudo systemctl restart nvargus-daemon`, then start again. If it still fails, power Marvin fully off and on (that fixed the left ZED), then reseat its GMSL cable. `FRONT_ONLY=1` drives with the front camera meanwhile.

### Jetson loses power
**Symptom:** Marvin drops off Tailscale mid-session; the journal just ends. Happened several times 2026-10-12 to 10-14.  
**Suspected:** 12 V brown-out. Check power first when the link vanishes.

### Raw IMU accel is useless for chair cues on skid-steer (2026-10-14)
Track judder is ~0.8 m/s² (peaks 3–5) while Marvin's real speed changes are ~0.3 m/s², so raw accelerometer made the chair pitch/roll at random and heave buzz. The chair now uses wheel-encoder acceleration and gyro yaw rate; see `windows/dbox/README.md`.

### GStreamer Black Screen
**Symptom:** Windows connects to RTSP server (no 503), pipeline creates on Jetson, but video is black with no frames.  
**Root cause found:** orin_gstreamer_sender.py wasn't being launched with ROS2 environment variables, so it couldn't see ZED topics.  
**Current state:** Thread safety fix applied (GLib.idle_add for push-buffer), correct topic names set, needs full test with proper ROS env launch.

---

## Bugs Fixed This Project

### ZED Camera Crashes
- **Problem:** ZED cameras crash with `BadParameter` EGL error / segfault
- **Cause:** `DISPLAY` set **or** `export DISPLAY=` (empty string still breaks Argus)
- **Fix:** real `unset DISPLAY` on its own line before every ZED launch

### ZED hangs on "Waiting for valid static transformations" (2026-08-04)
- **Symptom:** Node heartbeats, topics advertised, **no image frames** (`hz` silent)
- **Cause:** `publish_tf:=false` / `publish_urdf:=false` while positional tracking enabled; IGVC yaml keeps tracking on
- **Fix:** launch with `publish_tf:=true` `publish_urdf:=true` (and serial + yaml). Fixed `orin_launch_all.sh` includes this.

### Dual ZED stacks fight cameras (2026-08-04)
- **Symptom:** `CAMERA STREAM FAILED TO START` / detection timeout
- **Cause:** IGVC serial-number watchdogs **and** `orin_launch_all` ZEDs both running
- **Fix:** `sudo pkill -f zed_camera.launch.py` then restart Argus; only one stack. `orin_launch_all.sh` preflight now kills leftover ZEDs + restarts Argus.

### Velocity mode no motion / Sparks purple (2026-08-07)
- **Symptom:** Teensy `OK L=1200` but kart doesn't move; Spark LEDs solid purple
- **Cause:** Closed-loop RPM path not producing output; WebUI / duty path works
- **Fix:** Default `orin_vehicle_controller.py` to **`--duty`** (`UL/UR`)

### WebUI dead after Ctrl+C simchair_drive (2026-08-07)
- **Symptom:** Restore said “actuator_node up” but Chrome `:8000` useless
- **Cause:** Only `actuator_node` restarted — not `webui_node` / full service
- **Fix:** `simchair_drive.sh` runs `sudo systemctl restart avros-webui` once on exit

### Dual Teensy owners (2026-08-07)
- **Symptom:** Neither WebUI nor sim chair drives
- **Cause:** `actuator_node` and `orin_vehicle_controller` both on `/dev/ttyACM0`
- **Fix:** Only one owner; launch_all stops WebUI when `SIMCHAIR_DRIVE=1`

### ZED Multi-Camera Crash
- **Problem:** Launching multiple ZED cameras simultaneously crashes Argus daemon
- **Fix:** Launch one at a time with 25 second sleep between each

### Wrong ROS Topic Names
- **Problem:** orin_gstreamer_sender.py subscribed to `/zed_front/zed_node/rgb/image_rect_color` (wrong)
- **Fix:** Correct topic is `/zed_front/zed_node/rgb/color/rect/image`

### Vehicle Control Inversions
- **Throttle/brake inverted:** `(brake - throttle)` → `(throttle - brake)`
- **Steering inverted:** `steering *` → `-steering *`

### OpenCV Windows Not Showing (Windows)
- **Problem:** cv2.namedWindow/imshow called from background threads on Windows
- **Fix:** All OpenCV calls must be on main thread — use Queue to pass frames from threads

### Address Already In Use
- **Problem:** Relaunching scripts fails with port already bound
- **Fix:** `sudo pkill -f <scriptname>` before relaunching

### GStreamer x264enc Profile Error
- **Problem:** `baseline profile doesn't support 4:4:4` 
- **Cause:** BGR input is treated as 4:4:4 by x264enc
- **Fix:** Add `video/x-raw,format=I420` cap between videoconvert and x264enc

### GStreamer nvv4l2h264enc Link Error
- **Problem:** `could not link` error with NVIDIA hardware encoder
- **Cause:** Requires NVMM memory
- **Fix:** Add `nvvidconv ! video/x-raw(memory:NVMM),format=NV12` before encoder

### GStreamer 503 Service Unavailable
- **Problem:** Windows connects before pipeline is ready
- **Fix 1:** Retry loop in windows_gstreamer_receiver.py
- **Fix 2:** Prime appsrc with blank frame on pipeline creation

---

## Architecture Decisions

Mostly from the JPEG era (July–September) and kept as history; the current
video design and why is in [RELAY_TELEOP_2026-10-10.md](RELAY_TELEOP_2026-10-10.md).

### Why JPEG over TCP instead of GStreamer RTSP
GStreamer RTSP (H.264) was attempted repeatedly but produced corrupted bitstreams due to Python thread safety issues with GstRtspServer. JPEG-over-TCP was simpler and worked reliably at 15fps. GStreamer is still being pursued for quality improvement.

### Why Tailscale
Team uses Tailscale for all inter-machine communication. The local router is irrelevant — machines communicate directly over the internet.

### Why ZED compressed topics
The ZED SDK already encodes JPEG internally. Forwarding those bytes directly avoids re-encoding (better quality, less CPU) vs our previous approach of converting BGRA→BGR→resize→JPEG with OpenCV.

### Why sleep 25 for ZED cameras
Automated detection approaches all failed:
- `grep` on tmux output
- `stdbuf` buffering workarounds  
- `tmux capture-pane` (visible only)
- `tmux capture-pane -S -` (full scrollback)
- `ros2 topic list` polling
None were reliable. Hardcoded 25s sleep works every time.

### Why /usr/bin/python3
Conda is installed on the Jetson and intercepts the `python3` command, breaking ROS2 package imports. Full path `/usr/bin/python3` bypasses conda.

---

## Pending Next Steps (Priority Order)

1. **Glass-to-glass outdoors**: a laptop showing `http://100.93.121.3:8090/?clock=1` ~1 m in front of the front ZED (indoors near the chair is a cellular dead spot)
2. **Latency study Step 2**: encoder vbv-size + intra-refresh, viewer `jitterBufferTarget = 0`; A/B against the baselines in MEASUREMENTS.md
3. **Router signal log** during a drive (`windows/latency/router_poll.js`) to tell dead zones from a busy cell
4. **analyze_latency.py**: handle a Jetson clock step (seen 10-16 ~25 min after a reboot) before trusting whole-run queue stats
5. **Motors**: re-check the degradation issue above

---

## Team Constraints

- **NEVER modify files inside `/home/dinosaur/IGVC/`** — shared IGVC competition code
- Windows launch dir: `C:\Users\VRX 226\simchair_teleop\windows\` (git working copy, `main`)
- Jetson teleop dir: `~/SimChair_AVL/` (scp-deployed copy of `jetson/` and the viewer page, not a git clone)
- The team's WebUI launch (`avros_bringup webui.launch.py`) runs its own actuator_node: stop it, with their OK, before `start_all.sh`
