#!/usr/bin/env python3
"""
Procesador de datos de Binance - Separado del descargador
Lee archivos descargados y los procesa para trading
"""

import pandas as pd
import json
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
# import talib # ¡IMPORTANTE: HEMOS ELIMINADO LA IMPORTACIÓN DE TALIB!
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BinanceDataProcessor:
    """
    Procesador independiente de datos de Binance
    Lee archivos descargados y los procesa para análisis técnico y define la variable objetivo (target).
    """
    
    def __init__(self, data_folder: str = "binance_data"):
        self.data_folder = data_folder
        self.processed_folder = "processed_data"
        self.create_processed_folder()
        
    def create_processed_folder(self):
        """Crea carpeta para datos procesados"""
        if not os.path.exists(self.processed_folder):
            os.makedirs(self.processed_folder)
            logging.info(f"Carpeta procesados creada: {self.processed_folder}")
    
    def load_klines_data(self, symbol: str = "SOLUSDT", interval: str = "1m") -> pd.DataFrame:
        """Carga datos de velas desde archivo CSV"""
        # Esta función ya no será el punto principal para cargar el dataset grande.
        # Se mantendrá por si necesitas cargar archivos pequeños.
        try:
            filename = f"{self.data_folder}/{symbol}_{interval}.csv"
            logging.info(f"Cargando datos desde: {filename}")
            df = pd.read_csv(filename)
            # Asegurarse de que las columnas de tiempo sean datetime
            df['open_time'] = pd.to_datetime(df['open_time'])
            df['close_time'] = pd.to_datetime(df['close_time'])
            return df
        except FileNotFoundError:
            logging.error(f"Archivo no encontrado: {filename}")
            return pd.DataFrame()
        except Exception as e:
            logging.error(f"Error al cargar datos: {e}")
            return pd.DataFrame()

    def calculate_sma(self, df: pd.DataFrame, windows: List[int]) -> pd.DataFrame:
        """Calcula Simple Moving Average (SMA)"""
        for w in windows:
            df[f'sma_{w}'] = df['close'].rolling(window=w).mean()
        return df

    def calculate_ema(self, df: pd.DataFrame, windows: List[int]) -> pd.DataFrame:
        """Calcula Exponential Moving Average (EMA)"""
        for w in windows:
            df[f'ema_{w}'] = df['close'].ewm(span=w, adjust=False).mean()
        return df

    def calculate_rsi(self, df: pd.DataFrame, window: int) -> pd.DataFrame:
        """Calcula Relative Strength Index (RSI)"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    def calculate_bollinger_bands(self, df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
        """
        Calcula las Bandas de Bollinger y añade las columnas al DataFrame.
        Las columnas BB_SMA y BB_STD son la media móvil y la desviación estándar
        que son directamente características para el modelo ML.
        """
        if len(df) < window:
            logging.warning(f"No hay suficientes datos ({len(df)}) para calcular Bandas de Bollinger con ventana {window}. Retornando DataFrame original.")
            return df

        df['BB_SMA'] = df['close'].rolling(window=window).mean()
        df['BB_STD'] = df['close'].rolling(window=window).std()

        df['BB_UPPER'] = df['BB_SMA'] + (df['BB_STD'] * num_std)
        df['BB_LOWER'] = df['BB_SMA'] - (df['BB_STD'] * num_std)

        logging.debug(f"Bandas de Bollinger calculadas. Columnas añadidas: BB_UPPER, BB_LOWER, BB_SMA, BB_STD")
        return df

    def calculate_macd(self, df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
        """
        Calcula Moving Average Convergence Divergence (MACD)
        Añade las columnas 'MACD', 'MACD_SIGNAL', 'MACD_HIST' al DataFrame.
        """
        if len(df) < slow_period:
            logging.warning(f"No hay suficientes datos ({len(df)}) para calcular MACD con periodo lento {slow_period}. Retornando DataFrame original.")
            return df

        if not pd.api.types.is_numeric_dtype(df['close']):
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df.dropna(subset=['close'], inplace=True)
            if df.empty:
                logging.warning("Columna 'close' no numérica y se volvió vacía después de limpiar NaNs en calculate_macd. Retornando DataFrame original.")
                return df

        ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()

        df['MACD'] = ema_fast - ema_slow
        df['MACD_SIGNAL'] = df['MACD'].ewm(span=signal_period, adjust=False).mean()
        df['MACD_HIST'] = df['MACD'] - df['MACD_SIGNAL']

        logging.debug("MACD calculado. Columnas añadidas: MACD, MACD_SIGNAL, MACD_HIST")
        return df

    def detect_trading_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detecta señales de trading básicas basadas en indicadores.
        Esta función ya NO es la fuente de la variable objetivo del ML.
        Sus salidas 'signal', 'signal_reason', 'signal_strength' se excluirán de los features.
        """
        df['signal'] = 0  # 0: no signal
        df['signal_reason'] = ''
        df['signal_strength'] = 0.0

        # Ejemplo de lógica antigua que ahora solo es informativa o para otros usos.
        # Compra por cruce de SMA
        buy_conditions_sma = (df['sma_5'] > df['sma_20']) & \
                             (df['sma_5'].shift(1) <= df['sma_20'].shift(1))
        df.loc[buy_conditions_sma, 'signal'] = 1
        df.loc[buy_conditions_sma, 'signal_reason'] = 'SMA_Cross_Buy'
        df.loc[buy_conditions_sma, 'signal_strength'] = 0.5

        # Venta por cruce de SMA
        sell_conditions_sma = (df['sma_5'] < df['sma_20']) & \
                              (df['sma_5'].shift(1) >= df['sma_20'].shift(1))
        df.loc[sell_conditions_sma, 'signal'] = -1
        df.loc[sell_conditions_sma, 'signal_reason'] = 'SMA_Cross_Sell'
        df.loc[sell_conditions_sma, 'signal_strength'] = 0.5

        # Compra por RSI sobrevendido
        buy_conditions_rsi = (df['rsi'] < 30) & (df['rsi'].shift(1) >= 30)
        df.loc[buy_conditions_rsi & (df['signal'] == 0), 'signal'] = 1 # No sobrescribir SMA si ya hay señal
        df.loc[buy_conditions_rsi & (df['signal_reason'] == ''), 'signal_reason'] = 'RSI_Oversold_Buy'
        df.loc[buy_conditions_rsi & (df['signal_strength'] == 0), 'signal_strength'] = 0.3

        # Venta por RSI sobrecomprado
        sell_conditions_rsi = (df['rsi'] > 70) & (df['rsi'].shift(1) <= 70)
        df.loc[sell_conditions_rsi & (df['signal'] == 0), 'signal'] = -1 # No sobrescribir SMA
        df.loc[sell_conditions_rsi & (df['signal_reason'] == ''), 'signal_reason'] = 'RSI_Overbought_Sell'
        df.loc[sell_conditions_rsi & (df['signal_strength'] == 0), 'signal_strength'] = 0.3
        
        return df

    def calculate_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extrae características temporales de open_time."""
        df['hour'] = df['open_time'].dt.hour
        df['day_of_week'] = df['open_time'].dt.dayofweek
        df['day_of_month'] = df['open_time'].dt.day
        df['month'] = df['open_time'].dt.month
        return df
    
    def calculate_future_profitability_target(self,
                                            df: pd.DataFrame,
                                            price_change_percent_threshold: float = 0.005,
                                            horizon_candles: int = 5
                                           ) -> pd.DataFrame:
        if df.empty:
            print("--- DEBUG: DataFrame de entrada a calculate_future_profitability_target está vacío. ---")
            return df # O manejar según sea necesario
            
        print(f"\n--- DEBUG: Iniciando cálculo de target. Filas iniciales: {len(df)} ---")
        print(f"--- DEBUG: Threshold: {price_change_percent_threshold}, Horizon: {horizon_candles} ---")

        # Paso 1: Calcular future_close
        df['future_close'] = df['close'].shift(-horizon_candles)
        print("\n--- DEBUG: Columnas después de 'future_close' calculada ---")
        print(df.columns.tolist())
        print("\n--- DEBUG: Primeras 10 filas de 'close' y 'future_close' ---")
        print(df[['close', 'future_close']].head(10).to_string())
        
        # Paso 2: Calcular future_return
        df['future_return'] = (df['future_close'] - df['close']) / df['close']
        print("\n--- DEBUG: Primeras 10 filas de 'future_return' ---")
        print(df['future_return'].head(10).to_string())
        print("\n--- DEBUG: Estadísticas descriptivas de 'future_return' ---")
        print(df['future_return'].describe().to_string())
        print("\n--- DEBUG: Conteo de valores únicos en 'future_return' (con NaNs) ---")
        print(df['future_return'].value_counts(dropna=False).to_string())

        # Paso 3: Definir las condiciones y asignar el target
        conditions = [
            df['future_return'] > price_change_percent_threshold,         # Subida (target 1)
            df['future_return'] < -price_change_percent_threshold         # Bajada (target -1)
        ]
        choices = [1, -1]
        df['target'] = np.select(conditions, choices, default=0)
        
        # Paso 4: Manejar NaNs en el target (por ejemplo, si future_return fue NaN)
        df['target'] = df['target'].where(df['future_return'].notna(), np.nan)

        print("\n--- DEBUG: Primeras 10 filas de 'target' después del cálculo ---")
        print(df['target'].head(10).to_string())
        print("\n--- DEBUG: Conteo FINAL de la columna 'target' (con NaNs):\n", df['target'].value_counts(dropna=False).to_string())

        # Guardar un fragmento para depuración manual (si la carpeta info existe y se puede escribir)
        debug_info_dir = "info"
        if not os.path.exists(debug_info_dir):
            os.makedirs(debug_info_dir)
            logging.info(f"Carpeta '{debug_info_dir}' creada para depuración.")
        
        debug_sample_path = os.path.join(debug_info_dir, "debug_target_sample.csv")
        try:
            # Selecciona las columnas relevantes y las primeras 100 filas
            debug_df = df[['open_time', 'close', 'future_close', 'future_return', 'target']].head(100)
            if not debug_df.empty:
                debug_df.to_csv(debug_sample_path, index=False)
                logging.info(f"Fragmento de depuración guardado en: {debug_sample_path}")
            else:
                logging.warning("No hay datos en el DataFrame para guardar el fragmento de depuración.")
        except Exception as e:
            logging.error(f"Error al guardar debug_target_sample.csv: {e}")

        # Puedes eliminar las columnas intermedias si no las necesitas como features
        # Las comentamos TEMPORALMENTE para depuración.
        # df = df.drop(columns=['future_close', 'future_return'], errors='ignore')
        
        # Filtrar filas con NaNs en el target, si es necesario para el entrenamiento posterior
        # Pero para la depuración de este punto, queremos ver los NaNs.
        # df = df.dropna(subset=['target']) # Esta línea debe manejarse más tarde en train_model.py si aplica

        print(f"--- DEBUG: Finalizando cálculo de target. Filas finales: {len(df)} ---")

        return df

    def process_data_chunk(self, chunk_df: pd.DataFrame) -> pd.DataFrame:
        """
        Procesa un chunk de datos de velas, añadiendo todos los indicadores técnicos y el TARGET.
        """
        if chunk_df.empty:
            return chunk_df
        
        # Asegurarse de que los datos sean numéricos
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume',
                        'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
        for col in numeric_cols:
            if col in chunk_df.columns:
                chunk_df[col] = pd.to_numeric(chunk_df[col], errors='coerce')

        # Eliminar NaNs al inicio causados por la conversión a numérico si aplica
        initial_rows = len(chunk_df)
        chunk_df.dropna(subset=numeric_cols, inplace=True)
        if len(chunk_df) < initial_rows:
            logging.warning(f"Se eliminaron {initial_rows - len(chunk_df)} filas con NaNs en columnas numéricas esenciales.")

        # Asegurar que 'open_time' es datetime para funciones de tiempo
        chunk_df['open_time'] = pd.to_datetime(chunk_df['open_time'])

        # Cálculo de características temporales
        chunk_df = self.calculate_time_features(chunk_df)
        
        # Cálculo de indicadores técnicos
        chunk_df = self.calculate_sma(chunk_df, [5, 20, 50])
        chunk_df = self.calculate_ema(chunk_df, [12, 26])
        chunk_df = self.calculate_rsi(chunk_df, 14)
        chunk_df = self.calculate_bollinger_bands(chunk_df, 20, 2.0)
        chunk_df = self.calculate_macd(chunk_df, 12, 26, 9)
        
        # --- NUEVA ADICIÓN CLAVE: Cálculo de la Variable Objetivo (Target) ---
        # Definimos que si el precio sube 0.5% en las próximas 5 velas, es una señal de "compra exitosa" (target = 1)
        # Puedes ajustar price_change_percent_threshold y horizon_candles
        chunk_df = self.calculate_future_profitability_target(chunk_df, 
                                                                price_change_percent_threshold=0.0, 
                                                                horizon_candles=5)
        
        # Detectar señales (la función antigua, ahora solo informativa o para otros usos, no el target del ML)
        chunk_df = self.detect_trading_signals(chunk_df)

        return chunk_df

if __name__ == "__main__":
    logging.info("Este script es un módulo y está diseñado para ser importado.")
    logging.info("Para probarlo, puedes crear un DataFrame pequeño y pasarlo a process_data_chunk.")
    
    # Ejemplo de un DataFrame de prueba
    data = {
        'open_time': pd.to_datetime(['2023-01-01 00:00:00', '2023-01-01 00:01:00', '2023-01-01 00:02:00', '2023-01-01 00:03:00', '2023-01-01 00:04:00'] * 10),
        'open': np.random.rand(50) * 100 + 1000,
        'high': np.random.rand(50) * 100 + 1000,
        'low': np.random.rand(50) * 100 + 1000,
        'close': np.random.rand(50) * 100 + 1000,
        'volume': np.random.rand(50) * 1000,
        'quote_asset_volume': np.random.rand(50) * 100000,
        'number_of_trades': np.random.randint(100, 1000, 50),
        'taker_buy_base_asset_volume': np.random.rand(50) * 500,
        'taker_buy_quote_asset_volume': np.random.rand(50) * 50000,
        'close_time': pd.to_datetime(['2023-01-01 00:00:59', '2023-01-01 00:01:59', '2023-01-01 00:02:59', '2023-01-01 00:03:59', '2023-01-01 00:04:59'] * 10),
    }
    sample_df = pd.DataFrame(data)
    
    processor = BinanceDataProcessor()
    processed_sample_df = processor.process_data_chunk(sample_df)
    print("\nDataFrame de prueba procesado (primeras 5 filas):")
    print(processed_sample_df.head())
    print("\nConteo de la columna 'target' en el ejemplo:")
    print(processed_sample_df['target'].value_counts(dropna=False))