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
import talib

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
            print(f"Carpeta procesados creada: {self.processed_folder}")
    
    def load_klines_data(self, symbol: str = "SOLUSDT", interval: str = "1m") -> pd.DataFrame:
        """Carga datos de velas desde archivo CSV"""
        try:
            filename = f"{self.data_folder}/{symbol}_{interval}_klines.csv"
            
            if not os.path.exists(filename):
                print(f"Archivo no encontrado: {filename}")
                return None
            
            df = pd.read_csv(filename)
            df['open_time'] = pd.to_datetime(df['open_time'])
            df['close_time'] = pd.to_datetime(df['close_time'])
            
            # Ordenar por tiempo
            df = df.sort_values('open_time').reset_index(drop=True)
            
            print(f"Datos cargados: {filename}")
            print(f"Período: {df['open_time'].min()} a {df['open_time'].max()}")
            print(f"Total velas: {len(df)}")
            
            return df
            
        except Exception as e:
            print(f"Error cargando datos {symbol} {interval}: {e}")
            return None
    
    def load_current_price(self, symbol: str = "SOLUSDT") -> Dict:
        """Carga precio actual desde archivo JSON"""
        try:
            filename = f"{self.data_folder}/{symbol}_24hr_ticker.json"
            
            if not os.path.exists(filename):
                print(f"Archivo no encontrado: {filename}")
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
            
            print(f"Precio actual {symbol}: ${current_price['price']:.4f}")
            return current_price
            
        except Exception as e:
            print(f"Error cargando precio actual {symbol}: {e}")
            return None
    
    def calculate_sma(self, df: pd.DataFrame, periods: List[int] = [5, 20, 50]) -> pd.DataFrame:
        """Calcula medias móviles simples"""
        try:
            df_copy = df.copy()
            
            for period in periods:
                column_name = f"sma_{period}"
                df_copy[column_name] = df_copy['close'].rolling(window=period).mean()
                
            print(f"SMAs calculadas: {periods}")
            return df_copy
            
        except Exception as e:
            print(f"Error calculando SMAs: {e}")
            return df
    
    def calculate_ema(self, df: pd.DataFrame, periods: List[int] = [12, 26]) -> pd.DataFrame:
        """Calcula medias móviles exponenciales"""
        try:
            df_copy = df.copy()
            
            for period in periods:
                column_name = f"ema_{period}"
                df_copy[column_name] = df_copy['close'].ewm(span=period).mean()
                
            print(f"EMAs calculadas: {periods}")
            return df_copy
            
        except Exception as e:
            print(f"Error calculando EMAs: {e}")
            return df
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Calcula RSI (Relative Strength Index)"""
        try:
            df_copy = df.copy()
            
            # Calcular cambios de precios
            delta = df_copy['close'].diff()
            
            # Separar ganancias y pérdidas
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Calcular medias móviles
            avg_gains = gains.rolling(window=period).mean()
            avg_losses = losses.rolling(window=period).mean()
            
            # Calcular RS y RSI
            rs = avg_gains / avg_losses
            df_copy['rsi'] = 100 - (100 / (1 + rs))
            
            print(f"RSI calculado (período {period})")
            return df_copy
            
        except Exception as e:
            print(f"Error calculando RSI: {e}")
            return df
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """Calcula Bandas de Bollinger"""
        try:
            df_copy = df.copy()
            
            # Media móvil central
            df_copy['bb_middle'] = df_copy['close'].rolling(window=period).mean()
            
            # Desviación estándar
            std = df_copy['close'].rolling(window=period).std()
            
            # Bandas superior e inferior
            df_copy['bb_upper'] = df_copy['bb_middle'] + (std * std_dev)
            df_copy['bb_lower'] = df_copy['bb_middle'] - (std * std_dev)
            
            print(f"Bandas de Bollinger calculadas (período {period}, std {std_dev})")
            return df_copy
            
        except Exception as e:
            print(f"Error calculando Bollinger Bands: {e}")
            return df
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Calcula MACD"""
        try:
            df_copy = df.copy()
            
            # EMAs rápida y lenta
            ema_fast = df_copy['close'].ewm(span=fast).mean()
            ema_slow = df_copy['close'].ewm(span=slow).mean()
            
            # Línea MACD
            df_copy['macd'] = ema_fast - ema_slow
            
            # Línea de señal
            df_copy['macd_signal'] = df_copy['macd'].ewm(span=signal).mean()
            
            # Histograma
            df_copy['macd_histogram'] = df_copy['macd'] - df_copy['macd_signal']
            
            print(f"MACD calculado ({fast}, {slow}, {signal})")
            return df_copy
            
        except Exception as e:
            print(f"Error calculando MACD: {e}")
            return df
    
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
                
                df_copy.loc[rsi_oversold & (df_copy['signal'] == 0), 'signal'] = 1
                df_copy.loc[rsi_oversold & (df_copy['signal'] == 0), 'signal_reason'] = "RSI_OVERSOLD"
                
                df_copy.loc[rsi_overbought & (df_copy['signal'] == 0), 'signal'] = -1
                df_copy.loc[rsi_overbought & (df_copy['signal'] == 0), 'signal_reason'] = "RSI_OVERBOUGHT"
            
            # Calcular fuerza de señal
            signal_count = len(df_copy[df_copy['signal'] != 0])
            if signal_count > 0:
                print(f"Señales detectadas: {signal_count}")
                
                # Mostrar últimas señales
                recent_signals = df_copy[df_copy['signal'] != 0].tail(5)
                for _, row in recent_signals.iterrows():
                    signal_type = "COMPRA" if row['signal'] == 1 else "VENTA"
                    print(f"{row['open_time']}: {signal_type} - {row['signal_reason']} - Precio: ${row['close']:.4f}")
            
            return df_copy
            
        except Exception as e:
            print(f"Error detectando señales: {e}")
            return df
    
    def calculate_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict:
        """Calcula niveles de soporte y resistencia"""
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
            
            print("Niveles de soporte y resistencia:")
            print(f"Precio actual: ${current_price:.4f}")
            if levels["nearest_support"]:
                print(f"Soporte más cercano: ${levels['nearest_support']:.4f}")
            if levels["nearest_resistance"]:
                print(f"Resistencia más cercana: ${levels['nearest_resistance']:.4f}")
            
            return levels
            
        except Exception as e:
            print(f"Error calculando soporte/resistencia: {e}")
            return {}
    
    def process_full_analysis(self, symbol: str = "SOLUSDT", interval: str = "1m") -> Dict:
        """Procesa análisis técnico completo"""
        try:
            print(f"\n=== PROCESANDO ANÁLISIS COMPLETO {symbol} {interval} ===")
            
            # 1. Cargar datos
            df = self.load_klines_data(symbol, interval)
            if df is None:
                return None
            
            # 2. Calcular indicadores
            print("\n1. Calculando indicadores técnicos...")
            df = self.calculate_sma(df, [5, 20, 50])
            df = self.calculate_ema(df, [12, 26])
            df = self.calculate_rsi(df, 14)
            df = self.calculate_bollinger_bands(df, 20, 2.0)
            df = self.calculate_macd(df, 12, 26, 9)
            
            # 3. Detectar señales
            print("\n2. Detectando señales de trading...")
            df = self.detect_trading_signals(df)
            
            # 4. Calcular soporte/resistencia
            print("\n3. Calculando soporte y resistencia...")
            levels = self.calculate_support_resistance(df)
            
            # 5. Obtener precio actual
            print("\n4. Obteniendo precio actual...")
            current_price = self.load_current_price(symbol)
            
            # 6. Preparar datos para bot
            latest_data = df.tail(1).iloc[0]
            
            analysis_result = {
                "symbol": symbol,
                "interval": interval,
                "timestamp": datetime.now().isoformat(),
                "current_price": current_price,
                "latest_candle": {
                    "open": latest_data['open'],
                    "high": latest_data['high'],
                    "low": latest_data['low'],
                    "close": latest_data['close'],
                    "volume": latest_data['volume'],
                    "time": latest_data['open_time'].isoformat()
                },
                "indicators": {
                    "sma_5": latest_data.get('sma_5'),
                    "sma_20": latest_data.get('sma_20'),
                    "sma_50": latest_data.get('sma_50'),
                    "ema_12": latest_data.get('ema_12'),
                    "ema_26": latest_data.get('ema_26'),
                    "rsi": latest_data.get('rsi'),
                    "bb_upper": latest_data.get('bb_upper'),
                    "bb_middle": latest_data.get('bb_middle'),
                    "bb_lower": latest_data.get('bb_lower'),
                    "macd": latest_data.get('macd'),
                    "macd_signal": latest_data.get('macd_signal'),
                    "macd_histogram": latest_data.get('macd_histogram')
                },
                "signals": {
                    "current_signal": int(latest_data.get('signal', 0)),
                    "signal_reason": latest_data.get('signal_reason', ""),
                    "signal_strength": float(latest_data.get('signal_strength', 0.0))
                },
                "levels": levels,
                "data_quality": {
                    "total_candles": len(df),
                    "data_start": df['open_time'].min().isoformat(),
                    "data_end": df['open_time'].max().isoformat(),
                    "missing_values": df.isnull().sum().sum()
                }
            }
            
            # 7. Guardar análisis procesado
            filename = f"{self.processed_folder}/{symbol}_{interval}_analysis.json"
            with open(filename, 'w') as f:
                json.dump(analysis_result, f, indent=2, default=str)
            
            # 8. Guardar DataFrame procesado
            csv_filename = f"{self.processed_folder}/{symbol}_{interval}_processed.csv"
            df.to_csv(csv_filename, index=False)
            
            print(f"\n=== ANÁLISIS COMPLETADO ===")
            print(f"Análisis guardado: {filename}")
            print(f"Datos procesados: {csv_filename}")
            print(f"Señal actual: {analysis_result['signals']['current_signal']}")
            print(f"Precio actual: ${current_price['price'] if current_price else 'N/A'}")
            
            return analysis_result
            
        except Exception as e:
            print(f"Error en análisis completo: {e}")
            return None
    
    def get_trading_recommendation(self, symbol: str = "SOLUSDT", interval: str = "1m") -> Dict:
        """Obtiene recomendación de trading procesada"""
        try:
            filename = f"{self.processed_folder}/{symbol}_{interval}_analysis.json"
            
            if not os.path.exists(filename):
                print(f"Análisis no encontrado: {filename}")
                print("Ejecuta process_full_analysis() primero")
                return None
            
            with open(filename, 'r') as f:
                analysis = json.load(f)
            
            # Interpretar señales
            signal = analysis['signals']['current_signal']
            
            if signal == 1:
                recommendation = "COMPRA"
                action = "BUY"
            elif signal == -1:
                recommendation = "VENTA"  
                action = "SELL"
            else:
                recommendation = "MANTENER"
                action = "HOLD"
            
            # Calcular confianza basada en múltiples factores
            confidence = 0.5  # Base
            
            # Ajustar por RSI
            rsi = analysis['indicators'].get('rsi')
            if rsi:
                if (signal == 1 and rsi < 40) or (signal == -1 and rsi > 60):
                    confidence += 0.2
            
            # Ajustar por MACD
            macd = analysis['indicators'].get('macd')
            macd_signal = analysis['indicators'].get('macd_signal')
            if macd and macd_signal:
                if (signal == 1 and macd > macd_signal) or (signal == -1 and macd < macd_signal):
                    confidence += 0.2
            
            recommendation_data = {
                "symbol": symbol,
                "recommendation": recommendation,
                "action": action,
                "confidence": min(confidence, 1.0),
                "reason": analysis['signals']['signal_reason'],
                "price": analysis['current_price']['price'] if analysis['current_price'] else None,
                "timestamp": datetime.now().isoformat(),
                "indicators_summary": {
                    "rsi": rsi,
                    "trend": "UP" if analysis['indicators'].get('sma_5', 0) > analysis['indicators'].get('sma_20', 0) else "DOWN"
                }
            }
            
            print(f"Recomendación para {symbol}:")
            print(f"Acción: {recommendation} ({confidence*100:.1f}% confianza)")
            print(f"Razón: {recommendation_data['reason']}")
            print(f"Precio: ${recommendation_data['price']:.4f}" if recommendation_data['price'] else "Precio no disponible")
            
            return recommendation_data
            
        except Exception as e:
            print(f"Error obteniendo recomendación: {e}")
            return None

def main():
    """Función principal para probar el procesador"""
    print("=== BINANCE DATA PROCESSOR ===")
    print("Procesador independiente de datos descargados")
    
    # Crear instancia del procesador
    processor = BinanceDataProcessor()
    
    symbol = "SOLUSDT"
    interval = "1m"
    
    print(f"\n1. Cargando datos de {symbol} {interval}...")
    df = processor.load_klines_data(symbol, interval)
    
    if df is not None:
        print(f"\n2. Procesando análisis técnico completo...")
        analysis = processor.process_full_analysis(symbol, interval)
        
        if analysis:
            print(f"\n3. Obteniendo recomendación de trading...")
            recommendation = processor.get_trading_recommendation(symbol, interval)
            
            print(f"\n=== PROCESAMIENTO COMPLETADO ===")
            print(f"Archivos procesados guardados en: {processor.processed_folder}/")
    else:
        print("Error: No se pudieron cargar los datos")
        print("Ejecuta primero binance_data_downloader.py")

if __name__ == "__main__":
    main()