#!/usr/bin/env bash
set -e

# Simple start command for the hexapod
if [ -f "install/setup.bash" ]; then
  source install/setup.bash
elif [ -f "/opt/ros/humble/setup.bash" ]; then
  source /opt/ros/humble/setup.bash
fi

ros2 launch hexapod_bringup hexapod.launch.py