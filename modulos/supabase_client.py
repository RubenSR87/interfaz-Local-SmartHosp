import requests
import json

SUPABASE_URL = "https://mlurfiaujxxeclqoxnpw.supabase.co"
SUPABASE_KEY = "sb_publishable_qe05FiqVkD3Qogk-2koIIg_uOnIAM_w"

# Mapeo de nombres de sensores a columnas de la tabla 'sensor_readings'
COLUMN_MAPPING = {
    "temperatura": "temperature",
    "humedad": "humidity",
    "ruido": "noise_level",
    "luz": "light_level",
    "co2": "gas_level",
    "aforo": "people_count"
}

def enviar_lecturas_dict(data_dict):
    """
    Envía un diccionario de mediciones a la tabla 'sensor_readings' en Supabase.
    Ejemplo: {"temperature": 24.5, "humidity": 55.0}
    """
    url = f"{SUPABASE_URL}/rest/v1/sensor_readings"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        response = requests.post(url, headers=headers, json=data_dict, timeout=3.0)
        if response.status_code not in (200, 201):
            print(f"[Supabase Sync] Error {response.status_code} al enviar datos: {response.text}")
        else:
            print(f"[Supabase Sync] Sincronizado en 'sensor_readings': {data_dict}")
    except Exception as e:
        print(f"[Supabase Sync] Error de conexión: {str(e)}")

def enviar_lectura(sensor_name, valor):
    """
    Mapea un sensor individual a su respectiva columna e inserta un registro.
    """
    col = COLUMN_MAPPING.get(sensor_name)
    if not col:
        print(f"[Supabase Sync] Nombre de sensor no reconocido: {sensor_name}")
        return
    enviar_lecturas_dict({col: float(valor)})
