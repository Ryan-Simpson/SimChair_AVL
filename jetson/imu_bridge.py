"""
imu_bridge.py  —  run on Jetson (Phase 3 haptics)
Xsens IMU → UDP binary telemetry to Windows @ 50 Hz.

Packet (44 bytes, little-endian):
  seq:u32, t_ms:u64, ax,ay,az,gx,gy,gz,roll,pitch : float32  (8 floats)

Usage (same ROS env as sensors):
  unset DISPLAY
  source /home/dinosaur/IGVC/install/setup.bash
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  export CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
  export ROS_DOMAIN_ID=42
  /usr/bin/python3 ~/Documents/SimChair_Teleop/imu_bridge.py --windows-ip 100.91.25.107
"""

import argparse
import math
import socket
import struct
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu

UDP_PORT = 5007
TARGET_HZ = 50.0
INTERVAL = 1.0 / TARGET_HZ
PACKET_FMT = '<IQ8f'  # seq + t_ms + 8 floats = 44 bytes
PACKET_SIZE = struct.calcsize(PACKET_FMT)

# Prefer Xsens if present; fall back to ZED front (kart body motion still useful)
IMU_TOPICS = [
    '/imu/data',
    '/imu/data_raw',
    '/xsens/imu/data',
    '/zed_front/zed_node/imu/data',
]


def quat_to_roll_pitch(qx, qy, qz, qw):
    sinr_cosp = 2.0 * (qw * qx + qy * qz)
    cosr_cosp = 1.0 - 2.0 * (qx * qx + qy * qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    sinp = 2.0 * (qw * qy - qz * qx)
    if abs(sinp) >= 1.0:
        pitch = math.copysign(math.pi / 2.0, sinp)
    else:
        pitch = math.asin(sinp)
    return roll, pitch


class ImuBridge(Node):
    def __init__(self, windows_ip: str, topic=None):
        super().__init__('imu_bridge')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dest = (windows_ip, UDP_PORT)
        self.seq = 0
        self.last_send = 0.0
        self.rx = 0
        self.tx = 0
        self.active_topic = None
        qos = qos_profile_sensor_data

        topics = [topic] if topic else IMU_TOPICS
        for t in topics:
            self.create_subscription(Imu, t, lambda msg, name=t: self._imu_cb(msg, name), qos)
            self.get_logger().info(f'Listening {t} (sensor QoS)')

        self.create_timer(2.0, self._stats)
        self.get_logger().info(f'IMU bridge → {windows_ip}:{UDP_PORT} @ {TARGET_HZ:.0f} Hz')

    def _imu_cb(self, msg: Imu, topic: str):
        self.rx += 1
        if self.active_topic is None:
            self.active_topic = topic
            self.get_logger().info(f'Using topic: {topic}')
        # Prefer first topic that won; ignore others once locked
        if topic != self.active_topic:
            return

        now = time.monotonic()
        if now - self.last_send < INTERVAL:
            return
        self.last_send = now
        self._send(msg)

    def _send(self, msg: Imu):
        q = msg.orientation
        roll, pitch = quat_to_roll_pitch(q.x, q.y, q.z, q.w)
        t_ms = msg.header.stamp.sec * 1000 + msg.header.stamp.nanosec // 1_000_000
        self.seq += 1
        packet = struct.pack(
            PACKET_FMT,
            self.seq,
            t_ms,
            float(msg.linear_acceleration.x),
            float(msg.linear_acceleration.y),
            float(msg.linear_acceleration.z),
            float(msg.angular_velocity.x),
            float(msg.angular_velocity.y),
            float(msg.angular_velocity.z),
            float(roll),
            float(pitch),
        )
        try:
            self.sock.sendto(packet, self.dest)
            self.tx += 1
        except OSError as e:
            self.get_logger().warn(f'UDP send failed: {e}')

    def _stats(self):
        print(f'[imu_bridge] topic={self.active_topic or "none"} '
              f'rx={self.rx} tx={self.tx} → {self.dest}')
        self.rx = 0
        self.tx = 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--windows-ip', default='100.91.25.107')
    parser.add_argument('--topic', default=None, help='Force IMU topic (optional)')
    args = parser.parse_args()

    assert PACKET_SIZE == 44, PACKET_SIZE
    rclpy.init()
    node = ImuBridge(args.windows_ip, args.topic)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
