# Starting Marvin teleop (sim chair PC)

Commands are run from a PowerShell or cmd window on the sim chair PC.
Marvin = Jetson `dinosaur@100.93.121.3`, chair PC = `100.91.25.107`.

## 1. Start Marvin

```
ssh dinosaur@100.93.121.3 "bash ~/SimChair_AVL/jetson/relay_teleop/start_all.sh"
```

Starts all 3 cameras, drive (gear mode), Xsens, the IMU bridge and the
bitrate controller. Takes about 2 minutes (cameras start one at a time).
Wait for `Video: open http://100.93.121.3:8090/`.

Options go before `bash`:

| Option | Effect |
|---|---|
| `START_SCALE=0.6` | starting video bitrate (0.25–1.5, then it adapts) |
| `MAX_SCALE=3` | let video go higher (night, fast link) |
| `FRONT_ONLY=1` | front camera only |
| `NO_IMU=1` | skip the Xsens and IMU bridge |
| `DRIVE_MODE=diff` | force one drive mode instead of paddle gears |

Example: `ssh dinosaur@100.93.121.3 "START_SCALE=0.6 bash ~/SimChair_AVL/jetson/relay_teleop/start_all.sh"`

## 2. Start the chair side

Double-click `C:\Users\VRX 226\simchair_teleop\windows\start_chair.bat`
(or run it from a terminal). It opens:

- **Marvin Sender (no D-BOX)**: wheel/pedals to Marvin
- **IMU Chair**: Marvin's IMU/encoder cues to the D-BOX
- the viewer at http://100.93.121.3:8090/

## 3. Drive

Put the chair in park (0) once to arm, then paddle 1 = differential,
2 = Ackermann (0/3 = off).

## Check and stop

| Task | Command |
|---|---|
| What's running on Marvin | `ssh dinosaur@100.93.121.3 "tmux list-windows -t simchair"` |
| Watch Marvin's windows | `ssh -t dinosaur@100.93.121.3 "tmux attach -t simchair"` (`Ctrl+B` `N` = next, `Ctrl+B` `D` = leave running) |
| Stop Marvin | `ssh dinosaur@100.93.121.3 "bash ~/SimChair_AVL/jetson/relay_teleop/stop_all.sh"` |
| Stop the chair side | close the "Marvin Sender (no D-BOX)" and "IMU Chair" windows |

## If a camera won't open

`CAMERA STREAM FAILED TO START` or `MOTION SENSORS NOT DETECTED`:

```
ssh dinosaur@100.93.121.3 "bash ~/SimChair_AVL/jetson/relay_teleop/stop_all.sh; sudo systemctl restart nvargus-daemon"
```

Then run step 1 again. If it still fails, it's hardware: power Marvin off and
reseat that camera's GMSL cable (the left ZED did this on 2026-10-14), or
start with `FRONT_ONLY=1` in the meantime.

## Viewer

If a tile goes black, click **Reconnect** on the page. Open only one viewer.
