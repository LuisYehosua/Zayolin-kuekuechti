import logging
import time
import os

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
#from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig  
from pynput import keyboard  # Importación para el paro de emergencia

import motion_commander
from motion_commander import MotionCommander

URI = 'radio://0/80/2M'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

# =====================================================
# FILTRO DE ALTURA Y DETECCIÓN DE ANOMALÍAS
# =====================================================

z_filtrada = None
z_prev = None
t_prev = None

ALPHA = 0.90          # Intensidad del filtro
DZDT_THRESHOLD = 2.0  # m/s

# =====================================================

# ==========================================
# CONGELAMIENTO DE ALTURA
# ==========================================

z_congelada = None

congelamiento_activo = False

print(">>> MOTION COMMANDER PERSONALIZADO CARGADO <<<")

TIEMPO_CONGELAMIENTO = 1.5  # segundos

tiempo_inicio_congelamiento = 0


# --- FUNCIÓN CALLBACK PARA LOGS ---
def datos_sensores_callback(timestamp, data, logconf):

    global z_filtrada
    global z_prev
    global t_prev
    global z_congelada
    global congelamiento_activo
    global tiempo_inicio_congelamiento

    # ==========================================
    # Lectura de sensores
    # ==========================================

    x = data['stateEstimate.x']
    y = data['stateEstimate.y']
    z = data['stateEstimate.z']

    roll = data['stabilizer.roll']
    pitch = data['stabilizer.pitch']
    yaw = data['stabilizer.yaw']

    # ==========================================
    # Inicialización del filtro
    # ==========================================

    if z_filtrada is None:
        z_filtrada = z

    # ==========================================
    # Filtro exponencial
    # ==========================================

    z_filtrada = ALPHA * z_filtrada + (1 - ALPHA) * z

    # ==========================================
    # Detección de anomalías
    # ==========================================

    alerta = ""

    if z_prev is not None:

        dt = (timestamp - t_prev) / 1000.0

        if dt > 0:

            dzdt = (z - z_prev) / dt

            if abs(dzdt) > DZDT_THRESHOLD:

                alerta = (
                    f" <-- ANOMALIA Z (dz/dt={dzdt:.2f} m/s)"
                )

                if not congelamiento_activo:

                    z_congelada = z_filtrada

                    motion_commander.Z_CONGELADA = z_filtrada

                    motion_commander.CONGELAMIENTO_ACTIVO = True

                    congelamiento_activo = True

                    tiempo_inicio_congelamiento = time.time()

                    print(
                        f"\n*** ALTURA CONGELADA EN {z_congelada:.2f} m ***\n"
                    )

    z_prev = z
    t_prev = timestamp

    # ==========================================
    # FIN DEL CONGELAMIENTO
    # ==========================================

    if congelamiento_activo:

        if time.time() - tiempo_inicio_congelamiento > TIEMPO_CONGELAMIENTO:

            congelamiento_activo = False

            motion_commander.CONGELAMIENTO_ACTIVO = False

            print(
                "\n*** FIN CONGELAMIENTO ALTURA ***\n"
            )

    # ==========================================
    # Estado del congelamiento
    # ==========================================

    estado_altura = ""

    if congelamiento_activo:

        estado_altura = (
            f" [CONGELADA:{z_congelada:.2f}]"
        )

    # ==========================================
    # Impresión de datos
    # ==========================================

    print(
        f"[{timestamp:5d}] "
        f"POS -> "
        f"X:{x:6.2f}m "
        f"Y:{y:6.2f}m "
        f"Z:{z:6.2f}m "
        f"Zf:{z_filtrada:6.2f}m | "
        f"ANG -> "
        f"Roll:{roll:6.1f}° "
        f"Pitch:{pitch:6.1f}° "
        f"Yaw:{yaw:6.1f}°"
        f"{estado_altura}"
        f"{alerta}"
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

        # Inicia el "escuchador" del teclado en segundo plano
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

            mc.forward(1.5, velocity=0.73)
            time.sleep(2.0) # Pequeña pausa de estabilidad
            
            # Sube
            print('Cambio1')
            mc.up(0.65)
            time.sleep(2.0)
            
            # Avanza
            print('Cambio2')
            mc.forward(1.6, velocity=0.73)
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
