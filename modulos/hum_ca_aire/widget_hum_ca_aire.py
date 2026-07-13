import math
import random
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPainterPath, QFont, QPen, QBrush, QLinearGradient, QImage
)
import os

class SensorHumedadWorker(QThread):
    datos_actualizados = Signal(float)

    def __init__(self, simulacion=True):
        super().__init__()
        self.simulacion = simulacion
        self.corriendo = True
        self.valor_simulado = 50.0 

    def run(self):
        while self.corriendo:
            if self.simulacion:
                # Fluctúa drásticamente para poder probar todos los estados gráficos
                variacion = random.uniform(-20.0, 25.0) 
                self.valor_simulado += variacion
                
                # Rebote suave en los límites
                if self.valor_simulado > 100.0:
                    self.valor_simulado -= 40.0
                elif self.valor_simulado < 0.0:
                    self.valor_simulado += 30.0
                    
                self.datos_actualizados.emit(self.valor_simulado)
            
            self.msleep(2000)

    def detener(self):
        self.corriendo = False
        self.wait()


class SensorCalidadWorker(QThread):
    datos_actualizados = Signal(float)

    def __init__(self, simulacion=True):
        super().__init__()
        self.simulacion = simulacion
        self.corriendo = True
        self.valor_simulado = 50.0 

    def run(self):
        while self.corriendo:
            if self.simulacion:
                variacion = random.uniform(-15.0, 25.0) 
                self.valor_simulado += variacion
                if self.valor_simulado > 400.0:
                    self.valor_simulado -= 150.0
                elif self.valor_simulado < 0.0:
                    self.valor_simulado += 50.0
                self.datos_actualizados.emit(self.valor_simulado)
            self.msleep(2000)

    def detener(self):
        self.corriendo = False
        self.wait()


