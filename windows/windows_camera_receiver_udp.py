"""
windows_camera_receiver_udp.py  —  chunked JPEG/UDP receiver (3 monitors)

Pairs with jetson/orin_camera_sender_udp.py
Ports: Left 9001, Front 9002, Right 9003

Latency-focused:
  - Socket thread only assembles JPEG bytes (no imdecode on RX path)
  - Queue depth 1 → always display newest complete frame
  - Incomplete frames expire quickly (~100 ms)

Usage:
  python windows_camera_receiver_udp.py
  python windows_camera_receiver_udp.py --fullscreen
"""

from __future__ import annotations

import argparse
import queue
import socket
import struct
import threading
import time

import cv2
import numpy as np

MAGIC = b'MJPG'
HEADER = struct.Struct('>4sIHH')  # magic, frame_id, chunk_idx, num_chunks
HEADER_LEN = HEADER.size

CAMERAS = [
    ('Left', 9001, 0),
    ('Front', 9002, 1920),
    ('Right', 9003, 3840),
]


class FrameAssembler:
    """Reassemble chunked JPEG frames; prefer newest, drop incomplete fast."""

    def __init__(self, max_age_s: float = 0.1):
        self.max_age_s = max_age_s
        self.cur_id = None
        self.num_chunks = 0
        self.chunks: dict[int, bytes] = {}
        self.started = 0.0
        self.dropped_incomplete = 0

    def push(self, frame_id: int, chunk_idx: int, num_chunks: int, payload: bytes):
        now = time.monotonic()

        # Newer frame → abandon incomplete previous immediately (latency > completeness)
        if self.cur_id is None or frame_id != self.cur_id:
            if self.cur_id is not None and self.chunks:
                self.dropped_incomplete += 1
            self.cur_id = frame_id
            self.num_chunks = num_chunks
            self.chunks = {}
            self.started = now

        if num_chunks != self.num_chunks or chunk_idx >= num_chunks:
            return None

        self.chunks[chunk_idx] = payload

        if len(self.chunks) < num_chunks:
            if now - self.started > self.max_age_s:
                self.dropped_incomplete += 1
                self.cur_id = None
                self.chunks = {}
            return None

        data = b''.join(self.chunks[i] for i in range(num_chunks))
        self.cur_id = None
        self.chunks = {}
        return data


def stream(name: str, port: int, jpeg_queue: queue.Queue, stats: dict, max_age_s: float):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 << 20)
    except OSError:
        pass
    sock.bind(('0.0.0.0', port))
    sock.settimeout(0.5)
    print(f'[{name}] Listening UDP :{port}')

    asm = FrameAssembler(max_age_s=max_age_s)
    while True:
        try:
            pkt, _addr = sock.recvfrom(2048)
        except socket.timeout:
            continue
        except OSError as e:
            print(f'[{name}] socket error: {e}')
            break

        if len(pkt) < HEADER_LEN:
            continue
        magic, frame_id, chunk_idx, num_chunks = HEADER.unpack_from(pkt, 0)
        if magic != MAGIC or num_chunks == 0:
            continue

        data = asm.push(frame_id, chunk_idx, num_chunks, pkt[HEADER_LEN:])
        stats['incomplete'] = asm.dropped_incomplete
        if data is None:
            continue

        stats['count'] += 1
        stats['bytes'] += len(data)
        # Keep only newest JPEG — decode happens on main thread
        try:
            jpeg_queue.get_nowait()
            stats['stale'] += 1
        except queue.Empty:
            pass
        try:
            jpeg_queue.put_nowait(data)
        except queue.Full:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fullscreen', action='store_true')
    parser.add_argument(
        '--assemble-ms',
        type=int,
        default=100,
        help='Max ms to wait for all chunks of a frame (default 100)',
    )
    args = parser.parse_args()
    max_age_s = max(30, args.assemble_ms) / 1000.0

    queues = {}
    stats = {}
    for name, port, _ in CAMERAS:
        q = queue.Queue(maxsize=1)
        queues[name] = q
        stats[name] = {
            'count': 0,
            'bytes': 0,
            'bad': 0,
            'stale': 0,
            'incomplete': 0,
            'last_print': time.time(),
            'last_incomplete': 0,
        }
        threading.Thread(
            target=stream,
            args=(name, port, q, stats[name], max_age_s),
            daemon=True,
        ).start()

    for name, _, x_offset in CAMERAS:
        win = f'ZED {name}'
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.moveWindow(win, x_offset, 0)
        if args.fullscreen:
            cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.resizeWindow(win, 1280, 720)
        ph = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(
            ph,
            f'{name}: waiting UDP...',
            (40, 360),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (200, 200, 200),
            2,
        )
        cv2.imshow(win, ph)

    print('UDP receiver up (low-latency). Press Q to quit.')
    print('Tip: if image looks blocky, check drop_inc — high drops = UDP loss (try profile hq).')
    while True:
        now = time.time()
        for name, _, _ in CAMERAS:
            s = stats[name]
            if now - s['last_print'] > 2.0:
                fps = s['count'] / 2.0
                inc_delta = s['incomplete'] - s['last_incomplete']
                print(
                    f'[{name}] ~{fps:.1f} fps  kB={s["bytes"] // 1024}  '
                    f'bad={s["bad"]}  stale={s["stale"]}  drop_inc={inc_delta}'
                )
                s['count'] = 0
                s['bytes'] = 0
                s['bad'] = 0
                s['stale'] = 0
                s['last_incomplete'] = s['incomplete']
                s['last_print'] = now

            try:
                data = queues[name].get_nowait()
            except queue.Empty:
                continue

            frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                s['bad'] += 1
                continue
            # Smooth upscale to monitor size — nearest stretch makes JPEG look more pixelated
            h, w = frame.shape[:2]
            if args.fullscreen or w < 1600:
                frame = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_LINEAR)
            cv2.imshow(f'ZED {name}', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
