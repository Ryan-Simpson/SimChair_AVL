"""
orin_vehicle_controller.py  —  run on Jetson
Receives sim chair UDP commands (port 5006) and drives the Teensy diff-drive
bridge over USB serial.

v5 changes (Spark silent while UDP readings look fine):
  - NEVER send 'S' — only L0 R0 for stops (S duty/brake mode can leave Spark dead)
  - Print Teensy replies (OK / E / WD) so serial path is visible
  - Hold last drive cmd through DERP gaps; latch after UDP silence

UDP: "steering,throttle,brake,mode\\n"  or v2 with seq,timestamp
Sender modes: 0=N 1=D 2=S 3=R
"""

import argparse
import socket
import serial
import struct
import threading
import time

UDP_PORT         = 5006
STATUS_PORT      = 5008
STATUS_DEST      = ('100.91.25.107', STATUS_PORT)
SERIAL_PORT      = '/dev/ttyACM0'
SERIAL_BAUD      = 115200

MAX_RPM          = 1200.0
MAX_DUTY         = 0.25   # Teensy firmware caps open-loop at 0.30
TURN_GAIN        = 0.6

SERIAL_HZ        = 50.0
SERIAL_DT        = 1.0 / SERIAL_HZ

UDP_LATCH_S      = 2.5
REARM_RAMP_S     = 0.25

STATE_DRIVING    = 1
STATE_STOPPED    = 0
STATE_WATCHDOG   = 2

parser = argparse.ArgumentParser(description='UDP → Teensy vehicle controller')
mode = parser.add_mutually_exclusive_group()
mode.add_argument(
    '--duty', action='store_true',
    help='UL/UR open-loop duty (default — moves Sparks without encoder PID)',
)
mode.add_argument(
    '--velocity', action='store_true',
    help='L/R RPM velocity setpoints (needs working Spark closed-loop)',
)
args = parser.parse_args()
# Default duty: velocity mode acks OK L=… but Sparks stay purple / no motion.
DRIVE_MODE = 'velocity' if args.velocity else 'duty'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', UDP_PORT))
sock.settimeout(0.02)

status_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.0)
time.sleep(0.3)
ser.reset_input_buffer()
ser.reset_output_buffer()

lock = threading.Lock()
last_seq         = -1
latched_stopped  = False
vehicle_state    = STATE_STOPPED
cmd_left         = 0.0
cmd_right        = 0.0
last_packet_time = time.monotonic()
last_print       = 0.0
last_teensy_print = 0.0
running          = True
rearm_t0         = 0.0

print('Vehicle controller ready (v5.1 — E=encoder feedback, not error).')
print(f'  UDP  : 0.0.0.0:{UDP_PORT}')
print(f'  Status → {STATUS_DEST[0]}:{STATUS_DEST[1]} @ 1 Hz')
print(f'  Serial: {SERIAL_PORT} @ {SERIAL_BAUD}  stream={SERIAL_HZ:.0f} Hz')
print(f'  MAX_RPM={MAX_RPM}  TURN_GAIN={TURN_GAIN}  drive_mode={DRIVE_MODE}')
print(f'  UDP latch={UDP_LATCH_S}s  rearm_ramp={REARM_RAMP_S}s')
print('  Expect [teensy] OK L=… when commands parse. E lines = measured RPM + position.')


def send_serial(cmd: str):
    try:
        ser.write((cmd + '\n').encode())
    except serial.SerialException as e:
        print(f'Serial write error: {e}')


def drain_serial():
    """Read Teensy lines. E = encoder feedback (rate-limited). Always show OK/ERR/DIAG/#."""
    global last_teensy_print
    buf = b''
    while running:
        try:
            n = ser.in_waiting
            if not n:
                time.sleep(0.005)
                continue
            buf += ser.read(n)
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                text = line.decode(errors='replace').strip()
                if not text:
                    continue
                now = time.monotonic()
                if text.startswith('E '):
                    # Feedback at 50 Hz — print at most 2 Hz
                    if (now - last_teensy_print) >= 0.5:
                        print(f'[teensy] {text}')
                        last_teensy_print = now
                    continue
                # OK / ERR / DIAG / # WDT / etc.
                print(f'[teensy] {text}')
                last_teensy_print = now
        except serial.SerialException as e:
            print(f'Serial read error: {e}')
            time.sleep(0.05)


def parse_packet(data: bytes):
    global last_seq
    text = data.decode(errors='replace').strip()
    parts = text.split(',')
    if len(parts) < 4:
        return None

    if len(parts) >= 6:
        try:
            seq = int(parts[0])
            steering = float(parts[2])
            throttle = float(parts[3])
            brake    = float(parts[4])
            mode     = int(parts[5])
        except ValueError:
            return None
        if seq <= last_seq:
            return None
        last_seq = seq
        return seq, steering, throttle, brake, mode

    try:
        steering = float(parts[0])
        throttle = float(parts[1])
        brake    = float(parts[2])
        mode     = int(parts[3]) if len(parts) > 3 else 1
    except ValueError:
        return None
    last_seq += 1
    return last_seq, steering, throttle, brake, mode


