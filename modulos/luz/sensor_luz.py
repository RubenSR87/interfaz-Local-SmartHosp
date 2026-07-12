import time
import board
import adafruit_bh1750

i2c = board.I2C()
# inicializar sensor
sensor_luz = adafruit_bh1750.BH1750(i2c)

print("Iniciando lectura. Presiona Ctrl+C para detener.\n")
try:
    while True:
        try:
            # la propiedad .lux extrae el valor directamente
            nivel_luz = sensor_luz.lux
            print(f"Nivel de iluminacion: {nivel_luz:.2f} Lux")
            
        except Exception as error:
            print(f"Error al leer el sensor: {error}")
            
        time.sleep(1.0)
except KeyboardInterrupt:
    print('\nlectura detenida')
