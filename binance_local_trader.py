#!/usr/bin/env python3
"""
Sistema de trading Binance optimizado para PC local
Descarga datos reales y ejecuta trading con credenciales configuradas
"""

import json
import requests
import hmac
import hashlib
import time
import pandas as pd
import numpy as np
from datetime import datetime
import os

class LocalBinanceTrader:
    def __init__(self):
        # Configuración
        self.api_key = "ampzPA2IWP1EA5NVJAdruAyPbitxs1kqc6tOkTWf9fu27LOkGVOD2A5PhMF62zX3"
        self.api_secret = "wbazWkMzHznABGONO1dD5i0qFZEUGRO8vhv1xebktqYmaHjkLZvodsRjgZZYDhCi"
        self.base_url = "https://api.binance.com"
        self.symbol = "SOLUSDT"
        
        # Estado
        self.balance_usdt = 1000.0  # Balance virtual para pruebas
        self.position = None
        self.trades = []
        
        print(f"Trader local iniciado para {self.symbol}")
        print(f"API Key: ***{self.api_key[-8:]}")
    
    def download_real_data(self):
        """Descarga datos reales de Binance (sin autenticación)"""
        try:
            print("Descargando datos reales de Binance...")
            
            # 1. Precio actual
            response = requests.get(f"{self.base_url}/api/v3/ticker/price", 
                                  params={'symbol': self.symbol}, timeout=10)
            if response.status_code != 200:
                print(f"Error precio: {response.status_code}")
                return None
            
            price_data = response.json()
            current_price = float(price_data['price'])
            
            # 2. Estadísticas 24h
            response = requests.get(f"{self.base_url}/api/v3/ticker/24hr",
                                  params={'symbol': self.symbol}, timeout=10)
            if response.status_code != 200:
                print(f"Error ticker: {response.status_code}")
                return None
            
            ticker_data = response.json()
            
            # 3. Datos históricos (200 velas de 1 minuto)
            response = requests.get(f"{self.base_url}/api/v3/klines",
                                  params={
                                      'symbol': self.symbol,
                                      'interval': '1m',
                                      'limit': 200
                                  }, timeout=15)
            if response.status_code != 200:
                print(f"Error klines: {response.status_code}")
                return None
            
            klines_data = response.json()
            
            # Procesar datos históricos
            df = pd.DataFrame(klines_data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'buy_volume', 'buy_quote_volume', 'ignore'
            ])
            
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            # Guardar datos localmente
            df.to_csv(f'{self.symbol}_live_data.csv', index=False)
            
            market_data = {
                'price': current_price,
                'change_24h': float(ticker_data['priceChangePercent']),
                'volume_24h': float(ticker_data['volume']),
                'high_24h': float(ticker_data['highPrice']),
                'low_24h': float(ticker_data['lowPrice']),
                'bid_price': float(ticker_data['bidPrice']),
                'ask_price': float(ticker_data['askPrice']),
                'historical_df': df,
                'data_points': len(df),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"✓ Precio: ${current_price:.4f}")
            print(f"✓ Cambio 24h: {market_data['change_24h']:+.2f}%")
            print(f"✓ Volumen: {market_data['volume_24h']:,.0f}")
            print(f"✓ Datos históricos: {len(df)} velas")
            print(f"✓ Rango: {df['low'].min():.4f} - {df['high'].max():.4f}")
            
            return market_data
            
        except requests.RequestException as e:
            print(f"Error de conexión: {e}")
            return None
        except Exception as e:
            print(f"Error procesando datos: {e}")
            return None
    
    def calculate_indicators(self, df):
        """Calcula indicadores técnicos avanzados"""
        try:
            # Medias móviles
            df['sma_9'] = df['close'].rolling(window=9).mean()
            df['sma_21'] = df['close'].rolling(window=21).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # EMAs
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
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Price momentum
            df['momentum'] = df['close'].pct_change(periods=5) * 100
            
            print("✓ Indicadores técnicos calculados")
            return df
            
        except Exception as e:
            print(f"Error calculando indicadores: {e}")
            return df
    
    def generate_advanced_signals(self, df):
        """Genera señales de trading avanzadas"""
        try:
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            prev2 = df.iloc[-3]
            
            buy_signals = []
            sell_signals = []
            signal_strength = 0
            
            # 1. Golden Cross (SMA 9 cruza arriba de SMA 21)
            if (latest['sma_9'] > latest['sma_21'] and 
                prev['sma_9'] <= prev['sma_21']):
                buy_signals.append("GOLDEN_CROSS")
                signal_strength += 0.3
            
            # 2. Death Cross (SMA 9 cruza abajo de SMA 21)
            if (latest['sma_9'] < latest['sma_21'] and 
                prev['sma_9'] >= prev['sma_21']):
                sell_signals.append("DEATH_CROSS")
                signal_strength -= 0.3
            
            # 3. RSI divergences y niveles
            if latest['rsi'] < 25:  # Muy sobrevendido
                buy_signals.append("RSI_OVERSOLD_EXTREME")
                signal_strength += 0.25
            elif latest['rsi'] < 30:  # Sobrevendido
                buy_signals.append("RSI_OVERSOLD")
                signal_strength += 0.15
            elif latest['rsi'] > 75:  # Muy sobrecomprado
                sell_signals.append("RSI_OVERBOUGHT_EXTREME")
                signal_strength -= 0.25
            elif latest['rsi'] > 70:  # Sobrecomprado
                sell_signals.append("RSI_OVERBOUGHT")
                signal_strength -= 0.15
            
            # 4. MACD bullish/bearish
            if (latest['macd'] > latest['macd_signal'] and 
                prev['macd'] <= prev['macd_signal']):
                buy_signals.append("MACD_BULLISH_CROSS")
                signal_strength += 0.2
            elif (latest['macd'] < latest['macd_signal'] and 
                  prev['macd'] >= prev['macd_signal']):
                sell_signals.append("MACD_BEARISH_CROSS")
                signal_strength -= 0.2
            
            # 5. Bollinger Bands squeeze/expansion
            if latest['close'] <= latest['bb_lower']:
                buy_signals.append("BB_LOWER_TOUCH")
                signal_strength += 0.15
            elif latest['close'] >= latest['bb_upper']:
                sell_signals.append("BB_UPPER_TOUCH")
                signal_strength -= 0.15
            
            # 6. Volume confirmation
            if latest['volume_ratio'] > 1.5:  # Alto volumen
                if signal_strength > 0:
                    buy_signals.append("HIGH_VOLUME_CONFIRM")
                    signal_strength += 0.1
                elif signal_strength < 0:
                    sell_signals.append("HIGH_VOLUME_CONFIRM")
                    signal_strength -= 0.1
            
            # 7. Momentum
            if latest['momentum'] > 2:  # Fuerte momentum alcista
                buy_signals.append("STRONG_MOMENTUM_UP")
                signal_strength += 0.1
            elif latest['momentum'] < -2:  # Fuerte momentum bajista
                sell_signals.append("STRONG_MOMENTUM_DOWN")
                signal_strength -= 0.1
            
            # Determinar acción final
            if signal_strength > 0.6:
                action = "BUY"
                confidence = min(signal_strength, 1.0)
                active_signals = buy_signals
            elif signal_strength < -0.6:
                action = "SELL"
                confidence = min(abs(signal_strength), 1.0)
                active_signals = sell_signals
            else:
                action = "HOLD"
                confidence = 0
                active_signals = []
            
            signal_data = {
                'action': action,
                'confidence': confidence,
                'signal_strength': signal_strength,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'active_signals': active_signals,
                'price': latest['close'],
                'rsi': latest['rsi'],
                'macd': latest['macd'],
                'volume_ratio': latest['volume_ratio'],
                'momentum': latest['momentum'],
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"✓ Señal: {action}")
            if confidence > 0:
                print(f"✓ Confianza: {confidence*100:.1f}%")
                print(f"✓ Indicadores activos: {', '.join(active_signals)}")
            
            return signal_data
            
        except Exception as e:
            print(f"Error generando señales: {e}")
            return {'action': 'HOLD', 'confidence': 0}
    
    def simulate_trading(self, signal_data, market_data):
        """Simula operaciones de trading (paper trading)"""
        try:
            action = signal_data['action']
            confidence = signal_data['confidence']
            price = market_data['price']
            
            # Requiere alta confianza
            if confidence < 0.7:
                print(f"Confianza insuficiente: {confidence*100:.1f}% < 70%")
                return False
            
            if action == "BUY" and not self.position:
                # Abrir posición long
                position_size = self.balance_usdt * 0.1  # 10% del balance
                quantity = position_size / price
                
                self.position = {
                    'type': 'LONG',
                    'entry_price': price,
                    'quantity': quantity,
                    'entry_time': datetime.now(),
                    'position_value': position_size,
                    'stop_loss': price * 0.985,  # 1.5% stop loss
                    'take_profit': price * 1.025,  # 2.5% take profit
                    'signals': signal_data['active_signals']
                }
                
                print(f"🟢 POSICIÓN ABIERTA:")
                print(f"   Tipo: LONG")
                print(f"   Precio: ${price:.4f}")
                print(f"   Cantidad: {quantity:.6f} SOL")
                print(f"   Valor: ${position_size:.2f}")
                print(f"   Stop Loss: ${self.position['stop_loss']:.4f}")
                print(f"   Take Profit: ${self.position['take_profit']:.4f}")
                
                return True
                
            elif action == "SELL" and self.position and self.position['type'] == 'LONG':
                # Cerrar posición long
                entry_price = self.position['entry_price']
                quantity = self.position['quantity']
                pnl = (price - entry_price) * quantity
                pnl_percent = (pnl / self.position['position_value']) * 100
                
                # Actualizar balance
                self.balance_usdt += pnl
                
                # Registrar trade
                trade = {
                    'entry_time': self.position['entry_time'].isoformat(),
                    'exit_time': datetime.now().isoformat(),
                    'type': 'LONG',
                    'entry_price': entry_price,
                    'exit_price': price,
                    'quantity': quantity,
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'exit_reason': 'SIGNAL',
                    'entry_signals': self.position['signals'],
                    'exit_signals': signal_data['active_signals']
                }
                
                self.trades.append(trade)
                self.position = None
                
                print(f"🔴 POSICIÓN CERRADA:")
                print(f"   P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)")
                print(f"   Precio salida: ${price:.4f}")
                print(f"   Nuevo balance: ${self.balance_usdt:.2f}")
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error en simulación: {e}")
            return False
    
    def check_stop_loss_take_profit(self, current_price):
        """Verifica stop loss y take profit"""
        if not self.position:
            return False
        
        stop_loss = self.position['stop_loss']
        take_profit = self.position['take_profit']
        
        if current_price <= stop_loss:
            print(f"⚠️ STOP LOSS activado: ${current_price:.4f} <= ${stop_loss:.4f}")
            return self.close_position_at_price(current_price, "STOP_LOSS")
        elif current_price >= take_profit:
            print(f"🎯 TAKE PROFIT activado: ${current_price:.4f} >= ${take_profit:.4f}")
            return self.close_position_at_price(current_price, "TAKE_PROFIT")
        
        return False
    
    def close_position_at_price(self, price, reason):
        """Cierra posición a precio específico"""
        if not self.position:
            return False
        
        entry_price = self.position['entry_price']
        quantity = self.position['quantity']
        pnl = (price - entry_price) * quantity
        pnl_percent = (pnl / self.position['position_value']) * 100
        
        self.balance_usdt += pnl
        
        trade = {
            'entry_time': self.position['entry_time'].isoformat(),
            'exit_time': datetime.now().isoformat(),
            'type': 'LONG',
            'entry_price': entry_price,
            'exit_price': price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'exit_reason': reason,
            'entry_signals': self.position['signals']
        }
        
        self.trades.append(trade)
        self.position = None
        
        print(f"Posición cerrada por {reason}: P&L ${pnl:.2f} ({pnl_percent:+.2f}%)")
        return True
    
    def run_complete_analysis(self):
        """Ejecuta análisis completo del mercado"""
        print(f"\n{'='*60}")
        print(f"ANÁLISIS COMPLETO {self.symbol} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
        # 1. Descargar datos reales
        market_data = self.download_real_data()
        if not market_data:
            print("❌ Error descargando datos de mercado")
            return False
        
        # 2. Verificar stop loss/take profit
        if self.position:
            if self.check_stop_loss_take_profit(market_data['price']):
                # Si se cerró por SL/TP, no procesar nuevas señales
                pass
        
        # 3. Calcular indicadores
        df = self.calculate_indicators(market_data['historical_df'])
        
        # 4. Generar señales
        signals = self.generate_advanced_signals(df)
        
        # 5. Ejecutar trading
        if signals['action'] != 'HOLD':
            self.simulate_trading(signals, market_data)
        
        # 6. Mostrar estado actual
        print(f"\n📊 ESTADO ACTUAL:")
        print(f"   Balance: ${self.balance_usdt:.2f}")
        print(f"   Posición: {'Abierta (' + self.position['type'] + ')' if self.position else 'Cerrada'}")
        print(f"   Trades realizados: {len(self.trades)}")
        
        if self.trades:
            total_pnl = sum(t['pnl'] for t in self.trades)
            winning_trades = len([t for t in self.trades if t['pnl'] > 0])
            win_rate = (winning_trades / len(self.trades)) * 100
            print(f"   P&L total: ${total_pnl:.2f}")
            print(f"   Win rate: {win_rate:.1f}%")
        
        # 7. Guardar datos
        self.save_analysis_data(market_data, signals, df)
        
        return True
    
    def save_analysis_data(self, market_data, signals, df):
        """Guarda datos de análisis"""
        try:
            # Guardar log de trading
            trading_log = {
                'symbol': self.symbol,
                'timestamp': datetime.now().isoformat(),
                'balance': self.balance_usdt,
                'current_position': self.position,
                'total_trades': len(self.trades),
                'trades': self.trades,
                'current_market': {
                    'price': market_data['price'],
                    'change_24h': market_data['change_24h'],
                    'volume_24h': market_data['volume_24h']
                },
                'current_signals': signals
            }
            
            with open(f'{self.symbol}_trading_log.json', 'w') as f:
                json.dump(trading_log, f, indent=2, default=str)
            
            # Guardar datos técnicos procesados
            df_recent = df.tail(50)  # Últimas 50 velas
            df_recent.to_csv(f'{self.symbol}_technical_analysis.csv', index=False)
            
            print(f"✓ Datos guardados en archivos locales")
            
        except Exception as e:
            print(f"Error guardando datos: {e}")

def main():
    """Función principal"""
    print("🚀 SISTEMA TRADING BINANCE LOCAL")
    print("Conectando con datos reales de Binance...")
    
    try:
        trader = LocalBinanceTrader()
        success = trader.run_complete_analysis()
        
        if success:
            print(f"\n✅ Análisis completado exitosamente")
            print(f"📁 Archivos generados:")
            print(f"   - {trader.symbol}_live_data.csv")
            print(f"   - {trader.symbol}_trading_log.json")
            print(f"   - {trader.symbol}_technical_analysis.csv")
        else:
            print(f"\n❌ Error en análisis")
            
    except Exception as e:
        print(f"Error general: {e}")

if __name__ == "__main__":
    main()