# Percept-Stack Always On — Sim-Chair Ops Notes

**Updated:** 2026-08-24  
**Assumption:** `percept-stack` (from [carla-nav2-avl](https://github.com/arassal/carla-nav2-avl)) **always runs on Marvin** (`dinosaur`). It owns ZEDs, sensors, Argus, and heavy perception on boot.

Sim-chair teleop must **attach** to that stack. It must **not** relaunch or kill the car’s cameras.

---

## WebUI shows “Disconnected” (boot / stale session)

**Symptom:** `avros-webui` is `active`, `:8000` is listening, `lsof` shows only `actuator_node`, but Chrome says **Disconnected** and the stick does nothing.

**Cause (typical):** HTTP page is up; the live browser ↔ `webui_node` session is stale or never finished (boot race, old tab, Tailscale blip, heavy percept boot). Not a Teensy dual-owner issue and not sim-chair.

**Fix — run this first (before sim-chair or Spark debugging):**
```bash
sudo journalctl -u avros-webui -n 50 --no-pager
sudo systemctl restart avros-webui
sleep 5
systemctl is-active avros-webui
ss -ltnp | grep 8000
```

Then hard-refresh `https://100.93.121.3:8000` (or open a new tab / accept cert again).

**Expect:** `active`, `webui_node` on `:8000`, UI Connected, stick works. Idle Teensy `OK S` in the journal is normal.

---

## Verified healthy boot (2026-08-21)

### Services / ports
| Check | Good value |
|-------|------------|
| `systemctl is-active percept-stack avros-webui` | `active` `active` |
| `sudo lsof /dev/ttyACM0` | **only** `actuator_node` |
| `:8000` | `webui_node` |
| `:8080` / `:8090` | `web_video_server` / dashboard |

### ROS env for CLI (critical)
```bash
conda deactivate          # (base) breaks DDS discovery
unset ROS_DOMAIN_ID DISPLAY
source /opt/ros/humble/setup.bash
source /home/dinosaur/IGVC/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
# if node list empty but kart works:
ros2 daemon stop; ros2 daemon start
```
`which python3` must be `/usr/bin/python3`.

### Nodes that steer + see (domain 0)
**Drive:** `/webui_node` → `/avros/actuator_command` → `/actuator_node` → Teensy  
**State:** `/avros/actuator_state`  
**Cameras:** `/zed_front|left|right/zed_node` (+ containers)  
**Percept:** `/perception_costmap`, `/perception_viz`, `/costmap_rgb`, `/web_video_server`  
**Sensors:** `/xsens_mti_node`, `/velodyne_*`, `/ekf_filter_node_odom`, `/ntrip_client`, `/robot_state_publisher`

### ActuatorCommand (what WebUI publishes)
Type: `avros_msgs/msg/ActuatorCommand`  
Fields seen live: `estop`, `throttle`, `brake`, `steer`, `mode` (`N`/`D`/`R`/…)  
QoS: RELIABLE, KEEP_LAST 10  
While sticking: `/avros/actuator_command` ≈ **20 Hz**

---

## Who owns what

| Resource | Owner (normal) | Sim-chair may… |
|----------|----------------|----------------|
| ZED ×3, Argus, sensors | `percept-stack` / tmux `percept` | Subscribe only (camera sender) |
| Chrome joystick `:8000` | `avros-webui` → `actuator_node` | Leave alone, **or** publish same cmd topic |
| `/dev/ttyACM0` Teensy | **`actuator_node` only** (preferred) | Steal only with legacy `--drive` |
| UDP video 9001–9003 | Our `orin_camera_sender_udp.py` | Start via attach script |
| UDP control 5006 | Our ROS bridge (preferred) or serial vehicle ctrl | Not both with Chrome stick |

---

## What broke (and why)

### 1. `orin_launch_all.sh` vs always-on percept
Kills ZEDs, restarts Argus, second camera stack → Orin crash/lag, broken car.  
**Rule:** Use `simchair_attach.sh` only.

### 2. Hot-unplug / dual stacks / REV Client
Kill software before unplugging. One Teensy owner. Close REV Client while driving.

### 3. Purple Sparks + `OK L=… R=…`
Velocity acks without torque. Legacy `--drive` duty serial is fallback. Prefer `--ros-drive` so `actuator_node` keeps the path that works with Chrome.

### 4. Empty `ros2 node list` while joystick works
**conda `(base)`** or wedged **ros2 daemon** — not a dead stack.

### 6. Raw 720p×3 camera sender crashes Jetson (2026-08-24)
With `percept-stack` up, `CAMERA_SOURCE=raw` + 1280×720 on all three cams overloaded/crashed the Orin.  
**Default attach = `compressed`** (stable FPS, softer image).  
Cautious sharper try: `CAMERA_SOURCE=raw CAMERA_PROFILE=indoor` (960×540). Avoid raw `default`/`hq` unless percept is light/off.

---

## Correct launch (percept stays up)

### Preferred: video + wheel via same topic as WebUI
```bash
bash ~/Documents/SimChair_Teleop/simchair_attach.sh --ros-drive
```
Keeps WebUI service + `actuator_node` on Teensy.  
**Close Chrome stick** while using the wheel.

Windows:
```powershell
cd "C:\Users\VRX 226\simchair_teleop\windows"
.\start_all.bat
```
Mode **0** = park, **1** = drive.

### Video only
```bash
bash ~/Documents/SimChair_Teleop/simchair_attach.sh
```

### Legacy serial duty (if ROS path fails)
```bash
bash ~/Documents/SimChair_Teleop/simchair_attach.sh --drive
```

### Sync Windows → Jetson
```powershell
cd "C:\Users\VRX 226\simchair_teleop\jetson"
python -m http.server 8765
```
```bash
cd ~/Documents/SimChair_Teleop
curl -O http://100.91.25.107:8765/simchair_attach.sh
curl -O http://100.91.25.107:8765/orin_simchair_ros_bridge.py
curl -O http://100.91.25.107:8765/orin_camera_sender_udp.py
chmod +x simchair_attach.sh
```

---

## Correct kill (leave percept alone)
```bash
tmux kill-session -t simchair 2>/dev/null
sudo pkill -f orin_simchair_ros_bridge
sudo pkill -f orin_camera_sender
sudo pkill -f imu_bridge.py
# only if legacy --drive:
sudo pkill -f orin_vehicle_controller
sudo systemctl restart avros-webui
sudo lsof /dev/ttyACM0
```

---

## See also
- [LAUNCH.txt](../LAUNCH.txt)  
- [CONTROL_PROTOCOL.md](CONTROL_PROTOCOL.md)  
- Scripts: `simchair_attach.sh`, `orin_simchair_ros_bridge.py`, `simchair_drive.sh`
