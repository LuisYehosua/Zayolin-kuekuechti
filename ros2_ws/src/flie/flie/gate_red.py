#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import logging
import time
import os

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import LogConfig  
from pynput import keyboard  # Importación para el paro de emergencia

# =====================================================
# IMPORTANTE: Usamos tu MotionCommander personalizado
# =====================================================
from flie import motion_commander
from flie.motion_commander import MotionCommander

URI = 'radio://0/80/2M'

# =====================================================
# CONFIGURACIÓN DEL ARCHIVO DE TEXTO (.TXT)
# =====================================================
NOMBRE_ARCHIVO = "telemetria_dron.txt"
archivo_log = open(NOMBRE_ARCHIVO, "w", encoding="utf-8")

# Sólo mostrar errores críticos del framework de logging
logging.basicConfig(level=logging.ERROR)

# =====================================================
# FILTRO DE ALTURA Y DETECCIÓN DE ANOMALÍAS
# =====================================================
z_filtrada = None
z_prev = None
t_prev = None

ALPHA = 0.90          # Intensidad del filtro
DZDT_THRESHOLD = 2.0  # m/s

z_congelada = None
congelamiento_activo = False
TIEMPO_CONGELAMIENTO = 1.5  # segundos
tiempo_inicio_congelamiento = 0

print(">>> MOTION COMMANDER PERSONALIZADO + ROS 2 CARGADO <<<")

# =====================================================
# NODO DE VISIÓN ROS 2
# =====================================================
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

# =====================================================
# FUNCIÓN CALLBACK PARA LOGS DE TELEMETRÍA
# =====================================================
def datos_sensores_callback(timestamp, data, logconf):
    global z_filtrada, z_prev, t_prev, z_congelada
    global congelamiento_activo, tiempo_inicio_congelamiento

    x = data['stateEstimate.x']
    y = data['stateEstimate.y']
    z = data['stateEstimate.z']
    roll = data['stabilizer.roll']
    pitch = data['stabilizer.pitch']
    yaw = data['stabilizer.yaw']

    if z_filtrada is None:
        z_filtrada = z

    z_filtrada = ALPHA * z_filtrada + (1 - ALPHA) * z
    alerta = ""

    if z_prev is not None:
        dt = (timestamp - t_prev) / 1000.0
        if dt > 0:
            dzdt = (z - z_prev) / dt
            if abs(dzdt) > DZDT_THRESHOLD:
                alerta = f" <-- ANOMALIA Z (dz/dt={dzdt:.2f} m/s)"

                if not congelamiento_activo:
                    z_congelada = z_filtrada
                    motion_commander.Z_CONGELADA = z_filtrada
                    motion_commander.CONGELAMIENTO_ACTIVO = True
                    congelamiento_activo = True
                    tiempo_inicio_congelamiento = time.time()

                    msg_anomalia = f"\n*** ALTURA CONGELADA EN {z_congelada:.2f} m ***\n"
                    print(msg_anomalia)
                    archivo_log.write(msg_anomalia + "\n")
                    archivo_log.flush()

    z_prev = z
    t_prev = timestamp

    if congelamiento_activo:
        if time.time() - tiempo_inicio_congelamiento > TIEMPO_CONGELAMIENTO:
            congelamiento_activo = False
            motion_commander.CONGELAMIENTO_ACTIVO = False
            msg_fin_congelamiento = "\n*** FIN CONGELAMIENTO ALTURA ***\n"
            print(msg_fin_congelamiento)
            archivo_log.write(msg_fin_congelamiento + "\n")
            archivo_log.flush()

    estado_altura = f" [CONGELADA:{z_congelada:.2f}]" if congelamiento_activo else ""

    cadena_datos = (
        f"[{timestamp:5d}] POS -> X:{x:6.2f}m Y:{y:6.2f}m Z:{z:6.2f}m Zf:{z_filtrada:6.2f}m | "
        f"ANG -> Roll:{roll:6.1f}° Pitch:{pitch:6.1f}° Yaw:{yaw:6.1f}°"
        f"{estado_altura}{alerta}"
    )

    # print(cadena_datos) # Descomentar si quieres ver todo el flujo de datos en terminal
    archivo_log.write(cadena_datos + "\n")
    archivo_log.flush()


