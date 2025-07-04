import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from backtesting.engine import TradingSimulator

# --- RUTAS DE ARCHIVOS (Ajustar si es necesario la base) ---
# BASE_DIR será la carpeta donde se encuentre este script (ej: C:\proyectos\MODULO BINANCE\botviejo1)
BASE_DIR = os.path.dirname(__file__)

# Rutas para datos y modelos (asumiendo que están en subcarpetas)
DATA_DIR = os.path.join(BASE_DIR, "processed_data") # O "data" si así se llama tu carpeta de datos
MODELS_DIR = os.path.join(BASE_DIR, "ml_models")    # O "models" si así se llama tu carpeta de modelos

MODEL_PATH = os.path.join(MODELS_DIR, 'random_forest_model.joblib')
SCALER_PATH = os.path.join(MODELS_DIR, 'min_max_scaler.joblib')
HISTORICAL_DATA_PATH = os.path.join(DATA_DIR, 'SOLUSDT_processed_small_dataset.csv')

OUTPUT_RESULTS_DIR = os.path.join(BASE_DIR, "backtest_results") # Carpeta para resultados

INITIAL_CAPITAL = 10000.0
LEVERAGE = 1.0
COMMISSION_RATE = 0.00075

if __name__ == "__main__":
    print("Iniciando Backtest del Modelo de Machine Learning...")

    # Crear directorios si no existen
    os.makedirs(OUTPUT_RESULTS_DIR, exist_ok=True)
    # No creamos DATA_DIR o MODELS_DIR aquí, asumimos que el proceso de
    # pre-procesamiento o entrenamiento ya los crea y llena.

    for path in [MODEL_PATH, SCALER_PATH, HISTORICAL_DATA_PATH]:
        if not os.path.exists(path):
            print(f"Error: Archivo no encontrado: {path}")
            print(f"Por favor, asegúrate de que el archivo '{os.path.basename(path)}' exista en '{os.path.dirname(path)}'.")
            print("Si es tu primera ejecución, podrías necesitar generar los datos procesados y entrenar el modelo primero.")
            exit()
    # Instanciar TradingSimulator (en Colab, debe estar definida globalmente)
    simulator = TradingSimulator(
        initial_balance=INITIAL_CAPITAL,
        leverage=LEVERAGE,
        commission=COMMISSION_RATE
    )
    try:
        simulator.load_ml_model(MODEL_PATH, SCALER_PATH)
    except Exception as e:
        print(f"Fallo al cargar modelo/scaler: {e}")
        exit()
    print(f"Cargando datos históricos desde: {HISTORICAL_DATA_PATH}")
    try:
        df_historical = pd.read_csv(HISTORICAL_DATA_PATH)
        df_historical['open_time'] = pd.to_datetime(df_historical['open_time'])
        df_historical.set_index('open_time', inplace=True)
        print(f"Datos históricos cargados: {len(df_historical)} velas.")
    except Exception as e:
        print(f"Fallo al cargar o procesar datos históricos: {e}")
        exit()
    print("Ejecutando simulación de trading con el modelo ML...")
    trades_df, equity_curve_series = simulator.run_ml_backtest(df_historical)
    print("\n--- RESUMEN DEL BACKTEST ---")
    metrics = simulator.calculate_metrics()
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    print("\n--- TRADES EJECUTADOS (Primeros 10 y Últimos 10) ---")
    if not trades_df.empty:
        print(trades_df.head(10))
        if len(trades_df) > 10:
            print("...")
            print(trades_df.tail(10))
    else:
        print("No se ejecutaron trades.")
    os.makedirs(OUTPUT_RESULTS_DIR, exist_ok=True)
    trades_output_path = os.path.join(OUTPUT_RESULTS_DIR, 'ml_backtest_trades.csv')
    equity_output_path = os.path.join(OUTPUT_RESULTS_DIR, 'ml_backtest_equity_curve.csv')
    trades_df.to_csv(trades_output_path, index=False)
    equity_curve_series.to_csv(equity_output_path)
    print(f"\nResultados guardados en '{OUTPUT_RESULTS_DIR}/ml_backtest_trades.csv' y '{OUTPUT_RESULTS_DIR}/ml_backtest_equity_curve.csv'")
    if not equity_curve_series.empty:
        plt.figure(figsize=(15, 8))
        plt.plot(equity_curve_series.index, equity_curve_series, label='Capital del Bot', color='blue')
        plt.title('Equity Curve del Backtest (Modelo ML)', fontsize=16)
        plt.xlabel('Fecha/Hora', fontsize=12)
        plt.ylabel('Capital ($)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=10)
        plt.tight_layout()
        plt.show()
        closed_trades = trades_df[trades_df['status'].str.startswith('CLOSED')]
        if not closed_trades.empty:
            plt.figure(figsize=(10, 6))
            sns.histplot(closed_trades['pnl_net'], bins=50, kde=True, color='green')
            plt.title('Distribución de PnL Neto por Trade Cerrado', fontsize=14)
            plt.xlabel('PnL Neto ($)', fontsize=12)
            plt.ylabel('Frecuencia', fontsize=12)
            plt.axvline(x=0, color='red', linestyle='--', label='Cero PnL')
            plt.legend()
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            plt.show()
