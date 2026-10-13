# Relay teleop: drive + 3-camera WebRTC over cellular (2026-10-08 → 10-12)

**Operator:** Ryan Simpson / AVL  
**Status:** Driving Marvin from the D-BOX sim chair with 3 live ZED X cameras works,
indoors, at **1.2 Mbps total video** on a good day. Since 2026-10-12 the bitrate is
**adaptive** (§4a): on a bad day (~250 kbps) the side cameras pause and the front
stays live. Outdoor test still to do.

Scripts: [`jetson/relay_teleop/`](../jetson/relay_teleop/) ·
Viewer: [`windows/multicam_viewer.html`](../windows/multicam_viewer.html) ·
Bridge: [`jetson/orin_simchair_ros_bridge.py`](../jetson/orin_simchair_ros_bridge.py)

---

## 1. TL;DR

| What | Result |
|---|---|
| Network path | Sim chair ↔ **Vultr LA Tailscale Peer Relay** ↔ Marvin (AT&T cellular). Control RTT median **38 ms** (was 132 ms on DERP). |
| Drive | Sim chair → UDP 5006 → bridge → `/avros/actuator_command` → actuator_node → Teensy. ~20 Hz, steering + throttle + brake(=reverse) correct. |
| Video | 3 × ZED X → `avros_webrtc` (NVENC H.264) → MediaMTX → Chrome (WHEP). 480×300, front 7.5 fps, sides 15 fps. |
| **Video budget** | **1.2 Mbps total best indoors** (front 500 / sides 350 kbps). 1.5 works but spikier. **1.8 collapses in ~3 s.** |
| Biggest lesson | Over capacity, cellular doesn't drop — it **queues**. Video *and drive commands* arrive 1–9 s late. |
| **Adaptive bitrate** (10-12) | `rate_controller` pings the sim chair, cuts bitrate when RTT rises, pauses side cams if still clogged. Same signal, ~5× less capacity than 10-10 → front-only held at 7.5 fps, RTT median 53 ms. |

---

## 2. Network: why a peer relay

Tailscale could not go direct between the two ends:

- **Campus (Cal Poly Pomona, Ethernet on the sim chair PC)** blocks unsolicited
  inbound UDP **and** outbound UDP except a few ports. Verified open: **3478, 4500**.
  Blocked: 41641, 40000, 443, 51820, 12345. (pktmon showed zero inbound packets
  from the kart; a Windows firewall rule alone did nothing.)
- **AT&T cellular on Marvin** is behind carrier NAT.
- Result: traffic fell back to Tailscale **DERP** (shared relay, TCP-ish, 80–240 ms).
  Campus IT ticket ruled out.

**Fix:** our own Tailscale Peer Relay on a small VPS, listening on the two UDP
ports campus allows.

| Item | Value |
|---|---|
| Host | Vultr `vc2-1c-1gb`, **Los Angeles**, Ubuntu 24.04 (~$5/mo) |
| Public IP / tailnet | `66.42.96.149` / `100.70.103.45`, hostname `avros-relay`, `tag:relay` |
| SSH | root, **key only** (`/etc/ssh/sshd_config.d/00-keyonly.conf`) |
| Firewall (ufw) | 22/tcp, 3478/udp, 4500/udp only |
| tailscaled port | `PORT="3478"` in `/etc/default/tailscaled` |
| Relay port | `tailscale set --relay-server-port=4500` |
| A/B toggle | `tailscale set --relay-server-port=""` (off) / `=4500` (on) |

Tailnet policy additions (admin console → Access controls), everything else default:

```json
"tagOwners": { "tag:relay": ["autogroup:admin"] },
"grants": [
  { "src": ["100.93.121.3", "100.91.25.107"], "dst": ["tag:relay"],
    "app": { "tailscale.com/cap/relay": [] } }
]
```

Check from the sim chair: `tailscale ping 100.93.121.3` → expect
`via peer-relay(66.42.96.149:4500:vni:…)` in ~40–50 ms.

> This supersedes the "must be **direct**" checks in
> [NETWORK_OPTIONS.md](NETWORK_OPTIONS.md) and [MEASUREMENTS.md](MEASUREMENTS.md)
> for the campus ↔ cellular case: direct is impossible there; **peer-relay is the target**.

### Measured (2026-10-09, kart stationary, 20 Hz UDP echo, 3-min rounds)

