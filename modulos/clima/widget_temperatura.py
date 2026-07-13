import sys
import os
import time
import random
import math
from PySide6.QtCore import QThread, Signal, Qt, QRectF, QPointF, QEasingCurve, QPropertyAnimation, Property
from PySide6.QtWidgets import QWidget, QStyle, QStyleOption
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient, QRadialGradient, QFont, QPixmap

class TemperaturaSensorThread(QThread):
    temperatura_cambiada = Signal(float)
    humedad_cambiada = Signal(float)
    log_mensaje = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.simulado = False

    def run(self):
        try:
            import board
            import adafruit_dht
            HAS_LIBS = True
        except ImportError:
            HAS_LIBS = False
            self.log_mensaje.emit("Librerías adafruit_dht o board no encontradas. Iniciando modo simulación.")
            self.simulado = True

        if not HAS_LIBS or self.simulado:
            self.run_simulation()
            return

        try:
            self.log_mensaje.emit("Inicializando sensor DHT11 en pin GPIO 4...")
            sensor_dht = adafruit_dht.DHT11(board.D4)
            
            self.log_mensaje.emit("Sensor DHT11 conectado. Monitoreando clima...")
            while self.running:
                try:
                    temp_c = sensor_dht.temperature
                    hum = sensor_dht.humidity
                    if temp_c is not None:
                        self.temperatura_cambiada.emit(float(temp_c))
                        if hum is not None:
                            self.humedad_cambiada.emit(float(hum))
                        self.log_mensaje.emit(f"DHT11 - Temp: {temp_c:.1f}°C | Hum: {hum}%")
                except RuntimeError as error:
                    # Errores temporales de lectura del DHT11 son comunes, se ignora y reintenta
                    pass
                
                # Dormir 2.5 segundos de manera interrumpible (DHT11 requiere min 2s de tasa)
                for _ in range(25):
                    if not self.running:
                        break
                    time.sleep(0.1)
                    
            sensor_dht.exit()
            
        except Exception as e:
            self.log_mensaje.emit(f"Error en sensor real: {str(e)}. Iniciando simulación.")
            self.run_simulation()

    def run_simulation(self):
        self.log_mensaje.emit("Iniciando simulación de clima...")
        base_temp = 22.0
        while self.running:
            # Fluctuaciones realistas de temperatura
            fluctuacion = random.uniform(-1.2, 1.2)
            temp_simulada = max(11.0, min(39.0, base_temp + fluctuacion))
            base_temp = temp_simulada
            
            self.temperatura_cambiada.emit(temp_simulada)
            self.log_mensaje.emit(f"Simulación - Temp: {temp_simulada:.1f}°C")
            
            # Dormir 6 segundos interrumpibles
            for _ in range(60):
                if not self.running:
                    break
                time.sleep(0.1)

    def stop(self):
        self.running = False
        self.wait()


