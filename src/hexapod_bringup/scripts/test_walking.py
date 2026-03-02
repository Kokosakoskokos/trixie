#!/usr/bin/env python3
"""Test script for hexapod walking."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import time


class WalkingTest(Node):
    """Test walking functionality."""
    
    def __init__(self):
        super().__init__('walking_test')
        
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.gait_pub = self.create_publisher(String, 'gait_type', 10)
        
        self.get_logger().info('Walking test node started')
        self.get_logger().info('Commands: w/s = forward/back, a/d = turn, space = stop, q = quit')
    
    def send_cmd(self, linear_x=0.0, linear_y=0.0, angular_z=0.0):
        """Send velocity command."""
        msg = Twist()
        msg.linear.x = linear_x
        msg.linear.y = linear_y
        msg.angular.z = angular_z
        self.cmd_vel_pub.publish(msg)
    
    def set_gait(self, gait_type):
        """Set gait type."""
        msg = String()
        msg.data = gait_type
        self.gait_pub.publish(msg)
        self.get_logger().info(f'Set gait to: {gait_type}')
    
    def run_demo(self):
        """Run walking demo."""
        self.get_logger().info('=== Walking Demo ===')
        
        # Wait for everything to start
        time.sleep(2)
        
        # Test tripod gait
        self.set_gait('tripod')
        time.sleep(1)
        
        self.get_logger().info('Walking forward...')
        self.send_cmd(linear_x=0.05)
        time.sleep(3)
        
        self.get_logger().info('Stopping...')
        self.send_cmd()
        time.sleep(1)
        
        self.get_logger().info('Turning left...')
        self.send_cmd(angular_z=0.3)
        time.sleep(2)
        
        self.get_logger().info('Stopping...')
        self.send_cmd()
        time.sleep(1)
        
        # Test wave gait
        self.set_gait('wave')
        time.sleep(1)
        
        self.get_logger().info('Walking forward with wave gait...')
        self.send_cmd(linear_x=0.03)
        time.sleep(3)
        
        self.get_logger().info('Stopping...')
        self.send_cmd()
        
        self.get_logger().info('Demo complete!')


def main():
    rclpy.init()
    node = WalkingTest()
    
    try:
        node.run_demo()
    except KeyboardInterrupt:
        pass
    finally:
        node.send_cmd()  # Stop robot
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
