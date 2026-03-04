"""PCA9685 servo driver for hexapod legs."""

import smbus2
import time
import math


class PCA9685:
    """PCA9685 PWM driver over I2C."""
    
    # Registers
    MODE1 = 0x00
    MODE2 = 0x01
    PRESCALE = 0xFE
    LED0_ON_L = 0x06
    
    def __init__(self, bus_num=1, address=0x40):
        self.bus = smbus2.SMBus(bus_num)
        self.address = address
        self._init_device()
    
    def _init_device(self):
        """Initialize the PCA9685."""
        # Reset
        self.bus.write_byte_data(self.address, self.MODE1, 0x00)
        time.sleep(0.005)
        
        # Set frequency to 50Hz (standard for servos)
        self.set_pwm_freq(50)
        
        # Auto-increment enabled
        mode1 = self.bus.read_byte_data(self.address, self.MODE1)
        mode1 = mode1 | 0x20
        self.bus.write_byte_data(self.address, self.MODE1, mode1)
    
    def set_pwm_freq(self, freq_hz):
        """Set PWM frequency."""
        prescaleval = 25000000.0 / (4096 * freq_hz) - 1
        prescale = int(math.floor(prescaleval + 0.5))
        
        old_mode = self.bus.read_byte_data(self.address, self.MODE1)
        new_mode = (old_mode & 0x7F) | 0x10
        self.bus.write_byte_data(self.address, self.MODE1, new_mode)
        self.bus.write_byte_data(self.address, self.PRESCALE, prescale)
        self.bus.write_byte_data(self.address, self.MODE1, old_mode)
        time.sleep(0.005)
        self.bus.write_byte_data(self.address, self.MODE1, old_mode | 0x80)
    
    def set_pwm(self, channel, on, off):
        """Set PWM for a channel."""
        reg = self.LED0_ON_L + 4 * channel
        self.bus.write_byte_data(self.address, reg, on & 0xFF)
        self.bus.write_byte_data(self.address, reg + 1, on >> 8)
        self.bus.write_byte_data(self.address, reg + 2, off & 0xFF)
        self.bus.write_byte_data(self.address, reg + 3, off >> 8)
    
    def set_servo_angle(self, channel, angle_deg, min_pulse=500, max_pulse=2500):
        """Set servo angle in degrees (0-180 typical for MG995)."""
        # MG995: 500us = 0deg, 2500us = 180deg
        angle_deg = max(0, min(180, angle_deg))
        pulse_us = min_pulse + (angle_deg / 180.0) * (max_pulse - min_pulse)
        
        # Convert to PCA9685 counts (50Hz = 20ms period, 4096 counts)
        # 20ms = 20000us
        count = int((pulse_us / 20000.0) * 4096)
        self.set_pwm(channel, 0, count)
    
    def set_neutral(self, channel):
        """Set servo to neutral position (90 degrees)."""
        self.set_servo_angle(channel, 90)
    
    def set_all_neutral(self, channels):
        """Set all servos to neutral."""
        for ch in channels:
            self.set_neutral(ch)
            time.sleep(0.01)


