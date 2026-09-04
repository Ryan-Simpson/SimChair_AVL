#!/usr/bin/env python3
"""
orin_simchair_ros_bridge.py  —  run on Jetson (with car stack up)

Receives sim-chair UDP on :5006 and publishes the SAME topic WebUI uses:
  /avros/actuator_command  (avros_msgs/msg/ActuatorCommand)

Why this exists:
  - Leaves actuator_node as sole Teensy owner (no serial steal)
  - Does not stop avros-webui / percept-stack
  - Avoids orin_launch_all dual-ZED crashes
  - Uses whatever drive mode actuator_node currently uses (works when Chrome does)

UDP packet (same as orin_vehicle_controller):
  "steering,throttle,brake,mode\\n"
  mode: 0=N(park) 1=D 2=S 3=R
  optional v2: seq,timestamp_ms,steering,throttle,brake,mode

Usage (conda OFF, Cyclone set — same as WebUI):
  conda deactivate
  unset ROS_DOMAIN_ID DISPLAY
  source /opt/ros/humble/setup.bash
  source /home/dinosaur/IGVC/install/setup.bash
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  export CYCLONEDDS_URI=file:///home/dinosaur/IGVC/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml
  /usr/bin/python3 ~/Documents/SimChair_Teleop/orin_simchair_ros_bridge.py

Windows: simchair_sender_dbox.exe  (mode 1 = drive)
Do NOT also run Chrome stick at the same time (two commanders).
"""

from __future__ import annotations

import argparse
import socket
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from avros_msgs.msg import ActuatorCommand
from std_msgs.msg import Header

MODE_MAP = {
    0: 'N',  # park / neutral
    1: 'D',  # drive
    2: 'S',  # stop / brake-style (WebUI idle often uses S on serial; we send N+zero)
    3: 'R',  # reverse
}


def command_qos():
    # Match webui_node → actuator_node (RELIABLE, KEEP_LAST 10)
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
        durability=DurabilityPolicy.VOLATILE,
    )


class SimChairRosBridge(Node):
    def __init__(self, udp_port: int, topic: str):
        super().__init__('simchair_ros_bridge')
        self.pub = self.create_publisher(ActuatorCommand, topic, command_qos())
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', udp_port))
        self.sock.settimeout(0.05)
        self.last_seq = -1
        self.last_print = 0.0
        self.packets = 0
        self.get_logger().info(
            f'Sim-chair UDP :{udp_port} → {topic} (ActuatorCommand). '
            f'Teensy stays with actuator_node. Do not use Chrome stick at the same time.'
        )
        self.create_timer(0.01, self._poll_udp)  # 100 Hz poll; sender ~20 Hz

    def _parse(self, data: bytes):
        text = data.decode(errors='replace').strip()
        parts = text.split(',')
        if len(parts) < 4:
            return None
        try:
            if len(parts) >= 6:
                seq = int(parts[0])
                steering = float(parts[2])
                throttle = float(parts[3])
                brake = float(parts[4])
                mode = int(parts[5])
                if seq <= self.last_seq:
                    return None
                self.last_seq = seq
            else:
                steering = float(parts[0])
                throttle = float(parts[1])
                brake = float(parts[2])
                mode = int(parts[3])
                self.last_seq += 1
        except ValueError:
            return None
        return steering, throttle, brake, mode

    def _poll_udp(self):
        try:
            data, _ = self.sock.recvfrom(256)
        except socket.timeout:
            return
        except OSError as e:
            self.get_logger().warn(f'UDP error: {e}')
            return

        parsed = self._parse(data)
        if parsed is None:
            return
        steering, throttle, brake, mode_i = parsed

        # Clamp like a sane teleop range
        steering = max(-1.0, min(1.0, steering))
        throttle = max(0.0, min(1.0, throttle))
        brake = max(0.0, min(1.0, brake))

        msg = ActuatorCommand()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = ''
        msg.estop = False
        msg.throttle = float(throttle)
        msg.brake = float(brake)
        # Negate: wheel left/right was mirrored vs WebUI / actuator convention
        msg.steer = float(-steering)

        if mode_i == 0:
            msg.mode = 'N'
            msg.throttle = 0.0
            msg.brake = 0.0
            msg.steer = 0.0
        elif mode_i == 2:
            # Sender "S" — treat as full stop / park for safety
            msg.mode = 'N'
            msg.throttle = 0.0
            msg.brake = 1.0
            msg.steer = 0.0
        else:
            msg.mode = MODE_MAP.get(mode_i, 'D')

        self.pub.publish(msg)
        self.packets += 1

        now = time.monotonic()
        if now - self.last_print > 0.25:
            self.get_logger().info(
                f'#{self.last_seq} mode={msg.mode} '
                f'S:{msg.steer:+.2f} T:{msg.throttle:.2f} B:{msg.brake:.2f}'
            )
            self.last_print = now


def main():
    parser = argparse.ArgumentParser(description='Sim-chair UDP → /avros/actuator_command')
    parser.add_argument('--udp-port', type=int, default=5006)
    parser.add_argument('--topic', default='/avros/actuator_command')
    args = parser.parse_args()

    rclpy.init()
    node = SimChairRosBridge(udp_port=args.udp_port, topic=args.topic)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.sock.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
