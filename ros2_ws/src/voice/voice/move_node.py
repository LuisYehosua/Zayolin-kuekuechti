#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import cflib.crtp
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

URI = 'radio://0/80/2M' # Asegúrate de que sea tu URI correcto

class CrazyflieVoiceController(Node):
    def __init__(self, mc):
        super().__init__('cf_voice_controller')
        self.mc = mc
        self.subscription = self.create_subscription(
            String,
            '/m1/voice_cmds',
            self.command_callback,
            10)
        self.get_logger().info("¡Despegue inicial completado! Esperando comandos de voz...")

    def command_callback(self, msg):
        comando = msg.data
        self.get_logger().info(f"Ejecutando: {comando}")
        
        # El bloque "if-elif" sin el takeoff
        if comando == "forward":
            self.mc.forward(0.5)
        elif comando == "back":
            self.mc.back(0.5)
        elif comando == "right":
            self.mc.right(0.5)
        elif comando == "left":
            self.mc.left(0.5)
        elif comando == "turn right":
            self.mc.turn_right(90)
        elif comando == "turn left":
            self.mc.turn_left(90)
        elif comando == "up":
            self.mc.up(0.2)
        elif comando == "down":
            self.mc.down(0.2)
        elif comando == "land":
            self.mc.land()

def main(args=None):
    cflib.crtp.init_drivers()
    rclpy.init(args=args)
    
    # Nos conectamos al dron
    with SyncCrazyflie(URI, cf=cflib.crazyflie.Crazyflie(rw_cache='./cache')) as scf:
        # Despegue automático estándar al entrar al bloque
        with MotionCommander(scf) as mc:
            node = CrazyflieVoiceController(mc)
            try:
                rclpy.spin(node) # Mantenemos el nodo vivo escuchando los comandos
            except KeyboardInterrupt:
                pass
            finally:
                # Si algo falla o apagas el nodo con Ctrl+C, aseguro mi aterrizaje
                mc.land()
                node.destroy_node()
                rclpy.shutdown()

if __name__ == '__main__':
    main()
