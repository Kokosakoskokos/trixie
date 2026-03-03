"""Gait generation for hexapod walking."""

import math


class TripodGait:
    """Tripod gait - alternating between two tripods.
    
    Legs 0, 2, 4 move together (Tripod A)
    Legs 1, 3, 5 move together (Tripod B)
    """
    
    def __init__(self, step_height=0.03, step_length=0.06, cycle_time=0.8):
        self.step_height = step_height
        self.step_length = step_length
        self.cycle_time = cycle_time
        
        # Tripod groups
        self.tripod_a = [0, 2, 4]
        self.tripod_b = [1, 3, 5]
        
        # Stance positions (default foot positions relative to body)
        self.stance_positions = [
            (0.12, 0.08, -0.12),   # 0: Front Left
            (0.0, 0.10, -0.12),    # 1: Middle Left
            (-0.12, 0.08, -0.12),  # 2: Rear Left
            (-0.12, -0.08, -0.12), # 3: Rear Right
            (0.0, -0.10, -0.12),   # 4: Middle Right
            (0.12, -0.08, -0.12),  # 5: Front Right
        ]
    
    def generate_foot_trajectory(self, phase, direction=0.0):
        """Generate foot trajectory for one leg.
        
        Args:
            phase: 0.0 to 1.0 (0=start of swing, 0.5=start of stance)
            direction: Movement direction in radians (0=forward, pi/2=left, etc.)
        
        Returns:
            tuple: (x_offset, y_offset, z_offset) relative to stance position
        """
        # Normalize phase
        phase = phase % 1.0
        
        # Swing phase: 0.0 to 0.5
        # Stance phase: 0.5 to 1.0
        
        if phase < 0.5:
            # Swing phase - leg moving forward
            swing_phase = phase / 0.5  # 0 to 1
            
            # X/Y: move from -step_length/2 to +step_length/2
            linear_pos = -self.step_length/2 + swing_phase * self.step_length
            
            # Z: parabolic lift
            z_lift = self.step_height * math.sin(swing_phase * math.pi)
            
            x_offset = linear_pos * math.cos(direction)
            y_offset = linear_pos * math.sin(direction)
            z_offset = z_lift
            
        else:
            # Stance phase - leg on ground, body moving forward
            stance_phase = (phase - 0.5) / 0.5  # 0 to 1
            
            # Move from +step_length/2 to -step_length/2 (pushing body forward)
            linear_pos = self.step_length/2 - stance_phase * self.step_length
            
            x_offset = linear_pos * math.cos(direction)
            y_offset = linear_pos * math.sin(direction)
            z_offset = 0.0
        
        return (x_offset, y_offset, z_offset)
    
    def get_foot_positions(self, time, direction=0.0, speed=1.0):
        """Get foot positions at given time.
        
        Args:
            time: Current time in seconds
            direction: Movement direction (radians, 0=forward)
            speed: Speed multiplier (1.0 = normal)
        
        Returns:
            List of 6 foot positions [(x,y,z), ...] in body frame
        """
        # Adjust cycle time by speed
        cycle_time = self.cycle_time / max(0.1, speed)
        
        # Current phase in cycle
        cycle_phase = (time % cycle_time) / cycle_time
        
        positions = []
        
        for leg_id in range(6):
            # Tripod A and B are 180 degrees out of phase
            if leg_id in self.tripod_a:
                leg_phase = cycle_phase
            else:
                leg_phase = (cycle_phase + 0.5) % 1.0
            
            # Get trajectory offset
            offset = self.generate_foot_trajectory(leg_phase, direction)
            
            # Add to stance position
            stance = self.stance_positions[leg_id]
            pos = (
                stance[0] + offset[0],
                stance[1] + offset[1],
                stance[2] + offset[2]
            )
            positions.append(pos)
        
        return positions
    
    def is_stable(self, time):
        """Check if the robot is in a statically stable configuration.
        
        Args:
            time: Current time
        
        Returns:
            bool: True if at least 3 legs are on the ground
        """
        cycle_phase = (time % self.cycle_time) / self.cycle_time
        
        # Tripod A is on ground during stance (phase 0.5 to 1.0)
        # Tripod B is on ground during stance (phase 0.0 to 0.5)
        tripod_a_ground = cycle_phase >= 0.5
        tripod_b_ground = cycle_phase < 0.5
        
        # During transitions, both might be on ground
        return True  # Tripod gait is always statically stable


