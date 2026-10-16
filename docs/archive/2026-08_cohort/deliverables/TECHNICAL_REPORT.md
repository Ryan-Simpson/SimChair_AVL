# Haptic Sim-Chair-Based Teleoperation System for Autonomous Vehicle Platforms

**AVL Summer Cohort 2026: Written Technical Report**

**Authors:** Ryan Simpson, Tyler Carrasco, Yi-Szen Tang, Kevin Xu, Justin Dang  
**Faculty Mentor:** Dr. Behnam Bahr  
**Affiliation:** Autonomous Vehicles Laboratory (AVL), California State Polytechnic University, Pomona (CPP)  
**Date:** August 7, 2026

---

## Abstract

Remote operation of ground vehicles presents fundamental challenges in situational awareness. An operator who is not physically present loses sensory feedback that enables precise and confident driving, including peripheral vision and the perception of acceleration. Conventional teleoperation systems provide only a flat video feed, which limits effectiveness in hazardous-environment operations and safety intervention for autonomous vehicles.

The Cal Poly Pomona Autonomous Vehicles Lab has developed a bidirectional haptic teleoperation system that restores this missing feedback. The test platform, a go-kart named Marvin, carries three Stereolabs ZED X stereo cameras and an Xsens MTi-680G IMU, managed by an onboard NVIDIA Jetson Orin. The operator is seated in a D-BOX motion-enabled simulation chair fitted with a Thrustmaster racing wheel and pedals, facing three monitors arranged to reproduce a driver’s natural field of view. Steering and pedal inputs are transmitted to the vehicle in real time over a Tailscale VPN, while vehicle accelerations are intended to drive the motion chair so the operator experiences forces acting on the vehicle.

As of this report, remote driving control and live three-camera JPEG video are verified operational. The IMU-to-chair haptic path has a software bridge in place and requires end-to-end demo verification. This report presents the system architecture, methodology, measured baseline results, engineering challenges and solutions, conclusions, and recommended future work.

**Keywords:** teleoperation, haptic feedback, ROS 2, Jetson Orin, D-BOX, Tailscale, autonomous vehicles

---

## 1. Introduction

### 1.1 Motivation

When a human drives a vehicle from a remote station, three sensory channels that normally make driving intuitive are degraded or missing: wide field of view and depth cues, vestibular and somatosensory perception of acceleration and vibration, and tight coupling between control input and vehicle response. Flat single-camera teleoperation leaves operators slow, imprecise, and fatigued. Industry remote-driving systems (e.g., commercial AV fallback and hazardous-site teleops) therefore invest heavily in panoramic video, low-latency links, and motion cueing.

### 1.2 Project objective

This project builds a low-cost, campus-deployable teleoperation stack that combines:

1. **Vision**: panoramic live video from three vehicle-mounted ZED X cameras displayed on three operator monitors  
2. **Control**: low-latency wheel and pedal commands to a differential-drive go-kart  
3. **Haptics**: vehicle IMU accelerations mapped into a D-BOX motion chair (integration in progress)

Communication runs entirely over **Tailscale VPN** rather than line-of-sight radio, so the operator and vehicle can sit on independent internet connections.

### 1.3 Platform and team context

Marvin is an AVL go-kart used alongside the lab’s IGVC (Intelligent Ground Vehicle Competition) ROS 2 stack. Teleoperation software is maintained outside the shared IGVC tree (`/home/dinosaur/IGVC/`), which is treated as read-only. The work was carried out during the AVL Summer Cohort 2026 under Dr. Behnam Bahr, with Ryan Simpson as team lead.

### 1.4 Report organization

Section 2 describes system architecture. Section 3 covers methodology and implementation. Section 4 reports results and metrics. Section 5 discusses challenges and solutions. Section 6 concludes. Section 7 outlines future work.

---

## 2. System Architecture

### 2.1 Operator station (Windows)

| Component | Role |
|-----------|------|
| Thrustmaster wheel and pedals | Steering, throttle, brake via SDL2 |
| `simchair_sender_dbox.exe` | Reads inputs; sends UDP control; drives D-BOX from local cues |
| D-BOX LiveMotion chair | Physical motion feedback (APP_KEY: CalPolyPomonaDevSim) |
| Three monitors (NVIDIA Surround) | Panoramic display at x = 0, 1920, 3840 |
| `windows_camera_receiver_udp.py` | Receives chunked JPEG over UDP; OpenCV display on main thread |
| `windows_camera_receiver.py` | Legacy JPEG over TCP |
| Tailscale IP | `100.91.25.107` |

### 2.2 Vehicle (Jetson Orin “dinosaur”)

