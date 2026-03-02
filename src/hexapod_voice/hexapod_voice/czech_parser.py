"""Czech language command parser for hexapod robot."""

import re
from typing import Dict, Optional, Tuple


class CzechCommandParser:
    """Parse Czech text commands into robot actions."""
    
    # Movement commands in Czech
    MOVEMENT_COMMANDS = {
        # Forward
        'dopředu': {'linear_x': 0.1},
        'vpřed': {'linear_x': 0.1},
        'jeď dopředu': {'linear_x': 0.1},
        'pojď dopředu': {'linear_x': 0.1},
        'běž dopředu': {'linear_x': 0.15},
        
        # Backward
        'dozadu': {'linear_x': -0.1},
        'zpátky': {'linear_x': -0.1},
        'jeď dozadu': {'linear_x': -0.1},
        'couvej': {'linear_x': -0.05},
        'couvat': {'linear_x': -0.05},
        
        # Left
        'doleva': {'linear_y': 0.1},
        'vlevo': {'linear_y': 0.1},
        'jeď doleva': {'linear_y': 0.1},
        
        # Right
        'doprava': {'linear_y': -0.1},
        'vpravo': {'linear_y': -0.1},
        'jeď doprava': {'linear_y': -0.1},
        
        # Turn left
        'otoč se doleva': {'angular_z': 0.5},
        'zatoč doleva': {'angular_z': 0.5},
        'rotuj doleva': {'angular_z': 0.5},
        
        # Turn right
        'otoč se doprava': {'angular_z': -0.5},
        'zatoč doprava': {'angular_z': -0.5},
        'rotuj doprava': {'angular_z': -0.5},
        
        # Stop
        'stop': {},
        'zastav': {},
        'zastavit': {},
        'stůj': {},
        'nehybně': {},
        
        # Speed variations
        'pomalu dopředu': {'linear_x': 0.05},
        'rychle dopředu': {'linear_x': 0.2},
        'pomalu dozadu': {'linear_x': -0.05},
        'rychle dozadu': {'linear_x': -0.2},
    }
    
    # Gait commands
    GAIT_COMMANDS = {
        'tripod': ['tripod', 'tříbodový', 'rychlý'],
        'wave': ['wave', 'vlnkový', 'pomalý', 'stabilní'],
    }
    
    # AI commands
    AI_COMMANDS = {
        'enable': ['zapni ai', 'zapni umělou inteligenci', 'ai zapni', 'autonomní režim'],
        'disable': ['vypni ai', 'vypni umělou inteligenci', 'ai vypni', 'manuální režim'],
    }
    
    # Status queries
    STATUS_QUERIES = {
        'battery': ['baterie', 'kolik máš baterie', 'stav baterie'],
        'position': ['kde jsi', 'pozice', 'souřadnice'],
        'sensors': ['senzory', 'co vidíš', 'co detekuješ'],
    }
    
    # Greetings and responses
    GREETINGS = {
        'hello': ['ahoj', 'čau', 'dobrý den', 'zdravím', 'nazdar'],
        'how_are_you': ['jak se máš', 'jak to jde', 'všechno v pořádku'],
    }
    
    # Numbers in Czech
    NUMBERS = {
        'nula': 0, 'jedna': 1, 'jeden': 1, 'dvě': 2, 'dva': 2, 'tři': 3, 'čtyři': 4,
        'pět': 5, 'šest': 6, 'sedm': 7, 'osm': 8, 'devět': 9, 'deset': 10,
        'dvacet': 20, 'třicet': 30, 'čtyřicet': 40, 'padesát': 50,
    }
    
    def __init__(self):
        self.command_history = []
    
    def parse_command(self, text: str) -> Optional[Dict]:
        """Parse Czech text command into structured action.
        
        Args:
            text: Czech command text
        
        Returns:
            Dict with action type and parameters, or None if not understood
        """
        text = text.lower().strip()
        
        # Check for movement commands
        for cmd, params in self.MOVEMENT_COMMANDS.items():
            if cmd in text:
                return {
                    'type': 'movement',
                    'action': 'move',
                    'params': params,
                    'original_text': text
                }
        
        # Check for gait change
        for gait_type, keywords in self.GAIT_COMMANDS.items():
            for keyword in keywords:
                if keyword in text and ('chůze' in text or 'chod' in text or 'gait' in text or 'způsob' in text):
                    return {
                        'type': 'gait',
                        'action': 'change_gait',
                        'gait_type': gait_type,
                        'original_text': text
                    }
        
        # Check for AI commands
        for action, keywords in self.AI_COMMANDS.items():
            for keyword in keywords:
                if keyword in text:
                    return {
                        'type': 'ai',
                        'action': action,
                        'original_text': text
                    }
        
        # Check for status queries
        for query_type, keywords in self.STATUS_QUERIES.items():
            for keyword in keywords:
                if keyword in text:
                    return {
                        'type': 'status',
                        'query': query_type,
                        'original_text': text
                    }
        
        # Check for greetings
        for greeting_type, keywords in self.GREETINGS.items():
            for keyword in keywords:
                if keyword in text:
                    return {
                        'type': 'greeting',
                        'greeting': greeting_type,
                        'original_text': text
                    }
        
        # Try to parse complex commands with distances
        complex_cmd = self._parse_complex_command(text)
        if complex_cmd:
            return complex_cmd
        
        return None
    
    def _parse_complex_command(self, text: str) -> Optional[Dict]:
        """Parse complex commands with distances/times."""
        # Pattern: "jeď X metrů dopředu" or "pojď X metrů"
        distance_pattern = r'(\d+(?:\.\d+)?)\s*(?:metrů?|m|centimetrů?|cm)?'
        
        # Find distance
        distance_match = re.search(distance_pattern, text)
        distance = None
        if distance_match:
            distance = float(distance_match.group(1))
            # Convert cm to meters
            if 'centimetr' in text or ' cm' in text:
                distance /= 100
        
        # Find written numbers
        for word, num in self.NUMBERS.items():
            if word in text:
                distance = float(num)
                if 'centimetr' in text or ' cm' in text:
                    distance /= 100
                break
        
        # Determine direction
        direction = None
        if any(word in text for word in ['dopředu', 'vpřed']):
            direction = 'forward'
        elif any(word in text for word in ['dozadu', 'zpátky', 'couvej']):
            direction = 'backward'
        elif any(word in text for word in ['doleva', 'vlevo']):
            direction = 'left'
        elif any(word in text for word in ['doprava', 'vpravo']):
            direction = 'right'
        
        if direction and distance:
            params = {}
            if direction == 'forward':
                params['linear_x'] = min(0.2, distance / 2)  # Speed based on distance
            elif direction == 'backward':
                params['linear_x'] = -min(0.2, distance / 2)
            elif direction == 'left':
                params['linear_y'] = min(0.2, distance / 2)
            elif direction == 'right':
                params['linear_y'] = -min(0.2, distance / 2)
            
            return {
                'type': 'movement',
                'action': 'move_distance',
                'params': params,
                'distance': distance,
                'direction': direction,
                'original_text': text
            }
        
        return None
    
    def generate_response(self, command_result: Dict, success: bool = True) -> str:
        """Generate Czech response to command.
        
        Args:
            command_result: Parsed command result
            success: Whether command was executed successfully
        
        Returns:
            Czech response string
        """
        if not success:
            responses = [
                "Promiň, to jsem nepochopil.",
                "Tohle neumím udělat.",
                "Zkuste to prosím jinak.",
                "Nerozuměl jsem příkazu.",
            ]
            return responses[hash(command_result.get('original_text', '')) % len(responses)]
        
        cmd_type = command_result.get('type')
        
        if cmd_type == 'movement':
            action = command_result.get('action')
            if action == 'move_distance':
                distance = command_result.get('distance', 0)
                direction = command_result.get('direction', '')
                return f"Jedu {distance} metrů {self._direction_to_czech(direction)}."
            else:
                return "Rozumím, jedu."
        
        elif cmd_type == 'gait':
            gait = command_result.get('gait_type', '')
            return f"Měním způsob chůze na {gait}."
        
        elif cmd_type == 'ai':
            action = command_result.get('action')
            if action == 'enable':
                return "Zapínám umělou inteligenci."
            else:
                return "Vypínám umělou inteligenci, přebírám manuální kontrolu."
        
        elif cmd_type == 'greeting':
            responses = [
                "Ahoj! Jsem připraven.",
                "Zdravím! Co mám udělat?",
                "Dobrý den! Čekám na příkazy.",
                "Nazdar! Jsem tu.",
            ]
            return responses[hash(command_result.get('original_text', '')) % len(responses)]
        
        elif cmd_type == 'status':
            query = command_result.get('query')
            if query == 'battery':
                return "Stav baterie zjišťuji..."
            elif query == 'position':
                return "Zjišťuji svou pozici..."
            elif query == 'sensors':
                return "Kontroluji senzory..."
        
        return "Rozumím."
    
    def _direction_to_czech(self, direction: str) -> str:
        """Convert direction to Czech."""
        mapping = {
            'forward': 'dopředu',
            'backward': 'dozadu',
            'left': 'doleva',
            'right': 'doprava',
        }
        return mapping.get(direction, direction)


