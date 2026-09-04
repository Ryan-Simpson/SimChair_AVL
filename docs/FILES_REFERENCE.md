# Files Reference

**Updated:** 2026-08-07

## Layout (Windows workspace)

```
C:\Users\VRX 226\cursor-test\
  windows\       ← launch Windows apps from here
  jetson\        ← mirrors of Jetson teleop scripts (edit here, push to Marvin)
  CARS_Poster\   ← symposium poster / Canva pack
  docs\          ← these docs
  _archive\      ← old mirrors / experiments (not day-to-day)
  LAUNCH.txt     ← short cheat sheet
```

Jetson live copies: `~/Documents/SimChair_Teleop/`  
C++ / D-BOX SDK archive: `C:\Users\VRX 226\Test Workspace\`  
Legacy Windows runtime: `C:\Users\VRX 226\test\` (prefer `cursor-test\windows\`)

---

## Windows runtime (`cursor-test\windows\`)

| File | Purpose | Status |
|------|---------|--------|
| `simchair_sender_dbox.exe` | Wheel/pedals → UDP 5006; D-BOX from inputs | Working |
| `dbxLive64.dll` / `SDL2.dll` | Required next to the exe | Required |
| `windows_camera_receiver_udp.py` | Chunked JPEG/UDP 9001–9003 → 3 monitors | **Primary path** |
| `windows_camera_receiver.py` | JPEG/TCP 9001–9003 → 3 monitors | Legacy fallback |
| `windows_zed_stream_receiver.py` | ZED SDK stream | Experimental |
| `windows_gstreamer_rtp_receiver.py` | RTP/UDP H.264 | Experimental |
| `windows_control_status.py` | UDP 5008 link status | Working |
| `windows_imu_washout_test.py` | Haptics bench / washout test | Working |
| `windows_haptic_receiver.py` | IMU washout console | Working |
| `start_all.bat` | One-shot launcher (`VIDEO_MODE=udp` default) | Working |

---

## Jetson teleop (`~/Documents/SimChair_Teleop/` ↔ `cursor-test\jetson\`)

| File | Purpose | Status |
|------|---------|--------|
| `orin_launch_all.sh` | Full stack in tmux `teleop` | **Primary** — UDP cams + `--duty` drive by default |
| `orin_camera_sender_udp.py` | ZED → chunked JPEG/UDP → Windows | **Primary video** |
| `orin_camera_sender.py` | ZED → JPEG/TCP 9001–9003 | Legacy (`CAMERA_TRANSPORT=tcp`) |
| `orin_vehicle_controller.py` | UDP 5006 → Teensy; default `--duty` | Working |
| `imu_bridge.py` | IMU → Windows UDP 5007 @ 50 Hz | Working script |
| `simchair_drive.sh` | Borrow Teensy; restart `avros-webui` on exit | Working |
| `cam_probe.py` | Camera probe utility | Optional |

Superseded scripts under `_archive\experiments\` (old GStreamer senders, etc.).

---

## Key code notes

### orin_vehicle_controller.py

- UDP **5006**, status UDP **5008** → `100.91.25.107`  
- Serial `/dev/ttyACM0` @ 115200, stream **50 Hz**  
- Default drive mode **duty** (`UL/UR`); use `--velocity` for L/R RPM  
- Stops with `L0 R0` / `UL0 UR0` — **never send `S`**  
- UDP latch ~2.5 s → watchdog stop; N then D to re-arm  

### orin_camera_sender_udp.py

- Ports: left **9001**, front **9002**, right **9003** (UDP)  
- Chunk protocol: magic `MJPG` + frame_id + chunk_idx/num + ≤1200 B payload  
- Defaults: **1280×720**, **30 fps**, JPEG **q=85**, prefer raw re-encode  
- `--prefer-compressed` forwards ROS compressed JPEG (lighter CPU)  
- `--windows-ip` default `100.91.25.107`  

### orin_camera_sender.py (legacy TCP)

```python
TARGET_FPS = 15
JPEG_QUALITY = 70  # when re-encoding raw
```

### imu_bridge.py

- Packet 44 bytes LE: `seq:u32, t_ms:u64, ax,ay,az,gx,gy,gz,roll,pitch`  
- Default Windows IP `100.91.25.107`, port **5007**  

### ZED launch requirements

1. `unset DISPLAY` (not empty `DISPLAY=`)  
2. `publish_tf:=true` and `publish_urdf:=true`  
3. Serial numbers + IGVC yaml overrides  
4. Do not run launch_all ZEDs **and** IGVC ZED watchdogs at once  

| Camera | Serial |
|--------|--------|
| front | 42569280 |
| left | 49910017 |
| right | 43779087 |

### start_all.bat

| `VIDEO_MODE` | Receiver |
|--------------|----------|
| `udp` (default) | `windows_camera_receiver_udp.py` |
| `jpeg` | `windows_camera_receiver.py` (TCP) |
| `zed` / `rtp` | experimental |

### D-BOX SDK (C++)

See `C:\Users\VRX 226\Test Workspace\2026_Sim_Chair\`  
`APP_KEY = "CalPolyPomonaDevSim"`, streaming ~50 Hz.
