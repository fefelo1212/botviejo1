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

    def calculate_bollinger_bands(self, df: pd.DataFrame, window: int, num_std: float) -> pd.DataFrame:
        """Calcula Bollinger Bands"""
        df['rolling_mean'] = df['close'].rolling(window=window).mean()
        df['rolling_std'] = df['close'].rolling(window=window).std()
        df['BB_UPPER'] = df['rolling_mean'] + (df['rolling_std'] * num_std)
        df['BB_LOWER'] = df['rolling_mean'] - (df['rolling_std'] * num_std)
        # Puedes mantener bb_middle si lo usas en el backtester o como feature
        df['BB_MIDDLE'] = df['rolling_mean'] # Renombramos para consistencia
        df = df.drop(columns=['rolling_mean', 'rolling_std']) # Estas son intermedias
        return df

    def calculate_macd(self, df: pd.DataFrame, fast_period: int, slow_period: int, signal_period: int) -> pd.DataFrame:
        """Calcula Moving Average Convergence Divergence (MACD)"""
        ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
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
    
    def calculate_future_profitability_target(self, df: pd.DataFrame, 
                                            price_change_percent_threshold: float = 0.005, 
                                            horizon_candles: int = 5) -> pd.DataFrame:
        """
        Calcula una variable objetivo (target) basada en la rentabilidad futura.
        
        Args:
            df (pd.DataFrame): DataFrame con la columna 'close'.
            price_change_percent_threshold (float): Porcentaje de cambio de precio
                                                    necesario para considerar una señal positiva (ej. 0.005 para 0.5%).
            horizon_candles (int): Número de velas hacia adelante para calcular el retorno.
                                   Un valor de 5 significa las próximas 5 velas.
        Returns:
            pd.DataFrame: DataFrame con la columna 'target' añadida.
        """
        # Calcula el precio de cierre 'horizon_candles' velas en el futuro.
        df['future_close'] = df['close'].shift(-horizon_candles)
        
        # Calcular el retorno porcentual desde el cierre actual hasta el futuro_cierre
        df['future_return'] = (df['future_close'] - df['close']) / df['close']
        
        # Definir el target: 1 si el retorno futuro excede el umbral, 0 en caso contrario.
        # Las últimas 'horizon_candles' filas tendrán NaN en 'future_close'/'future_return',
        # por lo que el target también será NaN y se eliminarán en train_model.py
        df['target'] = np.where(df['future_return'] > price_change_percent_threshold, 1, 0)
        
        # Puedes eliminar las columnas intermedias si no las necesitas como features
        df = df.drop(columns=['future_close', 'future_return'], errors='ignore')
        
        logging.info(f"Calculado target de rentabilidad futura: umbral={price_change_percent_threshold*100}%, horizonte={horizon_candles} velas.")
        logging.info("Conteo de la nueva columna 'target':\n" + str(df['target'].value_counts(dropna=False)))

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
                                                                price_change_percent_threshold=0.005, 
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