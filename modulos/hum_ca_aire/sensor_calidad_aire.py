import os
import sys
import time

import board
import adafruit_ads1x15.ads1115 as ADS

from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin


# Permite importar módulos desde la raíz del proyecto.
RUTA_PROYECTO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

if RUTA_PROYECTO not in sys.path:
    sys.path.append(RUTA_PROYECTO)


try:
    from modulos.supabase_client import enviar_lectura
except ImportError:
    enviar_lectura = None


class SensorCalidadAire:
    """
    Lectura del sensor MQ-135 mediante el ADC ADS1115.

    Este archivo no ejecuta ciclos infinitos cuando se importa desde
    el dashboard. El widget puede llamar a leer() periódicamente.
    """

    def __init__(
        self,
        voltaje_entrada: float = 5.0,
        r0: float = 14.5,  # TODO: Reemplaza este valor con tu R0 calibrado en aire limpio
        rl: float = 10.0,  # Resistencia de carga (RL) del módulo (típicamente 10k o 1k)
        enviar_supabase: bool = True,
    ):
        self.voltaje_entrada = voltaje_entrada
        self.r0 = r0
        self.rl = rl
        self.enviar_supabase = enviar_supabase

        self.i2c = board.I2C()
        self.ads = ADS.ADS1115(self.i2c)

        # Entrada A0 del ADS1115.
        self.canal_gas = AnalogIn(self.ads, Pin.A0)

        print("[MQ-135] Sensor de calidad de aire conectado.")

    def leer(self) -> dict:
        """
        Realiza una sola lectura.

        Retorna:
            {
                "voltaje": float,
                "rs": float,
                "ratio": float,
                "ppm": float
            }
        """

        voltaje_gas = self.canal_gas.voltage

        if voltaje_gas <= 0.01:
            raise RuntimeError(
                "Voltaje demasiado bajo. Revisa las conexiones del MQ-135."
            )

        if voltaje_gas >= self.voltaje_entrada:
            raise RuntimeError(
                "El voltaje leído es igual o superior al voltaje de entrada."
            )

        # Cálculo corregido: Se incluye la resistencia de carga (RL) para obtener Rs
        rs = self.rl * ((self.voltaje_entrada - voltaje_gas) / voltaje_gas)

        ratio = rs / self.r0

        if ratio <= 0:
            raise RuntimeError("El ratio Rs/R0 no es válido.")

        # Ecuación empírica para estimación de ppm en MQ-135
        ppm = 116.6 * (ratio ** -2.769)

        datos = {
            "voltaje": round(voltaje_gas, 3),
            "rs": round(rs, 4),
            "ratio": round(ratio, 4),
            "ppm": round(ppm, 1),
        }

        return datos

    def leer_ppm(self) -> float:
        """
        Devuelve solamente el valor que necesita el widget.
        """
        return self.leer()["ppm"]

    def leer_y_enviar(self) -> dict:
        """
        Realiza una lectura y la envía a Supabase si está habilitado.
        """
        datos = self.leer()

        if self.enviar_supabase and enviar_lectura is not None:
            try:
                enviar_lectura("co2", datos["ppm"])
            except Exception as error:
                # Un fallo de Internet no debe detener el dashboard.
                print(
                    f"[Supabase] No se pudo enviar la lectura: {error}"
                )

        return datos


def ejecutar_prueba() -> None:
    """
    Solo se ejecuta al abrir este archivo directamente.
    No se ejecuta cuando el dashboard lo importa.
    """

    sensor = SensorCalidadAire()

    print("Iniciando prueba del MQ-135.")
    print("Presiona Ctrl+C para detener.\n")
    print("-" * 60)

    try:
        while True:
            try:
                datos = sensor.leer_y_enviar()

                print(
                    f"Voltaje: {datos['voltaje']:.3f} V | "
                    f"Rs: {datos['rs']:.4f} kΩ | "
                    f"Calidad de aire estimada: "
                    f"{datos['ppm']:.1f} ppm"
                )

            except Exception as error:
                print(f"[MQ-135] Error de lectura: {error}")

            time.sleep(10.0)

    except KeyboardInterrupt:
        print("\nLectura detenida.")


if __name__ == "__main__":
    ejecutar_prueba()