# Marvin Sim Chair Teleop

Remote-drive **Marvin**, a Jetson Orin go-kart, from a Windows D-BOX sim chair.
The operator gets three live camera views in a browser, a racing wheel, and
motion cues in the chair. Everything runs over Tailscale through a peer relay,
so it works with Marvin on cellular.

Cal Poly Pomona · Autonomous Vehicles Laboratory (AVL)

**How to start it: [docs/START_TELEOP.md](docs/START_TELEOP.md)**

---

## How it fits together

```
Sim chair PC (Windows, 100.91.25.107)            Marvin (Jetson AGX Orin, 100.93.121.3)
wheel / pedals / D-BOX                           ZED X ×3 · Xsens · Teensy · Spark MAX
                                                 AT&T cellular (Sierra AirLink router)

simchair_sender_dbox.exe --no-dbox
   ── UDP 5006 steer/throttle/brake/gear ──►     orin_simchair_ros_bridge.py
                                                   → /avros/actuator_command → actuator_node → Teensy

Chrome: multicam_viewer.html (:8090)
   ◄── WebRTC (WHEP :8889) ─────────────────     ZED → avros_webrtc (NVENC H.264) → MediaMTX
                                                   rate_controller adapts the bitrate

imu_haptic_receiver.exe → D-BOX
   ◄── UDP 5007 motion cues, 25 Hz ─────────     Xsens + wheel odom → imu_bridge.py

        both ends ⇄ Tailscale peer relay (Vultr LA, 66.42.96.149:4500)
```

## Status (2026-10-16)

| Part | State |
|---|---|
| Drive | Working. Paddle gears: 1 = differential, 2 = Ackermann, 0/3 = off. Arm with park (0). Actuator max 0.40 m/s. |
| Video, 3 cameras | Working over cellular. 480×300; front 7.5 fps, sides 15 fps; adaptive bitrate (0.125–1.8 Mbps). 2026-10-16 late-morning test: 90 min, all 3 cameras, outdoors. |
| IMU → chair | Working, driver-approved 2026-10-14: wheel-encoder accel + speed × yaw + yaw → washout → D-BOX. |
| Cellular | The limit. Night 10–13 Mbps up; busy daytime can drop to ~250 kbps, with occasional 1-minute stalls; dead spots inside the building. If 3 cameras struggle, restart with `FRONT_ONLY=1`. Numbers in [docs/MEASUREMENTS.md](docs/MEASUREMENTS.md). |

## Repo layout

| Path | What it is |
|---|---|
| [`jetson/relay_teleop/`](jetson/relay_teleop/) | Marvin side: `start_all.sh` / `stop_all.sh` and one `run_*.sh` per tmux window |
| `jetson/orin_simchair_ros_bridge.py`, `simchair_ackermann.py` | UDP 5006 → `/avros/actuator_command`, diff / Ackermann mapping |
| `jetson/imu_bridge.py` | Xsens + wheel odom → chair cues, UDP 5007 |
| [`windows/`](windows/) | Chair side: `start_chair.bat`, `simchair_sender_dbox.exe`, `imu_haptic_receiver.exe`, `multicam_viewer.html` |
| [`windows/dbox/`](windows/dbox/) | C++ sources for both exes (CMake, D-BOX SDK) |
| `windows/latency/` | Latency study: log analysis and router signal poller |
| [`docs/`](docs/README.md) | Current docs |
| [`legacy/`](legacy/README.md) | Old JPEG / H.265-era scripts, not used |
| [`docs/archive/`](docs/archive/README.md) | Out-of-date docs, cohort deliverables, poster |

Edit here, then copy changed Jetson files to `~/SimChair_AVL/` on Marvin with
`scp` (same layout; it's a copy, not a git clone). The viewer page is served
from Marvin's copy, so copy `windows/multicam_viewer.html` too.
`windows\dbxLive64.dll` and `SDL2.dll` are not in git; keep them next to the exes.

## Hard rules

1. **One Teensy owner.** The relay stack starts its own `actuator_node`. If the team's WebUI launch (`avros_bringup webui.launch.py`) is running, it has one too: stop it first, with the team's OK.
2. **One viewer.** Every extra viewer tab sends the video again over the cellular upload.
3. **Don't edit `/home/dinosaur/IGVC/`** (team code).
4. **Physical E-stop latches the Spark MAXes.** A software restart won't clear it.

## Team

Ryan Simpson (lead), Tyler Carrasco, Yi-Szen Tang, Kevin Xu, Justin Dang
Mentor: Dr. Behnam Bahr
