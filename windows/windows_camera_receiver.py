"""
windows_camera_receiver.py  —  JPEG/TCP receiver (3 monitors)
Windows appear as soon as the app starts; frame stats print every ~2s.
"""

import socket
import struct
import threading
import queue
import time
import cv2
import numpy as np

JETSON_IP = '100.93.121.3'

CAMERAS = [
    ('Left',  9001,     0),
    ('Front', 9002,  1920),
    ('Right', 9003,  3840),
]


def recvall(sock, n):
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def stream(name, port, frame_queue, stats):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    print(f'[{name}] Connecting on port {port}...')
    sock.connect((JETSON_IP, port))
    sock.settimeout(None)
    print(f'[{name}] Connected — waiting for JPEG frames...')

    while True:
        header = recvall(sock, 4)
        if header is None:
            print(f'[{name}] Connection lost (header).')
            break
        (size,) = struct.unpack('>I', header)
        if size < 100 or size > 5_000_000:
            print(f'[{name}] Bad frame size={size} — sync lost, reconnect needed.')
            break
        data = recvall(sock, size)
        if data is None:
            print(f'[{name}] Connection lost (body).')
            break

        arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            print(f'[{name}] JPEG decode failed (size={size})')
            continue

        stats['count'] += 1
        stats['bytes'] += size
        try:
            frame_queue.get_nowait()
        except queue.Empty:
            pass
        frame_queue.put(frame)

    sock.close()


def main():
    queues = {}
    stats = {}
    for name, port, _ in CAMERAS:
        q = queue.Queue(maxsize=2)
        queues[name] = q
        s = {'count': 0, 'bytes': 0, 'last_print': time.time()}
        stats[name] = s
        t = threading.Thread(target=stream, args=(name, port, q, s), daemon=True)
        t.start()

    # Create windows immediately on main thread (even before frames)
    placeholders = {}
    for name, _, x_offset in CAMERAS:
        win = f'ZED {name}'
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.moveWindow(win, x_offset, 0)
        cv2.resizeWindow(win, 960, 600)
        ph = np.zeros((600, 960, 3), dtype=np.uint8)
        cv2.putText(ph, f'{name}: waiting for frames...', (40, 300),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)
        placeholders[name] = ph
        cv2.imshow(win, ph)

    print('Windows open. If stuck on "waiting", check Jetson camera sender + topic hz.')
    print('Press Q to quit.')

    while True:
        now = time.time()
        for name, _, _ in CAMERAS:
            s = stats[name]
            if now - s['last_print'] > 2.0:
                print(f'[{name}] frames={s["count"]} bytes={s["bytes"]}')
                s['count'] = 0
                s['bytes'] = 0
                s['last_print'] = now

            try:
                frame = queues[name].get_nowait()
            except queue.Empty:
                continue

            cv2.imshow(f'ZED {name}', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
