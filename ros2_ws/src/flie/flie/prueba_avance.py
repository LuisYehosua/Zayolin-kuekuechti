#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import logging
import time

import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

URI = 'radio://0/80/2M'

# Clase del Nodo de ROS 2
class SimpleFlightNode(Node):
    def __init__(self):
        # Nombramos el nodo
        super().__init__('cf_simple_flight_node')
        self.get_logger().info("Nodo de vuelo iniciado. ¡Sistemas listos!")

def main(args=None):
    # 1. Inicializar ROS 2
    rclpy.init(args=args)
    
    # 2. Crear nuestro nodo
    node = SimpleFlightNode()

    # 3. Inicializar los drivers del Crazyflie
    logging.basicConfig(level=logging.ERROR)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    node.get_logger().info(f"Conectando al Crazyflie en {URI}...")

    try:
        # Iniciamos la conexión síncrona
        with SyncCrazyflie(URI) as scf:
            node.get_logger().info("¡Conectado! Armando motores...")
            
            # Arm the Crazyflie
            scf.cf.platform.send_arming_request(True)
            time.sleep(1.0)

            # We take off when the commander is created
            with MotionCommander(scf) as mc:
                node.get_logger().info('¡Despegando!')
                time.sleep(1.0)

                node.get_logger().info('Avanzando 2.0 metros a 0.73 m/s...')
                mc.forward(2.0, velocity=0.73)
                time.sleep(1.0)

                # We land when the MotionCommander goes out of scope
                node.get_logger().info('Secuencia terminada. ¡Aterrizando!')

    except Exception as e:
        node.get_logger().error(f"Se produjo un error durante el vuelo: {e}")
        
    finally:
        # 4. Limpieza: destruir el nodo y apagar ROS 2 correctamente
        node.get_logger().info('Apagando nodo...')
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()