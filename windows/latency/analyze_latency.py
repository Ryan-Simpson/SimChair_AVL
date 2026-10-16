"""analyze_latency.py — latency study timeline (Step 1, 2026-10-15).

Joins whatever logs a run produced into one time-binned table plus a summary:

  --owd     logs/imu_owd_*.csv from imu_haptic_receiver.exe (required)
            queue_ms = owd_raw - baseline, where owd_raw = PC arrival - Jetson send
            time of each 25 Hz IMU packet. The packets share Marvin's cellular
            upload with the video, so queue_ms is the upload queue. No clock
            sync is needed; only the drift between the two clocks matters, and
            it is reported (and removable with --baseline drift).
  --viewer  marvin_video_stats_*.json from the viewer's "Save stats" button
  --marvin  marvin_1hz.csv from /tmp/drive_log.py (upload kbps, ping, GPS)
  --router  router_*.csv from router_poll.js (RSRP / SINR / cell id)
  --g2g     g2g CSV of glass-to-glass readings: sample,live,filmed (SS.mmm each)

Usage:
  python analyze_latency.py --owd logs/imu_owd_20261015_210000.csv \\
      --viewer marvin_video_stats_....json --bin 10
"""
import argparse
import csv
import json
import statistics as st


def pct(v, p):
    if not v:
        return float('nan')
    v = sorted(v)
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]


def load_owd(path, baseline):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append((int(r['pc_ms']) / 1000.0, int(r['seq']), int(r['owd_raw_ms'])))
    if not rows:
        raise SystemExit(f'{path}: no packets')
    t0 = rows[0][0]
    # per-minute minima -> clock drift estimate (ms per minute)
    mins = {}
    for t, _, o in rows:
        k = int((t - t0) // 60)
        mins[k] = min(mins.get(k, o), o)
    ks = sorted(mins)
    drift = 0.0
    if len(ks) >= 3:
        mx, my = st.mean(ks), st.mean(mins[k] for k in ks)
        den = sum((k - mx) ** 2 for k in ks)
        drift = sum((k - mx) * (mins[k] - my) for k in ks) / den if den else 0.0
    slope = drift if baseline == 'drift' else 0.0
    resid = [(t, s, o - slope * (t - t0) / 60.0) for t, s, o in rows]
    base = min(r for _, _, r in resid)
    out = [(t, s, r - base) for t, s, r in resid]
    lost = 0
    seqs = [s for _, s, _ in rows]
    for a, b in zip(seqs, seqs[1:]):
        if 1 < b - a < 1000:
            lost += b - a - 1
    return out, drift, lost


def load_viewer(path):
    d = json.load(open(path))
    cams = {}
    for c, samples in d['cams'].items():
        cams[c] = [dict(s, t=s['wall'] / 1000.0) for s in samples]
    return cams


def cam_bin(samples, lo, hi):
    s = [x for x in samples if lo <= x['t'] < hi]
    if len(s) < 2:
        return None
    a, b = s[0], s[-1]
    dt = b['t'] - a['t']
    if dt <= 0:
        return None
    jbe = b['jbe'] - a['jbe']
    return {
        'fps': (b['fd'] - a['fd']) / dt,
        'kbps': (b['bytes'] - a['bytes']) * 8 / dt / 1000,
        'lost': b['lost'] - a['lost'],
        'frz': b['frz'] - a['frz'],
        'jb_ms': (b['jbd'] - a['jbd']) / jbe * 1000 if jbe > 0 else float('nan'),
    }


def load_csv_t(path, tcol):
    with open(path) as f:
        return [dict(r, t=float(r[tcol])) for r in csv.DictReader(f)]


def g2g_summary(path):
    vals = []
    with open(path) as f:
        for r in csv.DictReader(f):
            d = (float(r['live']) - float(r['filmed'])) % 100.0
            vals.append(d * 1000)
    if vals:
        print(f'\nGlass-to-glass ({len(vals)} samples): median {st.median(vals):.0f} ms, '
              f'min {min(vals):.0f}, p90 {pct(vals, 90):.0f}, max {max(vals):.0f}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--owd', required=True)
    ap.add_argument('--viewer')
    ap.add_argument('--marvin')
    ap.add_argument('--router')
    ap.add_argument('--g2g')
    ap.add_argument('--bin', type=float, default=10.0, help='seconds per row')
    ap.add_argument('--baseline', choices=['global', 'drift'], default='global')
    a = ap.parse_args()

    owd, drift, lost = load_owd(a.owd, a.baseline)
    t0, t1 = owd[0][0], owd[-1][0]
    q = [x[2] for x in owd]
    dur = t1 - t0
    print(f'Run {dur:.0f} s, {len(owd)} IMU packets, {lost} lost, clock drift {drift:+.1f} ms/min '
          f'({drift * dur / 60:+.0f} ms over the run{"; removed" if a.baseline == "drift" else ""})')
    print(f'Upload queue: median {st.median(q):.0f} ms, p90 {pct(q, 90):.0f}, p99 {pct(q, 99):.0f}, '
          f'max {max(q):.0f}; >500 ms {sum(x > 500 for x in q) / len(q) * 100:.1f}% of packets')

    cams = load_viewer(a.viewer) if a.viewer else {}
    mv = load_csv_t(a.marvin, 'wall') if a.marvin else []
    rt = load_csv_t(a.router, 'wall') if a.router else []

    hdr = f'{"t(s)":>6} {"queue med/max":>13} {"gap ms":>6}'
    if mv:
        hdr += f' {"up kbps":>7}'
    if rt:
        hdr += f' {"RSRP":>5} {"SINR":>5} {"cell":>8}'
    for c in cams:
        hdr += f' | {c[4:]:>5} fps kbps frz jb'
    print('\n' + hdr)
    t = t0
    while t < t1:
        lo, hi = t, t + a.bin
        b = [x for x in owd if lo <= x[0] < hi]
        arr = [x[0] for x in b]
        gap = max((y - x for x, y in zip(arr, arr[1:])), default=float('nan')) * 1000
        line = (f'{lo - t0:6.0f} {st.median([x[2] for x in b]):6.0f}/{max(x[2] for x in b):6.0f} {gap:6.0f}'
                if b else f'{lo - t0:6.0f} {"no packets":>13} {"":>6}')
        if mv:
            m = [float(r['tx_kbps']) for r in mv if lo <= r['t'] < hi and r['tx_kbps']]
            line += f' {st.mean(m):7.0f}' if m else f' {"":>7}'
        if rt:
            r = [x for x in rt if lo <= x['t'] < hi]
            line += (f' {r[-1].get("rsrp", ""):>5} {r[-1].get("sinr", ""):>5} {r[-1].get("cell", ""):>8}'
                     if r else f' {"":>5} {"":>5} {"":>8}')
        for c, s in cams.items():
            v = cam_bin(s, lo, hi)
            line += (f' | {v["fps"]:9.1f} {v["kbps"]:4.0f} {v["frz"]:3d} {v["jb_ms"]:3.0f}'
                     if v else f' | {"n/a":>9} {"":>4} {"":>3} {"":>3}')
        print(line)
        t = hi
    if a.g2g:
        g2g_summary(a.g2g)


if __name__ == '__main__':
    main()
