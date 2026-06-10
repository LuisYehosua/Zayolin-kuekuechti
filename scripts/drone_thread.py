import time
import threading
import importlib.util
import os
from PyQt5.QtCore import QThread, pyqtSignal
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import LogConfig
from cflib.positioning.motion_commander import MotionCommander

class DroneThread(QThread):
    update_telemetry = pyqtSignal(dict)
    connection_status = pyqtSignal(str)
    flight_msg = pyqtSignal(str)

    def __init__(self, uri):
        super().__init__()
        self.uri = uri
        self.running = True
        self.scf = None
        self.cf = None 

    def run(self):
        cflib.crtp.init_drivers(enable_debug_driver=False)
        self.connection_status.emit("CONNECTING...")
        
        try:
            with SyncCrazyflie(self.uri, cf=Crazyflie()) as scf:
                self.scf = scf 
                self.cf = scf.cf
                self.connection_status.emit("CONNECTED")
                
                log_conf = LogConfig(name='Telemetry', period_in_ms=100)
                log_conf.add_variable('stateEstimate.x', 'float')
                log_conf.add_variable('stateEstimate.y', 'float')
                log_conf.add_variable('stateEstimate.z', 'float')
                log_conf.add_variable('stabilizer.roll', 'float')
                log_conf.add_variable('stabilizer.pitch', 'float')
                log_conf.add_variable('stabilizer.yaw', 'float')
                
                def log_callback(timestamp, data, logconf):
                    self.update_telemetry.emit(data)

                self.cf.log.add_config(log_conf)
                log_conf.data_received_cb.add_callback(log_callback)
                log_conf.start()
                
                while self.running:
                    self.msleep(100)
                    
                log_conf.stop()
                
        except Exception as e:
            print(f"[ERROR] No se pudo conectar: {e}")
            
        self.connection_status.emit("DISCONNECTED")

    def reset_estimador(self):
        """Resetea el Filtro de Kalman para evitar el Drift (dron fantasma) al aterrizar"""
        self.flight_msg.emit("🔄 Reseteando Filtro de Kalman...")
        self.cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        self.cf.param.set_value('kalman.resetEstimation', '0')
        time.sleep(1.0) # Esperar a que se estabilice

    def ejecutar_script_externo(self, nombre_archivo):
        """Carga un archivo de Python externo y ejecuta su rutina de vuelo"""
        if self.scf is None:
            self.flight_msg.emit("❌ Error: Dron no conectado.")
            return

        def rutina_hilo():
            ruta_script = os.path.join(os.getcwd(), nombre_archivo)
            if not os.path.exists(ruta_script):
                self.flight_msg.emit(f"❌ Error: No se encontró el script {nombre_archivo}")
                return

            try:
                # 1. Reseteamos la posición a 0,0,0 para borrar el error del vuelo anterior
                self.reset_estimador()

                # 2. Cargamos el script de Python seleccionado de forma dinámica
                self.flight_msg.emit(f"📂 Cargando {nombre_archivo}...")
                spec = importlib.util.spec_from_file_location("modulo_vuelo", ruta_script)
                modulo_vuelo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(modulo_vuelo)

                # 3. Ejecutamos la función 'iniciar_vuelo' que debe estar dentro de tu script
                modulo_vuelo.iniciar_vuelo(self.scf, self.flight_msg.emit)
                
            except Exception as e:
                self.flight_msg.emit(f"⚠️ Error en el script: {e}")

        # Lanzamos el script en segundo plano para no trabar la interfaz
        hilo = threading.Thread(target=rutina_hilo, daemon=True)
        hilo.start()

    def paro_emergencia(self):
        if self.cf is not None:
            self.cf.commander.send_stop_setpoint()

    def stop(self):
        self.running = False
