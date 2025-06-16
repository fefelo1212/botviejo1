import aiohttp
import asyncio
import pandas as pd
import time
from datetime import datetime, timedelta
import logging
import platform
import sys

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- INICIO DE LA CORRECCIÓN PARA WINDOWS ---
if platform.system() == "Windows":
    # Establece la política de bucle de eventos a SelectorEventLoop para compatibilidad con aiodns
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# --- FIN DE LA CORRECCIÓN PARA WINDOWS ---

# Fecha de inicio de la descarga (la fecha más temprana disponible para 1m)
START_DATE = datetime(2020, 8, 11, 3, 0) # Fecha de inicio de la descarga (SOLUSDT 1m)

async def fetch_klines_batch(session, symbol, interval, start_time_ms, end_time_ms, limit=1000):
    """
    Fetches a batch of klines from Binance.
    start_time_ms and end_time_ms should be in milliseconds.
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time_ms,
        "endTime": end_time_ms,
        "limit": limit
    }
    
    try:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            data = await resp.json()
            if not isinstance(data, list): # Handle potential API errors where data is not a list
                logger.error(f"Error fetching klines for {symbol} from {start_time_ms} to {end_time_ms}: {data}")
                return []
            return data
    except aiohttp.ClientError as e:
        logger.error(f"Network error fetching klines: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching klines: {e}")
        return []

async def download_historical_data_in_chunks(
    symbol: str = "SOLUSDT", 
    interval: str = "1m", 
    start_date: str = "2024-01-01", # Formato YYYY-MM-DD
    end_date: str = "now", # Formato YYYY-MM-DD o "now"
    chunk_type: str = "month", # "month", "week", "day"
    output_base_filename: str = "SOLUSDT_raw_historical_data" # Sin extensión .csv
):
    """
    Downloads historical kline data from Binance for a given symbol and interval
    over a specified date range, in defined chunks (e.g., month by month),
    and saves each chunk to a separate CSV file.
    """
    logger.info(f"Iniciando descarga de datos históricos por chunks para {symbol} - {interval}...")

    # Convertir fechas de inicio y fin del rango total
    start_dt_overall = pd.to_datetime(start_date)
    end_dt_overall = pd.to_datetime(end_date) if end_date != "now" else datetime.now()

    current_chunk_start = start_dt_overall

    all_downloaded_files = []

    while current_chunk_start < end_dt_overall:
        chunk_end_dt = None
        if chunk_type == "month":
            # Calcular el final del mes actual o el final total si se excede
            next_month = current_chunk_start.replace(day=28) + timedelta(days=4) # Asegura pasar al mes siguiente
            chunk_end_dt = (next_month - timedelta(days=next_month.day)).replace(hour=23, minute=59, second=59)
            chunk_end_dt = min(chunk_end_dt, end_dt_overall)
        elif chunk_type == "week":
            chunk_end_dt = current_chunk_start + timedelta(weeks=1) - timedelta(seconds=1) # Fin de la semana
            chunk_end_dt = min(chunk_end_dt, end_dt_overall)
        elif chunk_type == "day":
            chunk_end_dt = current_chunk_start + timedelta(days=1) - timedelta(seconds=1) # Fin del día
            chunk_end_dt = min(chunk_end_dt, end_dt_overall)
        else:
            logger.error("Tipo de chunk no soportado. Usa 'month', 'week' o 'day'.")
            return []

        # Asegurarse de que no descargamos más allá de la fecha final total
        if current_chunk_start >= chunk_end_dt:
             break # Ya hemos procesado todo el rango o hay un problema con el cálculo del chunk

        logger.info(f"--- Descargando chunk: {current_chunk_start.strftime('%Y-%m-%d')} a {chunk_end_dt.strftime('%Y-%m-%d')} ---")

        start_time_ms = int(current_chunk_start.timestamp() * 1000)
        end_time_ms = int(chunk_end_dt.timestamp() * 1000)
        
        chunk_klines_data = []
        current_batch_start_time = start_time_ms
        
        # Binance limits to 1000 klines per request (approx 16.67 hours for 1m interval)
        batch_duration_ms = 1000 * 60 * 1000 # 1000 minutes = 60,000,000 ms

        async with aiohttp.ClientSession() as session:
            while current_batch_start_time < end_time_ms:
                batch_end_time = min(current_batch_start_time + batch_duration_ms, end_time_ms)
                
                logger.debug(f"  Fetching batch from {datetime.fromtimestamp(current_batch_start_time / 1000)} to {datetime.fromtimestamp(batch_end_time / 1000)}")
                
                klines = await fetch_klines_batch(
                    session, symbol, interval, current_batch_start_time, batch_end_time, limit=1000
                )
                
                if not klines:
                    logger.warning(f"  No se recibieron datos para el batch: {datetime.fromtimestamp(current_batch_start_time / 1000)} a {datetime.fromtimestamp(batch_end_time / 1000)}. Intentando avanzar.")
                    current_batch_start_time = batch_end_time # Advance anyway
                    await asyncio.sleep(2) # Pausa para evitar rate limits excesivos
                    continue

                chunk_klines_data.extend(klines)

                # Update current_batch_start_time to the timestamp of the last kline received + 1ms
                if klines:
                    current_batch_start_time = klines[-1][0] + 1
                else:
                    current_batch_time = batch_end_time # Fallback to advance if klines is empty

                await asyncio.sleep(0.5) # Small delay to respect Binance rate limits (adjust if needed)

        if not chunk_klines_data:
            logger.error(f"  No se descargaron datos para el chunk: {current_chunk_start.strftime('%Y-%m-%d')} a {chunk_end_dt.strftime('%Y-%m-%d')}. Saltando este chunk.")
            current_chunk_start = chunk_end_dt + timedelta(seconds=1) # Avanzar al siguiente chunk
            continue

        # Convertir a DataFrame y limpiar
        df = pd.DataFrame(chunk_klines_data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])

        # Convertir timestamps a datetime
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        # Convertir columnas numéricas
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 
                        'quote_asset_volume', 'number_of_trades', 
                        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Eliminar columna 'ignore' que Binance incluye pero no se usa
        df = df.drop(columns=['ignore'])

        # Generar nombre de archivo para el chunk
        chunk_filename = f"{output_base_filename}_{current_chunk_start.strftime('%Y%m%d')}_{chunk_end_dt.strftime('%Y%m%d')}.csv"
        df.to_csv(chunk_filename, index=False)
        all_downloaded_files.append(chunk_filename)
        logger.info(f"  Total de {len(df)} velas descargadas para este chunk. Guardado en {chunk_filename}")

        # Preparar para el siguiente chunk
        current_chunk_start = chunk_end_dt + timedelta(seconds=1) # Avanza 1 segundo para no solapar

    logger.info("Descarga de todos los chunks completada.")
    return all_downloaded_files

if __name__ == "__main__":
    downloaded_files = asyncio.run(download_historical_data_in_chunks(
        symbol="SOLUSDT",
        interval="1m",
        start_date=START_DATE,
        end_date="now",
        chunk_type="month", # Puedes cambiar a "week" o "day"
        output_base_filename="SOLUSDT_raw_historical_data" 
    ))
    logger.info(f"Todos los archivos descargados: {downloaded_files}")
