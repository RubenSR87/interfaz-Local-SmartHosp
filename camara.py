import cv2
import time
from ultralytics import YOLO

# 1. carga del modelo ia
print("cargando modelo YOLO.....")
modelo = YOLO('yolo11n.pt') 

# 2. configuracion de la camara
print("conectando camara")

# 0 indica la cï¿½mara web predeterminada (USB)
cap = cv2.VideoCapture(0)

# Reducir resoluciï¿½n de captura de la webcam ayuda al rendimiento de la Pi
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("Error crï¿½tico: No se pudo conectar a la cï¿½mara.")
    exit()

print("ï¿½Sistema listo y monitoreando! Presiona 'q' en la ventana de video para salir.")

# ==========================================
# VARIABLES DE CONTROL
# ==========================================
INTERVALO_SEGUNDOS = 5
tiempo_ultima_captura = time.time() - INTERVALO_SEGUNDOS 
ultimos_resultados = None
aforo_actual = 0

# ==========================================
# 3. BUCLE PRINCIPAL (Video en vivo + Inferencia cada 5s)
# ==========================================
while True:
    # Leemos todos los frames para mantener el video fluido
    ret, frame = cap.read()
    
    if not ret:
        print("No se pudo leer el frame de la cï¿½mara web. Reintentando...")
        time.sleep(1)
        continue

    tiempo_actual = time.time()
    
    # --- ZONA DE PROCESAMIENTO IA (Cada 5 segundos) ---
    if (tiempo_actual - tiempo_ultima_captura) >= INTERVALO_SEGUNDOS:
        # OPTIMIZACIï¿½N PI: reducimos imgsz a 320 para aliviar la carga del procesador
        resultados = modelo.predict(frame, classes=[0], conf=0.45, imgsz=320, verbose=False)
        
        ultimos_resultados = resultados[0]
        aforo_actual = len(ultimos_resultados.boxes)
        
        print(f"[ {time.strftime('%H:%M:%S')} ] Aforo actualizado: {aforo_actual} personas")
        tiempo_ultima_captura = tiempo_actual

    # --- ZONA DE VISUALIZACIï¿½N CONTINUA ---
    if ultimos_resultados is not None:
        frame_anotado = ultimos_resultados.plot(img=frame.copy())
    else:
        frame_anotado = frame.copy()

    # Agregamos los textos sobre el video que sigue corriendo
    cv2.putText(frame_anotado, f"AFORO: {aforo_actual}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
    cv2.putText(frame_anotado, f"Act: {time.strftime('%H:%M:%S')}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    
    # Mantenemos a 640x480 para no forzar a la Pi a reescalar muy grande
    frame_redimensionado = cv2.resize(frame_anotado, (640, 480))
    
    try:
        cv2.imshow("Monitor de Aforo - EZVIZ", frame_redimensionado)
    except cv2.error:
        # Protecciï¿½n por si estï¿½s corriendo el cï¿½digo por SSH sin entorno de escritorio
        print("[AVISO] No se pudo abrir la ventana de video. Asegï¿½rate de tener un monitor conectado a la Raspberry Pi.")
        pass # El cï¿½digo seguirï¿½ contando por consola aunque no haya ventana

    # Condiciï¿½n de salida
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("Cerrando el sistema...")
        break

# Limpieza final
cap.release()
cv2.destroyAllWindows()