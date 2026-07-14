import math
import random
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPainterPath, QFont, QPen, QBrush, QLinearGradient, QRadialGradient, QImage
)
import os
from modulos.supabase_client import enviar_lectura

class SensorHumedadWorker(QThread):
    datos_actualizados = Signal(float)

    def __init__(self, simulacion=True):
        super().__init__()
        self.simulacion = simulacion
        self.corriendo = True
        self.sensor = None
        
        if not self.simulacion:
            try:
                import board
                import adafruit_dht
                # Inicializar DHT11 real en el pin GPIO 4
                self.sensor = adafruit_dht.DHT11(board.D4)
                print("[Humedad] Sensor real DHT11 inicializado.")
            except Exception as e:
                print(f"[Humedad] Error iniciando sensor real: {e}. Usando simulación.")
                self.simulacion = True
                
        self.valor_simulado = 50.0 

    def run(self):
        while self.corriendo:
            if self.simulacion:
                variacion = random.uniform(-20.0, 25.0) 
                self.valor_simulado += variacion
                if self.valor_simulado > 100.0:
                    self.valor_simulado -= 40.0
                elif self.valor_simulado < 0.0:
                    self.valor_simulado += 30.0
                self.datos_actualizados.emit(self.valor_simulado)
                print(f"[Sensor Humedad] Simulación - Humedad: {self.valor_simulado:.1f}%")
                self.msleep(2000)
            else:
                try:
                    hum = self.sensor.humidity
                    if hum is not None:
                        self.datos_actualizados.emit(float(hum))
                        print(f"[Sensor Humedad] Real - Humedad: {hum:.1f}%")
                except RuntimeError as error:
                    # Errores temporales de lectura de DHT11 se ignoran
                    pass
                except Exception as e:
                    print(f"[Humedad] Error leyendo sensor: {e}")
                
                # DHT11 requiere al menos 2 segundos entre lecturas
                for _ in range(25):
                    if not self.corriendo: break
                    self.msleep(100)

    def detener(self):
        self.corriendo = False
        if self.sensor is not None:
            self.sensor.exit()
        self.wait()


