---
marp: true
title: Marvin Sim Chair Teleoperation: AVL Summer Cohort 2026
paginate: true
theme: default
style: |
  section { font-size: 28px; }
  h1 { font-size: 40px; }
  h2 { font-size: 34px; }
  table { font-size: 22px; }
  footer { font-size: 14px; }
---

<!-- Slide 1: Cover -->

# Haptic Sim-Chair Teleoperation
## for Autonomous Vehicle Platforms

**AVL Summer Cohort 2026**  
California State Polytechnic University, Pomona

Ryan Simpson · Tyler Carrasco · Yi-Szen Tang · Kevin Xu · Justin Dang  
Mentor: Dr. Behnam Bahr

August 7, 2026

---

<!-- Slide 2: Agenda -->

# Agenda

1. Project overview  
2. Technical architecture  
3. Methodology (how we built it)  
4. Challenges and solutions  
5. Results and metrics  
6. Demo summary  
7. Future work  
8. Handoff / Q&A  

---

<!-- Slide 3: Overview: Problem -->

# Overview: The Problem

Remote drivers lose the cues that make driving intuitive:

- Peripheral vision and depth  
- Body motion / acceleration feel  
- Confident, precise control  

**Flat single-camera teleop is not enough** for hazardous sites or AV safety intervention.

---

<!-- Slide 4: Overview: Solution -->

# Overview: Our Solution

**Marvin** go-kart ↔ **D-BOX sim chair** over **Tailscale VPN**

| Channel | What it restores |
|---------|------------------|
| Vision | 3× ZED X → 3 panoramic monitors |
| Control | Thrustmaster wheel/pedals → differential drive |
| Haptics | IMU → D-BOX chair (bridge ready; E2E verify next) |

Goal: human-level sight + physical feedback at internet scale.

---

<!-- Slide 5: Overview: Status -->

# Overview: Current Status

| Capability | Status |
|------------|--------|
| Wheel/pedal remote drive | Working |
| 3-camera live JPEG video | Working (UDP primary) |
| D-BOX SDK on Windows | Working |
| Vehicle IMU → chair E2E | Script ready: verify live |
| Motor sustained quality | Open issue |

---

<!-- Slide 6: Tech Architecture: Diagram -->

# Technical Architecture

```
OPERATOR (Windows)           TAILSCALE              VEHICLE (Jetson)
Wheel/Pedals --> UDP :5006 --------------------> controller -> Teensy -> Motors
3 Monitors   <-- UDP :9001-3 <------------------ ZED X x3 -> camera_sender_udp
D-BOX        <-- UDP :5007 <-------------------- IMU bridge (Xsens)
Status       <-- UDP :5008 <-------------------- controller status
```

Primary video path: **chunked JPEG over UDP** (~1280×720 @ 30). TCP JPEG is legacy fallback.

---

<!-- Slide 7: Tech Architecture: Stack -->

# Technical Architecture: Stack

**Operator:** Windows · SDL2 · OpenCV · D-BOX LiveMotion · Tailscale `100.91.25.107`

**Vehicle:** Jetson Orin · Ubuntu 22.04 · ROS 2 Humble · CycloneDDS · domain 42 · `100.93.121.3`

**Actuation:** Teensy 4.1 @ 115200 → REV Spark MAX (differential drive)

**Key apps:** `simchair_sender_dbox.exe` · `orin_vehicle_controller.py` · `orin_camera_sender_udp.py` · `imu_bridge.py` · `windows_camera_receiver_udp.py`

---

<!-- Slide 8: Methodology -->

# Methodology

1. Keep teleop **outside** shared IGVC tree (read-only)  
2. Prefer **reliable demo path** (UDP JPEG; TCP fallback) over unfinished codecs  
3. Forward ZED **compressed** topics (no re-encode)  
4. Stagger ZED launches; `unset DISPLAY`; TF/URDF on  
5. OpenCV display **main thread only** on Windows  
6. Measure: Tailscale RTT + glass-to-glass stopwatch (10 samples)

