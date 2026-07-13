import sys
import random
import math
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPainterPath, QFont, QRadialGradient, QBrush, QLinearGradient, QPen
)
from modulos.supabase_client import enviar_lectura

class SensorLuzWorker(QThread):
    datos_actualizados = Signal(float)

    def __init__(self, simulacion=True):
        super().__init__()
        self.simulacion = simulacion
        self.corriendo = True
        self.sensor = None
        
        if not self.simulacion:
            try:
                import board
                import adafruit_bh1750
                i2c = board.I2C()
                self.sensor = adafruit_bh1750.BH1750(i2c)
            except Exception as e:
                print(f"Error al inicializar sensor de luz real, pasando a simulación: {e}")
                self.simulacion = True
                
        self.valor_simulado = 0.0 

    def run(self):
        while self.corriendo:
            if self.simulacion:
                variacion = random.uniform(-150.0, 200.0) 
                self.valor_simulado += variacion
                
                if self.valor_simulado > 1000.0:
                    self.valor_simulado -= 400.0
                if self.valor_simulado < 0.0:
                    self.valor_simulado += 300.0
                    
                self.datos_actualizados.emit(self.valor_simulado)
                print(f"[Sensor Luz] Simulación - Lux: {self.valor_simulado:.1f}")
                enviar_lectura("lux", self.valor_simulado)
            else:
                try:
                    nivel_luz = self.sensor.lux
                    self.datos_actualizados.emit(nivel_luz)
                    print(f"[Sensor Luz] Real - Lux: {nivel_luz:.1f}")
                    enviar_lectura("lux", nivel_luz)
                except Exception as e:
                    print(f"Error leyendo sensor de luz: {e}")
            
            self.msleep(2500)

    def detener(self):
        self.corriendo = False
        self.wait()


