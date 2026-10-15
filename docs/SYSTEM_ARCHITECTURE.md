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

Working since 2026-10-14 (`windows/start_chair.bat`):

```
Xsens MTi-680G /imu/data (100 Hz) + /filter/free_acceleration
/wheel_odom (SPARK-measured motor speed, 20 Hz)
        ↓
jetson/imu_bridge.py (relay_teleop/run_imu_bridge.sh) → UDP 44-byte packet @ 25 Hz, port 5007
  ax = d/dt wheel speed, ay = speed × gyro yaw rate (blended with Xsens accel only
  while they agree), az = Xsens gravity-free z, gz = gyro yaw rate
        ↓  Tailscale
windows/imu_haptic_receiver.exe (source windows/dbox/imu_receiver)
  washout: pitch from ax, roll from ay + yaw rate; fast lean-in, slow release;
  heave / engine rumble / ground tilt off; ramp to neutral after 500 ms of no packets
        ↓
D-BOX LiveMotion (APP_KEY "CalPolyPomonaDevSim"), 50 Hz
```

`simchair_sender_dbox.exe --no-dbox` drives Marvin without moving the chair.
Without the flag the sender instead rocks the chair from the driver's own inputs
(the older behaviour); only one program can own the chair. Raw accelerometer
cueing was tried first and rejected: skid-steer track judder swamps Marvin's real
accelerations (see `windows/dbox/README.md`).

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

**Script locations:** Jetson `~/SimChair_AVL/` · Windows `C:\Users\VRX 226\simchair_teleop\windows\` (legacy: `~/Documents/SimChair_Teleop/`, `cursor-test\windows\`).
