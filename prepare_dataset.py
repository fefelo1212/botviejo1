import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import logging
import os

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def prepare_data_for_ml(filepath="SOLUSDT_processed_big_dataset.csv", validation_split=0.15, test_split=0.15):
    """
    Carga el dataset procesado, separa características y objetivo,
    realiza una división temporal (train/validation/test) y escala las características.

    Args:
        filepath (str): Ruta al archivo CSV del dataset procesado.
        validation_split (float): Proporción del dataset para el conjunto de validación.
        test_split (float): Proporción del dataset para el conjunto de prueba.

    Returns:
        tuple: (X_train_scaled, X_val_scaled, X_test_scaled, y_train, y_val, y_test, scaler_X)
               Donde X son las características escaladas y y son las variables objetivo.
               scaler_X es el objeto scaler usado para transformar nuevos datos.
    """
    if not os.path.exists(filepath):
        logging.error(f"Error: El archivo '{filepath}' no se encontró. Asegúrate de haber ejecutado process_historical_data.py.")
        return None, None, None, None, None, None, None

    logging.info(f"Cargando el dataset desde '{filepath}'...")
    df = pd.read_csv(filepath)
    logging.info(f"Dataset cargado. Filas totales: {len(df)}")

    # Asegúrate de que 'open_time' sea un datetime para una correcta división temporal
    df['open_time'] = pd.to_datetime(df['open_time'])
    df = df.sort_values(by='open_time').reset_index(drop=True)

    # Identificar características (X) y variable objetivo (y)
    # Excluimos 'open_time', 'close_time', y otras columnas raw que no son features
    features = [col for col in df.columns if col not in ['open_time', 'close_time',
                                                          'open', 'high', 'low', 'close', 'volume',
                                                          'quote_asset_volume', 'number_of_trades',
                                                          'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                                                          'target']]
    X = df[features]
    y = df['target']

    logging.info(f"Características seleccionadas: {features}")
    logging.info(f"Variable objetivo: 'target'")

    # --- División temporal del dataset (Train / Validation / Test) ---
    # Calculamos los tamaños de los conjuntos
    total_len = len(df)
    test_len = int(total_len * test_split)
    validation_len = int(total_len * validation_split)
    train_len = total_len - test_len - validation_len

    logging.info(f"Tamaño total del dataset: {total_len} filas")
    logging.info(f"Tamaño del conjunto de entrenamiento: {train_len} filas")
    logging.info(f"Tamaño del conjunto de validación: {validation_len} filas")
    logging.info(f"Tamaño del conjunto de prueba: {test_len} filas")

    # Dividir el dataset manteniendo el orden cronológico
    X_train, y_train = X[:train_len], y[:train_len]
    X_val, y_val = X[train_len:train_len + validation_len], y[train_len:train_len + validation_len]
    X_test, y_test = X[train_len + validation_len:], y[train_len + validation_len:]

    logging.info("Dataset dividido en entrenamiento, validación y prueba (temporalmente).")

    # --- Escalado de características ---
    # Se escala solo X (las características), no y (la variable objetivo)
    # Es crucial que el scaler se entrene SOLO con el conjunto de entrenamiento para evitar filtraciones de datos
    scaler_X = MinMaxScaler()

    logging.info("Escalando características usando MinMaxScaler...")
    X_train_scaled = scaler_X.fit_transform(X_train)
    X_val_scaled = scaler_X.transform(X_val) # Usar transform, no fit_transform
    X_test_scaled = scaler_X.transform(X_test) # Usar transform, no fit_transform

    logging.info("Características escaladas con éxito.")

    return X_train_scaled, X_val_scaled, X_test_scaled, y_train, y_val, y_test, scaler_X

if __name__ == "__main__":
    X_train, X_val, X_test, y_train, y_val, y_test, scaler = prepare_data_for_ml()

    if X_train is not None:
        logging.info("\n--- Resumen de los Datasets ---")
        logging.info(f"Forma de X_train (escalado): {X_train.shape}")
        logging.info(f"Forma de y_train: {y_train.shape}")
        logging.info(f"Forma de X_val (escalado): {X_val.shape}")
        logging.info(f"Forma de y_val: {y_val.shape}")
        logging.info(f"Forma de X_test (escalado): {X_test.shape}")
        logging.info(f"Forma de y_test: {y_test.shape}")

        logging.info("\n--- Conteo de la variable objetivo en cada conjunto ---")
        logging.info("y_train conteo:\n" + str(y_train.value_counts()))
        logging.info("y_val conteo:\n" + str(y_val.value_counts()))
        logging.info("y_test conteo:\n" + str(y_test.value_counts()))

        logging.info("\nDataset listo para el entrenamiento del modelo.")
