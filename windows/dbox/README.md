# D-BOX motion (Windows, sim chair PC)

C++ sources that drive the D-BOX chair through the LiveMotion SDK
(installed at `C:\Program Files\DBOX-SDK-Package\LiveMotionSdk`).

| Folder | Builds | What it does |
|---|---|---|
| `sender/` | `simchair_sender_dbox.exe` | Wheel/pedals -> UDP :5006 to the Jetson, and rocks the chair from the driver's own inputs (steer -> roll, pedals -> pitch). This is the exe in `windows/`. |
| `imu_receiver/` | `imu_haptic_receiver.exe` | UDP :5007 from `jetson/imu_bridge.py` -> washout filter -> chair roll/pitch/heave at 50 Hz. Ramps to neutral after 500 ms without packets. Not tested on the chair yet. |

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
