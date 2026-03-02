from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    declared_arguments = []
    
    declared_arguments.append(
        DeclareLaunchArgument(
            'port',
            default_value='8080',
            description='HTTP port for web dashboard'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rosbridge_port',
            default_value='9090',
            description='WebSocket port for rosbridge'
        )
    )
    
    port = LaunchConfiguration('port')
    rosbridge_port = LaunchConfiguration('rosbridge_port')
    
    # Rosbridge server (for WebSocket connection from browser)
    rosbridge = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        parameters=[{
            'port': rosbridge_port,
        }]
    )
    
    # Web server for dashboard
    web_server = Node(
        package='hexapod_web',
        executable='web_server_node.py',
        name='web_server',
        parameters=[{
            'port': port,
            'rosbridge_port': rosbridge_port,
        }]
    )
    
    return LaunchDescription(declared_arguments + [
        rosbridge,
        web_server,
    ])
