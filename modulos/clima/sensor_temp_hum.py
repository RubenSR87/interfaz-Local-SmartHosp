import time
import board
import adafruit_dht
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from modulos.supabase_client import enviar_lectura, enviar_lecturas_dict

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
            
            # Enviar a Supabase en una sola fila para mayor eficiencia
            payload = {}
            if temperatura_c is not None:
                payload["temperature"] = float(temperatura_c)
            if humedad is not None:
                payload["humidity"] = float(humedad)
            if payload:
                enviar_lecturas_dict(payload)
            
        except RuntimeError as error:
            print(f"Reintentando lectura: {error.args[0]}")
            time.sleep(10.0)
            continue
            
        except Exception as error:
            sensor_dht.exit()
            print("error critico")
            raise error
        
        time.sleep(10.0)
except KeyboardInterrupt:
    print('\nlectura detenida')