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

# =====================================================
# CONFIGURACIÓN DEL ARCHIVO DE TEXTO (.TXT)
# =====================================================
NOMBRE_ARCHIVO = "telemetria_dron.txt"
# 'w' creará el archivo o sobrescribirá su contenido si ya existe.
archivo_log = open(NOMBRE_ARCHIVO, "w", encoding="utf-8")
# =====================================================

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

                    msg_anomalia = f"\n*** ALTURA CONGELADA EN {z_congelada:.2f} m ***\n"
                    print(msg_anomalia)
                    archivo_log.write(msg_anomalia + "\n")
                    archivo_log.flush()

    z_prev = z
    t_prev = timestamp

    # ==========================================
    # FIN DEL CONGELAMIENTO
    # ==========================================

    if congelamiento_activo:

        if time.time() - tiempo_inicio_congelamiento > TIEMPO_CONGELAMIENTO:

            congelamiento_activo = False
            motion_commander.CONGELAMIENTO_ACTIVO = False

            msg_fin_congelamiento = "\n*** FIN CONGELAMIENTO ALTURA ***\n"
            print(msg_fin_congelamiento)
            archivo_log.write(msg_fin_congelamiento + "\n")
            archivo_log.flush()

    # ==========================================
    # Estado del congelamiento
    # ==========================================

    estado_altura = ""

    if congelamiento_activo:

        estado_altura = (
            f" [CONGELADA:{z_congelada:.2f}]"
        )

    # ==========================================
    # Impresión de datos y guardado en archivo
    # ==========================================

    cadena_datos = (
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

    print(cadena_datos)                     # Muestra en la terminal
    archivo_log.write(cadena_datos + "\n")  # Escribe en el archivo .txt
    archivo_log.flush()                     # Asegura que se guarde de inmediato en el disco


if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI, cf=Crazyflie()) as scf:
        cf = scf.cf  # Obtenemos la referencia interna del dron

        # =================================================================
        # PARO DE EMBENCIA (KILL SWITCH)
        # =================================================================
        def al_presionar_tecla(tecla):
            if tecla == keyboard.Key.space:  # Si presionas ESPACIO
                msg_emergencia = (
                    "\n[!!!] PARO DE EMERGENCIA ACTIVADO [!!!]\n"
                    "Apagando motores inmediatamente...\n"
                )
                print(msg_emergencia)
                archivo_log.write(msg_emergencia)
                archivo_log.flush()
                archivo_log.close()  # Cerramos el archivo correctamente antes de salir abruptamente
                
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
            
            #Sube a la altura del cuadro
            print('Moving up 0.8m')
            mc.up(0.7)
            time.sleep(1)
            
            #Atravieza el cuadro
            print('Cuadro')
            mc.forward(1.5, velocity=0.73)
            time.sleep(2.0) # Pequeña pausa de estabilidad
            
            # Sube
            print('Sube')
            mc.up(0.65)
            time.sleep(2.0)
            
            # Avanza
            print('avanza vara alta')
            mc.forward(1.6, velocity=0.73)
            time.sleep(2.0)
            
            # Baja
            print('baja')
            mc.down(1.0)
            time.sleep(1.0)
            
            # Gira
            print('gira derecha')
            mc.turn_right(90)
            time.sleep(1.0)
            
            # Avanza
            print('avanza')
            mc.forward(1.73, velocity=0.73)
            time.sleep(1.0)
            
            # Gira
            print('gira para silla')
            mc.turn_right(90)
            time.sleep(1.0)
            
            # Baja
            print('baja a silla')
            mc.down(0.40)
            time.sleep(1.0)
            
            # Avanza
            print('avanza silla')
            mc.forward(1.5, velocity=0.73)
            time.sleep(1.0)
            
            # Sube
            print('sube')
            mc.up(0.3)
            time.sleep(1.0)
            
            # Avanza
            print('Avanza para aterrizar')
            mc.forward(1.2)
            time.sleep(1.0)
            
            print(" Secuencia completada con éxito.")

            # We land when the MotionCommander goes out of scope
            print('Landing!')

        # Apagamos el streaming de datos al terminar el bloque de vuelo
        log_config.stop()
        
        # Cierre limpio del archivo al finalizar la ejecución exitosa
        archivo_log.close()
        print(f"\n>> Archivo '{NOMBRE_ARCHIVO}' guardado y cerrado exitosamente.")
