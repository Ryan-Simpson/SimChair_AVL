# Known Issues, History, and Lessons Learned

## What's Working

| Feature | Status | Notes |
|---------|--------|-------|
| Sim chair wheel/pedal input | ✅ Working | simchair_sender_dbox.exe via SDL2 |
| UDP control to Jetson | ✅ Working | Port 5006, Tailscale |
| Vehicle controller → Teensy | ✅ Working | Default **`--duty`** (`UL/UR`); WebUI also drives |
| JPEG camera streaming | ✅ Working | UDP chunked JPEG 9001–9003; **do not run with H.265** |
| ZED H.265 front stream | ✅ Working | Ports 30000; `py -3.8` receiver; good FPS if link clean |
| ZED H.265 ×3 over Tailscale | ⚠️ Fragile | Unique ports OK; corrupt chunks / freezes under drive |
| Wheel via ROS bridge | ✅ Working | `--ros-drive` / `simchair_launch_clean.sh`; close Chrome stick |
| D-BOX SDK integration | ✅ Working | DBoxManager class, async streaming |
| ZED camera launch | ✅ Working | Owned by **percept-stack**; do not dual-launch |
| WebUI restore after sim chair | ✅ Working | Restart full `avros-webui` service |

## What's In Progress

| Feature | Status | Blocker |
|---------|--------|---------|
| Stable 3-cam teleop video | 🔄 Open | See `FRESH_CHAT_VIDEO_PROMPT.md` — Tailscale + ZED native ×3 |
| GStreamer H.264 / H.265 / WebRTC | 🔄 Candidate | Alternative to ZED native for lossy links |
| D-BOX ↔ IMU integration | 🔄 Script ready | `imu_bridge.py` → UDP 5007; E2E chair cueing needs demo verify |
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

1. **Motors** — re-verify spin / Spark / meas RPM (WebUI + sim-chair)
2. **IMU → D-BOX end-to-end** — `imu_bridge` exists; confirm chair motion from vehicle IMU
3. **Video quality** — JPEG works; optional `pub_downscale_factor:=1.0` / HD for stills; H.265 later
4. **Latency measurement** — target under 150ms glass-to-glass when on direct Tailscale
5. **Keep docs/scripts in sync** — edit in `cursor-test\jetson\`, push to `~/Documents/SimChair_Teleop/`

---

## Team Constraints

- **NEVER modify files inside `/home/dinosaur/IGVC/`** — shared IGVC competition code
- Windows launch dir: `C:\Users\VRX 226\cursor-test\windows\` (legacy: `test\`)
- Jetson teleop dir: `~/Documents/SimChair_Teleop/`
- iptables rules don't persist across reboots — must re-run every session (or use `orin_launch_all.sh`; opens TCP+UDP 9001–9003)
- SCP/SSH key may be missing — use Tailscale HTTP (`python -m http.server`) to move files
