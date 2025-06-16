import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib # Para guardar el modelo entrenado
import logging
import os
from prepare_dataset import prepare_data_for_ml # Importamos la función que ya creamos
from imblearn.over_sampling import SMOTE

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def train_and_evaluate_model(
    filepath="SOLUSDT_processed_big_dataset.csv",
    model_filename="random_forest_model.joblib",
    scaler_filename="min_max_scaler.joblib"
):
    """
    Entrena un modelo Random Forest Classifier y evalúa su rendimiento.
    Guarda el modelo entrenado y el scaler.

    Args:
        filepath (str): Ruta al archivo CSV del dataset procesado.
        model_filename (str): Nombre del archivo para guardar el modelo entrenado.
        scaler_filename (str): Nombre del archivo para guardar el scaler.
    """
    logging.info("Iniciando la preparación de datos para el entrenamiento del modelo...")
    X_train, X_val, X_test, y_train, y_val, y_test, scaler_X = prepare_data_for_ml(filepath=filepath)

    if X_train is None:
        logging.error("No se pudieron preparar los datos. Abortando entrenamiento del modelo.")
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

    # Ahora el modelo se entrenará con los datos re-balanceados
    X_train = X_train_resampled
    y_train = y_train_resampled

    # Inicialización y entrenamiento del modelo Random Forest
    # n_estimators: número de árboles en el bosque
    # random_state: para reproducibilidad de resultados
    model = RandomForestClassifier(n_estimators=50, random_state=42) # Eliminamos class_weight='balanced'
    model.fit(X_train, y_train)

    logging.info("Modelo Random Forest entrenado con éxito.")

    # --- Evaluación del modelo ---
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

    # --- Guardar el modelo y el scaler ---
    # Guardar el modelo entrenado
    joblib.dump(model, model_filename)
    logging.info(f"Modelo entrenado guardado como '{model_filename}'")

    # Guardar el scaler de características
    joblib.dump(scaler_X, scaler_filename)
    logging.info(f"Scaler de características guardado como '{scaler_filename}'")

    logging.info("Entrenamiento y evaluación del modelo completados.")

if __name__ == "__main__":
    train_and_evaluate_model()
