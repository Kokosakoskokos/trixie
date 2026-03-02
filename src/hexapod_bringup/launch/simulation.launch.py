from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    declared_arguments = []
    
    declared_arguments.append(
        DeclareLaunchArgument(
            'gait_type',
            default_value='tripod',
            description='Gait type for simulation'
        )
    )
    
    gait_type = LaunchConfiguration('gait_type')
    
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
    
    # Robot State Publisher
    robot_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description_content}]
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
        parameters=[{'gait_type': gait_type}]
    )
    
    # RViz
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', PathJoinSubstitution([
            FindPackageShare('hexapod_description'),
            'config',
            'view_robot.rviz'
        ])]
    )
    
    return LaunchDescription(declared_arguments + [
        robot_state_pub,
        ik_solver,
        gait_controller,
        rviz,
    ])
