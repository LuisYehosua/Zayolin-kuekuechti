import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.crazyflie.log import LogConfig  # Importamos el configurador de logs

URI = 'radio://0/80/2M'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


# --- FUNCIÓN CALLBACK PARA LOGS ---
# Esta función se ejecuta automáticamente en segundo plano cada 100ms
def datos_sensores_callback(timestamp, data, logconf):
    print(
        f"[{timestamp:5d}] "
        f"POS -> X: {data['stateEstimate.x']:6.2f}m, Y: {data['stateEstimate.y']:6.2f}m, Z: {data['stateEstimate.z']:6.2f}m | "
        f"ANG -> Roll: {data['stabilizer.roll']:6.1f}°, Pitch: {data['stabilizer.pitch']:6.1f}°, Yaw: {data['stabilizer.yaw']:6.1f}°"
    )


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    # Nota: Pasamos una instancia explícita de Crazyflie() para poder gestionar logs
    with SyncCrazyflie(URI, cf=Crazyflie()) as scf:
        cf = scf.cf  # Obtenemos la referencia interna del dron

        # =================================================================
        # CONFIGURACIÓN DEL LOGGING
        # =================================================================
        # Creamos la configuración. period_in_ms=10 significa 100ms (10Hz)
        log_config = LogConfig(name='TelemetriaSensores', period_in_ms=10)
        
        # Agregamos las variables que te interesan monitorear
        log_config.add_variable('stateEstimate.x', 'float')
        log_config.add_variable('stateEstimate.y', 'float')
        log_config.add_variable('stateEstimate.z', 'float')
        log_config.add_variable('stabilizer.roll', 'float')
        log_config.add_variable('stabilizer.pitch', 'float')
        log_config.add_variable('stabilizer.yaw', 'float')
        
        # Vinculamos la función callback que definimos arriba
        log_config.data_received_cb.add_callback(datos_sensores_callback)
        
        # Cargamos la configuración en el dron y la encendemos antes del vuelo
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

            print('Rolling right 0.2m at 0.73m/s')
            mc.right(2.0, velocity=0.73)
            time.sleep(1)

            print('Moving up 0.8m')
            mc.up(0.8)
            time.sleep(1)

            print('Move forward 2.0m at 0.73m/s')
            mc.forward(2.3, velocity=0.73)
            time.sleep(1)

            print('Moving up 0.8m')
            mc.up(0.8)
            time.sleep(1)

            print('Move forward 2.0m at 0.73m/s')
            mc.forward(1.5, velocity=0.73)
            time.sleep(1)


            print('Move down 1.7m')
            mc.down(1.7)
            time.sleep(1)

            print('Move forward 2.0m at 0.73m/')
            mc.forward(2.0, velocity=0.73)
            time.sleep(1)

            print('Rolling right 1.0m')
            mc.right(1.0, velocity=0.73)
            time.sleep(1)

            print('Turn left')
            mc.turn_left(180)
            time.sleep(1)

            print('Moving up 0.1m')
            mc.up(0.1)
            time.sleep(1)

            print('Move forward 2.0m at 0.73m/')
            mc.forward(5.0, velocity=0.73)
            time.sleep(1)

            # We land when the MotionCommander goes out of scope
            print('Landing!')


        # Apagamos el streaming de datos al terminar el bloque de vuelo
        log_config.stop()
