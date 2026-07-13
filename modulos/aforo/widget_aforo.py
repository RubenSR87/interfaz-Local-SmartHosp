import sys
import os
import time
import random
import math
from PySide6.QtCore import QThread, Signal, Qt, QRectF, QPointF, QEasingCurve, QPropertyAnimation, Property
from PySide6.QtWidgets import QWidget, QStyle, QStyleOption
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient, QRadialGradient, QFont

class AforoSensorThread(QThread):
    aforo_cambiado = Signal(int)
    log_mensaje = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.simulado = False

    def run(self):
        try:
            import cv2
            from ultralytics import YOLO
            HAS_LIBS = True
        except ImportError:
            HAS_LIBS = False
            self.log_mensaje.emit("Librerías ultralytics o cv2 no encontradas. Iniciando modo simulación.")
            self.simulado = True

        if not HAS_LIBS or self.simulado:
            self.run_simulation()
            return

        try:
            self.log_mensaje.emit("Cargando modelo YOLO (yolo11n.pt)...")
            modelo = YOLO('yolo11n.pt')
            
            self.log_mensaje.emit("Conectando cámara USB (índice 0)...")
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise Exception("No se pudo abrir la cámara web.")

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            INTERVALO_SEGUNDOS = 5
            tiempo_ultima_captura = time.time() - INTERVALO_SEGUNDOS
            
            self.log_mensaje.emit("Sensor de Aforo iniciado con éxito y monitoreando.")
            
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.5)
                    continue
                
                tiempo_actual = time.time()
                if (tiempo_actual - tiempo_ultima_captura) >= INTERVALO_SEGUNDOS:
                    resultados = modelo.predict(frame, classes=[0], conf=0.45, imgsz=320, verbose=False)
                    aforo_actual = len(resultados[0].boxes)
                    self.aforo_cambiado.emit(aforo_actual)
                    self.log_mensaje.emit(f"Aforo actualizado: {aforo_actual} personas")
                    tiempo_ultima_captura = tiempo_actual
                
                time.sleep(0.03)
                
            cap.release()
            
        except Exception as e:
            self.log_mensaje.emit(f"Error en sensor real: {str(e)}. Iniciando simulación.")
            self.run_simulation()

    def run_simulation(self):
        self.log_mensaje.emit("Iniciando simulación de aforo...")
        while self.running:
            aforo_simulado = random.randint(5, 38)
            self.aforo_cambiado.emit(aforo_simulado)
            self.log_mensaje.emit(f"Simulación - Aforo actualizado: {aforo_simulado} personas")
            
            for _ in range(70):
                if not self.running:
                    break
                time.sleep(0.1)

    def stop(self):
        self.running = False
        self.wait()


