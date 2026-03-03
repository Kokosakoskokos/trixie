#!/usr/bin/env python3
"""ROS2 node for camera streaming using OpenCV."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import threading
import http.server
import socketserver
from io import BytesIO


class MJPEGStreamHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for MJPEG streaming."""
    
    camera_frame = None
    
    def do_GET(self):
        if self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            
            while True:
                if MJPEGStreamHandler.camera_frame is not None:
                    try:
                        # Encode frame as JPEG
                        ret, jpeg = cv2.imencode('.jpg', MJPEGStreamHandler.camera_frame)
                        if ret:
                            self.wfile.write(b'--jpgboundary\r\n')
                            self.send_header('Content-type', 'image/jpeg')
                            self.send_header('Content-length', len(jpeg))
                            self.end_headers()
                            self.wfile.write(jpeg.tobytes())
                            self.wfile.write(b'\r\n')
                    except Exception:
                        break
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass


class CameraDriverNode(Node):
    """Node to capture camera and serve MJPEG stream."""
    
    def __init__(self):
        super().__init__('camera_driver_node')
        
        # Parameters
        self.declare_parameter('device', '/dev/video0')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 30)
        self.declare_parameter('stream_port', 8081)
        self.declare_parameter('use_hardware', True)
        self.declare_parameter('publish_ros_topic', True)
        
        self.use_hardware = self.get_parameter('use_hardware').value
        self.publish_ros = self.get_parameter('publish_ros_topic').value
        
        # CV Bridge
        self.bridge = CvBridge()
        
        # Publisher
        if self.publish_ros:
            self.image_pub = self.create_publisher(Image, 'camera/image_raw', 10)
        
        # Camera
        self.cap = None
        self.running = False
        self.capture_thread = None
        
        # HTTP server for MJPEG stream
        self.http_server = None
        self.http_thread = None
        
        if self.use_hardware:
            self.init_camera()
            self.start_stream_server()
        
        # Timer for capturing
        fps = self.get_parameter('fps').value
        self.timer = self.create_timer(1.0 / fps, self.capture_frame)
        
        self.get_logger().info('Camera driver node started')
        if self.use_hardware:
            self.get_logger().info(f'MJPEG stream at http://{self._get_ip()}:{self.get_parameter("stream_port").value}/stream.mjpg')
    
    def _get_ip(self):
        """Get IP address."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return 'localhost'
    
    def init_camera(self):
        """Initialize camera."""
        device = self.get_parameter('device').value
        width = self.get_parameter('width').value
        height = self.get_parameter('height').value
        
        self.cap = cv2.VideoCapture(device)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        if not self.cap.isOpened():
            self.get_logger().error(f'Failed to open camera: {device}')
            self.use_hardware = False
        else:
            self.get_logger().info(f'Camera opened: {width}x{height}')
    
    def start_stream_server(self):
        """Start HTTP server for MJPEG streaming."""
        port = self.get_parameter('stream_port').value
        
        try:
            self.http_server = socketserver.ThreadingTCPServer(('', port), MJPEGStreamHandler)
            self.http_thread = threading.Thread(target=self.http_server.serve_forever)
            self.http_thread.daemon = True
            self.http_thread.start()
            self.get_logger().info(f'Stream server started on port {port}')
        except Exception as e:
            self.get_logger().error(f'Failed to start stream server: {e}')
    
    def capture_frame(self):
        """Capture frame from camera."""
        if not self.use_hardware or self.cap is None:
            return
        
        ret, frame = self.cap.read()
        if not ret:
            return
        
        # Update stream frame
        MJPEGStreamHandler.camera_frame = frame
        
        # Publish to ROS topic
        if self.publish_ros:
            try:
                msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.header.frame_id = 'camera_link'
                self.image_pub.publish(msg)
            except Exception as e:
                self.get_logger().warn(f'Failed to publish image: {e}')
    
    def destroy_node(self):
        """Cleanup."""
        self.running = False
        
        if self.http_server:
            self.http_server.shutdown()
        
        if self.cap:
            self.cap.release()
        
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraDriverNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
