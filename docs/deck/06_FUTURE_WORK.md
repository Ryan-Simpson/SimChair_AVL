# Future Work: Marvin Sim Chair

Priority-ordered next steps and the upgrade phases that move the stack from “demo-capable” to industry-style teleoperation.

---

## Priority order (do these first)

1. **Motors**: re-verify spin / Spark / measured RPM (WebUI + sim-chair); chase degradation and right-tilt  
2. **IMU → D-BOX**: done 2026-10-14; next is tuning with more drivers and stronger accel if Marvin's speed cap is raised  
3. **Video quality**: UDP JPEG at 720p30 is in; next H.265 NVENC / ZED stream for bandwidth  
4. **Closed-loop velocity**: restore reliable `--velocity` (encoders / Spark PID) so duty is not permanent  
5. **Latency**: measure glass-to-glass on **direct** Tailscale; target &lt;150 ms median  
6. **Keep mirrors in sync**: edit in `cursor-test\jetson\`, push to `~/Documents/SimChair_Teleop/`

---

## Upgrade phases (current → target)

| Subsystem | Current | Target | Direction |
|-----------|---------|--------|-----------|
| **Video** | Chunked JPEG/UDP, 1280×720 @ 30 | H.265 NVENC, RTP/UDP, ≥1080p | ZED stream / GStreamer RTP |
| **Control** | UDP CSV ~20 Hz; **duty** default | Seq + timestamps; reliable velocity PID | Failsafe + encoder bring-up |
| **Haptics** | Working 2026-10-14 (encoder + gyro cues) | Classical washout; ramp to neutral on loss | UDP 5007 → washout → D-BOX |
| **Motors** | Duty works; velocity/purple issues; tilt | Sustained smooth closed-loop | Teensy/Spark A/B debug |
| **Ops** | Manual tmux; iptables lost on reboot | systemd + iptables-persistent | Demo reliability |

**Biggest single win for video next:** keep UDP JPEG as fallback; adopt hardware H.265 so bandwidth drops at higher resolution.

---

## Industry reference (what “done” looks like)

Commercial remote-driving stacks converge on:

- Hardware-encoded video over UDP (lost packet = one frame, not a stall)
- Fixed-rate control with sequence numbers and multi-layer watchdogs (stop in ~250-500 ms of silence)
- Motion platforms with classical washout filtering
- Supervised services that auto-restart and fail safe

Campus Tailscale is fine for demos; bonded cellular is the commercial WAN pattern.

---

## Integration milestones

| Milestone | Pass criteria |
|-----------|---------------|
| Haptics stands test | Brake pitch / cornering roll / bump heave felt in chair |
| Control failsafe | Cable pull → motors stop &lt;300 ms; re-arm required |
| Video Phase 1 | ≥720p, ≥30 fps, glass-to-glass &lt;150 ms, bandwidth &lt;25 Mbps (3 cams) |
| Soak | ≥30 min simultaneous cameras + control + haptics without motor collapse |
| Ops | Cold boot → operational with zero manual tmux |

---

## Constraints that stay

- Never modify `/home/dinosaur/IGVC/`
- Teleop scripts: Jetson `~/Documents/SimChair_Teleop/` · Windows `cursor-test\windows\`
- Prefer lab-accurate claims over symposium language until metrics are filled in [MEASUREMENTS.md](../MEASUREMENTS.md)

---

**See also:** [TARGET_ARCHITECTURE.md](../TARGET_ARCHITECTURE.md) · [KNOWN_ISSUES_AND_HISTORY.md](../KNOWN_ISSUES_AND_HISTORY.md) · [MEASUREMENTS.md](../MEASUREMENTS.md)
