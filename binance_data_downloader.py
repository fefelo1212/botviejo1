#!/usr/bin/env python3
"""
Módulo independiente para descargar datos de Binance
Descarga datos históricos y en tiempo real sin integración con bot
"""

import requests
import json
import time
import pandas as pd
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional
import websocket
import threading

class BinanceDataDownloader:
    """
    Descargador de datos de Binance completamente independiente
    No requiere API keys - usa endpoints públicos
    """
    
    def __init__(self, base_url: str = "https://api.binance.com"):
        self.base_url = base_url
        self.ws_url = "wss://stream.binance.com:9443/ws/"
        self.data_folder = "binance_data"
        self.create_data_folder()
        
    def create_data_folder(self):
        """Crea carpeta para guardar datos"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            print(f"Carpeta creada: {self.data_folder}")
    
    def get_server_time(self) -> Dict:
        """Obtiene tiempo del servidor Binance"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/time", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'serverTime' not in data:
                print(f"Respuesta inesperada del servidor: {data}")
                return None
                
            server_time = datetime.fromtimestamp(data['serverTime'] / 1000)
            print(f"Tiempo servidor Binance: {server_time}")
            return {"serverTime": data['serverTime'], "formatted": server_time}
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión con Binance: {e}")
            return None
        except Exception as e:
            print(f"Error procesando respuesta: {e}")
            return None
    
    def get_exchange_info(self) -> Dict:
        """Obtiene información del exchange y símbolos disponibles"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/exchangeInfo")
            data = response.json()
            
            # Guardar información completa
            filename = f"{self.data_folder}/exchange_info.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"Información del exchange guardada en: {filename}")
            print(f"Total símbolos disponibles: {len(data['symbols'])}")
            
            return data
        except Exception as e:
            print(f"Error obteniendo info exchange: {e}")
            return None
    
    def get_symbol_price(self, symbol: str = "SOLUSDT") -> Dict:
        """Obtiene precio actual de un símbolo"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/ticker/price", 
                                  params={"symbol": symbol})
            data = response.json()
            
            timestamp = datetime.now()
            price_data = {
                "symbol": data["symbol"],
                "price": float(data["price"]),
                "timestamp": timestamp.isoformat(),
                "timestamp_ms": int(timestamp.timestamp() * 1000)
            }
            
            print(f"{symbol}: ${price_data['price']:.4f} - {timestamp}")
            return price_data
            
        except Exception as e:
            print(f"Error obteniendo precio {symbol}: {e}")
            return None
    
    def get_24hr_ticker(self, symbol: str = "SOLUSDT") -> Dict:
        """Obtiene estadísticas de 24 horas"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/ticker/24hr",
                                  params={"symbol": symbol})
            data = response.json()
            
            ticker_data = {
                "symbol": data["symbol"],
                "priceChange": float(data["priceChange"]),
                "priceChangePercent": float(data["priceChangePercent"]),
                "weightedAvgPrice": float(data["weightedAvgPrice"]),
                "prevClosePrice": float(data["prevClosePrice"]),
                "lastPrice": float(data["lastPrice"]),
                "bidPrice": float(data["bidPrice"]),
                "askPrice": float(data["askPrice"]),
                "openPrice": float(data["openPrice"]),
                "highPrice": float(data["highPrice"]),
                "lowPrice": float(data["lowPrice"]),
                "volume": float(data["volume"]),
                "quoteVolume": float(data["quoteVolume"]),
                "openTime": data["openTime"],
                "closeTime": data["closeTime"],
                "count": data["count"],
                "timestamp": datetime.now().isoformat()
            }
            
            # Guardar datos
            filename = f"{self.data_folder}/{symbol}_24hr_ticker.json"
            with open(filename, 'w') as f:
                json.dump(ticker_data, f, indent=2)
            
            print(f"Ticker 24hr {symbol} guardado en: {filename}")
            print(f"Precio: ${ticker_data['lastPrice']:.4f} ({ticker_data['priceChangePercent']:.2f}%)")
            
            return ticker_data
            
        except Exception as e:
            print(f"Error obteniendo ticker 24hr {symbol}: {e}")
            return None
    
    def get_klines_historical(self, symbol: str = "SOLUSDT", 
                            interval: str = "1m", 
                            limit: int = 1000,
                            start_time: Optional[str] = None,
                            end_time: Optional[str] = None) -> pd.DataFrame:
        """
        Descarga datos históricos de velas (klines)
        
        Args:
            symbol: Par de trading (ej: SOLUSDT)
            interval: Intervalo (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Número de velas (máximo 1000)
            start_time: Tiempo inicio formato 'YYYY-MM-DD HH:MM:SS'
            end_time: Tiempo fin formato 'YYYY-MM-DD HH:MM:SS'
        """
        try:
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            # Convertir tiempos si se proporcionan
            if start_time:
                start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                params["startTime"] = int(start_dt.timestamp() * 1000)
            
            if end_time:
                end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                params["endTime"] = int(end_dt.timestamp() * 1000)
            
            response = requests.get(f"{self.base_url}/api/v3/klines", params=params)
            data = response.json()
            
            # Convertir a DataFrame
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos de datos
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 
                          'quote_asset_volume', 'number_of_trades',
                          'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col])
            
            # Guardar datos
            filename = f"{self.data_folder}/{symbol}_{interval}_klines.csv"
            df.to_csv(filename, index=False)
            
            print(f"Datos históricos guardados: {filename}")
            print(f"Período: {df['open_time'].min()} a {df['open_time'].max()}")
            print(f"Total velas: {len(df)}")
            print(f"Último precio: ${df['close'].iloc[-1]:.4f}")
            
            return df
            
        except Exception as e:
            print(f"Error descargando klines {symbol}: {e}")
            return None
    
    def get_order_book(self, symbol: str = "SOLUSDT", limit: int = 100) -> Dict:
        """Obtiene libro de órdenes (depth)"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/depth",
                                  params={"symbol": symbol, "limit": limit})
            data = response.json()
            
            order_book = {
                "symbol": symbol,
                "lastUpdateId": data["lastUpdateId"],
                "bids": [[float(price), float(qty)] for price, qty in data["bids"]],
                "asks": [[float(price), float(qty)] for price, qty in data["asks"]],
                "timestamp": datetime.now().isoformat()
            }
            
            # Guardar datos
            filename = f"{self.data_folder}/{symbol}_orderbook.json"
            with open(filename, 'w') as f:
                json.dump(order_book, f, indent=2)
            
            print(f"Order book {symbol} guardado: {filename}")
            print(f"Mejor bid: ${order_book['bids'][0][0]:.4f}")
            print(f"Mejor ask: ${order_book['asks'][0][0]:.4f}")
            
            return order_book
            
        except Exception as e:
            print(f"Error obteniendo order book {symbol}: {e}")
            return None
    
    def get_recent_trades(self, symbol: str = "SOLUSDT", limit: int = 500) -> List[Dict]:
        """Obtiene trades recientes"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/trades",
                                  params={"symbol": symbol, "limit": limit})
            data = response.json()
            
            trades = []
            for trade in data:
                trade_data = {
                    "id": trade["id"],
                    "price": float(trade["price"]),
                    "qty": float(trade["qty"]),
                    "quoteQty": float(trade["quoteQty"]),
                    "time": datetime.fromtimestamp(trade["time"] / 1000).isoformat(),
                    "isBuyerMaker": trade["isBuyerMaker"],
                    "isBestMatch": trade["isBestMatch"]
                }
                trades.append(trade_data)
            
            # Guardar datos
            filename = f"{self.data_folder}/{symbol}_recent_trades.json"
            with open(filename, 'w') as f:
                json.dump(trades, f, indent=2)
            
            print(f"Trades recientes {symbol} guardados: {filename}")
            print(f"Total trades: {len(trades)}")
            print(f"Último precio: ${trades[-1]['price']:.4f}")
            
            return trades
            
        except Exception as e:
            print(f"Error obteniendo trades recientes {symbol}: {e}")
            return None
    
    def download_multiple_intervals(self, symbol: str = "SOLUSDT", 
                                  intervals: List[str] = ["1m", "5m", "15m", "1h"]) -> Dict:
        """Descarga datos en múltiples intervalos"""
        results = {}
        
        print(f"Descargando datos de {symbol} en múltiples intervalos...")
        
        for interval in intervals:
            print(f"\nDescargando intervalo {interval}...")
            df = self.get_klines_historical(symbol, interval, limit=1000)
            if df is not None:
                results[interval] = df
                print(f"✓ {interval}: {len(df)} velas descargadas")
            else:
                print(f"✗ Error descargando {interval}")
        
        print(f"\nDescarga completada. Intervalos exitosos: {len(results)}")
        return results
    
    def create_summary_report(self, symbol: str = "SOLUSDT") -> Dict:
        """Crea reporte resumen de todos los datos descargados"""
        try:
            print(f"\nCreando reporte resumen para {symbol}...")
            
            # Obtener datos básicos
            price = self.get_symbol_price(symbol)
            ticker = self.get_24hr_ticker(symbol)
            
            # Datos de archivos guardados
            data_files = []
            for file in os.listdir(self.data_folder):
                if symbol in file:
                    file_path = os.path.join(self.data_folder, file)
                    file_size = os.path.getsize(file_path)
                    data_files.append({
                        "filename": file,
                        "size_bytes": file_size,
                        "size_kb": round(file_size / 1024, 2)
                    })
            
            summary = {
                "symbol": symbol,
                "report_time": datetime.now().isoformat(),
                "current_price": price,
                "ticker_24hr": ticker,
                "downloaded_files": data_files,
                "total_files": len(data_files),
                "total_size_kb": sum([f["size_kb"] for f in data_files])
            }
            
            # Guardar reporte
            filename = f"{self.data_folder}/{symbol}_summary_report.json"
            with open(filename, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"Reporte resumen guardado: {filename}")
            print(f"Total archivos: {summary['total_files']}")
            print(f"Tamaño total: {summary['total_size_kb']:.2f} KB")
            
            return summary
            
        except Exception as e:
            print(f"Error creando reporte resumen: {e}")
            return None

def main():
    """Función principal para probar el descargador"""
    print("=== BINANCE DATA DOWNLOADER ===")
    print("Descargador independiente de datos de Binance")
    
    # Crear instancia del descargador
    downloader = BinanceDataDownloader()
    
    # Símbolo a descargar
    symbol = "SOLUSDT"
    
    print(f"\n1. Verificando conexión con Binance...")
    server_time = downloader.get_server_time()
    
    if server_time:
        print(f"\n2. Descargando precio actual de {symbol}...")
        price = downloader.get_symbol_price(symbol)
        
        print(f"\n3. Descargando ticker 24hr de {symbol}...")
        ticker = downloader.get_24hr_ticker(symbol)
        
        print(f"\n4. Descargando datos históricos...")
        df = downloader.get_klines_historical(symbol, "1m", 1000)
        
        print(f"\n5. Descargando order book...")
        order_book = downloader.get_order_book(symbol)
        
        print(f"\n6. Descargando trades recientes...")
        trades = downloader.get_recent_trades(symbol)
        
        print(f"\n7. Descargando múltiples intervalos...")
        multiple_data = downloader.download_multiple_intervals(symbol)
        
        print(f"\n8. Creando reporte resumen...")
        summary = downloader.create_summary_report(symbol)
        
        print(f"\n=== DESCARGA COMPLETADA ===")
        print(f"Todos los datos guardados en: {downloader.data_folder}/")
        print(f"Revisa los archivos .csv y .json generados")
        
    else:
        print("Error: No se pudo conectar con Binance")

if __name__ == "__main__":
    main()