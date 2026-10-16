# Network Link: Tailscale Constraints and Alternatives

Decision doc for the vehicle ↔ operator-station link. Written July 18, 2026.

## Current: Tailscale (keep it)

Tailscale is WireGuard underneath. It gives us drive-from-anywhere plus zero
firewall/NAT configuration, and on campus it negotiates a direct peer-to-peer
path with ~1ms overhead. Two constraints to engineer around:

### Constraint 1 — MTU is 1280 bytes
Any packet larger than 1280 bytes gets fragmented, and fragmented UDP over a
tunnel is a recipe for stutter and loss amplification. **Rule: every UDP
payload we send must stay ≤1200 bytes.**

- ZED SDK streaming: set `chunk_size: 1200` (or nearest supported value)
- GStreamer RTP: set `rtph264pay mtu=1200`
- Control/IMU packets: tiny already, no action needed

This may explain some past streaming weirdness — check this FIRST when video
misbehaves over Tailscale.

### Constraint 2 — DERP relay fallback
If Tailscale can't punch through NAT it silently relays traffic through a DERP
server, adding 50ms+ and killing throughput. **Verify every session:**

```
tailscale ping 100.93.121.3     # from Windows
tailscale status                 # connection column must say "direct"
```

If relayed: check UDP not blocked by campus firewall; try `tailscale netcheck`.

## Alternatives (evaluated, mostly rejected)

| Option | MTU | Verdict |
|---|---|---|
| **Tailscale + chunk_size 1200** | 1280 | ✅ **Default.** Zero migration cost, works anywhere |
| **Dedicated local LAN (no VPN)** | 1500 | ✅ **Demo-day fallback + debug tool** — see below |
| Plain self-hosted WireGuard | ~1420 | ❌ Manual keys/NAT traversal for 220 bytes of MTU — not worth it |
| ZeroTier | ~2800 | ❌ Migration mid-sprint to solve an already-solved problem |
| Bonded cellular (DriveU-style) | n/a | ❌ Industry-correct for public roads; overkill for campus |

## The LAN fallback profile (worth 1 hour to set up)

For demo day, kart and operator station are within WiFi range. A dedicated
router (or Ethernet while the kart is on stands) gives full 1500 MTU,
sub-millisecond latency, and no tunnel at all.

- All senders/receivers are IP-based → switching = swapping Tailscale IPs for
  LAN IPs. Keep a config flag or a second copy of configs: `PROFILE=tailscale`
  vs `PROFILE=lan`.
- Security: acceptable on an isolated demo LAN (no internet uplink needed).
- **Debug value:** if video is smooth on LAN but bad over Tailscale, the
  network is the variable, not your pipeline. Fastest possible isolation test.

## Session checklist

1. `tailscale status` on both machines — logged in, peer visible
2. `tailscale ping <peer>` — must say **direct**, expect single-digit ms
3. Video payloads ≤1200 bytes (chunk_size / mtu settings)
4. iptables rules present on Jetson (until systemd/persistent setup lands)
