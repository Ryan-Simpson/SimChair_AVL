# System Architecture

**Updated:** 2026-08-07

## Control Flow (Windows → Kart)

```
Thrustmaster Wheel/Pedals (SDL2)
        ↓
simchair_sender_dbox.exe (Windows)
  - UDP CSV: "steering,throttle,brake,mode\n"
  - mode: 0=stop, 1=drive
        ↓
Tailscale VPN (UDP port 5006)
        ↓
orin_vehicle_controller.py (Jetson)
  - Default: open-loop duty  UL{x} UR{y}
  - Optional: --velocity     L{rpm} R{rpm}
        ↓
Teensy 4.1 (/dev/ttyACM0 @ 115200)
        ↓
REV Spark MAX → go-kart motors
```

**Ownership:** WebUI `actuator_node` **or** `orin_vehicle_controller` — never both.  
See [CONTROL_PROTOCOL.md](CONTROL_PROTOCOL.md).

## Video Flow (Kart → Windows) — primary

```
ZED X GMSL (front, left, right)
        ↓
ROS2 raw Image (prefer) or /compressed
        ↓
orin_camera_sender_udp.py (Jetson)
  - Resize to 1280×720, JPEG q≈85, ~30 fps
  - Chunk into ≤1200-byte UDP datagrams (magic MJPG)
        ↓
Tailscale VPN (UDP ports 9001 / 9002 / 9003)
        ↓
windows_camera_receiver_udp.py (Windows)
  - Reassemble chunks → JPEG decode
  - OpenCV main thread; windows at x=0, 1920, 3840
```

**Legacy:** `orin_camera_sender.py` + TCP + `windows_camera_receiver.py` (~15 fps).  
**Experimental:** GStreamer RTP H.264 / ZED native stream.

## Haptic Feedback Flow

```
Kart IMU (Xsens preferred; ZED front IMU fallback)
        ↓
imu_bridge.py → UDP binary @ 50 Hz port 5007
        ↓
Windows washout / D-BOX listener
  - APP_KEY: "CalPolyPomonaDevSim"
  - Also: simchair_sender_dbox.exe can drive chair from local inputs
```

## ROS2 Environment (Jetson)

```bash
unset DISPLAY   # never export DISPLAY=
source /home/dinosaur/IGVC/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
export ROS_DOMAIN_ID=42
```

**CRITICAL:** Use `/usr/bin/python3` (conda hijacks `python3`).  
**ZED:** `publish_tf:=true` `publish_urdf:=true` + serials — see `LAUNCH_PROCEDURE.md`.  
**Never modify** `/home/dinosaur/IGVC/`.

**Script locations:** Jetson `~/Documents/SimChair_Teleop/` · Windows `C:\Users\VRX 226\cursor-test\windows\`.
