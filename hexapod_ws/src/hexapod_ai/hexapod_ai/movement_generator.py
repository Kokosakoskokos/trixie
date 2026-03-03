"""AI movement generation for hexapod robot."""

import json
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MovementType(Enum):
    """Types of movements."""
    LINEAR = "linear"
    ROTATIONAL = "rotational"
    CIRCULAR = "circular"
    ZIGZAG = "zigzag"
    SPIRAL = "spiral"
    FIGURE_EIGHT = "figure_eight"
    SEARCH_PATTERN = "search_pattern"
    AVOIDANCE = "avoidance"


@dataclass
class MovementSegment:
    """Single movement segment."""
    duration: float  # seconds
    linear_x: float = 0.0
    linear_y: float = 0.0
    angular_z: float = 0.0
    gait_type: Optional[str] = None
    description: str = ""


class MovementGenerator:
    """Generate complex movement sequences."""
    
    def __init__(self):
        self.current_sequence: List[MovementSegment] = []
        self.sequence_index = 0
        self.start_time = 0.0
    
    def generate_movement(
        self,
        movement_type: MovementType,
        params: Dict
    ) -> List[MovementSegment]:
        """Generate movement sequence based on type and parameters.
        
        Args:
            movement_type: Type of movement pattern
            params: Parameters for the movement
        
        Returns:
            List of movement segments
        """
        generators = {
            MovementType.LINEAR: self._generate_linear,
            MovementType.ROTATIONAL: self._generate_rotational,
            MovementType.CIRCULAR: self._generate_circular,
            MovementType.ZIGZAG: self._generate_zigzag,
            MovementType.SPIRAL: self._generate_spiral,
            MovementType.FIGURE_EIGHT: self._generate_figure_eight,
            MovementType.SEARCH_PATTERN: self._generate_search_pattern,
            MovementType.AVOIDANCE: self._generate_avoidance,
        }
        
        generator = generators.get(movement_type)
        if generator:
            return generator(params)
        return []
    
    def _generate_linear(self, params: Dict) -> List[MovementSegment]:
        """Generate linear movement."""
        distance = params.get('distance', 1.0)  # meters
        speed = params.get('speed', 0.1)  # m/s
        direction = params.get('direction', 'forward')  # forward/backward/left/right
        
        duration = abs(distance / speed) if speed != 0 else 1.0
        
        linear_x, linear_y = 0.0, 0.0
        if direction == 'forward':
            linear_x = speed
        elif direction == 'backward':
            linear_x = -speed
        elif direction == 'left':
            linear_y = speed
        elif direction == 'right':
            linear_y = -speed
        
        return [MovementSegment(
            duration=duration,
            linear_x=linear_x,
            linear_y=linear_y,
            description=f"Move {direction} {distance}m at {speed}m/s"
        )]
    
    def _generate_rotational(self, params: Dict) -> List[MovementSegment]:
        """Generate rotational movement."""
        angle = params.get('angle', 90)  # degrees
        speed = params.get('speed', 0.5)  # rad/s
        direction = params.get('direction', 'left')  # left/right
        
        angle_rad = math.radians(angle)
        angular_z = speed if direction == 'left' else -speed
        duration = angle_rad / abs(angular_z)
        
        return [MovementSegment(
            duration=duration,
            angular_z=angular_z,
            description=f"Rotate {direction} {angle}° at {speed}rad/s"
        )]
    
    def _generate_circular(self, params: Dict) -> List[MovementSegment]:
        """Generate circular movement."""
        radius = params.get('radius', 0.5)  # meters
        speed = params.get('speed', 0.1)  # m/s
        direction = params.get('direction', 'clockwise')
        revolutions = params.get('revolutions', 1)
        
        circumference = 2 * math.pi * radius
        duration = (circumference * revolutions) / speed
        
        # For circular motion, combine linear and angular
        angular_speed = speed / radius
        if direction == 'counter_clockwise':
            angular_speed = -angular_speed
        
        return [MovementSegment(
            duration=duration,
            linear_x=speed,
            angular_z=angular_speed,
            gait_type='wave',  # More stable for turning
            description=f"Circle {direction} radius {radius}m, {revolutions} revs"
        )]
    
    def _generate_zigzag(self, params: Dict) -> List[MovementSegment]:
        """Generate zigzag pattern."""
        segment_length = params.get('segment_length', 0.5)
        num_segments = params.get('num_segments', 4)
        speed = params.get('speed', 0.1)
        
        segments = []
        for i in range(num_segments):
            # Forward segment
            segments.append(MovementSegment(
                duration=segment_length / speed,
                linear_x=speed,
                description=f"Zigzag forward segment {i+1}"
            ))
            # Turn
            turn_direction = 1 if i % 2 == 0 else -1
            segments.append(MovementSegment(
                duration=1.0,
                angular_z=turn_direction * 0.5,
                description=f"Zigzag turn {i+1}"
            ))
        
        return segments
    
    def _generate_spiral(self, params: Dict) -> List[MovementSegment]:
        """Generate spiral outward pattern."""
        max_radius = params.get('max_radius', 1.0)
        speed = params.get('speed', 0.08)
        
        segments = []
        num_loops = 3
        
        for i in range(num_loops * 4):  # 4 segments per loop
            progress = (i + 1) / (num_loops * 4)
            current_radius = max_radius * progress
            
            # Move forward with slight turn
            segments.append(MovementSegment(
                duration=0.5,
                linear_x=speed,
                angular_z=0.3,
                description=f"Spiral segment {i+1}, radius {current_radius:.2f}m"
            ))
        
        return segments
    
    def _generate_figure_eight(self, params: Dict) -> List[MovementSegment]:
        """Generate figure-8 pattern."""
        size = params.get('size', 0.5)
        speed = params.get('speed', 0.08)
        
        segments = []
        
        # First loop
        for _ in range(8):
            segments.append(MovementSegment(
                duration=0.5,
                linear_x=speed,
                angular_z=0.4,
                description="Figure-8 first loop"
            ))
        
        # Second loop (opposite direction)
        for _ in range(8):
            segments.append(MovementSegment(
                duration=0.5,
                linear_x=speed,
                angular_z=-0.4,
                description="Figure-8 second loop"
            ))
        
        return segments
    
    def _generate_search_pattern(self, params: Dict) -> List[MovementSegment]:
        """Generate systematic search pattern."""
        area_width = params.get('area_width', 2.0)
        area_height = params.get('area_height', 2.0)
        speed = params.get('speed', 0.08)
        
        segments = []
        num_passes = int(area_height / 0.5)  # 0.5m spacing
        
        for i in range(num_passes):
            # Move forward
            segments.append(MovementSegment(
                duration=area_width / speed,
                linear_x=speed,
                gait_type='tripod',
                description=f"Search pass {i+1} forward"
            ))
            
            # Side step
            if i < num_passes - 1:
                segments.append(MovementSegment(
                    duration=0.5 / speed,
                    linear_y=speed,
                    description=f"Search shift {i+1}"
                ))
                
                # Turn around
                segments.append(MovementSegment(
                    duration=2.0,
                    angular_z=math.pi,
                    description=f"Search turn {i+1}"
                ))
        
        return segments
    
    def _generate_avoidance(self, params: Dict) -> List[MovementSegment]:
        """Generate obstacle avoidance maneuver."""
        obstacle_direction = params.get('obstacle_direction', 'front')
        clearance = params.get('clearance', 0.5)
        
        segments = []
        
        if obstacle_direction == 'front':
            # Stop first
            segments.append(MovementSegment(
                duration=0.5,
                description="Stop for obstacle"
            ))
            # Back up
            segments.append(MovementSegment(
                duration=1.0,
                linear_x=-0.05,
                description="Back up from obstacle"
            ))
            # Turn
            segments.append(MovementSegment(
                duration=1.5,
                angular_z=0.5,
                description="Turn to avoid"
            ))
            # Move forward past
            segments.append(MovementSegment(
                duration=clearance / 0.08,
                linear_x=0.08,
                description="Pass obstacle"
            ))
            # Turn back
            segments.append(MovementSegment(
                duration=1.5,
                angular_z=-0.5,
                description="Turn back to original heading"
            ))
        
        return segments
    
    def start_sequence(self, segments: List[MovementSegment]):
        """Start executing a movement sequence."""
        self.current_sequence = segments
        self.sequence_index = 0
        self.start_time = 0.0
    
    def get_current_command(self, elapsed_time: float) -> Optional[MovementSegment]:
        """Get current movement command based on elapsed time."""
        if not self.current_sequence or self.sequence_index >= len(self.current_sequence):
            return None
        
        # Find current segment based on time
        accumulated_time = 0.0
        for i, segment in enumerate(self.current_sequence):
            accumulated_time += segment.duration
            if elapsed_time < accumulated_time:
                return segment
        
        return None
    
    def is_complete(self, elapsed_time: float) -> bool:
        """Check if sequence is complete."""
        if not self.current_sequence:
            return True
        
        total_duration = sum(s.duration for s in self.current_sequence)
        return elapsed_time >= total_duration
    
    def to_json(self) -> str:
        """Serialize sequence to JSON."""
        data = [
            {
                'duration': s.duration,
                'linear_x': s.linear_x,
                'linear_y': s.linear_y,
                'angular_z': s.angular_z,
                'gait_type': s.gait_type,
                'description': s.description
            }
            for s in self.current_sequence
        ]
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> List[MovementSegment]:
        """Deserialize sequence from JSON."""
        data = json.loads(json_str)
        return [
            MovementSegment(
                duration=d['duration'],
                linear_x=d.get('linear_x', 0.0),
                linear_y=d.get('linear_y', 0.0),
                angular_z=d.get('angular_z', 0.0),
                gait_type=d.get('gait_type'),
                description=d.get('description', '')
            )
            for d in data
        ]