class WidgetLuz(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_lux = 0.0
        self.anim_lux = 0.0
        self.max_lux = 1000.0
        
        self.rotacion_rayos = 0.0
        self.estrellas = [] 
        
        # --- UI LAYOUT ESTRUCTURADO ---
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(15, 15, 15, 15)
        
        # 1. PARTE SUPERIOR: Títulos ordenados con márgenes
        layout_titulos = QVBoxLayout()
        layout_titulos.setSpacing(2)
        
        self.lbl_titulo = QLabel("ILUMINACIÓN")
        self.lbl_titulo.setStyleSheet("color: #7f8c8d; font-size: 11px; font-weight: bold; background: transparent; letter-spacing: 1px;")
        
        self.lbl_subtitulo = QLabel("Nivel de luz ambiental")
        self.lbl_subtitulo.setStyleSheet("color: rgba(127, 140, 141, 0.7); font-size: 10px; background: transparent;")
        
        layout_titulos.addWidget(self.lbl_titulo)
        layout_titulos.addWidget(self.lbl_subtitulo)
        
        layout_principal.addLayout(layout_titulos)
        layout_principal.addStretch()
        
        self.estado_str = "Oscuro"

        # --- LÓGICA ANIMACIÓN ---
        self.timer_anim = QTimer(self)
        self.timer_anim.timeout.connect(self.animar)
        self.timer_anim.start(16) 

        self.worker = SensorLuzWorker(simulacion=False)
        self.worker.datos_actualizados.connect(self.set_lux)
        self.worker.start()

    def set_lux(self, lux):
        self.target_lux = lux

    def animar(self):
        diff = self.target_lux - self.anim_lux
        if abs(diff) > 0.5:
            self.anim_lux += diff * 0.05
        else:
            self.anim_lux = self.target_lux
            
        self.rotacion_rayos += 0.5
        if self.rotacion_rayos >= 360:
            self.rotacion_rayos = 0.0
            
        porcentaje = self.anim_lux / self.max_lux
        is_day = porcentaje >= 0.5
        
        # Generar estrellas
        if not is_day:
            probabilidad = (0.5 - porcentaje) * 0.4
            if random.random() < probabilidad:
                self.estrellas.append({
                    'x': random.uniform(0, 1),
                    'y': random.uniform(0, 1),
                    'vida': 1.0,
                    'tam': random.uniform(1.5, 4),
                    'vel': random.uniform(0.001, 0.003)
                })
        else:
            if porcentaje > 0.8 and random.random() < 0.05:
                self.estrellas.append({
                    'x': random.uniform(0, 1),
                    'y': random.uniform(0, 1),
                    'vida': 1.0,
                    'tam': random.uniform(2, 5),
                    'vel': random.uniform(0.005, 0.01)
                })
                
        for e in self.estrellas:
            e['y'] -= e['vel'] 
            e['vida'] -= 0.01
        
        self.estrellas = [e for e in self.estrellas if e['vida'] > 0]
        
        if is_day:
            if self.anim_lux > 700:
                estado = "Luz intensa"
            else:
                estado = "Luz adecuada"
        else:
            if self.anim_lux < 200:
                estado = "Muy oscuro"
            else:
                estado = "Luz baja"
                
        self.estado_str = estado
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        
        porcentaje = min(1.0, max(0.0, self.anim_lux / self.max_lux))
        is_day = porcentaje >= 0.5
        
        # 1. FONDO COMPLETO (Blanco)
        color_fondo = QColor(255, 255, 255)
        
        path_fondo_widget = QPainterPath()
        path_fondo_widget.addRoundedRect(QRectF(0, 0, w, h), 8, 8)
        painter.fillPath(path_fondo_widget, color_fondo)
        
        painter.setPen(QPen(QColor(0, 0, 0, 30), 1))
        painter.drawPath(path_fondo_widget)
        
        # 2. ESTRELLAS GLOBALES
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setClipPath(path_fondo_widget)
        for e in self.estrellas:
            alpha = int(255 * e['vida'])
            painter.setBrush(QColor(0, 0, 0, alpha // 3))
            painter.drawEllipse(QRectF(e['x'] * w, e['y'] * h, e['tam'], e['tam']))
        painter.setClipping(False)

        # 3. EL VASO
        w_vaso = w * 0.35
        if w_vaso > 100: w_vaso = 100
        if w_vaso < 40: w_vaso = 40
        h_vaso = h - 100 
        x_vaso = 25
        y_vaso = 75
        
        path_vaso = QPainterPath()
        radio_vaso = w_vaso / 2.0
        path_vaso.addRoundedRect(QRectF(x_vaso, y_vaso, w_vaso, h_vaso), radio_vaso, radio_vaso)
        
        painter.fillPath(path_vaso, QColor(0, 0, 0, 15))
        
        alto_agua = h_vaso * porcentaje
        y_agua = y_vaso + h_vaso - alto_agua
        
        path_agua_rect = QPainterPath()
        path_agua_rect.addRect(QRectF(x_vaso, y_agua, w_vaso, alto_agua))
        path_agua = path_vaso.intersected(path_agua_rect)
        
        if is_day:
            c_agua_top = QColor(250, 204, 21, 240)
            c_agua_bot = QColor(234, 179, 8, 220)
        else:
            c_agua_top = QColor(14, 165, 233, 240)
            c_agua_bot = QColor(2, 132, 199, 220)
            
        grad_agua = QLinearGradient(0, y_agua, 0, y_vaso + h_vaso)
        grad_agua.setColorAt(0.0, c_agua_top)
        grad_agua.setColorAt(1.0, c_agua_bot)
        painter.fillPath(path_agua, QBrush(grad_agua))
        
        painter.setPen(QPen(QColor(0, 0, 0, 50), 2))
        painter.drawPath(path_vaso)

        # 4. SOL / LUNA
        radio_base = w * 0.12
        if radio_base < 25: radio_base = 25
        if radio_base > 40: radio_base = 40
        
        # El indicador crece drásticamente conforme aumenta la luz (+25px de radio máximo)
        radio_ind = radio_base + (porcentaje * 25)
        
        x_ind = w * 0.65
            
        min_y = y_vaso + radio_ind
        max_y = y_vaso + h_vaso - radio_ind
        y_ind = max_y - (max_y - min_y) * porcentaje
        
        painter.setPen(Qt.PenStyle.NoPen)
        
        if is_day:
            f_dia = (porcentaje - 0.5) * 2.0 
            
            # Color del sol pasa de amarillo-naranja a blanco incandescente
            r_sol = 255
            g_sol = int(204 + (51 * f_dia)) 
            b_sol = int(21 + (234 * f_dia)) 
            color_cuerpo_sol = QColor(r_sol, g_sol, b_sol)
            
            color_rayos = QColor(255, 255, 255, int(150 + (105 * f_dia)))
            
            grad_glow = QRadialGradient(x_ind, y_ind, radio_ind * 2.5)
            grad_glow.setColorAt(0.0, QColor(255, 255, 255, int(150 + 105*f_dia)))
            grad_glow.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(grad_glow))
            painter.drawEllipse(QRectF(x_ind - radio_ind*2.5, y_ind - radio_ind*2.5, radio_ind*5, radio_ind*5))
            
            painter.setPen(QPen(color_rayos, max(2, int(3 + f_dia*2)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            num_rayos = 10 + int(f_dia * 4) # Más rayos al mediodía
            largo_rayo = radio_ind * (0.6 + f_dia*0.2)
            for i in range(num_rayos):
                angulo = math.radians(i * (360 / num_rayos) + self.rotacion_rayos)
                x_ini = x_ind + math.cos(angulo) * (radio_ind + 5)
                y_ini = y_ind + math.sin(angulo) * (radio_ind + 5)
                x_fin = x_ind + math.cos(angulo) * (radio_ind + 5 + largo_rayo)
                y_fin = y_ind + math.sin(angulo) * (radio_ind + 5 + largo_rayo)
                painter.drawLine(int(x_ini), int(y_ini), int(x_fin), int(y_fin))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color_cuerpo_sol)
            painter.drawEllipse(QRectF(x_ind - radio_ind, y_ind - radio_ind, radio_ind*2, radio_ind*2))
            
        else:
            color_luna = QColor(30, 41, 59) # Luna oscura para que contraste con el fondo blanco
            
            grad_glow = QRadialGradient(x_ind, y_ind, radio_ind * 2.5)
            grad_glow.setColorAt(0.0, QColor(30, 41, 59, 80))
            grad_glow.setColorAt(1.0, QColor(30, 41, 59, 0))
            painter.setBrush(QBrush(grad_glow))
            painter.drawEllipse(QRectF(x_ind - radio_ind*2.5, y_ind - radio_ind*2.5, radio_ind*5, radio_ind*5))
            
            path_luna = QPainterPath()
            path_luna.addEllipse(QRectF(x_ind - radio_ind, y_ind - radio_ind, radio_ind*2, radio_ind*2))
            
            f_noche = porcentaje * 2.0 
            offset_x = radio_ind * 0.4 + (radio_ind * 1.5 * (1.0 - f_noche))
            path_sombra = QPainterPath()
            path_sombra.addEllipse(QRectF(x_ind - radio_ind + offset_x, y_ind - radio_ind - radio_ind*0.2, radio_ind*2, radio_ind*2))
            
            path_creciente = path_luna.subtracted(path_sombra)
            
            painter.setBrush(color_luna)
            painter.drawPath(path_creciente)

        # 5. TEXTO LUX DENTRO DEL INDICADOR
        fuente_num = QFont("Segoe UI", 14, QFont.Weight.Bold)
        if radio_ind > 35:
            fuente_num = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(fuente_num)
        
        texto_completo = f"{int(self.anim_lux)}\nlux"
        rect_texto = QRectF(x_ind - radio_ind*1.5, y_ind - radio_ind, radio_ind*3, radio_ind*2)

        # Sombras fuertes para garantizar que resalte
        painter.setPen(QColor(0, 0, 0, 200))
        for dx, dy in [(1,1), (-1,-1), (1,-1), (-1,1), (0,2)]:
            painter.drawText(rect_texto.translated(dx, dy), Qt.AlignmentFlag.AlignCenter, texto_completo)
            
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect_texto, Qt.AlignmentFlag.AlignCenter, texto_completo)

        # 6. ESTADO EN UN CUADRO CON COLOR DINÁMICO
        r_b = int(30 + (245 - 30) * porcentaje)
        g_b = int(41 + (158 - 41) * porcentaje)
        b_b = int(59 + (11 - 59) * porcentaje)
        badge_bg = QColor(r_b, g_b, b_b)
        
        if porcentaje < 0.5:
            text_color = QColor(255, 255, 255)
        else:
            text_color = QColor(0, 0, 0)
            
        painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        fm = painter.fontMetrics()
        ancho_texto = fm.horizontalAdvance(self.estado_str)
        alto_texto = 28
        
        # Centrar el badge respecto al indicador de Sol/Luna (x_ind)
        x_badge = x_ind - (ancho_texto + 24) / 2.0
        
        # Asegurar que el badge no se salga por el borde derecho
        if x_badge + ancho_texto + 24 > w - 10:
            x_badge = w - (ancho_texto + 24) - 10
            
        rect_badge = QRectF(x_badge, h - alto_texto - 15, ancho_texto + 24, alto_texto)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(badge_bg)
        painter.drawRoundedRect(rect_badge, alto_texto/2.0, alto_texto/2.0)
        
        painter.setPen(text_color)
        painter.drawText(rect_badge, Qt.AlignmentFlag.AlignCenter, self.estado_str)

    def closeEvent(self, event):
        self.worker.detener()
        super().closeEvent(event)
