#!/usr/bin/env python3
"""
Bot de trading Binance configurado con credenciales reales
Sistema completo: descarga → procesamiento → trading
"""

import json
import requests
import hmac
import hashlib
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

class BinanceTradingSystem:
    def __init__(self):
        # Cargar configuración
        with open('binance_config.json', 'r') as f:
            self.config = json.load(f)
        
        self.api_key = self.config['api_key']
        self.api_secret = self.config['api_secret']
        self.base_url = self.config['base_url']
        self.symbol = self.config['symbol']
        self.position_size = self.config['position_size']
        
        # Estado del trading
        self.balance_usdt = 0
        self.position = None
        self.trades_log = []
        
        print(f"Sistema Binance inicializado para {self.symbol}")
        print(f"API Key: ***{self.api_key[-8:]}")
    
    def _get_signature(self, params_str):
        """Genera signature para autenticación"""
        timestamp = int(time.time() * 1000)
        query_string = f"{params_str}&timestamp={timestamp}" if params_str else f"timestamp={timestamp}"
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp
    
    def download_market_data(self):
        """Descarga datos de mercado en tiempo real"""
        try:
            print("Descargando datos de mercado...")
            
            # Precio actual
            response = requests.get(f"{self.base_url}/api/v3/ticker/price",
                                  params={'symbol': self.symbol}, timeout=5)
            response.raise_for_status()
            price_data = response.json()
            current_price = float(price_data['price'])
            
            # Ticker 24h
            response = requests.get(f"{self.base_url}/api/v3/ticker/24hr",
                                  params={'symbol': self.symbol}, timeout=5)
            response.raise_for_status()
            ticker_data = response.json()
            
            # Datos históricos (100 velas de 1 minuto)
            response = requests.get(f"{self.base_url}/api/v3/klines",
                                  params={
                                      'symbol': self.symbol,
                                      'interval': '1m',
                                      'limit': 100
                                  }, timeout=10)
            response.raise_for_status()
            klines = response.json()
            
            # Procesar datos históricos
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'buy_volume', 'buy_quote_volume', 'ignore'
            ])
            
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            # Guardar datos
            df.to_csv(f'{self.symbol}_market_data.csv', index=False)
            
            market_data = {
                'current_price': current_price,
                'change_24h': float(ticker_data['priceChangePercent']),
                'volume_24h': float(ticker_data['volume']),
                'high_24h': float(ticker_data['highPrice']),
                'low_24h': float(ticker_data['lowPrice']),
                'historical_data': df,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"Precio actual: ${current_price:.4f}")
            print(f"Cambio 24h: {market_data['change_24h']:+.2f}%")
            print(f"Datos históricos: {len(df)} velas")
            
            return market_data
            
        except Exception as e:
            print(f"Error descargando datos: {e}")
            return None
    
    def calculate_technical_indicators(self, df):
        """Calcula indicadores técnicos"""
        try:
            # SMA
            df['sma_5'] = df['close'].rolling(window=5).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # EMA
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # RSI
            delta = df['close'].diff()
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            avg_gains = gains.rolling(window=14).mean()
            avg_losses = losses.rolling(window=14).mean()
            rs = avg_gains / avg_losses
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            print("Indicadores técnicos calculados")
            return df
            
        except Exception as e:
            print(f"Error calculando indicadores: {e}")
            return df
    
    def generate_trading_signals(self, df):
        """Genera señales de trading"""
        try:
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            signals = []
            signal_strength = 0
            
            # Señal SMA Crossover
            if latest['sma_5'] > latest['sma_20'] and prev['sma_5'] <= prev['sma_20']:
                signals.append("SMA_BULLISH_CROSS")
                signal_strength += 0.3
            elif latest['sma_5'] < latest['sma_20'] and prev['sma_5'] >= prev['sma_20']:
                signals.append("SMA_BEARISH_CROSS")
                signal_strength -= 0.3
            
            # Señal RSI
            if latest['rsi'] < 30:
                signals.append("RSI_OVERSOLD")
                signal_strength += 0.2
            elif latest['rsi'] > 70:
                signals.append("RSI_OVERBOUGHT")
                signal_strength -= 0.2
            
            # Señal MACD
            if latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']:
                signals.append("MACD_BULLISH")
                signal_strength += 0.25
            elif latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']:
                signals.append("MACD_BEARISH")
                signal_strength -= 0.25
            
            # Señal Bollinger Bands
            if latest['close'] < latest['bb_lower']:
                signals.append("BB_OVERSOLD")
                signal_strength += 0.15
            elif latest['close'] > latest['bb_upper']:
                signals.append("BB_OVERBOUGHT")
                signal_strength -= 0.15
            
            # Determinar acción
            if signal_strength > 0.5:
                action = "BUY"
                confidence = min(signal_strength, 1.0)
            elif signal_strength < -0.5:
                action = "SELL"
                confidence = min(abs(signal_strength), 1.0)
            else:
                action = "HOLD"
                confidence = 0
            
            signal_data = {
                'action': action,
                'confidence': confidence,
                'signals': signals,
                'signal_strength': signal_strength,
                'price': latest['close'],
                'rsi': latest['rsi'],
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"Señal generada: {action} (confianza: {confidence*100:.1f}%)")
            if signals:
                print(f"Indicadores: {', '.join(signals)}")
            
            return signal_data
            
        except Exception as e:
            print(f"Error generando señales: {e}")
            return {'action': 'HOLD', 'confidence': 0}
    
    def get_account_info(self):
        """Obtiene información de la cuenta"""
        try:
            signature, timestamp = self._get_signature("")
            headers = {'X-MBX-APIKEY': self.api_key}
            params = {'timestamp': timestamp, 'signature': signature}
            
            response = requests.get(f"{self.base_url}/api/v3/account",
                                  headers=headers, params=params, timeout=10)
            response.raise_for_status()
            account = response.json()
            
            # Extraer balance USDT
            balances = account.get('balances', [])
            usdt_balance = next((b for b in balances if b['asset'] == 'USDT'), None)
            
            if usdt_balance:
                self.balance_usdt = float(usdt_balance['free'])
                print(f"Balance USDT: ${self.balance_usdt:.2f}")
            
            return {
                'can_trade': account.get('canTrade', False),
                'balance_usdt': self.balance_usdt,
                'balances': {b['asset']: float(b['free']) for b in balances if float(b['free']) > 0}
            }
            
        except Exception as e:
            print(f"Error obteniendo cuenta: {e}")
            return None
    
    def place_market_order(self, side, quantity):
        """Coloca orden de mercado"""
        try:
            params_str = f"symbol={self.symbol}&side={side}&type=MARKET&quantity={quantity:.6f}"
            signature, timestamp = self._get_signature(params_str)
            
            headers = {'X-MBX-APIKEY': self.api_key}
            data = {
                'symbol': self.symbol,
                'side': side,
                'type': 'MARKET',
                'quantity': f"{quantity:.6f}",
                'timestamp': timestamp,
                'signature': signature
            }
            
            response = requests.post(f"{self.base_url}/api/v3/order",
                                   headers=headers, data=data, timeout=10)
            
            if response.status_code == 200:
                order = response.json()
                print(f"Orden ejecutada: {side} {quantity:.6f} {self.symbol}")
                return order
            else:
                print(f"Error en orden: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error colocando orden: {e}")
            return None
    
    def execute_trading_signal(self, signal_data, market_data):
        """Ejecuta señal de trading"""
        try:
            action = signal_data['action']
            confidence = signal_data['confidence']
            price = market_data['current_price']
            
            # Requiere alta confianza para operar
            if confidence < 0.7:
                print(f"Confianza insuficiente: {confidence*100:.1f}% < 70%")
                return False
            
            # Verificar balance mínimo
            if self.balance_usdt < 20:
                print(f"Balance insuficiente: ${self.balance_usdt:.2f} < $20")
                return False
            
            if action == "BUY" and not self.position:
                # Calcular cantidad a comprar
                position_value = self.balance_usdt * self.position_size
                quantity = position_value / price
                
                # Ejecutar orden
                order = self.place_market_order("BUY", quantity)
                if order:
                    self.position = {
                        'side': 'BUY',
                        'quantity': quantity,
                        'entry_price': price,
                        'entry_time': datetime.now(),
                        'order_id': order.get('orderId')
                    }
                    print(f"Posición abierta: COMPRA {quantity:.6f} a ${price:.4f}")
                    return True
            
            elif action == "SELL" and self.position and self.position['side'] == 'BUY':
                # Cerrar posición long
                quantity = self.position['quantity']
                order = self.place_market_order("SELL", quantity)
                
                if order:
                    entry_price = self.position['entry_price']
                    pnl = (price - entry_price) * quantity
                    pnl_percent = (pnl / (entry_price * quantity)) * 100
                    
                    trade_record = {
                        'entry_time': self.position['entry_time'].isoformat(),
                        'exit_time': datetime.now().isoformat(),
                        'side': 'BUY',
                        'quantity': quantity,
                        'entry_price': entry_price,
                        'exit_price': price,
                        'pnl': pnl,
                        'pnl_percent': pnl_percent,
                        'reason': 'SIGNAL'
                    }
                    
                    self.trades_log.append(trade_record)
                    self.position = None
                    
                    print(f"Posición cerrada: P&L ${pnl:.2f} ({pnl_percent:+.2f}%)")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error ejecutando señal: {e}")
            return False
    
    def run_trading_cycle(self):
        """Ejecuta un ciclo completo de trading"""
        print(f"\n=== CICLO TRADING {datetime.now().strftime('%H:%M:%S')} ===")
        
        # 1. Obtener información de cuenta
        account = self.get_account_info()
        if not account or not account['can_trade']:
            print("Cuenta no puede operar")
            return False
        
        # 2. Descargar datos de mercado
        market_data = self.download_market_data()
        if not market_data:
            print("No se pudieron obtener datos de mercado")
            return False
        
        # 3. Calcular indicadores técnicos
        df = self.calculate_technical_indicators(market_data['historical_data'])
        
        # 4. Generar señales de trading
        signal = self.generate_trading_signals(df)
        
        # 5. Ejecutar trading si hay señal
        if signal['action'] != 'HOLD':
            self.execute_trading_signal(signal, market_data)
        else:
            print("Sin señales de trading")
        
        # 6. Mostrar estado actual
        print(f"Balance: ${self.balance_usdt:.2f}")
        print(f"Posición: {'Abierta' if self.position else 'Cerrada'}")
        print(f"Trades realizados: {len(self.trades_log)}")
        
        return True
    
    def save_trading_log(self):
        """Guarda log de trading"""
        log_data = {
            'symbol': self.symbol,
            'trades': self.trades_log,
            'total_trades': len(self.trades_log),
            'current_balance': self.balance_usdt,
            'position': self.position,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(f'{self.symbol}_trading_log.json', 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        print(f"Log guardado: {self.symbol}_trading_log.json")

def main():
    """Función principal"""
    print("=== SISTEMA TRADING BINANCE REAL ===")
    
    try:
        # Crear sistema de trading
        trader = BinanceTradingSystem()
        
        # Ejecutar ciclo de trading
        success = trader.run_trading_cycle()
        
        if success:
            # Guardar log
            trader.save_trading_log()
            print("\nCiclo completado exitosamente")
        else:
            print("\nError en ciclo de trading")
            
    except FileNotFoundError:
        print("Error: No se encontró binance_config.json")
        print("Ejecuta configure_binance_system.py primero")
    except Exception as e:
        print(f"Error general: {e}")

if __name__ == "__main__":
    main()