import pandas as pd
import logging
import os
from typing import List

# Importar la clase BinanceDataProcessor que contiene calculate_sma
from binance_data_processor import BinanceDataProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_sma_cross_signal(df: pd.DataFrame, fast_period: int = 10, slow_period: int = 50) -> pd.Series:
    """
    Genera señales de trading basadas en el cruce de dos medias móviles simples (SMA).
    Retorna:
    1 para señal de compra (cruce alcista: SMA rápida cruza por encima de la SMA lenta)
    -1 para señal de venta (cruce bajista: SMA rápida cruza por debajo de la SMA lenta)
    0 para no señal
    """
    if f'sma_{fast_period}' not in df.columns or f'sma_{slow_period}' not in df.columns:
        logging.error(f"SMAs {fast_period} o {slow_period} no encontradas en el DataFrame. Por favor, calcula las SMAs primero.")
        return pd.Series([0] * len(df), index=df.index)

    signals = pd.Series(0, index=df.index)

    # Condición de cruce alcista (compra)
    buy_condition = (df[f'sma_{fast_period}'].shift(1) < df[f'sma_{slow_period}'].shift(1)) & \
                    (df[f'sma_{fast_period}'] > df[f'sma_{slow_period}'])

    # Condición de cruce bajista (venta)
    sell_condition = (df[f'sma_{fast_period}'].shift(1) > df[f'sma_{slow_period}'].shift(1)) & \
                     (df[f'sma_{fast_period}'] < df[f'sma_{slow_period}'])

    signals.loc[buy_condition] = 1
    signals.loc[sell_condition] = -1

    logging.info(f"Señales de cruce de SMA ({fast_period}/{slow_period}) generadas.")
    return signals

if __name__ == "__main__":
    logging.info("Iniciando prueba de generación de señales con SMA.")

    # --- Parte 1: Cargar el Dataset (usando la ruta ABSOLUTA para Colab) ---
    filepath_dataset = "/content/drive/MyDrive/Botbinance/SOLUSDT_processed_big_dataset.csv"

    df_data = None
    try:
        df_data = pd.read_csv(filepath_dataset)
        logging.info(f"Dataset cargado desde: {filepath_dataset}. Filas: {len(df_data)}")
    except FileNotFoundError:
        logging.error(f"ERROR: El archivo '{filepath_dataset}' no se encontró. Asegúrate de que esté en tu Google Drive.")
        logging.info("Usando datos de prueba generados para demostración LOCAL.")
        data = {'open': [100, 102, 101, 105, 103, 106, 104, 107, 109, 108, 110, 112, 111, 115, 113, 114, 116, 115, 118, 117],
                'high': [103, 103, 102, 106, 104, 107, 105, 108, 110, 109, 111, 113, 112, 116, 114, 115, 117, 116, 119, 118],
                'low': [99, 101, 100, 104, 102, 105, 103, 106, 108, 107, 109, 111, 110, 114, 112, 113, 115, 114, 117, 116],
                'close': [101, 102, 101, 105, 103, 106, 104, 107, 109, 108, 110, 112, 111, 115, 113, 114, 116, 115, 118, 117],
                'volume': [100, 120, 110, 130, 115, 140, 125, 150, 135, 160, 145, 170, 155, 180, 165, 175, 185, 190, 195, 200]}
        df_data = pd.DataFrame(data)
        logging.info("Usando DataFrame de prueba para demostración.")

    if df_data is not None:
        # --- Parte 2: Calcular SMAs usando tu BinanceDataProcessor ---
        processor = BinanceDataProcessor()
        df_with_sma = processor.calculate_sma(df_data.copy(), periods=[10, 50])

        logging.info("DataFrame con SMAs calculadas:")
        logging.info(df_with_sma[['close', 'sma_10', 'sma_50']].head())

        # --- Parte 3: Generar Señales ---
        signals = generate_sma_cross_signal(df_with_sma, fast_period=10, slow_period=50)

        # --- Parte 4: Mostrar Resultados (ejemplo) ---
        df_with_sma['signal'] = signals
        logging.info("\nPrimeros 20 precios, SMAs y señales:")
        logging.info(df_with_sma[['close', 'sma_10', 'sma_50', 'signal']].head(20).to_string())

        logging.info("\nÚltimos 20 precios, SMAs y señales:")
        logging.info(df_with_sma[['close', 'sma_10', 'sma_50', 'signal']].tail(20).to_string())

        buy_signals_count = (signals == 1).sum()
        sell_signals_count = (signals == -1).sum()
        no_signals_count = (signals == 0).sum()

        logging.info(f"\nResumen de señales:")
        logging.info(f"Señales de Compra (1): {buy_signals_count}")
        logging.info(f"Señales de Venta (-1): {sell_signals_count}")
        logging.info(f"Sin Señal (0): {no_signals_count}")

    logging.info("Prueba de generación de señales con SMA finalizada.")
