# Legacy code (not used; kept for reference)

Everything here is from the July–September 2026 setups: JPEG over TCP/UDP,
ZED SDK H.265 streams, and the "attach to percept-stack" model. None of it is
used by the current relay teleop (`jetson/relay_teleop/start_all.sh` +
`windows/start_chair.bat`, see [docs/START_TELEOP.md](../docs/START_TELEOP.md)).
Moved here 2026-10-16. Don't deploy these to Marvin; several of them stop the
WebUI, restart Argus or patch files under `~/IGVC`.

The scripts still refer to their old locations (`~/Documents/SimChair_Teleop/`
on Marvin, `windows\` next to `simchair_sender_dbox.exe` and the D-BOX DLLs).
To run one again, copy it back to where it expects to be.

## jetson/

| File | What it did | Replaced by |
|---|---|---|
| `orin_launch_all.sh` | Full stack in tmux `teleop`: ZEDs, JPEG senders, vehicle controller | `relay_teleop/start_all.sh` |
| `orin_camera_sender.py` | ZED → JPEG over TCP 9001–9003 | WebRTC (`relay_teleop/run_webrtc_cam.sh`, avros_webrtc) |
| `orin_camera_sender_udp.py` | ZED → chunked JPEG over UDP 9001–9003 | WebRTC |
| `orin_vehicle_controller.py` | UDP 5006 → Teensy serial directly (duty / velocity) | `orin_simchair_ros_bridge.py` → `/avros/actuator_command` → actuator_node |
| `simchair_attach.sh` | Attach JPEG sender / bridge / IMU to a running percept-stack | `relay_teleop/start_all.sh` |
| `simchair_drive.sh` | Borrow the Teensy from the WebUI, restore it on exit | actuator_node via `relay_teleop/run_actuator.sh` |
| `simchair_enable_zed_streams.sh` | Turn ZED SDK H.265 streaming on/off (ports 30000/30004/30008) | WebRTC |
| `simchair_launch_clean.sh` | One-shot H.265 + bridge attach | `relay_teleop/start_all.sh` |
| `patch_zed_stream_ports.sh`, `patch_zed_stream_tailscale.sh`, `patch_zed_stream_3cam_stable.sh` | Edited ZED stream settings in `~/IGVC/src/avros_bringup/config` | Nothing: `~/IGVC` is team code and is no longer touched |

## windows/

| File | What it did | Replaced by |
|---|---|---|
| `windows_camera_receiver.py` | JPEG/TCP receiver, 3 monitors | `windows/multicam_viewer.html` (served from Marvin on :8090) |
| `windows_camera_receiver_udp.py` | Chunked JPEG/UDP receiver | viewer |
| `windows_zed_stream_receiver.py` | ZED SDK H.265 receiver | viewer |
| `windows_gstreamer_rtp_receiver.py` | RTP H.264 receiver (experiment) | viewer |
| `windows_control_status.py` | Status from `orin_vehicle_controller.py` on UDP 5008 | bridge output in tmux `simchair:bridge` |
| `windows_haptic_receiver.py` | Prints washout output from the IMU packets, no chair | `imu_haptic_receiver.exe` (still reads the same 44-byte packet, so it works as a debug console) |
| `windows_imu_washout_test.py` | First washout prototype, old 7-value packet | `imu_haptic_receiver.exe` |
| `start_all.bat` | One-shot launcher for the receivers above (`VIDEO_MODE=udp/jpeg/zed/rtp`) | `windows/start_chair.bat` |
| `requirements.txt` | Python packages for the receivers above | Not needed: the current Windows tools are the two exes, the browser and stdlib Python |
