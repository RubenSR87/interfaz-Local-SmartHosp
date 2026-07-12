import time
import board
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin

# constantes de calibracion
VOLTAJE_ENTRADA = 5.0  # si se trabaja con 3.3V lo cambiamos 

# R0 es la "resistencia base" en aire limpio. 
# si el valor de PPM es muy ALTO, aumentamos el valor
# si el valor de PPM es muy BAJO, disminuimos el valor
R0 = 37

# configuracion
print("configuracion")
i2c = board.I2C()
ads = ADS.ADS1115(i2c)
canal_gas = AnalogIn(ads, Pin.A0)

print("modulo conectado")
print("Iniciando lectura del MQ-135. Presiona Ctrl+C para detener.\n")
print("-" * 60)

try:
    while True:
        voltaje_gas = canal_gas.voltage
        
        if voltaje_gas > 0.01:
            # 1. calculo de la resistencia
            Rs = (VOLTAJE_ENTRADA - voltaje_gas) / voltaje_gas
            
            # 2. formula algoritmica para calcular el co2
            ratio = Rs / R0
            ppm = 116.6 * (ratio ** -2.769)
            
            print(f"Voltaje: {voltaje_gas:.3f} V | CO2 Estimado: {ppm:.1f} PPM")
        else:
            print("[Advertencia] Voltaje demasiado bajo, revisa las conexiones.")

        time.sleep(2.0)

except KeyboardInterrupt:
    print("\nlectura detenida")