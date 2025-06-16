# train_ml_strategy.py
"""
Script para entrenar, validar y guardar modelos de Machine Learning para estrategias de trading.

Uso:
    python train_ml_strategy.py --data SOLUSDT_ml_dataset.csv --model_output models/ml_strategy.pkl

Este script NO ejecuta trading real, solo entrena y guarda el modelo ML.
"""
import argparse
import pandas as pd
import joblib
from strategies.machine_learning import MLStrategy

# Argumentos de línea de comandos
def parse_args():
    parser = argparse.ArgumentParser(description="Entrenamiento de modelo ML para trading bot")
    parser.add_argument('--data', type=str, required=True, help='Ruta al archivo de datos históricos (CSV/JSON)')
    parser.add_argument('--model_output', type=str, default='models/ml_strategy.pkl', help='Ruta para guardar el modelo entrenado')
    return parser.parse_args()

def main():
    args = parse_args()
    # Cargar datos históricos
    if args.data.endswith('.csv'):
        data = pd.read_csv(args.data)
    elif args.data.endswith('.json'):
        data = pd.read_json(args.data)
    else:
        raise ValueError('Formato de datos no soportado')

    # Separar features y etiquetas (ajustar según tu dataset)
    X = data.drop(columns=['target'])
    # Eliminar columnas no numéricas e irrelevantes
    X = X.drop(columns=['open_time', 'close_time', 'ignore', 'future_close'], errors='ignore')
    y = data['target']

    # Inicializar y entrenar el modelo ML
    ml_strategy = MLStrategy()
    # Entrenar directamente con X e y, sin recalcular target
    ml_strategy.train(X, y)

    # Validar el modelo (puedes agregar validación cruzada, métricas, etc.)
    score = ml_strategy.model.score(X, y)
    print(f"Precisión del modelo en entrenamiento: {score:.4f}")

    # Guardar el modelo entrenado
    joblib.dump(ml_strategy.model, args.model_output)
    print(f"Modelo guardado en {args.model_output}")

if __name__ == "__main__":
    main()