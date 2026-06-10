import sys
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                             QTextEdit, QComboBox, QFrame)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import pyqtgraph.opengl as gl
from drone_thread import DroneThread

class CrazyflieGCS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crazyflie 2.1+ Ground Control Station")
        self.resize(1100, 700)
        self.modo_actual = "Ninguno"
        self.drone_thread = None
        self.URI = 'radio://0/80/2M'

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. ENCABEZADO
        header_layout = QHBoxLayout()
        title_label = QLabel("🚁 CRAZY FLY 2.1+")
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        header_layout.addWidget(title_label)
        
        self.connection_label = QLabel("Estado: DISCONNECTED")
        self.connection_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.connection_label)

        # --- NUEVO BOTÓN DE CONEXIÓN ---
        self.btn_connect = QPushButton("🔗 CONECTAR DRON")
        self.btn_connect.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px;")
        self.btn_connect.setCheckable(True) # Actúa como un interruptor On/Off
        header_layout.addWidget(self.btn_connect)

        self.battery_label = QLabel("Batería: --%")
        self.battery_label.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(self.battery_label)

        main_layout.addLayout(header_layout)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        main_layout.addWidget(line)

        # 2. CUERPO PRINCIPAL
        body_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        self.pantalla_modo = QLabel("MODO: SELECCIONE UNO")
        self.pantalla_modo.setStyleSheet("background-color: black; color: #00FF00; font-size: 16px; padding: 10px;")
        self.pantalla_modo.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.pantalla_modo)

        self.btn_keyword = QPushButton("Keyword")
        self.btn_voice = QPushButton("Voice")
        self.btn_vision = QPushButton("Vision")
        self.btn_custom = QPushButton("Custom")

        self.combo_custom = QComboBox()
        # Aquí van los nombres exactos de tus archivos Python
        self.combo_custom.addItems(["Selecciona Secuencia...", "Secuencia_Cuadrado.py", "Secuencia_Ataque.py"])
        self.combo_custom.hide()

        left_layout.addWidget(self.btn_keyword)
        left_layout.addWidget(self.btn_voice)
        left_layout.addWidget(self.btn_vision)
        left_layout.addWidget(self.btn_custom)
        left_layout.addWidget(self.combo_custom)
        left_layout.addStretch()
        body_layout.addLayout(left_layout, 1)

        # Centro (Modelo 3D)
        center_layout = QVBoxLayout()
        self.view_3d = gl.GLViewWidget()
        self.view_3d.setMinimumSize(300, 300)
        self.view_3d.opts['distance'] = 20
        grid = gl.GLGridItem()
        self.view_3d.addItem(grid)
        
        self.drone_box = gl.GLBoxItem(size=QtGui.QVector3D(2, 2, 0.5), color=(0, 255, 255, 100))
        self.view_3d.addItem(self.drone_box)
        
        center_layout.addWidget(QLabel("<b>Simulador de Orientación</b>"))
        center_layout.addWidget(self.view_3d)

        telemetry_layout = QGridLayout()
        self.lbl_roll = QLabel("Roll: 0.0°")
        self.lbl_pitch = QLabel("Pitch: 0.0°")
        self.lbl_yaw = QLabel("Yaw: 0.0°")
        self.lbl_x = QLabel("X: 0.0m")
        self.lbl_y = QLabel("Y: 0.0m")
        self.lbl_z = QLabel("Z: 0.0m")
        
        telemetry_layout.addWidget(self.lbl_roll, 0, 0)
        telemetry_layout.addWidget(self.lbl_pitch, 1, 0)
        telemetry_layout.addWidget(self.lbl_yaw, 2, 0)
        telemetry_layout.addWidget(self.lbl_x, 0, 1)
        telemetry_layout.addWidget(self.lbl_y, 1, 1)
        telemetry_layout.addWidget(self.lbl_z, 2, 1)
        
        center_layout.addLayout(telemetry_layout)
        body_layout.addLayout(center_layout, 2)

        # Derecha (Terminal)
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("<b>PANTALLA TERMINAL</b>"))
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background-color: #1e1e1e; color: #ffffff; font-family: Courier;")
        self.terminal.append(">> Crazyflie OS Iniciado...")
        right_layout.addWidget(self.terminal)
        
        body_layout.addLayout(right_layout, 2)
        main_layout.addLayout(body_layout)

        # 3. CONTROLES INFERIORES
        bottom_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ PLAY (Ejecutar)")
        self.btn_play.setStyleSheet("background-color: green; color: white; font-weight: bold; padding: 15px;")
        
        self.btn_stop = QPushButton("⏹ PARO DE EMERGENCIA")
        self.btn_stop.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 15px;")
        
        self.btn_save_log = QPushButton("📝 Guardar Vuelo (Log)")
        self.btn_save_log.setStyleSheet("background-color: gray; color: white; padding: 15px;")

        bottom_layout.addWidget(self.btn_play)
        bottom_layout.addWidget(self.btn_stop)
        bottom_layout.addWidget(self.btn_save_log)
        main_layout.addLayout(bottom_layout)

        # --- CONEXIÓN DE SEÑALES ---
        self.btn_connect.clicked.connect(self.toggle_conexion)
        self.btn_keyword.clicked.connect(lambda: self.cambiar_modo("KEYWORD"))
        self.btn_voice.clicked.connect(lambda: self.cambiar_modo("VOICE"))
        self.btn_vision.clicked.connect(lambda: self.cambiar_modo("VISION"))
        self.btn_custom.clicked.connect(self.activar_custom)
        self.btn_play.clicked.connect(self.ejecutar_script)
        self.btn_stop.clicked.connect(self.paro_emergencia_gui)

    def toggle_conexion(self):
        """Conecta o desconecta el dron dependiendo del estado del botón"""
        if self.btn_connect.isChecked():
            self.btn_connect.setText("🔌 DESCONECTAR")
            self.btn_connect.setStyleSheet("background-color: orange; color: white; font-weight: bold; padding: 5px;")
            self.imprimir_terminal(f"Intentando conectar a {self.URI}...")
            
            self.drone_thread = DroneThread(self.URI)
            self.drone_thread.update_telemetry.connect(self.actualizar_datos)
            self.drone_thread.connection_status.connect(self.actualizar_conexion)
            self.drone_thread.flight_msg.connect(self.imprimir_terminal)
            self.drone_thread.start()
        else:
            self.btn_connect.setText("🔗 CONECTAR DRON")
            self.btn_connect.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px;")
            self.imprimir_terminal("Desconectando del dron...")
            if self.drone_thread:
                self.drone_thread.stop()
                self.drone_thread.wait()

    def actualizar_datos(self, data):
        self.lbl_x.setText(f"X: {data['stateEstimate.x']:.2f}m")
        self.lbl_y.setText(f"Y: {data['stateEstimate.y']:.2f}m")
        self.lbl_z.setText(f"Z: {data['stateEstimate.z']:.2f}m")
        self.lbl_roll.setText(f"Roll: {data['stabilizer.roll']:.1f}°")
        self.lbl_pitch.setText(f"Pitch: {data['stabilizer.pitch']:.1f}°")
        self.lbl_yaw.setText(f"Yaw: {data['stabilizer.yaw']:.1f}°")
        
        offset_x, offset_y, offset_z = -1.0, -1.0, -0.25
        self.drone_box.resetTransform()
        self.drone_box.rotate(data['stabilizer.roll'], 1, 0, 0)
        self.drone_box.rotate(data['stabilizer.pitch'], 0, 1, 0)
        self.drone_box.rotate(data['stabilizer.yaw'], 0, 0, 1)
        self.drone_box.translate(offset_x, offset_y, offset_z, local=True)

    def actualizar_conexion(self, status):
        self.connection_label.setText(f"Estado: {status}")
        if status == "CONNECTED":
            self.connection_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
            self.imprimir_terminal("✅ Conectado.")
        else:
            self.connection_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            self.imprimir_terminal("❌ Desconectado.")

    def cambiar_modo(self, modo):
        self.modo_actual = modo
        self.combo_custom.hide()
        self.pantalla_modo.setText(f"MODO: {modo}")

    def activar_custom(self):
        self.cambiar_modo("CUSTOM")
        self.combo_custom.show()

    def imprimir_terminal(self, texto):
        self.terminal.append(f">> {texto}")

    def ejecutar_script(self):
        if self.modo_actual == "CUSTOM" and self.drone_thread:
            script = self.combo_custom.currentText()
            if script != "Selecciona Secuencia...":
                self.imprimir_terminal(f"▶️ Ejecutando archivo externo: {script}")
                self.drone_thread.ejecutar_script_externo(script)
            else:
                self.imprimir_terminal("⚠️ Selecciona un script primero.")
        else:
            self.imprimir_terminal("⚠️ Asegúrate de estar en modo 'Custom' y conectado al dron.")

    def paro_emergencia_gui(self):
        self.imprimir_terminal("🚨 ¡PARO DE EMERGENCIA!")
        if self.drone_thread:
            self.drone_thread.paro_emergencia()

    def closeEvent(self, event):
        if self.drone_thread:
            self.drone_thread.stop()
            self.drone_thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = CrazyflieGCS()
    ventana.show()
    sys.exit(app.exec_())
