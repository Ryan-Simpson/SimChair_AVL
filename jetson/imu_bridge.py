"""
imu_bridge.py  —  run on Jetson (Phase 3 haptics)
Xsens IMU → UDP binary telemetry to Windows @ 50 Hz.

Packet (44 bytes, little-endian):
  seq:u32, t_ms:u64, ax,ay,az,gx,gy,gz,roll,pitch : float32  (8 floats)

t_ms is the Jetson wall clock (ms since epoch) when the packet is sent. The
chair PC logs arrival minus t_ms; the change from the run's minimum is the
one-way queueing delay on Marvin's cellular upload, which the video shares.
(It used to be the Xsens header stamp, which is GNSS time and wrong indoors.)

ax/ay/az are motion cues, not raw accelerometer, because skid-steer track
judder swamps Marvin's real 0.3 m/s^2 accelerations (2026-10-14 drive):
  ax = d/dt of /wheel_odom speed      (forward speed-up +, braking -)
  ay = speed * gyro yaw rate          (centripetal, + = turning left)
  Each is then blended 50/50 with the Xsens gravity-free accel on that axis,
  but only while the two agree in direction and the encoder cue is above
  0.05 m/s^2, so cruising judder never reaches the chair while real
  speed-ups, stops and turns get the IMU's sharper edges. The IMU axis sign
  is learned from a slow running correlation with the encoder cue (the
  mount direction is unconfirmed), and blending waits until it is clear.
  az = Xsens /filter/free_acceleration z (bumps, gravity-free)
gx/gy/gz stay raw gyro (gz = yaw rate, + = left, also felt on pivot turns).
--cue imu sends the old raw values: gravity-free accel while
/filter/free_acceleration is fresh, else /imu/data linear_acceleration.
If /wheel_odom goes stale the odom cue falls back to the imu values.

Usage (same ROS env as sensors):
  unset DISPLAY
  source /home/dinosaur/IGVC/install/setup.bash
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  export CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
  export ROS_DOMAIN_ID=42
  /usr/bin/python3 ~/SimChair_AVL/jetson/imu_bridge.py --windows-ip 100.91.25.107 [--hz 25]
(relay_teleop/run_imu_bridge.sh does this.)
"""

import argparse
import math
import socket
import struct
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Vector3Stamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu

UDP_PORT = 5007
TARGET_HZ = 50.0
PACKET_FMT = '<IQ8f'  # seq + t_ms + 8 floats = 44 bytes
PACKET_SIZE = struct.calcsize(PACKET_FMT)
FREE_ACCEL_TOPIC = '/filter/free_acceleration'
FREE_ACCEL_STALE_S = 0.2
ODOM_TOPIC = '/wheel_odom'
ODOM_STALE_S = 0.3
SPEED_LPF_HZ = 3.0   # smooth encoder speed before differentiating
ACCEL_LPF_HZ = 2.0   # smooth the derivative
IMU_LPF_HZ = 2.0     # IMU accel smoothing before blending
BLEND_MIN = 0.05     # m/s^2: below this the encoder cue says "cruising", IMU ignored
SIGN_TAU_S = 20.0    # running-correlation time constant for the IMU axis sign
SIGN_MIN_CORR = 0.3  # |correlation| needed before the IMU is blended in

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
    def __init__(self, windows_ip: str, topic=None, hz: float = TARGET_HZ,
                 free_accel_topic: str = FREE_ACCEL_TOPIC, cue: str = 'odom'):
        super().__init__('imu_bridge')
        self.hz = hz
        self.interval = 1.0 / hz
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dest = (windows_ip, UDP_PORT)
        self.seq = 0
        self.last_send = 0.0
        self.rx = 0
        self.tx = 0
        self.active_topic = None
        self.free_accel = None
        self.free_accel_t = 0.0
        self.tx_free = 0
        self.cue = cue
        self.v_lp = None
        self.a_long = 0.0
        self.odom_t = 0.0
        self.tx_odom = 0
        self.tx_blend = 0
        self.axes = {k: _AxisBlend() for k in ('x', 'y')}
        qos = qos_profile_sensor_data

        topics = [topic] if topic else IMU_TOPICS
        for t in topics:
            self.create_subscription(Imu, t, lambda msg, name=t: self._imu_cb(msg, name), qos)
            self.get_logger().info(f'Listening {t} (sensor QoS)')

        if free_accel_topic:
            self.create_subscription(Vector3Stamped, free_accel_topic, self._free_accel_cb, qos)
            self.get_logger().info(f'Gravity-free accel from {free_accel_topic}')
        if cue == 'odom':
            self.create_subscription(Odometry, ODOM_TOPIC, self._odom_cb, 10)
            self.get_logger().info(f'Accel cues from {ODOM_TOPIC} speed + gyro yaw rate')
        self.create_timer(2.0, self._stats)
        self.get_logger().info(f'IMU bridge → {windows_ip}:{UDP_PORT} @ {self.hz:.0f} Hz')

    def _imu_cb(self, msg: Imu, topic: str):
        self.rx += 1
        if self.active_topic is None:
            self.active_topic = topic
            self.get_logger().info(f'Using topic: {topic}')
        # Prefer first topic that won; ignore others once locked
        if topic != self.active_topic:
            return

        now = time.monotonic()
        # 2 ms slack: input is 100 Hz, so a strict check rounds 40 ms up to 50
        if now - self.last_send < self.interval - 0.002:
            return
        self.last_send = now
        self._send(msg)

    def _free_accel_cb(self, msg: Vector3Stamped):
        self.free_accel = msg.vector
        self.free_accel_t = time.monotonic()

    def _odom_cb(self, msg: Odometry):
        now = time.monotonic()
        v = float(msg.twist.twist.linear.x)
        dt = now - self.odom_t
        if self.v_lp is None or dt > 0.5:
            self.v_lp, self.a_long = v, 0.0
        elif dt > 1e-3:
            prev = self.v_lp
            self.v_lp += _alpha(SPEED_LPF_HZ, dt) * (v - self.v_lp)
            self.a_long += _alpha(ACCEL_LPF_HZ, dt) * ((self.v_lp - prev) / dt - self.a_long)
        self.odom_t = now

    def _send(self, msg: Imu):
        q = msg.orientation
        roll, pitch = quat_to_roll_pitch(q.x, q.y, q.z, q.w)
        if self.free_accel is not None and time.monotonic() - self.free_accel_t < FREE_ACCEL_STALE_S:
            acc = self.free_accel
            self.tx_free += 1
        else:
            acc = msg.linear_acceleration
        ax, ay, az = float(acc.x), float(acc.y), float(acc.z)
        if self.cue == 'odom' and self.v_lp is not None and time.monotonic() - self.odom_t < ODOM_STALE_S:
            ax = self.a_long
            ay = self.v_lp * float(msg.angular_velocity.z)
            self.tx_odom += 1
            if acc is self.free_accel:
                dt = self.interval
                ax, bx = self.axes['x'].update(ax, float(acc.x), dt)
                ay, by = self.axes['y'].update(ay, float(acc.y), dt)
                self.tx_blend += bx or by
        self.seq += 1
        packet = struct.pack(
            PACKET_FMT,
            self.seq,
            int(time.time() * 1000),
            ax,
            ay,
            az,
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
              f'rx={self.rx} tx={self.tx} (gravity-free {self.tx_free}, odom cue {self.tx_odom}) '
              f'v={self.v_lp or 0.0:+.2f} a={self.a_long:+.2f} blended {self.tx_blend} '
              f'imu sign x {self.axes["x"].describe()} y {self.axes["y"].describe()} → {self.dest}')
        self.rx = 0
        self.tx = 0
        self.tx_free = 0
        self.tx_odom = 0
        self.tx_blend = 0


