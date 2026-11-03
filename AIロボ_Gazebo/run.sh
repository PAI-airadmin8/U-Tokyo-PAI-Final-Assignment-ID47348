#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/airobot_ws/pai_airobo_v3_delivery
if [ ! -x bin/airobo_native_motion_owner ] || [ src/airobo_native_motion_owner.cpp -nt bin/airobo_native_motion_owner ]; then
  g++ -O1 -std=c++17 src/airobo_native_motion_owner.cpp -o bin/airobo_native_motion_owner $(pkg-config --cflags --libs ignition-transport11)
fi
exec python3 -u autonomous_pick_place.py
