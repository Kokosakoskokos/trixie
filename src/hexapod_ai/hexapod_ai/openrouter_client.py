"""OpenRouter API client for AI integration."""

import json
import requests
from typing import List, Dict, Optional


class OpenRouterClient:
    """Client for OpenRouter API."""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://hexapod-robot.local",
            "X-Title": "Hexapod Robot"
        }
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """Send chat completion request.
        
        Args:
            messages: List of {"role": "system/user/assistant", "content": "..."}
            temperature: Randomness (0-1)
            max_tokens: Max response length
        
        Returns:
            Response content or None on error
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"OpenRouter API error: {e}")
            return None
    
    def get_models(self) -> List[Dict]:
        """Get available models."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/models",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException:
            return []


class HexapodAI:
    """AI interface for hexapod robot control."""
    
    SYSTEM_PROMPT_EN = """You are the AI brain of a hexapod walking robot. 
You receive sensor data and decide on movement commands.

Robot capabilities:
- Walk forward/backward/left/right
- Turn in place (rotate)
- Stand still
- Change gait type (tripod = fast, wave = stable)

Sensor data includes:
- IMU orientation and acceleration
- Ultrasonic distance sensors (front/left/right)
- GPS position

Respond ONLY with a JSON object in this format:
{
    "action": "move|turn|stop|change_gait",
    "params": {
        "linear_x": 0.0,  // forward/back speed m/s (-0.2 to 0.2)
        "linear_y": 0.0,  // left/right speed m/s (-0.2 to 0.2)
        "angular_z": 0.0  // rotation rad/s (-1.0 to 1.0)
    },
    "gait_type": "tripod|wave",  // only if action is change_gait
    "reasoning": "Brief explanation of decision"
}

Safety rules:
- If obstacle detected within 0.3m, stop or turn away
- If tilt exceeds 20 degrees, stop immediately
- Prefer smooth movements over abrupt changes"""

    SYSTEM_PROMPT_CZ = """Jsi AI mozek šestinohého chodícího robota.
Přijímáš data ze senzorů a rozhoduješ o pohybových příkazech.

Schopnosti robota:
- Chůze dopředu/dozadu/doleva/doprava
- Otáčení na místě
- Zastavení
- Změna způsobu chůze (tripod = rychlý, wave = stabilní)

Data ze senzorů zahrnují:
- IMU orientaci a zrychlení
- Ultrazvukové senzory vzdálenosti (přední/levý/pravý)
- GPS pozici

Odpovídej POUZE JSON objektem v tomto formátu:
{
    "action": "move|turn|stop|change_gait",
    "params": {
        "linear_x": 0.0,  // rychlost dopředu/dozadu m/s (-0.2 až 0.2)
        "linear_y": 0.0,  // rychlost doleva/doprava m/s (-0.2 až 0.2)
        "angular_z": 0.0  // rotační rychlost rad/s (-1.0 až 1.0)
    },
    "gait_type": "tripod|wave",  // pouze pokud action je change_gait
    "reasoning": "Stručné vysvětlení rozhodnutí"
}

Bezpečnostní pravidla:
- Pokud je detekována překážka do 0.3m, zastav se nebo se otoč
- Pokud náklon překročí 20 stupňů, okamžitě zastav
- Preferuj plynulé pohyby před náhlými změnami"""

    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet", language: str = "en"):
        self.client = OpenRouterClient(api_key, model)
        self.conversation_history = []
        self.language = language
        self.system_prompt = self.SYSTEM_PROMPT_CZ if language == "cz" else self.SYSTEM_PROMPT_EN
    
    def set_language(self, language: str):
        """Set AI language (en or cz)."""
        self.language = language
        self.system_prompt = self.SYSTEM_PROMPT_CZ if language == "cz" else self.SYSTEM_PROMPT_EN
    
    def decide_action(self, sensor_data: Dict) -> Optional[Dict]:
        """Get AI decision based on sensor data."""
        sensor_text = self._format_sensors(sensor_data)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"{self._get_sensor_prompt()}\n{sensor_text}\n\n{self._get_action_prompt()}"}
        ]
        
        response = self.client.chat_completion(messages, temperature=0.5)
        
        if response:
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                print(f"Failed to parse AI response: {response}")
        
        return None
    
    def _get_sensor_prompt(self) -> str:
        """Get sensor prompt in current language."""
        if self.language == "cz":
            return "Aktuální data ze senzorů:"
        return "Current sensor data:"
    
    def _get_action_prompt(self) -> str:
        """Get action prompt in current language."""
        if self.language == "cz":
            return "Co by měl robot udělat?"
        return "What should the robot do?"
    
    def _format_sensors(self, data: Dict) -> str:
        """Format sensor data as readable text."""
        lines = []
        
        if "imu" in data:
            imu = data["imu"]
            if self.language == "cz":
                lines.append(f"IMU Zrychlení: x={imu.get('ax',0):.2f}, y={imu.get('ay',0):.2f}, z={imu.get('az',0):.2f} m/s²")
                lines.append(f"IMU Gyro: x={imu.get('gx',0):.2f}, y={imu.get('gy',0):.2f}, z={imu.get('gz',0):.2f} rad/s")
            else:
                lines.append(f"IMU Acceleration: x={imu.get('ax',0):.2f}, y={imu.get('ay',0):.2f}, z={imu.get('az',0):.2f} m/s²")
                lines.append(f"IMU Gyro: x={imu.get('gx',0):.2f}, y={imu.get('gy',0):.2f}, z={imu.get('gz',0):.2f} rad/s")
        
        if "ultrasonic" in data:
            us = data["ultrasonic"]
            if self.language == "cz":
                lines.append(f"Vzdálenosti - Přední: {us.get('front',99):.2f}m, Levý: {us.get('left',99):.2f}m, Pravý: {us.get('right',99):.2f}m")
            else:
                lines.append(f"Distances - Front: {us.get('front',99):.2f}m, Left: {us.get('left',99):.2f}m, Right: {us.get('right',99):.2f}m")
        
        if "gps" in data:
            gps = data["gps"]
            if self.language == "cz":
                lines.append(f"GPS: lat={gps.get('lat',0):.6f}, lon={gps.get('lon',0):.6f}")
            else:
                lines.append(f"GPS: lat={gps.get('lat',0):.6f}, lon={gps.get('lon',0):.6f}")
        
        return "\n".join(lines)
    
    def chat(self, user_message: str) -> Optional[str]:
        """Have a conversation with the AI about the robot."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        return self.client.chat_completion(messages)
    
    def generate_movement(self, description: str) -> Optional[Dict]:
        """Generate complex movement sequence from description.
        
        Args:
            description: Natural language description of desired movement
        
        Returns:
            Dict with movement sequence or None
        """
        movement_prompt_en = f"""Generate a movement sequence for the following request: "{description}"

