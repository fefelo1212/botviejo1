#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Trading con Aprendizaje Automático
Modo paper trading para entrenamiento sin riesgo
"""
import os
import sys
import asyncio
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Optional
from websockets import connect

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("LearningBot")

# Cargar configuración
config_path = Path("config.env")
load_dotenv(dotenv_path=config_path)

class BinanceWebSocketClient:
    """Cliente WebSocket para Binance"""
    def __init__(self, data_queue):
        self.data_queue = data_queue
        self.ws = None
        self.is_connected = False
        self.symbol = os.getenv("DEFAULT_SYMBOL", "SOLUSDT").lower()
        # Construir URL con streams directamente
        streams = [
            f"{self.symbol}@kline_1m",  # Velas de 1 minuto
            f"{self.symbol}@trade",     # Trades en tiempo real
            f"{self.symbol}@depth20"    # Profundidad del mercado
        ]
        self.base_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"

    async def connect(self):
        """Establece la conexión WebSocket con Binance."""
        try:
            self.ws = await connect(self.base_url)
            self.is_connected = True
            logger.info("Conexión establecida con Binance WebSocket")
            return True
        except Exception as e:
            logger.error(f"Error al conectar con Binance WebSocket: {e}")
            self.is_connected = False
            return False

    async def subscribe(self, channels: List[str]):
        """Ya no necesita suscribirse porque los streams están en la URL"""
        return True

    async def _process_message(self, message):
        """Procesa un mensaje recibido del WebSocket."""
        try:
            data = json.loads(message)
            
            # El formato de los streams combinados incluye un campo 'data'
            if 'data' in data:
                data = data['data']

            # Procesar según el tipo de datos
            if "k" in data:  # Datos de vela
                candle = data['k']
                processed_data = {
                    "type": "kline",
                    "data": [{
                        "timestamp": candle['t'],
                        "open": float(candle['o']),
                        "high": float(candle['h']),
                        "low": float(candle['l']),
                        "close": float(candle['c']),
                        "volume": float(candle['v'])
                    }]
                }
                await self.data_queue.put(processed_data)

        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")

    async def receive_messages(self):
        """Recibe mensajes del WebSocket."""
        while True:
            try:
                if not self.ws:
                    await asyncio.sleep(1)
                    continue

                async for message in self.ws:
                    await self._process_message(message)

            except Exception as e:
                logger.error(f"Error recibiendo mensajes: {e}")
                if not self.is_connected:
                    await asyncio.sleep(5)
                    try:
                        await self.connect()
                    except:
                        continue

class PaperTradingEngine:
    """Motor de paper trading con aprendizaje"""
    
    def __init__(self, symbol="SOLUSDT", initial_balance=10000):
        self.symbol = symbol
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.position = None
        self.trades = []
        self.market_data = []
        self.learning_data = []
        
        # Configuración de riesgo
        self.max_position_size = 0.01  # 1% del balance
        self.take_profit_pct = 0.015   # 1.5% de ganancia objetivo
        self.stop_loss_pct = 0.01      # 1% de pérdida máxima
        
        # Configuración de indicadores
        self.indicator_weights = {
            'rsi': 0.3,
            'macd': 0.3,
            'sma_cross': 0.4
        }
        
        # Parámetros de indicadores
        self.indicator_config = {
            'rsi': {
                'period': 14,
                'overbought': 70,
                'oversold': 30
            },
            'macd': {
                'fast': 12,
                'slow': 26,
                'signal': 9
            },
            'sma': {
                'fast': 5,
                'slow': 20
            }
        }
        
        logger.info(f"Bot inicializado - Symbol: {self.symbol} - Balance inicial: ${self.initial_balance:.2f}")

    def analyze_market(self, candle_data):
        """Analiza datos de mercado y toma decisiones usando pesos dinámicos"""
        if len(self.market_data) < 26:  # Necesitamos al menos 26 velas para MACD
            return None
            
        df = pd.DataFrame(self.market_data)
        df = self.calculate_technical_indicators(df)
        
        current_price = float(candle_data['close'])
        current_data = df.iloc[-1]
        
        # Señales técnicas usando la configuración actual
        signals = {
            'rsi': {
                'value': current_data['rsi'],
                'signal': 1 if current_data['rsi'] < self.indicator_config['rsi']['oversold'] else 
                         -1 if current_data['rsi'] > self.indicator_config['rsi']['overbought'] else 0,
                'weight': self.indicator_weights['rsi']
            },
            'macd': {
                'value': current_data['macd'],
                'signal': 1 if current_data['macd'] > current_data['macd_signal'] else 
                         -1 if current_data['macd'] < current_data['macd_signal'] else 0,
                'weight': self.indicator_weights['macd']
            },
            'sma_cross': {
                'value': current_data['sma_fast'] - current_data['sma_slow'],
                'signal': 1 if current_data['sma_fast'] > current_data['sma_slow'] else 
                         -1 if current_data['sma_fast'] < current_data['sma_slow'] else 0,
                'weight': self.indicator_weights['sma_cross']
            }
        }
        
        # Calcular señal combinada
        weighted_signal = sum(s['signal'] * s['weight'] for s in signals.values())
        
        return {
            'price': current_price,
            'signals': signals,
            'weighted_signal': weighted_signal,
            'signal': 1 if weighted_signal > 0.5 else -1 if weighted_signal < -0.5 else 0
        }

    def calculate_technical_indicators(self, df):
        """Calcula indicadores técnicos en el DataFrame"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.indicator_config['rsi']['period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.indicator_config['rsi']['period']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=self.indicator_config['macd']['fast']).mean()
        exp2 = df['close'].ewm(span=self.indicator_config['macd']['slow']).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=self.indicator_config['macd']['signal']).mean()
        
        # SMAs
        df['sma_fast'] = df['close'].rolling(window=self.indicator_config['sma']['fast']).mean()
        df['sma_slow'] = df['close'].rolling(window=self.indicator_config['sma']['slow']).mean()
        
        return df

    def execute_trade(self, analysis):
        """Ejecuta operaciones basadas en el análisis"""
        if not analysis or 'signal' not in analysis:
            return
            
        current_price = analysis['price']
        signal = analysis['signal']
        
        # Si no hay posición abierta, considerar abrir una
        if self.position is None:
            if signal == 1:  # Señal de compra
                position_size = self.balance * self.max_position_size
                quantity = position_size / current_price
                
                self.position = {
                    'side': 'long',
                    'entry_price': current_price,
                    'quantity': quantity,
                    'take_profit': current_price * (1 + self.take_profit_pct),
                    'stop_loss': current_price * (1 - self.stop_loss_pct)
                }
                
                logger.info(f"[COMPRA] {quantity:.4f} {self.symbol} @ ${current_price:.2f}")
                
            elif signal == -1:  # Señal de venta
                position_size = self.balance * self.max_position_size
                quantity = position_size / current_price
                
                self.position = {
                    'side': 'short',
                    'entry_price': current_price,
                    'quantity': quantity,
                    'take_profit': current_price * (1 - self.take_profit_pct),
                    'stop_loss': current_price * (1 + self.stop_loss_pct)
                }
                
                logger.info(f"[VENTA] {quantity:.4f} {self.symbol} @ ${current_price:.2f}")
        
        # Si hay posición abierta, verificar si debemos cerrarla
        elif self.position:
            profit = None
            close_position = False
            
            if self.position['side'] == 'long':
                profit = (current_price - self.position['entry_price']) * self.position['quantity']
                # Cerrar si llegamos al take profit o stop loss
                if (current_price >= self.position['take_profit'] or 
                    current_price <= self.position['stop_loss'] or
                    signal == -1):  # También cerrar si hay señal contraria
                    close_position = True
                    
            elif self.position['side'] == 'short':
                profit = (self.position['entry_price'] - current_price) * self.position['quantity']
                # Cerrar si llegamos al take profit o stop loss
                if (current_price <= self.position['take_profit'] or
                    current_price >= self.position['stop_loss'] or
                    signal == 1):  # También cerrar si hay señal contraria
                    close_position = True
            
            if close_position:
                self.balance += profit
                self.trades.append({
                    'entry_price': self.position['entry_price'],
                    'exit_price': current_price,
                    'quantity': self.position['quantity'],
                    'side': self.position['side'],
                    'profit': profit,
                    'timestamp': datetime.now().isoformat()
                })
                
                logger.info(f"[CIERRE] {self.position['quantity']:.4f} {self.symbol} @ ${current_price:.2f} | " +
                          f"{'Ganancia' if profit > 0 else 'Pérdida'}: ${profit:.2f}")
                
                self.position = None
                
                # Guarda el historial de trades
                with open(f"{self.symbol}_trading_log.json", "w") as f:
                    json.dump({"trades": self.trades}, f, indent=2)

    def analyze_performance(self):
        """Analiza el rendimiento del trading"""
        if not self.trades:
            logger.info("No hay trades para analizar")
            return
            
        total_profit = sum(trade['profit'] for trade in self.trades)
        win_trades = sum(1 for trade in self.trades if trade['profit'] > 0)
        loss_trades = sum(1 for trade in self.trades if trade['profit'] < 0)
        
        logger.info(f"=== Análisis de Rendimiento ===")
        logger.info(f"Balance inicial: ${self.initial_balance:.2f}")
        logger.info(f"Balance final: ${self.balance:.2f}")
        logger.info(f"Ganancia total: ${total_profit:.2f}")
        logger.info(f"Trades ganadores: {win_trades}")
        logger.info(f"Trades perdedores: {loss_trades}")
        if self.trades:
            win_rate = (win_trades / len(self.trades)) * 100
            logger.info(f"Win rate: {win_rate:.1f}%")

