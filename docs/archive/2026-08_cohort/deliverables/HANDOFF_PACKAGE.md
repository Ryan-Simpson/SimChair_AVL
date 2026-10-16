# Codebase & Handoff Documentation: Marvin Sim Chair

**AVL Summer Cohort 2026 final deliverable**  
**Updated:** 2026-08-07  
**Audience:** next AVL operators, mentors, and AI sessions continuing this work

This package covers repository structure, setup instructions, known issues, and future recommendations. Authoritative ops detail remains in the linked docs under `docs/`.

---

## 1. Repository structure

```
C:\Users\VRX 226\cursor-test\
├── LAUNCH.txt                 Short cheat sheet
├── windows\                   Windows runtime: LAUNCH FROM HERE
│   ├── simchair_sender_dbox.exe
│   ├── dbxLive64.dll / SDL2.dll
│   ├── windows_camera_receiver_udp.py  ← PRIMARY video (UDP JPEG)
│   ├── windows_camera_receiver.py      ← legacy TCP JPEG
│   ├── windows_zed_stream_receiver.py  ← experimental
│   ├── windows_gstreamer_rtp_receiver.py
│   ├── windows_control_status.py
│   ├── windows_imu_washout_test.py
│   ├── start_all.bat                   ← VIDEO_MODE=udp default
│   └── requirements.txt
├── jetson\                    Mirror of Jetson teleop scripts
│   ├── orin_launch_all.sh              ← full stack (UDP cams + --duty)
│   ├── orin_camera_sender_udp.py       ← PRIMARY video
│   ├── orin_camera_sender.py           ← legacy TCP
│   ├── orin_vehicle_controller.py      ← default --duty
│   ├── imu_bridge.py
│   └── simchair_drive.sh               ← restores full avros-webui
├── docs\                      Full documentation
│   ├── deliverables\          ← THIS cohort submission pack
│   ├── deck\                  Section briefs
│   ├── LAUNCH_PROCEDURE.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── KNOWN_ISSUES_AND_HISTORY.md
│   ├── MEASUREMENTS.md
│   ├── TARGET_ARCHITECTURE.md
│   └── ...
├── CARS_Poster\               Symposium poster / Canva pack
└── _archive\                  Old mirrors / experiments: not day-to-day
```

