#!/usr/bin/env python3
"""ROS2 node for NEO-6M GPS module."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, NavSatStatus
import serial


class GPSDriverNode(Node):
    """Node to publish GPS data from NEO-6M."""
    
    def __init__(self):
        super().__init__('gps_driver_node')
        
        # Parameters
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 9600)
        self.declare_parameter('use_hardware', True)
        self.declare_parameter('publish_rate', 1.0)  # Hz
        self.declare_parameter('frame_id', 'gps_link')
        
        self.use_hardware = self.get_parameter('use_hardware').value
        self.frame_id = self.get_parameter('frame_id').value
        
        # Initialize serial
        if self.use_hardware:
            try:
                self.serial = serial.Serial(
                    port=self.get_parameter('port').value,
                    baudrate=self.get_parameter('baudrate').value,
                    timeout=1
                )
                self.get_logger().info(f'GPS initialized on {self.serial.port}')
            except Exception as e:
                self.get_logger().error(f'Failed to initialize GPS: {e}')
                self.use_hardware = False
        
        # Publisher
        self.gps_pub = self.create_publisher(NavSatFix, 'gps/fix', 10)
        
        # Timer
        rate = self.get_parameter('publish_rate').value
        self.timer = self.create_timer(1.0 / rate, self.timer_callback)
        
        self.get_logger().info('GPS driver node started')
    
    def parse_nmea(self, line):
        """Parse NMEA GGA sentence."""
        if not line.startswith('$GPGGA'):
            return None
        
        parts = line.split(',')
        if len(parts) < 10:
            return None
        
        try:
            # Check fix quality
            fix_quality = int(parts[6])
            if fix_quality == 0:
                return None  # No fix
            
            # Parse latitude
            lat_raw = parts[2]
            lat_dir = parts[3]
            if lat_raw and lat_dir:
                lat_deg = float(lat_raw[:2])
                lat_min = float(lat_raw[2:])
                latitude = lat_deg + lat_min / 60.0
                if lat_dir == 'S':
                    latitude = -latitude
            else:
                return None
            
            # Parse longitude
            lon_raw = parts[4]
            lon_dir = parts[5]
            if lon_raw and lon_dir:
                lon_deg = float(lon_raw[:3])
                lon_min = float(lon_raw[3:])
                longitude = lon_deg + lon_min / 60.0
                if lon_dir == 'W':
                    longitude = -longitude
            else:
                return None
            
            # Parse altitude
            altitude = float(parts[9]) if parts[9] else 0.0
            
            # Parse HDOP (horizontal dilution of precision)
            hdop = float(parts[8]) if parts[8] else 99.9
            
            return {
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'hdop': hdop,
                'fix_quality': fix_quality
            }
            
        except (ValueError, IndexError) as e:
            return None
    
    def timer_callback(self):
        """Read and publish GPS data."""
        if not self.use_hardware:
            return
        
        try:
            # Read lines until we get a GGA sentence
            for _ in range(10):  # Limit attempts
                line = self.serial.readline().decode('ascii', errors='ignore').strip()
                data = self.parse_nmea(line)
                
                if data:
                    msg = NavSatFix()
                    msg.header.stamp = self.get_clock().now().to_msg()
                    msg.header.frame_id = self.frame_id
                    
                    msg.latitude = data['latitude']
                    msg.longitude = data['longitude']
                    msg.altitude = data['altitude']
                    
                    # Status
                    msg.status = NavSatStatus()
                    msg.status.status = NavSatStatus.STATUS_FIX
                    msg.status.service = NavSatStatus.SERVICE_GPS
                    
                    # Position covariance (using HDOP)
                    # Approximate: covariance = (HDOP * 5m)^2
                    covariance = (data['hdop'] * 5.0) ** 2
                    msg.position_covariance = [
                        covariance, 0, 0,
                        0, covariance, 0,
                        0, 0, covariance * 4  # altitude less accurate
                    ]
                    msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_APPROXIMATED
                    
                    self.gps_pub.publish(msg)
                    break
                    
        except Exception as e:
            self.get_logger().warn(f'Error reading GPS: {e}')
    
    def destroy_node(self):
        """Close serial port."""
        if self.use_hardware and hasattr(self, 'serial'):
            self.serial.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = GPSDriverNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
