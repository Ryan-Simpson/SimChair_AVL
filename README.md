# Marvin Sim Chair Teleop

Remote-drive **Marvin**, a Jetson Orin go-kart, from a Windows D-BOX sim chair. The operator gets three camera views, a racing wheel, and motion cueing — over Tailscale, without taking over the car’s perception stack.

Cal Poly Pomona · Autonomous Vehicles Laboratory (AVL)

---

## How it fits together

```
Sim chair (Windows)                         Marvin (Jetson Orin)
wheel / pedals / D-BOX                      ZED X ×3 · Teensy · Spark MAX
        │                                            │
        │  UDP 5006  steer / throttle / brake        │
        ├──────────────────────────────────────────►│  ROS → /avros/actuator_command
        │                                            │
        │  H.265 30000  (front)                      │
        │  JPEG  9001–9003  (fallback)               │
        │◄──────────────────────────────────────────┤  percept-stack owns cameras
        │                                            │
        │  UDP 5007  IMU → chair                     │
        │◄──────────────────────────────────────────┘
```

The car already runs `percept-stack` (cameras, Argus, costmap) and WebUI. This repo **attaches** to that stack. It does not relaunch ZEDs.

| | Operator station | Vehicle |
|---|---|---|
| Host | Windows sim chair `100.91.25.107` | Jetson Orin `dinosaur` `100.93.121.3` |
| Input | Thrustmaster wheel + pedals | Teensy 4.1 → Spark MAX |
| Video | Three monitors (Surround 0 / 1920 / 3840) | ZED X front / left / right |
| Motion | D-BOX chair | Xsens IMU |

---

## Status

| Path | State |
|------|--------|
| Wheel → ROS → motors | Working. Use `--ros-drive`. Close the Chrome stick. |
| Front H.265 (ZED native) | Working. Best picture so far. |
| Three H.265 streams over Tailscale | Opens, then freezes / smears under load. Do not use for demos. |
| JPEG/UDP ×3 | Stable-ish with percept up. Softer image. Fallback only. |
| IMU → D-BOX | Bridge exists. End-to-end chair feel still needs a live check. |

**Do not** run JPEG and H.265 at the same time. **Do not** run `orin_launch_all.sh` while percept is up.

---

## Quick start

Confirm Tailscale is **direct** (`tailscale ping 100.93.121.3`), not a DERP relay.

### Jetson

```bash
conda deactivate
unset ROS_DOMAIN_ID DISPLAY
source /opt/ros/humble/setup.bash
source /home/dinosaur/IGVC/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml

bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --front-only
bash ~/Documents/SimChair_Teleop/simchair_attach.sh --ros-drive --no-cam
```

### Windows (Command Prompt, not PowerShell)

```bat
cd /d "C:\Users\VRX 226\simchair_teleop\windows"
set VIDEO_MODE=zed
start_all.bat
```

Mode **0** = park, **1** = drive.

JPEG fallback: omit `VIDEO_MODE` and run `simchair_attach.sh --ros-drive` (no `--no-cam`). Never mix that with H.265.

### Stop (leave the car healthy)

```bash
tmux kill-session -t simchair 2>/dev/null || true
pkill -f orin_simchair_ros_bridge 2>/dev/null || true
bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --off
```

Physical E-stop latches the Spark MAXes. A software restart will not clear it.

---

## Repo layout

| Path | What it is |
|------|------------|
| [`windows/`](windows/) | Runtime on the sim chair. Launch from here (`start_all.bat`). |
| [`jetson/`](jetson/) | Scripts mirrored to `~/Documents/SimChair_Teleop/` on the kart. |
| [`docs/`](docs/) | Ops notes, architecture, handoff. |
| [`CARS_Poster/`](CARS_Poster/) | Symposium poster materials. |
| [`_archive/`](_archive/) | Old experiments. Not day-to-day. |

Edit Jetson scripts here, then copy them to the kart (HTTP from the Windows tree is the usual path if SSH keys are missing).

---

## Hard rules

1. **`percept-stack` owns the cameras.** Attach only. Never `orin_launch_all.sh` while it is running.
2. **One Teensy owner.** Prefer `actuator_node` via `--ros-drive`. Do not also run `orin_vehicle_controller`.
3. **Car ROS domain is 0.** `unset ROS_DOMAIN_ID` — bashrc often injects `42`.
4. **One video path.** H.265 *or* JPEG, never both.
5. **Do not edit `/home/dinosaur/IGVC/`** unless the lab agrees. Stream ports already live in the ZED yaml.
6. **Do not kill** percept tmux `costmap_rgb`. Killing `rviz` / `viz` for bandwidth is fine.

---

## Docs

Start with the live map, then go deeper as needed:

- [Session handoff](docs/SESSION_HANDOFF_CONTEXT_LOSS.md) — current paths, ports, open issues
- [Percept + sim chair](docs/PERCEPT_STACK_AND_SIMCHAIR.md) — attach vs launch, WebUI, Teensy
- [H.265 bring-up](docs/H265_BRINGUP.md) — ZED native streams
- [Video architecture prompt](docs/FRESH_CHAT_VIDEO_PROMPT.md) — why 3-cam Tailscale fails; next design
- [Known issues](docs/KNOWN_ISSUES_AND_HISTORY.md) — what we already tried
- [All docs](docs/README.md)

`LAUNCH.txt` at the repo root is the short ops cheat sheet.

---

## Team

Ryan Simpson (lead), Tyler Carrasco, Yi-Szen Tang, Kevin Xu, Justin Dang  
Mentor: Dr. Behnam Bahr
