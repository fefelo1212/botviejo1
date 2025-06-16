import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedFeatureEngineer:
    def __init__(self):
        logger.info("Inicializando AdvancedFeatureEngineer.")

    def add_all_features(self, df):
        if df.empty:
            logger.warning("DataFrame vacío, no se pueden añadir características.")
            return pd.DataFrame()
        
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

        logger.info("Añadiendo indicadores técnicos avanzados...")
        df = self.add_technical_indicators(df)
        
        logger.info("Añadiendo características temporales...")
        df = self.add_time_based_features(df)
        
        logger.info(f"Features añadidas. Columnas actuales: {df.columns.tolist()}")
        return df

    def add_technical_indicators(self, df):
        if 'close' not in df.columns:
            logger.error("Columna 'close' no encontrada para indicadores técnicos.")
            return df

        df['SMA_10'] = df['close'].rolling(window=10).mean()
        df['SMA_30'] = df['close'].rolling(window=30).mean()
        
        df['RSI_14'] = self._calculate_rsi(df['close'], window=14)

        df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        window_bb = 20
        num_std_dev = 2
        df['BB_SMA'] = df['close'].rolling(window=window_bb).mean()
        df['BB_STD'] = df['close'].rolling(window=window_bb).std()
        df['BB_UPPER'] = df['BB_SMA'] + (df['BB_STD'] * num_std_dev)
        df['BB_LOWER'] = df['BB_SMA'] - (df['BB_STD'] * num_std_dev)

        logger.info("Indicadores técnicos añadidos: SMA_10, SMA_30, RSI_14, MACD, MACD_Signal, MACD_Hist, BB_UPPER, BB_LOWER, BB_SMA, BB_STD.")
        return df

    def add_time_based_features(self, df):
        if 'open_time' not in df.columns:
            logger.error("Columna 'open_time' no encontrada para características temporales.")
            return df
        
        if not pd.api.types.is_datetime64_any_dtype(df['open_time']):
             df['open_time'] = pd.to_datetime(df['open_time'], errors='coerce')
        
        df['hour'] = df['open_time'].dt.hour
        df['day_of_week'] = df['open_time'].dt.dayofweek
        df['day_of_month'] = df['open_time'].dt.day
        df['month'] = df['open_time'].dt.month
        
        logger.info("Características temporales añadidas: hour, day_of_week, day_of_month, month.")
        return df

    def _calculate_rsi(self, series, window):
        delta = series.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.ewm(com=window - 1, min_periods=window).mean()
        avg_loss = loss.ewm(com=window - 1, min_periods=window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
