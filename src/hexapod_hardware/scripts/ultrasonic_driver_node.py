#!/usr/bin/env python3
"""ROS2 node for ultrasonic distance sensors (HC-SR04)."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range
import RPi.GPIO as GPIO
import time


class UltrasonicSensor:
    """HC-SR04 ultrasonic sensor driver."""
    
    def __init__(self, trig_pin, echo_pin):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        
        GPIO.output(self.trig_pin, False)
        time.sleep(0.1)
    
    def read_distance(self):
        """Read distance in meters."""
        # Send trigger pulse
        GPIO.output(self.trig_pin, True)
        time.sleep(0.00001)  # 10us
        GPIO.output(self.trig_pin, False)
        
        # Wait for echo start
        start_time = time.time()
        timeout = start_time + 0.04  # 40ms timeout
        
        while GPIO.input(self.echo_pin) == 0:
            start_time = time.time()
            if start_time > timeout:
                return float('inf')
        
        # Wait for echo end
        end_time = time.time()
        timeout = end_time + 0.04
        
        while GPIO.input(self.echo_pin) == 1:
            end_time = time.time()
            if end_time > timeout:
                return float('inf')
        
        # Calculate distance
        # Speed of sound = 343 m/s
        # Distance = (time * speed) / 2 (round trip)
        duration = end_time - start_time
        distance = (duration * 343.0) / 2.0
        
        return distance


class UltrasonicDriverNode(Node):
    """Node to publish ultrasonic sensor data."""
    
    # Default pin configuration
    DEFAULT_PINS = {
        'front': {'trig': 23, 'echo': 24},
        'left': {'trig': 17, 'echo': 27},
        'right': {'trig': 5, 'echo': 6},
    }
    
    def __init__(self):
        super().__init__('ultrasonic_driver_node')
        
        # Parameters
        self.declare_parameter('use_hardware', True)
        self.declare_parameter('publish_rate', 10.0)  # Hz
        self.declare_parameter('min_range', 0.02)  # 2cm
        self.declare_parameter('max_range', 4.0)   # 4m
        
        self.use_hardware = self.get_parameter('use_hardware').value
        
        # Setup GPIO
        if self.use_hardware:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
        
        # Initialize sensors
        self.sensors = {}
        self.publishers = {}
        
        for name, pins in self.DEFAULT_PINS.items():
            topic_name = f'ultrasonic/{name}'
            self.publishers[name] = self.create_publisher(Range, topic_name, 10)
            
            if self.use_hardware:
                try:
                    self.sensors[name] = UltrasonicSensor(
                        pins['trig'], pins['echo']
                    )
                    self.get_logger().info(f'Ultrasonic sensor {name} initialized')
                except Exception as e:
                    self.get_logger().error(f'Failed to init {name} sensor: {e}')
        
        # Timer
        rate = self.get_parameter('publish_rate').value
        self.timer = self.create_timer(1.0 / rate, self.timer_callback)
        
        self.get_logger().info('Ultrasonic driver node started')
    
    def timer_callback(self):
        """Read and publish sensor data."""
        if not self.use_hardware:
            return
        
        min_range = self.get_parameter('min_range').value
        max_range = self.get_parameter('max_range').value
        
        for name, sensor in self.sensors.items():
            try:
                distance = sensor.read_distance()
                
                # Clamp to valid range
                distance = max(min_range, min(max_range, distance))
                
                msg = Range()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.header.frame_id = f'ultrasonic_{name}_link'
                msg.radiation_type = Range.ULTRASOUND
                msg.field_of_view = 0.26  # ~15 degrees
                msg.min_range = min_range
                msg.max_range = max_range
                msg.range = distance
                
                self.publishers[name].publish(msg)
                
            except Exception as e:
                self.get_logger().warn(f'Error reading {name} sensor: {e}')
    
    def destroy_node(self):
        """Cleanup GPIO."""
        if self.use_hardware:
            GPIO.cleanup()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UltrasonicDriverNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