| Path | Median | p95 | p99 | Loss |
|---|---|---|---|---|
| **Peer relay** (R1) | **38 ms** | 53 | 75 | 0% |
| DERP lax (R2) | 132 ms | 193 | 203 (max 499) | 0% |
| **Peer relay** (R3) | **38 ms** | 54 | 76 | 0.03% |

---

## 3. How to run it

### Jetson (Marvin)

```bash
# copy jetson/ to the Jetson, then:
bash jetson/relay_teleop/start_all.sh        # drive + 3 cams, tmux session "simchair"
VIDEO_ONLY=1 bash jetson/relay_teleop/start_all.sh   # cameras only, no motors
tmux attach -t simchair                      # look at the logs
bash jetson/relay_teleop/stop_all.sh         # stop everything it started
```

`start_all.sh` starts, in order: MediaMTX, the viewer page server (:8090),
robot_state_publisher, actuator_node, the bridge, the three ZEDs (20 s apart), the rate controller, then the three
encoders (**4 s apart**). `FIXED_BITRATE=1` skips the rate controller.
It only touches its own tmux session, so it doesn't disturb other people's
processes on the Jetson. Requirements: nothing else owns the Teensy (WebUI /
`avros-webui` stopped) and nothing else runs the ZEDs (percept stack down).

| Script | Does |
|---|---|
| `run_actuator.sh` | `actuator.launch.py` only — no WebUI, so the chair is the only commander |
| `run_bridge_live.sh` | chair → `/avros/actuator_command`, **watchdog e-stop off** (see §6) |
| `run_bridge_dry.sh` | chair → `/simchair_test/actuator_command` (nothing subscribes → no motion) |
| `run_rsp.sh` | static TF; **ZEDs hang on "Waiting for valid static transformations" without it** |
| `run_zed.sh <name> <serial>` | one ZED X with the team's `config/<name>.yaml` unchanged |
| `run_mediamtx.sh` | stock MediaMTX from `~/IGVC_webrtc/.mediamtx` |
| `run_webrtc_cam.sh <name> <fps> <bps> [side]` | `avros_webrtc` node for one camera; `side` = may be paused to 1 frame / 2 s |
| `run_rate_controller.sh <total_bps> <front_bps>` | adaptive bitrate for all encoders (§4a) |
| `run_viewer.sh` | serves `windows/multicam_viewer.html` at `http://<jetson>:8090/` |

Camera serials: front **42569280**, left **43779087**, right **49910017**.

### Sim chair PC

1. Start `windows/simchair_sender_dbox.exe` (sends `steering,throttle,brake,mode` to `100.93.121.3:5006`, ~20 Hz).
2. Open **http://100.93.121.3:8090/** in Chrome (served by the Jetson). **Close every other
   video tab.** Don't double-click the .html file: a `file://` page sends `Origin: null`,
   which MediaMTX's CORS rejects → "Failed to fetch".
3. Chair: **park (0)** once to arm the bridge → **drive (1)**. Brake = reverse.

