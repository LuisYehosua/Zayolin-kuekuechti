#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point
from std_msgs.msg import String

import cv2
import os
import numpy as np
import torch

from ultralytics import YOLO


class RealSenseWindowDetector(Node):

    def __init__(self):
        super().__init__('m1_crazy_vision_detector')

        # TOPICS LIMPIOS
        self.rgb_topic = '/camera/camera/color/image_raw'
        self.image_pub_topic = '/m1/vision/detections'
        self.coord_topic = '/m1/vision/coordinates'
        self.trigger_topic = '/m1/cross_trigger'

        # YOLO MODEL
        weights_dir = os.path.expanduser('~/Zayolin-kuekuechti/ros2_ws/weights/crazy_Train')
        model_path = os.path.join(weights_dir, 'best.pt')

        self.get_logger().info(f"Cargando modelo YOLO oficial: {model_path}")

        self.model = YOLO(model_path)
        self.model.to("cuda")
        torch.backends.cudnn.benchmark = True

        # VARIABLES
        self.last_frame = None
        self.last_detections = []

        # RGB SUBSCRIPTION
        self.rgb_sub = self.create_subscription(
            Image,
            self.rgb_topic,
            self.image_callback,
            10
        )

        # PUBLISHERS
        self.image_pub = self.create_publisher(Image, self.image_pub_topic, 10)
        self.coord_pub = self.create_publisher(Point, self.coord_topic, 10)
        self.trigger_pub = self.create_publisher(String, self.trigger_topic, 10)

        # YOLO TIMER
        self.timer = self.create_timer(0.1, self.yolo_process)

        self.get_logger().info("Detector de Visión iniciado (GPU mode).")

    # ---------- ROS Image -> OpenCV ----------
    def rosimg_to_numpy(self, msg):
        img = np.frombuffer(msg.data, dtype=np.uint8)
        img = img.reshape(msg.height, msg.width, -1)
        if msg.encoding == "rgb8":
            img = img[:, :, ::-1]
        return img

    # ---------- OpenCV -> ROS Image ----------
    def numpy_to_rosimg(self, img, header):
        msg = Image()
        msg.header = header
        msg.height = img.shape[0]
        msg.width = img.shape[1]
        msg.encoding = "bgr8"
        msg.is_bigendian = False
        msg.step = img.shape[1] * 3
        msg.data = img.tobytes()
        return msg

    # ---------- IMAGE CALLBACK ----------
    def image_callback(self, msg):
        try:
            frame = self.rosimg_to_numpy(msg)
            self.last_frame = frame
            annotated = frame.copy()

            if self.last_detections:
                for det in self.last_detections:
                    x1, y1, x2, y2, tag, class_name = det

                    # Colores: Rojo para la ventana, Celeste/Amarillo para mí (el drone)
                    color = (0, 0, 255) if class_name == "red_window" else (255, 255, 0)

                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        annotated,
                        f"{class_name} {tag}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        color,
                        2
                    )

            img_msg = self.numpy_to_rosimg(annotated, msg.header)
            self.image_pub.publish(img_msg)

        except Exception as e:
            self.get_logger().error(f"Error de imagen: {e}")

    # ---------- YOLO PROCESS ----------
    def yolo_process(self):
        if self.last_frame is None:
            return

        with torch.no_grad():
            results = self.model(self.last_frame, conf=0.5, verbose=False)

        if results and len(results[0].boxes) > 0:
            h, w, _ = self.last_frame.shape
            current_detections = []
            
            # Variables para verificar "Crazyflie dentro de red_window"
            red_window_coords = None
            crazyflie_coords = None

            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                
                tag = ""

                # Filtrar y guardar coordenadas por clase
                if class_name == "red_window":
                    red_window_coords = (x1, y1, x2, y2)
                    tag = "Objetivo"
                    
                    # Seguimos publicando el centro de la ventana en el topic Point
                    center = Point()
                    center.x = float((x1 + x2) / 2 - w/2)
                    center.y = float((y1 + y2) / 2 - h/2)
                    center.z = 0.0 # Ponemos 0 ya que quitamos la fórmula vieja de distancia
                    self.coord_pub.publish(center)

                elif class_name == "crazyflie":
                    crazyflie_coords = (x1, y1, x2, y2)
                    tag = "Drone"

                current_detections.append((x1, y1, x2, y2, tag, class_name))

            self.last_detections = current_detections

            # --- LÓGICA DE OBJETO DENTRO DE OBJETO ---
            if red_window_coords and crazyflie_coords:
                rx1, ry1, rx2, ry2 = red_window_coords
                cx1, cy1, cx2, cy2 = crazyflie_coords
                
                # Calcular el punto central del crazyflie detectado
                c_center_x = (cx1 + cx2) / 2
                c_center_y = (cy1 + cy2) / 2
                
                # Verificar si el centro del crazyflie está dentro de la red_window
                if (rx1 < c_center_x < rx2) and (ry1 < c_center_y < ry2):
                    trigger_msg = String()
                    trigger_msg.data = "CROSS_WINDOW"
                    self.trigger_pub.publish(trigger_msg)
                    self.get_logger().info("🎯 ¡Crazyflie dentro de red_window! Disparando cruzada.")

        else:
            self.last_detections = []


# ---------- MAIN ----------
def main(args=None):
    rclpy.init(args=args)
    node = RealSenseWindowDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
