#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String  # Corregido: std_msgs.msg
import time

# Libraries crazyflie
import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

# Radio PA connect with the drone 
URI = 'radio://0/80/2M'

# Class for camera
class CameraListener(Node):
    def __init__(self):
        super().__init__('Camera_listener')
        self.detectado = False
        
        self.trigger_sub = self.create_subscription(
            String,
            '/m1/cross_trigger',
            self.trigger_callback,
            10
        )

    def trigger_callback(self, msg):
        if msg.data == "CROSS_WINDOW":
            self.detectado = True

# main
def main(args=None):
    rclpy.init(args=args)
    node = CameraListener()

    cflib.crtp.init_drivers(enable_debug_driver=False) # Start drivers crazyradio PA

    try:
        with SyncCrazyflie(URI) as scf:
            print("¡Connected!")
            
            with MotionCommander(scf) as mc: # When the with start the drone takeoff
            
                print("Elevando...")
                mc.up(0.7)
                time.sleep(1.0)
                
                # State 1
                print("State 1: *-*-*-*-*-")
                
                # States variables 
                esperando_deteccion = True

                # Routine before detect
                mc.start_left(velocity=0.1)
                
                # Loop for wait the camera detect
                while rclpy.ok() and esperando_deteccion:
                    rclpy.spin_once(node, timeout_sec=0.1)
                    
                    if node.detectado:
                        print("Object detected")
                        mc.stop() # Stop the waiting routine
                        time.sleep(1.0)
                        esperando_deteccion = False

                # State 2
                print("State 2: *-*-*-*-*-")
                if not esperando_deteccion:
                    print("--> Ejecutando Paso 1: Avanzando 2.0 metros")
                    mc.forward(1.3, velocity=0.73)
                    time.sleep(1.0) # Pequeña pausa de estabilidad
                    #Sube
                    mc.up(0.6)
                    time.sleep(1.0)
                    #Avanza
                    mc.forward(1.3, velocity=0.73)
                    time.sleep(1.0)
                    #Baja
                    mc.down(1.0)
                    time.sleep(1.0)
                    #Gira
                    mc.turn_right(90)
                    yime.sleep(1.0)
                    #Avanza
                    mc.forward(1.4)
                    time.sleep(1.0)
                    #Gira
                    mc.turn_left(270)
                    time.sleep(1.0)
                    #Baja
                    mc.down(0.40)
                    time.sleep(1.0)
                    #Avanza
                    mc.forward(1.5, velocity=0.73)
                    time.sleep(1.0)
                    #Sube
                    mc.up(0.2)
                    time.sleep(1.0)
                    #Avanza
                    mc.forward(1.2)
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
