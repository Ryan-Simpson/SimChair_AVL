# Session handoff / current map

**Updated:** 2026-09-04  
Prefer live checks on Jetson/Windows. This is a memory map, not gospel.

**Fresh-chat design prompt:** [FRESH_CHAT_VIDEO_PROMPT.md](FRESH_CHAT_VIDEO_PROMPT.md)

---

## Paths

| Role | Path |
|------|------|
| Windows **runtime** | `C:\Users\VRX 226\simchair_teleop\windows` |
| Jetson script mirror (edit on Windows) | `C:\Users\VRX 226\simchair_teleop\jetson` |
| Docs | `C:\Users\VRX 226\simchair_teleop\docs` |
| Jetson live teleop | `~/Documents/SimChair_Teleop/` |
| Jetson IGVC | `/home/dinosaur/IGVC/` — **ask before editing** (stream ports were edited in `avros_bringup` config) |
| Percept stack | `carla-nav2-avl` → `percept-stack.service` / tmux `-L percept` |

Quick entry: `C:\Users\VRX 226\simchair_teleop\LAUNCH.txt`

IPs: Jetson Tailscale **100.93.121.3**, Windows **100.91.25.107**.

---

## Hard rules

1. **`percept-stack` always owns ZEDs/Argus/sensors.** Never `orin_launch_all.sh` while it is up.
2. **One Teensy owner:** `actuator_node` (WebUI) **or** legacy `orin_vehicle_controller` — never both.
3. **Preferred drive:** `--ros-drive` / `orin_simchair_ros_bridge.py` → `/avros/actuator_command` (WebUI stays up). Close Chrome stick while using wheel.
4. **Car ROS domain is 0.** Shell often has `ROS_DOMAIN_ID=42` from bashrc — `unset ROS_DOMAIN_ID` + Cyclone URI or nodes look “missing.”
5. **Never JPEG cam_sender + ZED H.265 at the same time** — saturates Tailscale (~100 MiB/s) and melts FPS.
6. **Do not kill `costmap_rgb`** tmux window — crashed the Jetson. Safe to kill only `rviz` + `viz` for teleop bandwidth.

---

## What works (verified 2026-08/09)

| Piece | Status |
|-------|--------|
| WebUI stick | `avros-webui` → `actuator_node` → Teensy; restart full service if “Disconnected” |
| Wheel via ROS | `simchair_attach.sh --ros-drive` or `simchair_launch_clean.sh` |
| ZED H.265 front | Works; good FPS when link not overloaded |
| ZED H.265 ×3 | Opens after unique ports in yaml; **unstable over Tailscale** (corrupt chunks / freezes) |
| Windows ZED recv | `py -3.8 windows_zed_stream_receiver.py --native-size` (`VIDEO_MODE=zed` in **cmd**: `set VIDEO_MODE=zed`) |
| Unique stream ports | `zed_front.yaml` 30000, `zed_left` 30004, `zed_right` 30008 under `avros_bringup/config` (ports **read-only at runtime**) |

---

## Video paths (pick ONE)

| Mode | Jetson | Windows |
|------|--------|---------|
| **H.265 (preferred quality)** | `simchair_enable_zed_streams.sh --all` or `--front-only`; **no** JPEG sender | `VIDEO_MODE=zed` / `windows_zed_stream_receiver.py` |
| **JPEG/UDP (fallback)** | `simchair_attach.sh` cam_sender (compressed default) | `windows_camera_receiver_udp.py` / default `start_all.bat` |
| **Clean teleop one-shot** | `simchair_launch_clean.sh` (H.265 + wheel, no JPEG) | `set VIDEO_MODE=zed` then `start_all.bat` |

Tailscale MTU ~1280 → ZED `stream_server.chunk_size` must be small (**1024** via `patch_zed_stream_3cam_stable.sh`). Default ~16084 / 4096 → `Corrupted frame chunk` / freezes.

Cameras are **SVGA** in percept yaml — soft when upscaled to 1080p; bitrate ≠ resolution.

---

## Ports

| Port | Use |
|------|-----|
| 8000 TCP | WebUI HTTPS |
| 5006 UDP | Sim-chair drive |
| 5007 UDP | IMU haptics |
| 5008 UDP | Status |
| 9001–9003 UDP | JPEG cameras |
| **30000 / 30004 / 30008 UDP** | ZED H.265 front / left / right |

---

## Percept tmux (`tmux -L percept`)

Typical windows: `sensors`, `ekf`, `zed_front/left/right`, `costmap`, `viz`, `rviz`, `wvs`, `www`, `costmap_rgb`.

- Teleop bandwidth relief: kill **`rviz`** + **`viz`** only.
- Restore normal lab: `sudo systemctl restart percept-stack` (recreates windows).

---

## Open problems / next design

1. **3× H.265 over Tailscale** still freezes/smears under drive (packet loss). Front-only is stable enough to demo.
2. Disk was **~94% full** (`IGVC/bags` ~686 GB) — causes system lag; clean bags when possible.
3. NoMachine Free = 1 session; heavy with RViz + streams.
4. Physical E-stop kills Sparks — must release hardware; WebUI/actuator restart does not clear a latched E-stop.
5. Best long-term video architecture still open → use **FRESH_CHAT_VIDEO_PROMPT.md**.

---

## Restore perception + WebUI (leave lab healthy)

```bash
tmux kill-session -t simchair 2>/dev/null || true
pkill -f orin_simchair_ros_bridge 2>/dev/null || true
pkill -f orin_camera_sender 2>/dev/null || true
bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --off 2>/dev/null || true
sudo systemctl restart percept-stack
sudo systemctl restart avros-webui
# wait 2–3 min
systemctl is-active percept-stack avros-webui
tmux -L percept list-windows -t percept
```

Hard-refresh `https://100.93.121.3:8000`.

---

## Sync scripts Windows → Jetson

```bat
cd /d "C:\Users\VRX 226\simchair_teleop\jetson"
py -3 -m http.server 8765
```
```bash
cd ~/Documents/SimChair_Teleop
curl -O http://100.91.25.107:8765/simchair_launch_clean.sh
sed -i 's/\r$//' simchair_launch_clean.sh && chmod +x simchair_launch_clean.sh
```
