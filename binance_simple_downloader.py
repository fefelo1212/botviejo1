#!/usr/bin/env python3
"""
Descargador simplificado de Binance para uso local
Optimizado para funcionar en cualquier entorno
"""

import requests
import json
import time
import pandas as pd
from datetime import datetime
import os

class SimpleBinanceDownloader:
    """Descargador simplificado de datos de Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.data_folder = "binance_data"
        os.makedirs(self.data_folder, exist_ok=True)
        
    def test_connection(self):
        """Prueba conexión básica"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/ping", timeout=5)
            if response.status_code == 200:
                print("✓ Conexión exitosa con Binance")
                return True
            else:
                print(f"✗ Error de conexión: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ No se pudo conectar: {e}")
            return False
    
    def get_price(self, symbol="SOLUSDT"):
        """Obtiene precio actual"""
        try:
            url = f"{self.base_url}/api/v3/ticker/price"
            response = requests.get(url, params={"symbol": symbol}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                price = float(data['price'])
                
                # Guardar precio
                price_data = {
                    "symbol": symbol,
                    "price": price,
                    "timestamp": datetime.now().isoformat(),
                    "source": "binance_api"
                }
                
                filename = f"{self.data_folder}/{symbol}_current_price.json"
                with open(filename, 'w') as f:
                    json.dump(price_data, f, indent=2)
                
                print(f"Precio {symbol}: ${price:.4f}")
                return price_data
            else:
                print(f"Error obteniendo precio: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error en get_price: {e}")
            return None
    
    def get_klines(self, symbol="SOLUSDT", interval="1m", limit=100):
        """Descarga datos de velas"""
        try:
            url = f"{self.base_url}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Crear DataFrame
                df = pd.DataFrame(data, columns=[
                    'open_time', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'buy_volume', 'buy_quote_volume', 'ignore'
                ])
                
                # Convertir tipos
                df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
                df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
                
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col])
                
                # Guardar datos
                filename = f"{self.data_folder}/{symbol}_{interval}_klines.csv"
                df.to_csv(filename, index=False)
                
                print(f"Descargadas {len(df)} velas {symbol} {interval}")
                print(f"Rango: {df['open_time'].min()} a {df['open_time'].max()}")
                print(f"Último precio: ${df['close'].iloc[-1]:.4f}")
                
                return df
            else:
                print(f"Error descargando klines: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error en get_klines: {e}")
            return None
    
    def get_ticker_24h(self, symbol="SOLUSDT"):
        """Obtiene estadísticas 24h"""
        try:
            url = f"{self.base_url}/api/v3/ticker/24hr"
            response = requests.get(url, params={"symbol": symbol}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                ticker_info = {
                    "symbol": data["symbol"],
                    "price": float(data["lastPrice"]),
                    "change_24h": float(data["priceChangePercent"]),
                    "high_24h": float(data["highPrice"]),
                    "low_24h": float(data["lowPrice"]),
                    "volume": float(data["volume"]),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Guardar ticker
                filename = f"{self.data_folder}/{symbol}_ticker_24h.json"
                with open(filename, 'w') as f:
                    json.dump(ticker_info, f, indent=2)
                
                print(f"Ticker 24h {symbol}:")
                print(f"  Precio: ${ticker_info['price']:.4f}")
                print(f"  Cambio: {ticker_info['change_24h']:+.2f}%")
                print(f"  Volumen: {ticker_info['volume']:,.0f}")
                
                return ticker_info
            else:
                print(f"Error obteniendo ticker: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error en get_ticker_24h: {e}")
            return None
    
    def download_full_dataset(self, symbol="SOLUSDT"):
        """Descarga conjunto completo de datos"""
        print(f"\n=== DESCARGANDO DATOS COMPLETOS {symbol} ===")
        
        results = {}
        
        # 1. Probar conexión
        if not self.test_connection():
            print("No se pudo conectar a Binance")
            return None
        
        # 2. Precio actual
        print("\n1. Obteniendo precio actual...")
        price = self.get_price(symbol)
        results['price'] = price
        
        # 3. Ticker 24h
        print("\n2. Obteniendo estadísticas 24h...")
        ticker = self.get_ticker_24h(symbol)
        results['ticker'] = ticker
        
        # 4. Datos históricos múltiples intervalos
        intervals = ["1m", "5m", "15m", "1h"]
        results['klines'] = {}
        
        for interval in intervals:
            print(f"\n3. Descargando velas {interval}...")
            df = self.get_klines(symbol, interval, 200)
            if df is not None:
                results['klines'][interval] = len(df)
            time.sleep(0.5)  # Evitar rate limit
        
        # 5. Crear resumen
        summary = {
            "symbol": symbol,
            "download_time": datetime.now().isoformat(),
            "status": "success" if price and ticker else "partial",
            "files_created": len([f for f in os.listdir(self.data_folder) if symbol in f]),
            "price": price['price'] if price else None,
            "change_24h": ticker['change_24h'] if ticker else None
        }
        
        filename = f"{self.data_folder}/{symbol}_download_summary.json"
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n=== DESCARGA COMPLETADA ===")
        print(f"Archivos creados: {summary['files_created']}")
        print(f"Precio actual: ${summary['price']:.4f}" if summary['price'] else "Precio: N/A")
        print(f"Cambio 24h: {summary['change_24h']:+.2f}%" if summary['change_24h'] else "Cambio: N/A")
        
        return results

def main():
    """Función principal"""
    print("=== BINANCE SIMPLE DOWNLOADER ===")
    
    downloader = SimpleBinanceDownloader()
    
    # Descargar datos de SOLUSDT
    symbol = "SOLUSDT"
    results = downloader.download_full_dataset(symbol)
    
    if results:
        print(f"\nDatos descargados exitosamente en: {downloader.data_folder}/")
        print("Archivos generados:")
        for file in sorted(os.listdir(downloader.data_folder)):
            if symbol in file:
                size = os.path.getsize(f"{downloader.data_folder}/{file}")
                print(f"  {file} ({size} bytes)")
    else:
        print("Error en la descarga")

if __name__ == "__main__":
    main()