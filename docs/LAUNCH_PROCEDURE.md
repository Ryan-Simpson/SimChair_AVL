# Launch Procedure

**Updated:** 2026-08-07  
**Windows runtime:** `C:\Users\VRX 226\cursor-test\windows\`  
**Jetson scripts:** `~/Documents/SimChair_Teleop/` (Windows mirror: `cursor-test\jetson\`)  
**Drive ownership:** see [CONTROL_PROTOCOL.md](CONTROL_PROTOCOL.md)  
**Video:** primary = **JPEG over UDP** (chunked); TCP JPEG is legacy fallback.

---

## Preferred — one command each side

### Jetson

```bash
bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
```

Preflight clears leftover `teleop` tmux, ZED watchdogs, and restarts Argus. Then starts:

1. Firewall **TCP + UDP** 9001–9003  
2. Sensors bringup  
3. ZED front / left / right (25s apart, serial numbers, `publish_tf:=true`, `publish_urdf:=true`)  
4. **`orin_camera_sender_udp.py`** → Windows (default `CAMERA_TRANSPORT=udp`)  
   - Target: **1280×720 @ 30 fps**, JPEG quality **85**, chunked UDP  
5. **Sim-chair drive** (default): stops WebUI, starts `orin_vehicle_controller.py --duty`  
6. `imu_bridge.py` → Windows UDP 5007  

Cameras only (keep Chrome WebUI on Teensy):

```bash
SIMCHAIR_DRIVE=0 bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
```

Legacy TCP video:

```bash
CAMERA_TRANSPORT=tcp bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
```

Drive-only if cameras already up:

```bash
bash ~/Documents/SimChair_Teleop/simchair_drive.sh
# Ctrl+C → sudo systemctl restart avros-webui (full WebUI, not actuator alone)
```

### Windows

```powershell
cd "C:\Users\VRX 226\cursor-test\windows"

# Full stack — default VIDEO_MODE=udp
.\start_all.bat

# Cameras only (UDP)
python windows_camera_receiver_udp.py

# Legacy TCP cameras
$env:VIDEO_MODE = "jpeg"; .\start_all.bat
# or: python windows_camera_receiver.py
```

Wheel **mode 1** = drive, **mode 0** = park.

---

## Clean relaunch (after camera crash)

### Jetson

```bash
tmux kill-session -t teleop 2>/dev/null
sudo pkill -f zed_camera.launch.py
sudo pkill -f component_container_isolated
sudo pkill -f orin_camera_sender
sudo pkill -f orin_vehicle_controller
sudo pkill -f imu_bridge
sleep 2
sudo systemctl restart nvargus-daemon
sleep 3
bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
```

### Windows

Close old receiver windows, then `.\start_all.bat` again.

---

## Kill teleop stack (Jetson)

```bash
tmux kill-session -t teleop

# If anything remains:
sudo pkill -f orin_camera_sender
sudo pkill -f orin_vehicle_controller
sudo pkill -f imu_bridge
sudo pkill -f zed_camera.launch.py
sudo pkill -f component_container_isolated

# Restore day-to-day WebUI
sudo systemctl start avros-webui
```

Monitor without attaching:

```bash
tmux list-windows -t teleop
tmux capture-pane -t teleop:cam_sender -p | tail -40
tmux capture-pane -t teleop:vehicle -p | tail -20
```

---

## Manual ZED launch (if not using launch_all)

Use **real** `unset DISPLAY` (not `export DISPLAY=`). Include serial + TF flags or the node hangs on *Waiting for valid static transformations*.

```bash
unset DISPLAY
source /home/dinosaur/IGVC/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
export ROS_DOMAIN_ID=42

ros2 launch zed_wrapper zed_camera.launch.py \
  camera_model:=zedx \
  camera_name:=zed_front \
  serial_number:=42569280 \
  publish_tf:=true \
  publish_urdf:=true \
  ros_params_override_path:=/home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/zed_front.yaml
```

| Camera | Serial | YAML |
|--------|--------|------|
| zed_front | 42569280 | zed_front.yaml |
| zed_left | 49910017 | zed_left.yaml |
| zed_right | 43779087 | zed_right.yaml |

Wait ~25s between cameras. Then UDP sender:

```bash
/usr/bin/python3 ~/Documents/SimChair_Teleop/orin_camera_sender_udp.py \
  --windows-ip 100.91.25.107 --fps 30 --quality 85 --width 1280 --height 720
```

---

## Sim-chair drive (borrow Teensy, restore WebUI)

Full protocol: [CONTROL_PROTOCOL.md](CONTROL_PROTOCOL.md).

```bash
bash ~/Documents/SimChair_Teleop/simchair_drive.sh
# Ctrl+C restores avros-webui.service (HTTPS :8000 + actuator)
```

Expect restore message: **“Restoring full Chrome WebUI”** — not “actuator_node up” alone.

Windows sender:

```powershell
cd "C:\Users\VRX 226\cursor-test\windows"
.\simchair_sender_dbox.exe
```

Before driving: `sudo lsof /dev/ttyACM0` — one owner only.

---

## Sync jetson\ → Kart (no SSH)

On Windows: `cd cursor-test\jetson` → `python -m http.server 8765`  
On Jetson:

```bash
cd ~/Documents/SimChair_Teleop
curl -O http://100.91.25.107:8765/orin_launch_all.sh
curl -O http://100.91.25.107:8765/orin_camera_sender_udp.py
curl -O http://100.91.25.107:8765/orin_camera_sender.py
curl -O http://100.91.25.107:8765/orin_vehicle_controller.py
curl -O http://100.91.25.107:8765/simchair_drive.sh
chmod +x orin_launch_all.sh simchair_drive.sh
```

---

## Important notes

- **Never** `export DISPLAY=` for ZED — use `unset DISPLAY` on its own line  
- iptables 9001–9003 (TCP/UDP) do **not** persist across Jetson reboot  
- Windows Firewall may need inbound UDP 9001–9003 for the new video path  
- Only one owner of `/dev/ttyACM0` (WebUI actuator **or** `orin_vehicle_controller`)  
- Drive default is **`--duty`** (UL/UR); `--velocity` often leaves Sparks purple  
- Use `/usr/bin/python3` on Jetson (conda hijacks bare `python3`)  
- Do **not** modify `/home/dinosaur/IGVC/`  
- Prefer `cursor-test\windows\` over legacy `C:\Users\VRX 226\test\`
