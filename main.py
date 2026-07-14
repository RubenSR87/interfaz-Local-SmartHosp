import sys
import threading # <-- NUEVO: Para correr tareas en el fondo
import os
import json
from flask import Flask, request, jsonify # <-- NUEVO: El servidor web
from flask_cors import CORS # <-- NUEVO: Seguridad de conexión

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLabel, QComboBox, QHBoxLayout, QVBoxLayout, QFrame
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from modulos.aforo.widget_aforo import WidgetAforo
from modulos.clima.widget_temperatura import WidgetTemperatura
from modulos.luz.widget_luz import WidgetLuz
from modulos.hum_ca_aire.widget_hum_ca_aire import WidgetHumCaAire
from modulos.ruido.widget_ruido import WidgetRuido
from modulos.config_ambientes import AMBIENTES_CONFIG

# <-- NUEVO: Importamos tu archivo de conexión para poder cambiarle la sala
from modulos import supabase_client 

# ==========================================
# INICIO DEL SERVIDOR DE ESCUCHA (FLASK)
# ==========================================
server_app = Flask(__name__)
CORS(server_app)

@server_app.route('/set_context', methods=['GET', 'POST'])
def set_context():
    # Retornar la sala activa de la raspberry para consulta pasiva de la web/app
    return jsonify({"status": "success", "room_id": supabase_client.CURRENT_ROOM_ID}), 200

def iniciar_servidor_flask():
    # use_reloader=False es VITAL para que no congele tu interfaz gráfica
    server_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
# ==========================================
# FIN DEL SERVIDOR
# ==========================================