**Live Jetson path:** `~/Documents/SimChair_Teleop/` (keep in sync with `cursor-test\jetson\`)  
**IGVC (read-only):** `/home/dinosaur/IGVC/`: **never modify**  
**C++ / D-BOX sources (external):** `C:\Users\VRX 226\Test Workspace\`

### Network identity

| Machine | Tailscale IP |
|---------|--------------|
| Windows sim-chair | `100.91.25.107` |
| Jetson dinosaur | `100.93.121.3` |

### Ports

| Port | Proto | Role |
|------|-------|------|
| 5006 | UDP | Control Windows → Jetson |
| 5007 | UDP | IMU Jetson → Windows |
| 5008 | UDP | Status Jetson → Windows |
| 9001-9003 | **UDP** | Chunked JPEG video (primary) |
| 9001-9003 | TCP | JPEG video (legacy fallback) |

---

## 2. Setup instructions

### 2.1 One-time / environment

**Windows**

1. Install Python 3 + `pip install -r windows\requirements.txt` (`opencv-python`, `numpy`)  
2. ZED SDK / GStreamer only if using experimental video modes  
3. Confirm Tailscale connected; three monitors in Surround (offsets 0 / 1920 / 3840)  
4. Thrustmaster drivers + D-BOX LiveMotion with APP_KEY `CalPolyPomonaDevSim`  
5. DLLs (`dbxLive64.dll`, `SDL2.dll`) must sit next to `simchair_sender_dbox.exe`

**Jetson**

1. ROS 2 Humble + IGVC install already present under `/home/dinosaur/IGVC/`  
2. Teleop scripts in `~/Documents/SimChair_Teleop/`  
3. Tailscale connected  
4. Use `/usr/bin/python3` (conda hijacks `python3`)

### 2.2 Every session: current demo path

**Jetson**

```bash
bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
```

Preflight clears ZED contention + restarts Argus. Starts tmux `teleop`: firewall (TCP+UDP 9001-9003), sensors, ZEDs, **UDP camera sender**, vehicle **`--duty`**, IMU bridge. Stops WebUI while driving.

Stop: `tmux kill-session -t teleop` then `sudo systemctl start avros-webui`

**Windows**

```powershell
cd "C:\Users\VRX 226\cursor-test\windows"
.\start_all.bat
# default VIDEO_MODE=udp → windows_camera_receiver_udp.py
# TCP fallback:  $env:VIDEO_MODE = "jpeg"; .\start_all.bat
```

### 2.3 ROS 2 env (any Jetson terminal touching ROS)

```bash
unset DISPLAY
source /home/dinosaur/IGVC/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
export ROS_DOMAIN_ID=42
```

ZED launch must use `publish_tf:=true` `publish_urdf:=true` and real `unset DISPLAY` (never `export DISPLAY=`).

### 2.4 Sync scripts after edits

Edit in `cursor-test\jetson\`, then copy to `~/Documents/SimChair_Teleop/` on Marvin (SCP or Tailscale HTTP file server if keys missing).

Full procedure: [`../LAUNCH_PROCEDURE.md`](../LAUNCH_PROCEDURE.md) · root [`../../LAUNCH.txt`](../../LAUNCH.txt)

---

## 3. Known issues

### Working

- Sim-chair wheel/pedal → UDP → Teensy (`--duty`)  
- Three-camera **UDP** JPEG streaming (2026-08-07); TCP path kept as fallback  
- D-BOX SDK integration on Windows  
- ZED multi-cam launch with stagger + TF flags  
- `simchair_drive.sh` restores full `avros-webui`  

### Open

| Issue | Notes |
|-------|-------|
| Velocity / closed-loop drive | Often Sparks purple; use `--duty` |
| Motor degradation after sustained use | Suspect Teensy firmware / Spark limits |
| Kart tilts/drifts right | Suspect hardware / Spark config mismatch |
| IMU → D-BOX end-to-end | `imu_bridge.py` ready; chair cueing not demo-verified |
| Tailscale often DERP not direct | Hurts latency budget |
| Glass-to-glass / bandwidth | Still TBD in measurements |
| iptables not persistent | Re-apply each boot (or use launch_all) |

### Do not regress (lessons learned)

- Real `unset DISPLAY` before ZED  
- TF/URDF true or no image frames  
- One ZED stack only; 25 s stagger  
- OpenCV main thread on Windows  
- `/usr/bin/python3` on Jetson  
- Never send Teensy `S` stop: use `UL0 UR0` / `L0 R0`  
- Only one Teensy owner; restore **full** WebUI service after sim chair  
- Never write inside `/home/dinosaur/IGVC/`  

Full history: [`../KNOWN_ISSUES_AND_HISTORY.md`](../KNOWN_ISSUES_AND_HISTORY.md)

---

## 4. Future recommendations

Priority order:

1. **Motors**: A/B Teensy firmware; verify meas RPM; fix right-tilt Spark configs  
2. **Haptics E2E**: live IMU → washout → D-BOX; ramp to neutral on packet loss  
3. **Video**: H.265 NVENC / RTP next; keep UDP JPEG as fallback  
4. **Latency**: Tailscale direct; glass-to-glass &lt;150 ms median  
5. **Control hardening**: seq + timestamps, 50 Hz, 300 ms latched STOPPED, Teensy silence watchdog  
6. **Ops**: systemd units, iptables-persistent, cold-boot without manual tmux  
7. **Soak**: ≥30 min simultaneous video + control + haptics  

Roadmap detail: [`../TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) · metrics log: [`../MEASUREMENTS.md`](../MEASUREMENTS.md)

---

## 5. File roles (quick)

| File | Purpose |
|------|---------|
| `simchair_sender_dbox.exe` | Wheel/pedals + D-BOX sender |
| `windows_camera_receiver_udp.py` | Primary UDP JPEG display |
| `windows_camera_receiver.py` | Legacy TCP JPEG display |
| `orin_launch_all.sh` | Full Jetson teleop stack |
| `orin_vehicle_controller.py` | UDP → Teensy (default `--duty`) |
| `orin_camera_sender_udp.py` | Primary UDP JPEG sender |
| `orin_camera_sender.py` | Legacy TCP JPEG sender |
| `imu_bridge.py` | IMU → UDP 5007 @ 50 Hz |
| `simchair_drive.sh` | Borrow Teensy; restart `avros-webui` |

Inventory: [`../FILES_REFERENCE.md`](../FILES_REFERENCE.md)

---

## 6. Safety & constraints for next operators

1. Spotter at the kart for any powered demo  
2. Start in stop mode; enable drive only when clear  
3. Prefer stands for early motor tests  
4. Sim-chair and Chrome WebUI must not both own `/dev/ttyACM0`  
5. Reliability beats new features for demos  

AI/operator mission context: [`../HANDOFF_GUIDE.md`](../HANDOFF_GUIDE.md)

---

## 7. Cohort deliverables cross-links

| Deliverable | Path |
|-------------|------|
| Technical report | [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md) |
| Slide deck (Marp) | [SLIDE_DECK.md](SLIDE_DECK.md) |
| Slide deck (HTML) | [slide_deck.html](slide_deck.html) |
| Demo video script | [DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md) |
| Demo video file | Record → `DEMO_VIDEO.mp4` (not in repo until filmed) |
| This handoff | [HANDOFF_PACKAGE.md](HANDOFF_PACKAGE.md) |
