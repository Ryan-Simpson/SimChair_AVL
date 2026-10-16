# H.265 / ZED Native Stream Bring-Up

**Updated:** 2026-09-04  
**Goal:** ZED SDK **H.265 NVENC** teleop video **without** killing `percept-stack`.

**Status:** Front H.265 works. 3× H.265 over Tailscale still lossy (corrupt chunks / freezes).  
**Never** run JPEG `orin_camera_sender` at the same time as H.265.  
**Design next step:** [FRESH_CHAT_VIDEO_PROMPT.md](FRESH_CHAT_VIDEO_PROMPT.md)

JPEG path stays fallback (`windows_camera_receiver_udp.py` + `orin_camera_sender_udp.py`).

---

## Why this

| | JPEG/UDP (today) | H.265 NVENC (target) |
|--|------------------|----------------------|
| Encode | CPU JPEG ×3 | Orin hardware NVENC |
| Bandwidth | High for soft 720p | ~4–8 Mbps/cam at HD |
| With percept up | Raw 720p×3 can crash Orin | Encoder offloads CPU |
| Quality | Blocky if bitrate-limited | Much sharper at same link |

Reference: [TARGET_ARCHITECTURE.md](TARGET_ARCHITECTURE.md) §2 · Stereolabs local streaming docs.

---

## Architecture (coexist with percept)

```
ZED nodes (already owned by percept-stack)
  → NVENC H.265 stream_server  UDP ports 30000 / 30004 / 30008
       → Tailscale → Windows pyzed (windows_zed_stream_receiver.py)
```

**Do not** run `orin_launch_all.sh` or a second ZED stack.  
**Do** enable streaming on the **existing** `/zed_*/zed_node` nodes.

Ports (match `windows_zed_stream_receiver.py`):

| Camera | Stream port |
|--------|-------------|
| Front  | 30000 |
| Left   | 30004 |
| Right  | 30008 |

---

## Phase 0 — Windows prerequisites (do first)

1. Install **ZED SDK for Windows** from Stereolabs (CUDA build matching your GPU).
2. Install **pyzed** for the Python you use to run receivers (not random conda env).
3. Verify:
```powershell
python -c "import pyzed.sl as sl; print('pyzed OK')"
```
4. Confirm Tailscale: `ping 100.93.121.3`

**Status 2026-08-27:** `pyzed` was **not** importable on the sim-chair PC (`ModuleNotFoundError`). Phase 1 Jetson work can proceed; Windows receive waits on SDK/pyzed.

---

## Phase 1 — Jetson: discover + open firewall + enable front only

Copy `jetson/simchair_enable_zed_streams.sh` to the kart, then:

```bash
# conda off + Cyclone (same as WebUI)
conda deactivate
unset ROS_DOMAIN_ID DISPLAY
source /opt/ros/humble/setup.bash
source /home/dinosaur/IGVC/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
ros2 daemon stop; ros2 daemon start

# See streaming-related services/params
bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --discover

# Firewall + enable FRONT only (safest first test)
bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --front-only
```

If services are missing, percept’s ZED launch may need `stream_server` params in yaml (ask before editing IGVC). Snippet:

```yaml
stream_server:
  stream_enabled: false   # we enable at runtime
  codec: 'H265'
  bitrate: 6000
  gop_size: 15
  adaptative_bitrate: false
  chunk_size: 1200
  port: 30000             # unique per camera
  target_framerate: 30
```

---

## Phase 2 — Windows: receive front only

```powershell
cd "C:\Users\VRX 226\simchair_teleop\windows"
python windows_zed_stream_receiver.py --front-only
```

Success = one sharp window. Failure = fall back to JPEG:
```powershell
python windows_camera_receiver_udp.py
```

If you see `POTENTIAL CALIBRATION ISSUE`: that is an SDK soft warning (poor factory cal for depth). The receiver treats it as OK for RGB-only teleop. Re-run after pulling the latest `windows_zed_stream_receiver.py`. If open still hard-fails, re-enable the Jetson stream (`--front-only`) and retry.

---

## Phase 3 — All three cameras

```bash
bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --all
```
```powershell
python windows_zed_stream_receiver.py
# or: $env:VIDEO_MODE='zed'; .\start_all.bat
```

Keep sim-chair drive as today:
```bash
bash ~/Documents/SimChair_Teleop/simchair_attach.sh --ros-drive
# skip JPEG cam_sender if H.265 video is primary — or run attach without fighting bandwidth
```

---

## Phase 4 — Measure + decide primary

Fill [MEASUREMENTS.md](MEASUREMENTS.md) Phase 1b:

- Resolution / FPS per cam  
- Glass-to-glass median (phone stopwatch)  
- Task Manager bitrate  
- Orin stability with percept + streams (30+ min)

If stable and sharper → H.265 primary, JPEG fallback.  
If flaky over Tailscale → try LAN IP profile; else keep JPEG for demos.

---

## Kill / disable streams (leave percept up)

```bash
bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --off
```

Does **not** stop `percept-stack` or WebUI.

---

## Risks

| Risk | Mitigation |
|------|------------|
| NVENC + perception YOLO fights GPU | Front-only first; lower bitrate 4000 |
| Dual ZED stacks | Never `orin_launch_all` for this |
| Tailscale MTU | `chunk_size: 1200` |
| No pyzed on Windows | Phase 0 before claiming success |
| `enable_streaming` absent | Need yaml `stream_server` from IGVC/percept owners |
| Freezes / tearing on 3 cams over Tailscale | `chunk_size` must be **≤ ~1024** (Tailscale MTU ~1280). Use `patch_zed_stream_3cam_stable.sh`. Prefer Tailscale **direct** peer (not DERP). Receiver: `--native-size` (don’t upscale SVGA→1080). |
| `ROS_DOMAIN_ID=42` → Node not found | `unset ROS_DOMAIN_ID` + Cyclone URI (same as enable script); car stack is not domain 42 |

---

## File map

| File | Role |
|------|------|
| `jetson/simchair_enable_zed_streams.sh` | Discover / firewall / enable / disable |
| `windows/windows_zed_stream_receiver.py` | pyzed H.265 receive |
| `windows/windows_camera_receiver_udp.py` | JPEG fallback |
| `docs/TARGET_ARCHITECTURE.md` | Design rationale |
