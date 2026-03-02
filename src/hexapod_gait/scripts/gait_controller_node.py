#!/usr/bin/env python3
"""ROS2 node for gait control."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64MultiArray, String
from hexapod_gait.gait_generator import GaitController
import math


class GaitControllerNode(Node):
    """Node to generate gait patterns and publish foot positions."""
    
    def __init__(self):
        super().__init__('gait_controller_node')
        
        # Parameters
        self.declare_parameter('gait_type', 'tripod')
        self.declare_parameter('publish_rate', 50.0)
        self.declare_parameter('body_height', 0.12)
        
        # Gait controller
        gait_type = self.get_parameter('gait_type').value
        self.gait = GaitController(gait_type)
        
        # Publishers
        self.foot_pub = self.create_publisher(
            Float64MultiArray, 'foot_positions', 10
        )
        
        # Subscribers
        self.cmd_vel_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, 10
        )
        self.gait_sub = self.create_subscription(
            String, 'gait_type', self.gait_type_callback, 10
        )
        
        # Timer
        self.start_time = self.get_clock().now()
        rate = self.get_parameter('publish_rate').value
        self.timer = self.create_timer(1.0 / rate, self.timer_callback)
        
        self.get_logger().info(f'Gait controller started with {gait_type} gait')
    
    def cmd_vel_callback(self, msg):
        """Receive velocity commands."""
        self.gait.set_velocity(msg.linear.x, msg.linear.y, msg.angular.z)
    
    def gait_type_callback(self, msg):
        """Switch gait type."""
        if msg.data in self.gait.GAIT_TYPES:
            self.gait.set_gait(msg.data)
            self.get_logger().info(f'Switched to {msg.data} gait')
    
    def timer_callback(self):
        """Generate and publish foot positions."""
        # Calculate elapsed time
        now = self.get_clock().now()
        elapsed = (now - self.start_time).nanoseconds / 1e9
        
        # Get foot positions from gait generator
        foot_positions = self.gait.get_foot_positions(elapsed)
        
        # Flatten to array [x0,y0,z0, x1,y1,z1, ...]
        msg = Float64MultiArray()
        for pos in foot_positions:
            msg.data.extend([pos[0], pos[1], pos[2]])
        
        self.foot_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = GaitControllerNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
