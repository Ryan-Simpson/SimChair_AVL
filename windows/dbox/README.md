# D-BOX motion (Windows, sim chair PC)

C++ sources that drive the D-BOX chair through the LiveMotion SDK
(installed at `C:\Program Files\DBOX-SDK-Package\LiveMotionSdk`).

| Folder | Builds | What it does |
|---|---|---|
| `sender/` | `simchair_sender_dbox.exe` | Wheel/pedals -> UDP :5006 to the Jetson. Without flags it also rocks the chair from the driver's own inputs (steer -> roll, pedals -> pitch). `--no-dbox` = drive only. |
| `imu_receiver/` | `imu_haptic_receiver.exe` | UDP :5007 from `jetson/imu_bridge.py` -> washout -> chair roll/pitch. Ramps to neutral after 500 ms without packets. **In use since 2026-10-14.** |

`windows/start_chair.bat` starts both (sender with `--no-dbox`) plus the viewer.

Only one program can drive the chair at a time: running `imu_haptic_receiver.exe`
needs the sender's own D-BOX motion turned off first.

Sources: `sender/` from `Test Workspace\cpp\v3_dbox`; `imu_receiver/` from the
`2026_Sim_Chair` project (github.com/Viora2006/AVL-Simulation-Chair-D-Box-Software,
plus the uncommitted IMU receiver and washout files). The D-BOX SDK headers and
`.lib`s are not copied here; the builds read them from the SDK install.

## Build

From a "Developer PowerShell for VS" (x64):

```powershell
cmake -S imu_receiver -B build/imu_receiver -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/imu_receiver

cmake -S sender -B build/sender -G Ninja -DCMAKE_BUILD_TYPE=Release `
      -DSDL2_DIR=C:/vcpkg/installed/x64-windows/share/sdl2
cmake --build build/sender
```

Pass `-DDBOX_SDK_ROOT=<path to LiveMotionSdk>` if the SDK is elsewhere.
`dbxLive64.dll` must sit next to the exe (the sender build copies it).

## IMU chair: how the cues are made (2026-10-14)

Tuned in the chair on Marvin's first night drive. What we learned:

- Skid-steer track judder swamps the accelerometer: driving shakes ~0.8 m/s^2
  (peaks 3-5) while Marvin's real speed changes are ~0.3 m/s^2. Raw IMU accel
  made the chair pitch/roll at random in a straight line, and heave was a
  constant up-and-down buzz.
- So `imu_bridge.py` (Jetson) sends cues instead of raw accel:
  - forward: d/dt of `/wheel_odom` speed (SPARK-measured motor RPM),
  - sideways: speed x Xsens gyro yaw rate (+ = turning left),
  - each blended with the Xsens accel only while they agree in direction;
    the IMU sign is learned from a running correlation. On 10-14 it never
    locked (correlation stayed under 0.3), so the chair ran on encoder + gyro.
  - `--cue imu` restores raw accelerometer values.
- The receiver adds yaw rate straight to roll so differential pivots are felt,
  leans in fast and releases slowly so a 1.3 s speed-up feels like a push,
  and has heave, ground-tilt copying and the D-BOX engine rumble off.

Receiver flags (defaults = the version in use):

| Flag | Default | Effect |
|---|---|---|
| `--pitch g` | 0.60 | forward/back accel -> pitch (negative flips) |
| `--roll g` | 0.40 | sideways accel -> roll |
| `--yaw g` | 0.30 | yaw rate (rad/s) -> roll |
| `--heave g` | 0 | vertical accel -> heave |
| `--tilt-rate r` | 0.6 | lean-in speed (normalized/s) |
| `--release r` | 0.15 | return-to-centre speed |
| `--tilt-hz f` | 0.8 | smoothing on the accel cues |
| `--heave-hz f` | 1.5 | heave high-pass |
| `--attitude a` | 0 | share of ground roll/pitch copied |
| `--engine 0/1` | 0 | D-BOX engine rumble |
| `--comfort c` | 0.5 | output clamp |

IMU rate is 25 Hz (`kImuHz`, must match `IMU_HZ` in `run_imu_bridge.sh`).
