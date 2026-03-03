#!/usr/bin/env python3
"""ROS2 node for MPU-6050 IMU."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, Temperature
from geometry_msgs.msg import Vector3
import smbus2
import math


class MPU6050:
    """MPU-6050 driver over I2C."""
    
    # Registers
    PWR_MGMT_1 = 0x6B
    CONFIG = 0x1A
    GYRO_CONFIG = 0x1B
    ACCEL_CONFIG = 0x1C
    
    ACCEL_XOUT_H = 0x3B
    TEMP_OUT_H = 0x41
    GYRO_XOUT_H = 0x43
    
    # Scale factors
    ACCEL_SCALE = 16384.0  # for +/- 2g
    GYRO_SCALE = 131.0     # for +/- 250 deg/s
    
    def __init__(self, bus_num=1, address=0x68):
        self.bus = smbus2.SMBus(bus_num)
        self.address = address
        self._init_device()
    
    def _init_device(self):
        """Initialize the MPU-6050."""
        # Wake up
        self.bus.write_byte_data(self.address, self.PWR_MGMT_1, 0x00)
        # Set DLPF to 44Hz
        self.bus.write_byte_data(self.address, self.CONFIG, 0x03)
        # Set gyro range to +/- 250 deg/s
        self.bus.write_byte_data(self.address, self.GYRO_CONFIG, 0x00)
        # Set accel range to +/- 2g
        self.bus.write_byte_data(self.address, self.ACCEL_CONFIG, 0x00)
    
    def read_word(self, reg):
        """Read a 16-bit word from device."""
        high = self.bus.read_byte_data(self.address, reg)
        low = self.bus.read_byte_data(self.address, reg + 1)
        val = (high << 8) + low
        if val >= 0x8000:
            return -((65535 - val) + 1)
        return val
    
    def read_accel(self):
        """Read accelerometer data (m/s^2)."""
        x = self.read_word(self.ACCEL_XOUT_H)
        y = self.read_word(self.ACCEL_XOUT_H + 2)
        z = self.read_word(self.ACCEL_XOUT_H + 4)
        
        # Convert to m/s^2 (1g = 9.80665 m/s^2)
        x = (x / self.ACCEL_SCALE) * 9.80665
        y = (y / self.ACCEL_SCALE) * 9.80665
        z = (z / self.ACCEL_SCALE) * 9.80665
        
        return (x, y, z)
    
    def read_gyro(self):
        """Read gyroscope data (rad/s)."""
        x = self.read_word(self.GYRO_XOUT_H)
        y = self.read_word(self.GYRO_XOUT_H + 2)
        z = self.read_word(self.GYRO_XOUT_H + 4)
        
        # Convert to rad/s
        x = math.radians(x / self.GYRO_SCALE)
        y = math.radians(y / self.GYRO_SCALE)
        z = math.radians(z / self.GYRO_SCALE)
        
        return (x, y, z)
    
    def read_temp(self):
        """Read temperature (Celsius)."""
        temp = self.read_word(self.TEMP_OUT_H)
        return (temp / 340.0) + 36.53


class IMUDriverNode(Node):
    """Node to publish IMU data."""
    
    def __init__(self):
        super().__init__('imu_driver_node')
        
        # Parameters
        self.declare_parameter('i2c_bus', 1)
        self.declare_parameter('i2c_address', 0x68)
        self.declare_parameter('publish_rate', 100.0)  # Hz
        self.declare_parameter('use_hardware', True)
        
        self.use_hardware = self.get_parameter('use_hardware').value
        
        # Initialize IMU
        if self.use_hardware:
            try:
                self.imu = MPU6050(
                    self.get_parameter('i2c_bus').value,
                    self.get_parameter('i2c_address').value
                )
                self.get_logger().info('IMU initialized')
            except Exception as e:
                self.get_logger().error(f'Failed to initialize IMU: {e}')
                self.use_hardware = False
        
        # Publishers
        self.imu_pub = self.create_publisher(Imu, 'imu/data', 10)
        self.temp_pub = self.create_publisher(Temperature, 'imu/temperature', 10)
        
        # Timer
        rate = self.get_parameter('publish_rate').value
        self.timer = self.create_timer(1.0 / rate, self.timer_callback)
        
        self.get_logger().info('IMU driver node started')
    
    def timer_callback(self):
        """Read and publish IMU data."""
        if not self.use_hardware:
            return
        
        try:
            ax, ay, az = self.imu.read_accel()
            gx, gy, gz = self.imu.read_gyro()
            temp = self.imu.read_temp()
            
            # Create IMU message
            imu_msg = Imu()
            imu_msg.header.stamp = self.get_clock().now().to_msg()
            imu_msg.header.frame_id = 'imu_link'
            
            # Linear acceleration
            imu_msg.linear_acceleration.x = ax
            imu_msg.linear_acceleration.y = ay
            imu_msg.linear_acceleration.z = az
            
            # Angular velocity
            imu_msg.angular_velocity.x = gx
            imu_msg.angular_velocity.y = gy
            imu_msg.angular_velocity.z = gz
            
            # Orientation (not provided by MPU-6050 without DMP/fusion)
            # Set to invalid quaternion
            imu_msg.orientation.x = 0.0
            imu_msg.orientation.y = 0.0
            imu_msg.orientation.z = 0.0
            imu_msg.orientation.w = 1.0
            
            # Covariance (unknown, set to -1)
            imu_msg.orientation_covariance[0] = -1
            
            self.imu_pub.publish(imu_msg)
            
            # Temperature
            temp_msg = Temperature()
            temp_msg.header = imu_msg.header
            temp_msg.temperature = temp
            self.temp_pub.publish(temp_msg)
            
        except Exception as e:
            self.get_logger().error(f'Error reading IMU: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = IMUDriverNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