| Component | Role |
|-----------|------|
| NVIDIA Jetson Orin | Ubuntu 22.04, ROS 2 Humble, CycloneDDS |
| 3× Stereolabs ZED X (GMSL) | Front, left, right panoramic vision |
| Xsens MTi-680G IMU | Vehicle motion sensing |
| Teensy 4.1 USB serial | Bridge to REV Spark MAX motor controllers |
| REV Spark MAX + differential drive | Left/right propulsion |
| Velodyne LiDAR, NTRIP GPS | Platform sensors (IGVC stack; not required for teleop demo) |
| Tailscale IP | `100.93.121.3` |

### 2.3 Network channels

| Direction | Port | Protocol | Function |
|-----------|------|----------|----------|
| Windows → Jetson | 5006 | UDP | Control: `steering,throttle,brake,mode` |
| Jetson → Windows | 5007 | UDP | IMU binary telemetry (~50 Hz) |
| Jetson → Windows | 5008 | UDP | Vehicle controller status |
| Jetson → Windows | 9001-9003 | **UDP** | Chunked JPEG video (primary) |
| Jetson → Windows | 9001-9003 | TCP | JPEG video (legacy fallback) |

### 2.4 Data-flow summary

**Control:** Thrustmaster → SDL2 → `simchair_sender_dbox.exe` → Tailscale UDP :5006 → `orin_vehicle_controller.py` → USB serial `L{rpm} R{rpm}` → Teensy → Spark MAX → motors.

**Video (current primary path):** ZED X → ROS 2 raw Image → `orin_camera_sender_udp.py` (1280×720 JPEG q≈85, chunked) → Tailscale UDP :9001-9003 → `windows_camera_receiver_udp.py` → three monitors. Legacy TCP path (`orin_camera_sender.py`) remains as fallback.

**Haptics (bridge ready):** Xsens → ROS 2 `/imu/data` → `imu_bridge.py` → UDP :5007 → Windows washout / D-BOX listener. End-to-end chair motion from vehicle IMU requires live verification before claiming as complete.

### 2.5 Software layout

```
cursor-test/
  windows/     Windows runtime (launch here)
  jetson/      Mirror of Jetson teleop scripts
  docs/        Architecture, launch, measurements, deliverables
  CARS_Poster/ Symposium poster assets
  _archive/    Historical experiments (not day-to-day)
```

Live Jetson copies: `~/Documents/SimChair_Teleop/`. Full stack launch: `orin_launch_all.sh` (tmux session `teleop`).

---

## 3. Methodology

### 3.1 Design principles

1. **Reliability over novelty for the demo path**: Prefer verified JPEG (TCP historically; UDP chunked for higher FPS/quality) over incomplete H.265 pipelines.  
2. **Do not modify shared IGVC code**: Source ROS overlays; keep teleop scripts in `SimChair_Teleop`.  
3. **Internet-scale link**: Tailscale (WireGuard) for all inter-machine traffic; keep UDP payloads within MTU 1280 (chunks ≤1200 bytes).  
4. **Fail-safe motor commands**: Stop with `L0 R0`; never send Teensy `S` (can leave Spark silent).

### 3.2 Control implementation

Wheel and pedal axes are normalized and packed as CSV over UDP at approximately 20 Hz from the SDL loop. On the Jetson, `orin_vehicle_controller.py` (v5.1) applies differential-drive mixing, streams serial commands at 50 Hz, exposes status on UDP :5008, and applies a ~400 ms UDP silence watchdog that zeros motors. Mode bit 0 stops; mode 1 enables drive. Re-arm after latch uses explicit N then D sequencing as implemented in the controller.

An alternate path uses the IGVC Chrome WebUI joystick; it is mutually exclusive with sim-chair ownership of `/dev/ttyACM0`. `simchair_drive.sh` borrows the Teensy and restores WebUI on exit.

### 3.3 Video implementation

Each ZED camera is launched with `unset DISPLAY`, camera serial numbers, and `publish_tf:=true` / `publish_urdf:=true` so the node publishes images (positional tracking in IGVC YAML otherwise hangs waiting for static TF). Cameras are staggered by ~25 seconds to avoid Argus daemon crashes observed with simultaneous multi-camera start.

`orin_camera_sender_udp.py` re-encodes raw frames to 1280×720 JPEG (quality ≈85) at up to 30 fps and sends them as ≤1200-byte UDP chunks (magic `MJPG`) to avoid Tailscale MTU issues and TCP head-of-line blocking. The legacy TCP sender forwards ROS compressed topics at ~15 fps. Windows receivers use background threads for sockets and the main thread for OpenCV window updates.

Experimental receivers exist for ZED SDK H.265 streaming and GStreamer RTP; they are not the primary demo path.

