# Demo Video Script: Marvin Sim Chair

**Requirement:** 3 to 8 minutes showing **real system operation**  
**Due:** Friday, August 7, 2026, 11:59 PM  
**Output file (record tonight):** place finished video next to this file as  
`docs/deliverables/DEMO_VIDEO.mp4` (or `.mov`) and attach it to the cohort email.

No recorded footage exists in the repository yet. Use this script to film and edit tonight.

---

## Target runtime: ~5 minutes

| Segment | Time | Content |
|---------|------|---------|
| 1. Title card | 0:00-0:15 | Title, team, AVL / CPP |
| 2. Problem | 0:15-0:45 | Why teleop needs vision + motion |
| 3. Operator station | 0:45-1:30 | Chair, wheel, three monitors |
| 4. Vehicle | 1:30-2:00 | Marvin + ZED cameras + Jetson |
| 5. Live video | 2:00-3:00 | Three camera streams running |
| 6. Live drive | 3:00-4:30 | Wheel input → kart motion (stands or safe area) |
| 7. Architecture beat | 4:30-5:00 | Quick overlay: Tailscale, ports |
| 8. Status + close | 5:00-5:30 | What works / next steps / thank you |

Trim to stay between **3:00 and 8:00**.

---

## Shot list (film these)

1. **Wide:** operator seated in D-BOX with wheel and three monitors lit  
2. **Close:** hands on wheel / feet on pedals  
3. **Monitor wall:** left / front / right live views (phone or screen capture)  
4. **Marvin exterior:** kart with ZED X cameras visible  
5. **Jetson / compute area** (if visible without unsafe filming)  
6. **Live drive:** kart on stands or supervised safe ground: wheels respond to throttle/steer  
7. **Optional:** status window (`windows_control_status.py`)  
8. **Optional:** short Tailscale ping / “connected” UI if clean  

**Audio:** voiceover from script below OR on-camera Ryan (lead). Quiet lab ambient OK under VO.

---

## Voiceover script (~5 min)

### [0:00] Title
“Haptic Sim-Chair-Based Teleoperation for Autonomous Vehicle Platforms. Cal Poly Pomona Autonomous Vehicles Lab, Summer Cohort 2026.”

### [0:15] Problem
“When you drive a vehicle remotely, you lose peripheral vision and the feeling of acceleration. Flat video alone makes precise driving hard. We built a system that restores panoramic vision and control: and prepares motion feedback through a D-BOX chair.”

### [0:45] Operator station
“Here is the operator station: a Thrustmaster wheel and pedals, a D-BOX motion chair, and three monitors arranged like a driver’s field of view.”

### [1:30] Vehicle
“On the vehicle side, Marvin: our go-kart: carries three Stereolabs ZED X cameras and an Xsens IMU, all managed by an NVIDIA Jetson Orin. Communication runs over Tailscale VPN, so the chair and kart do not need line-of-sight radio.”

### [2:00] Live video
“These are the live left, front, and right camera streams. We send chunked JPEG frames over UDP from the Jetson: targeting 720p at 30 frames per second: and display them on the Surround monitors.”

### [3:00] Live drive
“When the operator turns the wheel and applies throttle, commands go over UDP to the Jetson, through our vehicle controller in open-loop duty mode, to a Teensy and Spark MAX motor controllers. You can see the kart respond in real time.”

### [4:30] Architecture
“Three channels: control on UDP 5006, video on UDP 9001 through 9003, and IMU telemetry on UDP 5007 for chair motion cueing.”

### [5:00] Close
“Today, remote driving and panoramic UDP video are working. Next, we complete vehicle IMU to chair motion, move to hardware H.265, and harden closed-loop motor control. Thank you: Autonomous Vehicles Lab, Cal Poly Pomona.”

---

## On-screen text overlays (optional)

- Title / authors  
- “Working: Control + UDP JPEG video”  
- “Tailscale VPN: internet-scale link”  
- “Next: IMU → D-BOX · H.265 · velocity PID”  

**Lab-accurate wording:** say “UDP JPEG video” not “H.265” unless that path is what you film. Say “motion chair ready / IMU bridge ready” not “full haptic demo” unless chair clearly moves from vehicle IMU during the take.

---

## Recording checklist (before you hit record)

- [ ] Jetson: `bash ~/Documents/SimChair_Teleop/orin_launch_all.sh`  
- [ ] Windows: `.\start_all.bat` or `python windows_camera_receiver_udp.py`  
- [ ] Windows: wheel mode 1 (`simchair_sender_dbox.exe` if not via start_all)  
- [ ] Three monitors showing live frames  
- [ ] Kart on stands or supervised area; spotter present  
- [ ] Phone charged / second camera for operator + vehicle  
- [ ] 10+ seconds of clean drive footage (no crashes cut)  

## Export settings

- Resolution: 1080p or better  
- Format: MP4 (H.264) preferred for email  
- Filename: `AVL_Summer2026_Marvin_SimChair_Demo.mp4`  
- Upload: Google Drive / OneDrive link in email if file &gt; attachment limit; still attach report + slides  

## Safety

- Spotter at the kart at all times  
- Start in mode stop; enable drive only when filming drive segment  
- Prefer stands for wheel-spin shots if outdoor drive is not cleared  

---

**After recording:** drop the file into `docs/deliverables/` and check it off in `README.md`.
