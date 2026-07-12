import time
import board
import adafruit_dht

# se inicializa el sensor DHT11 en el pin GPIO 4
sensor_dht = adafruit_dht.DHT11(board.D4)

print("Iniciando lectura del DHT11 en VS Code...")
print("Presiona Ctrl+C en la terminal para detener el programa.\n")
try:
    while True:
        try:
            # extraccion de los datos del sensor
            temperatura_c = sensor_dht.temperature
            humedad = sensor_dht.humidity
            
            print(f"Temperatura: {temperatura_c:.1f} C  |  Humedad: {humedad}%")
            
        except RuntimeError as error:
            print(f"Reintentando lectura: {error.args[0]}")
            time.sleep(2.0)
            continue
            
        except Exception as error:
            sensor_dht.exit()
            print("error critico")
            raise error
        
        time.sleep(2.0)
except KeyboardInterrupt:
    print('\nlectura detenida')