def mix(steering, throttle, brake, mode):
    forward = (throttle - brake) * MAX_RPM
    if mode == 3:  # Reverse
        forward = -forward
    turn = -steering * MAX_RPM * TURN_GAIN
    left = max(-MAX_RPM, min(MAX_RPM, forward - turn))
    right = max(-MAX_RPM, min(MAX_RPM, forward + turn))
    return left, right


def mix_duty(steering, throttle, brake, mode):
    """Open-loop duty for Spark smoke test (Teensy caps ±0.30)."""
    forward = (throttle - brake) * MAX_DUTY
    if mode == 3:
        forward = -forward
    turn = -steering * MAX_DUTY * TURN_GAIN
    left = max(-MAX_DUTY, min(MAX_DUTY, forward - turn))
    right = max(-MAX_DUTY, min(MAX_DUTY, forward + turn))
    return left, right


def serial_loop():
    next_t = time.monotonic()
    while running:
        now = time.monotonic()
        with lock:
            left = cmd_left
            right = cmd_right
            latch = latched_stopped
            state = vehicle_state
            ramp_t0 = rearm_t0

        stopped = latch or state == STATE_STOPPED

        if stopped:
            if DRIVE_MODE == 'duty':
                send_serial('UL0 UR0')
            else:
                send_serial('L0 R0')
        else:
            elapsed = now - ramp_t0
            if elapsed < REARM_RAMP_S:
                scale = max(0.0, min(1.0, elapsed / REARM_RAMP_S))
                left *= scale
                right *= scale
            if DRIVE_MODE == 'duty':
                send_serial(f'UL{left:.3f} UR{right:.3f}')
            else:
                send_serial(f'L{left:.0f} R{right:.0f}')

        next_t += SERIAL_DT
        sleep = next_t - time.monotonic()
        if sleep > 0:
            time.sleep(sleep)
        else:
            next_t = time.monotonic()


def status_loop():
    status_seq = 0
    while running:
        time.sleep(1.0)
        status_seq += 1
        with lock:
            state = vehicle_state
            left = cmd_left
            right = cmd_right
        pkt = struct.pack('!I B ff', status_seq, state, left, right)
        try:
            status_sock.sendto(pkt, STATUS_DEST)
        except OSError:
            pass


# One-shot DIAG so we see Spark mode / bus voltage immediately
send_serial('D')
time.sleep(0.05)

threading.Thread(target=drain_serial, daemon=True).start()
threading.Thread(target=serial_loop, daemon=True).start()
threading.Thread(target=status_loop, daemon=True).start()

try:
    while True:
        now = time.monotonic()
        with lock:
            age = now - last_packet_time
            if age > UDP_LATCH_S and vehicle_state == STATE_DRIVING:
                latched_stopped = True
                vehicle_state = STATE_WATCHDOG
                cmd_left = cmd_right = 0.0
                print('WATCHDOG — latched (no UDP). N then D to re-arm.')

        try:
            data, _ = sock.recvfrom(256)
        except socket.timeout:
            continue

        parsed = parse_packet(data)
        if parsed is None:
            continue

        seq, steering, throttle, brake, mode = parsed

        with lock:
            last_packet_time = time.monotonic()

            if mode == 0:
                was_driving = vehicle_state == STATE_DRIVING
                cmd_left = cmd_right = 0.0
                latched_stopped = False
                vehicle_state = STATE_STOPPED
                if was_driving:
                    print(f'PARK (seq={seq})')
                continue

            if latched_stopped or vehicle_state != STATE_DRIVING:
                latched_stopped = False
                rearm_t0 = time.monotonic()
                print(f'RE-ARMED mode={mode} (seq={seq})')

            if DRIVE_MODE == 'duty':
                cmd_left, cmd_right = mix_duty(steering, throttle, brake, mode)
            else:
                cmd_left, cmd_right = mix(steering, throttle, brake, mode)
            vehicle_state = STATE_DRIVING
            left, right = cmd_left, cmd_right

        now = time.time()
        if now - last_print > 0.2:
            if DRIVE_MODE == 'duty':
                print(f'#{seq} mode={mode} S:{steering:+.2f} T:{throttle:.2f} B:{brake:.2f} '
                      f'-> UL:{left:+.3f} UR:{right:+.3f}')
            else:
                print(f'#{seq} mode={mode} S:{steering:+.2f} T:{throttle:.2f} B:{brake:.2f} '
                      f'-> L:{left:+.0f} R:{right:+.0f} RPM')
            last_print = now

except KeyboardInterrupt:
    print('Shutting down.')
finally:
    running = False
    try:
        send_serial('L0 R0' if DRIVE_MODE != 'duty' else 'UL0 UR0')
    except Exception:
        pass
    time.sleep(0.05)
    ser.close()
    sock.close()
    status_sock.close()