class WidgetAforo(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # Estilo estético premium de tarjeta
        self.setStyleSheet("""
            WidgetAforo {
                background-color: #FFFFFF; 
                border: 1px solid #E5E7EB; 
                border-radius: 8px;        
            }
        """)
        
        self._aforo = 0
        self._animated_aforo = 0.0
        
        # Coordenadas de diseño adaptadas para panel de texto izquierdo
        self.x_start = 245
        self.margin_right = 45
        
        # Configuración de animación para la interpolación de valores
        self.animation = QPropertyAnimation(self, b"animated_aforo")
        self.animation.setDuration(700) 
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Inicializar e iniciar el hilo del sensor
        self.sensor_thread = AforoSensorThread()
        self.sensor_thread.aforo_cambiado.connect(self.set_aforo)
        self.sensor_thread.log_mensaje.connect(self.on_sensor_log)
        self.sensor_thread.start()

    @Property(float)
    def animated_aforo(self):
        return self._animated_aforo

    @animated_aforo.setter
    def animated_aforo(self, val):
        self._animated_aforo = val
        self.update() 

    def set_aforo(self, valor):
        self._aforo = valor
        self.animation.stop()
        self.animation.setStartValue(self._animated_aforo)
        self.animation.setEndValue(float(valor))
        self.animation.start()

    def on_sensor_log(self, mensaje):
        print(f"[Aforo Sensor] {mensaje}")

    def get_status_info(self, val):
        # Reglas extraídas del código React provisto:
        # Capacidad Máxima (espera/factor 1.20, comedor/factor 1.40, etc.)
        # Con capacidad máxima de diseño establecida en 25 (conteo 5 a 5, límite de 35+):
        # IO = val / 25
        # IO <= 0.80 (val <= 20) -> Muy Adecuado (Green)
        # IO <= 1.00 (val <= 25) -> Adecuado (Turquoise/Greenish-blue)
        # IO <= 1.20 (val <= 30) -> Regular/Límite (Yellow)
        # IO <= 1.40 (val <= 35) -> Inadecuado (Orange)
        # IO > 1.40 (val > 35) -> Riesgo Operativo (Red)
        if val <= 20:
            return "Muy Adecuado", QColor("#2ECC71") # Verde
        elif val <= 25:
            return "Adecuado", QColor("#1ABC9C") # Verde Turquesa
        elif val <= 30:
            return "Regular (Límite)", QColor("#F1C40F") # Amarillo
        elif val <= 35:
            return "Inadecuado", QColor("#E67E22") # Naranja
        else:
            return "Riesgo Operativo", QColor("#E74C3C") # Rojo

    def get_color_for_index(self, index):
        val = (index + 1) * 5
        status_text, status_color = self.get_status_info(val)
        return status_color

    def get_color_for_value(self, value):
        status_text, status_color = self.get_status_info(value)
        return status_color

    def value_to_x(self, val):
        w = self.width()
        spacing = (w - self.x_start - self.margin_right) / 6.0
        
        if val <= 5:
            pct = max(0.0, val / 5.0)
            x_init = self.x_start - 20
            return x_init + pct * (self.x_start - x_init)
        elif val >= 35:
            return self.x_start + 6.0 * spacing
        else:
            pct = (val - 5.0) / 30.0
            x_end = self.x_start + 6.0 * spacing
            return self.x_start + pct * (x_end - self.x_start)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dibujar fondo y borde
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        
        w = self.width()
        h = self.height()
        
        # 1. Dibujar Panel de Texto Izquierdo
        status_text, status_color = self.get_status_info(self._animated_aforo)
        
        font_title = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.setPen(QColor("#9CA3AF"))
        painter.drawText(QRectF(25, 20, 170, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "CONTROL DE AFORO")
        
        font_number = QFont("Segoe UI", 32, QFont.Weight.Bold)
        painter.setFont(font_number)
        painter.setPen(status_color)
        painter.drawText(QRectF(25, 42, 170, 48), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{int(self._animated_aforo)}")
        
        font_sub = QFont("Segoe UI", 8, QFont.Weight.Medium)
        painter.setFont(font_sub)
        painter.setPen(QColor("#6B7280"))
        painter.drawText(QRectF(25, 92, 170, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Personas en sala")
        
        font_desc = QFont("Segoe UI", 10, QFont.Weight.Bold)
        font_desc.setItalic(True)
        painter.setFont(font_desc)
        painter.setPen(status_color)
        painter.drawText(QRectF(25, 116, 170, 36), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, status_text)
        
        pen_divider = QPen(QColor("#E5E7EB"), 1.5)
        painter.setPen(pen_divider)
        painter.drawLine(210, 15, 210, 155)

        # 2. Dibujar Regla y Gráficos (Parte Derecha)
        y_ruler = 45
        spacing = (w - self.x_start - self.margin_right) / 6.0
        
        pen_ruler = QPen(QColor("#E5E7EB"), 2)
        painter.setPen(pen_ruler)
        painter.drawLine(self.x_start - 20, y_ruler, w - self.margin_right + 20, y_ruler)
        
        font_labels = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font_labels)
        
        for i in range(7):
            col_x = self.x_start + i * spacing
            val = (i + 1) * 5
            
            painter.setPen(QPen(QColor("#9CA3AF"), 1.5))
            painter.drawLine(col_x, y_ruler, col_x, y_ruler + 6)
            
            label_text = f"{val}+" if i == 6 else f"{val}"
            
            is_active = self._animated_aforo >= val
            if is_active:
                painter.setPen(QPen(self.get_color_for_index(i), 1))
            else:
                painter.setPen(QPen(QColor("#9CA3AF"), 1))
                
            painter.drawText(QRectF(col_x - 25, y_ruler - 25, 50, 18), Qt.AlignmentFlag.AlignCenter, label_text)
            
        # Línea de progreso de la regla
        val_x = self.value_to_x(self._animated_aforo)
        if self._animated_aforo > 0:
            grad_ruler = QLinearGradient(self.x_start - 20, y_ruler, val_x, y_ruler)
            grad_ruler.setColorAt(0.0, QColor("#2ECC71"))
            if self._animated_aforo > 20:
                grad_ruler.setColorAt(0.5, QColor("#F1C40F"))
            grad_ruler.setColorAt(1.0, self.get_color_for_value(self._animated_aforo))
            
            pen_progress = QPen(QBrush(grad_ruler), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_progress)
            painter.drawLine(self.x_start - 20, y_ruler, val_x, y_ruler)

        # Indicador flotante
        self.draw_floating_badge(painter, val_x)
        
        # Dibujar Agrupaciones de Personas (5 por columna)
        y_group = 120
        for i in range(7):
            col_x = self.x_start + i * spacing
            color = self.get_color_for_index(i)
            self.draw_person_group(painter, col_x, y_group, color, i)
            
        painter.end()

    def draw_floating_badge(self, painter, val_x):
        badge_w = 40
        badge_h = 20
        badge_y = 12
        
        badge_rect = QRectF(val_x - badge_w / 2.0, badge_y, badge_w, badge_h)
        color = self.get_color_for_value(self._animated_aforo)
        
        arrow_path = QPainterPath()
        arrow_path.moveTo(val_x - 4, badge_y + badge_h)
        arrow_path.lineTo(val_x + 4, badge_y + badge_h)
        arrow_path.lineTo(val_x, badge_y + badge_h + 4)
        arrow_path.closeSubpath()
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPath(arrow_path)
        
        painter.drawRoundedRect(badge_rect, 6, 6)
        
        painter.setPen(QColor("#FFFFFF"))
        font_badge = QFont("Segoe UI", 8, QFont.Weight.Black)
        painter.setFont(font_badge)
        
        text_val = f"{int(self._animated_aforo)}"
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text_val)

    def draw_person_group(self, painter, col_x, y_group, color, group_index):
        base_val = group_index * 5
        
        # Distribución de 5 personas en pirámide
        offsets = [
            (-15, -8),  # 1. Back-Left
            (15, -8),   # 2. Back-Right
            (0, -14),   # 3. Back-Center
            (-8, 6),    # 4. Front-Left
            (8, 6)      # 5. Front-Right
        ]
        
        for j in range(5):
            dx, dy = offsets[j]
            x = col_x + dx
            y = y_group + dy
            
            # Relación de 1 a 1: cada muñeco representa exactamente 1 persona de aforo
            threshold = base_val + (j + 1)
            prev_threshold = threshold - 1
            
            if self._animated_aforo >= threshold:
                activity = 1.0
            elif self._animated_aforo <= prev_threshold:
                activity = 0.0
            else:
                activity = self._animated_aforo - prev_threshold
                
            self.draw_individual_person(painter, x, y, color, activity)

    def draw_individual_person(self, painter, x, y, color, activity):
        inactive_color = QColor("#CBD5E1")
        
        opacity = 0.18 + 0.82 * activity
        scale = 1.0 + 0.24 * math.sin(activity * math.pi)
        
        painter.save()
        painter.translate(x, y)
        painter.scale(scale, scale)
        
        painter.setPen(QPen(QColor("#FFFFFF"), 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        # Cabeza
        painter.drawEllipse(-6, -18, 12, 12)
        # Torso
        mask_path = QPainterPath()
        mask_path.moveTo(-11, 16)
        mask_path.lineTo(-11, 9)
        mask_path.arcTo(-11, 0, 22, 18, 180, -180)
        mask_path.lineTo(11, 16)
        mask_path.closeSubpath()
        painter.drawPath(mask_path)
        
        # Relleno
        if activity > 0:
            rad_grad = QRadialGradient(0, -12, 6)
            rad_grad.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), int(60 * activity)))
            rad_grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setBrush(QBrush(rad_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(-8, -20, 16, 16)
            
            lin_grad = QLinearGradient(0, 0, 0, 16)
            lin_grad.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), int(70 * activity)))
            lin_grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setBrush(QBrush(lin_grad))
            painter.drawPath(mask_path)
            
        r = int(inactive_color.red() + (color.red() - inactive_color.red()) * activity)
        g = int(inactive_color.green() + (color.green() - inactive_color.green()) * activity)
        b = int(inactive_color.blue() + (color.blue() - inactive_color.blue()) * activity)
        pen_c = QColor(r, g, b)
        pen_c.setAlpha(int(255 * opacity))
        
        pen_w = 1.6 + 0.6 * activity
        painter.setPen(QPen(pen_c, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        painter.drawEllipse(-6, -18, 12, 12)
        painter.drawLine(0, -6, 0, 0)
        painter.drawArc(-11, 0, 22, 18, 0, 180 * 16)
        
        painter.restore()

    def closeEvent(self, event):
        self.sensor_thread.stop()
        super().closeEvent(event)
