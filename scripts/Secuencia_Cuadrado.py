import time
from cflib.positioning.motion_commander import MotionCommander

def iniciar_vuelo(scf, imprimir):
    """
    scf: Es la conexión síncrona que le presta la interfaz.
    imprimir: Es la función para mandar mensajes a la pantalla negra de la GCS.
    """
    imprimir("Iniciando script externo: Secuencia Cuadrado")
    
    with MotionCommander(scf) as mc:
        imprimir("⬆️ Despegando...")
        time.sleep(1.0)
        
        imprimir("➡️ Avanzando...")
        mc.forward(0.4)
        time.sleep(1.0)
        
        imprimir("🔄 Girando...")
        mc.turn_left(90)
        time.sleep(1.0)
        
        imprimir("⬇️ Aterrizando...")
        
    imprimir("✅ Secuencia Cuadrado finalizada.")