---

<!-- Slide 9: Challenges & Solutions (1) -->

# Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| ZED EGL / Argus crash | Real `unset DISPLAY` (not empty string) |
| No frames / TF hang | `publish_tf:=true` `publish_urdf:=true` |
| Dual ZED stacks fight | One stack only; kill watchdogs |
| Multi-cam crash | 25 s stagger between cameras |
| OpenCV blank windows | Main-thread imshow + queues |

---

<!-- Slide 10: Challenges & Solutions (2) -->

# Challenges & Solutions (cont.)

| Challenge | Solution |
|-----------|----------|
| GStreamer RTSP unreliable | Adopt JPEG (TCP then UDP chunked) as primary |
| Control inverted | Fix throttle-brake and steering signs |
| Conda breaks ROS Python | Always `/usr/bin/python3` |
| Tailscale MTU 1280 | UDP chunks ≤1200 bytes |

**Still open:** motor degradation, right-tilt, IMU→chair E2E, DERP vs direct.

---

<!-- Slide 11: Results & Metrics: Capabilities -->

# Results: Verified Capabilities

- Remote drive from sim chair over Tailscale  
- Three live camera streams on Surround monitors  
- D-BOX SDK integrated (local input cueing)  
- Reproducible full-stack launch (`orin_launch_all.sh`)  

Baseline date: **2026-07-27** · TCP video **2026-08-04** · UDP JPEG primary **2026-08-07**

---

<!-- Slide 12: Results & Metrics: Numbers -->

# Results: Baseline Metrics

| Metric | Value | Target |
|--------|-------|--------|
| Tailscale RTT | **88-112 ms** (DERP) | Direct peer path |
| Video | **1280×720 @ 30** JPEG/UDP (target) | H.265 / higher res |
| Glass-to-glass | TBD | &lt;150 ms median |
| Control rate | ~20 Hz | 50 Hz + seq/watchdogs |
| Bandwidth (3 cams) | TBD | &lt;25 Mbps |

*Do not invent TBD numbers: measure before claiming.*

---

<!-- Slide 13: Demo Summary -->

# Demo Summary

**What you see:** operator in D-BOX chair → panoramic video → kart responds to wheel

**Verified path tonight:**
1. Jetson: `orin_launch_all.sh`  
2. Windows: `start_all.bat` or `windows_camera_receiver_udp.py` + `simchair_sender_dbox.exe`

**Do not claim unless checked live:** H.265 primary, &lt;150 ms G2G, full IMU→chair washout, perfect sustained motors.

---

<!-- Slide 14: Future Work -->

# Future Work (Priority Order)

1. Motors: degradation and right-tilt  
2. IMU → D-BOX end-to-end + washout tuning  
3. H.265 / higher res video  
4. Latency on **direct** Tailscale (&lt;150 ms)  
5. Control seq + multi-layer watchdogs  
6. systemd + persistent firewall + soak ≥30 min  

---

<!-- Slide 15: Handoff -->

# Codebase & Handoff

```
cursor-test/windows/   <- launch Windows apps
cursor-test/jetson/    <- push to ~/Documents/SimChair_Teleop/
cursor-test/docs/      <- architecture, launch, known issues
```

**Never modify** `/home/dinosaur/IGVC/`

See: `docs/deliverables/HANDOFF_PACKAGE.md` · `docs/LAUNCH_PROCEDURE.md` · `docs/KNOWN_ISSUES_AND_HISTORY.md`

---

<!-- Slide 16: Closing -->

# Thank You

**Questions?**

Team: Ryan Simpson (lead) · Tyler Carrasco · Yi-Szen Tang · Kevin Xu · Justin Dang  
Mentor: Dr. Behnam Bahr · AVL, Cal Poly Pomona

Deliverables: Technical report · This deck · Demo video · Handoff package  
Submit To: mghasemi@cpp.edu · CC: rmsimpson@cpp.edu, kbraga@cpp.edu
