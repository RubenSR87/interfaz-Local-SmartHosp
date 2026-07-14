import math
import random
from pathlib import Path
from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPainterPath, QFont, QPen, QBrush, QLinearGradient, QImage
from modulos.supabase_client import enviar_lectura

class SensorRuidoWorker(QThread):
    datos_actualizados = Signal(float)

    def __init__(self, simulacion=True):
        super().__init__()
        self.simulacion = simulacion
        self.corriendo = True
        self.stream = None
        self.audio_buffer = []
        
        if not self.simulacion:
            try:
                import sounddevice as sd
                import numpy as np
                
                def callback_audio(indata, frames, time_info, status):
                    rms = np.sqrt(np.mean(indata**2))
                    self.audio_buffer.append(rms)
                
                self.stream = sd.InputStream(channels=1, samplerate=48000, callback=callback_audio)
                self.stream.start()
                print("[Ruido] Sensor de micrófono real iniciado.")
            except Exception as e:
                print(f"[Ruido] Error iniciando micrófono: {e}. Usando simulación.")
                self.simulacion = True
                
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
                print(f"[Sensor Ruido] Simulación - Nivel: {self.valor_simulado:.1f} dB")
                self.msleep(1500)
            else:
                import numpy as np
                if self.audio_buffer:
                    promedio_rms = np.mean(self.audio_buffer)
                    self.audio_buffer.clear()
                    if promedio_rms > 0:
                        db_spl = 20 * np.log10(promedio_rms) + 115
                    else:
                        db_spl = 0.0
                    self.datos_actualizados.emit(float(db_spl))
                    print(f"[Sensor Ruido] Real - Nivel: {db_spl:.1f} dB")
                self.msleep(1500)

    def detener(self):
        self.corriendo = False
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
        self.wait()

class WidgetRuido(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #FFFFFF; border-radius: 12px;")
        
        self.target_valor = 40.0
        self.anim_valor = 40.0
        self.fase_onda = 0.0
        
        self.fase_onda = 0.0
        
        # Cargar imagen de megafono provista por el usuario
        base_path = Path(__file__).parent / "img"
        base_path.mkdir(parents=True, exist_ok=True)
        self.img_megafono = QImage(str(base_path / "megafono.png"))
        
        self.worker = SensorRuidoWorker(simulacion=False)
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
        elif self.anim_valor < 70:
            estado = "Moderado"
            color_base = QColor(234, 179, 8) # Amarillo
            emoji = "😶"
        elif self.anim_valor < 90:
            estado = "Alto"
            color_base = QColor(249, 115, 22) # Naranja
            emoji = "🗣️"
        else:
            estado = "Crítico"
            color_base = QColor(220, 38, 38) # Rojo
            emoji = "📢"
            
        # 1. Dibujar el fondo blanco con borde y sombra suave
        path_fondo = QPainterPath()
        path_fondo.addRoundedRect(2, 2, w - 4, h - 4, 16, 16)
        
        # Sombra simulada muy sutil
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 10))
        painter.drawRoundedRect(4, 4, w - 4, h - 4, 16, 16)
        
        # Fondo blanco
        painter.fillPath(path_fondo, QColor(255, 255, 255))
        
        # Borde ultra fino
        painter.setPen(QPen(QColor(229, 231, 235), 1))
        painter.drawPath(path_fondo)
        
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
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        rect_titulo = QRectF(20, 15, 250, 20)
        painter.setPen(QColor(127, 140, 141)) # Gris tipo Temperatura
        painter.drawText(rect_titulo, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "RUIDO AMBIENTAL")

        # 4. TEXTOS (Valor y Estado) abajo
        painter.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        rect_val = QRectF(20, h - 90, 200, 70)
        painter.setPen(color_base) # Color dinámico
        painter.drawText(rect_val, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, f"{int(self.anim_valor)} dB")
        
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        rect_est = QRectF(220, h - 65, 150, 30)
        painter.setPen(color_base)
        painter.drawText(rect_est, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, estado)

        # 5. BARRA VERTICAL (Derecha)
        x_barra = w - 40
        y_start = 50
        y_end = h - 50
        alto_barra = y_end - y_start
        
        painter.setPen(QPen(QColor(0, 0, 0, 30), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(x_barra), int(y_start), int(x_barra), int(y_end))
        
        y_progreso = y_end - (alto_barra * f_ruido)
        
        painter.setPen(QPen(color_base, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(x_barra), int(y_progreso), int(x_barra), int(y_end))
        
        # 6. ICONO (Imagen PNG pegada a la barra)
        rect_icono = QRectF(w - 75, y_progreso - 20, 40, 40)
        
        if not self.img_megafono.isNull():
            painter.drawImage(rect_icono, self.img_megafono)
        else:
            # Fallback en caso de que falte la imagen
            painter.setFont(QFont("Segoe UI Emoji", 24))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(rect_icono, Qt.AlignmentFlag.AlignCenter, "📢")

    def closeEvent(self, event):
        self.worker.detener()
        super().closeEvent(event)
