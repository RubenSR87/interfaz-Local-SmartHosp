import math
import random
from pathlib import Path
from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPainterPath, QFont, QPen, QBrush, QLinearGradient, QImage

class SensorRuidoWorker(QThread):
    datos_actualizados = Signal(float)

    def __init__(self, simulacion=True):
        super().__init__()
        self.simulacion = simulacion
        self.corriendo = True
        self.valor_simulado = 40.0 

    def run(self):
        while self.corriendo:
            if self.simulacion:
                # Simular dB de 35 a 105
                variacion = random.uniform(-15.0, 25.0) 
                self.valor_simulado += variacion
                if self.valor_simulado > 110.0:
                    self.valor_simulado -= 40.0
                elif self.valor_simulado < 35.0:
                    self.valor_simulado += 20.0
                self.datos_actualizados.emit(self.valor_simulado)
            self.msleep(1500)

    def detener(self):
        self.corriendo = False
        self.wait()

class WidgetRuido(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0F172A; border-radius: 12px;")
        
        self.target_valor = 40.0
        self.anim_valor = 40.0
        self.fase_onda = 0.0
        
        # Cargar iconos PNG si existen
        base_path = Path(__file__).parent / "img"
        base_path.mkdir(parents=True, exist_ok=True)
        self.img_silencioso = QImage(str(base_path / "silencioso.png"))
        self.img_moderado = QImage(str(base_path / "moderado.png"))
        self.img_alto = QImage(str(base_path / "alto.png"))
        self.img_critico = QImage(str(base_path / "critico.png"))
        
        self.worker = SensorRuidoWorker()
        self.worker.datos_actualizados.connect(self.actualizar_target)
        self.worker.start()
        
        self.timer_anim = QTimer(self)
        self.timer_anim.timeout.connect(self.animar)
        self.timer_anim.start(16)
        
    def actualizar_target(self, valor):
        self.target_valor = valor

    def animar(self):
        diff = self.target_valor - self.anim_valor
        if abs(diff) > 0.1:
            self.anim_valor += diff * 0.05
        else:
            self.anim_valor = self.target_valor
            
        # Velocidad de la onda proporcional al volumen
        velocidad = 0.1 + (self.anim_valor / 100.0) * 0.3
        self.fase_onda += velocidad
        if self.fase_onda > math.pi * 2:
            self.fase_onda -= math.pi * 2
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Limitar dB de 30 a 110 para cálculos visuales
        db_visual = min(110.0, max(30.0, self.anim_valor))
        f_ruido = (db_visual - 30.0) / 80.0  # 0.0 a 1.0
        
        if self.anim_valor < 50:
            estado = "Silencioso"
            color_base = QColor(34, 197, 94) # Verde
            emoji = "🤫"
            img = self.img_silencioso
        elif self.anim_valor < 70:
            estado = "Moderado"
            color_base = QColor(234, 179, 8) # Amarillo
            emoji = "😶"
            img = self.img_moderado
        elif self.anim_valor < 90:
            estado = "Alto"
            color_base = QColor(249, 115, 22) # Naranja
            emoji = "🗣️"
            img = self.img_alto
        else:
            estado = "Crítico"
            color_base = QColor(220, 38, 38) # Rojo
            emoji = "📢"
            img = self.img_critico
            
        # 1. Dibujar el fondo con un gradiente sutil
        grad_fondo = QLinearGradient(0, 0, 0, h)
        grad_fondo.setColorAt(0.0, QColor(15, 23, 42))
        grad_fondo.setColorAt(1.0, QColor(2, 6, 23))
        
        path_fondo = QPainterPath()
        path_fondo.addRoundedRect(0, 0, w, h, 12, 12)
        painter.fillPath(path_fondo, grad_fondo)
        
        # 2. Dibujar ONDAS DE SONIDO (Centro)
        amplitud = 5 + (f_ruido * (h * 0.3)) # La onda crece con el ruido
        frecuencia = 2 + (f_ruido * 4)       # Más ondas si hay más ruido
        
        margin_der = 80
        ancho_onda = w - margin_der
        centro_y = h / 2
        
        # Dibujar 3 líneas de ondas superpuestas para efecto
        for i, opacidad in enumerate([100, 150, 255]):
            path_onda = QPainterPath()
            path_onda.moveTo(0, centro_y)
            
            fase_offset = self.fase_onda * (i + 1) * 0.5
            amp_actual = amplitud * (0.5 + i * 0.25)
            
            for x in range(0, int(ancho_onda), 2):
                y = centro_y + math.sin((x / ancho_onda) * math.pi * frecuencia + fase_offset) * amp_actual
                # Atenuar los bordes de la onda para que nazca y muera suavemente
                f_atenuacion = math.sin((x / ancho_onda) * math.pi)
                y = centro_y + (y - centro_y) * f_atenuacion
                path_onda.lineTo(x, y)
                
            pen_onda = QPen(color_base, 2 + i)
            color_pen = color_base
            color_pen.setAlpha(opacidad)
            pen_onda.setColor(color_pen)
            painter.setPen(pen_onda)
            painter.drawPath(path_onda)
            
        # 3. TÍTULO
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        rect_titulo = QRectF(20, 15, 250, 30)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect_titulo, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "RUIDO AMBIENTAL")

        # 4. TEXTOS (Valor y Estado) abajo
        painter.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        rect_val = QRectF(20, h - 70, 150, 50)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect_val, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, f"{int(self.anim_valor)} dB")
        
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        rect_est = QRectF(150, h - 60, 150, 30)
        painter.setPen(color_base)
        painter.drawText(rect_est, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, estado)

        # 5. BARRA VERTICAL (Derecha)
        x_barra = w - 40
        y_start = 50
        y_end = h - 50
        alto_barra = y_end - y_start
        
        painter.setPen(QPen(QColor(255, 255, 255, 30), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(x_barra), int(y_start), int(x_barra), int(y_end))
        
        y_progreso = y_end - (alto_barra * f_ruido)
        
        painter.setPen(QPen(color_base, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(x_barra), int(y_progreso), int(x_barra), int(y_end))
        
        # 6. ICONO (Dinámico, pegado a la barra)
        rect_icono = QRectF(w - 60, y_progreso - 20, 40, 40)
        if img.isNull():
            painter.setFont(QFont("Segoe UI Emoji", 24))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect_icono, Qt.AlignmentFlag.AlignCenter, emoji)
        else:
            painter.drawImage(rect_icono, img)

    def closeEvent(self, event):
        self.worker.detener()
        super().closeEvent(event)