Available movement types:
- linear: Move in straight line (params: distance, speed, direction)
- rotational: Rotate in place (params: angle, speed, direction)
- circular: Move in circle (params: radius, speed, direction, revolutions)
- zigzag: Zigzag pattern (params: segment_length, num_segments, speed)
- spiral: Spiral outward (params: max_radius, speed)
- figure_eight: Figure-8 pattern (params: size, speed)
- search_pattern: Systematic area search (params: area_width, area_height, speed)
- avoidance: Obstacle avoidance (params: obstacle_direction, clearance)

Respond with JSON:
{{
    "movement_type": "type_name",
    "params": {{...}},
    "description": "Brief description of the movement"
}}"""

        movement_prompt_cz = f"""Vygeneruj pohybovou sekvenci pro následující požadavek: "{description}"

Dostupné typy pohybů:
- linear: Pohyb po přímce (parametry: distance, speed, direction)
- rotational: Otáčení na místě (parametry: angle, speed, direction)
- circular: Kruhový pohyb (parametry: radius, speed, direction, revolutions)
- zigzag: Pohyb v klikatce (parametry: segment_length, num_segments, speed)
- spiral: Spirálový pohyb (parametry: max_radius, speed)
- figure_eight: Pohyb v osmičce (parametry: size, speed)
- search_pattern: Systematické prohledávání (parametry: area_width, area_height, speed)
- avoidance: Vyhýbání se překážce (parametry: obstacle_direction, clearance)

Odpověz JSON formátem:
{{
    "movement_type": "název_typu",
    "params": {{...}},
    "description": "Stručný popis pohybu"
}}"""

        prompt = movement_prompt_cz if self.language == "cz" else movement_prompt_en
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat_completion(messages, temperature=0.7)
        
        if response:
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                print(f"Failed to parse movement response: {response}")
        
        return None
