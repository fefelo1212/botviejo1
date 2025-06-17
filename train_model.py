import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import logging
import os
import glob
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import MinMaxScaler

# Importamos la clase BinanceDataProcessor
from binance_data_processor import BinanceDataProcessor 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def prepare_data_for_ml_chunked(
    filepath: str,
    chunk_size_mb: int = 10, 
    overlap_candles: int = 100,
    processed_chunks_base_dir: str = "/content/drive/MyDrive/Botbinance/temp_processed_chunks",
    final_processed_csv_filename: str = "SOLUSDT_full_processed_for_ml.csv"
):
    """
    Prepara los datos para el Machine Learning leyendo el dataset grande por chunks,
    procesando cada chunk y guardándolo en Google Drive para persistencia.
    Luego, carga y concatena los chunks procesados para el entrenamiento.
    """
    # Si filepath es una lista de archivos, los concatenamos antes de procesar por chunks
    if isinstance(filepath, list):
        logging.info(f"Concatenando {len(filepath)} archivos de datos brutos SOLUSDT...")
        df_list = [pd.read_csv(f) for f in filepath]
        full_df = pd.concat(df_list, ignore_index=True)
        # Guardar temporalmente el archivo concatenado para procesamiento por chunks
        temp_concat_path = os.path.join(processed_chunks_base_dir, "SOLUSDT_full_concat.csv")
        full_df.to_csv(temp_concat_path, index=False)
        filepath = temp_concat_path
    if not os.path.exists(filepath):
        logging.error(f"Archivo de dataset no encontrado: {filepath}")
        return None, None, None, None, None, None, None

    processor = BinanceDataProcessor()
    estimated_bytes_per_row = 160
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
    csv_iterator = pd.read_csv(filepath, chunksize=chunksize_rows, iterator=True, nrows=50000)
    processed_chunk_files = []

    while True:
        chunk_filename = os.path.join(processed_chunks_base_dir, f"chunk_{chunk_idx:05d}.csv")
        if os.path.exists(chunk_filename):
            logging.info(f"Chunk {chunk_idx + 1} ya procesado y guardado: {chunk_filename}. Cargando para concatenar.")
            processed_chunk_files.append(chunk_filename)
            try:
                # Avanza el iterador para que no vuelva a procesar el mismo chunk
                # Esto es una corrección para asegurar que el iterador de CSV avance adecuadamente si el archivo ya existe.
                for _ in range(int(chunksize_rows / chunksize_rows)):
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
        
        # Aquí el procesador de datos ahora también calculará el nuevo 'target'
        processed_combined_df = processor.process_data_chunk(combined_df) 
        
        # Ajustamos el criterio de primera fila válida:
        # Ahora el target (ej. 'future_return') es clave, además de los indicadores.
        # Asumiendo que el nuevo target tendrá NaNs al final si se usa .shift(-N)
        first_valid_row_idx = processed_combined_df.dropna(
            subset=['rsi', 'sma_20', 'ema_26', 'MACD', 'MACD_SIGNAL', 'MACD_HIST', 'target'] # Indicadores y target en mayúsculas
        ).index.min()
        
        if first_valid_row_idx is None:
            logging.warning(f"Chunk {chunk_idx + 1}: No se encontraron filas válidas después del cálculo de indicadores y target. Saltando este chunk.")
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
    full_processed_df.dropna(inplace=True) # Elimina NaNs en cualquier columna, incluyendo el nuevo 'target'
    logging.info(f"Filas eliminadas por NaNs: {initial_rows - len(full_processed_df)}")
    
    # --- INICIO DE MODIFICACIONES CLAVE ---
    
    # 1. Redefinición del Target: Ahora buscamos la columna 'target' que binance_data_processor.py creará
    if 'target' in full_processed_df.columns:
        y = full_processed_df['target'] # Usamos la nueva columna 'target' como variable objetivo
    else:
        logging.error("La columna 'target' (variable objetivo) no se encuentra en el DataFrame procesado. Asegúrate de que binance_data_processor.py la cree.")
        return None, None, None, None, None, None, None

    # 2. Alineación de Features: Modificamos la lista de exclusión para ser más inteligente
    # Mantendremos 'open', 'high', 'low', 'close', 'volume' y todos los indicadores.
    # Solo excluimos columnas de metadatos o las antiguas columnas de señal/razón.
    features_to_exclude = [
        'open_time', 'close_time', 'signal_reason', 'signal_strength',
        'signal', # Excluimos la antigua columna 'signal' basada en reglas de indicadores
        'target'  # Excluimos la nueva columna 'target' de las features, ya que es la variable objetivo
    ]
    
    # Asegurarse de no excluir columnas que ya no existen o que son útiles
    X = full_processed_df.drop(columns=[col for col in features_to_exclude if col in full_processed_df.columns])
    
    # Convertir todas las columnas de X a numérico, manejando errores.
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')
    X.dropna(inplace=True) # Eliminar NaNs que pudieran aparecer por la conversión a numérico
    y = y.loc[X.index] # Asegurar que y tenga el mismo índice que X después de dropear NaNs
    
    logging.info(f"Dimensiones de X antes de escalado: {X.shape}")
    logging.info(f"Dimensiones de y antes de escalado: {y.shape}")
    logging.info(f"Columnas finales de características (X): {X.columns.tolist()}")

    # 3. Corrección de Fugas de Datos: Implementación de la división temporal (cronológica)
    # Ya no usamos train_test_split de forma aleatoria.
    train_ratio = 0.70 # 70% para entrenamiento
    val_ratio = 0.15   # 15% para validación
    test_ratio = 0.15  # 15% para prueba (test)

    # Calcular los tamaños de los splits
    total_rows_clean = len(X) # Usamos el número de filas después de dropear NaNs
    train_size = int(total_rows_clean * train_ratio)
    val_size = int(total_rows_clean * val_ratio)
    # El tamaño del test se calcula para tomar el resto y asegurar que no haya errores de redondeo
    test_size = total_rows_clean - train_size - val_size 
    
    # Realizar la división temporal
    X_train = X.iloc[:train_size]
    y_train = y.iloc[:train_size]

    X_val = X.iloc[train_size : train_size + val_size]
    y_val = y.iloc[train_size : train_size + val_size]

    X_test = X.iloc[train_size + val_size : train_size + val_size + test_size]
    y_test = y.iloc[train_size + val_size : train_size + val_size + test_size]

    logging.info(f"Forma de X_train (temporal): {X_train.shape}")
    logging.info(f"Forma de X_val (temporal): {X_val.shape}")
    logging.info(f"Forma de X_test (temporal): {X_test.shape}")
    logging.info(f"Forma de y_train (temporal): {y_train.shape}")
    logging.info(f"Forma de y_val (temporal): {y_val.shape}")
    logging.info(f"Forma de y_test (temporal): {y_test.shape}")
    
    # El escalado se mantiene igual, pero es importante que X_train, X_val, X_test sean DataFrames
    # para que el scaler mantenga los nombres de las columnas.
    scaler_X = MinMaxScaler()
    X_train_scaled = scaler_X.fit_transform(X_train)
    X_val_scaled = scaler_X.transform(X_val)
    X_test_scaled = scaler_X.transform(X_test)

    # Convertir de nuevo a DataFrame para mantener los nombres de las columnas
    X_train = pd.DataFrame(X_train_scaled, columns=X.columns, index=X_train.index)
    X_val = pd.DataFrame(X_val_scaled, columns=X.columns, index=X_val.index)
    X_test = pd.DataFrame(X_test_scaled, columns=X.columns, index=X_test.index)
    
    logging.info("Datos preparados para ML con chunks y división temporal.")
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
    
    # 4. Mitigar el Sobreajuste: Ajustamos los hiperparámetros del Random Forest
    logging.info("Aplicando SMOTE para balancear el conjunto de entrenamiento (después de la división temporal)...")
    # SMOTE ahora se aplica después de la división temporal, lo cual es correcto.
    # No es necesario usar stratify=y aquí, ya que el target '0' o '1' ya estará desbalanceado.
    smote = SMOTE(random_state=42, k_neighbors=5) 
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
    
    logging.info(f"Forma de X_train original: {X_train.shape}")
    logging.info(f"Forma de y_train original: {y_train.shape}")
    logging.info(f"Forma de X_train después de SMOTE: {X_train_resampled.shape}")
    logging.info(f"Forma de y_train después de SMOTE: {y_train_resampled.shape}")
    logging.info("Conteo de la variable objetivo en y_train_resampled:\n" + str(pd.Series(y_train_resampled).value_counts()))
    
    # Guardar el conteo de clases del target antes de SMOTE y entrenamiento
    import pandas as pd
    target_counts = pd.Series(y_train).value_counts(dropna=False)
    os.makedirs(os.path.join(BASE_DIR, 'info'), exist_ok=True)
    with open(os.path.join(BASE_DIR, 'info', 'target_value_counts.txt'), 'w') as f:
        f.write('Conteo de clases de la variable target (y_train) antes de SMOTE y entrenamiento:\n')
        f.write(str(target_counts))
    logging.info(f"Conteo de clases de la variable target guardado en info/target_value_counts.txt: {target_counts.to_dict()}")
    
    X_train = X_train_resampled
    y_train = y_train_resampled
    
    # Configuramos el modelo con hiperparámetros para reducir el sobreajuste
    model = RandomForestClassifier(
        n_estimators=100,      # Aumentamos los estimadores para mayor robustez
        max_depth=10,          # Limitamos la profundidad de los árboles
        min_samples_leaf=5,    # Mínimo de muestras por hoja para evitar hojas muy específicas
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    logging.info("Modelo Random Forest entrenado con éxito con nuevos hiperparámetros.")
    
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
    # Define la BASE_DIR para que sea la carpeta donde está este script
    BASE_DIR = os.path.dirname(__file__)

    # Buscar solo el primer archivo mensual de SOLUSDT
    RAW_DATA_DIR = os.path.join(BASE_DIR, "binance_data")
    solusdt_files = sorted(glob.glob(os.path.join(RAW_DATA_DIR, 'SOLUSDT_raw_historical_data_*.csv')))
    solusdt_files = solusdt_files[:1]  # Solo el primer archivo

    if not solusdt_files:
        raise FileNotFoundError("No se encontraron archivos SOLUSDT_raw_historical_data_*.csv en binance_data/")

    # La ruta para cargar el dataset BRUTO ahora será una lista de archivos
    BIG_DATASET_PATH = solusdt_files

    # Define las rutas de entrada/salida basándose en BASE_DIR
    PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "processed_data")
    MODELS_DIR = os.path.join(BASE_DIR, "ml_models")

    # Asegura que las carpetas de salida existan
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    # La ruta donde se guardarán los chunks procesados (temporalmente o el final si no hay concat)
    PROCESSED_DATASET_FILENAME = 'SOLUSDT_processed_small_dataset.csv'
    FINAL_PROCESSED_DATASET_PATH = os.path.join(PROCESSED_DATA_DIR, PROCESSED_DATASET_FILENAME)

    # Rutas para guardar el modelo y el escalador
    MODEL_SAVE_PATH = os.path.join(MODELS_DIR, 'random_forest_model.joblib')
    SCALER_SAVE_PATH = os.path.join(MODELS_DIR, 'min_max_scaler.joblib')

    # Llama a la función principal para entrenar y guardar el modelo y el dataset procesado
    train_and_evaluate_model(
        filepath=BIG_DATASET_PATH,
        model_filename=MODEL_SAVE_PATH,
        scaler_filename=SCALER_SAVE_PATH,
        chunk_size_mb=10, 
        overlap_candles=100,
        processed_chunks_base_dir=PROCESSED_DATA_DIR
    )
