"""
orin_camera_sender.py  --  run on Jetson
Streams ZED cameras to Windows over TCP.

Strategy:
  1) Prefer /compressed JPEG topics (sensor QoS)
  2) If no compressed frames for 3s, fall back to raw Image + cv2 JPEG encode

Prints [stats] every 2s so you can see which path is alive.
"""

import time
import socket
import struct
import threading

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from sensor_msgs.msg import CompressedImage, Image

# name -> (compressed_topic, raw_topic, tcp_port)
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

TARGET_FPS = 15
FRAME_INTERVAL = 1.0 / TARGET_FPS
JPEG_QUALITY = 70


def sensor_qos():
    return QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        history=HistoryPolicy.KEEP_LAST,
        depth=5,
        durability=DurabilityPolicy.VOLATILE,
    )


class CameraServer:
    def __init__(self, name, port):
        self.name = name
        self.conn = None
        self.lock = threading.Lock()
        self.last_sent = 0.0
        self.frames_in = 0
        self.frames_out = 0
        self.source = 'none'
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('0.0.0.0', port))
        self.server.listen(1)
        print(f'[{name}] Waiting on TCP {port}...')
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while True:
            conn, addr = self.server.accept()
            with self.lock:
                if self.conn is not None:
                    try:
                        self.conn.close()
                    except OSError:
                        pass
                self.conn = conn
            print(f'[{self.name}] Windows connected: {addr}')

    def send_jpeg(self, data: bytes, source: str):
        self.frames_in += 1
        self.source = source
        now = time.monotonic()
        if now - self.last_sent < FRAME_INTERVAL:
            return
        self.last_sent = now

        with self.lock:
            conn = self.conn
        if conn is None:
            return
        try:
            conn.sendall(struct.pack('>I', len(data)) + data)
            self.frames_out += 1
        except OSError as e:
            print(f'[{self.name}] send failed: {e}')
            with self.lock:
                try:
                    conn.close()
                except OSError:
                    pass
                self.conn = None


class CameraSender(Node):
    def __init__(self):
        super().__init__('camera_sender')
        self.bridge = CvBridge()
        self.servers = {}
        self.got_compressed = {n: False for n in CAMERAS}
        self.raw_enabled = {n: False for n in CAMERAS}
        qos = sensor_qos()

        for name, (c_topic, r_topic, port) in CAMERAS.items():
            self.servers[name] = CameraServer(name, port)

            self.create_subscription(
                CompressedImage, c_topic,
                lambda msg, n=name: self.on_compressed(msg, n),
                qos,
            )
            self.get_logger().info(f'{name}: listen compressed {c_topic}')

            # Raw always subscribed as backup; ignored once compressed flows
            self.create_subscription(
                Image, r_topic,
                lambda msg, n=name: self.on_raw(msg, n),
                qos,
            )
            self.raw_enabled[name] = True
            self.get_logger().info(f'{name}: listen raw {r_topic}')

        self.create_timer(2.0, self._stats)
        self.create_timer(5.0, self._hint)
        self.get_logger().info('Camera sender ready (compressed + raw fallback).')

    def on_compressed(self, msg, name):
        self.got_compressed[name] = True
        self.servers[name].send_jpeg(bytes(msg.data), 'compressed')

    def on_raw(self, msg, name):
        # Prefer compressed when available
        if self.got_compressed[name]:
            return
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception:
            # ZED often publishes BGRA
            try:
                bgra = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgra8')
                frame = cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)
            except Exception as e:
                self.get_logger().warn(f'{name} raw convert failed: {e}')
                return

        ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        if ok:
            self.servers[name].send_jpeg(buf.tobytes(), 'raw')

    def _stats(self):
        parts = []
        for name, srv in self.servers.items():
            parts.append(
                f'{name}:{srv.source} in={srv.frames_in} out={srv.frames_out}'
            )
            srv.frames_in = 0
            srv.frames_out = 0
        print('[stats] ' + ' | '.join(parts))

    def _hint(self):
        dead = [n for n, s in self.servers.items() if s.source == 'none']
        if dead:
            print(
                f'[hint] no images yet for {dead}. Check: '
                f'ros2 topic hz <topic>  and  ros2 topic info -v <topic>'
            )


def main():
    rclpy.init()
    node = CameraSender()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
