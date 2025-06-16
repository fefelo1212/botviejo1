import pandas as pd
import os
import logging
from features.advanced_feature_engineer import AdvancedFeatureEngineer

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_and_save_dataset(
    input_folder: str = ".", # Carpeta donde están los archivos CSV raw (por defecto, la carpeta actual)
    input_base_filename: str = "SOLUSDT_raw_historical_data", # Prefijo de los archivos generados por download_historical_data.py
    output_filename: str = "SOLUSDT_processed_big_dataset.csv"
):
    """
    Combines raw historical data CSVs, adds advanced features,
    calculates the TP/SL target, and saves the final processed dataset.
    """
    logger.info(f"Iniciando el procesamiento de datos históricos desde '{input_folder}'...")

    all_raw_files = []
    for f in os.listdir(input_folder):
        if f.startswith(input_base_filename) and f.endswith(".csv"):
            all_raw_files.append(os.path.join(input_folder, f))
    
    if not all_raw_files:
        logger.error(f"No se encontraron archivos que comiencen con '{input_base_filename}' en '{input_folder}'.")
        return

    all_raw_files.sort() # Asegura que los archivos se lean en orden cronológico
    logger.info(f"Archivos raw encontrados para procesar: {len(all_raw_files)}")

    # Cargar y concatenar todos los DataFrames
    list_dfs = []
    for filepath in all_raw_files:
        logger.info(f"Cargando {filepath}...")
        df_chunk = pd.read_csv(filepath)
        list_dfs.append(df_chunk)
    
    # Concatenar todos los DataFrames
    raw_df = pd.concat(list_dfs, ignore_index=True)
    logger.info(f"Todos los archivos raw combinados. Total de velas: {len(raw_df)}")

    # Asegurarse de que open_time sea de tipo datetime y esté ordenado
    raw_df['open_time'] = pd.to_datetime(raw_df['open_time'])
    raw_df = raw_df.sort_values('open_time').drop_duplicates(subset=['open_time'])
    # NO establecer 'open_time' como índice aquí. Lo haremos después de añadir las features.
    processed_df = raw_df  # Asignar a processed_df para seguir el flujo

    logger.info("Aplicando ingeniería de características avanzadas...")
    feature_engineer = AdvancedFeatureEngineer()
    # Pasa el DataFrame con 'open_time' como columna regular
    processed_df = feature_engineer.add_all_features(processed_df)

    # Establecer 'open_time' como índice después de que todas las características han sido añadidas
    processed_df.set_index('open_time', inplace=True)

    logger.info("Calculando la columna 'target' (TP/SL)...")
    # Parámetros del target (ajusta si es necesario)
    TP_RATIO = 0.005  # 0.5% Take Profit
    SL_RATIO = 0.002  # 0.2% Stop Loss
    TARGET_WINDOW = 20 # Número de velas hacia adelante para buscar TP/SL (aprox. 20 minutos)

    # Convertir 'close', 'high', 'low' a numérico para asegurar operaciones
    for col in ['open', 'high', 'low', 'close', 'volume']:
        processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce')

    # Calcular precios de TP y SL para cada vela
    tp_prices = processed_df['close'] * (1 + TP_RATIO)
    sl_prices = processed_df['close'] * (1 - SL_RATIO)

    # Inicializar la columna target con 0
    processed_df['target'] = 0

    # --- LÓGICA DE TARGET: RE-IMPLEMENTACIÓN SIMILAR A LA ORIGINAL, PREPARADA PARA NÚMERO GRANDE ---
    from numba import njit # Importar Numba si se va a usar

    try:
        @njit
        def _calculate_target_numba(close_prices, high_prices, low_prices, tp_ratio, sl_ratio, window):
            targets = [0] * len(close_prices)
            for i in range(len(close_prices) - window):
                current_close = close_prices[i]
                tp_price = current_close * (1 + tp_ratio)
                sl_price = current_close * (1 - sl_ratio)

                reached_tp = False
                reached_sl = False
                first_tp_idx = -1
                first_sl_idx = -1

                for j in range(i + 1, i + 1 + window):
                    if j >= len(close_prices): # Avoid index out of bounds near end
                        break
                    if high_prices[j] >= tp_price:
                        if not reached_tp:
                            reached_tp = True
                            first_tp_idx = j
                    if low_prices[j] <= sl_price:
                        if not reached_sl:
                            reached_sl = True
                            first_sl_idx = j
                    
                    if reached_tp and reached_sl:
                        break # Found both, can decide now

                if reached_tp and reached_sl:
                    if first_tp_idx <= first_sl_idx: # TP came first or at same candle
                        targets[i] = 1
                    else: # SL came first
                        targets[i] = -1
                elif reached_tp:
                    targets[i] = 1
                elif reached_sl:
                    targets[i] = -1
                else:
                    targets[i] = 0
            return targets
        # Llamar a la función Numba
        processed_df['target'] = _calculate_target_numba(
            processed_df['close'].values,
            processed_df['high'].values,
            processed_df['low'].values,
            TP_RATIO,
            SL_RATIO,
            TARGET_WINDOW
        )
        logger.info("Target TP/SL calculado usando Numba.")

    except ImportError:
        logger.warning("Numba no está instalado o falló la compilación. El cálculo del target puede ser lento.")
        # Fallback a la implementación de Pandas (más lenta)
        def _calculate_target_pandas(df, tp_ratio, sl_ratio, window):
            targets = []
            for i in range(len(df)):
                if i + window >= len(df):
                    targets.append(0) # Not enough future data
                    continue
                
                current_close = df['close'].iloc[i]
                tp_price = current_close * (1 + tp_ratio)
                sl_price = current_close * (1 - sl_ratio)
                
                future_highs = df['high'].iloc[i+1 : i+1+window]
                future_lows = df['low'].iloc[i+1 : i+1+window]
                
                reached_tp = False
                reached_sl = False
                first_tp_idx = -1
                first_sl_idx = -1

                for j_offset in range(window):
                    idx_in_df = i + 1 + j_offset
                    if idx_in_df >= len(df): break # Should not happen with outer check, but safe
                    
                    if df['high'].iloc[idx_in_df] >= tp_price:
                        if not reached_tp:
                            reached_tp = True
                            first_tp_idx = idx_in_df
                    if df['low'].iloc[idx_in_df] <= sl_price:
                        if not reached_sl:
                            reached_sl = True
                            first_sl_idx = idx_in_df
                    
                    if reached_tp and reached_sl:
                        break

                if reached_tp and reached_sl:
                    if first_tp_idx <= first_sl_idx:
                        targets.append(1)
                    else:
                        targets.append(-1)
                elif reached_tp:
                    targets.append(1)
                elif reached_sl:
                    targets.append(-1)
                else:
                    targets.append(0)
            return pd.Series(targets, index=df.index)

        processed_df['target'] = _calculate_target_pandas(processed_df, TP_RATIO, SL_RATIO, TARGET_WINDOW)
        logger.info("Target TP/SL calculado usando Pandas (puede ser lento).")

    # Asegurar que el target esté en int
    processed_df['target'] = processed_df['target'].fillna(0).astype(int)
    
    # Eliminar filas con NaN introducidos por los indicadores (al principio del dataset)
    initial_rows = len(processed_df)
    processed_df.dropna(inplace=True)
    rows_removed = initial_rows - len(processed_df)
    if rows_removed > 0:
        logger.warning(f"Se eliminaron {rows_removed} filas al principio del dataset debido a valores NaN de indicadores.")

    logger.info(f"Dataset final procesado. Filas restantes: {len(processed_df)}")
    logger.info(f"Conteo de la columna 'target' final: \n{processed_df['target'].value_counts()}")

    processed_df.to_csv(output_filename, index=True) # Guardar con el índice de tiempo
    logger.info(f"Dataset procesado guardado en {output_filename}")

if __name__ == "__main__":
    # Asegúrate de que 'input_folder' sea la ruta correcta donde se guardaron los CSVs por chunk.
    # Si están en la misma carpeta que este script, '.' es correcto.
    process_and_save_dataset(
        input_folder=".", 
        input_base_filename="SOLUSDT_raw_historical_data",
        output_filename="SOLUSDT_processed_big_dataset.csv"
    )
