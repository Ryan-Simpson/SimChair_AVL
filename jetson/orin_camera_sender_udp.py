"""
orin_camera_sender_udp.py  —  run on Jetson
Streams ZED cameras to Windows over UDP (chunked JPEG).

Why UDP vs the old TCP path:
  - No TCP head-of-line blocking / reconnect stalls on Tailscale
  - Lets us push higher FPS / quality without a reliable-stream backlog

Protocol (each datagram):
  magic      : 4s   b'MJPG'
  frame_id   : u32  big-endian
  chunk_idx  : u16
  num_chunks : u16
  payload    : bytes  (max ~1200 — Tailscale MTU ~1280)

Ports (same numbers as TCP path, UDP): left 9001, front 9002, right 9003

Usage:
  /usr/bin/python3 orin_camera_sender_udp.py --windows-ip 100.91.25.107
  /usr/bin/python3 orin_camera_sender_udp.py --profile indoor
"""

from __future__ import annotations

import argparse
import socket
import struct
import time

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CompressedImage, Image

CAMERAS = {
    'left': (
        '/zed_left/zed_node/rgb/color/rect/image/compressed',
        '/zed_left/zed_node/rgb/color/rect/image',
        9001,
    ),
    'front': (
        '/zed_front/zed_node/rgb/color/rect/image/compressed',
        '/zed_front/zed_node/rgb/color/rect/image',
        9002,
    ),
    'right': (
        '/zed_right/zed_node/rgb/color/rect/image/compressed',
        '/zed_right/zed_node/rgb/color/rect/image',
        9003,
    ),
}

# Named profiles (override fps/quality/size when --profile is set)
# Higher JPEG quality = fewer blocks; slightly lower fps = fewer UDP chunks lost.
PROFILES = {
    'indoor': {'fps': 30.0, 'quality': 80, 'width': 960, 'height': 540},
    'default': {'fps': 30.0, 'quality': 90, 'width': 1280, 'height': 720},
    # Prefer this when FPS is already fine but image looks blocky/pixelated
    'hq': {'fps': 25.0, 'quality': 96, 'width': 1280, 'height': 720},
    'sharp': {'fps': 20.0, 'quality': 97, 'width': 1600, 'height': 900},
}

MAGIC = b'MJPG'
HEADER = struct.Struct('>4sIHH')  # magic, frame_id, chunk_idx, num_chunks
MAX_PAYLOAD = 1200


def sensor_qos():
    # depth=1: never build a backlog of stale images (latency)
    return QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
        durability=DurabilityPolicy.VOLATILE,
    )


class UdpCamera:
    def __init__(self, name: str, port: int, dest: tuple[str, int], max_fps: float):
        self.name = name
        self.dest = dest
        self.interval = 1.0 / max_fps
        self.last_sent = 0.0
        self.frame_id = 0
        self.frames_in = 0
        self.frames_out = 0
        self.bytes_out = 0
        self.skipped = 0
        self.source = 'none'
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2 << 20)
        except OSError:
            pass
        print(f'[{name}] UDP → {dest[0]}:{port}')

    def send_jpeg(self, data: bytes, source: str):
        self.frames_in += 1
        self.source = source
        now = time.monotonic()
        if now - self.last_sent < self.interval:
            self.skipped += 1
            return
        self.last_sent = now

        self.frame_id = (self.frame_id + 1) & 0xFFFFFFFF
        chunks = [
            data[i : i + MAX_PAYLOAD] for i in range(0, len(data), MAX_PAYLOAD)
        ] or [b'']
        n = len(chunks)
        if n > 0xFFFF:
            print(f'[{self.name}] frame too large ({len(data)} B) — skip')
            return

        fid = self.frame_id
        try:
            for idx, chunk in enumerate(chunks):
                pkt = HEADER.pack(MAGIC, fid, idx, n) + chunk
                self.sock.sendto(pkt, self.dest)
            self.frames_out += 1
            self.bytes_out += len(data)
        except OSError as e:
            print(f'[{self.name}] UDP send failed: {e}')


