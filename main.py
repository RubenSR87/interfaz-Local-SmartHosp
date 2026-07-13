import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLabel
from PySide6.QtCore import Qt
from modulos.aforo.widget_aforo import WidgetAforo

class PlaceholderWidget(QWidget):
    def __init__(self, titulo):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF; 
                border: 1px solid #D1D5DB; /* Borde sutil */
                border-radius: 6px;        /* Curva ligeramente más fina */
            }
            QLabel {
                border: none;
                color: #4B5563; 
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        layout_interno = QGridLayout()
        
        # --- EL SECRETO PARA MAXIMIZAR EL ESPACIO INTERNO ---
        # Esto elimina el "relleno" invisible dentro del cuadro.
        # Si luego necesitas que tus iconos no toquen el borde, 
        # le puedes poner (4, 4, 4, 4) por ejemplo.
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
        
        # --- REDUCCIÓN EXTREMA DE MARCOS EXTERIORES ---
        # Separación entre los cuadros (4 píxeles)
        layout_grid.setSpacing(4)  
        # Margen contra los bordes de la pantalla (4 píxeles)
        layout_grid.setContentsMargins(4, 4, 4, 4) 
        
        self.mod_iluminacion = PlaceholderWidget("Iluminación\n(Lateral Izquierda)")
        self.mod_ruido = PlaceholderWidget("Ruido\n(Superior Central)")
        self.mod_humedad_aire = PlaceholderWidget("Humedad y Aire\n(Superior Derecho)")
        self.mod_temperatura = PlaceholderWidget("Temperatura\n(Central Inferior)")
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
        # Asegurar la correcta finalización de hilos en los widgets hijos
        if hasattr(self, 'mod_personas') and hasattr(self.mod_personas, 'closeEvent'):
            self.mod_personas.closeEvent(event)
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = DashboardHospital()
    ventana.show()
    sys.exit(app.exec())