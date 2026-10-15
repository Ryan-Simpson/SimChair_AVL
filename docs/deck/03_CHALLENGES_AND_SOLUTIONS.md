# Challenges and Solutions: Marvin Sim Chair

Solved issues and architecture choices that keep the demo path reliable. Open problems are listed separately at the end.

---

## Solved: Challenge → Root cause → Solution

| Challenge | Root cause | Solution |
|-----------|------------|----------|
| ZED crash / EGL `BadParameter` | `DISPLAY` set, or `export DISPLAY=` (empty string still breaks Argus) | Real `unset DISPLAY` on its own line before every ZED launch |
| ZED hangs: “Waiting for valid static transformations” | `publish_tf:=false` / `publish_urdf:=false` while tracking stays on in IGVC yaml | Launch with `publish_tf:=true` `publish_urdf:=true` (+ serial + yaml) |
| `CAMERA STREAM FAILED TO START` | IGVC ZED watchdogs and teleop ZEDs both owning cameras | `sudo pkill -f zed_camera.launch.py`, restart Argus; only one stack |
| Multi-camera Argus crash | Three ZEDs started at once | Stagger launches with **25 s** sleep between cameras |
| Black / missing OpenCV windows on Windows | `cv2` calls from background threads | Receive on threads; **imshow only on main thread** via queues |
| Wrong / no video from ROS | Subscribed to incorrect topic names | Use `/zed_*/zed_node/rgb/color/rect/image` (+ compressed variant for sender) |
| Throttle/brake and steering felt inverted | Sign error in mix | `(throttle - brake)` and negated steering scale |
| Port already in use on relaunch | Previous process still bound | `sudo pkill -f <script>` before restart |
| GStreamer RTSP unreliable / black frames | Thread-safety with GstRtspServer; env/topic mistakes | Prefer **JPEG**; TCP then **UDP chunked**; GStreamer/RTP secondary |
| Conda breaks ROS Python imports | `python3` points into conda | Always `/usr/bin/python3` on Jetson |
| Velocity cmds ack but no motion | Spark closed-loop / encoder path | Default vehicle controller to **`--duty`** |
| WebUI dead after simchair Ctrl+C | Restored `actuator_node` only | Restart full **`avros-webui`** service |
| Dual Teensy owners | WebUI + vehicle controller | Exclusive ownership; launch_all stops WebUI when driving |

---

## Architecture decisions (why we built it this way)

| Decision | Why |
|----------|-----|
| **JPEG over UDP (chunked)** as primary video | Raises FPS/quality vs TCP 15 fps path; no TCP HOL blocking; stays OpenCV-simple (no GStreamer required) |
| **TCP JPEG kept as fallback** | Proven 2026-08-04 path if UDP/firewall issues |
| **Raw re-encode at 1280×720 q85** | Control resolution/quality independent of ROS compressed downscale |
| **Tailscale for all links** | Works without campus LAN; machines on independent internet |
| **Hardcoded 25 s ZED stagger** | Fixed sleep more reliable than topic-ready polling |
| **Duty-mode drive default** | Velocity setpoints left Sparks purple; UL/UR moves kart |
| **UDP control CSV on :5006** | Low overhead; Jetson watchdog zeros on silence |

**MTU note:** Tailscale MTU is **1280**: UDP JPEG chunks ≤1200 bytes.

---

## Still open (do not present as solved)

| Issue | Symptom | Suspected cause | Next step |
|-------|---------|-----------------|-----------|
| **Motor degradation** | Fine at first launch; later hard to move / unresponsive | Teensy firmware limiter or Spark current limit | A/B with phone-joystick Teensy firmware |
| **Kart tilts right** | Drift/tilt right despite symmetric L/R commands | Hardware / mismatched Spark configs | Compare left vs right Spark parameters |
| **IMU → D-BOX E2E** | Raw IMU accel made the chair pitch/roll at random and buzz | Skid-steer track judder (~0.8 m/s²) swamps real accel (~0.3 m/s²) | Cue from wheel-encoder accel + gyro yaw rate; heave off; fast lean-in, slow release (2026-10-14) |
| **Tailscale DERP** | Often relayed (lax), not direct | NAT/firewall | Aim for **direct** before latency claims |

---

**See also:** [KNOWN_ISSUES_AND_HISTORY.md](../KNOWN_ISSUES_AND_HISTORY.md) · [TARGET_ARCHITECTURE.md](../TARGET_ARCHITECTURE.md)
