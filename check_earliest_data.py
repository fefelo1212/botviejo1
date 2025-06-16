from binance.client import Client
from datetime import datetime
import os

# --- IMPORTANTE ---
# Puedes usar variables de entorno para las API keys, o dejar el cliente sin claves para datos públicos
# client = Client(os.environ.get('BINANCE_API_KEY'), os.environ.get('BINANCE_API_SECRET'))
client = Client()  # Para datos públicos como klines, a veces no se requieren claves.

def get_earliest_klines_date(symbol: str, interval: str) -> datetime | None:
    """
    Consulta la API de Binance para encontrar la fecha y hora más temprana
    disponible para un símbolo y un intervalo de velas dados.
    """
    try:
        # Intentamos ir muy atrás en el tiempo (Unix Epoch - 1 de enero de 1970)
        # La API de Binance automáticamente devolverá el primer dato que tenga.
        # Limitamos a 1 para obtener solo la primera vela.
        klines = client.get_historical_klines(symbol, interval, "1 Jan, 1970", limit=1)
        
        if klines:
            # La primera vela en la lista [0] contiene el open_time en milisegundos [0]
            earliest_open_time_ms = klines[0][0]
            # Convertir milisegundos a objeto datetime
            return datetime.fromtimestamp(earliest_open_time_ms / 1000)
        else:
            print(f"No se encontraron datos históricos para {symbol} en el intervalo {interval}.")
            return None
    except Exception as e:
        print(f"Error al consultar la API de Binance: {e}")
        print("Asegúrate de que el símbolo y el intervalo sean correctos y que tienes conexión a internet.")
        print("Si el error persiste, verifica tus claves API si es una cuenta restringida o IP bloqueada.")
        return None

if __name__ == "__main__":
    symbol_to_check = "SOLUSDT"
    interval_to_check = "1m" # El mismo intervalo que estás descargando (1 minuto)

    print(f"Consultando la fecha más temprana para {symbol_to_check} en intervalo {interval_to_check}...")
    earliest_date = get_earliest_klines_date(symbol_to_check, interval_to_check)

    if earliest_date:
        print(f"\nLa fecha y hora más temprana disponible para {symbol_to_check} en {interval_to_check} es: {earliest_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Puedes configurar START_DATE en datetime({earliest_date.year}, {earliest_date.month}, {earliest_date.day}) o datetime({earliest_date.year}, {earliest_date.month}, {earliest_date.day}, {earliest_date.hour}, {earliest_date.minute}) en tu script.")
    else:
        print("No se pudo determinar la fecha más temprana.")