class CameraSenderUdp(Node):
    def __init__(
        self,
        windows_ip: str,
        max_fps: float,
        jpeg_quality: int,
        width: int,
        height: int,
        prefer_raw: bool,
    ):
        super().__init__('camera_sender_udp')
        self.bridge = CvBridge()
        self.jpeg_quality = jpeg_quality
        self.width = width
        self.height = height
        self.prefer_raw = prefer_raw
        self.encode_params = [
            int(cv2.IMWRITE_JPEG_QUALITY),
            jpeg_quality,
        ]
        self.got_compressed = {n: False for n in CAMERAS}
        self.cams: dict[str, UdpCamera] = {}
        self._busy = {n: False for n in CAMERAS}
        qos = sensor_qos()

        for name, (c_topic, r_topic, port) in CAMERAS.items():
            self.cams[name] = UdpCamera(name, port, (windows_ip, port), max_fps)

            if not prefer_raw:
                self.create_subscription(
                    CompressedImage,
                    c_topic,
                    lambda msg, n=name: self.on_compressed(msg, n),
                    qos,
                )
                self.get_logger().info(f'{name}: compressed {c_topic}')

            self.create_subscription(
                Image,
                r_topic,
                lambda msg, n=name: self.on_raw(msg, n),
                qos,
            )
            self.get_logger().info(
                f'{name}: raw {r_topic} → {width}x{height} q={jpeg_quality}'
            )

        self.create_timer(2.0, self._stats)
        self.get_logger().info(
            f'UDP JPEG sender ready → {windows_ip}  '
            f'target={width}x{height}@{max_fps:.0f}fps q={jpeg_quality}  '
            f'prefer_raw={prefer_raw}'
        )

    def on_compressed(self, msg, name: str):
        if self.prefer_raw:
            return
        self.got_compressed[name] = True
        self.cams[name].send_jpeg(bytes(msg.data), 'compressed')

    def on_raw(self, msg, name: str):
        if not self.prefer_raw and self.got_compressed[name]:
            return
        # Drop if still encoding previous frame for this cam (avoid backlog)
        if self._busy[name]:
            self.cams[name].skipped += 1
            return
        self._busy[name] = True
        try:
            try:
                frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            except Exception:
                try:
                    bgra = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgra8')
                    frame = cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)
                except Exception as e:
                    self.get_logger().warn(f'{name} raw convert failed: {e}')
                    return

            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(
                    frame,
                    (self.width, self.height),
                    interpolation=cv2.INTER_AREA,
                )

            ok, buf = cv2.imencode('.jpg', frame, self.encode_params)
            if ok:
                self.cams[name].send_jpeg(buf.tobytes(), 'raw')
        finally:
            self._busy[name] = False

    def _stats(self):
        parts = []
        for name, cam in self.cams.items():
            parts.append(
                f'{name}:{cam.source} in={cam.frames_in} out={cam.frames_out} '
                f'skip={cam.skipped} kB={cam.bytes_out // 1024}'
            )
            cam.frames_in = 0
            cam.frames_out = 0
            cam.bytes_out = 0
            cam.skipped = 0
        print('[stats] ' + ' | '.join(parts))


def main():
    parser = argparse.ArgumentParser(description='ZED → Windows UDP JPEG sender')
    parser.add_argument('--windows-ip', default='100.91.25.107')
    parser.add_argument('--profile', choices=sorted(PROFILES.keys()), default=None)
    parser.add_argument('--fps', type=float, default=None)
    parser.add_argument('--quality', type=int, default=None, help='JPEG quality 1-100 (raw path)')
    parser.add_argument('--width', type=int, default=None)
    parser.add_argument('--height', type=int, default=None)
    parser.add_argument(
        '--prefer-raw',
        action='store_true',
        default=True,
        help='Re-encode from raw at width/height/quality (default ON)',
    )
    parser.add_argument(
        '--prefer-compressed',
        action='store_true',
        help='Forward ROS compressed JPEG (lighter CPU, less control of res/quality)',
    )
    args = parser.parse_args()

    base = dict(PROFILES['default'])
    if args.profile:
        base.update(PROFILES[args.profile])
    fps = args.fps if args.fps is not None else base['fps']
    quality = args.quality if args.quality is not None else base['quality']
    width = args.width if args.width is not None else base['width']
    height = args.height if args.height is not None else base['height']
    prefer_raw = not args.prefer_compressed

    print(
        f'Profile={args.profile or "default"} → '
        f'{width}x{height}@{fps:.0f}fps q={quality}'
    )

    rclpy.init()
    node = CameraSenderUdp(
        windows_ip=args.windows_ip,
        max_fps=fps,
        jpeg_quality=quality,
        width=width,
        height=height,
        prefer_raw=prefer_raw,
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