class PanelHumedad(QFrame):
    """
    Panel dinámico de Humedad tipo ventana realista.
    Simula condensación, gotas en 3D resbalando por el cristal, 
    y el efecto de un vidrio reluciente y limpio cuando está seco.
    """
    def __init__(self):
        super().__init__()
        self.target_valor = 50.0
        self.anim_valor = 50.0
        self.target_valor_ca = 50.0
        self.anim_valor_ca = 50.0
        self.gotas_agua = []
        
        # Cargar imagen de fondo si existe
        ruta_img = Path(__file__).parent / "fondo_paisaje.jpg"
        self.img_fondo = QImage(str(ruta_img)) if ruta_img.exists() else None
        
        # Iconos personalizados PNG
        base_path = Path(__file__).parent
        self.img_t_rojo = QImage(str(base_path / "termometro_rojo.png"))
        self.img_t_azul = QImage(str(base_path / "termometro_azul.png"))
        self.img_sol = QImage(str(base_path / "sol.png"))
        self.img_nube = QImage(str(base_path / "nube.png"))

        # Generar gotas de lluvia aleatorias
        for _ in range(80):
            self.gotas_agua.append({
                'x': random.uniform(0, 1),
                'y': random.uniform(-1.0, 1.0),
                'tam': random.uniform(4, 12),
                'vel': random.uniform(0.001, 0.006),
                'trail': random.uniform(10, 50)
            })
            
        self.worker = SensorHumedadWorker()
        self.worker.datos_actualizados.connect(self.actualizar_target)
        self.worker.start()

        self.worker_ca = SensorCalidadWorker()
        self.worker_ca.datos_actualizados.connect(self.actualizar_target_ca)
        self.worker_ca.start()
        
        self.timer_anim = QTimer(self)
        self.timer_anim.timeout.connect(self.animar)
        self.timer_anim.start(16)
        
    def actualizar_target(self, valor):
        self.target_valor = valor

    def actualizar_target_ca(self, valor):
        self.target_valor_ca = valor

    def animar(self):
        if not hasattr(self, 'target_valor'):
            return
            
        diff = self.target_valor - self.anim_valor
        if abs(diff) > 0.1:
            self.anim_valor += diff * 0.05
        else:
            self.anim_valor = self.target_valor
            
        diff_ca = self.target_valor_ca - self.anim_valor_ca
        if abs(diff_ca) > 0.1:
            self.anim_valor_ca += diff_ca * 0.05
        else:
            self.anim_valor_ca = self.target_valor_ca
            
        # Animación física de las gotas resbalando por el cristal
        porcentaje = min(1.0, max(0.0, self.anim_valor / 100.0))
        if porcentaje > 0.4:
            multiplicador = (porcentaje - 0.4) * 10
            for g in self.gotas_agua:
                # Las gotas grandes caen más rápido
                g['y'] += (g['vel'] * (g['tam']/4.0)) * multiplicador
                if g['y'] > 1.2:
                    g['y'] = random.uniform(-0.2, 0.0)
                    g['x'] = random.uniform(0, 1)
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        porcentaje = min(1.0, max(0.0, self.anim_valor / 100.0))
        
        # --- 1. PAISAJE DE FONDO (Detrás del cristal) ---
        if porcentaje < 0.4:
            color_top = QColor("#38BDF8")
            color_bot = QColor("#BAE6FD")
            opacidad_nubes = 0.0
        elif porcentaje < 0.7:
            f = (porcentaje - 0.4) / 0.3
            color_top = QColor(int(56 + (148-56)*f), int(189 + (163-189)*f), int(248 + (184-248)*f)) 
            color_bot = QColor(int(186 + (203-186)*f), int(230 + (213-230)*f), int(253 + (225-253)*f))
            opacidad_nubes = f
        else:
            f = (porcentaje - 0.7) / 0.3
            color_top = QColor(int(148 + (71-148)*f), int(163 + (85-163)*f), int(184 + (105-184)*f))
            color_bot = QColor(int(203 + (100-203)*f), int(213 + (116-213)*f), int(225 + (139-225)*f))
            opacidad_nubes = 1.0

        grad_cielo = QLinearGradient(0, 0, 0, h)
        grad_cielo.setColorAt(0.0, color_top)
        grad_cielo.setColorAt(1.0, color_bot)
        
        path_fondo = QPainterPath()
        path_fondo.addRoundedRect(0, 0, w, h, 12, 12)
        painter.setClipPath(path_fondo) 
        
        if self.img_fondo is not None and not self.img_fondo.isNull():
            painter.drawImage(QRectF(0, 0, w, h), self.img_fondo)
            if opacidad_nubes > 0:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 0, 0, int(150 * opacidad_nubes)))
                painter.drawRect(0, 0, w, h)
        else:
            painter.fillPath(path_fondo, QBrush(grad_cielo))
            
            if porcentaje < 0.6:
                f_sol = 1.0 - (porcentaje / 0.6)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(253, 224, 71, int(255 * f_sol))) 
                painter.drawEllipse(w * 0.15, h * 0.15, 60, 60)
                
            color_montana = QColor("#166534") 
            if opacidad_nubes > 0:
                r = int(22 + (30-22)*opacidad_nubes)
                g = int(101 + (41-101)*opacidad_nubes)
                b = int(52 + (59-52)*opacidad_nubes)
                color_montana = QColor(r, g, b)
                
            path_montana = QPainterPath()
            path_montana.moveTo(0, h)
            path_montana.lineTo(0, h * 0.6)
            path_montana.quadTo(w * 0.3, h * 0.4, w * 0.6, h * 0.6)
            path_montana.quadTo(w * 0.8, h * 0.7, w, h * 0.55)
            path_montana.lineTo(w, h)
            painter.fillPath(path_montana, QBrush(color_montana))

            color_mont_frente = QColor("#15803D")
            if opacidad_nubes > 0:
                r = int(21 + (15-21)*opacidad_nubes)
                g = int(128 + (23-128)*opacidad_nubes)
                b = int(61 + (42-61)*opacidad_nubes)
                color_mont_frente = QColor(r, g, b)

            path_montana2 = QPainterPath()
            path_montana2.moveTo(0, h)
            path_montana2.lineTo(0, h * 0.7)
            path_montana2.quadTo(w * 0.4, h * 0.5, w, h * 0.75)
            path_montana2.lineTo(w, h)
            painter.fillPath(path_montana2, QBrush(color_mont_frente))

        # --- 2. LA VENTANA Y SUS EFECTOS ---
        grosor_marco = 8
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(25, 30, 35)) 
        painter.drawRect(QRectF(w/2 - grosor_marco/2, 0, grosor_marco, h)) 
        painter.drawRect(QRectF(0, h/2 - grosor_marco/2, w, grosor_marco)) 

        if porcentaje > 0.3:
            f_niebla = min(1.0, (porcentaje - 0.3) / 0.7)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, int(150 * f_niebla)))
            painter.drawRect(0, 0, w, h)
            
            for g in self.gotas_agua:
                x = g['x'] * w
                y = g['y'] * h
                tam = g['tam']
                
                painter.setPen(QPen(QColor(255, 255, 255, int(80 * f_niebla)), tam * 0.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(int(x + tam/2), int(y), int(x + tam/2), int(y - g['trail']))
                
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 0, 0, int(100 * f_niebla)))
                painter.drawEllipse(QRectF(x + 1, y + 2, tam, tam * 1.3))
                
                grad_gota = QLinearGradient(x, y, x, y + tam * 1.3)
                grad_gota.setColorAt(0.0, QColor(0, 0, 0, int(120 * f_niebla))) 
                grad_gota.setColorAt(1.0, QColor(255, 255, 255, int(220 * f_niebla))) 
                painter.setBrush(grad_gota)
                painter.drawEllipse(QRectF(x, y, tam, tam * 1.3))
                
                painter.setBrush(QColor(255, 255, 255, int(255 * f_niebla)))
                painter.drawEllipse(QRectF(x + tam*0.25, y + tam*0.15, tam*0.3, tam*0.35))

        if porcentaje < 0.4:
            f_brillo = 1.0 - (porcentaje / 0.4)
            painter.setPen(Qt.PenStyle.NoPen)
            
            path_brillo1 = QPainterPath()
            path_brillo1.moveTo(w*0.1, 0)
            path_brillo1.lineTo(w*0.35, 0)
            path_brillo1.lineTo(w*0.05, h)
            path_brillo1.lineTo(-w*0.2, h)
            painter.fillPath(path_brillo1, QColor(255, 255, 255, int(40 * f_brillo)))
            
            path_brillo2 = QPainterPath()
            path_brillo2.moveTo(w*0.4, 0)
            path_brillo2.lineTo(w*0.45, 0)
            path_brillo2.lineTo(w*0.15, h)
            path_brillo2.lineTo(w*0.1, h)
            painter.fillPath(path_brillo2, QColor(255, 255, 255, int(25 * f_brillo)))

        # --- 3. INTERFAZ DE HUMEDAD HUD ---
        margin_x = 25
        margin_der = 100  # Espacio para el panel derecho de calidad de aire
        
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        rect_titulo = QRectF(w - margin_der - 215, 15, 200, 30)
        painter.setPen(QColor(0, 0, 0, 200)) 
        painter.drawText(rect_titulo.translated(1, 1), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, "HUMEDAD")
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect_titulo, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, "HUMEDAD")

        # BARRA DESLIZADORA HUMEDAD
        y_barra = h * 0.85
        ancho_barra = w - margin_x - margin_der
        start_x = margin_x
        
        color_linea = QColor(14, 165, 233) if porcentaje < 0.5 else QColor(30, 58, 138)
        
        painter.setPen(QPen(color_linea, 3))
        painter.drawLine(int(start_x), int(y_barra), int(start_x + ancho_barra), int(y_barra))
        
        painter.drawLine(int(start_x), int(y_barra - 8), int(start_x), int(y_barra + 8))
        painter.drawLine(int(start_x + ancho_barra), int(y_barra - 8), int(start_x + ancho_barra), int(y_barra + 8))
        
        x_actual = start_x + (ancho_barra * porcentaje)
        
        r = 8.0
        cy = y_barra + 2.0
        cx = x_actual
        punta_y = y_barra - 14.0
        
        path_gota = QPainterPath()
        path_gota.moveTo(cx, punta_y)
        path_gota.cubicTo(cx + r + 2, punta_y + 4, cx + r, cy + r, cx, cy + r)
        path_gota.cubicTo(cx - r, cy + r, cx - r - 2, punta_y + 4, cx, punta_y)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawPath(path_gota)
        painter.setPen(QPen(color_linea, 2))
        painter.drawPath(path_gota)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(14, 165, 233, 100) if porcentaje < 0.5 else QColor(30, 58, 138, 100))
        painter.drawEllipse(QRectF(cx - 3, cy - 1, 6, 6))
        
        texto_val = f"{int(self.anim_valor)}%"
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        rect_texto = QRectF(x_actual - 30, y_barra + 14, 60, 30)
        
        painter.setPen(QColor(0, 0, 0, 200)) 
        for dx, dy in [(1,1), (-1,-1), (1,-1), (-1,1), (0,2)]:
            painter.drawText(rect_texto.translated(dx, dy), Qt.AlignmentFlag.AlignCenter, texto_val)
        
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect_texto, Qt.AlignmentFlag.AlignCenter, texto_val)
        
        # ICONOS PNG O EMOJIS (Humedad)
        painter.setFont(QFont("Segoe UI Emoji", 24))
        
        # Top-Left (Termómetro rojo + Sol)
        rect_t_izq = QRectF(15, 15, 40, 40)
        rect_sol = QRectF(50, 15, 40, 40)
        if self.img_t_rojo.isNull():
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect_t_izq, Qt.AlignmentFlag.AlignCenter, "🌡️")
        else:
            painter.drawImage(rect_t_izq, self.img_t_rojo)
            
        if self.img_sol.isNull():
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect_sol, Qt.AlignmentFlag.AlignCenter, "☀️")
        else:
            painter.drawImage(rect_sol, self.img_sol)
            
        # Bottom-Right (Termómetro azul + Nube) Ajustado a la izquierda por el panel AQI
        rect_t_der = QRectF(w - margin_der - 75, y_barra - 45, 40, 40)
        rect_nube = QRectF(w - margin_der - 40, y_barra - 45, 40, 40)
        if self.img_t_azul.isNull():
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect_t_der, Qt.AlignmentFlag.AlignCenter, "🌡️")
        else:
            painter.drawImage(rect_t_der, self.img_t_azul)
            
        if self.img_nube.isNull():
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect_nube, Qt.AlignmentFlag.AlignCenter, "🌧️")
        else:
            painter.drawImage(rect_nube, self.img_nube)

        # --- 4. INTERFAZ DE CALIDAD DE AIRE (Derecha) ---
        aqi = int(self.anim_valor_ca)
        if aqi <= 50:
            estado_ca = "Bueno"
            color_ca = QColor(34, 197, 94)  # Verde
            icono_ca = "🍃"
        elif aqi <= 100:
            estado_ca = "Moderado"
            color_ca = QColor(234, 179, 8)  # Amarillo
            icono_ca = "☁️"
        elif aqi <= 300:
            estado_ca = "Malo"
            color_ca = QColor(249, 115, 22)  # Naranja
            icono_ca = "🌫️"
        else:
            estado_ca = "Crítico"
            color_ca = QColor(220, 38, 38)   # Rojo
            icono_ca = "☣️"

        # Título Calidad
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        rect_tit_ca = QRectF(w - 90, 15, 80, 40)
        painter.setPen(QColor(0, 0, 0, 200))
        painter.drawText(rect_tit_ca.translated(1, 1), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "CALIDAD\nAIRE")
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect_tit_ca, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "CALIDAD\nAIRE")

        # Barra Vertical
        x_barra_v = w - 50
        y_start_v = 65
        y_end_v = h - 60
        alto_barra = y_end_v - y_start_v
        
        painter.setPen(QPen(QColor(255, 255, 255, 50), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(x_barra_v), int(y_start_v), int(x_barra_v), int(y_end_v))
        
        f_aqi = min(1.0, max(0.0, aqi / 500.0))
        y_actual_v = y_end_v - (alto_barra * f_aqi)
        
        painter.setPen(QPen(color_ca, 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(x_barra_v), int(y_actual_v), int(x_barra_v), int(y_end_v))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(QRectF(x_barra_v - 8, y_actual_v - 8, 16, 16))
        painter.setBrush(color_ca)
        painter.drawEllipse(QRectF(x_barra_v - 5, y_actual_v - 5, 10, 10))
        
        # Valor AQI
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        rect_val_ca = QRectF(w - 90, y_end_v + 10, 80, 25)
        painter.setPen(QColor(0, 0, 0, 200))
        painter.drawText(rect_val_ca.translated(1, 1), Qt.AlignmentFlag.AlignHCenter, f"{aqi} AQI")
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect_val_ca, Qt.AlignmentFlag.AlignHCenter, f"{aqi} AQI")

        # Estado
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        rect_est_ca = QRectF(w - 90, y_end_v + 35, 80, 20)
        painter.setPen(QColor(0, 0, 0, 200))
        painter.drawText(rect_est_ca.translated(1, 1), Qt.AlignmentFlag.AlignHCenter, estado_ca)
        painter.setPen(color_ca)
        painter.drawText(rect_est_ca, Qt.AlignmentFlag.AlignHCenter, estado_ca)
        
        # EMOJI dinámico
        painter.setFont(QFont("Segoe UI Emoji", 24))
        painter.setPen(QColor(0, 0, 0, 150))
        painter.drawText(QRectF(x_barra_v - 20, y_actual_v - 45, 40, 40).translated(1, 1), Qt.AlignmentFlag.AlignCenter, icono_ca)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(x_barra_v - 20, y_actual_v - 45, 40, 40), Qt.AlignmentFlag.AlignCenter, icono_ca)


    def closeEvent(self, event):
        self.worker.detener()
        self.worker_ca.detener()
        super().closeEvent(event)


class WidgetHumCaAire(QWidget):
    """
    Contenedor principal para la celda de 'Superior Derecho'.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.panel_humedad = PanelHumedad()
        layout.addWidget(self.panel_humedad)

    def closeEvent(self, event):
        self.panel_humedad.closeEvent(event)
        super().closeEvent(event)
