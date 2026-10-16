# System Architecture

**Updated:** 2026-10-16 (relay teleop). The older JPEG / H.265 / direct-serial
flows are described in [archive/](archive/README.md).

## Network

```
Sim chair PC 100.91.25.107 ⇄ Tailscale peer relay (Vultr LA, 66.42.96.149:4500) ⇄ Marvin 100.93.121.3
                                                                                 └ AT&T cellular, Sierra AirLink 192.168.13.31
```

On campus ↔ cellular Tailscale can't go direct, and DERP added ~100 ms, so
both ends use our own peer relay (control RTT ~38 ms median). Everything below
shares Marvin's cellular **upload**, which is the bottleneck: when we send more
than the cell carries, the modem queues instead of dropping, and video, drive
replies and IMU packets all arrive late together.
Details: [RELAY_TELEOP_2026-10-10.md](RELAY_TELEOP_2026-10-10.md).

## Drive (chair → Marvin)

```
Thrustmaster wheel/pedals (SDL2)
        ↓
simchair_sender_dbox.exe --no-dbox     UDP 5006 "steering,throttle,brake,mode", ~20 Hz
        ↓
orin_simchair_ros_bridge.py            gear mode: paddle 1 = diff, 2 = Ackermann, 0/3 = off
  arm with park (0); newest packet only (stale bursts after a stall are dropped)
        ↓
/avros/actuator_command
        ↓
actuator_node (the only Teensy owner) → Teensy 4.1 → Spark MAX → motors
  max 0.40 m/s
```

## Video (Marvin → chair)

```
ZED X ×3 (GMSL)  run_zed.sh by serial
        ↓  /<cam>/zed_node/rgb/color/rect/image
avros_webrtc webrtc_node ×3           NVENC H.264 CBR, 480×300; front 7.5 fps, sides 15 fps
  bitrate = base × /webrtc/bitrate_scale
        ↓  RTSP :8554
MediaMTX (stock)                      WebRTC / WHEP :8889
        ↓  Tailscale
Chrome: multicam_viewer.html          served from Marvin :8090; one viewer only
  auto-cutoff if the front RTT > 2 s or frames stall for 6 s
```

`rate_controller` pings the chair PC 5×/s and sets `/webrtc/bitrate_scale`
(0.25–1.5 of 1.2 Mbps total; front 500 kbps, sides 350 kbps each at 1.0). If the
link is still clogged at the floor it pauses the side cameras, leaving the
front at ~125 kbps.

## Chair motion (Marvin → chair)

```
Xsens MTi-680G /imu/data (100 Hz) + /filter/free_acceleration
/wheel_odom (SPARK-measured motor speed, 20 Hz)
        ↓
imu_bridge.py → UDP 5007, 44-byte packet @ 25 Hz
  ax = d/dt wheel speed, ay = speed × gyro yaw rate (blended with Xsens accel only
  while they agree), az = Xsens gravity-free z, gz = gyro yaw rate,
  t_ms = Jetson wall clock at send
        ↓  Tailscale
imu_haptic_receiver.exe (source windows/dbox/imu_receiver)
  washout: pitch from ax, roll from ay + yaw rate; fast lean-in, slow release;
  heave / engine rumble / ground tilt off; ramp to neutral after 500 ms of no packets
  logs arrival − t_ms to windows\logs\imu_owd_*.csv (upload queue signal)
        ↓
D-BOX LiveMotion (APP_KEY "CalPolyPomonaDevSim"), 50 Hz
```

`simchair_sender_dbox.exe` without `--no-dbox` instead rocks the chair from the
driver's own inputs (the older behaviour); only one program can own the chair.
Raw accelerometer cueing was rejected: skid-steer track judder swamps Marvin's
real accelerations (see `windows/dbox/README.md`).

## ROS environment (Marvin)

`jetson/relay_teleop/env.sh`, sourced by every run script:

```bash
unset ROS_DOMAIN_ID DISPLAY        # domain 0, same as the WebUI; never export DISPLAY=
source /opt/ros/humble/setup.bash
source ~/IGVC/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$HOME/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
```

Use `/usr/bin/python3` (conda hijacks `python3`). Don't modify `~/IGVC`.
DDS multicast (239.255.0.1) shows up as ~1 Mbps on `eno1` but stays on the
kart LAN; the cellular upload is what `tailscale0` sends.
