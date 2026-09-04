"""
windows_control_status.py  —  run on Windows (optional, Phase 2)
Listens for 1 Hz status packets from orin_vehicle_controller.py (UDP 5008).

Packet format (16 bytes, big-endian):
    seq: uint32, state: uint8, left_rpm: float32, right_rpm: float32

States: 0=STOPPED, 1=DRIVING, 2=WATCHDOG (latched stop)
"""

import socket
import struct
import time

UDP_PORT = 5008
FMT = '!I B ff'
SIZE = struct.calcsize(FMT)

STATE_NAMES = {0: 'STOPPED', 1: 'DRIVING', 2: 'WATCHDOG'}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', UDP_PORT))
sock.settimeout(2.0)

print(f'Control status listener on port {UDP_PORT}')
print('Waiting for Jetson status packets...')

last_seq = -1
while True:
    try:
        data, addr = sock.recvfrom(64)
    except socket.timeout:
        print('LINK DOWN — no status for 2s')
        continue

    if len(data) < SIZE:
        continue

    seq, state, left_rpm, right_rpm = struct.unpack(FMT, data[:SIZE])
    if seq <= last_seq:
        continue
    last_seq = seq

    name = STATE_NAMES.get(state, f'UNKNOWN({state})')
    age_ms = 0  # fresh packet
    print(f'[{name}] seq={seq} L={left_rpm:+.0f} R={right_rpm:+.0f} RPM  from {addr[0]}')