# =====================================================
# FUNCIÓN PRINCIPAL
# =====================================================
def main(args=None):
    rclpy.init(args=args)
    node = CameraListener()

    cflib.crtp.init_drivers(enable_debug_driver=False)

    try:
        with SyncCrazyflie(URI, cf=Crazyflie()) as scf:
            cf = scf.cf  # Referencia interna del dron
            
            # --- PARO DE EMERGENCIA ---
            def al_presionar_tecla(tecla):
                if tecla == keyboard.Key.space:
                    msg_emergencia = "\n[!!!] PARO DE EMERGENCIA ACTIVADO [!!!]\nApagando motores inmediatamente...\n"
                    print(msg_emergencia)
                    archivo_log.write(msg_emergencia)
                    archivo_log.flush()
                    archivo_log.close()
                    cf.commander.send_stop_setpoint()
                    os._exit(1)

            listener = keyboard.Listener(on_press=al_presionar_tecla)
            listener.start()
            print(">> PARO DE EMERGENCIA ARMADO: Presiona ESPACIO en cualquier momento para abortar.\n")
            
            # --- CONFIGURACIÓN DEL LOGGING ---
            log_config = LogConfig(name='TelemetriaSensores', period_in_ms=100)
            log_config.add_variable('stateEstimate.x', 'float')
            log_config.add_variable('stateEstimate.y', 'float')
            log_config.add_variable('stateEstimate.z', 'float')
            log_config.add_variable('stabilizer.roll', 'float')
            log_config.add_variable('stabilizer.pitch', 'float')
            log_config.add_variable('stabilizer.yaw', 'float')
            log_config.data_received_cb.add_callback(datos_sensores_callback)
            cf.log.add_config(log_config)
            log_config.start()

            # --- ARMADO Y VUELO ---
            cf.platform.send_arming_request(True)
            time.sleep(1.0)

            with MotionCommander(scf) as mc:
                print('Taking off!')
                time.sleep(1)
                
                # Sube a la altura de búsqueda
                print('Moving up 0.7m')
                mc.up(0.7)
                time.sleep(1.0)
                
                # =====================================================
                # ESTADO 1: BÚSQUEDA DEL CUADRO CON ROS 2
                # =====================================================
                print("State 1: Buscando Cuadro Rojo *-*-*-*-*-")
                esperando_deteccion = True
                mc.start_left(velocity=0.1)  # Comienza a barrer hacia la izquierda
                
                while rclpy.ok() and esperando_deteccion:
                    rclpy.spin_once(node, timeout_sec=0.1)
                    
                    if node.detectado:
                        print("\n[!] ¡OBJETO DETECTADO! Deteniendo búsqueda...")
                        mc.stop()
                        time.sleep(1.0)
                        esperando_deteccion = False

                # =====================================================
                # ESTADO 2: RUTINA DE OBSTÁCULOS
                # =====================================================
                if not esperando_deteccion:
                    print("State 2: Iniciando Rutina *-*-*-*-*-")
                    
                    # Atraviesa el cuadro
                    print('Cuadro')
                    mc.forward(1.0, velocity=0.73)
                    time.sleep(2.0)
                    
                    # Sube
                    print('Sube')
                    mc.up(0.65)
                    time.sleep(2.0)
                    
                    # Avanza vara alta
                    print('Avanza vara alta')
                    mc.forward(1.6, velocity=0.73)
                    time.sleep(2.0)
                    
                    # Baja
                    print('Baja')
                    mc.down(1.0)
                    time.sleep(1.0)
                    
                    # Gira
                    print('Gira derecha')
                    mc.turn_right(90)
                    time.sleep(1.0)
                    
                    # Avanza
                    print('Avanza')
                    mc.forward(1.73, velocity=0.73)
                    time.sleep(1.0)
                    
                    # Gira
                    print('Gira para silla')
                    mc.turn_right(90)
                    time.sleep(1.0)
                    
                    # Baja a silla
                    print('Baja a silla')
                    mc.down(0.40)
                    time.sleep(1.0)
                    
                    # Avanza silla
                    print('Avanza silla')
                    mc.forward(1.5, velocity=0.73)
                    time.sleep(1.0)
                    
                    # Sube
                    print('Sube')
                    mc.up(0.3)
                    time.sleep(1.0)
                    
                    # Avanza para aterrizar
                    print('Avanza para aterrizar')
                    mc.forward(1.2)
                    time.sleep(1.0)
                    
                    print("--> Secuencia completada con éxito.")

                print('Landing!')

            # --- APAGADO Y LIMPIEZA ---
            log_config.stop()
            archivo_log.close()
            print(f"\n>> Archivo '{NOMBRE_ARCHIVO}' guardado y cerrado exitosamente.")

    except KeyboardInterrupt:
        print("¡Aterrizando de emergencia por teclado (Ctrl+C)!")
    except Exception as e:
        print(f"Error de vuelo: {e}")
    finally:
        print("Apagando motores y desconectando ROS 2...")
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
