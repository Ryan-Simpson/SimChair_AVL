# Control Protocol — Teensy ownership

**Updated:** 2026-08-07  
**Rule:** Only **one** process may own `/dev/ttyACM0` at a time.

| Mode | Who drives | Owns Teensy | When to use |
|------|------------|-------------|-------------|
| **Lab day-to-day** | Chrome WebUI joystick | `actuator_node` via `avros-webui.service` | Leave kart this way when done |
| **Full teleop (launch_all default)** | Sim chair wheel/pedals | `orin_vehicle_controller.py --duty` | Demos / chair runs |
| **Drive-only borrow** | Sim chair | same, via `simchair_drive.sh` | Cameras already up |

---

## Leave WebUI when finished

```bash
sudo pkill -f orin_vehicle_controller 2>/dev/null
sudo systemctl start avros-webui
sudo lsof /dev/ttyACM0   # expect actuator_node only
```

Drive at: `https://100.93.121.3:8000`  
If ROS topics look empty: `unset ROS_DOMAIN_ID` (WebUI is domain 0).

---

## Full teleop (`orin_launch_all.sh` default)

```bash
bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
```

- Stops WebUI  
- Starts `orin_vehicle_controller.py --duty` (open-loop UL/UR — moves Sparks)  
- Starts UDP camera sender + IMU bridge  

Windows: `start_all.bat` (`VIDEO_MODE=udp`). Wheel **mode 1**.

Restore WebUI when done:
```bash
sudo pkill -f orin_vehicle_controller
tmux kill-session -t teleop   # if tearing down cameras too
sudo systemctl start avros-webui
sudo lsof /dev/ttyACM0
```

---

## Cameras without stealing drive

```bash
SIMCHAIR_DRIVE=0 bash ~/Documents/SimChair_Teleop/orin_launch_all.sh
```

---

## Borrow Teensy (`simchair_drive.sh`)

Uses `--duty`. On Ctrl+C runs **`sudo systemctl restart avros-webui`** (full stack: `:8000` + actuator).  
Do **not** rely on starting `actuator_node` alone — Chrome will not work.

```bash
bash ~/Documents/SimChair_Teleop/simchair_drive.sh
```

Windows: `.\simchair_sender_dbox.exe` — mode **1** drive, **0** park.

---

## Drive mode note

| Flag | Teensy cmds | Behavior |
|------|-------------|----------|
| **`--duty` (default)** | `UL/UR` open-loop | Sparks green/red under throttle — **use this** |
| **`--velocity`** | `L/R` RPM | May ack `OK L=…` while Sparks stay purple (no motion) |

Override examples:
```bash
VEHICLE_ARGS="--velocity" bash ~/Documents/SimChair_Teleop/simchair_drive.sh
```

---

## Checklist before blaming hardware

1. `sudo lsof /dev/ttyACM0` → **exactly one** of `actuator_node` **or** `orin_vehicle_controller`  
2. If both → stop one  
3. Sim chair: mode **1**, non-zero throttle, vehicle log shows `drive_mode=duty`  
4. After Ctrl+C: `systemctl is-active avros-webui` and `ss -ltnp | grep 8000`  

---

## Anti-patterns

- WebUI + `orin_vehicle_controller` both on Teensy  
- Restoring only `actuator_node` and expecting Chrome `:8000` to work  
- Leaving sim-chair vehicle running overnight — always restore WebUI when done  
