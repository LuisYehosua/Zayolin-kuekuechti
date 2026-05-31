#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
import time

# Libraries crazyflie
import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

#Radio PA conect whith the drone 
URI = 'radio://0/80/2M'

#Class for camera
class CameraListener(Node):
    def __init__(self):
        super().__init__('Camera_listener')
        self.detectado = False
        
        self.coord_sub = self.create_subscription(
            Point,
            '/m1/blue/coordinates',
            self.coord_callback,
            10
        )

    def coord_callback(self, msg):
        self.detectado = True

#main
def main(args=None):
    rclpy.init(args=args)
    node = CameraListener()

    cflib.crtp.init_drivers(enable_debug_driver=False) #Start drivers crazyradio PA

    try:
        with SyncCrazyflie(URI) as scf:
            print("¡Conected")
            
            with MotionCommander(scf) as mc: #When the with start the drone takeoff
                
                #State 1
                print("State 1: *-*-*-*-*-")
                
                # States variables 
                esperando_deteccion = True

                #Routine before detect
                mc.start_right(velocity=0.15)
                
                # Loop for whait the camera detect
                while rclpy.ok() and esperando_deteccion:
                    rclpy.spin_once(node, timeout_sec=0.1)
                    
                    if node.detectado:
                        print("Object detected")
                        mc.stop() #Stop the waiting routine
                        time.sleep(1.0)
                        esperando_deteccion = False

                #State 2
                print("State 2: *-*-*-*-*-")
                if not esperando_deteccion:
                    print("--> Ejecutando Paso 1: Avanzando 0.5 metros")
                    mc.forward(0.5, velocity=0.73)
                    time.sleep(0.5) # Pequeña pausa de estabilidad
                    
                    print("--> Ejecutando Paso 2: Girando 90 grados a la izquierda")
                    mc.turn_left(90)
                    time.sleep(0.5)
                    
                    print("--> Ejecutando Paso 3: Avanzando 0.3 metros")
                    mc.forward(1.0, velocity=0.2)
                    time.sleep(0.5)

                    print(" Secuencia completada con éxito.")

    except KeyboardInterrupt:
        print("¡Aterrizando de emergencia por teclado!")
    except Exception as e:
        print(f"Error de vuelo: {e}")
    finally:
        print("Apagando motores y desconectando ROS 2...")
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()