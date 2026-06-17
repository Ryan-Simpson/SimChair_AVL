Read-Host -Prompt "Press enter to start"

cd 'C:\Users\VRX 226\cpp_agv'

vrx_ros2_ws\install\setup.ps1


$env:RMW_IMPLEMENTATION = 'rmw_fastrtps_cpp'
$env:FASTRTPS_DEFAULT_PROFILES_FILE = '.\husarnet-fastdds.xml'




ros2 launch "vrx_ros2_ws\launch\launchdemo.py";
Read-Host -Prompt "Press enter to start"
IMUClient_AGV - Shortcut


Read-Host -Prompt "Press enter to exit"



