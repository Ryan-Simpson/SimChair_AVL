
from launch import LaunchDescription
from launch_ros.actions import Node
import subprocess
def generate_launch_description():
    return LaunchDescription([
        Node(
            package='vrx_controller',
            executable='vrx_controller_pub',

        ),
        Node(
            package='imu_subscriber_server',
            executable='imu_subscriber_server_node',
        ),
    ])

    
    
    