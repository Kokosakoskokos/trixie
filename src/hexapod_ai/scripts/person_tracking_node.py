#!/usr/bin/env python3
"""ROS2 node for person detection and tracking."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from std_msgs.msg import String, Bool
from cv_bridge import CvBridge
import cv2
import numpy as np
import math


class PersonTracker:
    """Person detection and tracking using OpenCV DNN."""
    
    def __init__(self):
        # Load pre-trained MobileNet SSD model
        self.net = cv2.dnn.readNetFromCaffe(
            'MobileNetSSD_deploy.prototxt',
            'MobileNetSSD_deploy.caffemodel'
        )
        
        # Classes MobileNet SSD can detect
        self.classes = [
            'background', 'aeroplane', 'bicycle', 'bird', 'boat',
            'bottle', 'bus', 'car', 'cat', 'chair', 'cow', 'diningtable',
            'dog', 'horse', 'motorbike', 'person', 'pottedplant',
            'sheep', 'sofa', 'train', 'tvmonitor'
        ]
        
        self.person_class_id = 15  # 'person' class index
        
        # Tracking state
        self.tracked_person = None  # (x, y, w, h) in normalized coordinates
        self.lost_frames = 0
        self.max_lost_frames = 30
        
        # Confidence threshold
        self.confidence_threshold = 0.5
    
    def detect(self, frame):
        """Detect persons in frame.
        
        Args:
            frame: OpenCV image (BGR)
        
        Returns:
            List of detections [(x, y, w, h, confidence), ...]
        """
        h, w = frame.shape[:2]
        
        # Create blob from image
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)),
            0.007843, (300, 300), 127.5
        )
        
        # Pass blob through network
        self.net.setInput(blob)
        detections = self.net.forward()
        
        persons = []
        
        # Loop through detections
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            if confidence > self.confidence_threshold:
                class_id = int(detections[0, 0, i, 1])
                
                # Check if it's a person
                if class_id == self.person_class_id:
                    # Get bounding box coordinates
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    x, y, x2, y2 = box.astype(int)
                    
                    bw = x2 - x
                    bh = y2 - y
                    
                    # Normalize coordinates
                    nx = (x + bw/2) / w  # Center x (0-1)
                    ny = (y + bh/2) / h  # Center y (0-1)
                    nw = bw / w          # Width (0-1)
                    nh = bh / h          # Height (0-1)
                    
                    persons.append((nx, ny, nw, nh, confidence))
        
        return persons
    
    def update_tracking(self, detections):
        """Update tracking with new detections.
        
        Args:
            detections: List of person detections
        
        Returns:
            Tracked person (x, y, w, h) or None
        """
        if not detections:
            self.lost_frames += 1
            if self.lost_frames > self.max_lost_frames:
                self.tracked_person = None
            return self.tracked_person
        
        # If no current tracking, pick largest detection
        if self.tracked_person is None:
            # Sort by area (w * h)
            detections.sort(key=lambda d: d[2] * d[3], reverse=True)
            best = detections[0]
            self.tracked_person = best[:4]
            self.lost_frames = 0
            return self.tracked_person
        
        # Find detection closest to current tracking
        tx, ty = self.tracked_person[0], self.tracked_person[1]
        
        best_match = None
        best_distance = float('inf')
        
        for det in detections:
            dx, dy = det[0], det[1]
            distance = math.sqrt((dx - tx)**2 + (dy - ty)**2)
            
            if distance < best_distance:
                best_distance = distance
                best_match = det
        
        # Update if close enough
        if best_match and best_distance < 0.3:  # 30% of frame size
            self.tracked_person = best_match[:4]
            self.lost_frames = 0
        else:
            self.lost_frames += 1
            if self.lost_frames > self.max_lost_frames:
                self.tracked_person = None
        
        return self.tracked_person
    
    def get_tracking_error(self, frame_width=640, frame_height=480):
        """Get tracking error from frame center.
        
        Returns:
            (error_x, error_y, distance_estimate) in normalized coordinates
        """
        if self.tracked_person is None:
            return None
        
        x, y, w, h = self.tracked_person
        
        # Error from center (0.5, 0.5)
        error_x = x - 0.5
        error_y = y - 0.5
        
        # Estimate distance based on person height in frame
        # Larger height = closer
        distance_estimate = 1.0 / (h + 0.01)  # Inverse of height
        
        return (error_x, error_y, distance_estimate)
    
    def draw_detections(self, frame, detections, tracked=None):
        """Draw detection boxes on frame."""
        h, w = frame.shape[:2]
        
        # Draw all detections
        for det in detections:
            x, y, bw, bh, conf = det
            px = int((x - bw/2) * w)
            py = int((y - bh/2) * h)
            pw = int(bw * w)
            ph = int(bh * h)
            
            cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 255, 0), 2)
            cv2.putText(frame, f'Person: {conf:.2f}', (px, py - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw tracked person in different color
        if tracked:
            x, y, bw, bh = tracked
            px = int((x - bw/2) * w)
            py = int((y - bh/2) * h)
            pw = int(bw * w)
            ph = int(bh * h)
            
            cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 0, 255), 3)
            
            # Draw center point
            cx = int(x * w)
            cy = int(y * h)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            
            # Draw line to frame center
            cv2.line(frame, (cx, cy), (w//2, h//2), (255, 0, 0), 2)
        
        # Draw frame center
        cv2.circle(frame, (w//2, h//2), 5, (255, 255, 0), -1)
        
        return frame


class PersonTrackingNode(Node):
    """ROS2 node for person tracking."""
    
    def __init__(self):
        super().__init__('person_tracking_node')
        
        # Parameters
        self.declare_parameter('use_camera', True)
        self.declare_parameter('camera_topic', 'camera/image_raw')
        self.declare_parameter('tracking_enabled', False)
        self.declare_parameter('max_linear_speed', 0.1)
        self.declare_parameter('max_angular_speed', 0.5)
        self.declare_parameter('target_distance', 1.0)  # meters (estimated)
        
        self.tracking_enabled = self.get_parameter('tracking_enabled').value
        self.max_linear = self.get_parameter('max_linear_speed').value
        self.max_angular = self.get_parameter('max_angular_speed').value
        self.target_distance = self.get_parameter('target_distance').value
        
        # CV Bridge
        self.bridge = CvBridge()
        
        # Tracker
        self.tracker = PersonTracker()
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.status_pub = self.create_publisher(String, 'tracking/status', 10)
        self.debug_pub = self.create_publisher(Image, 'tracking/debug', 10)
        
        # Subscribers
        self.camera_sub = self.create_subscription(
            Image,
            self.get_parameter('camera_topic').value,
            self.camera_callback,
            10
        )
        self.command_sub = self.create_subscription(
            String,
            'tracking/command',
            self.command_callback,
            10
        )
        
        # Timer for control loop
        self.timer = self.create_timer(0.1, self.control_loop)
        
        self.get_logger().info('Person tracking node started')
    
    def command_callback(self, msg):
        """Handle tracking commands."""
        cmd = msg.data.lower()
        
        if cmd in ['start', 'enable', 'zapni']:
            self.tracking_enabled = True
            self.get_logger().info('Person tracking ENABLED')
        elif cmd in ['stop', 'disable', 'vypni']:
            self.tracking_enabled = False
            self.get_logger().info('Person tracking DISABLED')
            # Stop robot
            self.cmd_vel_pub.publish(Twist())
        elif cmd in ['toggle', 'přepni']:
            self.tracking_enabled = not self.tracking_enabled
            self.get_logger().info(f"Person tracking: {'ON' if self.tracking_enabled else 'OFF'}")
    
    def camera_callback(self, msg):
        """Process camera frame."""
        if not self.get_parameter('use_camera').value:
            return
        
        try:
            # Convert to OpenCV
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            
            # Detect persons
            detections = self.tracker.detect(frame)
            
            # Update tracking
            tracked = self.tracker.update_tracking(detections)
            
            # Draw debug visualization
            debug_frame = self.tracker.draw_detections(frame.copy(), detections, tracked)
            
            # Add status text
            status = "TRACKING" if tracked else "SEARCHING"
            cv2.putText(debug_frame, status, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0) if tracked else (0, 0, 255), 2)
            
            # Publish debug image
            debug_msg = self.bridge.cv2_to_imgmsg(debug_frame, 'bgr8')
            self.debug_pub.publish(debug_msg)
            
            # Publish status
            status_msg = String()
            if tracked:
                x, y, w, h = tracked
                status_msg.data = f"tracking:{x:.2f},{y:.2f},{w:.2f},{h:.2f}"
            else:
                status_msg.data = "lost"
            self.status_pub.publish(status_msg)
            
        except Exception as e:
            self.get_logger().error(f'Error processing frame: {e}')
    
    def control_loop(self):
        """Control loop for following tracked person."""
        if not self.tracking_enabled:
            return
        
        error = self.tracker.get_tracking_error()
        
        if error is None:
            # No person tracked - stop or search
            self.cmd_vel_pub.publish(Twist())
            return
        
        error_x, error_y, distance = error
        
        # Calculate control commands
        twist = Twist()
        
        # Angular control (pan to keep person centered)
        # error_x is -0.5 to 0.5, positive means person is right of center
        twist.angular.z = -error_x * self.max_angular * 2.0
        
        # Clamp angular velocity
        twist.angular.z = max(-self.max_angular, min(self.max_angular, twist.angular.z))
        
        # Linear control (move to maintain distance)
        # If person is too far (small in frame), move forward
        # If person is too close (large in frame), move backward
        distance_error = distance - self.target_distance
        
        # Only move if distance error is significant
        if abs(distance_error) > 0.2:
            twist.linear.x = distance_error * self.max_linear * 0.5
            twist.linear.x = max(-self.max_linear, min(self.max_linear, twist.linear.x))
        
        # Publish command
        self.cmd_vel_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = PersonTrackingNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop robot
        node.cmd_vel_pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
