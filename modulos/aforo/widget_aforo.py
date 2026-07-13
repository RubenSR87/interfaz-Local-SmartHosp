import sys
import os
import time
import random
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
            aforo_simulado = random.randint(10, 115)
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
        
        # Nuevas coordenadas de diseño adaptadas para panel de texto izquierdo
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

    def get_color_for_index(self, index):
        # Gradiente semáforo dinámico (Verde -> Amarillo/Naranja -> Rojo)
        # index de 0 a 10 (11 elementos)
        hue = int(120 - index * 12)
        if hue < 0:
            hue = 0
        return QColor.fromHsl(hue, 220, 115)

    def get_color_for_value(self, value):
        idx = (value - 10.0) / 10.0
        if idx < 0.0:
            idx = 0.0
        elif idx > 10.0:
            idx = 10.0
        return self.get_color_for_index(idx)

    def get_status_info(self, val):
        # Estados reactivos según aforo
        if val <= 30:
            return "El espacio es cómodo", QColor("#10B981") # Verde
        elif val <= 80:
            return "Aglomeración aumentando", QColor("#D97706") # Amarillo/Naranja
        elif val <= 100:
            return "Límite de aforo próximo", QColor("#EA580C") # Rojo
        else:
            return "Peligro de sobreaforo", QColor("#EF4444") # Crítico / Rojo intenso

    def value_to_x(self, val):
        w = self.width()
        spacing = (w - self.x_start - self.margin_right) / 10.0
        
        if val <= 10:
            pct = max(0.0, val / 10.0)
            x_init = self.x_start - 20
            return x_init + pct * (self.x_start - x_init)
        elif val >= 110:
            return self.x_start + 10.0 * spacing
        else:
            pct = (val - 10.0) / 100.0
            x_end = self.x_start + 10.0 * spacing
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
        
        # 1. Dibujar Panel de Texto Izquierdo (Reactivo)
        status_text, status_color = self.get_status_info(self._animated_aforo)
        
        # Título
        font_title = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.setPen(QColor("#9CA3AF"))
        painter.drawText(QRectF(25, 20, 170, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "CONTROL DE AFORO")
        
        # Número Grande
        font_number = QFont("Segoe UI", 32, QFont.Weight.Bold)
        painter.setFont(font_number)
        painter.setPen(status_color)
        painter.drawText(QRectF(25, 42, 170, 48), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{int(self._animated_aforo)}")
        
        # Subtítulo (Personas registradas)
        font_sub = QFont("Segoe UI", 8, QFont.Weight.Medium)
        painter.setFont(font_sub)
        painter.setPen(QColor("#6B7280"))
        painter.drawText(QRectF(25, 92, 170, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Personas en sala")
        
        # Descripción Reactiva (WordWrap habilitado para mensajes largos)
        font_desc = QFont("Segoe UI", 10, QFont.Weight.Bold)
        font_desc.setItalic(True)
        painter.setFont(font_desc)
        painter.setPen(status_color)
        painter.drawText(QRectF(25, 116, 170, 36), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, status_text)
        
        # Divider Line entre texto y gráficos
        pen_divider = QPen(QColor("#E5E7EB"), 1.5)
        painter.setPen(pen_divider)
        painter.drawLine(210, 15, 210, 155)

        # 2. Dibujar Regla y Gráficos (Parte Derecha)
        y_ruler = 45
        spacing = (w - self.x_start - self.margin_right) / 10.0
        
        # Línea base de la regla
        pen_ruler = QPen(QColor("#E5E7EB"), 2)
        painter.setPen(pen_ruler)
        painter.drawLine(self.x_start - 20, y_ruler, w - self.margin_right + 20, y_ruler)
        
        # Ticks y etiquetas
        font_labels = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font_labels)
        
        for i in range(11):
            col_x = self.x_start + i * spacing
            val = (i + 1) * 10
            
            # Marca física
            painter.setPen(QPen(QColor("#9CA3AF"), 1.5))
            painter.drawLine(col_x, y_ruler, col_x, y_ruler + 6)
            
            # Etiqueta
            label_text = f"{val}+" if i == 10 else f"{val}"
            
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
            grad_ruler.setColorAt(0.0, QColor("#10B981"))
            if self._animated_aforo > 60:
                grad_ruler.setColorAt(0.5, QColor("#FBBF24"))
            grad_ruler.setColorAt(1.0, self.get_color_for_value(self._animated_aforo))
            
            pen_progress = QPen(QBrush(grad_ruler), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_progress)
            painter.drawLine(self.x_start - 20, y_ruler, val_x, y_ruler)

        # Indicador flotante
        self.draw_floating_badge(painter, val_x)
        
        # Figuras vectoriales de las personas
        y_head = 85
        y_shoulder = 112
        
        for i in range(11):
            col_x = self.x_start + i * spacing
            val = (i + 1) * 10
            prev_val = val - 10
            
            if self._animated_aforo >= val:
                activity = 1.0
            elif self._animated_aforo <= prev_val:
                activity = 0.0
            else:
                activity = (self._animated_aforo - prev_val) / 10.0
                
            color = self.get_color_for_index(i)
            self.draw_person(painter, col_x, y_head, y_shoulder, color, activity)
            
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

    def draw_person(self, painter, col_x, y_head, y_shoulder, color, activity):
        inactive_color = QColor("#E2E8F0") 
        
        if activity > 0:
            radial_grad = QRadialGradient(col_x, y_head + 9, 9)
            radial_grad.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), int(60 * activity)))
            radial_grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setBrush(QBrush(radial_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(col_x - 12, y_head - 3, 24, 24)
            
            linear_grad = QLinearGradient(col_x, y_shoulder, col_x, y_shoulder + 25)
            linear_grad.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), int(70 * activity)))
            linear_grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            
            body_path = QPainterPath()
            body_path.moveTo(col_x - 18, y_shoulder + 25)
            body_path.lineTo(col_x - 18, y_shoulder + 14)
            body_path.arcTo(col_x - 18, y_shoulder, 36, 28, 180, -180)
            body_path.lineTo(col_x + 18, y_shoulder + 25)
            body_path.closeSubpath()
            
            painter.setBrush(QBrush(linear_grad))
            painter.drawPath(body_path)
            
        r = int(inactive_color.red() + (color.red() - inactive_color.red()) * activity)
        g = int(inactive_color.green() + (color.green() - inactive_color.green()) * activity)
        b = int(inactive_color.blue() + (color.blue() - inactive_color.blue()) * activity)
        pen_color = QColor(r, g, b)
        
        pen_w = 2.0 + 1.0 * activity
        pen_person = QPen(pen_color, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen_person)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        painter.drawEllipse(col_x - 9, y_head, 18, 18)
        painter.drawLine(col_x, y_head + 18, col_x, y_shoulder)
        painter.drawArc(col_x - 18, y_shoulder, 36, 28, 0, 180 * 16)

    def closeEvent(self, event):
        self.sensor_thread.stop()
        super().closeEvent(event)
