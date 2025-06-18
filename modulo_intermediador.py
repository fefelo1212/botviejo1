"""
Módulo Intermediador para compatibilidad de datos entre fuentes Binance y el backtesting clásico.

- Recibe archivos o DataFrames con formato Binance (open_time, open, high, low, close, volume, ...)
- Devuelve DataFrames compatibles con el backtesting clásico (timestamp, open, high, low, close, volume)
- Puede ser usado en cualquier script que requiera adaptar datos históricos para simulaciones o análisis.

Entre quiénes trabaja:
- Fuente: Archivos CSV históricos de Binance (binance_data/SOLUSDT_raw_historical_data_*.csv)
- Destino: Módulo de backtesting clásico (backtesting.py)

Uso típico:
    from modulo_intermediador import adaptar_binance_a_backtesting
    df = adaptar_binance_a_backtesting('binance_data/SOLUSDT_raw_historical_data_20200811_20200831.csv')
    # df ahora es compatible con backtesting.py
"""

import pandas as pd

def adaptar_binance_a_backtesting(file_path_or_df):
    """
    Adapta un archivo CSV o DataFrame de Binance al formato esperado por el backtesting clásico.
    Args:
        file_path_or_df: ruta al archivo CSV o DataFrame con columnas tipo Binance
    Returns:
        DataFrame con columnas: timestamp, open, high, low, close, volume
    """
    if isinstance(file_path_or_df, str):
        df = pd.read_csv(file_path_or_df)
    else:
        df = file_path_or_df.copy()
    # Renombrar open_time a timestamp
    if 'open_time' in df.columns:
        df = df.rename(columns={'open_time': 'timestamp'})
    # Filtrar solo las columnas necesarias
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    df = df[[col for col in cols if col in df.columns]]
    # Convertir timestamp a datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df
