#!/usr/bin/env python3
"""ROS2 node for AI control via OpenRouter."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from hexapod_ai.openrouter_client import HexapodAI
import json
import os


class AIControllerNode(Node):
    """Node to control hexapod using AI via OpenRouter."""
    
    def __init__(self):
        super().__init__('ai_controller_node')
        
        # Parameters
        self.declare_parameter('api_key', '')
        self.declare_parameter('model', 'anthropic/claude-3.5-sonnet')
        self.declare_parameter('decision_rate', 0.5)  # Hz (every 2 seconds)
        self.declare_parameter('enabled', True)
        self.declare_parameter('safety_stop_distance', 0.3)  # meters
        self.declare_parameter('language', 'en')  # 'en' or 'cz'
        
        # Get API key from parameter or environment
        api_key = self.get_parameter('api_key').value
        if not api_key:
            api_key = os.environ.get('OPENROUTER_API_KEY', '')
        
        if not api_key:
            self.get_logger().error(
                'No OpenRouter API key provided. Set via parameter or OPENROUTER_API_KEY env var.'
            )
        
        model = self.get_parameter('model').value
        language = self.get_parameter('language').value
        self.ai = HexapodAI(api_key, model, language) if api_key else None
        
        self.enabled = self.get_parameter('enabled').value
        self.safety_stop_distance = self.get_parameter('safety_stop_distance').value
        
        # Latest sensor data
        self.latest_sensor_data = {}
        
        # Subscribers
        self.sensor_sub = self.create_subscription(
            String, 'ai/sensor_data', self.sensor_callback, 10
        )
        self.command_sub = self.create_subscription(
            String, 'ai/command', self.command_callback, 10
        )
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.gait_pub = self.create_publisher(String, 'gait_type', 10)
        self.decision_pub = self.create_publisher(String, 'ai/decision', 10)
        
        # Timer for AI decisions
        rate = self.get_parameter('decision_rate').value
        self.timer = self.create_timer(1.0 / rate, self.timer_callback)
        
        self.get_logger().info(f'AI controller started (model: {model})')
    
    def sensor_callback(self, msg):
        """Receive aggregated sensor data."""
        try:
            self.latest_sensor_data = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warn('Failed to parse sensor data')
    
    def command_callback(self, msg):
        """Receive direct AI commands."""
        command = msg.data.lower().strip()
        
        # User-friendly command aliases
        enable_commands = ['start', 'on', 'autopilot on', 'auto on', 'begin']
        disable_commands = ['stop', 'off', 'autopilot off', 'auto off', 'pause', 'manual']
        
        if command in enable_commands:
            self.enabled = True
            self.get_logger().info('AI autopilot ENABLED - Robot will make its own decisions')
        elif command in disable_commands:
            self.enabled = False
            self.get_logger().info('MANUAL mode - You are in control')
            # Stop the robot for safety
            self.publish_velocity(0.0, 0.0, 0.0)
        elif command.startswith('chat:') or command.startswith('ask:'):
            # Handle chat message
            chat_msg = command[5:].strip() if ':' in command else command
            response = self.ai.chat(chat_msg) if self.ai else None
            if response:
                self.get_logger().info(f'AI: {response}')
        else:
            self.get_logger().warn(f'Unknown command: {command}. Try: start/stop/autopilot on/autopilot off')
    
    def timer_callback(self):
        """Make AI decision and publish command."""
        if not self.enabled or not self.ai:
            return
        
        if not self.latest_sensor_data:
            self.get_logger().warn('No sensor data available')
            return
        
        # Safety check - emergency stop if obstacle too close
        us_data = self.latest_sensor_data.get('ultrasonic', {})
        front_dist = us_data.get('front', float('inf'))
        
        if front_dist < self.safety_stop_distance:
            self.get_logger().warn(f'Obstacle detected at {front_dist:.2f}m - emergency stop')
            self.publish_velocity(0.0, 0.0, 0.0)
            return
        
        # Get AI decision
        decision = self.ai.decide_action(self.latest_sensor_data)
        
        if decision:
            # Publish decision for logging
            decision_msg = String()
            decision_msg.data = json.dumps(decision)
            self.decision_pub.publish(decision_msg)
            
            # Log reasoning
            reasoning = decision.get('reasoning', 'No reasoning provided')
            self.get_logger().info(f'AI decision: {reasoning}')
            
            # Execute action
            action = decision.get('action', 'stop')
            
            if action == 'move':
                params = decision.get('params', {})
                self.publish_velocity(
                    params.get('linear_x', 0.0),
                    params.get('linear_y', 0.0),
                    params.get('angular_z', 0.0)
                )
            elif action == 'turn':
                params = decision.get('params', {})
                self.publish_velocity(0.0, 0.0, params.get('angular_z', 0.5))
            elif action == 'stop':
                self.publish_velocity(0.0, 0.0, 0.0)
            elif action == 'change_gait':
                gait_type = decision.get('gait_type', 'tripod')
                gait_msg = String()
                gait_msg.data = gait_type
                self.gait_pub.publish(gait_msg)
                self.get_logger().info(f'Changed gait to {gait_type}')
    
    def publish_velocity(self, linear_x: float, linear_y: float, angular_z: float):
        """Publish velocity command."""
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.linear.y = float(linear_y)
        msg.angular.z = float(angular_z)
        self.cmd_vel_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = AIControllerNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop robot on shutdown
        node.publish_velocity(0.0, 0.0, 0.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
