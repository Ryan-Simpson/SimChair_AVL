"""Marvin-side drive log: 1 Hz GPS + eno1 throughput + ping RTT to the chair PC -> CSV.

Latency study (docs/MEASUREMENTS.md). Run inside the simchair tmux session:
  mkdir -p /tmp/drivelog
  tmux new-window -d -t simchair -n drivelog     "source ~/SimChair_AVL/jetson/relay_teleop/env.sh; /usr/bin/python3 ~/SimChair_AVL/jetson/relay_teleop/drive_log.py /tmp/drivelog/marvin_1hz.csv"
  for w in rate webrtc_front webrtc_left webrtc_right bridge; do
    tmux pipe-pane -o -t simchair:$w "cat >> /tmp/drivelog/$w.log"; done
eno1 rx includes the Velodyne (~16 Mbps on the kart LAN), not just cellular.
"""
import subprocess
import sys
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import NavSatFix

OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/drivelog/marvin_1hz.csv'
PEER = '100.91.25.107'
IFACE = 'eno1'


def nic_bytes():
    with open(f'/sys/class/net/{IFACE}/statistics/tx_bytes') as f:
        tx = int(f.read())
    with open(f'/sys/class/net/{IFACE}/statistics/rx_bytes') as f:
        rx = int(f.read())
    return tx, rx


class DriveLog(Node):
    def __init__(self):
        super().__init__('drive_log')
        self.fix = None
        self.rtt = ''
        self.create_subscription(NavSatFix, '/gnss', self._gnss, qos_profile_sensor_data)
        threading.Thread(target=self._pinger, daemon=True).start()
        self.f = open(OUT, 'a', buffering=1)
        if self.f.tell() == 0:
            self.f.write('wall,lat,lon,alt,fix_status,tx_kbps,rx_kbps,ping_ms\n')
        self.prev = (time.time(), *nic_bytes())
        self.create_timer(1.0, self._tick)

    def _gnss(self, m):
        self.fix = m

    def _pinger(self):
        while True:
            r = subprocess.run(['ping', '-c', '1', '-W', '2', PEER], capture_output=True, text=True)
            t = [w for w in r.stdout.split() if w.startswith('time=')]
            self.rtt = t[0][5:] if t else 'lost'
            time.sleep(0.5)

    def _tick(self):
        now, tx, rx = time.time(), *nic_bytes()
        t0, tx0, rx0 = self.prev
        dt = max(now - t0, 1e-3)
        self.prev = (now, tx, rx)
        m = self.fix
        pos = f'{m.latitude:.7f},{m.longitude:.7f},{m.altitude:.1f},{m.status.status}' if m else ',,,'
        self.f.write(f'{now:.2f},{pos},{(tx - tx0) * 8 / dt / 1000:.0f},{(rx - rx0) * 8 / dt / 1000:.0f},{self.rtt}\n')


rclpy.init()
rclpy.spin(DriveLog())