class PlaceholderWidget(QWidget):
    def __init__(self, titulo):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF; 
                border: 1px solid #D1D5DB; 
                border-radius: 6px;        
            }
            QLabel {
                border: none;
                color: #4B5563; 
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        layout_interno = QGridLayout()
        layout_interno.setContentsMargins(0, 0, 0, 0) 
        
        label = QLabel(titulo)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout_interno.addWidget(label)
        self.setLayout(layout_interno)


class DashboardHospital(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard - Módulo Hospitalario")
        self.setFixedSize(1024, 660) # Aumentamos la altura para acomodar el encabezado superior
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: #F3F4F6;")
        
        layout_principal = QVBoxLayout(central_widget)
        layout_principal.setContentsMargins(10, 10, 10, 10)
        layout_principal.setSpacing(10)
        
        # --- ENCABEZADO SUPERIOR PREMIUM (HEADER) ---
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
        """)
        header_frame.setFixedHeight(60)
        
        layout_header = QHBoxLayout(header_frame)
        layout_header.setContentsMargins(15, 0, 15, 0)
        
        # Título principal de la aplicación
        lbl_app_titulo = QLabel("HOSPITAL SMART MONITOR")
        font_titulo = QFont("Inter", 12)
        font_titulo.setBold(True)
        lbl_app_titulo.setFont(font_titulo)
        lbl_app_titulo.setStyleSheet("color: #1F2937; border: none; letter-spacing: 1px;")
        
        # Selector desplegable de cuartos (QComboBox)
        self.combo_sala = QComboBox()
        self.combo_sala.setFixedWidth(280)
        self.combo_sala.setStyleSheet("""
            QComboBox {
                background-color: #F9FAFB;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 12px;
                color: #374151;
                font-size: 13px;
                font-weight: bold;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                selection-background-color: #E5E7EB;
                selection-color: #1F2937;
                color: #374151;
            }
        """)
        
        # Llenar combobox con los cuartos disponibles
        self.mapeo_indice_sala = []
        for room_id, info in AMBIENTES_CONFIG.items():
            self.combo_sala.addItem(info['label'])
            self.mapeo_indice_sala.append(room_id)
            
        # Cargar cuarto inicial cargado de config.json
        sala_actual = supabase_client.CURRENT_ROOM_ID
        if sala_actual in self.mapeo_indice_sala:
            idx = self.mapeo_indice_sala.index(sala_actual)
            self.combo_sala.setCurrentIndex(idx)
            
        # Conectar evento de cambio de selección
        self.combo_sala.currentIndexChanged.connect(self._on_sala_seleccionada_cambiada)
        
        lbl_sala_titulo = QLabel("Ambiente:")
        font_label = QFont("Inter", 10)
        font_label.setBold(True)
        lbl_sala_titulo.setFont(font_label)
        lbl_sala_titulo.setStyleSheet("color: #4B5563; border: none;")
        
        layout_header.addWidget(lbl_app_titulo)
        layout_header.addStretch()
        layout_header.addWidget(lbl_sala_titulo)
        layout_header.addWidget(self.combo_sala)
        
        layout_principal.addWidget(header_frame)
        
        # --- CONTENEDOR GRID DE TARJETAS DE MONITOREO ---
        widget_grid = QWidget()
        layout_grid = QGridLayout(widget_grid)
        layout_grid.setSpacing(6)
        layout_grid.setContentsMargins(0, 0, 0, 0)
        
        self.mod_iluminacion = WidgetLuz()
        self.mod_ruido = WidgetRuido()
        self.mod_humedad_aire = WidgetHumCaAire()
        self.mod_temperatura = WidgetTemperatura()
        self.mod_personas = WidgetAforo()
        
        layout_grid.addWidget(self.mod_iluminacion, 0, 0, 2, 1)
        layout_grid.addWidget(self.mod_ruido, 0, 1, 1, 1)
        layout_grid.addWidget(self.mod_humedad_aire, 0, 2, 1, 1)
        layout_grid.addWidget(self.mod_temperatura, 1, 1, 1, 2)
        layout_grid.addWidget(self.mod_personas, 2, 0, 1, 3)
        
        layout_grid.setColumnStretch(0, 1) 
        layout_grid.setColumnStretch(1, 2) 
        layout_grid.setColumnStretch(2, 2) 
        
        layout_grid.setRowStretch(0, 3) 
        layout_grid.setRowStretch(1, 2) 
        layout_grid.setRowStretch(2, 2) 
        
        layout_principal.addWidget(widget_grid)

        # Inicializar y conectar almacenamiento de últimas lecturas
        self.ultimas_lecturas = {
            "temperature": None,
            "humidity": None,
            "noise_level": None,
            "light_level": None,
            "gas_level": None,
            "people_count": None
        }

        # Conectar señales para recolectar datos en tiempo real
        if hasattr(self.mod_temperatura, "sensor_thread"):
            self.mod_temperatura.sensor_thread.temperatura_cambiada.connect(self._actualizar_temp)
            self.mod_temperatura.sensor_thread.humedad_cambiada.connect(self._actualizar_hum)
            # Conectar la señal de humedad de temperatura para actualizar la tarjeta de humedad
            self.mod_temperatura.sensor_thread.humedad_cambiada.connect(self.mod_humedad_aire.panel_humedad.actualizar_target)
        
        if hasattr(self.mod_iluminacion, "worker"):
            self.mod_iluminacion.worker.datos_actualizados.connect(self._actualizar_luz)
            
        if hasattr(self.mod_ruido, "worker"):
            self.mod_ruido.worker.datos_actualizados.connect(self._actualizar_ruido)
            
        if hasattr(self.mod_humedad_aire.panel_humedad, "worker_ca"):
            self.mod_humedad_aire.panel_humedad.worker_ca.datos_actualizados.connect(self._actualizar_gas)
            
        if hasattr(self.mod_personas, "sensor_thread"):
            self.mod_personas.sensor_thread.aforo_cambiado.connect(self._actualizar_aforo)

        # Timer para sincronización unificada cada 10 segundos
        self.timer_supabase = QTimer(self)
        self.timer_supabase.timeout.connect(self._sincronizar_supabase)
        self.timer_supabase.start(10000) # 10 segundos

    def _actualizar_temp(self, val):
        self.ultimas_lecturas["temperature"] = float(val)

    def _actualizar_hum(self, val):
        self.ultimas_lecturas["humidity"] = float(val)

    def _actualizar_luz(self, val):
        self.ultimas_lecturas["light_level"] = float(val)

    def _actualizar_ruido(self, val):
        self.ultimas_lecturas["noise_level"] = float(val)

    def _actualizar_gas(self, val):
        self.ultimas_lecturas["gas_level"] = float(val)

    def _actualizar_aforo(self, val):
        self.ultimas_lecturas["people_count"] = int(val)

    def _on_sala_seleccionada_cambiada(self, index):
        if index < 0 or index >= len(self.mapeo_indice_sala):
            return
            
        nuevo_room_id = self.mapeo_indice_sala[index]
        
        # 1. Actualizar memoria en supabase_client
        supabase_client.actualizar_room_id(nuevo_room_id)
        
        # 2. Guardar en config.json para persistencia local
        dir_path = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(dir_path, "config.json")
        try:
            with open(config_file, "w") as f:
                json.dump({"room_id": nuevo_room_id}, f, indent=2)
            print(f"[Dashboard] Persistido room_id '{nuevo_room_id}' en config.json")
        except Exception as e:
            print(f"[Dashboard] Error al persistir config.json: {e}")
            
        # 3. Forzar sincronización Supabase inmediata con el nuevo room_id
        self._sincronizar_supabase()

    def _sincronizar_supabase(self):
        payload = self.ultimas_lecturas.copy()
        # Sincronizar solo si hay al menos un dato válido cargado
        if any(v is not None for v in payload.values()):
            supabase_client.enviar_lecturas_dict(payload)

    def closeEvent(self, event):
        if hasattr(self, 'mod_personas') and hasattr(self.mod_personas, 'closeEvent'):
            self.mod_personas.closeEvent(event)
        if hasattr(self, 'mod_temperatura') and hasattr(self.mod_temperatura, 'closeEvent'):
            self.mod_temperatura.closeEvent(event)
        if hasattr(self, 'mod_iluminacion') and hasattr(self.mod_iluminacion, 'closeEvent'):
            self.mod_iluminacion.closeEvent(event)
        if hasattr(self, 'mod_humedad_aire') and hasattr(self.mod_humedad_aire, 'closeEvent'):
            self.mod_humedad_aire.closeEvent(event)
        if hasattr(self, 'mod_ruido') and hasattr(self.mod_ruido, 'closeEvent'):
            self.mod_ruido.closeEvent(event)
        super().closeEvent(event)

if __name__ == "__main__":
    # ---> NUEVO: Encendemos el servidor en el fondo ANTES de mostrar la pantalla
    hilo_flask = threading.Thread(target=iniciar_servidor_flask)
    hilo_flask.daemon = True
    hilo_flask.start()
    print("Oído digital encendido en el puerto 5000...")

    app = QApplication(sys.argv)
    ventana = DashboardHospital()
    ventana.show()
    sys.exit(app.exec())