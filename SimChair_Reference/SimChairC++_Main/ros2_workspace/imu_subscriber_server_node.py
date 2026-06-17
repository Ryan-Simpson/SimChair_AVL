import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Imu
import socket
import time
import logging


HOST = "127.0.0.1"
PORT = 9999
 

class ImuSubscriberServer(Node):
    def __init__(self):
        super().__init__('minimal_subscriber')

        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT,
            history=QoSHistoryPolicy.RMW_QOS_POLICY_HISTORY_KEEP_LAST,
            depth=1
        )
        # /camera/accel/sample
        self.subscription = self.create_subscription(
            Imu,
            '/camera/accel/sample',
            self.listener_callback,
            qos_profile=qos_profile)
        self.subscription  # prevent unused variable warning
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.s.bind((HOST,PORT))
        self.s.listen()
        self.conn, self.addr = self.s.accept()

        time.sleep(5)

    def listener_callback(self, msg):
        pitch = round(msg.linear_acceleration.x,2)
        roll = round(msg.linear_acceleration.z,2)
        pitch_str = str(pitch)
        roll_str = str(roll)
        accel_msg = (pitch_str + "/" + roll_str + "/")
        # with self.conn:
        self.conn.send(accel_msg.encode())

        self.get_logger().info(accel_msg)
        # print(msg.linear_acceleration)

        # print("Pitch: " + pitch_str + " " + "Roll: " + roll_str)
        time.sleep(.2)



def main(args=None):
    rclpy.init(args=args)
    imu_subscriber_server = ImuSubscriberServer()
    rclpy.spin(imu_subscriber_server)
    imu_subscriber_server.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
