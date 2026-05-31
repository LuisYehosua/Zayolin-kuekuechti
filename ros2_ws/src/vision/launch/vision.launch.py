from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():

    yolo_node = Node(
        package='vision',
        executable='object_detector',
        name='object',
        output='screen'
    )


    yolo_view = Node(
        package='rqt_image_view',
        executable='rqt_image_view',
        name='yolo_view',
        arguments=['/m1/blue/detections']
    )

    return LaunchDescription([
        yolo_node,
        yolo_view,
    ])