Single camera instead: `http://100.93.121.3:8889/zed_front` (MediaMTX's own page).

---

## 4. Results

### Drive (2026-10-09 dry run, 2026-10-10 live)

- 19.5–19.7 Hz command rate at the bridge, median gap 50 ms, largest gap 0.55 s while healthy.
- Steering: wheel right → sender `+` → bridge negates → `−` = right turn (REP-103). ✅
- Throttle/brake full range; `v = (throttle − brake) × max_v` → brake drives in reverse (kept on purpose — Marvin is slow and it's intuitive).
- actuator_node caps: 0.4 m/s, 1.5 rad/s, gentle accel. "Felt good."

### Video — single front camera (2026-10-10)

| Bitrate | Steady-state | Notes |
|---|---|---|
| 1.5 Mbps | ~7.5 fps, RTT median 40–130 ms, spikes 300–400 ms, jitter buffer 100–230 ms | First ~20 s: RTT 350–1100 ms. Then link froze 4 min when a 2nd viewer was added. |
| 0.8 Mbps | stable while driving | |

### Video — 3 cameras, bitrate ladder (2026-10-10 evening, indoors, driving slowly)

Ping = independent 5 Hz ICMP from the sim chair during each run.

| Total | Front / side kbps | Ping median / p95 / max | Video RTT p95 (worst cam) | Side jitter buffer p95 | Freezes | Verdict |
|---|---|---|---|---|---|---|
| 0.9 Mbps | 300 / 300 | 53 / 527 / 1335 ms* | 250 ms | **~1.5 s** | 3 | OK, but sides laggy |
| **1.2 Mbps** | **500 / 350** | **56 / 166 / 670 ms** | 270 ms | ~160 ms | 4 | **Best** |
| 1.5 Mbps | 600 / 450 | 58 / 245 / 951 ms | 362 ms | ~120 ms | 12 | Works, frays |
| 1.8 Mbps | 800 / 500 | collapsed | 1.5–9.5 s | — | — | **Collapses ~3 s after 3rd stream** |

\* 0.9 run started all 3 streams at once (startup spike included); later runs staggered 4 s.

All runs: 0 packet loss until collapse; decode < 1 ms; 480×300.

Jetson load with all 3 cameras streaming: CPU ~23 % avg (12 cores), GPU 43 %, RAM 4.7/62 GB,
51 °C. Front ZED process ~94 % of one core (depth on), sides ~30 % each, each encoder ~7 %.

### Cellular radio (AirLink ACEmanager, indoors, during the ladder test)

| | Value | Meaning |
|---|---|---|
| Carrier / tech | AT&T, LTE-Advanced Pro (4G) | |
| Band | **LTE Band 2** (1900 MHz) | high band, poor building penetration |
| RSRP | **−111 dBm** | weak (good ≈ −80 to −90) |
| RSRQ | −13 dB | fair–poor |
| SINR | **0.3 dB** | very poor (good > 13) |
| Bars | 2 | |

On 2026-10-09 the upload measured ~4.5–5 Mbps; today indoors the ceiling was ~1.5.
Hypothesis (user): **indoors vs outdoors**. Next session: log RSRP/SINR/band
outdoors and rerun the ladder (1.2 → 1.8 → 2.5 → 3 Mbps).

---

## 4a. Adaptive bitrate (2026-10-12, indoors, raining)

Code: `rate_controller` + live bitrate in `avros_webrtc` (IGVC_ROS2
`feature/avros-webrtc`, commit `4c00046`; details in its README).

```
rate_controller: ping sim chair 5x/s over Tailscale
  queue delay = median RTT (1 s) - min RTT (120 s)
  > 200 ms or > 40% ping loss -> scale x0.7 (1/s)    > 800 ms -> floor 0.25
  < 80 ms for 2 s while video flows -> +2 %/s       range 0.25-1.5, start 0.6
  still clogged 3 s at the floor -> side cams to 1 frame / 2 s
  resume sides after 15 s calm once front alone >= 1.3x the 3-cam floor
-> /webrtc/bitrate_scale, /webrtc/sides_enabled -> each encoder: bitrate_bps x scale (live)
```

`nvv4l2h264enc` accepts a new `bitrate` while PLAYING (gst-inspect says
READY-only): noise test 1000→200→1000→400 kbps measured 1074→318→1112→492, ~1 s to apply.

**The link that day.** Same radio as 10-10 but much less capacity —
looks like a busy cell, not Marvin's position:

| | 10-10 | 10-12 |
|---|---|---|
| RSRP / RSRQ / SINR | −111 / −13 / 0.3 dB | −107 / −12 / **6.2 dB** |
| Band, bars | LTE B2, 2 | LTE B2, 2 |
| Video the link held | ~1.2 Mbps | **~200–300 kbps** |
| Idle ping (no video) | 56 ms | swung 55 ms ↔ 940 ms / 30 % loss within minutes; once ~10 kbps throughput |

**Drives** (viewer on the sim chair, slow speed, e-stop operator):

| Run | Result |
|---|---|
| Fixed 1.2 Mbps | front connected, no frames, viewer auto-cutoff in ~15 s |
| AIMD only (no side pause) | controller pinned at floor; 0.25 × 1.2 Mbps = **~480 kbps actually sent** (NVENC overshoots small CBR targets + IDR every 1 s + overhead). Ping p95 488 ms, max 2.3 s, 6 % loss; viewer cutoff after ~7 min |
| **AIMD + side pause** | sides paused within ~1 min and stayed paused. **Front: 7.5 fps, 0 stalled samples, video RTT median 53 / p95 256 / max 1183 ms, 0 loss** (last ~100 s). Ping over the drive: median 53, p95 852, max 3404 ms — spikes mostly in the first 3–4 min while it searched |

Lessons:
- Lowering the floor further doesn't help — the encoder won't go that low.
  Dropping cameras does. Sides are ~60 % of the load.
- Start lower (0.3) and pause the sides sooner (~1.5 s) to cut the first-minute spikes.
- The Jetson went dark once mid-drive with the router still up; journal ends
  abruptly (no shutdown), power cycle fixed it. Consistent with the known
  shared-12 V brown-out (IGVC_ROS2 CLAUDE.md), not confirmed.
- 10-11: the Vultr relay stopped (no shutdown logged); after restart DNS was
  broken because tailscaled rewrote resolv.conf — fixed with
  `tailscale set --accept-dns=false` and relinking `/etc/resolv.conf` to
  `../run/systemd/resolve/stub-resolv.conf`. Without the relay the link falls
  back to DERP (125–141 ms) and video freezes.

---

## 5. What went wrong (and the lessons)

1. **Over capacity = huge delay, not loss.** Fixed-bitrate (CBR) video has no
   congestion control. When the cell uplink shrinks, the modem queue grows to
   seconds. Commands share that uplink, so they arrive **late**:
   at 8:23:45 PM the lag was 1.4–1.8 s while driving at full throttle; at 1.8 Mbps RTT
   reached 9.5 s. The missing-packet watchdog **cannot** see this (packets keep coming).
2. **Every extra viewer doubles that camera's upload.** A forgotten MediaMTX tab
   pushed a 1.5 Mbps stream over the edge → 4-minute link freeze (8:10–8:15 PM).
   Closing the video brought the link back within seconds — twice.
3. **Starting all streams at once** → ~20 s lag spike (simultaneous keyframes).
   Staggering by 4 s removed it.
4. **Low bitrate + 1 s keyframes at 15 fps** → keyframes go out as bursts →
   browser jitter buffer swells to 1.5 s on the side cams. 350 kbps fixed it.
5. **ZED wrapper hangs** on "Waiting for valid static transformations" when
   `sensors.launch.py` (robot_state_publisher) isn't running → `run_rsp.sh`.
6. **`Gst.Fraction(...)` fails on the Jetson's PyGObject** → `avros_webrtc` now
   writes the framerate caps as integers (`fps×1000/1000`). Commit `4d75c4f`
   on `feature/avros-webrtc` (IGVC_ROS2).
7. **Router web UI looks broken** through an SSH tunnel: the AirLink web server
   returns **503** on parallel requests, so half the CSS/JS never loads. Load
   it one file at a time, or reload until it works.

---

## 6. Safety configuration (current)

| Layer | Setting |
|---|---|
| Physical | **Remote e-stop operator present** for every drive (slow-speed tests). |
| Bridge watchdog | **Off** for now (`--watchdog-ms 1e9`, user's call). Code supports it: no packet for 450 ms → latched e-stop, re-armed by park. 450 ms clears the sender's ~300 ms pause on each mode switch (300 ms tripped falsely). Re-enable: `WATCHDOG_MS=450 bash run_bridge_live.sh`. |
| Bridge startup | Latched until the chair sends **park** once. |
| actuator_node | Stops motors if no command for 0.5 s (doesn't latch). |
| Not covered | **Late** commands during uplink congestion (§5.1). Discussed a "stale command" check (drop commands older than ~300 ms, using a separate RTT probe or sender timestamps) — **parked** for now. |

---

## 7. Cellular router (Sierra Wireless AirLink, ALEOS 4.18.1)

- LAN `192.168.13.31`; Orin `.10` (DHCP reservation), Velodyne `.11`.
  Setup doc: `AirLink_Orin_Velodyne_Networking_Setup_Professional-1.docx`.
- **ACEmanager is on port 9443** (not 443): from the sim chair,
  `ssh -N -L 9443:192.168.13.31:9443 dinosaur@100.93.121.3` then `https://localhost:9443`.
  Signal: **Status → Cellular**.
- ⚠️ Still on the **default admin password** and **AAF development mode**.
  Agree a new password as a team and record it somewhere private (not in this repo).

---

## 8. Next steps

1. **Outdoor test** with RSRP/SINR/band logged, now with adaptive bitrate on
   (`MAX_SCALE` up to 2–3 to see what a good link allows).
2. ~~Adaptive bitrate~~ done 10-12 (§4a). Tune: start 0.3, pause sides after ~1.5 s.
3. Small video tweaks: minimal browser jitter buffer, longer side-cam IDR interval.
   Maybe drop side fps when scale is low instead of a hard pause.
4. Stale-command protection (§6) before any faster or unsupervised driving.
5. Merge `feature/bridge-watchdog` and `feature/avros-webrtc` once reviewed.
