import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib # Para guardar el modelo entrenado
import logging
import os
import glob # Para listar archivos de chunks procesados
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

# Importamos la clase BinanceDataProcessor
from binance_data_processor import BinanceDataProcessor # Asegúrate de que el archivo esté en el mismo directorio o se defina en Colab

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def prepare_data_for_ml_chunked(
    filepath: str,
    chunk_size_mb: int = 10, # Tamaño del chunk en MB, para la prueba inicial
    overlap_candles: int = 100, # Número de velas de solapamiento entre chunks
    processed_chunks_base_dir: str = "/content/drive/MyDrive/Botbinance/temp_processed_chunks", # Directorio en Drive
    final_processed_csv_filename: str = "SOLUSDT_full_processed_for_ml.csv"
):
    """
    Prepara los datos para el Machine Learning leyendo el dataset grande por chunks,
    procesando cada chunk y guardándolo en Google Drive para persistencia.
    Luego, carga y concatena los chunks procesados para el entrenamiento.
    """
    if not os.path.exists(filepath):
        logging.error(f"Archivo de dataset no encontrado: {filepath}")
        return None, None, None, None, None, None, None

    processor = BinanceDataProcessor()
    estimated_bytes_per_row = 160 # Aproximación para 20 columnas flotantes. Ajustar si el CSV es muy diferente.
    chunksize_rows = int((chunk_size_mb * 1024 * 1024) / estimated_bytes_per_row)
    if chunksize_rows < overlap_candles * 2:
        chunksize_rows = overlap_candles * 2 + 100
        logging.warning(f"Chunk size de {chunk_size_mb} MB es muy pequeño. Ajustado a {chunksize_rows} filas para asegurar el procesamiento de indicadores.")
    logging.info(f"Estimando {chunksize_rows} filas por chunk para {chunk_size_mb} MB.")

    os.makedirs(processed_chunks_base_dir, exist_ok=True)
    logging.info(f"Directorio de chunks procesados creado/verificado: {processed_chunks_base_dir}")

    header = pd.read_csv(filepath, nrows=0).columns.tolist()
    total_rows = sum(1 for line in open(filepath)) - 1
    logging.info(f"Total de filas en el dataset original: {total_rows}")

    current_start_row = 1
    chunk_idx = 0
    overlap_buffer = pd.DataFrame()
    csv_iterator = pd.read_csv(filepath, chunksize=chunksize_rows, iterator=True)
    processed_chunk_files = []

    while True:
        chunk_filename = os.path.join(processed_chunks_base_dir, f"chunk_{chunk_idx:05d}.csv")
        if os.path.exists(chunk_filename):
            logging.info(f"Chunk {chunk_idx + 1} ya procesado y guardado: {chunk_filename}. Cargando para concatenar.")
            processed_chunk_files.append(chunk_filename)
            try:
                _ = next(csv_iterator)
            except StopIteration:
                break
            current_start_row += chunksize_rows
            chunk_idx += 1
            continue
        logging.info(f"Procesando y guardando chunk {chunk_idx + 1}...")
        try:
            df_chunk = next(csv_iterator)
        except StopIteration:
            break
        df_chunk['open_time'] = pd.to_datetime(df_chunk['open_time'])
        df_chunk['close_time'] = pd.to_datetime(df_chunk['close_time'])
        combined_df = pd.concat([overlap_buffer, df_chunk]).reset_index(drop=True)
        logging.info(f"Tamaño combinado (buffer + chunk): {len(combined_df)} filas.")
        processed_combined_df = processor.process_data_chunk(combined_df)
        first_valid_row_idx = processed_combined_df.dropna(subset=['rsi', 'sma_20', 'ema_26', 'macd']).index.min()
        if first_valid_row_idx is None:
            logging.warning(f"Chunk {chunk_idx + 1}: No se encontraron filas válidas después del cálculo de indicadores. Saltando este chunk.")
            overlap_buffer = df_chunk.tail(overlap_candles).copy()
            current_start_row += len(df_chunk)
            chunk_idx += 1
            continue
        start_index_for_current_data = len(overlap_buffer)
        effective_start_idx = max(first_valid_row_idx, start_index_for_current_data)
        processed_chunk_data = processed_combined_df.iloc[effective_start_idx:]
        logging.info(f"Chunk {chunk_idx + 1} procesado. Filas útiles añadidas: {len(processed_chunk_data)}. Columnas: {processed_chunk_data.columns.tolist()}")
        processed_chunk_data.to_csv(chunk_filename, index=False)
        processed_chunk_files.append(chunk_filename)
        logging.info(f"Chunk {chunk_idx + 1} guardado en: {chunk_filename}")
        overlap_buffer = df_chunk.tail(overlap_candles).copy()
        chunk_idx += 1
        current_start_row += len(df_chunk)

    logging.info(f"Fase de procesamiento de chunks completada. Total de chunks guardados: {len(processed_chunk_files)}")
    logging.info("Cargando y concatenando todos los chunks procesados desde Google Drive...")
    existing_processed_files = sorted(glob.glob(os.path.join(processed_chunks_base_dir, "chunk_*.csv")))
    if not existing_processed_files:
        logging.error("No se encontraron chunks procesados para cargar. Algo salió mal en la fase de procesamiento.")
        return None, None, None, None, None, None, None
    full_processed_df_list = []
    for f in existing_processed_files:
        try:
            full_processed_df_list.append(pd.read_csv(f))
        except Exception as e:
            logging.error(f"Error al cargar el chunk procesado {f}: {e}")
    if not full_processed_df_list:
        logging.error("No se pudieron cargar chunks válidos para la concatenación final.")
        return None, None, None, None, None, None, None
    full_processed_df = pd.concat(full_processed_df_list, ignore_index=True)
    logging.info(f"Todos los chunks concatenados. Dimensiones del DataFrame final: {full_processed_df.shape}")
    final_csv_path = os.path.join(processed_chunks_base_dir, final_processed_csv_filename)
    try:
        full_processed_df.to_csv(final_csv_path, index=False)
        logging.info(f"DataFrame completo procesado guardado en: {final_csv_path}")
    except Exception as e:
        logging.warning(f"No se pudo guardar el DataFrame completo procesado como un solo CSV debido a: {e}. Continuamos con la preparación para ML.")
    logging.info("Preparando datos finales para entrenamiento y validación desde el DataFrame consolidado...")
    initial_rows = len(full_processed_df)
    full_processed_df.dropna(inplace=True)
    logging.info(f"Filas eliminadas por NaNs: {initial_rows - len(full_processed_df)}")
    features_to_exclude = [
        'open_time', 'close_time', 'open', 'high', 'low', 'signal_reason', 'signal_strength',
        'bb_upper', 'bb_middle', 'bb_lower',
        'volume',
        'target',
        'SMA_10', 'SMA_30', 'RSI_14', 'EMA_12', 'EMA_26', 'MACD', 'MACD_Signal', 'MACD_Hist', 'BB_SMA', 'BB_STD'
    ]
    if 'signal' in full_processed_df.columns:
        y = full_processed_df['signal']
        features_to_exclude.append('signal')
    else:
        logging.error("La columna 'signal' (variable objetivo) no se encuentra en el DataFrame procesado.")
        return None, None, None, None, None, None, None
    X = full_processed_df.drop(columns=[col for col in features_to_exclude if col in full_processed_df.columns])
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')
    X.dropna(inplace=True)
    y = y.loc[X.index]
    logging.info(f"Dimensiones de X antes de escalado: {X.shape}")
    logging.info(f"Dimensiones de y antes de escalado: {y.shape}")
    logging.info(f"Columnas finales de características (X): {X.columns.tolist()}")
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)
    logging.info(f"Forma de X_train: {X_train.shape}")
    logging.info(f"Forma de X_val: {X_val.shape}")
    logging.info(f"Forma de X_test: {X_test.shape}")
    logging.info(f"Forma de y_train: {y_train.shape}")
    logging.info(f"Forma de y_val: {y_val.shape}")
    logging.info(f"Forma de y_test: {y_test.shape}")
    scaler_X = MinMaxScaler()
    X_train = scaler_X.fit_transform(X_train)
    X_val = scaler_X.transform(X_val)
    X_test = scaler_X.transform(X_test)
    X_train = pd.DataFrame(X_train, columns=X.columns)
    X_val = pd.DataFrame(X_val, columns=X.columns)
    X_test = pd.DataFrame(X_test, columns=X.columns)
    logging.info("Datos preparados para ML con chunks.")
    return X_train, X_val, X_test, y_train, y_val, y_test, scaler_X

