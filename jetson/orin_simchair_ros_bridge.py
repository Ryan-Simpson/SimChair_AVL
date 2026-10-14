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

Link-loss watchdog:
  - No packet for --watchdog-ms (default 450) -> publish estop=True and LATCH.
    (450 clears the sender's ~300 ms pause on every mode switch.)
    actuator_node's e-stop zeroes the target with its fastest decel and
    ignores /cmd_vel while set, so Nav2 cannot take over on link loss.
  - While latched, e-stop is re-published at 10 Hz and drive packets are
    ignored. Release: put the sender in park (mode 0), then drive again.
  - On startup the bridge also waits for park before accepting drive.
  - Each poll drains the socket and applies only the newest packet, so a
    burst after a network stall never replays stale commands.

Drive modes (--drive-mode):
  diff       (default) wheel = spin rate, gas = forward, brake = reverse.
             Turning at a standstill spins in place (tank style).
  ackermann  car feel: wheel = turn radius (ω = v·steer/R_min, no turn when
             stopped), gas accelerates with momentum, brake slows, brake held
             at a stop for 0.5 s → reverse. See simchair_ackermann.py.
             Speed/accel limits are read from actuator_node at startup so the
             bridge ramps inside them and the arc stays exact.
  gear       paddle shifters pick live: gear 1 = diff, gear 2 = ackermann,
             gear 0 and 3 = off (zero command). Switching resets the
             ackermann speed state, so a mode change never carries momentum.
"""

from __future__ import annotations

import argparse
import socket
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from avros_msgs.msg import ActuatorCommand
from rcl_interfaces.srv import GetParameters
from std_msgs.msg import Header

from simchair_ackermann import AckermannMapper, AckermannParams

# actuator_node param → AckermannParams field it bounds (read at startup)
ACTUATOR_LIMITS = {
    'max_linear_mps': 'max_v',
    'max_angular_rps': 'max_w_rps',
    'max_linear_accel_mps2': 'accel',
    'max_linear_decel_mps2': 'decel',
    'track_width_m': 'track_m',
}
# repo defaults (avros_bringup/config/actuator_params.yaml), used until read
ACTUATOR_DEFAULTS = {'max_v': 1.5, 'max_w_rps': 1.5, 'accel': 0.3, 'decel': 1.3,
                     'track_m': 0.7366}
STALE_RESET_S = 0.5  # = actuator cmd_timeout: kart has stopped, drop momentum
GEAR_NAMES = {0: 'off', 1: 'differential (tank)', 2: 'ackermann (car)', 3: 'off'}

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
    def __init__(self, udp_port: int, topic: str, watchdog_s: float,
                 ackermann: AckermannParams | None = None, gear_select: bool = False):
        super().__init__('simchair_ros_bridge')
        self.gear_select = gear_select   # paddle gear picks diff (1) / ackermann (2)
        self.last_gear = None
        # Ackermann mode: user limits as given, clipped to actuator_node's.
        self.ack_req = ackermann
        self.ack = None
        self.limits = dict(ACTUATOR_DEFAULTS)
        self.last_step = None
        if ackermann is not None:
            self.ack = AckermannMapper(ackermann)
            self._apply_limits()
            self.param_cli = self.create_client(
                GetParameters, '/actuator_node/get_parameters')
            self.param_timer = self.create_timer(2.0, self._fetch_limits)
            self.param_future = None
        self.pub = self.create_publisher(ActuatorCommand, topic, command_qos())
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', udp_port))
        self.sock.setblocking(False)
        self.last_seq = -1
        self.last_print = 0.0
        self.packets = 0
        # Watchdog: latched until the sender reports park (mode 0).
        self.watchdog_s = watchdog_s
        self.last_rx = None          # monotonic time of last valid packet
        self.latched = True          # start latched: require park first
        self.tripped = False         # True only after a link-loss trip
        self.last_estop_pub = 0.0
        self.get_logger().info(
            f'Sim-chair UDP :{udp_port} → {topic} (ActuatorCommand). '
            f'Watchdog {watchdog_s * 1000:.0f} ms. Put sender in park (0) to arm. '
            f'Teensy stays with actuator_node. Do not use Chrome stick at the same time.'
        )
        if gear_select:
            mode_name = 'GEAR (1 = diff, 2 = ackermann, 0/3 = off)'
        else:
            mode_name = 'ACKERMANN (car style)' if self.ack else 'diff (tank style)'
        self.get_logger().info('Drive mode: ' + mode_name)
        self.create_timer(0.01, self._poll_udp)  # 100 Hz poll; sender ~20 Hz
        self.create_timer(0.02, self._watchdog)  # 50 Hz

    def _apply_limits(self):
        req, lim = self.ack_req, self.limits
        p = self.ack.p
        p.max_w_rps = lim['max_w_rps']
        p.track_m = lim['track_m']
        p.max_fwd_mps = min(req.max_fwd_mps, lim['max_v'])
        p.max_rev_mps = min(req.max_rev_mps, lim['max_v'])
        p.accel_mps2 = min(req.accel_mps2, lim['accel'])
        p.brake_decel_mps2 = min(req.brake_decel_mps2, lim['decel'])
        p.coast_decel_mps2 = min(req.coast_decel_mps2, lim['decel'])
        self.get_logger().info(
            f'Ackermann: R_min {p.min_radius_m:.2f} m, fwd {p.max_fwd_mps:.2f} / '
            f'rev {p.max_rev_mps:.2f} m/s, accel {p.accel_mps2:.2f}, '
            f'brake {p.brake_decel_mps2:.2f}, coast {p.coast_decel_mps2:.2f} m/s², '
            f'lat cap {p.lat_accel_mps2:.2f} m/s², pivot {p.pivot_rps:.2f} rad/s '
            f'(actuator max_v {lim["max_v"]:.2f}, max_w {lim["max_w_rps"]:.2f})')

    def _fetch_limits(self):
        """Read actuator_node's live limits once; retry every 2 s until it answers."""
        if self.param_future is None:
            if not self.param_cli.service_is_ready():
                return
            req = GetParameters.Request()
            req.names = list(ACTUATOR_LIMITS)
            self.param_future = self.param_cli.call_async(req)
            return
        if not self.param_future.done():
            return
        res = self.param_future.result()
        self.param_future = None
        if res is None or len(res.values) != len(ACTUATOR_LIMITS):
            return
        for name, val in zip(ACTUATOR_LIMITS, res.values):
            num = val.double_value if val.type == 3 else float(val.integer_value)
            if val.type in (2, 3) and num > 0.0:
                self.limits[ACTUATOR_LIMITS[name]] = num
        self.param_timer.cancel()
        self.get_logger().info('Read limits from actuator_node.')
        self._apply_limits()

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

    def _publish_estop(self):
        msg = ActuatorCommand()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = ''
        msg.estop = True
        msg.mode = 'N'
        self.pub.publish(msg)
        self.last_estop_pub = time.monotonic()

    def _watchdog(self):
        now = time.monotonic()
        if (not self.latched and self.last_rx is not None
                and now - self.last_rx > self.watchdog_s):
            self.latched = True
            self.tripped = True
            self._publish_estop()
            self.get_logger().warn(
                f'WATCHDOG: no packet for {(now - self.last_rx) * 1000:.0f} ms '
                f'→ E-STOP latched. Put sender in park (0) to re-arm.'
            )
        elif self.tripped and now - self.last_estop_pub >= 0.1:
            self._publish_estop()  # hold e-stop at 10 Hz while latched

    def _poll_udp(self):
        # Drain everything queued; keep only the newest valid packet.
        parsed = None
        while True:
            try:
                data, _ = self.sock.recvfrom(256)
            except BlockingIOError:
                break
            except OSError as e:
                self.get_logger().warn(f'UDP error: {e}')
                break
            p = self._parse(data)
            if p is not None:
                parsed = p
        if parsed is None:
            return
        self.last_rx = time.monotonic()
        steering, throttle, brake, mode_i = parsed

        if self.latched:
            if mode_i != 0:
                return  # ignore drive packets until park
            self.latched = False
            if self.tripped:
                self.get_logger().warn('Park received → watchdog re-armed, E-STOP released.')
            else:
                self.get_logger().info('Park received → armed.')
            self.tripped = False

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

        ack_log = ''
        # gear mode: 0 = off, 1 = diff, 2 = ackermann, 3 = off
        use_ack = self.ack is not None and (not self.gear_select or mode_i == 2)
        if mode_i == 0 or (self.gear_select and mode_i == 3):
            msg.mode = 'N'
            msg.throttle = 0.0
            msg.brake = 0.0
            msg.steer = 0.0
        elif mode_i == 2 and not self.gear_select:
            # Sender "S" — treat as full stop / park for safety
            msg.mode = 'N'
            msg.throttle = 0.0
            msg.brake = 1.0
            msg.steer = 0.0
        elif use_ack:
            ack_log = self._ackermann(msg, -steering, throttle, brake)
        else:
            msg.mode = MODE_MAP.get(mode_i, 'D')
        if self.ack is not None and (not use_ack or mode_i == 0):
            self.ack.reset()  # leaving ackermann: next entry starts from rest
            self.last_step = None
        if self.gear_select and mode_i != self.last_gear:
            self.get_logger().info(f'Gear {mode_i}: {GEAR_NAMES.get(mode_i, "off")}')
            self.last_gear = mode_i

        self.pub.publish(msg)
        self.packets += 1

        now = time.monotonic()
        if now - self.last_print > 0.25:
            self.get_logger().info(
                f'#{self.last_seq} mode={msg.mode} '
                f'S:{msg.steer:+.2f} T:{msg.throttle:.2f} B:{msg.brake:.2f}{ack_log}'
            )
            self.last_print = now

    def _ackermann(self, msg: ActuatorCommand, steer: float, gas: float,
                   brake: float) -> str:
        """Fill msg from the car-style mapper; steer is REP-103 (left = +)."""
        now = time.monotonic()
        if self.last_step is None or now - self.last_step > STALE_RESET_S:
            # First packet, or a gap long enough that actuator_node timed out
            # and stopped the kart: don't resume at the old speed.
            self.ack.reset()
            dt = 0.0
        else:
            dt = now - self.last_step
        self.last_step = now
        v, w = self.ack.step(steer, gas, brake, dt)
        # Encode so actuator_node's v = (T − B)·max_v, ω = steer·max_w gives back (v, ω)
        max_v, max_w = self.limits['max_v'], self.limits['max_w_rps']
        msg.throttle = max(v, 0.0) / max_v
        msg.brake = max(-v, 0.0) / max_v
        msg.steer = max(-1.0, min(1.0, w / max_w))
        msg.mode = 'R' if self.ack.reverse else 'D'
        left, right = self.ack.tracks(v, w)
        return f' | v {v:+.2f} m/s ω {w:+.2f} rad/s L {left:+.2f} R {right:+.2f}'


def main():
    parser = argparse.ArgumentParser(description='Sim-chair UDP → /avros/actuator_command')
    parser.add_argument('--udp-port', type=int, default=5006)
    parser.add_argument('--topic', default='/avros/actuator_command')
    parser.add_argument('--watchdog-ms', type=float, default=450.0,
                        help='E-stop if no packet for this long (latched until park)')
    d = AckermannParams()
    parser.add_argument('--drive-mode', choices=('diff', 'ackermann', 'gear'),
                        default='diff')
    parser.add_argument('--min-radius', type=float, default=d.min_radius_m,
                        help='ackermann: full-lock turn radius, m (> track/2 = 0.37)')
    parser.add_argument('--max-speed', type=float, default=d.max_fwd_mps,
                        help='ackermann: full-gas speed, m/s (capped at actuator max)')
    parser.add_argument('--rev-speed', type=float, default=d.max_rev_mps)
    parser.add_argument('--accel', type=float, default=d.accel_mps2)
    parser.add_argument('--brake-decel', type=float, default=d.brake_decel_mps2)
    parser.add_argument('--coast-decel', type=float, default=d.coast_decel_mps2)
    parser.add_argument('--rev-hold', type=float, default=d.rev_hold_s,
                        help='ackermann: hold brake at a stop this long (s) for reverse')
    parser.add_argument('--lat-accel', type=float, default=d.lat_accel_mps2,
                        help='ackermann: speed-sensitive steering cap, m/s² (0 = off)')
    parser.add_argument('--pivot', type=float, default=d.pivot_rps,
                        help='ackermann: turn rate allowed at a standstill (0 = pure car)')
    args = parser.parse_args()

    ack = None
    if args.drive_mode in ('ackermann', 'gear'):
        ack = AckermannParams(
            min_radius_m=args.min_radius, max_fwd_mps=args.max_speed,
            max_rev_mps=args.rev_speed, accel_mps2=args.accel,
            brake_decel_mps2=args.brake_decel, coast_decel_mps2=args.coast_decel,
            rev_hold_s=args.rev_hold, lat_accel_mps2=args.lat_accel,
            pivot_rps=args.pivot)

    rclpy.init()
    node = SimChairRosBridge(udp_port=args.udp_port, topic=args.topic,
                             watchdog_s=args.watchdog_ms / 1000.0, ackermann=ack,
                             gear_select=args.drive_mode == 'gear')
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