class HexapodServos:
    """Manager for all 18 hexapod servos across 2 PCA9685 boards."""
    
    # Servo mapping: leg_id -> [coxa, femur, tibia] channels
    # Board 1 (0x40): Legs 0, 1, 2 (Left side)
    # Board 2 (0x41): Legs 3, 4, 5 (Right side)
    SERVO_MAP = {
        0: {'coxa': 0, 'femur': 1, 'tibia': 2,   'board': 0x40},
        1: {'coxa': 3, 'femur': 4, 'tibia': 5,   'board': 0x40},
        2: {'coxa': 6, 'femur': 7, 'tibia': 8,   'board': 0x40},
        3: {'coxa': 0, 'femur': 1, 'tibia': 2,   'board': 0x41},
        4: {'coxa': 3, 'femur': 4, 'tibia': 5,   'board': 0x41},
        5: {'coxa': 6, 'femur': 7, 'tibia': 8,   'board': 0x41},
    }
    
    # Joint direction multipliers (flip if servo is mounted reversed)
    # Format: leg_id -> {'coxa': 1/-1, 'femur': 1/-1, 'tibia': 1/-1}
    JOINT_DIRECTIONS = {
        0: {'coxa': 1, 'femur': -1, 'tibia': 1},
        1: {'coxa': 1, 'femur': -1, 'tibia': 1},
        2: {'coxa': 1, 'femur': -1, 'tibia': 1},
        3: {'coxa': -1, 'femur': 1, 'tibia': -1},
        4: {'coxa': -1, 'femur': 1, 'tibia': -1},
        5: {'coxa': -1, 'femur': 1, 'tibia': -1},
    }
    
    # Offset angles for calibration (degrees)
    JOINT_OFFSETS = {
        0: {'coxa': 0, 'femur': 0, 'tibia': 0},
        1: {'coxa': 0, 'femur': 0, 'tibia': 0},
        2: {'coxa': 0, 'femur': 0, 'tibia': 0},
        3: {'coxa': 0, 'femur': 0, 'tibia': 0},
        4: {'coxa': 0, 'femur': 0, 'tibia': 0},
        5: {'coxa': 0, 'femur': 0, 'tibia': 0},
    }

    # Joint limits (radians) for each leg/joint: min, max
    # Tune per mechanical limits to avoid binding.
    JOINT_LIMITS = {
        0: {'coxa': (-1.57, 1.57), 'femur': (-1.57, 1.57), 'tibia': (-2.0, 0.5)},
        1: {'coxa': (-1.57, 1.57), 'femur': (-1.57, 1.57), 'tibia': (-2.0, 0.5)},
        2: {'coxa': (-1.57, 1.57), 'femur': (-1.57, 1.57), 'tibia': (-2.0, 0.5)},
        3: {'coxa': (-1.57, 1.57), 'femur': (-1.57, 1.57), 'tibia': (-2.0, 0.5)},
        4: {'coxa': (-1.57, 1.57), 'femur': (-1.57, 1.57), 'tibia': (-2.0, 0.5)},
        5: {'coxa': (-1.57, 1.57), 'femur': (-1.57, 1.57), 'tibia': (-2.0, 0.5)},
    }
    
    def __init__(self, bus_num=1):
        self.pca40 = PCA9685(bus_num, 0x40)
        self.pca41 = PCA9685(bus_num, 0x41)
        self.boards = {0x40: self.pca40, 0x41: self.pca41}
    
    def angle_to_servo(self, leg_id, joint, angle_rad):
        """Convert joint angle (radians) to servo angle (degrees)."""
        # Clamp to joint limits
        joint_min, joint_max = self.JOINT_LIMITS[leg_id][joint]
        angle_rad = max(joint_min, min(joint_max, angle_rad))

        # Convert rad to deg
        angle_deg = math.degrees(angle_rad)
        
        # Apply direction multiplier
        direction = self.JOINT_DIRECTIONS[leg_id][joint]
        angle_deg *= direction
        
        # Apply offset
        offset = self.JOINT_OFFSETS[leg_id][joint]
        angle_deg += offset
        
        # Convert to 0-180 servo range (90 is neutral)
        # URDF uses radians centered at 0, servos use 0-180 centered at 90
        servo_angle = angle_deg + 90
        
        return max(0, min(180, servo_angle))
    
    def set_joint_angle(self, leg_id, joint, angle_rad):
        """Set a single joint angle (radians from URDF)."""
        servo_angle = self.angle_to_servo(leg_id, joint, angle_rad)
        servo_info = self.SERVO_MAP[leg_id]
        channel = servo_info[joint]
        board_addr = servo_info['board']
        
        self.boards[board_addr].set_servo_angle(channel, servo_angle)
    
    def set_leg_angles(self, leg_id, coxa_rad, femur_rad, tibia_rad):
        """Set all three joints for a leg."""
        self.set_joint_angle(leg_id, 'coxa', coxa_rad)
        self.set_joint_angle(leg_id, 'femur', femur_rad)
        self.set_joint_angle(leg_id, 'tibia', tibia_rad)
    
    def set_all_neutral(self):
        """Set all servos to neutral position."""
        for board in self.boards.values():
            for ch in range(9):
                board.set_neutral(ch)
                time.sleep(0.005)
    
    def disable_all(self):
        """Disable all PWM outputs (servos go limp)."""
        for board in self.boards.values():
            for ch in range(16):
                board.set_pwm(ch, 0, 0)
