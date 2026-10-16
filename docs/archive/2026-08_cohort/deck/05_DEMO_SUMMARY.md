# Demo Summary: Marvin Sim Chair

**Updated:** 2026-08-07

What a live lab demo shows today, how to start it, and what not to over-claim.

---

## What the audience sees

1. **Operator station**: D-BOX chair, Thrustmaster wheel/pedals, three panoramic monitors  
2. **Panoramic video**: left / front / right ZED views (UDP JPEG)  
3. **Remote drive**: wheel/pedals → UDP 5006 → duty-mode vehicle controller → motors  
4. **Status**: optional control-status window (UDP 5008)  
5. **Vehicle**: Marvin with three ZED X cameras and Jetson Orin  

---

## Current demo path

| Channel | Path | Status |
|---------|------|--------|
| Control | Wheel → UDP 5006 → `orin_vehicle_controller.py --duty` → Teensy | Working |
| Video | ZED → `orin_camera_sender_udp.py` → UDP JPEG 9001-9003 → `windows_camera_receiver_udp.py` | Working |
| Haptics | Local input→D-BOX via sender exe | Available |
| Haptics | Vehicle IMU/encoder cues → UDP 5007 → washout → D-BOX (`start_chair.bat`) | Working 2026-10-14 |

**Do not claim unless checked that day:** H.265 primary, glass-to-glass &lt;150 ms, full IMU→chair washout, perfect sustained motors.

---

## Minimal launch (demo day)

### Jetson

```bash
bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
```

Preflight clears ZED contention; starts UDP cameras, `--duty` drive, IMU bridge.

Stop: `tmux kill-session -t teleop` then `sudo systemctl start avros-webui`

### Windows

```powershell
cd "C:\Users\VRX 226\cursor-test\windows"
.\start_all.bat
# default VIDEO_MODE=udp
```

Drive-only borrow: `bash ~/Documents/SimChair_Teleop/simchair_drive.sh` (Ctrl+C restores WebUI).

---

## Demo talk track (≈60 s)

1. Problem: remote drivers lose FOV and motion cues  
2. Solution: three-camera panorama + wheel/pedals over Tailscale + D-BOX  
3. Show monitors (UDP JPEG path)  
4. Show kart respond to wheel  
5. Close: next = vehicle-IMU motion cueing + H.265 / lower latency  

---

**See also:** [LAUNCH_PROCEDURE.md](../LAUNCH_PROCEDURE.md) · [LAUNCH.txt](../../LAUNCH.txt)