class SensorCalidadWorker(QThread):

    datos_actualizados = Signal(float)
    error_lectura = Signal(str)

    def __init__(self, simulacion=None):
        super().__init__()

        # Si no se especifica manualmente, se lee desde una variable de entorno.
        # Valor predeterminado: simulación.
        if simulacion is None:
            modo = os.getenv("SMARTHOSP_MODE", "simulacion").lower()
            self.simulacion = modo != "real"
        else:
            self.simulacion = simulacion

        self.corriendo = True
        self.valor_simulado = 50.0
        self.sensor = None

        if not self.simulacion:
            try:
                # Importación diferida:
                # Windows no necesita tener instaladas las librerías de Raspberry.
                from modulos.hum_ca_aire.sensor_calidad_aire import (
                    SensorCalidadAire
                )

                self.sensor = SensorCalidadAire(
                    voltaje_entrada=5.0,
                    r0=37.0,
                    enviar_supabase=False,
                )

                print(
                    "[Calidad de aire] Modo real activado: "
                    "MQ-135 + ADS1115."
                )

            except Exception as error:
                self.simulacion = True
                self.sensor = None

                mensaje = (
                    "[Calidad de aire] No se pudo iniciar el sensor real. "
                    f"Se utilizará simulación. Detalle: {error}"
                )

                print(mensaje)
                self.error_lectura.emit(mensaje)

    def run(self):
        while self.corriendo:
            if self.simulacion:
                self._leer_simulacion()
                intervalo_ms = 2000
            else:
                self._leer_sensor_real()
                intervalo_ms = 10000

            self.msleep(intervalo_ms)

    def _leer_simulacion(self):
        variacion = random.uniform(-15.0, 25.0)
        self.valor_simulado += variacion

        if self.valor_simulado > 400.0:
            self.valor_simulado -= 150.0
        elif self.valor_simulado < 0.0:
            self.valor_simulado += 50.0

        self.datos_actualizados.emit(self.valor_simulado)
        print(f"[Sensor Calidad Aire] Simulación - AQI: {self.valor_simulado:.1f} ppm")

    def _leer_sensor_real(self):
        if self.sensor is None:
            return

        try:
            datos = self.sensor.leer_y_enviar()
            ppm = float(datos["ppm"])

            self.datos_actualizados.emit(ppm)

            print(
                f"[Sensor Calidad Aire] Real - "
                f"Voltaje: {datos['voltaje']:.3f} V | "
                f"Estimación: {ppm:.1f} ppm"
            )

        except Exception as error:
            mensaje = f"Error leyendo MQ-135: {error}"
            print(f"[Calidad de aire] {mensaje}")
            self.error_lectura.emit(mensaje)

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

        # Iconos Calidad de Aire (PNGs dinámicos desde subcarpeta img)
        ruta_img_ca = base_path / "img"
        ruta_img_ca.mkdir(parents=True, exist_ok=True)
        self.img_ca_bueno = QImage(str(ruta_img_ca / "ca_bueno.png"))
        self.img_ca_moderado = QImage(str(ruta_img_ca / "ca_moderado.png"))
        self.img_ca_malo = QImage(str(ruta_img_ca / "ca_malo.png"))
        self.img_ca_critico = QImage(str(ruta_img_ca / "ca_critico.png"))

        # Generar gotas de lluvia aleatorias
        for _ in range(80):
            self.gotas_agua.append({
                'x': random.uniform(0, 1),
                'y': random.uniform(-1.0, 1.0),
                'tam': random.uniform(4, 12),
                'vel': random.uniform(0.001, 0.006),
                'trail': random.uniform(10, 50)
            })
            
        self.worker = SensorHumedadWorker(simulacion=True)
        self.worker.datos_actualizados.connect(self.actualizar_target)
        self.worker.start()

        self.worker_ca = SensorCalidadWorker(simulacion=False)
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
        
        # --- 1. FONDO BLANCO ---
        path_fondo = QPainterPath()
        path_fondo.addRoundedRect(0, 0, w, h, 12, 12)
        painter.fillPath(path_fondo, QColor(255, 255, 255))
        
        # --- 2. EFECTOS DE GOTAS Y EMPAÑO ---
        aqi = self.anim_valor_ca
        
        if porcentaje > 0.3:
            f_niebla = min(1.0, (porcentaje - 0.3) / 0.7)
            
            if aqi > 100:
                # Lluvia ácida (tonos verdes amarillentos)
                color_niebla = QColor(132, 204, 22, int(40 * f_niebla))
                color_rastro = QColor(132, 204, 22, int(60 * f_niebla))
                color_gota_start = QColor(132, 204, 22, int(80 * f_niebla))
            else:
                # Lluvia normal (tonos celestes)
                color_niebla = QColor(14, 165, 233, int(40 * f_niebla))
                color_rastro = QColor(14, 165, 233, int(60 * f_niebla))
                color_gota_start = QColor(14, 165, 233, int(80 * f_niebla))
                
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color_niebla)
            painter.drawRect(0, 0, w, h)
            
            for g in self.gotas_agua:
                x = g['x'] * w
                y = g['y'] * h
                tam = g['tam']
                
                # Rastro de la gota
                painter.setPen(QPen(color_rastro, tam * 0.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(int(x + tam/2), int(y), int(x + tam/2), int(y - g['trail']))
                
                # Sombra de la gota
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 0, 0, int(40 * f_niebla)))
                painter.drawEllipse(QRectF(x + 1, y + 2, tam, tam * 1.3))
                
                # Cuerpo de la gota (Gradiente)
                grad_gota = QLinearGradient(x, y, x, y + tam * 1.3)
                grad_gota.setColorAt(0.0, color_gota_start) 
                grad_gota.setColorAt(1.0, QColor(255, 255, 255, int(200 * f_niebla))) 
                painter.setBrush(grad_gota)
                painter.drawEllipse(QRectF(x, y, tam, tam * 1.3))
                
                # Brillo de la gota
                painter.setBrush(QColor(255, 255, 255, int(255 * f_niebla)))
                painter.drawEllipse(QRectF(x + tam*0.25, y + tam*0.15, tam*0.3, tam*0.35))
        elif aqi > 100:
            # Humo verde clarito si hay mala calidad de aire pero no humedad
            f_humo = min(1.0, (aqi - 100) / 200.0)
            painter.setPen(Qt.PenStyle.NoPen)
            
            offset = (self.anim_valor_ca * 0.2) % 100
            for i in range(3):
                cx = w * (0.2 + i * 0.3) + math.sin(offset + i) * 30
                cy = h * 0.5 + math.cos(offset + i) * 30
                radio = w * 0.45
                
                grad = QRadialGradient(cx, cy, radio)
                grad.setColorAt(0.0, QColor(132, 204, 22, int(40 * f_humo))) # Verde clarito
                grad.setColorAt(1.0, QColor(132, 204, 22, 0))
                
                painter.setBrush(grad)
                painter.drawEllipse(QRectF(cx - radio, cy - radio, radio*2, radio*2))

        # --- 3. INTERFAZ DE HUMEDAD HUD ---
        margin_x = 20
        margin_der = w * 0.35  # Dinámico: 35% del ancho para calidad de aire
        if margin_der < 100: margin_der = 100
        
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        rect_titulo = QRectF(margin_x, 15, w * 0.5, 20)
        painter.setPen(QColor(127, 140, 141)) # Gris
        painter.drawText(rect_titulo, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "HUMEDAD")

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
        painter.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        rect_texto = QRectF(margin_x, y_barra - 65, ancho_barra, 50)
        
        painter.setPen(color_linea) # Usar el color dinámico de la línea (celeste/azul oscuro)
        painter.drawText(rect_texto, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, texto_val)
        
        # Iconos (No dibujar porque cambian el fondo limpio o se ven raros en blanco)
        # o podemos dibujar solo texto negro
        pass


        # --- 4. INTERFAZ DE CALIDAD DE AIRE (Derecha) ---
        aqi = int(self.anim_valor_ca)
        if aqi <= 50:
            estado_ca = "Bueno"
            color_ca = QColor(135, 206, 235)  # Celeste pastel
            img_ca = self.img_ca_bueno
            fallback_emoji = "🍃"
        elif aqi <= 100:
            estado_ca = "Moderado"
            color_ca = QColor(234, 179, 8)  # Amarillo
            img_ca = self.img_ca_moderado
            fallback_emoji = "☁️"
        elif aqi <= 300:
            estado_ca = "Malo"
            color_ca = QColor(249, 115, 22)  # Naranja
            img_ca = self.img_ca_malo
            fallback_emoji = "🌫️"
        else:
            estado_ca = "Crítico"
            color_ca = QColor(239, 115, 115)  # Rojo pálido/claro
            img_ca = self.img_ca_critico
            fallback_emoji = "☣️"

        # Título Calidad
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        rect_tit_ca = QRectF(w - margin_der, 15, margin_der - 10, 30)
        painter.setPen(QColor(127, 140, 141)) # Gris
        painter.drawText(rect_tit_ca, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, "CALIDAD AIRE")

        # Barra Vertical
        x_barra_v = w - 40

        y_start_v = 65
        y_end_v = h - 60
        alto_barra = y_end_v - y_start_v
        
        painter.setPen(QPen(QColor(0, 0, 0, 30), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
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
        
        # Valor AQI (ppm)
        fuente_val = QFont("Segoe UI", 14, QFont.Weight.Bold)
        if w > 350: fuente_val = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(fuente_val)
        
        # Reducimos el ancho para que no choque con la barra de humedad
        ancho_val = min(100, margin_der - 40)
        rect_val_ca = QRectF(x_barra_v - ancho_val - 20, y_end_v - 15, ancho_val, 40)
        painter.setPen(color_ca) # Usar el color del estado en lugar de negro
        painter.drawText(rect_val_ca, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, f"{aqi} ppm")

        # Estado
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        rect_est_ca = QRectF(x_barra_v - ancho_val - 10, y_end_v + 25, ancho_val, 25)
        painter.setPen(color_ca)
        painter.drawText(rect_est_ca, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, estado_ca)
        
        # EMOJI dinámico -> Imagen dinámica
        rect_icono_ca = QRectF(x_barra_v - 20, y_actual_v - 45, 40, 40)
        if not img_ca.isNull():
            painter.drawImage(rect_icono_ca, img_ca)
        else:
            painter.setFont(QFont("Segoe UI Emoji", 24))
            painter.setPen(QColor(0, 0, 0, 150))
            painter.drawText(rect_icono_ca.translated(1, 1), Qt.AlignmentFlag.AlignCenter, fallback_emoji)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect_icono_ca, Qt.AlignmentFlag.AlignCenter, fallback_emoji)


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
