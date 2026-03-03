from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    declared_arguments = []
    
    declared_arguments.append(
        DeclareLaunchArgument(
            'api_key',
            default_value='',
            description='OpenRouter API key (or set OPENROUTER_API_KEY env var)'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'model',
            default_value='anthropic/claude-3.5-sonnet',
            description='OpenRouter model to use'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'enabled',
            default_value='false',
            description='Start with AI control enabled'
        )
    )
    
    api_key = LaunchConfiguration('api_key')
    model = LaunchConfiguration('model')
    enabled = LaunchConfiguration('enabled')
    
    # Sensor Aggregator Node
    sensor_aggregator = Node(
        package='hexapod_ai',
        executable='sensor_aggregator_node.py',
        name='sensor_aggregator'
    )
    
    # AI Controller Node
    ai_controller = Node(
        package='hexapod_ai',
        executable='ai_controller_node.py',
        name='ai_controller',
        parameters=[{
            'api_key': api_key,
            'model': model,
            'enabled': enabled,
        }]
    )
    
    return LaunchDescription(declared_arguments + [
        sensor_aggregator,
        ai_controller,
    ])
