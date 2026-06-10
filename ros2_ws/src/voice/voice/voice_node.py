#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import speech_recognition as sr
import threading

class VoiceCommanderNode(Node):
    def __init__(self):
        super().__init__('voice_commander')
        self.publisher_ = self.create_publisher(String, '/m1/voice_cmds', 10)
        
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        
        # Diccionario de comandos permitidos
        self.valid_commands = [
            "take off", "turn right", "turn left", "right", "left", "forward", "back", "land", "up", "down"
        ]
        
        # Iniciamos el hilo de escucha para no bloquear ROS 2
        self.get_logger().info('¡Micrófono encendido! Di "Drone [comando]"')
        threading.Thread(target=self.listen_loop, daemon=True).start()

    def listen_loop(self):
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while rclpy.ok():
                try:
                    # Escuchamos el audio
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=5)
                    # Usamos en-US para que entienda los comandos en inglés sin importar tu acento
                    text = self.recognizer.recognize_google(audio, language='en-US').lower()
                    self.get_logger().info(f'Escuché: "{text}"')
                    
                    # Verificamos la palabra de seguridad
                    if "drone" in text:
                        # Buscamos si dijo algún comando válido
                        for cmd in self.valid_commands:
                            if cmd in text:
                                msg = String()
                                msg.data = cmd
                                self.publisher_.publish(msg)
                                self.get_logger().info(f'Comando enviado: {cmd}')
                                break # Solo enviamos el primer comando que detecte
                
                except sr.UnknownValueError:
                    pass # No entendió nada, ignorar
                except sr.RequestError:
                    self.get_logger().error("Error de conexión con el servicio de voz")

def main(args=None):
    rclpy.init(args=args)
    node = VoiceCommanderNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
