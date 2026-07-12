import sounddevice as sd
import numpy as np
import time

audio_buffer = []

# 1. funcion callback que captura el audio en tiempo real
def callback_audio(indata, frames, time_info, status):
    if status: 
        pass # imprimir status si quieres depurar cortes de audio
    
    # calculo del RMS (Root Mean Square) real del bloque de audio
    rms = np.sqrt(np.mean(indata**2))
    audio_buffer.append(rms)

# inicializacion del flujo de audio (cambiar channels=2 a channels=1 si el microfono es mono)
stream = sd.InputStream(channels=1, samplerate=48000, callback=callback_audio)
stream.start()

print("Iniciando lectura de micrï¿½fono...")

try:
    while True:
        # 2. procesamiento de los datos acumulados
        if audio_buffer:
            # se promedia el RMS acumulado para dar estabilidad a la lectura
            promedio_rms = np.mean(audio_buffer)
            audio_buffer.clear() 
            
            # 3. Conversion a dB
            if promedio_rms > 0:
                # modificar el + 115 para ir calibrando
                # sala en silencio debe marcar entre 35 dB y 45 dB
                db_spl = 20 * np.log10(promedio_rms) + 115
            else:
                db_spl = 0.0
                
            ruido_str = f"{db_spl:.1f} dB"
        else:
            ruido_str = "-- dB"
        
        print(f"Nivel de Ruido Ambiental: {ruido_str}")
        
        # intervalo de actualizacion del sensor
        time.sleep(2.5)

except KeyboardInterrupt:
    print("\nLectura detenida.")
finally:
    # es crucial detener el stream de audio para liberar la tarjeta de sonido
    stream.stop()
    stream.close()