class LearningTradingBot:
    """Bot principal con capacidades de aprendizaje"""
    
    def __init__(self):
        self.engine = PaperTradingEngine()
        self.ws_client = None
        self.running = False
        self.data_queue = asyncio.Queue()
        
    async def connect_to_market(self):
        """Conecta a datos de mercado en tiempo real"""
        self.ws_client = BinanceWebSocketClient(self.data_queue)
        return await self.ws_client.connect()
            
    async def run_learning_mode(self):
        """Ejecuta el bot en modo aprendizaje"""
        logger.info("[BOT] Iniciando modo de aprendizaje automático")
        logger.info("[TRADING] Paper Trading activado - Sin riesgo real")
        
        if not await self.connect_to_market():
            return
        
        # Suscribirse a los canales necesarios
        await self.ws_client.subscribe([])
        
        self.running = True
        last_candle_time = None
        
        # Iniciar recepción de mensajes en segundo plano
        receiver_task = asyncio.create_task(self.ws_client.receive_messages())
        
        try:
            while self.running:
                try:
                    data = await self.data_queue.get()
                    
                    if data['type'] == 'kline':
                        candle_data = data['data'][0]
                        
                        # Evitar procesar la misma vela múltiples veces
                        if candle_data['timestamp'] != last_candle_time:
                            self.engine.market_data.append(candle_data)
                            
                            # Mantener solo las últimas 100 velas
                            if len(self.engine.market_data) > 100:
                                self.engine.market_data = self.engine.market_data[-100:]
                            
                            # Analizar mercado y ejecutar operaciones
                            analysis = self.engine.analyze_market(candle_data)
                            if analysis and analysis['signal']:
                                self.engine.execute_trade(analysis)
                            
                            last_candle_time = candle_data['timestamp']
                            
                            # Log de actividad cada 5 velas
                            if len(self.engine.market_data) % 5 == 0:
                                logger.info(f"[PRECIO] {self.engine.symbol}: ${candle_data['close']:.4f} | "
                                          f"Datos: {len(self.engine.market_data)} velas | "
                                          f"Balance: ${self.engine.balance:.2f}")
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error en bucle principal: {e}")
                    await asyncio.sleep(5)
        finally:
            receiver_task.cancel()
            await self.shutdown()
    
    async def shutdown(self):
        """Cierra el bot limpiamente"""
        self.running = False
        if self.ws_client and self.ws_client.ws:
            await self.ws_client.ws.close()
        self.engine.analyze_performance()

async def main():
    """Función principal"""
    bot = LearningTradingBot()
    try:
        await bot.run_learning_mode()
    except KeyboardInterrupt:
        logger.info("Deteniendo bot por solicitud del usuario...")
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass