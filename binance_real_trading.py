#!/usr/bin/env python3
"""
Bot de trading real con Binance usando credenciales API
Módulo para operaciones reales con gestión de riesgo
"""

import requests
import hmac
import hashlib
import time
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List
from binance_config import config

class BinanceRealTrader:
    """
    Trader real de Binance con credenciales API
    Ejecuta operaciones reales con gestión de riesgo
    """
    
    def __init__(self):
        self.config = config
        self.base_url = self.config.get_api_url()
        self.session = requests.Session()
        
        # Configuración de trading
        self.symbol = "SOLUSDT"
        self.min_quantity = 0.01
        self.max_position_size = 0.1  # 10% del balance
        
        print(f"Trader inicializado para {self.symbol}")
        print(f"URL: {self.base_url}")
        print(f"Testnet: {self.config.use_testnet}")
    
    def _get_timestamp(self) -> int:
        """Obtiene timestamp actual para requests"""
        return int(time.time() * 1000)
    
    def _create_signature(self, params: str) -> str:
        """Crea signature para requests autenticados"""
        timestamp = self._get_timestamp()
        query_string = f"{params}&timestamp={timestamp}"
        
        signature = hmac.new(
            self.config.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp
    
    def _make_authenticated_request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Optional[Dict]:
        """Realiza request autenticado a Binance"""
        try:
            if not self.config.is_configured():
                print("Error: Credenciales no configuradas")
                return None
            
            if params is None:
                params = {}
            
            # Crear query string
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            
            # Crear signature
            signature, timestamp = self._create_signature(query_string)
            
            # Agregar timestamp y signature
            params['timestamp'] = timestamp
            params['signature'] = signature
            
            # Headers
            headers = self.config.get_headers()
            
            # URL completa
            url = f"{self.base_url}{endpoint}"
            
            # Realizar request
            if method == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            elif method == "POST":
                response = self.session.post(url, params=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"Método no soportado: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error en request: {e}")
            return None
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Prueba conexión con API de Binance"""
        try:
            # Test sin autenticación
            response = self.session.get(f"{self.base_url}/api/v3/ping", timeout=5)
            if response.status_code != 200:
                print("Error en ping básico")
                return False
            
            # Test con autenticación
            account_info = self.get_account_info()
            if account_info:
                print("✓ Conexión autenticada exitosa")
                return True
            else:
                print("✗ Error en autenticación")
                return False
                
        except Exception as e:
            print(f"Error probando conexión: {e}")
            return False
    
    def get_account_info(self) -> Optional[Dict]:
        """Obtiene información de la cuenta"""
        try:
            result = self._make_authenticated_request("/api/v3/account")
            
            if result:
                # Procesar información de balances
                balances = {}
                for balance in result.get('balances', []):
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    
                    if total > 0:
                        balances[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': total
                        }
                
                account_summary = {
                    'can_trade': result.get('canTrade', False),
                    'can_withdraw': result.get('canWithdraw', False),
                    'can_deposit': result.get('canDeposit', False),
                    'balances': balances,
                    'update_time': datetime.fromtimestamp(result.get('updateTime', 0) / 1000).isoformat()
                }
                
                print("Información de cuenta obtenida:")
                print(f"  Puede tradear: {account_summary['can_trade']}")
                print(f"  Balances principales:")
                for asset, balance in list(balances.items())[:5]:  # Solo primeros 5
                    if balance['total'] > 0.001:  # Solo balances significativos
                        print(f"    {asset}: {balance['total']:.6f}")
                
                return account_summary
            else:
                print("No se pudo obtener información de cuenta")
                return None
                
        except Exception as e:
            print(f"Error obteniendo info de cuenta: {e}")
            return None
    
    def get_symbol_info(self, symbol: str = None) -> Optional[Dict]:
        """Obtiene información del símbolo de trading"""
        try:
            if symbol is None:
                symbol = self.symbol
            
            # Obtener info del exchange
            response = self.session.get(f"{self.base_url}/api/v3/exchangeInfo", timeout=10)
            response.raise_for_status()
            exchange_info = response.json()
            
            # Buscar símbolo específico
            for sym in exchange_info.get('symbols', []):
                if sym['symbol'] == symbol:
                    symbol_info = {
                        'symbol': sym['symbol'],
                        'status': sym['status'],
                        'base_asset': sym['baseAsset'],
                        'quote_asset': sym['quoteAsset'],
                        'min_quantity': None,
                        'step_size': None,
                        'min_notional': None
                    }
                    
                    # Extraer filtros importantes
                    for filter_item in sym.get('filters', []):
                        if filter_item['filterType'] == 'LOT_SIZE':
                            symbol_info['min_quantity'] = float(filter_item['minQty'])
                            symbol_info['step_size'] = float(filter_item['stepSize'])
                        elif filter_item['filterType'] == 'MIN_NOTIONAL':
                            symbol_info['min_notional'] = float(filter_item['minNotional'])
                    
                    print(f"Información de {symbol}:")
                    print(f"  Estado: {symbol_info['status']}")
                    print(f"  Cantidad mínima: {symbol_info['min_quantity']}")
                    print(f"  Notional mínimo: {symbol_info['min_notional']}")
                    
                    return symbol_info
            
            print(f"Símbolo {symbol} no encontrado")
            return None
            
        except Exception as e:
            print(f"Error obteniendo info del símbolo: {e}")
            return None
    
    def get_current_price(self, symbol: str = None) -> Optional[float]:
        """Obtiene precio actual del símbolo"""
        try:
            if symbol is None:
                symbol = self.symbol
            
            response = self.session.get(
                f"{self.base_url}/api/v3/ticker/price",
                params={"symbol": symbol},
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            price = float(data['price'])
            print(f"Precio actual {symbol}: ${price:.4f}")
            return price
            
        except Exception as e:
            print(f"Error obteniendo precio: {e}")
            return None
    
    def calculate_quantity(self, price: float, percentage: float = 0.05) -> float:
        """Calcula cantidad a tradear basada en porcentaje del balance"""
        try:
            account = self.get_account_info()
            if not account:
                return self.min_quantity
            
            # Obtener balance USDT
            usdt_balance = account['balances'].get('USDT', {}).get('free', 0)
            
            if usdt_balance < 10:  # Mínimo $10
                print(f"Balance USDT insuficiente: ${usdt_balance:.2f}")
                return 0
            
            # Calcular cantidad basada en porcentaje
            position_value = usdt_balance * percentage
            quantity = position_value / price
            
            # Redondear a step size apropiado
            symbol_info = self.get_symbol_info()
            if symbol_info and symbol_info['step_size']:
                step_size = symbol_info['step_size']
                quantity = round(quantity / step_size) * step_size
            
            # Verificar mínimos
            min_qty = symbol_info.get('min_quantity', self.min_quantity) if symbol_info else self.min_quantity
            quantity = max(quantity, min_qty)
            
            print(f"Cantidad calculada: {quantity:.6f} (${quantity * price:.2f})")
            return quantity
            
        except Exception as e:
            print(f"Error calculando cantidad: {e}")
            return self.min_quantity
    
    def place_order(self, side: str, quantity: float, order_type: str = "MARKET") -> Optional[Dict]:
        """Coloca una orden en Binance"""
        try:
            if not self.config.is_configured():
                print("Error: Credenciales no configuradas")
                return None
            
            # Verificar parámetros
            if side not in ["BUY", "SELL"]:
                print(f"Side inválido: {side}")
                return None
            
            if quantity <= 0:
                print(f"Cantidad inválida: {quantity}")
                return None
            
            # Parámetros de la orden
            params = {
                'symbol': self.symbol,
                'side': side,
                'type': order_type,
                'quantity': f"{quantity:.6f}"
            }
            
            print(f"Colocando orden {side} {quantity:.6f} {self.symbol}")
            
            # Ejecutar orden
            result = self._make_authenticated_request("/api/v3/order", params, method="POST")
            
            if result:
                order_info = {
                    'orderId': result.get('orderId'),
                    'symbol': result.get('symbol'),
                    'side': result.get('side'),
                    'type': result.get('type'),
                    'quantity': result.get('origQty'),
                    'price': result.get('price'),
                    'status': result.get('status'),
                    'time': datetime.fromtimestamp(result.get('transactTime', 0) / 1000).isoformat()
                }
                
                print(f"✓ Orden ejecutada:")
                print(f"  ID: {order_info['orderId']}")
                print(f"  Estado: {order_info['status']}")
                print(f"  Cantidad: {order_info['quantity']}")
                
                return order_info
            else:
                print("✗ Error ejecutando orden")
                return None
                
        except Exception as e:
            print(f"Error colocando orden: {e}")
            return None
    
    def get_open_orders(self) -> List[Dict]:
        """Obtiene órdenes abiertas"""
        try:
            result = self._make_authenticated_request("/api/v3/openOrders", {'symbol': self.symbol})
            
            if result:
                print(f"Órdenes abiertas: {len(result)}")
                return result
            else:
                return []
                
        except Exception as e:
            print(f"Error obteniendo órdenes abiertas: {e}")
            return []
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancela una orden específica"""
        try:
            params = {
                'symbol': self.symbol,
                'orderId': order_id
            }
            
            result = self._make_authenticated_request("/api/v3/order", params, method="DELETE")
            
            if result:
                print(f"✓ Orden {order_id} cancelada")
                return True
            else:
                print(f"✗ Error cancelando orden {order_id}")
                return False
                
        except Exception as e:
            print(f"Error cancelando orden: {e}")
            return False

def setup_and_test():
    """Configuración inicial y pruebas"""
    print("=== SETUP BINANCE REAL TRADING ===")
    
    # Verificar configuración
    if not config.is_configured():
        print("Introduce tus credenciales de Binance:")
        api_key = input("API Key: ").strip()
        api_secret = input("API Secret: ").strip()
        
        if api_key and api_secret:
            config.set_credentials(api_key, api_secret)
        else:
            print("Credenciales inválidas")
            return False
    
    # Crear trader
    trader = BinanceRealTrader()
    
    # Probar conexión
    if trader.test_connection():
        print("✓ Sistema configurado correctamente")
        
        # Mostrar información básica
        trader.get_symbol_info()
        trader.get_current_price()
        
        return True
    else:
        print("✗ Error en configuración")
        return False

if __name__ == "__main__":
    setup_and_test()