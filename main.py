import sys
import threading # <-- NUEVO: Para correr tareas en el fondo
from flask import Flask, request, jsonify # <-- NUEVO: El servidor web
from flask_cors import CORS # <-- NUEVO: Seguridad de conexión

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLabel
from PySide6.QtCore import Qt

from modulos.aforo.widget_aforo import WidgetAforo
from modulos.clima.widget_temperatura import WidgetTemperatura
from modulos.luz.widget_luz import WidgetLuz
from modulos.hum_ca_aire.widget_hum_ca_aire import WidgetHumCaAire
from modulos.ruido.widget_ruido import WidgetRuido

# <-- NUEVO: Importamos tu archivo de conexión para poder cambiarle la sala
from modulos import supabase_client 

# ==========================================
# INICIO DEL SERVIDOR DE ESCUCHA (FLASK)
# ==========================================
server_app = Flask(__name__)
CORS(server_app)

@server_app.route('/set_context', methods=['POST'])
def set_context():
    data = request.json
    if data and 'room_id' in data:
        nuevo_cuarto = data['room_id']
        
        # Le cambiamos la variable a tu archivo supabase_client
        supabase_client.CURRENT_ROOM_ID = nuevo_cuarto
        
        print(f"\n📡 ¡ORDEN RECIBIDA DESDE LA APP! Cambiando a sala: {nuevo_cuarto}\n")
        return jsonify({"status": "success", "room_id": nuevo_cuarto}), 200
        
    return jsonify({"status": "error", "message": "Falta el room_id"}), 400

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
        self.setFixedSize(1024, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: #F3F4F6;")
        
        layout_grid = QGridLayout(central_widget)
        
        layout_grid.setSpacing(4)  
        layout_grid.setContentsMargins(4, 4, 4, 4) 
        
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