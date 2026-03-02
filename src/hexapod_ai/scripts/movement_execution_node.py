#!/usr/bin/env python3
"""ROS2 node for executing AI-generated movement sequences."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from hexapod_ai.movement_generator import (
    MovementGenerator, MovementType, AIMovementInterface, MovementSegment
)
import json


class MovementExecutionNode(Node):
    """Node to execute complex movement sequences."""
    
    def __init__(self):
        super().__init__('movement_execution_node')
        
        # Parameters
        self.declare_parameter('language', 'en')
        
        # Movement handling
        self.generator = MovementGenerator()
        self.ai_interface = AIMovementInterface()
        self.current_sequence: list[MovementSegment] = []
        self.sequence_start_time = None
        self.is_executing = False
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.gait_pub = self.create_publisher(String, 'gait_type', 10)
        self.status_pub = self.create_publisher(String, 'movement/status', 10)
        
        # Subscribers
        self.movement_sub = self.create_subscription(
            String,
            'ai/movement_command',
            self.movement_command_callback,
            10
        )
        
        # Timer for execution
        self.timer = self.create_timer(0.05, self.execution_timer)  # 20Hz
        
        self.get_logger().info('Movement execution node started')
    
    def movement_command_callback(self, msg):
        """Receive movement command."""
        try:
            data = json.loads(msg.data)
            
            # Check if it's a predefined movement type
            if 'movement_type' in data:
                movement_type = MovementType(data['movement_type'])
                params = data.get('params', {})
                segments = self.generator.generate_movement(movement_type, params)
            
            # Check if it's a natural language description
            elif 'description' in data:
                language = self.get_parameter('language').value
                segments = self.ai_interface.generate_from_description(
                    data['description'], language
                )
            
            # Check if it's a raw sequence
            elif 'sequence' in data:
                segments = MovementGenerator.from_json(json.dumps(data['sequence']))
            
            else:
                self.get_logger().warn('Unknown movement command format')
                return
            
            if segments:
                self.start_sequence(segments)
                
        except Exception as e:
            self.get_logger().error(f'Failed to parse movement command: {e}')
    
    def start_sequence(self, segments: list[MovementSegment]):
        """Start executing a movement sequence."""
        self.current_sequence = segments
        self.sequence_start_time = self.get_clock().now()
        self.is_executing = True
        
        total_duration = sum(s.duration for s in segments)
        self.get_logger().info(f'Starting movement sequence: {len(segments)} segments, {total_duration:.1f}s')
        
        # Publish status
        status = {
            'status': 'started',
            'segments': len(segments),
            'duration': total_duration
        }
        self.status_pub.publish(String(data=json.dumps(status)))
    
    def execution_timer(self):
        """Timer callback for movement execution."""
        if not self.is_executing or not self.current_sequence:
            return
        
        # Calculate elapsed time
        now = self.get_clock().now()
        elapsed = (now - self.sequence_start_time).nanoseconds / 1e9
        
        # Get current segment
        current = self.generator.get_current_command(elapsed)
        
        if current is None:
            # Sequence complete
            self.is_executing = False
            self.cmd_vel_pub.publish(Twist())  # Stop
            self.get_logger().info('Movement sequence complete')
            
            status = {'status': 'complete'}
            self.status_pub.publish(String(data=json.dumps(status)))
            return
        
        # Publish command
        twist = Twist()
        twist.linear.x = current.linear_x
        twist.linear.y = current.linear_y
        twist.angular.z = current.angular_z
        self.cmd_vel_pub.publish(twist)
        
        # Change gait if specified
        if current.gait_type:
            self.gait_pub.publish(String(data=current.gait_type))


def main(args=None):
    rclpy.init(args=args)
    node = MovementExecutionNode()
    
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
