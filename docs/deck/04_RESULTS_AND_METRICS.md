# Results and Metrics: Marvin Sim Chair

Baseline recorded **2026-07-27** (Ryan Simpson / AVL). TCP JPEG re-verified **2026-08-04**. UDP JPEG primary path introduced **2026-08-07**. Numbers below are lab measurements: do not invent values for TBD rows.

**Link:** Windows `100.91.25.107` ↔ Jetson `100.93.121.3` (Tailscale)

---

## Verified capabilities

| Feature | Result | Notes |
|---------|--------|-------|
| Sim-chair wheel/pedal input | Working | SDL2 → `simchair_sender_dbox.exe` |
| UDP control to Jetson | Working | Port 5006 over Tailscale |
| Vehicle controller → Teensy | Working | Serial 115200; default `--duty` (`UL`/`UR`) |
| Three-camera JPEG streaming | Working | **UDP** 9001-9003 chunked JPEG (TCP legacy) |
| D-BOX SDK on Windows | Working | LiveMotion app key integrated |
| ZED multi-camera launch | Working | 25 s stagger; TF/URDF flags required |
| Vehicle IMU → D-BOX chair | Not yet verified E2E | Bridge script ready (`imu_bridge.py`) |

---

## Network (baseline)

| Metric | Value | Notes |
|--------|-------|-------|
| Tailscale path | **DERP relay (lax)** | Target: **direct** (relay adds ~50-100 ms) |
| Tailscale ping RTT | **88-112 ms** (10 samples) | From sim-chair, 2026-07-27 |
| Direct peer connection | No (at baseline) | Fix NAT/firewall before latency demo claims |

---

## Video

| Metric | TCP baseline (2026-08-04) | UDP primary (2026-08-07) | Next target |
|--------|---------------------------|--------------------------|-------------|
| Resolution | ~960×600 display | **1280×720** encode target | 1920×1200 / H.265 |
| Frame rate | **15 fps** cap | **30 fps** target | 30+ sustained |
| Codec / transport | JPEG / TCP | JPEG / **UDP** (chunked) | H.265 / RTP-UDP |
| Glass-to-glass latency | **TBD** | **TBD** | &lt;150 ms median |
| Total bandwidth (3 cams) | **TBD** | **TBD** | &lt;25 Mbps |

---

## Control (UDP :5006)

| Metric | Baseline | Target |
|--------|----------|--------|
| Packet format | `steering,throttle,brake,mode` | Add `seq`, `timestamp_ms` |
| Send rate | ~20 Hz (SDL loop) | 50 Hz fixed |
| Jetson watchdog | 400 ms | 300 ms + latched STOPPED |
| Teensy watchdog | None | 250 ms silence → zero motors |
| Failsafe (cable pull on stands) | **TBD** | Stop &lt;300 ms; re-arm required |

---

## Haptics

| Metric | Baseline | Target |
|--------|----------|--------|
| IMU topic | `/imu/data` (Xsens MTi-680G) | Same |
| Bridge rate | Script @ 50 Hz design | Confirmed 50 Hz on wire |
| IMU → chair path | Not E2E verified | UDP 5007 → washout → D-BOX |
| Packet-loss chair behavior | N/A | Ramp to neutral ≥1 s |

---

## How we measure (for filling TBDs)

**Glass-to-glass:** phone stopwatch in front of a ZED lens; photograph phone + operator monitor together; 10 samples → report median.

**Tailscale path:**

```powershell
tailscale ping 100.93.121.3
tailscale status   # must say "direct", not relay
```

**IMU rate (Jetson):** `ros2 topic hz /imu/data` with domain 42 + CycloneDDS env loaded.

---

**See also:** [MEASUREMENTS.md](../MEASUREMENTS.md) · [KNOWN_ISSUES_AND_HISTORY.md](../KNOWN_ISSUES_AND_HISTORY.md)
