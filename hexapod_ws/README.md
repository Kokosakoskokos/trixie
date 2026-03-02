# Hexapod Robot - ROS2

A fully-featured hexapod walking robot powered by ROS2 Humble, running on Raspberry Pi 4B with Ubuntu Server 22.04.

![Hexapod Robot](docs/hexapod.png)

## Features

- **18 DOF Legs** - 6 legs with 3 servos each (MG995)
- **Multiple Gaits** - Tripod (fast) and Wave (stable) walking patterns
- **AI Control** - OpenRouter integration for intelligent decision making
- **Person Tracking** - Computer vision-based person detection and following
- **Voice Commands** - Czech language support for voice/text control
- **Web Dashboard** - Real-time monitoring and control interface
- **Sensor Suite** - IMU, ultrasonic sensors, GPS, camera

## Hardware

| Component | Specification |
|-----------|---------------|
| Main Board | Raspberry Pi 4B 8GB |
| OS | Ubuntu Server 22.04 LTS |
| ROS Version | ROS2 Humble Hawksbill |
| Servos | 18x MG995 (3 per leg) |
| Servo Controller | 2x PCA9685 (I2C) |
| IMU | MPU-6050 |
| Distance Sensors | 3x HC-SR04 Ultrasonic |
| GPS | NEO-6M |
| Camera | USB Webcam |
| Power | 5V 10A BEC |

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Kokosakoskokos/trixie.git ~/hexapod_ws
cd ~/hexapod_ws

# Install dependencies
sudo apt update
sudo apt install -y python3-pip python3-opencv ros-humble-rosbridge-server
pip3 install requests RPi.GPIO smbus2 pyserial

# Build workspace
colcon build --symlink-install
source install/setup.bash
```

### Launch Robot

```bash
# Full system with hardware
ros2 launch hexapod_bringup hexapod.launch.py use_hardware:=true

# Simulation mode (no hardware)
ros2 launch hexapod_bringup simulation.launch.py

# With AI enabled
ros2 launch hexapod_bringup hexapod.launch.py use_ai:=true

# With Czech voice commands
ros2 launch hexapod_voice voice_control.launch.py
```

## Package Structure

```
hexapod_ws/
├── src/
│   ├── hexapod_ai/          # AI control and person tracking
│   ├── hexapod_bringup/     # Launch files
│   ├── hexapod_description/ # URDF robot model
│   ├── hexapod_gait/        # Gait generation
│   ├── hexapod_hardware/    # Hardware drivers
│   ├── hexapod_kinematics/  # Inverse kinematics
│   ├── hexapod_voice/       # Czech voice commands
│   └── hexapod_web/         # Web dashboard
```

## Usage

### Manual Control

```bash
# Movement commands
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {x: 0.1}}"  # Forward
ros2 topic pub /cmd_vel geometry_msgs/Twist "{angular: {z: 0.5}}" # Turn left
ros2 topic pub /cmd_vel geometry_msgs/Twist "{}"                   # Stop

# Change gait
ros2 topic pub /gait_type std_msgs/String "data: 'tripod'"
ros2 topic pub /gait_type std_msgs/String "data: 'wave'"
```

### Czech Voice Commands

```bash
# Send Czech commands
ros2 topic pub /voice/czech_command std_msgs/String "data: 'jeď dopředu'"
ros2 topic pub /voice/czech_command std_msgs/String "data: 'zastav'"
ros2 topic pub /voice/czech_command std_msgs/String "data: 'otoč se doleva'"
```

**Supported Czech Commands:**
- `dopředu`, `vpřed` - Forward
- `dozadu`, `zpátky` - Backward
- `doleva`, `vlevo` - Left
- `doprava`, `vpravo` - Right
- `zastav`, `stop` - Stop
- `zapni ai` - Enable AI
- `vypni ai` - Disable AI

### Person Tracking

```bash
# Download model first
python3 src/hexapod_ai/scripts/download_model.py

# Start tracking node
ros2 run hexapod_ai person_tracking_node.py

# Enable/disable tracking
ros2 topic pub /tracking/command std_msgs/String "data: 'start'"
ros2 topic pub /tracking/command std_msgs/String "data: 'stop'"
```

### AI Movement Generation

```bash
# Generate complex movements
ros2 topic pub /ai/movement_command std_msgs/String "data: '{\"description\": \"circle around\"}'"
ros2 topic pub /ai/movement_command std_msgs/String "data: '{\"description\": \"search pattern\"}'"
```

**Available Movement Types:**
- `linear` - Straight line
- `rotational` - Turn in place
- `circular` - Circle pattern
- `zigzag` - Zigzag pattern
- `spiral` - Spiral outward
- `figure_eight` - Figure-8 pattern
- `search_pattern` - Systematic area search
- `avoidance` - Obstacle avoidance

### Web Dashboard

Access the dashboard at `http://<pi-ip>:8080`

Features:
- Live camera feed
- Sensor data display (IMU, ultrasonic)
- D-pad manual control
- Speed adjustment
- Gait selection
- AI enable/disable
- Person tracking controls
- Real-time logs

## Configuration

### Servo Calibration

Edit `hexapod_hardware/hexapod_hardware/servo_driver.py`:

```python
JOINT_OFFSETS = {
    0: {'coxa': 0, 'femur': 5, 'tibia': -3},  # Leg 0 offsets
    # ... adjust per leg
}
```

### AI Settings

Set OpenRouter API key:
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Or in launch file:
```bash
ros2 launch hexapod_bringup hexapod.launch.py api_key:="sk-or-v1-..."
```

### Camera Settings

Edit `hexapod_hardware/scripts/camera_driver_node.py`:
```python
self.declare_parameter('width', 640)
self.declare_parameter('height', 480)
self.declare_parameter('fps', 30)
```

## I2C Setup

```bash
# Enable I2C
sudo raspi-config
# Interface Options -> I2C -> Enable

# Check devices
sudo i2cdetect -y 1
# Expected: 0x40, 0x41 (PCA9685), 0x68 (MPU-6050)
```

## Safety Features

- **Emergency Stop**: Publishes empty Twist to `/cmd_vel`
- **Obstacle Detection**: Stops if object < 30cm
- **Tilt Protection**: Stops if tilt > 20 degrees
- **Servo Limits**: Software limits on joint angles
- **Watchdog**: Auto-stop on communication loss

## Troubleshooting

### Servos not responding
```bash
# Check I2C
sudo i2cdetect -y 1

# Verify permissions
sudo usermod -a -G gpio,i2c $USER
# Log out and back in
```

### Camera not working
```bash
# Check device
ls /dev/video*

# Test with OpenCV
python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

### Build errors
```bash
# Clean and rebuild
rm -rf build/ install/ log/
colcon build --symlink-install
```

## Development

### Adding New Gaits

Edit `hexapod_gait/hexapod_gait/gait_generator.py`:

```python
class MyGait:
    def get_foot_positions(self, time, direction=0.0, speed=1.0):
        # Your gait logic
        return positions
```

### Adding Voice Commands

Edit `hexapod_voice/hexapod_voice/czech_parser.py`:

```python
MOVEMENT_COMMANDS = {
    'my_command': {'linear_x': 0.1},
}
```

## License

MIT License - See LICENSE file

## Credits

- Created by [Kokosakoskokos](https://github.com/Kokosakoskokos)
- Powered by ROS2 and OpenCV
- AI by OpenRouter

## Support

For issues and feature requests, please use GitHub Issues.
