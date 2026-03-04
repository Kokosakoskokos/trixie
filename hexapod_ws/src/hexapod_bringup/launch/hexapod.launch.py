from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    declared_arguments = []
    
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_hardware',
            default_value='true',
            description='Use real hardware (servos, sensors)'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'gait_type',
            default_value='tripod',
            description='Gait type: tripod or wave'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_ai',
            default_value='false',
            description='Enable AI control via OpenRouter'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'ai_model',
            default_value='anthropic/claude-3.5-sonnet',
            description='OpenRouter model for AI control'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'web_dashboard',
            default_value='true',
            description='Launch web dashboard'
        )
    )
    declared_arguments.append(
            DeclareLaunchArgument(
            'web_port',
            default_value='8080',
            description='Web dashboard port'
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_camera',
            default_value='true',
            description='Enable camera streaming'
        )
    )
    
    use_hardware = LaunchConfiguration('use_hardware')
    gait_type = LaunchConfiguration('gait_type')
    use_ai = LaunchConfiguration('use_ai')
    ai_model = LaunchConfiguration('ai_model')
    web_dashboard = LaunchConfiguration('web_dashboard')
    web_port = LaunchConfiguration('web_port')
    use_camera = LaunchConfiguration('use_camera')
    
    # Robot description
    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name='xacro')]),
        ' ',
        PathJoinSubstitution([
            FindPackageShare('hexapod_description'),
            'urdf',
            'hexapod.urdf.xacro'
        ])
    ])
    
    # Config file
    config_file = PathJoinSubstitution([
        FindPackageShare('hexapod_bringup'),
        'config',
        'hexapod.yaml'
    ])

    # Robot State Publisher
    robot_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description_content}]
    )
    
    # Servo Driver Node
    servo_driver = Node(
        package='hexapod_hardware',
        executable='servo_driver_node.py',
        name='servo_driver',
        parameters=[config_file, {'use_hardware': use_hardware}]
    )
    
    # IMU Driver Node
    imu_driver = Node(
        package='hexapod_hardware',
        executable='imu_driver_node.py',
        name='imu_driver',
        parameters=[config_file, {'use_hardware': use_hardware}]
    )
    
    # Ultrasonic Driver Node
    ultrasonic_driver = Node(
        package='hexapod_hardware',
        executable='ultrasonic_driver_node.py',
        name='ultrasonic_driver',
        parameters=[config_file, {'use_hardware': use_hardware}]
    )
    
    # GPS Driver Node
    gps_driver = Node(
        package='hexapod_hardware',
        executable='gps_driver_node.py',
        name='gps_driver',
        parameters=[config_file, {'use_hardware': use_hardware}]
    )
    
    # IK Solver Node
    ik_solver = Node(
        package='hexapod_kinematics',
        executable='ik_solver_node.py',
        name='ik_solver'
    )
    
    # Gait Controller Node
    gait_controller = Node(
        package='hexapod_gait',
        executable='gait_controller_node.py',
        name='gait_controller',
        parameters=[config_file, {'gait_type': gait_type}]
    )
    
    # Sensor Aggregator Node (for AI)
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
        parameters=[config_file, {
            'model': ai_model,
            'enabled': use_ai,
        }]
    )

    # Web Dashboard
    web_dashboard_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('hexapod_web'),
                'launch',
                'web_dashboard.launch.py'
            ])
        ]),
        launch_arguments=[
            ('port', web_port),
        ],
        condition=IfCondition(web_dashboard)
    )

    # Camera Driver Node
    camera_driver = Node(
        package='hexapod_hardware',
        executable='camera_driver_node.py',
        name='camera_driver',
        parameters=[config_file, {
            'use_hardware': use_camera,
            'stream_port': 8081,
        }]
    )

    return LaunchDescription(declared_arguments + [
        robot_state_pub,
        servo_driver,
        imu_driver,
        ultrasonic_driver,
        gps_driver,
        camera_driver,
        ik_solver,
        gait_controller,
        sensor_aggregator,
        ai_controller,
        web_dashboard_launch,
    ])
