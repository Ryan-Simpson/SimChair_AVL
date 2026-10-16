# Archived docs (out of date; kept for history)

These describe setups that are no longer used, or deadlines that have passed.
For how things work now, start at [docs/README.md](../README.md). Moved here
2026-10-16; links inside these files point to where things were when they were
written and may be broken.

| Doc | Written | Why it's archived |
|---|---|---|
| `HANDOFF_GUIDE.md`, `KICKOFF_PROMPT.md` | 2026-07 | Instructions for an AI session working toward the 2026-08-06 demo. Done. |
| `TARGET_ARCHITECTURE.md` | 2026-07-18 | Two-week upgrade plan (H.265, hardening) for the August demo. The video plan was replaced by WebRTC over the peer relay. |
| `NETWORK_OPTIONS.md` | 2026-07-18 | Tailscale direct vs DERP on campus. Replaced by the Vultr peer relay: [RELAY_TELEOP_2026-10-10.md](../RELAY_TELEOP_2026-10-10.md) §2. |
| `LAUNCH_PROCEDURE.md` | 2026-08-07 | Start/stop for JPEG/UDP video and `orin_vehicle_controller`. Now: [START_TELEOP.md](../START_TELEOP.md). |
| `CONTROL_PROTOCOL.md` | 2026-08-07 | Teensy ownership between the WebUI and `orin_vehicle_controller`. Now actuator_node is the only Teensy owner (rule kept in the main README). |
| `PERCEPT_STACK_AND_SIMCHAIR.md` | 2026-08-24 | "percept-stack owns the cameras, attach only". The relay stack now starts its own ZEDs. |
| `H265_BRINGUP.md` | 2026-09-04 | ZED SDK H.265 streams; 3 streams over Tailscale never worked. Replaced by WebRTC. |
| `FRESH_CHAT_VIDEO_PROMPT.md` | 2026-09-04 | Prompt that started the video redesign. That redesign is the current WebRTC stack. |
| `SESSION_HANDOFF_CONTEXT_LOSS.md` | 2026-09-04 | Snapshot of paths/ports from September. |
| `SYSTEM_OVERVIEW.txt` | 2026-08-06 | Long-form overview of the JPEG-era system. |
| `PROJECT_OVERVIEW.md` | 2026-07 | Goals and hardware; the main README now covers this. |
| `ABSTRACT.md`, `CARS_ABSTRACT_DRAFTS.md` | 2026-09 | CARS 2026 abstract text and drafts (submitted). |
| `2026-08_cohort/deliverables/`, `2026-08_cohort/deck/` | 2026-08-07 | Summer cohort final deliverables: report, slides, demo script, handoff package (submitted). |
| `CARS_Poster/` | 2026-09 | Symposium poster sources and assets. |
