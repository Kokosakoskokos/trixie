#!/usr/bin/env python3
"""ROS2 node for PCA9685 servo control."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from hexapod_hardware.servo_driver import HexapodServos
import math


class ServoDriverNode(Node):
    """Node to control hexapod servos via JointState messages."""
    
    def __init__(self):
        super().__init__('servo_driver_node')
        
        # Parameters
        self.declare_parameter('i2c_bus', 1)
        self.declare_parameter('use_hardware', True)
        self.declare_parameter('rate', 50)  # Hz
        
        self.use_hardware = self.get_parameter('use_hardware').value
        
        # Initialize servo driver
        if self.use_hardware:
            try:
                self.servos = HexapodServos(self.get_parameter('i2c_bus').value)
                self.get_logger().info('Servo driver initialized')
                # Set neutral on startup
                self.servos.set_all_neutral()
                self.get_logger().info('Servos set to neutral position')
            except Exception as e:
                self.get_logger().error(f'Failed to initialize servo driver: {e}')
                self.use_hardware = False
        
        # Subscriber for joint states
        self.joint_sub = self.create_subscription(
            JointState,
            'joint_states',
            self.joint_callback,
            10
        )

        # Subscriber for servo commands (e.g., zeroing)
        self.command_sub = self.create_subscription(
            String,
            'servo/command',
            self.command_callback,
            10
        )
        
        self.get_logger().info('Servo driver node started')
    
    def joint_callback(self, msg):
        """Process incoming joint states and update servos."""
        if not self.use_hardware:
            return
        
        for i, name in enumerate(msg.name):
            # Parse joint name: leg_X_joint_type_joint
            # e.g., leg_0_coxa_joint
            parts = name.split('_')
            if len(parts) != 4 or parts[0] != 'leg':
                continue
            
            try:
                leg_id = int(parts[1])
                joint_type = parts[2]  # coxa, femur, or tibia
                
                if leg_id < 0 or leg_id > 5:
                    continue
                if joint_type not in ['coxa', 'femur', 'tibia']:
                    continue
                
                angle_rad = msg.position[i] if i < len(msg.position) else 0.0
                
                # Update servo
                self.servos.set_joint_angle(leg_id, joint_type, angle_rad)
                
            except (ValueError, IndexError) as e:
                self.get_logger().warn(f'Failed to parse joint name {name}: {e}')

    def command_callback(self, msg):
        """Handle servo commands (zeroing)."""
        if not self.use_hardware:
            return

        command = msg.data.lower().strip()

        if command in ['zero', 'zero all', 'home', 'home all']:
            self.get_logger().info('Zeroing all legs to neutral')
            self.servos.set_all_neutral()
            return

        if command.startswith('zero leg'):
            # Format: "zero leg X"
            parts = command.split()
            if len(parts) == 3 and parts[2].isdigit():
                leg_id = int(parts[2])
                if 0 <= leg_id <= 5:
                    self.get_logger().info(f'Zeroing leg {leg_id} to neutral')
                    self.servos.set_leg_angles(leg_id, 0.0, 0.0, 0.0)
                else:
                    self.get_logger().warn('Invalid leg id (0-5)')
            else:
                self.get_logger().warn('Invalid command format. Use: "zero leg X"')
            return

        self.get_logger().warn(f'Unknown servo command: {command}')
    
    def destroy_node(self):
        """Cleanup on shutdown."""
        if self.use_hardware:
            self.get_logger().info('Setting servos to neutral before shutdown')
            self.servos.set_all_neutral()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ServoDriverNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