class AIMovementInterface:
    """Interface for AI to generate and describe movements."""
    
    MOVEMENT_DESCRIPTIONS = {
        MovementType.LINEAR: {
            'en': 'Move linearly in a straight line',
            'cz': 'Pohyb po přímce'
        },
        MovementType.ROTATIONAL: {
            'en': 'Rotate in place',
            'cz': 'Otáčení na místě'
        },
        MovementType.CIRCULAR: {
            'en': 'Move in a circular pattern',
            'cz': 'Kruhový pohyb'
        },
        MovementType.ZIGZAG: {
            'en': 'Move in a zigzag pattern',
            'cz': 'Pohyb v klikatce'
        },
        MovementType.SPIRAL: {
            'en': 'Move in a spiral pattern',
            'cz': 'Spirálový pohyb'
        },
        MovementType.FIGURE_EIGHT: {
            'en': 'Move in a figure-8 pattern',
            'cz': 'Pohyb v osmičce'
        },
        MovementType.SEARCH_PATTERN: {
            'en': 'Systematic search pattern',
            'cz': 'Systematické prohledávání'
        },
        MovementType.AVOIDANCE: {
            'en': 'Obstacle avoidance maneuver',
            'cz': 'Manévr pro vyhnutí se překážce'
        },
    }
    
    def __init__(self):
        self.generator = MovementGenerator()
    
    def generate_from_description(self, description: str, language: str = 'en') -> Optional[List[MovementSegment]]:
        """Generate movement from natural language description.
        
        Args:
            description: Natural language description of desired movement
            language: 'en' or 'cz'
        
        Returns:
            Movement segments or None
        """
        desc_lower = description.lower()
        
        # Parse description for movement type
        if any(word in desc_lower for word in ['circle', 'kruh', 'kružnice']):
            return self.generator.generate_movement(MovementType.CIRCULAR, {
                'radius': self._extract_number(desc_lower, 0.5),
                'speed': 0.08
            })
        
        elif any(word in desc_lower for word in ['zigzag', 'klikatka', 'cikcak']):
            return self.generator.generate_movement(MovementType.ZIGZAG, {
                'segment_length': self._extract_number(desc_lower, 0.5),
                'num_segments': 4,
                'speed': 0.08
            })
        
        elif any(word in desc_lower for word in ['spiral', 'spirála']):
            return self.generator.generate_movement(MovementType.SPIRAL, {
                'max_radius': self._extract_number(desc_lower, 1.0),
                'speed': 0.08
            })
        
        elif any(word in desc_lower for word in ['figure 8', 'figure eight', 'osmička', 'osmicka']):
            return self.generator.generate_movement(MovementType.FIGURE_EIGHT, {
                'size': self._extract_number(desc_lower, 0.5),
                'speed': 0.08
            })
        
        elif any(word in desc_lower for word in ['search', 'hledej', 'prohledat', 'prohledávej']):
            return self.generator.generate_movement(MovementType.SEARCH_PATTERN, {
                'area_width': 2.0,
                'area_height': 2.0,
                'speed': 0.08
            })
        
        elif any(word in desc_lower for word in ['avoid', 'vyhni se', 'obejdi']):
            return self.generator.generate_movement(MovementType.AVOIDANCE, {
                'obstacle_direction': 'front',
                'clearance': 0.5
            })
        
        elif any(word in desc_lower for word in ['rotate', 'otoč se', 'otoc se', 'rotace']):
            angle = self._extract_number(desc_lower, 90)
            return self.generator.generate_movement(MovementType.ROTATIONAL, {
                'angle': angle,
                'speed': 0.5,
                'direction': 'left' if any(w in desc_lower for w in ['left', 'doleva']) else 'right'
            })
        
        else:
            # Default to linear
            distance = self._extract_number(desc_lower, 1.0)
            direction = 'forward'
            if any(w in desc_lower for w in ['back', 'zpátky', 'dozadu', 'couvej']):
                direction = 'backward'
            elif any(w in desc_lower for w in ['left', 'doleva', 'vlevo']):
                direction = 'left'
            elif any(w in desc_lower for w in ['right', 'doprava', 'vpravo']):
                direction = 'right'
            
            return self.generator.generate_movement(MovementType.LINEAR, {
                'distance': distance,
                'speed': 0.1,
                'direction': direction
            })
    
    def _extract_number(self, text: str, default: float) -> float:
        """Extract first number from text."""
        import re
        numbers = re.findall(r'\d+\.?\d*', text)
        if numbers:
            return float(numbers[0])
        return default
    
    def describe_movement(self, segments: List[MovementSegment], language: str = 'en') -> str:
        """Generate human-readable description of movement."""
        if not segments:
            return "No movement" if language == 'en' else "Žádný pohyb"
        
        total_duration = sum(s.duration for s in segments)
        
        if language == 'cz':
            return f"Sekvence {len(segments)} segmentů, celková doba {total_duration:.1f} sekund"
        else:
            return f"Sequence of {len(segments)} segments, total duration {total_duration:.1f} seconds"