class WaveGait:
    """Wave gait - legs move one at a time in a wave pattern.
    More stable but slower than tripod gait.
    """
    
    def __init__(self, step_height=0.03, step_length=0.04, cycle_time=1.2):
        self.step_height = step_height
        self.step_length = step_length
        self.cycle_time = cycle_time
        
        # Leg sequence: 0, 4, 2, 3, 1, 5 (optimal for stability)
        self.leg_sequence = [0, 4, 2, 3, 1, 5]
        
        self.stance_positions = [
            (0.12, 0.08, -0.12),
            (0.0, 0.10, -0.12),
            (-0.12, 0.08, -0.12),
            (-0.12, -0.08, -0.12),
            (0.0, -0.10, -0.12),
            (0.12, -0.08, -0.12),
        ]
    
    def get_foot_positions(self, time, direction=0.0, speed=1.0):
        """Get foot positions at given time."""
        cycle_time = self.cycle_time / max(0.1, speed)
        cycle_phase = (time % cycle_time) / cycle_time
        
        positions = []
        
        for leg_id in range(6):
            # Find position in sequence
            seq_pos = self.leg_sequence.index(leg_id)
            
            # Each leg has 1/6 of cycle for swing, 5/6 for stance
            leg_phase = (cycle_phase + seq_pos / 6.0) % 1.0
            
            if leg_phase < 1/6.0:
                # Swing phase
                swing_prog = leg_phase * 6.0  # 0 to 1
                
                linear_pos = -self.step_length/2 + swing_prog * self.step_length
                z_lift = self.step_height * math.sin(swing_prog * math.pi)
                
                offset = (
                    linear_pos * math.cos(direction),
                    linear_pos * math.sin(direction),
                    z_lift
                )
            else:
                # Stance phase
                stance_prog = (leg_phase - 1/6.0) * 6/5.0  # 0 to 1
                
                linear_pos = self.step_length/2 - stance_prog * self.step_length
                
                offset = (
                    linear_pos * math.cos(direction),
                    linear_pos * math.sin(direction),
                    0.0
                )
            
            stance = self.stance_positions[leg_id]
            pos = (
                stance[0] + offset[0],
                stance[1] + offset[1],
                stance[2] + offset[2]
            )
            positions.append(pos)
        
        return positions


class GaitController:
    """High-level gait controller that can switch between gaits."""
    
    GAIT_TYPES = {
        'tripod': TripodGait,
        'wave': WaveGait,
    }
    
    def __init__(self, gait_type='tripod'):
        self.current_gait = self.GAIT_TYPES[gait_type]()
        self.gait_type = gait_type
        
        # Movement commands
        self.linear_velocity = 0.0  # m/s
        self.angular_velocity = 0.0  # rad/s
        self.direction = 0.0  # radians
    
    def set_gait(self, gait_type):
        """Switch gait type."""
        if gait_type in self.GAIT_TYPES:
            self.current_gait = self.GAIT_TYPES[gait_type]()
            self.gait_type = gait_type
    
    def set_velocity(self, linear_x=0.0, linear_y=0.0, angular_z=0.0):
        """Set desired velocity.
        
        Args:
            linear_x: Forward/backward velocity (m/s)
            linear_y: Left/right velocity (m/s)
            angular_z: Rotation rate (rad/s)
        """
        # Calculate direction and speed from linear components
        self.linear_velocity = math.sqrt(linear_x**2 + linear_y**2)
        self.direction = math.atan2(linear_y, linear_x)
        self.angular_velocity = angular_z
    
    def get_foot_positions(self, time):
        """Get foot positions for current time."""
        # Speed factor based on velocity
        speed = min(2.0, self.linear_velocity / 0.05)  # Normalize
        
        return self.current_gait.get_foot_positions(
            time, self.direction, speed
        )
    
    def get_body_rotation(self, time, dt):
        """Get body rotation for turning."""
        return self.angular_velocity * dt
