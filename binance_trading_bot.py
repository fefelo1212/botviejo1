#!/usr/bin/env python3
"""
Bot de trading que usa datos procesados de Binance
Separado completamente de la descarga y procesamiento
"""

import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd

class BinanceTradingBot:
    """
    Bot de trading que consume datos ya procesados de Binance
    No descarga datos - solo lee archivos procesados
    """
    
    def __init__(self, processed_folder: str = "processed_data"):
        self.processed_folder = processed_folder
        self.symbol = "SOLUSDT"
        self.interval = "1m"
        self.balance = 10000.0  # Balance virtual para paper trading
        self.position = None
        self.trades_log = []
        self.running = False
        
        print("Bot de trading Binance inicializado")
        print(f"Balance inicial: ${self.balance:.2f}")
        print(f"Símbolo: {self.symbol}")
        print(f"Intervalo: {self.interval}")
    
    def load_processed_analysis(self) -> Optional[Dict]:
        """Carga el análisis técnico procesado más reciente"""
        try:
            filename = f"{self.processed_folder}/{self.symbol}_{self.interval}_analysis.json"
            
            if not os.path.exists(filename):
                print(f"Archivo de análisis no encontrado: {filename}")
                return None
            
            # Verificar que el archivo sea reciente (menos de 10 minutos)
            file_time = os.path.getmtime(filename)
            current_time = time.time()
            age_minutes = (current_time - file_time) / 60
            
            if age_minutes > 10:
                print(f"Archivo de análisis muy antiguo: {age_minutes:.1f} minutos")
                return None
            
            with open(filename, 'r') as f:
                analysis = json.load(f)
            
            print(f"Análisis cargado exitosamente (edad: {age_minutes:.1f} min)")
            return analysis
            
        except Exception as e:
            print(f"Error cargando análisis: {e}")
            return None
    
    def get_current_price(self, analysis: Dict) -> float:
        """Extrae precio actual del análisis"""
        try:
            if analysis['current_price'] and analysis['current_price']['price']:
                return float(analysis['current_price']['price'])
            elif analysis['latest_candle']['close']:
                return float(analysis['latest_candle']['close'])
            else:
                print("No se pudo obtener precio actual")
                return None
        except Exception as e:
            print(f"Error obteniendo precio: {e}")
            return None
    
    def analyze_signals(self, analysis: Dict) -> Dict:
        """Analiza las señales de trading del análisis procesado"""
        try:
            signals = analysis['signals']
            indicators = analysis['indicators']
            
            # Señal principal del procesador
            main_signal = signals['current_signal']
            signal_reason = signals['signal_reason']
            
            # Análisis adicional de confirmación
            confirmations = 0
            total_checks = 0
            
            # Confirmar con RSI
            rsi = indicators.get('rsi')
            if rsi:
                total_checks += 1
                if main_signal == 1 and rsi < 70:  # Compra y RSI no sobrecomprado
                    confirmations += 1
                elif main_signal == -1 and rsi > 30:  # Venta y RSI no sobrevendido
                    confirmations += 1
                elif main_signal == 0:  # Sin señal principal
                    confirmations += 1
            
            # Confirmar con MACD
            macd = indicators.get('macd')
            macd_signal = indicators.get('macd_signal')
            if macd and macd_signal:
                total_checks += 1
                if main_signal == 1 and macd > macd_signal:  # Compra y MACD bullish
                    confirmations += 1
                elif main_signal == -1 and macd < macd_signal:  # Venta y MACD bearish
                    confirmations += 1
                elif main_signal == 0:
                    confirmations += 1
            
            # Confirmar con tendencia SMA
            sma_5 = indicators.get('sma_5')
            sma_20 = indicators.get('sma_20')
            if sma_5 and sma_20:
                total_checks += 1
                if main_signal == 1 and sma_5 > sma_20:  # Compra y tendencia alcista
                    confirmations += 1
                elif main_signal == -1 and sma_5 < sma_20:  # Venta y tendencia bajista
                    confirmations += 1
                elif main_signal == 0:
                    confirmations += 1
            
            # Calcular confianza
            confidence = confirmations / total_checks if total_checks > 0 else 0
            
            signal_analysis = {
                "signal": main_signal,
                "reason": signal_reason,
                "confidence": confidence,
                "confirmations": confirmations,
                "total_checks": total_checks,
                "rsi": rsi,
                "macd_bullish": macd > macd_signal if macd and macd_signal else None,
                "trend_up": sma_5 > sma_20 if sma_5 and sma_20 else None
            }
            
            return signal_analysis
            
        except Exception as e:
            print(f"Error analizando señales: {e}")
            return {"signal": 0, "confidence": 0, "reason": "ERROR"}
    
    def can_open_position(self, signal_type: str, price: float) -> bool:
        """Verifica si se puede abrir una posición"""
        # No abrir si ya hay posición abierta
        if self.position:
            return False
        
        # Verificar balance mínimo
        min_balance = 100.0
        if self.balance < min_balance:
            print(f"Balance insuficiente: ${self.balance:.2f} < ${min_balance:.2f}")
            return False
        
        # Verificar precio válido
        if not price or price <= 0:
            print("Precio inválido")
            return False
        
        return True
    
    def calculate_position_size(self, price: float) -> float:
        """Calcula tamaño de posición (10% del balance)"""
        position_percent = 0.10  # 10% del balance
        position_value = self.balance * position_percent
        quantity = position_value / price
        return round(quantity, 6)
    
    def open_position(self, signal_type: str, price: float, reason: str, confidence: float):
        """Abre una nueva posición"""
        try:
            if not self.can_open_position(signal_type, price):
                return False
            
            quantity = self.calculate_position_size(price)
            
            self.position = {
                "type": signal_type,
                "entry_price": price,
                "quantity": quantity,
                "entry_time": datetime.now(),
                "reason": reason,
                "confidence": confidence,
                "stop_loss": price * 0.99 if signal_type == "BUY" else price * 1.01,
                "take_profit": price * 1.01 if signal_type == "BUY" else price * 0.99
            }
            
            print(f"\n🔴 POSICIÓN ABIERTA:")
            print(f"Tipo: {signal_type}")
            print(f"Precio entrada: ${price:.4f}")
            print(f"Cantidad: {quantity:.6f} SOL")
            print(f"Valor: ${quantity * price:.2f}")
            print(f"Razón: {reason}")
            print(f"Confianza: {confidence*100:.1f}%")
            print(f"Stop Loss: ${self.position['stop_loss']:.4f}")
            print(f"Take Profit: ${self.position['take_profit']:.4f}")
            
            return True
            
        except Exception as e:
            print(f"Error abriendo posición: {e}")
            return False
    
    def check_exit_conditions(self, current_price: float) -> Optional[str]:
        """Verifica condiciones de salida"""
        if not self.position:
            return None
        
        pos_type = self.position["type"]
        stop_loss = self.position["stop_loss"]
        take_profit = self.position["take_profit"]
        
        # Verificar Stop Loss
        if pos_type == "BUY" and current_price <= stop_loss:
            return "STOP_LOSS"
        elif pos_type == "SELL" and current_price >= stop_loss:
            return "STOP_LOSS"
        
        # Verificar Take Profit
        if pos_type == "BUY" and current_price >= take_profit:
            return "TAKE_PROFIT"
        elif pos_type == "SELL" and current_price <= take_profit:
            return "TAKE_PROFIT"
        
        # Verificar tiempo máximo (30 minutos)
        position_age = datetime.now() - self.position["entry_time"]
        if position_age > timedelta(minutes=30):
            return "TIME_LIMIT"
        
        return None
    
    def close_position(self, exit_price: float, exit_reason: str):
        """Cierra la posición actual"""
        try:
            if not self.position:
                return
            
            entry_price = self.position["entry_price"]
            quantity = self.position["quantity"]
            pos_type = self.position["type"]
            
            # Calcular P&L
            if pos_type == "BUY":
                pnl = (exit_price - entry_price) * quantity
            else:  # SELL
                pnl = (entry_price - exit_price) * quantity
            
            pnl_percent = (pnl / (entry_price * quantity)) * 100
            
            # Actualizar balance
            self.balance += pnl
            
            # Registrar trade
            trade_record = {
                "entry_time": self.position["entry_time"].isoformat(),
                "exit_time": datetime.now().isoformat(),
                "type": pos_type,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": quantity,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "exit_reason": exit_reason,
                "entry_reason": self.position["reason"],
                "confidence": self.position["confidence"]
            }
            
            self.trades_log.append(trade_record)
            
            print(f"\n🔴 POSICIÓN CERRADA:")
            print(f"Tipo: {pos_type}")
            print(f"Entrada: ${entry_price:.4f} -> Salida: ${exit_price:.4f}")
            print(f"P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)")
            print(f"Razón salida: {exit_reason}")
            print(f"Balance: ${self.balance:.2f}")
            
            # Limpiar posición
            self.position = None
            
            # Guardar log de trades
            self.save_trades_log()
            
        except Exception as e:
            print(f"Error cerrando posición: {e}")
    
    def save_trades_log(self):
        """Guarda log de trades en archivo"""
        try:
            filename = f"trades_log_{self.symbol}.json"
            
            log_data = {
                "symbol": self.symbol,
                "start_balance": 10000.0,
                "current_balance": self.balance,
                "total_trades": len(self.trades_log),
                "trades": self.trades_log,
                "performance": self.calculate_performance()
            }
            
            with open(filename, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            print(f"Log de trades guardado: {filename}")
            
        except Exception as e:
            print(f"Error guardando log: {e}")
    
    def calculate_performance(self) -> Dict:
        """Calcula métricas de rendimiento"""
        if not self.trades_log:
            return {}
        
        total_trades = len(self.trades_log)
        winning_trades = len([t for t in self.trades_log if t['pnl'] > 0])
        losing_trades = total_trades - winning_trades
        
        total_pnl = sum([t['pnl'] for t in self.trades_log])
        total_return = ((self.balance - 10000.0) / 10000.0) * 100
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        avg_win = sum([t['pnl'] for t in self.trades_log if t['pnl'] > 0]) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum([t['pnl'] for t in self.trades_log if t['pnl'] < 0]) / losing_trades if losing_trades > 0 else 0
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_return": total_return,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss
        }
    
    def print_status(self):
        """Imprime estado actual del bot"""
        print(f"\n=== STATUS BOT ===")
        print(f"Balance: ${self.balance:.2f}")
        print(f"Posición: {'Abierta' if self.position else 'Cerrada'}")
        
        if self.position:
            pos = self.position
            current_time = datetime.now()
            duration = current_time - pos["entry_time"]
            print(f"  Tipo: {pos['type']}")
            print(f"  Precio entrada: ${pos['entry_price']:.4f}")
            print(f"  Duración: {duration.seconds // 60} min")
        
        performance = self.calculate_performance()
        if performance:
            print(f"Trades totales: {performance['total_trades']}")
            print(f"Tasa éxito: {performance['win_rate']:.1f}%")
            print(f"Retorno: {performance['total_return']:+.2f}%")
    
    def run_single_cycle(self):
        """Ejecuta un ciclo único de trading"""
        try:
            print(f"\n--- CICLO TRADING {datetime.now().strftime('%H:%M:%S')} ---")
            
            # 1. Cargar análisis procesado
            analysis = self.load_processed_analysis()
            if not analysis:
                print("No hay análisis disponible - salteando ciclo")
                return
            
            # 2. Obtener precio actual
            current_price = self.get_current_price(analysis)
            if not current_price:
                print("No se pudo obtener precio actual")
                return
            
            print(f"Precio actual: ${current_price:.4f}")
            
            # 3. Verificar condiciones de salida si hay posición
            if self.position:
                exit_reason = self.check_exit_conditions(current_price)
                if exit_reason:
                    self.close_position(current_price, exit_reason)
                    return
            
            # 4. Analizar señales si no hay posición
            if not self.position:
                signal_analysis = self.analyze_signals(analysis)
                
                signal = signal_analysis['signal']
                confidence = signal_analysis['confidence']
                reason = signal_analysis['reason']
                
                print(f"Señal: {signal} (confianza: {confidence*100:.1f}%)")
                print(f"Razón: {reason}")
                
                # 5. Ejecutar operación si hay señal fuerte
                min_confidence = 0.6  # 60% confianza mínima
                
                if abs(signal) == 1 and confidence >= min_confidence:
                    signal_type = "BUY" if signal == 1 else "SELL"
                    self.open_position(signal_type, current_price, reason, confidence)
                else:
                    print("Señal insuficiente para operar")
            
            # 6. Mostrar estado
            self.print_status()
            
        except Exception as e:
            print(f"Error en ciclo de trading: {e}")
    
    def run_continuous(self, cycles: int = 100):
        """Ejecuta el bot de forma continua"""
        print(f"\n=== INICIANDO BOT TRADING CONTINUO ===")
        print(f"Ciclos máximos: {cycles}")
        print(f"Intervalo: 60 segundos")
        
        self.running = True
        cycle_count = 0
        
        try:
            while self.running and cycle_count < cycles:
                cycle_count += 1
                print(f"\n{'='*50}")
                print(f"CICLO {cycle_count}/{cycles}")
                
                self.run_single_cycle()
                
                if cycle_count < cycles:
                    print(f"Esperando 60 segundos...")
                    time.sleep(60)  # Esperar 1 minuto
                
        except KeyboardInterrupt:
            print("\nBot detenido por usuario")
        except Exception as e:
            print(f"Error en ejecución continua: {e}")
        finally:
            self.running = False
            print(f"\n=== BOT DETENIDO ===")
            self.print_status()

def main():
    """Función principal"""
    print("=== BOT TRADING BINANCE ===")
    print("Bot que consume datos procesados independientes")
    
    # Crear instancia del bot
    bot = BinanceTradingBot()
    
    # Ejecutar un ciclo de prueba
    print("\n1. Ejecutando ciclo de prueba...")
    bot.run_single_cycle()
    
    # Preguntar si ejecutar modo continuo
    print(f"\n¿Ejecutar en modo continuo? (y/n): ", end="")
    response = input().lower()
    
    if response == 'y':
        print("Ejecutando bot en modo continuo...")
        print("Presiona Ctrl+C para detener")
        bot.run_continuous(cycles=50)  # 50 ciclos = ~50 minutos
    else:
        print("Modo de prueba completado")

if __name__ == "__main__":
    main()