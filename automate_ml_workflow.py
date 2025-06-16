"""
Script maestro para automatizar el flujo de entrenamiento y backtesting ML usando datos de Binance local.
- Genera el dataset con columna 'target'
- Entrena el modelo ML
- Realiza backtesting usando el modelo entrenado
- Muestra métricas y resultados
"""
import os
import subprocess
import sys
import pandas as pd
from backtesting import BacktestEngine
from strategies.machine_learning import MLStrategy
import joblib

# 1. Generar dataset con columna 'target'
print("[1/4] Generando dataset ML...")
subprocess.run([sys.executable, 'generate_ml_dataset.py'], check=True)

# 2. Entrenar modelo ML
print("[2/4] Entrenando modelo ML...")
subprocess.run([sys.executable, 'train_ml_strategy.py', '--data', 'SOLUSDT_ml_dataset.csv', '--model_output', 'models/ml_strategy.pkl'], check=True)

# 3. Backtesting usando el modelo ML
print("[3/4] Ejecutando backtesting con modelo ML...")
# Cargar modelo entrenado
model = joblib.load('models/ml_strategy.pkl')

# Definir función de estrategia ML para backtesting
def ml_strategy_fn(df):
    # Preprocesar features igual que en entrenamiento
    features = df.drop(columns=['open_time','close_time','ignore'], errors='ignore')
    features = features.dropna()
    # Predecir señales
    preds = model.predict(features)
    # Convertir a pandas Series con el mismo índice
    return pd.Series(preds, index=features.index)

# Instanciar motor de backtest
backtest = BacktestEngine(symbol='SOL/USDT', timeframe='1m', initial_balance=10000)
backtest.load_data_from_csv('SOLUSDT_ml_dataset.csv')
results = backtest.run_backtest(ml_strategy_fn)

# 4. Mostrar resultados
print("[4/4] Resultados del backtesting ML:")
for k, v in results.items():
    print(f"{k}: {v}")
backtest.plot_results()
