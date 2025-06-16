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
    Lee archivos descargados y los procesa para análisis técnico
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
            filename = f"{self.data_folder}/{symbol}_{interval}_klines.csv"
            
            if not os.path.exists(filename):
                logging.warning(f"Archivo no encontrado: {filename}")
                return None
            
            df = pd.read_csv(filename)
            df['open_time'] = pd.to_datetime(df['open_time'])
            df['close_time'] = pd.to_datetime(df['close_time'])
            
            # Ordenar por tiempo
            df = df.sort_values('open_time').reset_index(drop=True)
            
            logging.info(f"Datos cargados: {filename}")
            logging.info(f"Período: {df['open_time'].min()} a {df['open_time'].max()}")
            logging.info(f"Total velas: {len(df)}")
            
            return df
            
        except Exception as e:
            logging.error(f"Error cargando datos {symbol} {interval}: {e}")
            return None
    
    def load_current_price(self, symbol: str = "SOLUSDT") -> Dict:
        """Carga precio actual desde archivo JSON"""
        try:
            filename = f"{self.data_folder}/{symbol}_24hr_ticker.json"
            
            if not os.path.exists(filename):
                logging.warning(f"Archivo no encontrado: {filename}")
                return None
            
            with open(filename, 'r') as f:
                data = json.load(f)
            
            current_price = {
                "symbol": data["symbol"],
                "price": data["lastPrice"],
                "change_24h": data["priceChangePercent"],
                "volume": data["volume"],
                "high_24h": data["highPrice"],
                "low_24h": data["lowPrice"],
                "timestamp": data["timestamp"]
            }
            
            logging.info(f"Precio actual {symbol}: ${current_price['price']:.4f}")
            return current_price
            
        except Exception as e:
            logging.error(f"Error cargando precio actual {symbol}: {e}")
            return None

    # --- FUNCIONES DE CÁLCULO DE INDICADORES (IMPLEMENTACIONES DE PANDAS/NUMPY) ---
    # Asegúrate de que las columnas de entrada (ej. 'close') sean de tipo float.

    def calculate_sma(self, df: pd.DataFrame, periods: List[int] = [5, 20, 50]) -> pd.DataFrame:
        """Calcula medias móviles simples usando Pandas."""
        df_copy = df.copy()
        for period in periods:
            column_name = f"sma_{period}"
            # Convertir a float antes del cálculo
            df_copy[column_name] = df_copy['close'].astype(float).rolling(window=period).mean()
        logging.info(f"SMAs calculadas: {periods} usando Pandas.")
        return df_copy
    
    def calculate_ema(self, df: pd.DataFrame, periods: List[int] = [12, 26]) -> pd.DataFrame:
        """Calcula medias móviles exponenciales usando Pandas."""
        df_copy = df.copy()
        for period in periods:
            column_name = f"ema_{period}"
            # Convertir a float antes del cálculo
            df_copy[column_name] = df_copy['close'].astype(float).ewm(span=period, adjust=False).mean()
        logging.info(f"EMAs calculadas: {periods} usando Pandas.")
        return df_copy
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Calcula RSI (Relative Strength Index) usando Pandas/NumPy."""
        df_copy = df.copy()
        # Asegurarse de que 'close' sea numérico.
        delta = df_copy['close'].astype(float).diff(1)
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)

        avg_gain = gain.ewm(com=period-1, adjust=False).mean()
        avg_loss = loss.ewm(com=period-1, adjust=False).mean()

        rs = avg_gain / avg_loss
        df_copy['rsi'] = 100 - (100 / (1 + rs))
        # Manejar casos de división por cero (si avg_loss es 0 y avg_gain no lo es)
        df_copy['rsi'] = df_copy['rsi'].replace([np.inf, -np.inf], 100) # Si rs es inf, RSI es 100
        df_copy['rsi'] = df_copy['rsi'].fillna(0) # Si avg_gain y avg_loss son 0, RSI es 0
        
        logging.info(f"RSI calculado (período {period}) usando Pandas/NumPy.")
        return df_copy
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """Calcula Bandas de Bollinger usando Pandas."""
        df_copy = df.copy()
        # Asegurarse de que 'close' sea numérico.
        rolling_mean = df_copy['close'].astype(float).rolling(window=period).mean()
        rolling_std = df_copy['close'].astype(float).rolling(window=period).std()
        
        df_copy['bb_middle'] = rolling_mean
        df_copy['bb_upper'] = rolling_mean + (rolling_std * std_dev)
        df_copy['bb_lower'] = rolling_mean - (rolling_std * std_dev)
        logging.info(f"Bandas de Bollinger calculadas (período {period}, std {std_dev}) usando Pandas.")
        return df_copy
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Calcula MACD usando Pandas."""
        df_copy = df.copy()
        # Asegurarse de que 'close' sea numérico.
        fast_ema = df_copy['close'].astype(float).ewm(span=fast, adjust=False).mean()
        slow_ema = df_copy['close'].astype(float).ewm(span=slow, adjust=False).mean()
        
        df_copy['macd'] = fast_ema - slow_ema
        df_copy['macd_signal'] = df_copy['macd'].ewm(span=signal, adjust=False).mean()
        df_copy['macd_histogram'] = df_copy['macd'] - df_copy['macd_signal']
        logging.info(f"MACD calculado ({fast}, {slow}, {signal}) usando Pandas.")
        return df_copy

    def detect_trading_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detecta señales de trading basadas en indicadores"""
        try:
            df_copy = df.copy()
            
            # Inicializar columnas de señales
            df_copy['signal'] = 0
            df_copy['signal_strength'] = 0.0
            df_copy['signal_reason'] = ""
            
            # Señales SMA (cruce de medias)
            if 'sma_5' in df_copy.columns and 'sma_20' in df_copy.columns:
                # Usar .shift(1) para comparar con el valor anterior
                sma_bullish = (df_copy['sma_5'] > df_copy['sma_20']) & (df_copy['sma_5'].shift(1) <= df_copy['sma_20'].shift(1))
                sma_bearish = (df_copy['sma_5'] < df_copy['sma_20']) & (df_copy['sma_5'].shift(1) >= df_copy['sma_20'].shift(1))
                
                df_copy.loc[sma_bullish, 'signal'] = 1
                df_copy.loc[sma_bullish, 'signal_reason'] = "SMA_CROSS_UP"
                
                df_copy.loc[sma_bearish, 'signal'] = -1
                df_copy.loc[sma_bearish, 'signal_reason'] = "SMA_CROSS_DOWN"
            
            # Señales RSI
            if 'rsi' in df_copy.columns:
                rsi_oversold = df_copy['rsi'] < 30
                rsi_overbought = df_copy['rsi'] > 70
                
                # Solo aplicar si no hay una señal SMA más fuerte o si la señal actual es 0
                df_copy.loc[rsi_oversold & (df_copy['signal'] == 0), 'signal'] = 1
                df_copy.loc[rsi_oversold & (df_copy['signal'] == 0), 'signal_reason'] = "RSI_OVERSOLD"
                
                df_copy.loc[rsi_overbought & (df_copy['signal'] == 0), 'signal'] = -1
                df_copy.loc[rsi_overbought & (df_copy['signal'] == 0), 'signal_reason'] = "RSI_OVERBOUGHT"
            
            # Calcular fuerza de señal (simplificado para el chunking)
            # La fuerza de la señal y la impresión detallada se hará en el procesamiento final.
            # Por ahora, solo queremos que las columnas existan.
            
            return df_copy
            
        except Exception as e:
            logging.error(f"Error detectando señales: {e}")
            return df
    
    def calculate_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict:
        """Calcula niveles de soporte y resistencia (No se usará en el chunking, solo para análisis final)."""
        logging.warning("calculate_support_resistance no está optimizado para procesamiento por chunks y puede ser lento en grandes DFs.")
        try:
            recent_data = df.tail(window * 3)  # Últimas velas para análisis
            
            # Máximos y mínimos locales
            highs = recent_data['high'].rolling(window=window, center=True).max()
            lows = recent_data['low'].rolling(window=window, center=True).min()
            
            # Niveles de resistencia (máximos frecuentes)
            resistance_levels = highs.dropna().value_counts().head(3).index.tolist()
            
            # Niveles de soporte (mínimos frecuentes)  
            support_levels = lows.dropna().value_counts().head(3).index.tolist()
            
            current_price = df['close'].iloc[-1]
            
            levels = {
                "current_price": current_price,
                "resistance_levels": resistance_levels,
                "support_levels": support_levels,
                "nearest_resistance": min([r for r in resistance_levels if r > current_price], default=None),
                "nearest_support": max([s for s in support_levels if s < current_price], default=None)
            }
            
            logging.info("Niveles de soporte y resistencia calculados.")
            return levels
            
        except Exception as e:
            logging.error(f"Error calculando soporte/resistencia: {e}")
            return {}

    def process_data_chunk(self, chunk_df: pd.DataFrame) -> pd.DataFrame:
        """
        Procesa un chunk de datos, aplicando todos los indicadores técnicos.
        Esta función está diseñada para ser llamada iterativamente.
        """
        if chunk_df.empty:
            return chunk_df
        
        # Asegurarse de que las columnas numéricas sean float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in chunk_df.columns:
                chunk_df[col] = pd.to_numeric(chunk_df[col], errors='coerce')
        
        # Aplicar indicadores técnicos usando Pandas/NumPy
        chunk_df = self.calculate_sma(chunk_df, [5, 20, 50])
        chunk_df = self.calculate_ema(chunk_df, [12, 26])
        chunk_df = self.calculate_rsi(chunk_df, 14)
        chunk_df = self.calculate_bollinger_bands(chunk_df, 20, 2.0)
        chunk_df = self.calculate_macd(chunk_df, 12, 26, 9)
        
        # Detectar señales
        chunk_df = self.detect_trading_signals(chunk_df)

        return chunk_df

if __name__ == "__main__":
    logging.info("Este script es un módulo y está diseñado para ser importado.")
    logging.info("Para probarlo, puedes crear un DataFrame pequeño y pasarlo a process_data_chunk.")
    
    # Ejemplo de un DataFrame de prueba
    data = {
        'open_time': pd.to_datetime(['2023-01-01 00:00:00', '2023-01-01 00:01:00', '2023-01-01 00:02:00', '2023-01-01 00:03:00', '2023-01-01 00:04:00'] * 10),
        'open': np.random.rand(50) * 100 + 1000,
        'high': np.random.rand(50) * 100 + 1050,
        'low': np.random.rand(50) * 100 + 950,
        'close': np.random.rand(50) * 100 + 1000,
        'volume': np.random.rand(50) * 1000
    }
    test_df = pd.DataFrame(data)
    test_df['close'] = test_df['close'].sort_values().values # Asegurar una tendencia para indicadores

    processor = BinanceDataProcessor()
    processed_test_chunk = processor.process_data_chunk(test_df)
    logging.info("Chunk de prueba procesado. Primeras 5 filas:")
    logging.info(processed_test_chunk.head())
    logging.info(f"Columnas del chunk procesado: {processed_test_chunk.columns.tolist()}")