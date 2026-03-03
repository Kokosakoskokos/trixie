#!/usr/bin/env python3
"""ROS2 node for serving the web dashboard."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import http.server
import socketserver
import threading
import os
import json
from pathlib import Path


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for dashboard."""
    
    def __init__(self, *args, package_path=None, **kwargs):
        self.package_path = package_path
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.path = '/index.html'
        
        # Map to package directories
        if self.path.startswith('/static/'):
            file_path = os.path.join(self.package_path, 'static', self.path[8:])
        elif self.path.startswith('/templates/'):
            file_path = os.path.join(self.package_path, 'templates', self.path[11:])
        else:
            file_path = os.path.join(self.package_path, 'templates', self.path[1:])
        
        # Serve file
        if os.path.exists(file_path):
            self.send_response(200)
            
            # Set content type
            if file_path.endswith('.html'):
                self.send_header('Content-type', 'text/html')
            elif file_path.endswith('.js'):
                self.send_header('Content-type', 'application/javascript')
            elif file_path.endswith('.css'):
                self.send_header('Content-type', 'text/css')
            
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class WebServerNode(Node):
    """Node to serve the web dashboard."""
    
    def __init__(self):
        super().__init__('web_server_node')
        
        # Parameters
        self.declare_parameter('port', 8080)
        self.declare_parameter('rosbridge_port', 9090)
        
        self.port = self.get_parameter('port').value
        self.rosbridge_port = self.get_parameter('rosbridge_port').value
        
        # Find package path
        self.package_path = self._get_package_path()
        
        # Start HTTP server in separate thread
        self.server = None
        self.server_thread = None
        self.start_server()
        
        self.get_logger().info(f'Web dashboard available at http://{self._get_ip()}:{self.port}')
        self.get_logger().info(f'Make sure rosbridge_server is running on port {self.rosbridge_port}')
    
    def _get_package_path(self):
        """Get the package share directory path."""
        from ament_index_python.packages import get_package_share_directory
        return get_package_share_directory('hexapod_web')
    
    def _get_ip(self):
        """Get the machine's IP address."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return 'localhost'
    
    def start_server(self):
        """Start the HTTP server."""
        def handler(*args, **kwargs):
            return DashboardHandler(*args, package_path=self.package_path, **kwargs)
        
        try:
            self.server = socketserver.TCPServer(('', self.port), handler)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            self.get_logger().info(f'HTTP server started on port {self.port}')
        except Exception as e:
            self.get_logger().error(f'Failed to start HTTP server: {e}')
    
    def destroy_node(self):
        """Cleanup on shutdown."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WebServerNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
