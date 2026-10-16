"""
windows_imu_washout_test.py  —  run on Windows (Phase 3 dev/test)
Receives imu_bridge.py packets on UDP 5007 and prints washout-filter outputs.
Use to verify telemetry flow before building ImuHapticReceiver.exe.

Usage:
    python windows_imu_washout_test.py
"""

import math
import socket
import struct
import time

UDP_PORT = 5007
PACKET_FMT = '<IQ7f'
PACKET_SIZE = struct.calcsize(PACKET_FMT)
WATCHDOG_S = 0.5
COMFORT = 0.5
DT = 1.0 / 50.0


class WashoutFilter:
    """Python mirror of WashoutFilter.cpp for bench testing."""

    def __init__(self, sample_hz=50.0, comfort=0.5):
        self.dt = 1.0 / sample_hz
        self.comfort = comfort
        self.lpf_ax = self.lpf_ay = self.lpf_az = 0.0
        self.hpf_az = self.prev_az = 0.0
        self.out_p = self.out_r = self.out_h = 0.0

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return dt / (tau + dt)

    def update(self, ax, ay, az, roll, pitch):
        a_tilt = self._alpha(0.8, self.dt)
        a_heave = self._alpha(1.5, self.dt)

        self.lpf_ax += a_tilt * (ax - self.lpf_ax)
        self.lpf_ay += a_tilt * (ay - self.lpf_ay)

        pitch_t = -0.15 * self.lpf_ax / 0.35
        roll_t = 0.20 * self.lpf_ay / 0.35
        pitch_t = 0.7 * pitch_t + 0.3 * max(-1, min(1, pitch / 0.35))
        roll_t = 0.7 * roll_t + 0.3 * max(-1, min(1, roll / 0.35))

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


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', UDP_PORT))
    sock.settimeout(0.05)

    washout = WashoutFilter()
    last_seq = 0
    last_packet = time.monotonic()

    print(f'IMU washout test listener on port {UDP_PORT}')
    while True:
        try:
            data, addr = sock.recvfrom(128)
        except socket.timeout:
            if time.monotonic() - last_packet > WATCHDOG_S:
                washout.ramp_neutral()
                print('WATCHDOG → ramp neutral')
                last_packet = time.monotonic()  # avoid spam
            continue

        if len(data) < PACKET_SIZE:
            continue

        seq, t_ms, ax, ay, az, gx, gy, gz, roll, pitch = struct.unpack(
            PACKET_FMT, data[:PACKET_SIZE])
        if seq <= last_seq:
            continue
        last_seq = seq
        last_packet = time.monotonic()

        p, r, h = washout.update(ax, ay, az, roll, pitch)
        print(f'#{seq} pitch={p:+.3f} roll={r:+.3f} heave={h:+.3f}  '
              f'acc=({ax:+.2f},{ay:+.2f},{az:+.2f})')


if __name__ == '__main__':
    main()
