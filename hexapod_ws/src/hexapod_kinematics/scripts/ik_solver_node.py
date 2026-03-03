#!/usr/bin/env python3
"""ROS2 node for inverse kinematics solver."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState, Imu
from geometry_msgs.msg import Point, Pose
from std_msgs.msg import Float64MultiArray
from hexapod_kinematics.leg_ik import HexapodKinematics
from hexapod_kinematics.body_pose import BodyPoseController
import math


class IKSolverNode(Node):
    """Node to solve IK and publish joint states."""
    
    def __init__(self):
        super().__init__('ik_solver_node')
        
        # Parameters
        self.declare_parameter('publish_rate', 50.0)
        self.declare_parameter('body_height', 0.12)
        self.declare_parameter('enable_stability_control', True)
        
        # Kinematics
        self.kinematics = HexapodKinematics()
        self.body_pose = BodyPoseController()
        self.body_pose.set_target_height(self.get_parameter('body_height').value)
        
        self.enable_stability = self.get_parameter('enable_stability_control').value
        
        # Current foot positions (default stance)
        self.foot_positions = self.kinematics.get_stance_positions(
            body_height=self.get_parameter('body_height').value
        )
        
        # Publisher for joint states
        self.joint_pub = self.create_publisher(JointState, 'joint_states', 10)
        
        # Subscribers
        self.foot_sub = self.create_subscription(
            Float64MultiArray,
            'foot_positions',
            self.foot_position_callback,
            10
        )
        
        self.imu_sub = self.create_subscription(
            Imu,
            'imu/data',
            self.imu_callback,
            10
        )
        
        # Timer
        rate = self.get_parameter('publish_rate').value
        self.timer = self.create_timer(1.0 / rate, self.timer_callback)
        
        self.get_logger().info('IK solver node started')
    
    def foot_position_callback(self, msg):
        """Receive new foot positions."""
        if len(msg.data) != 18:
            self.get_logger().warn(f'Expected 18 values, got {len(msg.data)}')
            return
        
        for i in range(6):
            self.foot_positions[i] = (
                msg.data[i*3],
                msg.data[i*3 + 1],
                msg.data[i*3 + 2]
            )
    
    def imu_callback(self, msg):
        """Receive IMU data for stability control."""
        if self.enable_stability:
            self.body_pose.update_from_imu(
                msg.linear_acceleration.x,
                msg.linear_acceleration.y,
                msg.linear_acceleration.z
            )
    
    def timer_callback(self):
        """Solve IK and publish joint states."""
        # Apply body pose transformation for stability
        if self.enable_stability:
            adjusted_positions = self.body_pose.get_stance_foot_positions(self.foot_positions)
        else:
            adjusted_positions = self.foot_positions
        
        # Solve IK for all legs
        angles = self.kinematics.solve_all_legs(adjusted_positions)
        
        # Create joint state message
        joint_msg = JointState()
        joint_msg.header.stamp = self.get_clock().now().to_msg()
        
        for leg_id in range(6):
            leg_angles = angles[leg_id]
            
            if leg_angles is None:
                self.get_logger().warn(f'Leg {leg_id} IK failed')
                continue
            
            coxa, femur, tibia = leg_angles
            
            joint_msg.name.extend([
                f'leg_{leg_id}_coxa_joint',
                f'leg_{leg_id}_femur_joint',
                f'leg_{leg_id}_tibia_joint'
            ])
            joint_msg.position.extend([coxa, femur, tibia])
        
        self.joint_pub.publish(joint_msg)


def main(args=None):
    rclpy.init(args=args)
    node = IKSolverNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