### 3.4 Haptics implementation

`imu_bridge.py` packs a 44-byte little-endian packet (`seq`, timestamp, linear accel, gyro, roll, pitch) at 50 Hz to the Windows host on UDP :5007. Windows-side washout test utilities (`windows_imu_washout_test.py`, `windows_haptic_receiver.py`) support classical washout-style cueing development. The D-BOX SDK is integrated in the C++ sender. Full closed-loop vehicle-IMU→chair demonstration remains a validation milestone.

### 3.5 Operations methodology

Jetson bring-up uses `orin_launch_all.sh` (firewall TCP+UDP 9001-9003, sensors, ZEDs, UDP camera sender, vehicle controller `--duty`, IMU bridge). Windows uses `start_all.bat` (`VIDEO_MODE=udp` default) or `windows_camera_receiver_udp.py`. iptables rules do not persist across Jetson reboot until systemd/persistent firewall work is completed.

### 3.6 Measurement methodology

Network RTT is measured with `tailscale ping` and path type via `tailscale status` (direct vs DERP relay). Glass-to-glass video latency uses a phone stopwatch in front of a ZED lens photographed together with the operator monitor (10 samples, report median). IMU rate uses `ros2 topic hz /imu/data` under ROS domain 42 and CycloneDDS.

---

## 4. Results

### 4.1 Verified capabilities

| Capability | Status | Evidence / notes |
|------------|--------|------------------|
| Sim-chair wheel/pedal → UDP control | Working | `simchair_sender_dbox.exe` + SDL2 |
| UDP control → Teensy RPM commands | Working | Port 5006; serial 115200 |
| Three-camera live JPEG display | Working | Verified 2026-08-04 |
| D-BOX SDK integration | Working | Chair driven from local inputs |
| ZED multi-camera launch recipe | Working | Stagger + TF/URDF flags |
| Vehicle IMU → D-BOX E2E | Not verified | Bridge script ready |
| Sustained motor quality | Open | Degradation / right-tilt under investigation |

### 4.2 Baseline metrics (2026-07-27)

**Network**

| Metric | Value |
|--------|-------|
| Tailscale path | DERP relay (lax); direct preferred |
| Ping RTT (10 samples) | 88-112 ms |

**Video**

| Metric | TCP baseline | UDP primary (2026-08-07) | Target |
|--------|--------------|--------------------------|--------|
| Resolution | ~960×600 | 1280×720 encode | ≥1080p / H.265 |
| Frame rate | 15 fps | 30 fps target | 30+ sustained |
| Codec / transport | JPEG / TCP | JPEG / UDP (chunked) | H.265 / RTP-UDP |
| Glass-to-glass latency | TBD | TBD | &lt;150 ms median |
| Aggregate bandwidth | TBD | TBD | &lt;25 Mbps |

**Control**

| Metric | Value | Target |
|--------|-------|--------|
| Send rate | ~20 Hz | 50 Hz fixed |
| Jetson watchdog | 400 ms | 300 ms + latched STOPPED |
| Teensy silence watchdog | None | 250 ms → zero motors |
| Cable-pull failsafe | TBD | Stop &lt;300 ms |

### 4.3 Interpretation

Control and panoramic video establish a usable remote-driving loop over the public internet via Tailscale. DERP relay latency (~90-110 ms RTT) already consumes a large fraction of a 150 ms glass-to-glass budget; a **direct** Tailscale peer path is required before latency targets can be fairly evaluated. Video resolution and frame rate are constrained by JPEG bandwidth on the current link; H.265 hardware encoding on Orin NVENC is the planned upgrade. Haptics software components exist but must not be reported as fully demonstrated until chair motion is confirmed from vehicle IMU data during a live run.

---

## 5. Challenges and Solutions

### 5.1 Solved challenges

| Challenge | Root cause | Solution |
|-----------|------------|----------|
| ZED EGL / Argus crashes | `DISPLAY` set or empty `DISPLAY=` | Real `unset DISPLAY` before ZED launch |
| No image frames; TF wait hang | `publish_tf` / `publish_urdf` false with tracking on | Launch with both true + serials |
| Camera start failures | Dual ZED stacks (IGVC + teleop) | Kill watchdogs; one stack only |
| Multi-cam Argus crash | Simultaneous ZED start | 25 s stagger between cameras |
| OpenCV windows missing | GUI calls off main thread (Windows) | Queue frames; imshow on main thread |
| Control feel inverted | Sign errors in mixing | Correct throttle−brake and steering sign |
| Unreliable H.264 RTSP | GStreamer thread-safety / env issues | Adopt JPEG (TCP then UDP chunked) |
| Conda breaks ROS imports | `python3` hijacked | Use `/usr/bin/python3` |

