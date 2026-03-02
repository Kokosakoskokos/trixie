#!/usr/bin/env python3
"""ROS2 node for Czech command processing."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from hexapod_voice.czech_parser import CzechCommandParser, CzechMovementGenerator


class CzechCommandNode(Node):
    """Node to process Czech text commands."""
    
    def __init__(self):
        super().__init__('czech_command_node')
        
        # Parameters
        self.declare_parameter('enable_responses', True)
        
        # Parser
        self.parser = CzechCommandParser()
        self.movement_gen = CzechMovementGenerator()
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.gait_pub = self.create_publisher(String, 'gait_type', 10)
        self.ai_pub = self.create_publisher(String, 'ai/command', 10)
        self.response_pub = self.create_publisher(String, 'voice/response', 10)
        
        # Subscribers
        self.command_sub = self.create_subscription(
            String,
            'voice/czech_command',
            self.command_callback,
            10
        )
        
        self.get_logger().info('Czech command node started')
        self.get_logger().info('Připraven na české příkazy!')
    
    def command_callback(self, msg):
        """Process Czech command."""
        text = msg.data
        self.get_logger().info(f'Přijat příkaz: {text}')
        
        # Parse command
        result = self.parser.parse_command(text)
        
        if result is None:
            self.get_logger().warn(f'Nerozuměl jsem: {text}')
            response = self.parser.generate_response({}, success=False)
            self.publish_response(response)
            return
        
        # Execute command
        success = self.execute_command(result)
        
        # Generate response
        if self.get_parameter('enable_responses').value:
            response = self.parser.generate_response(result, success)
            self.publish_response(response)
    
    def execute_command(self, command: dict) -> bool:
        """Execute parsed command."""
        cmd_type = command.get('type')
        
        try:
            if cmd_type == 'movement':
                params = command.get('params', {})
                twist = Twist()
                twist.linear.x = params.get('linear_x', 0.0)
                twist.linear.y = params.get('linear_y', 0.0)
                twist.angular.z = params.get('angular_z', 0.0)
                self.cmd_vel_pub.publish(twist)
                return True
            
            elif cmd_type == 'gait':
                gait_type = command.get('gait_type', 'tripod')
                msg = String()
                msg.data = gait_type
                self.gait_pub.publish(msg)
                return True
            
            elif cmd_type == 'ai':
                action = command.get('action', 'disable')
                msg = String()
                msg.data = action
                self.ai_pub.publish(msg)
                return True
            
            elif cmd_type == 'status':
                # Status queries are handled by response generation
                return True
            
            elif cmd_type == 'greeting':
                # Just respond, no action needed
                return True
            
            return False
            
        except Exception as e:
            self.get_logger().error(f'Chyba při vykonávání příkazu: {e}')
            return False
    
    def publish_response(self, text: str):
        """Publish voice response."""
        msg = String()
        msg.data = text
        self.response_pub.publish(msg)
        self.get_logger().info(f'Odpověď: {text}')


def main(args=None):
    rclpy.init(args=args)
    node = CzechCommandNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
