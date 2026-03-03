"""Body pose controller for hexapod stability."""

import math


class BodyPoseController:
    """Control body orientation for stability and terrain adaptation."""
    
    def __init__(self):
        # Body orientation (roll, pitch, yaw in radians)
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        
        # Body position offset
        self.x_offset = 0.0
        self.y_offset = 0.0
        self.z_offset = 0.0
        
        # Target height
        self.target_height = 0.12
        
        # Stability compensation
        self.com_pitch_factor = 0.1  # Compensate acceleration with pitch
        self.com_roll_factor = 0.1   # Compensate lateral with roll
    
    def update_from_imu(self, accel_x, accel_y, accel_z):
        """Update body pose based on IMU readings for stability.
        
        Args:
            accel_x: Forward acceleration (m/s^2)
            accel_y: Lateral acceleration (m/s^2)
            accel_z: Vertical acceleration (m/s^2)
        """
        # Calculate pitch from forward acceleration
        # When accelerating forward, pitch up slightly to maintain stability
        target_pitch = -accel_x * self.com_pitch_factor
        
        # Calculate roll from lateral acceleration
        target_roll = accel_y * self.com_roll_factor
        
        # Smooth transition
        alpha = 0.1
        self.pitch = self.pitch * (1 - alpha) + target_pitch * alpha
        self.roll = self.roll * (1 - alpha) + target_roll * alpha
    
    def set_target_height(self, height):
        """Set target body height."""
        self.target_height = max(0.08, min(0.15, height))
    
    def transform_foot_position(self, foot_pos, leg_mount_pos):
        """Transform foot position from body frame to leg frame.
        
        Args:
            foot_pos: (x, y, z) foot position in body frame
            leg_mount_pos: (x, y, z) leg mounting position on body
        
        Returns:
            Transformed foot position accounting for body pose
        """
        # Relative position from leg mount to foot
        dx = foot_pos[0] - leg_mount_pos[0]
        dy = foot_pos[1] - leg_mount_pos[1]
        dz = foot_pos[2] - leg_mount_pos[2]
        
        # Apply body rotation (roll, pitch, yaw)
        # Rotation matrices applied in order: yaw -> pitch -> roll
        
        # Yaw rotation (around Z)
        cos_yaw = math.cos(self.yaw)
        sin_yaw = math.sin(self.yaw)
        x1 = dx * cos_yaw - dy * sin_yaw
        y1 = dx * sin_yaw + dy * cos_yaw
        z1 = dz
        
        # Pitch rotation (around Y)
        cos_pitch = math.cos(self.pitch)
        sin_pitch = math.sin(self.pitch)
        x2 = x1 * cos_pitch + z1 * sin_pitch
        y2 = y1
        z2 = -x1 * sin_pitch + z1 * cos_pitch
        
        # Roll rotation (around X)
        cos_roll = math.cos(self.roll)
        sin_roll = math.sin(self.roll)
        x3 = x2
        y3 = y2 * cos_roll - z2 * sin_roll
        z3 = y2 * sin_roll + z2 * cos_roll
        
        # Add body offset
        return (
            x3 + self.x_offset,
            y3 + self.y_offset,
            z3 + self.z_offset
        )
    
    def get_stance_foot_positions(self, base_stance_positions):
        """Get foot positions adjusted for current body pose.
        
        Args:
            base_stance_positions: List of 6 (x,y,z) tuples
        
        Returns:
            Adjusted foot positions
        """
        # Leg mount positions from URDF
        leg_mounts = [
            (0.067, 0.072, 0),   # 0: Front Left
            (0.0,   0.072, 0),   # 1: Middle Left
            (-0.067, 0.072, 0),  # 2: Rear Left
            (-0.067, -0.072, 0), # 3: Rear Right
            (0.0,   -0.072, 0),  # 4: Middle Right
            (0.067, -0.072, 0),  # 5: Front Right
        ]
        
        adjusted = []
        for i, foot_pos in enumerate(base_stance_positions):
            new_pos = self.transform_foot_position(foot_pos, leg_mounts[i])
            adjusted.append(new_pos)
        
        return adjusted
    
    def compensate_for_rotation(self, angular_velocity, foot_positions, phase):
        """Compensate foot positions for body rotation during turning.
        
        Args:
            angular_velocity: Rotation rate (rad/s)
            foot_positions: Current foot positions
            phase: Gait phase (0-1)
        
        Returns:
            Compensated foot positions
        """
        if abs(angular_velocity) < 0.1:
            return foot_positions
        
        compensated = []
        for i, pos in enumerate(foot_positions):
            # Add tangential offset based on leg position and rotation
            x, y, z = pos
            
            # Distance from center
            r = math.sqrt(x**2 + y**2)
            
            # Tangential displacement for rotation
            # Outer legs need to move more during rotation
            tangential_offset = angular_velocity * r * 0.05
            
            # Apply offset perpendicular to radius
            angle = math.atan2(y, x)
            new_x = x - tangential_offset * math.sin(angle)
            new_y = y + tangential_offset * math.cos(angle)
            
            compensated.append((new_x, new_y, z))
        
        return compensated
