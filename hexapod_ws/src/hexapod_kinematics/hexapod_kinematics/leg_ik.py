"""Inverse kinematics for hexapod leg."""

import math


class LegKinematics:
    """IK solver for a single hexapod leg.
    
    Leg structure:
    - Coxa: hip joint (rotates around Z)
    - Femur: thigh (rotates around Y)
    - Tibia: shin (rotates around Y)
    
    Coordinate frame (for right-side legs):
    - X: forward
    - Y: outward from body
    - Z: up
    """
    
    def __init__(self, coxa_len=0.035, femur_len=0.065, tibia_len=0.100):
        self.coxa_len = coxa_len
        self.femur_len = femur_len
        self.tibia_len = tibia_len
    
    def solve_ik(self, x, y, z, leg_side='right'):
        """Solve inverse kinematics for leg.
        
        Args:
            x, y, z: Target foot position in leg coordinate frame (meters)
            leg_side: 'left' or 'right' (affects angle signs)
        
        Returns:
            tuple: (coxa_angle, femur_angle, tibia_angle) in radians
                   or None if unreachable
        """
        # Coxa angle (hip rotation around Z)
        coxa_angle = math.atan2(y, x)
        
        # Distance in XY plane from coxa to foot
        L = math.sqrt(x**2 + y**2)
        
        # Distance from femur joint to foot (in the leg plane)
        # Subtract coxa length
        L1 = L - self.coxa_len
        
        # Distance from femur joint to foot (3D)
        d = math.sqrt(L1**2 + z**2)
        
        # Check reachability
        max_reach = self.femur_len + self.tibia_len
        min_reach = abs(self.femur_len - self.tibia_len)
        
        if d > max_reach or d < min_reach:
            return None  # Target unreachable
        
        # Femur-tibia angle using law of cosines
        # cos(phi) = (femur^2 + tibia^2 - d^2) / (2 * femur * tibia)
        cos_phi = (self.femur_len**2 + self.tibia_len**2 - d**2) / \
                  (2 * self.femur_len * self.tibia_len)
        phi = math.acos(max(-1, min(1, cos_phi)))
        
        # Tibia angle (relative to femur)
        tibia_angle = phi - math.pi  # Negative for typical hexapod config
        
        # Femur angle
        # alpha: angle from horizontal to line connecting femur joint to foot
        alpha = math.atan2(-z, L1)  # Negative z because positive z is up
        
        # beta: angle between femur and line to foot
        cos_beta = (self.femur_len**2 + d**2 - self.tibia_len**2) / \
                   (2 * self.femur_len * d)
        beta = math.acos(max(-1, min(1, cos_beta)))
        
        femur_angle = alpha + beta
        
        # Adjust for left/right leg differences
        if leg_side == 'left':
            coxa_angle = -coxa_angle
            femur_angle = -femur_angle
            tibia_angle = -tibia_angle
        
        return (coxa_angle, femur_angle, tibia_angle)
    
    def solve_ik_body_frame(self, foot_x, foot_y, foot_z, leg_id):
        """Solve IK from body-centered frame.
        
        Args:
            foot_x, foot_y, foot_z: Target foot position in body frame
            leg_id: 0-5 (leg identifier)
        
        Returns:
            tuple: (coxa, femur, tibia) angles in radians or None
        """
        # Leg mounting positions and angles (from URDF)
        leg_mounts = [
            {'x': 0.067, 'y': 0.072, 'angle': 0.785},   # 0: Front Left
            {'x': 0.0,   'y': 0.072, 'angle': 1.571},   # 1: Middle Left
            {'x': -0.067, 'y': 0.072, 'angle': 2.356},  # 2: Rear Left
            {'x': -0.067, 'y': -0.072, 'angle': -2.356}, # 3: Rear Right
            {'x': 0.0,   'y': -0.072, 'angle': -1.571},  # 4: Middle Right
            {'x': 0.067, 'y': -0.072, 'angle': -0.785},  # 5: Front Right
        ]
        
        mount = leg_mounts[leg_id]
        side = 'left' if leg_id < 3 else 'right'
        
        # Transform from body frame to leg frame
        dx = foot_x - mount['x']
        dy = foot_y - mount['y']
        
        # Rotate by negative mount angle to align with leg coordinates
        cos_a = math.cos(-mount['angle'])
        sin_a = math.sin(-mount['angle'])
        
        x = dx * cos_a - dy * sin_a
        y = dx * sin_a + dy * cos_a
        z = foot_z
        
        return self.solve_ik(x, y, z, side)


class HexapodKinematics:
    """Kinematics manager for all 6 legs."""
    
    def __init__(self):
        self.leg_ik = LegKinematics()
    
    def solve_all_legs(self, foot_positions):
        """Solve IK for all 6 legs.
        
        Args:
            foot_positions: List of 6 tuples [(x,y,z), ...] in body frame
        
        Returns:
            List of 6 tuples [(coxa, femur, tibia), ...] or None for unreachable
        """
        angles = []
        for leg_id, pos in enumerate(foot_positions):
            result = self.leg_ik.solve_ik_body_frame(
                pos[0], pos[1], pos[2], leg_id
            )
            angles.append(result)
        return angles
    
    def get_stance_positions(self, body_height=0.12, stance_radius=0.12):
        """Get default foot positions for standing stance.
        
        Args:
            body_height: Height of body above ground (m)
            stance_radius: Distance of feet from body center (m)
        
        Returns:
            List of 6 foot positions [(x,y,z), ...]
        """
        # Leg angles around body (in body frame)
        leg_angles = [0.785, 1.571, 2.356, -2.356, -1.571, -0.785]
        
        positions = []
        for angle in leg_angles:
            x = stance_radius * math.cos(angle)
            y = stance_radius * math.sin(angle)
            z = -body_height  # Feet below body
            positions.append((x, y, z))
        
        return positions