def train_and_evaluate_model(
    filepath: str = "/content/drive/MyDrive/Botbinance/SOLUSDT_processed_big_dataset.csv",
    model_filename: str = "/content/drive/MyDrive/Botbinance/random_forest_model.joblib",
    scaler_filename: str = "/content/drive/MyDrive/Botbinance/min_max_scaler.joblib",
    chunk_size_mb: int = 10,
    overlap_candles: int = 100,
    processed_chunks_base_dir: str = "/content/drive/MyDrive/Botbinance/temp_processed_chunks"
):
    """
    Entrena un modelo Random Forest Classifier y evalúa su rendimiento.
    Guarda el modelo entrenado y el scaler.
    """
    logging.info("Iniciando la preparación de datos para el entrenamiento del modelo usando chunks persistentes...")
    X_train, X_val, X_test, y_train, y_val, y_test, scaler_X = prepare_data_for_ml_chunked(
        filepath=filepath,
        chunk_size_mb=chunk_size_mb,
        overlap_candles=overlap_candles,
        processed_chunks_base_dir=processed_chunks_base_dir
    )
    if X_train is None:
        logging.error("No se pudieron preparar los datos en chunks. Abortando entrenamiento del modelo.")
        return
    logging.info("Datos preparados. Iniciando entrenamiento del Random Forest Classifier...")
    logging.info("Aplicando SMOTE para balancear el conjunto de entrenamiento...")
    smote = SMOTE(random_state=42, k_neighbors=5)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
    logging.info(f"Forma de X_train original: {X_train.shape}")
    logging.info(f"Forma de y_train original: {y_train.shape}")
    logging.info(f"Forma de X_train después de SMOTE: {X_train_resampled.shape}")
    logging.info(f"Forma de y_train después de SMOTE: {y_train_resampled.shape}")
    logging.info("Conteo de la variable objetivo en y_train_resampled:\n" + str(pd.Series(y_train_resampled).value_counts()))
    X_train = X_train_resampled
    y_train = y_train_resampled
    model = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    logging.info("Modelo Random Forest entrenado con éxito.")
    logging.info("\n--- Evaluando el modelo en el conjunto de VALIDACIÓN ---")
    y_val_pred = model.predict(X_val)
    logging.info(f"Accuracy (Validación): {accuracy_score(y_val, y_val_pred):.4f}")
    logging.info("Reporte de Clasificación (Validación):\n" + classification_report(y_val, y_val_pred))
    logging.info("Matriz de Confusión (Validación):\n" + str(confusion_matrix(y_val, y_val_pred)))
    logging.info("\n--- Evaluando el modelo en el conjunto de PRUEBA (Test) ---")
    y_test_pred = model.predict(X_test)
    logging.info(f"Accuracy (Prueba): {accuracy_score(y_test, y_test_pred):.4f}")
    logging.info("Reporte de Clasificación (Prueba):\n" + classification_report(y_test, y_test_pred))
    logging.info("Matriz de Confusión (Prueba):\n" + str(confusion_matrix(y_test, y_test_pred)))
    model_dir = os.path.dirname(model_filename)
    if model_dir and not os.path.exists(model_dir):
        os.makedirs(model_dir)
        logging.info(f"Directorio de modelos creado: {model_dir}")
    joblib.dump(model, model_filename)
    logging.info(f"Modelo entrenado guardado como '{model_filename}'")
    joblib.dump(scaler_X, scaler_filename)
    logging.info(f"Scaler de características guardado como '{scaler_filename}'")
    logging.info("Entrenamiento y evaluación del modelo completados.")

if __name__ == "__main__":
    BIG_DATASET_PATH = "/content/drive/MyDrive/Botbinance/SOLUSDT_processed_big_dataset.csv"
    PROCESSED_CHUNKS_DIR = "/content/drive/MyDrive/Botbinance/temp_processed_chunks"
    MODEL_SAVE_PATH = "/content/drive/MyDrive/Botbinance/random_forest_model.joblib"
    SCALER_SAVE_PATH = "/content/drive/MyDrive/Botbinance/min_max_scaler.joblib"
    train_and_evaluate_model(
        filepath=BIG_DATASET_PATH,
        model_filename=MODEL_SAVE_PATH,
        scaler_filename=SCALER_SAVE_PATH,
        chunk_size_mb=10,
        overlap_candles=100,
        processed_chunks_base_dir=PROCESSED_CHUNKS_DIR
    )
