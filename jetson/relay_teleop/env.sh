#!/bin/bash
# env.sh — shared ROS environment for the relay_teleop scripts (sourced, not run)
# Same setup as avros-webui: conda off, Cyclone, domain 0.
unset ROS_DOMAIN_ID DISPLAY
source /opt/ros/humble/setup.bash
source "${IGVC_WS:-$HOME/IGVC}/install/setup.bash"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://${IGVC_WS:-$HOME/IGVC}/install/avros_bringup/share/avros_bringup/config/cyclonedds.xml"