class WidgetTemperatura(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # Estilo estético premium de tarjeta
        self.setStyleSheet("""
            WidgetTemperatura {
                background-color: #FFFFFF; 
                border: 1px solid #E5E7EB; 
                border-radius: 8px;        
            }
        """)
        
        self._temp = 22.0
        self._animated_temp = 22.0
        
        # Rutas actualizadas de las imágenes en la carpeta img/temperatura
        self.img_path_cold = "img/temperatura/cold.png"
        self.img_path_chill = "img/temperatura/chill.jpg"
        self.img_path_hot = "img/temperatura/hot.jpeg"
        
        # Cachear pixmaps en el constructor para alto rendimiento en la Pi 5
        self.pixmap_cold = QPixmap(self.img_path_cold)
        self.pixmap_chill = QPixmap(self.img_path_chill)
        self.pixmap_hot = QPixmap(self.img_path_hot)
        
        # Coordenadas de inicio para gráficos de termómetro
        self.x_start = 245
        self.margin_right = 45
        
        # Configuración de animación para la interpolación de valores
        self.animation = QPropertyAnimation(self, b"animated_temp")
        self.animation.setDuration(800) 
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Inicializar e iniciar el hilo del sensor
        self.sensor_thread = TemperaturaSensorThread()
        self.sensor_thread.temperatura_cambiada.connect(self.set_temp)
        self.sensor_thread.log_mensaje.connect(self.on_sensor_log)
        self.sensor_thread.start()

    @Property(float)
    def animated_temp(self):
        return self._animated_temp

    @animated_temp.setter
    def animated_temp(self, val):
        self._animated_temp = val
        self.update() 

    def set_temp(self, valor):
        self._temp = valor
        self.animation.stop()
        self.animation.setStartValue(self._animated_temp)
        self.animation.setEndValue(float(valor))
        self.animation.start()

    def on_sensor_log(self, mensaje):
        print(f"[Temperatura Sensor] {mensaje}")

    def get_color_for_temp(self, temp):
        # Rango de temperatura mapeado a gradiente semáforo dinámico (Azul -> Verde -> Naranja -> Rojo)
        if temp <= 22:
            pct = max(0.0, (temp - 10.0) / 12.0)
            hue = int(200 - pct * 80)
        elif temp <= 30:
            pct = max(0.0, (temp - 22.0) / 8.0)
            hue = int(120 - pct * 80)
        else:
            pct = min(1.0, (temp - 30.0) / 10.0)
            hue = int(40 - pct * 40)
        return QColor.fromHsl(hue, 220, 115)

    def get_status_info(self, temp):
        # Reglas para 'corredor' obtenidas del archivo React provisto:
        # Excelente (5): [22, 23.9] -> Verde Turquesa
        # Bueno (4): [20, 21.9], [24, 25.9] -> Verde Clásico
        # Regular (3): [18, 19.9], [26, 27.9] -> Amarillo/Ámbar
        # Malo (2): [16, 17.9], [28, 30] -> Naranja
        # Muy Malo (1): <-inf, 15.9] y [30.1, +inf> -> Rojo
        if 22.0 <= temp <= 23.9:
            return "Excelente", QColor("#1ABC9C") 
        elif (20.0 <= temp < 22.0) or (23.9 < temp <= 25.9):
            return "Bueno", QColor("#2ECC71") 
        elif (18.0 <= temp < 20.0) or (25.9 < temp <= 27.9):
            return "Regular", QColor("#F1C40F") 
        elif (16.0 <= temp < 18.0) or (27.9 < temp <= 30.0):
            return "Malo", QColor("#E67E22") 
        else:
            return "Muy Malo", QColor("#E74C3C") 

    def temp_to_x(self, temp):
        w = self.width()
        x_therm_start = self.x_start + 45
        x_therm_end = w - self.margin_right - 20
        spacing = (x_therm_end - x_therm_start) / 30.0
        
        if temp <= 10.0:
            return x_therm_start
        elif temp >= 40.0:
            return x_therm_end
        else:
            return x_therm_start + (temp - 10.0) * spacing

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dibujar fondo y borde
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        
        w = self.width()
        h = self.height()
        
        # 1. Dibujar Panel de Texto Izquierdo (Reactivo y Limpio)
        status_text, status_color = self.get_status_info(self._animated_temp)
        
        font_title = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.setPen(QColor("#9CA3AF"))
        painter.drawText(QRectF(25, 20, 170, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "TEMPERATURA AMBIENTE")
        
        font_number = QFont("Segoe UI", 32, QFont.Weight.Bold)
        painter.setFont(font_number)
        painter.setPen(status_color)
        painter.drawText(QRectF(25, 45, 170, 50), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{self._animated_temp:.1f} °C")
        
        # Se removió la línea con información técnica ("Sensor DHT11 Pasillo")
        
        font_desc = QFont("Segoe UI", 10, QFont.Weight.Bold)
        font_desc.setItalic(True)
        painter.setFont(font_desc)
        painter.setPen(status_color)
        # Reubicado a y=110 debido al espacio libre del texto técnico
        painter.drawText(QRectF(25, 110, 170, 36), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, status_text)
        
        pen_divider = QPen(QColor("#E5E7EB"), 1.5)
        painter.setPen(pen_divider)
        painter.drawLine(210, 15, 210, 155)

        # 2. Dibujar Termómetro Horizontal
        y_center = 65
        x_bulb = self.x_start + 25
        r_bulb = 20
        
        x_therm_start = self.x_start + 45
        x_therm_end = w - self.margin_right - 20
        spacing = (x_therm_end - x_therm_start) / 30.0
        
        # A. Dibujar Líneas y Flechas de Guía (Fondo)
        self.draw_guide_arrow(painter, x_therm_start, 102, 75)
        x_comfort = x_therm_start + 12.0 * spacing
        self.draw_guide_arrow(painter, x_comfort, 102, 75)
        self.draw_guide_arrow(painter, x_therm_end, 102, 75)
        
        # B. Dibujar marcas (ticks) y números de escala
        font_labels = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font_labels)
        
        for temp_val in range(10, 41, 5):
            tx = x_therm_start + (temp_val - 10.0) * spacing
            painter.setPen(QPen(QColor("#D1D5DB"), 1.2))
            painter.drawLine(tx, y_center - 10, tx, y_center - 15)
            painter.setPen(QPen(QColor("#9CA3AF"), 1))
            painter.drawText(QRectF(tx - 20, y_center - 32, 40, 15), Qt.AlignmentFlag.AlignCenter, f"{temp_val}°")
            
        # C. Dibujar el Tubo de Vidrio Vacío
        tube_path = QPainterPath()
        tube_path.moveTo(x_therm_start, y_center - 7)
        tube_path.lineTo(x_therm_end - 6, y_center - 7)
        tube_path.arcTo(x_therm_end - 12, y_center - 7, 12, 14, 90, -180)
        tube_path.lineTo(x_therm_start, y_center + 7)
        tube_path.closeSubpath()
        
        painter.setPen(QPen(QColor("#E5E7EB"), 2))
        painter.setBrush(QBrush(QColor("#F9FAFB")))
        painter.drawPath(tube_path)
        
        # D. Dibujar Líquido Fluido (Mercurio)
        x_val = self.temp_to_x(self._animated_temp)
        fluid_w = x_val - x_therm_start
        color_fluid = self.get_color_for_temp(self._animated_temp)
        
        if fluid_w > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            grad_fluid = QLinearGradient(x_therm_start, y_center - 4, x_val, y_center - 4)
            grad_fluid.setColorAt(0.0, color_fluid)
            grad_fluid.setColorAt(1.0, color_fluid.lighter(115))
            painter.setBrush(QBrush(grad_fluid))
            painter.drawRoundedRect(QRectF(x_therm_start - 2, y_center - 4, fluid_w + 4, 8), 3, 3)
            
        # Reflejo 3D brillante superior
        painter.setPen(QPen(QColor(255, 255, 255, 110), 1.5))
        painter.drawLine(x_therm_start, y_center - 4, x_therm_end - 6, y_center - 4)

        # E. Dibujar el Bulbo Ocular de la Base
        radial_aura = QRadialGradient(x_bulb, y_center, r_bulb + 6)
        radial_aura.setColorAt(0.0, QColor(color_fluid.red(), color_fluid.green(), color_fluid.blue(), 75))
        radial_aura.setColorAt(1.0, QColor(color_fluid.red(), color_fluid.green(), color_fluid.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        radial_aura_brush = QBrush(radial_aura)
        painter.setBrush(radial_aura_brush)
        painter.drawEllipse(x_bulb - r_bulb - 6, y_center - r_bulb - 6, (r_bulb + 6) * 2, (r_bulb + 6) * 2)
        
        grad_bulb = QRadialGradient(x_bulb, y_center, r_bulb)
        grad_bulb.setColorAt(0.0, color_fluid.lighter(120))
        grad_bulb.setColorAt(0.8, color_fluid)
        grad_bulb.setColorAt(1.0, color_fluid.darker(110))
        painter.setPen(QPen(QColor("#E5E7EB"), 2))
        painter.setBrush(QBrush(grad_bulb))
        painter.drawEllipse(x_bulb - r_bulb, y_center - r_bulb, r_bulb * 2, r_bulb * 2)
        
        # F. Dibujar el icono dinámico (Cargando imágenes de frío, chill y calor)
        self.draw_bulb_icon(painter, x_bulb, y_center, self._animated_temp)

        # G. Dibujar los tres iconos de referencia abajo (Vectoriales Estables)
        y_icons = 117
        self.draw_ref_icon(painter, x_therm_start, y_icons, "cold")
        self.draw_ref_icon(painter, x_comfort, y_icons, "comfort")
        self.draw_ref_icon(painter, x_therm_end, y_icons, "hot")
        
        painter.end()

    def draw_guide_arrow(self, painter, x, y_start, y_end):
        painter.setPen(QPen(QColor("#D1D5DB"), 1.2, Qt.PenStyle.DashLine))
        painter.drawLine(x, y_start, x, y_end)
        
        painter.setPen(QPen(QColor("#D1D5DB"), 1.2, Qt.PenStyle.SolidLine))
        painter.setBrush(QBrush(QColor("#D1D5DB")))
        arrow = QPainterPath()
        arrow.moveTo(x - 3, y_end + 3)
        arrow.lineTo(x + 3, y_end + 3)
        arrow.lineTo(x, y_end)
        arrow.closeSubpath()
        painter.drawPath(arrow)

    def draw_bulb_icon(self, painter, cx, cy, temp):
        pixmap_to_draw = None
        fallback_type = ""
        
        if temp < 18.0:
            pixmap_to_draw = self.pixmap_cold
            fallback_type = "cold"
        elif temp <= 27.0:
            pixmap_to_draw = self.pixmap_chill
            fallback_type = "chill"
        else:
            pixmap_to_draw = self.pixmap_hot
            fallback_type = "hot"

        if pixmap_to_draw and not pixmap_to_draw.isNull():
            rect_dest = QRectF(cx - 13, cy - 13, 26, 26)
            clip_path = QPainterPath()
            clip_path.addEllipse(cx - 13, cy - 13, 26, 26)
            
            painter.save()
            painter.setClipPath(clip_path)
            painter.drawPixmap(rect_dest, pixmap_to_draw, QRectF(pixmap_to_draw.rect()))
            painter.restore()
        else:
            painter.save()
            painter.setPen(QPen(QColor("#FFFFFF"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            if fallback_type == "cold":
                for i in range(6):
                    angle = i * 60
                    rad = math.radians(angle)
                    dx = 7 * math.cos(rad)
                    dy = 7 * math.sin(rad)
                    painter.drawLine(cx, cy, cx + dx, cy + dy)
                    dx_tick = 5 * math.cos(rad)
                    dy_tick = 5 * math.sin(rad)
                    painter.drawLine(cx + dx_tick, cy + dy_tick, cx + dx_tick + 2 * math.cos(math.radians(angle+45)), cy + dy_tick + 2 * math.sin(math.radians(angle+45)))
                    painter.drawLine(cx + dx_tick, cy + dy_tick, cx + dx_tick + 2 * math.cos(math.radians(angle-45)), cy + dy_tick + 2 * math.sin(math.radians(angle-45)))
            elif fallback_type == "chill":
                path = QPainterPath()
                path.moveTo(cx - 5, cy + 5)
                path.quadTo(cx - 5, cy - 5, cx + 5, cy - 5)
                path.quadTo(cx + 5, cy + 5, cx - 5, cy + 5)
                painter.setBrush(QBrush(QColor(255, 255, 255, 100)))
                painter.drawPath(path)
            else:
                path = QPainterPath()
                path.moveTo(cx, cy + 7)
                path.cubicTo(cx - 6, cy + 7, cx - 6, cy - 1, cx, cy - 7)
                path.cubicTo(cx + 6, cy - 1, cx + 6, cy + 7, cx, cy + 7)
                path.closeSubpath()
                painter.setBrush(QBrush(QColor(255, 255, 255, 100)))
                painter.drawPath(path)
                
            painter.restore()

    def draw_ref_icon(self, painter, cx, cy, icon_type):
        painter.save()
        
        label = ""
        sub_label = ""
        
        if icon_type == "cold":
            label = "Muy Frío"
            sub_label = "< 18°C"
        elif icon_type == "comfort":
            label = "Agradable"
            sub_label = "20°C-24°C"
        else:
            label = "Muy Caliente"
            sub_label = "> 28°C"
            
        # Dibujo Vectorial Fijo e Impecable para las referencias de escala
        if icon_type == "cold":
            painter.setPen(QPen(QColor("#3B82F6"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for i in range(6):
                angle = i * 60
                rad = math.radians(angle)
                painter.drawLine(cx, cy, cx + 9 * math.cos(rad), cy + 9 * math.sin(rad))
                dx_tick = 6 * math.cos(rad)
                dy_tick = 6 * math.sin(rad)
                painter.drawLine(cx + dx_tick, cy + dy_tick, cx + dx_tick + 2 * math.cos(math.radians(angle+45)), cy + dy_tick + 2 * math.sin(math.radians(angle+45)))
                painter.drawLine(cx + dx_tick, cy + dy_tick, cx + dx_tick + 2 * math.cos(math.radians(angle-45)), cy + dy_tick + 2 * math.sin(math.radians(angle-45)))
        elif icon_type == "comfort":
            painter.setPen(QPen(QColor("#10B981"), 1.8))
            path = QPainterPath()
            path.moveTo(cx - 6, cy + 6)
            path.quadTo(cx - 6, cy - 6, cx + 6, cy - 6)
            path.quadTo(cx + 6, cy + 6, cx - 6, cy + 6)
            painter.setBrush(QBrush(QColor(16, 185, 129, 30)))
            painter.drawPath(path)
        else:
            painter.setPen(QPen(QColor("#EF4444"), 1.6))
            painter.setBrush(QBrush(QColor(239, 68, 68, 30)))
            painter.drawEllipse(cx - 5, cy - 5, 10, 10)
            for i in range(8):
                angle = i * 45
                rad = math.radians(angle)
                painter.drawLine(cx + 6 * math.cos(rad), cy + 6 * math.sin(rad),
                                 cx + 9 * math.cos(rad), cy + 9 * math.sin(rad))
                    
        # Dibujar etiquetas bajo los iconos de referencia
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#4B5563"))
        painter.drawText(QRectF(cx - 45, cy + 14, 90, 14), Qt.AlignmentFlag.AlignCenter, label)
        
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Medium))
        painter.setPen(QColor("#9CA3AF"))
        painter.drawText(QRectF(cx - 45, cy + 26, 90, 12), Qt.AlignmentFlag.AlignCenter, sub_label)
        
        painter.restore()

    def closeEvent(self, event):
        self.sensor_thread.stop()
        super().closeEvent(event)