class _AxisBlend:
    """Blend one encoder-derived cue with the matching IMU accel axis."""

    def __init__(self):
        self.imu_lp = 0.0
        self.cov = 0.0   # running E[enc*imu]
        self.var_e = 1e-6
        self.var_i = 1e-6

    def corr(self) -> float:
        return self.cov / math.sqrt(self.var_e * self.var_i)

    def describe(self) -> str:
        c = self.corr()
        return f'{"+" if c > 0 else "-"}{abs(c):.2f}' + ('' if abs(c) >= SIGN_MIN_CORR else '(learning)')

    def update(self, enc: float, imu: float, dt: float):
        self.imu_lp += _alpha(IMU_LPF_HZ, dt) * (imu - self.imu_lp)
        if abs(enc) > BLEND_MIN:  # learn only while actually accelerating/turning
            k = dt / SIGN_TAU_S
            self.cov += k * (enc * self.imu_lp - self.cov)
            self.var_e += k * (enc * enc - self.var_e)
            self.var_i += k * (self.imu_lp * self.imu_lp - self.var_i)
        c = self.corr()
        if abs(c) < SIGN_MIN_CORR or abs(enc) <= BLEND_MIN:
            return enc, False
        imu_s = math.copysign(1.0, c) * self.imu_lp
        if imu_s * enc <= 0:  # disagree in direction: trust the encoder
            return enc, False
        return 0.5 * (enc + imu_s), True


def _alpha(cutoff_hz: float, dt: float) -> float:
    tau = 1.0 / (2.0 * math.pi * cutoff_hz)
    return dt / (tau + dt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--windows-ip', default='100.91.25.107')
    parser.add_argument('--topic', default=None, help='Force IMU topic (optional)')
    parser.add_argument('--hz', type=float, default=TARGET_HZ, help='UDP send rate')
    parser.add_argument('--free-accel-topic', default=FREE_ACCEL_TOPIC,
                        help="gravity-free accel (Vector3Stamped); '' = send /imu/data accel")
    parser.add_argument('--cue', choices=['odom', 'imu'], default='odom',
                        help='odom: ax/ay from wheel speed + yaw rate (default); imu: raw accel')
    args = parser.parse_args()

    assert PACKET_SIZE == 44, PACKET_SIZE
    rclpy.init()
    node = ImuBridge(args.windows_ip, args.topic, args.hz, args.free_accel_topic, args.cue)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
