from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    declared_arguments = []
    
    declared_arguments.append(
        DeclareLaunchArgument(
            'language',
            default_value='cz',
            description='Language for voice commands (en or cz)'
        )
    )
    
    language = LaunchConfiguration('language')
    
    # Czech Command Node
    czech_node = Node(
        package='hexapod_voice',
        executable='czech_command_node.py',
        name='czech_command',
        parameters=[{
            'enable_responses': True,
        }]
    )
    
    return LaunchDescription(declared_arguments + [
        czech_node,
    ])
