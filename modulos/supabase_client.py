import requests
import json
import threading
import os

SUPABASE_URL = "https://mlurfiaujxxeclqoxnpw.supabase.co"
SUPABASE_KEY = "sb_publishable_qe05FiqVkD3Qogk-2koIIg_uOnIAM_w"

# Lista de IDs de salas válidas (según la configuración de métricas de React)
VALID_ROOM_IDS = {
    "hosp", "recu", "quim_ad", "quim_ni", "espera",
    "personal", "jefatura", "corredor", "consultorio",
    "reunion", "observacion", "hidratacion"
}

def obtener_room_id():
    """
    Lee el archivo config.json en la raíz del proyecto para obtener el room_id configurado.
    Si no existe o no es válido, retorna 'hosp'.
    """
    dir_path = os.path.dirname(os.path.abspath(__file__))
    root_path = os.path.abspath(os.path.join(dir_path, ".."))
    config_file = os.path.join(root_path, "config.json")
    
    room_id = "hosp"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                room_id = config.get("room_id", "hosp")
        except Exception:
            room_id = "hosp"
            
    if room_id not in VALID_ROOM_IDS:
        return "hosp"
    return room_id

# Inicializar la variable global cargando el estado persistido
CURRENT_ROOM_ID = obtener_room_id()

# Mapeo de nombres de sensores a columnas de la tabla 'sensor_readings'
COLUMN_MAPPING = {
    "temperatura": "temperature",
    "humedad": "humidity",
    "ruido": "noise_level",
    "luz": "light_level",
    "lux": "light_level",           # <-- AÑADIDO PARA QUE RECONOZCA 'lux'
    "co2": "gas_level",
    "calidad_aire": "gas_level",    # <-- AÑADIDO PARA QUE RECONOZCA 'calidad_aire'
    "aforo": "people_count"
}

# Creación de una sesión HTTP global con Keep-Alive habilitado.
session = requests.Session()
session.headers.update({
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
})

def actualizar_room_id(nuevo_room_id):
    """
    Actualiza dinámicamente el room_id en memoria para los siguientes envíos de red.
    """
    global CURRENT_ROOM_ID
    if nuevo_room_id in VALID_ROOM_IDS:
        CURRENT_ROOM_ID = nuevo_room_id
        print(f"[Supabase Sync] room_id en memoria actualizado a: {CURRENT_ROOM_ID}")
    else:
        print(f"[Supabase Sync] Intento de establecer room_id no válido: {nuevo_room_id}")

def _enviar_lecturas_dict_sync(data_dict):
    """
    Realiza la petición POST de manera síncrona dentro del hilo secundario.
    """
    url = f"{SUPABASE_URL}/rest/v1/sensor_readings"
    try:
        response = session.post(url, json=data_dict, timeout=4.0)
        if response.status_code not in (200, 201):
            print(f"[Supabase Sync] Error {response.status_code} al enviar datos: {response.text}")
        else:
            print(f"[Supabase Sync] Sincronizado en 'sensor_readings': {data_dict}")
    except Exception as e:
        print(f"[Supabase Sync] Error de conexión: {str(e)}")

def enviar_lecturas_dict(data_dict):
    """
    Envía un diccionario de mediciones a la tabla 'sensor_readings' en un hilo de fondo.
    Limpia y castea los tipos de datos para cumplir con la definición de la base de datos de PostgreSQL.
    """
    global CURRENT_ROOM_ID

    cleaned_dict = {}
    for k, v in data_dict.items():
        if v is None:
            continue
        # PostgreSQL no permite insertar flotantes en columnas enteras
        if k == "people_count":
            try:
                cleaned_dict[k] = int(round(float(v)))
            except (ValueError, TypeError):
                pass
        else:
            try:
                cleaned_dict[k] = float(v)
            except (ValueError, TypeError):
                pass

    if cleaned_dict:
        # Inyectar la sala correspondiente a este dispositivo
        cleaned_dict["room_id"] = CURRENT_ROOM_ID
        
        t = threading.Thread(target=_enviar_lecturas_dict_sync, args=(cleaned_dict,))
        t.daemon = True
        t.start()

def enviar_lectura(sensor_name, valor):
    """
    Mapea un sensor individual a su respectiva columna e inserta un registro de forma asíncrona.
    """
    col = COLUMN_MAPPING.get(sensor_name)
    if not col:
        print(f"[Supabase Sync] Nombre de sensor no reconocido: {sensor_name}")
        return
    enviar_lecturas_dict({col: valor})
