"""
windows_haptic_receiver.py  —  run on Windows sim-chair
Receives imu_bridge.py UDP (port 5007), runs classical washout, prints cues.

ZED camera IMUs often have gravity mostly in X/Y (mount tilt). Without bias
removal, pitch pegs at the comfort limit. We average ~2 s at start and subtract.
"""

from __future__ import annotations

import argparse
import math
import socket
import struct
import time

UDP_PORT = 5007
PACKET_FMT = '<IQ8f'  # seq + t_ms + 8 floats = 44 bytes
PACKET_SIZE = struct.calcsize(PACKET_FMT)
WATCHDOG_S = 0.5
COMFORT = 0.5
CALIB_S = 2.0  # hold kart still for this long at start


class WashoutFilter:
    """Classical washout on *bias-removed* accel + attitude deltas."""

    def __init__(self, sample_hz: float = 50.0, comfort: float = 0.5):
        self.dt = 1.0 / sample_hz
        self.comfort = comfort
        self.lpf_ax = self.lpf_ay = 0.0
        self.hpf_az = self.prev_az = 0.0
        self.out_p = self.out_r = self.out_h = 0.0

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return dt / (tau + dt)

    def update(self, ax: float, ay: float, az: float, roll: float, pitch: float):
        a_tilt = self._alpha(0.8, self.dt)
        a_heave = self._alpha(1.5, self.dt)

        self.lpf_ax += a_tilt * (ax - self.lpf_ax)
        self.lpf_ay += a_tilt * (ay - self.lpf_ay)

        pitch_t = -0.15 * self.lpf_ax / 0.35
        roll_t = 0.20 * self.lpf_ay / 0.35
        pitch_t = 0.7 * pitch_t + 0.3 * max(-1.0, min(1.0, pitch / 0.35))
        roll_t = 0.7 * roll_t + 0.3 * max(-1.0, min(1.0, roll / 0.35))

        self.hpf_az = a_heave * (self.hpf_az + az - self.prev_az)
        self.prev_az = az
        heave_t = 0.25 * self.hpf_az

        lim = self.comfort
        pitch_t = max(-lim, min(lim, pitch_t))
        roll_t = max(-lim, min(lim, roll_t))
        heave_t = max(-lim, min(lim, heave_t))

        rate = 3.0 / 20.0
        for target, attr in ((pitch_t, 'out_p'), (roll_t, 'out_r')):
            cur = getattr(self, attr)
            delta = max(-rate * self.dt, min(rate * self.dt, target - cur))
            setattr(self, attr, cur + delta)
        self.out_h = heave_t
        return self.out_p, self.out_r, self.out_h

    def ramp_neutral(self):
        rate = self.comfort / 1.0
        for attr in ('out_p', 'out_r', 'out_h'):
            cur = getattr(self, attr)
            step = max(-rate * self.dt, min(rate * self.dt, -cur))
            setattr(self, attr, cur + step)
        return self.out_p, self.out_r, self.out_h


def main():
    parser = argparse.ArgumentParser(description='IMU washout haptic receiver (console)')
    parser.add_argument('--port', type=int, default=UDP_PORT)
    parser.add_argument('--comfort', type=float, default=COMFORT)
    parser.add_argument('--calib', type=float, default=CALIB_S,
                        help='Seconds to average gravity bias at start (kart still)')
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', args.port))
    sock.settimeout(0.05)

    washout = WashoutFilter(comfort=args.comfort)
    last_seq = 0
    last_packet = time.monotonic()
    last_stats = time.monotonic()
    watchdog_latched = False

    bias_ax = bias_ay = bias_az = 0.0
    bias_roll = bias_pitch = 0.0
    calib_n = 0
    calib_sum = [0.0] * 5  # ax ay az roll pitch
    calib_done = False
    calib_t0 = None

    print('=' * 60)
    print(' SimChair haptic receiver (washout console)')
    print(f' UDP {args.port}  comfort={args.comfort}  watchdog={WATCHDOG_S}s')
    print(f' Hold kart STILL for {args.calib:.1f}s to zero gravity bias')
    print(' Then rock/drive → pitch/roll/heave should move around 0')
    print('=' * 60)

    while True:
        now = time.monotonic()
        try:
            data, addr = sock.recvfrom(128)
        except socket.timeout:
            if now - last_packet > WATCHDOG_S:
                p, r, h = washout.ramp_neutral()
                if not watchdog_latched:
                    print(f'WATCHDOG → ramp neutral  pitch={p:+.3f} roll={r:+.3f} heave={h:+.3f}')
                    watchdog_latched = True
            continue

        if len(data) < PACKET_SIZE:
            continue

        seq, t_ms, ax, ay, az, gx, gy, gz, roll, pitch = struct.unpack(
            PACKET_FMT, data[:PACKET_SIZE])
        if seq <= last_seq:
            continue

        last_seq = seq
        last_packet = now
        watchdog_latched = False

        if not calib_done:
            if calib_t0 is None:
                calib_t0 = now
                print('Calibrating bias… keep still')
            calib_sum[0] += ax
            calib_sum[1] += ay
            calib_sum[2] += az
            calib_sum[3] += roll
            calib_sum[4] += pitch
            calib_n += 1
            if now - calib_t0 >= args.calib and calib_n > 10:
                bias_ax = calib_sum[0] / calib_n
                bias_ay = calib_sum[1] / calib_n
                bias_az = calib_sum[2] / calib_n
                bias_roll = calib_sum[3] / calib_n
                bias_pitch = calib_sum[4] / calib_n
                calib_done = True
                print(
                    f'Bias locked  acc=({bias_ax:+.2f},{bias_ay:+.2f},{bias_az:+.2f})  '
                    f'att=({bias_roll:+.2f},{bias_pitch:+.2f})  n={calib_n}'
                )
            elif now - last_stats >= 0.5:
                print(f'  calib… {now - calib_t0:.1f}/{args.calib:.1f}s  acc=({ax:+.2f},{ay:+.2f},{az:+.2f})')
                last_stats = now
            continue

        dax = ax - bias_ax
        day = ay - bias_ay
        daz = az - bias_az
        droll = roll - bias_roll
        dpitch = pitch - bias_pitch

        p, r, h = washout.update(dax, day, daz, droll, dpitch)

        if now - last_stats >= 0.2:
            print(
                f'#{seq}  pitch={p:+.3f}  roll={r:+.3f}  heave={h:+.3f}  '
                f'dacc=({dax:+.2f},{day:+.2f},{daz:+.2f})  from {addr[0]}'
            )
            last_stats = now


if __name__ == '__main__':
    assert PACKET_SIZE == 44, PACKET_SIZE
    main()
