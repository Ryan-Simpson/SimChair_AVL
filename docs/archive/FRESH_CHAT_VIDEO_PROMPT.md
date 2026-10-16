# Fresh-chat prompt: best video + teleop architecture

**Copy everything below the line into a new chat.** Attach or point at repo `C:\Users\VRX 226\simchair_teleop` (especially `docs/`, `jetson/`, `windows/`).

---

You are helping redesign **Marvin Sim Chair teleop video** for a go-kart (“Marvin” / Jetson Orin AGX host `dinosaur`) driven from a Windows sim chair over Tailscale.

## Goal

Propose the **best practical architecture** for:

1. **3-camera panoramic video** on the Windows sim chair (left / front / right monitors) with usable FPS and minimal freeze/smear while driving.
2. **Coexistence with `percept-stack`** (carla-nav2-avl) which **always** owns the three ZED X cameras, Argus, costmap, and sensors on boot.
3. **Wheel drive** via ROS (`/avros/actuator_command` → existing `actuator_node` → Teensy) without stealing the Teensy from WebUI when possible.

Do **not** assume we can stop perception for demos. Do **not** recommend `orin_launch_all.sh` while percept is up (it kills ZEDs/Argus).

## Constraints (hard)

- Jetson: Tailscale `100.93.121.3`; Windows chair: `100.91.25.107`.
- Link is often Tailscale (sometimes DERP relay) — MTU ~1280; UDP-heavy protocols suffer.
- ZED SDK native streaming uses NVENC H.265 and custom UDP chunks; ports currently **30000 / 30004 / 30008**.
- `stream_server.port` / bitrate are **read-only at runtime**; unique ports must live in  
  `/home/dinosaur/IGVC/src/avros_bringup/config/zed_{front,left,right}.yaml` (already set).
- Camera grab is **SVGA @ 15** for percept headroom (soft when upscaled to 1080p).
- Running **JPEG UDP sender (`orin_camera_sender_udp`) + H.265 streams together** saturated ~100 MiB/s and destroyed performance.
- Killing percept tmux `costmap_rgb` crashed the Jetson; killing `rviz`/`viz` is OK for bandwidth.
- Windows ZED receive works with **Python 3.8 + pyzed**; `start_all.bat` defaults to JPEG unless `set VIDEO_MODE=zed` in **cmd** (not PowerShell `$env:`).
- Disk has been critically full (`IGVC/bags` hundreds of GB) — treat as ops risk.
- Physical E-stop disables Spark MAXes; software restart alone does not re-enable motion.

## What was already tried

| Approach | Result |
|----------|--------|
| JPEG/UDP compressed from ROS topics | Stable-ish with percept; soft/blocky |
| Raw 720p×3 JPEG with percept | Crashed / overloaded Orin |
| ZED H.265 front only | **Good FPS**, usable; best so far |
| ZED H.265 ×3 after unique ports | Opens; **corrupt chunks / freezes / smear** on Tailscale under load (`recv: 2904 / expect 4112` etc.) |
| Smaller `chunk_size` (4096 then aim 1024), lower bitrate, adaptive | Helps some; 3-cam still fragile on tunnel |
| `--native-size` on Windows receiver | Reduces upscale “tear” look; does not fix packet loss |
| NoMachine + RViz camera panes | Huge extra bandwidth / lag |

Repo scripts of note: `jetson/simchair_launch_clean.sh`, `simchair_enable_zed_streams.sh`, `simchair_attach.sh --ros-drive --no-cam`, `windows/windows_zed_stream_receiver.py`, `docs/H265_BRINGUP.md`, `docs/PERCEPT_STACK_AND_SIMCHAIR.md`, `docs/SESSION_HANDOFF_CONTEXT_LOSS.md`.

## What I want from you

1. **Ranked options** (best → fallback) for 3-view teleop video given Tailscale + percept always on. Include hybrids (e.g. H.265 front + JPEG sides, WebRTC, GStreamer RTP/SRT, lower FPS/res sides, LAN profile, etc.).
2. For the **top recommendation**: concrete architecture diagram, Jetson vs Windows components, estimated bitrate, why it survives MTU/loss better than ZED native ×3.
3. **Migration plan** in phases that don’t brick percept/WebUI (what to change in IGVC yaml vs SimChair-only scripts).
4. Explicit **non-goals** / what to stop doing (based on failures above).
5. A short **“demo day” runbook** (commands only) for the chosen path.

Reason from first principles + the failure evidence. Prefer something we can ship in days, not a research rewrite. Ask clarifying questions only if they block the recommendation.
