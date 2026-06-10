import logging
import time
import os

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig  
from pynput import keyboard  # Importación para el paro de emergencia

URI = 'radio://0/80/2M'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


# --- FUNCIÓN CALLBACK PARA LOGS ---
def datos_sensores_callback(timestamp, data, logconf):
    print(
        f"[{timestamp:5d}] "
        f"POS -> X: {data['stateEstimate.x']:6.2f}m, Y: {data['stateEstimate.y']:6.2f}m, Z: {data['stateEstimate.z']:6.2f}m | "
        f"ANG -> Roll: {data['stabilizer.roll']:6.1f}°, Pitch: {data['stabilizer.pitch']:6.1f}°, Yaw: {data['stabilizer.yaw']:6.1f}°"
    )


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI, cf=Crazyflie()) as scf:
        cf = scf.cf  # Obtenemos la referencia interna del dron

        # =================================================================
        # PARO DE EMERGENCIA (KILL SWITCH)
        # =================================================================
        def al_presionar_tecla(tecla):
            if tecla == keyboard.Key.space:  # Si presionas ESPACIO
                print("\n[!!!] PARO DE EMERGENCIA ACTIVADO [!!!]")
                print("Apagando motores inmediatamente...")
                cf.commander.send_stop_setpoint() # Corta la potencia a 0
                os._exit(1) # Cierra Python saltándose los time.sleep

        # Inicia el "escuchador" del teclado en segundo plano 1.26m
        listener = keyboard.Listener(on_press=al_presionar_tecla)
        listener.start()
        print(">> PARO DE EMERGENCIA ARMADO: Presiona ESPACIO en cualquier momento para abortar.\n")
        # =================================================================

        # =================================================================
        # CONFIGURACIÓN DEL LOGGING
        # =================================================================
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
        # =================================================================

        # Arm the Crazyflie
        cf.platform.send_arming_request(True)
        time.sleep(1.0)

        # We take off when the commander is created
        with MotionCommander(scf) as mc:
            print('Taking off!')
            time.sleep(1)

            print('Moving up 0.8m')
            mc.up(0.7)
            time.sleep(1)

            print('Cambio0')
            mc.forward(1.5, velocity=0.73)
            time.sleep(2.0) # Pequeña pausa de estabilidad
            
            # Sube
            print('Cambio1')
            mc.up(0.65)
            time.sleep(2.0)
            
            # Avanza
            print('Cambio2')
            mc.forward(1.4, velocity=0.79)
            time.sleep(2.0)
            
            # Baja
            print('Cambio3')
            mc.down(1.0)
            time.sleep(1.0)
            
            # Gira
            print('Cambio4')
            mc.turn_right(90)
            time.sleep(1.0) # Corregido typo: yime a time
            
            # Avanza
            print('Cambio5')
            mc.forward(1.4)
            time.sleep(1.0)
            
            # Gira
            print('Cambio6')
            mc.turn_left(270)
            time.sleep(1.0)
            
            # Baja
            print('Cambio7')
            mc.down(0.40)
            time.sleep(1.0)
            
            # Avanza
            print('Cambio8')
            mc.forward(1.5, velocity=0.73)
            time.sleep(1.0)
            
            # Sube
            print('Cambio9')
            mc.up(0.2)
            time.sleep(1.0)
            
            # Avanza
            print('Cambio10')
            mc.forward(1.2)
            time.sleep(1.0)
            
            print(" Secuencia completada con éxito.")

            # We land when the MotionCommander goes out of scope
            print('Landing!')

        # Apagamos el streaming de datos al terminar el bloque de vuelo
        log_config.stop()