### 5.2 Architecture decisions

- **JPEG (TCP, then UDP chunked for higher FPS/quality) over GStreamer RTSP** after repeated bitstream failures.  
- **Forward ZED compressed topics** to avoid OpenCV re-encode CPU cost.  
- **Tailscale for all links** so campus LAN is unnecessary.  
- **Hardcoded camera stagger** after automated readiness detection proved unreliable.

### 5.3 Open challenges

1. **Motor degradation** after sustained use: suspected Teensy firmware rate limiting or Spark current limits; A/B test with phone-joystick Teensy firmware.  
2. **Rightward tilt/drift** despite symmetric commanded RPM: investigate hardware and Spark configuration mismatch.  
3. **IMU→D-BOX end-to-end validation**: bridge present; washout tuning and live confirmation remaining.  
4. **Tailscale often on DERP**: firewall/NAT tuning for direct peers before latency claims.

---

## 6. Conclusion

This project delivered a working internet-scale teleoperation loop for the AVL Marvin platform: panoramic three-camera video and sim-chair wheel/pedal control over Tailscale, with D-BOX SDK integration on the operator station and an IMU telemetry bridge prepared for motion cueing. The current primary video path uses chunked JPEG over UDP targeting 1280×720 at 30 fps (TCP JPEG remains as fallback); control uses open-loop duty mode. Baseline Tailscale RTT was 88-112 ms under DERP relay (2026-07-27).

Key engineering outcomes include a reproducible ZED multi-camera launch procedure (DISPLAY handling, TF/URDF flags, staggered start), a main-thread-safe Windows video receiver, and documented failure modes that future teams should not re-discover. Remaining gaps are motor reliability under sustained load, full vehicle-to-chair haptic demonstration, video codec upgrade for higher resolution at lower bitrate, and operational hardening (systemd, persistent firewall, control sequence numbers and multi-layer watchdogs).

The work shows that consumer simulation hardware (Thrustmaster, D-BOX) can be combined with a ROS 2 Jetson robotics platform to build immersive teleoperation suitable for campus research demos and as a foundation for autonomy safety-intervention studies.

---

## 7. Future Work

Priority order recommended for the next development cycle:

1. **Motors**: re-verify spin and measured RPM; resolve degradation and right-tilt.  
2. **IMU → D-BOX end-to-end**: confirm chair motion from vehicle IMU; tune classical washout (tilt coordination + heave); ramp to neutral on packet loss.  
3. **Video upgrade**: ZED SDK H.265 NVENC streaming (RTP/UDP) targeting ≥720p @ 30 fps and &lt;25 Mbps for three cameras.  
4. **Latency campaign**: force Tailscale direct path; complete glass-to-glass stopwatch study (target &lt;150 ms median).  
5. **Control hardening**: sequence numbers, timestamps, 50 Hz send rate, 300 ms latched stop, Teensy silence watchdog, cable-pull failsafe test.  
6. **Operations**: systemd units for teleop services, iptables-persistent, cold-boot to ready without manual tmux.  
7. **Soak testing**: ≥30 minutes simultaneous video + control + haptics before formal demos.

---

## References / Internal documentation

1. AVL Sim Chair workspace docs: `docs/SYSTEM_ARCHITECTURE.md`, `docs/LAUNCH_PROCEDURE.md`, `docs/KNOWN_ISSUES_AND_HISTORY.md`, `docs/MEASUREMENTS.md`, `docs/TARGET_ARCHITECTURE.md`  
2. Stereolabs ZED SDK / ROS 2 wrapper documentation (camera streaming, TF publishing)  
3. D-BOX LiveMotion SDK developer documentation  
4. Tailscale networking and WireGuard MTU guidance  
5. Classical washout filter literature for motion cueing (industry standard in motion platforms)

---

## Appendix A: Quick launch (verified path)

**Jetson:**

```bash
bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
```

**Windows:**

```powershell
cd "C:\Users\VRX 226\cursor-test\windows"
python windows_camera_receiver_udp.py
# or: .\start_all.bat
.\simchair_sender_dbox.exe
```

## Appendix B: Team and contacts

| Role | Name | Email (submission) |
|------|------|--------------------|
| Team lead | Ryan Simpson | rmsimpson@cpp.edu |
| Faculty mentor | Dr. Behnam Bahr | bbahr@cpp.edu |
| Cohort submission |: | mghasemi@cpp.edu (To); CC rmsimpson@cpp.edu, kbraga@cpp.edu |

---

*End of report. Formatted length is intended to meet or exceed an 8-page technical report when exported to PDF (11 pt body, 1-inch margins, single spacing ~8-10 pages including tables).*
