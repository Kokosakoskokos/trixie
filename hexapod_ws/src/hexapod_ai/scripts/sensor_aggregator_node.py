#!/usr/bin/env python3
"""ROS2 node for aggregating sensor data for AI consumption."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, Range, NavSatFix
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import json


class SensorAggregatorNode(Node):
    """Aggregate sensor data and publish as JSON for AI node."""
    
    def __init__(self):
        super().__init__('sensor_aggregator_node')
        
        # Parameters
        self.declare_parameter('publish_rate', 5.0)  # Hz
        
        # Sensor data storage
        self.imu_data = {}
        self.ultrasonic_data = {}
        self.gps_data = {}
        self.current_velocity = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        
        # Subscribers
        self.imu_sub = self.create_subscription(
            Imu, 'imu/data', self.imu_callback, 10
        )
        self.ultrasonic_front_sub = self.create_subscription(
            Range, 'ultrasonic/front', self.make_us_callback('front'), 10
        )
        self.ultrasonic_left_sub = self.create_subscription(
            Range, 'ultrasonic/left', self.make_us_callback('left'), 10
        )
        self.ultrasonic_right_sub = self.create_subscription(
            Range, 'ultrasonic/right', self.make_us_callback('right'), 10
        )
        self.gps_sub = self.create_subscription(
            NavSatFix, 'gps/fix', self.gps_callback, 10
        )
        self.cmd_vel_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, 10
        )
        
        # Publisher
        self.sensor_pub = self.create_publisher(String, 'ai/sensor_data', 10)
        
        # Timer
        rate = self.get_parameter('publish_rate').value
        self.timer = self.create_timer(1.0 / rate, self.timer_callback)
        
        self.get_logger().info('Sensor aggregator node started')
    
    def imu_callback(self, msg):
        """Store IMU data."""
        self.imu_data = {
            'ax': msg.linear_acceleration.x,
            'ay': msg.linear_acceleration.y,
            'az': msg.linear_acceleration.z,
            'gx': msg.angular_velocity.x,
            'gy': msg.angular_velocity.y,
            'gz': msg.angular_velocity.z,
        }
    
    def make_us_callback(self, direction):
        """Create ultrasonic callback for given direction."""
        def callback(msg):
            self.ultrasonic_data[direction] = msg.range
        return callback
    
    def gps_callback(self, msg):
        """Store GPS data."""
        self.gps_data = {
            'lat': msg.latitude,
            'lon': msg.longitude,
            'alt': msg.altitude,
        }
    
    def cmd_vel_callback(self, msg):
        """Store current velocity."""
        self.current_velocity = {
            'x': msg.linear.x,
            'y': msg.linear.y,
            'z': msg.angular.z,
        }
    
    def timer_callback(self):
        """Publish aggregated sensor data."""
        data = {
            'imu': self.imu_data,
            'ultrasonic': self.ultrasonic_data,
            'gps': self.gps_data,
            'velocity': self.current_velocity,
        }
        
        msg = String()
        msg.data = json.dumps(data)
        self.sensor_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SensorAggregatorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