class CzechMovementGenerator:
    """Generate natural Czech descriptions of robot movements."""
    
    def describe_movement(self, linear_x: float, linear_y: float, angular_z: float) -> str:
        """Generate Czech description of current movement.
        
        Args:
            linear_x: Forward/backward velocity
            linear_y: Left/right velocity
            angular_z: Rotation velocity
        
        Returns:
            Czech description
        """
        descriptions = []
        
        if abs(linear_x) > 0.01:
            if linear_x > 0:
                speed = "rychle" if linear_x > 0.1 else "pomalu"
                descriptions.append(f"jedu {speed} dopředu")
            else:
                speed = "rychle" if linear_x < -0.1 else "pomalu"
                descriptions.append(f"couvám {speed}")
        
        if abs(linear_y) > 0.01:
            if linear_y > 0:
                descriptions.append("pohybuji se doleva")
            else:
                descriptions.append("pohybuji se doprava")
        
        if abs(angular_z) > 0.1:
            if angular_z > 0:
                descriptions.append("otáčím se doleva")
            else:
                descriptions.append("otáčím se doprava")
        
        if not descriptions:
            return "Stojím na místě."
        
        return "Právě " + ", ".join(descriptions) + "."
    
    def describe_sensor_status(self, front_dist: float, left_dist: float, right_dist: float) -> str:
        """Generate Czech description of sensor readings."""
        obstacles = []
        
        if front_dist < 0.3:
            obstacles.append(f"přede mnou je překážka ve vzdálenosti {front_dist:.2f} metrů")
        if left_dist < 0.3:
            obstacles.append(f"vlevo je překážka ve vzdálenosti {left_dist:.2f} metrů")
        if right_dist < 0.3:
            obstacles.append(f"vpravo je překážka ve vzdálenosti {right_dist:.2f} metrů")
        
        if obstacles:
            return "Detekuji: " + "; ".join(obstacles) + "."
        else:
            return "Cesta je volná."
    
    def describe_gait(self, gait_type: str) -> str:
        """Generate Czech description of gait."""
        if gait_type == 'tripod':
            return "Používám rychlý tříbodový způsob chůze."
        elif gait_type == 'wave':
            return "Používám pomalý vlnkový způsob chůze pro větší stabilitu."
        else:
            return f"Používám způsob chůze {gait_type}."
