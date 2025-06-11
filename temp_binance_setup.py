#!/usr/bin/env python3
"""
Configuración temporal con API Key proporcionada
"""

# Credenciales proporcionadas
API_KEY = "ampzPA2IWP1EA5NVJAdruAyPbitxs1kqc6tOkTWf9fu27LOkGVOD2A5PhMF62zX3"
API_SECRET = "wbazWkMzHznABGONO1dD5i0qFZEUGRO8vhv1xebktqYmaHjkLZvodsRjgZZYDhCi"

def setup_with_secret(api_secret):
    """Configura sistema completo cuando se proporcione el secret"""
    
    import json
    import os
    from datetime import datetime
    
    print("Configurando sistema Binance...")
    
    # Crear configuración completa
    config = {
        "api_key": API_KEY,
        "api_secret": api_secret,
        "base_url": "https://api.binance.com",
        "testnet_url": "https://testnet.binance.vision",
        "use_testnet": False,  # Usar real por defecto
        "symbol": "SOLUSDT",
        "position_size": 0.05,
        "setup_time": datetime.now().isoformat(),
        "configured": True
    }
    
    # Guardar configuración
    with open('binance_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    # Crear archivo .env
    env_content = f"""BINANCE_API_KEY={API_KEY}
BINANCE_API_SECRET={api_secret}
SYMBOL=SOLUSDT
USE_TESTNET=false
POSITION_SIZE=0.05
"""
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print(f"Configuración completada:")
    print(f"API Key: ***{API_KEY[-8:]}")
    print(f"API Secret: ***{api_secret[-8:]}")
    print(f"Símbolo: SOLUSDT")
    print(f"Archivos creados: binance_config.json, .env")
    
    return test_binance_connection(config)

def test_binance_connection(config):
    """Prueba conexión con Binance"""
    import requests
    import hmac
    import hashlib
    import time
    
    try:
        base_url = config['base_url']
        
        # Test ping básico
        response = requests.get(f"{base_url}/api/v3/ping", timeout=5)
        if response.status_code != 200:
            print("Error: No se puede conectar con Binance")
            return False
        
        print("Conexión básica exitosa")
        
        # Test autenticado
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}"
        
        signature = hmac.new(
            config['api_secret'].encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'X-MBX-APIKEY': config['api_key'],
            'Content-Type': 'application/json'
        }
        
        params = {
            'timestamp': timestamp,
            'signature': signature
        }
        
        response = requests.get(f"{base_url}/api/v3/account", 
                              headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            account_data = response.json()
            print("Autenticación exitosa")
            print(f"Puede tradear: {account_data.get('canTrade', False)}")
            
            # Mostrar balance USDT
            balances = account_data.get('balances', [])
            usdt_balance = next((b for b in balances if b['asset'] == 'USDT'), None)
            if usdt_balance:
                free_usdt = float(usdt_balance['free'])
                print(f"Balance USDT: ${free_usdt:.2f}")
            
            return True
        else:
            print(f"Error de autenticación: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"Error en prueba de conexión: {e}")
        return False

def create_simple_trader():
    """Crea trader simplificado"""
    
    trader_code = f'''#!/usr/bin/env python3
"""
Trader Binance configurado automáticamente
API Key: ***{API_KEY[-8:]}
"""

import json
import requests
import hmac
import hashlib
import time
import pandas as pd
from datetime import datetime

# Cargar configuración
try:
    with open('binance_config.json', 'r') as f:
        CONFIG = json.load(f)
    print("Configuración cargada exitosamente")
except:
    print("Error: No se encontró binance_config.json")
    print("Ejecuta temp_binance_setup.py primero")
    exit(1)

class SimpleBinanceTrader:
    def __init__(self):
        self.api_key = CONFIG['api_key']
        self.api_secret = CONFIG['api_secret']
        self.base_url = CONFIG['base_url']
        self.symbol = CONFIG['symbol']
        
    def get_price(self):
        """Obtiene precio actual de SOLUSDT"""
        try:
            response = requests.get(f"{{self.base_url}}/api/v3/ticker/price",
                                  params={{'symbol': self.symbol}}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                price = float(data['price'])
                print(f"Precio {{self.symbol}}: ${{price:.4f}}")
                return price
            return None
        except Exception as e:
            print(f"Error obteniendo precio: {{e}}")
            return None
    
    def get_account(self):
        """Obtiene información de cuenta"""
        try:
            timestamp = int(time.time() * 1000)
            query_string = f"timestamp={{timestamp}}"
            
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {{'X-MBX-APIKEY': self.api_key}}
            params = {{'timestamp': timestamp, 'signature': signature}}
            
            response = requests.get(f"{{self.base_url}}/api/v3/account",
                                  headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                account = response.json()
                print(f"Cuenta activa - Puede tradear: {{account.get('canTrade', False)}}")
                
                # Mostrar balances principales
                balances = account.get('balances', [])
                for balance in balances:
                    if float(balance['free']) > 0.001:
                        asset = balance['asset']
                        free = float(balance['free'])
                        print(f"  {{asset}}: {{free:.6f}}")
                
                return account
            else:
                print(f"Error de cuenta: {{response.status_code}}")
                return None
        except Exception as e:
            print(f"Error obteniendo cuenta: {{e}}")
            return None
    
    def download_data(self):
        """Descarga datos históricos"""
        try:
            response = requests.get(f"{{self.base_url}}/api/v3/klines",
                                  params={{
                                      'symbol': self.symbol,
                                      'interval': '1m',
                                      'limit': 100
                                  }}, timeout=10)
            
            if response.status_code == 200:
                klines = response.json()
                df = pd.DataFrame(klines, columns=[
                    'open_time', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'buy_volume', 'buy_quote_volume', 'ignore'
                ])
                
                df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col])
                
                # Guardar datos
                filename = f"{{self.symbol}}_data.csv"
                df.to_csv(filename, index=False)
                
                print(f"Datos descargados: {{len(df)}} velas")
                print(f"Archivo: {{filename}}")
                print(f"Último precio: ${{df['close'].iloc[-1]:.4f}}")
                
                return df
            return None
        except Exception as e:
            print(f"Error descargando datos: {{e}}")
            return None
    
    def run_status_check(self):
        """Ejecuta verificación de estado completa"""
        print("=== VERIFICACIÓN SISTEMA BINANCE ===")
        print(f"Símbolo: {{self.symbol}}")
        print(f"API Key: ***{{self.api_key[-8:]}}")
        
        # 1. Precio actual
        price = self.get_price()
        
        # 2. Estado de cuenta
        account = self.get_account()
        
        # 3. Descargar datos
        data = self.download_data()
        
        if price and account and data is not None:
            print("\\n✓ Sistema funcionando correctamente")
            print("✓ Conexión con Binance establecida")
            print("✓ Credenciales válidas")
            print("✓ Datos descargados exitosamente")
            return True
        else:
            print("\\n✗ Sistema con problemas")
            return False

if __name__ == "__main__":
    trader = SimpleBinanceTrader()
    trader.run_status_check()
'''
    
    with open('simple_binance_trader.py', 'w') as f:
        f.write(trader_code)
    
    print("Trader simplificado creado: simple_binance_trader.py")

if __name__ == "__main__":
    print("=== CONFIGURACIÓN TEMPORAL BINANCE ===")
    print(f"API Key configurada: ***{API_KEY[-8:]}")
    print("Esperando API Secret para completar configuración...")
    
    create_simple_trader()
    
    print("\nIntroduce tu API Secret para completar:")
    api_secret = input("API Secret: ").strip()
    
    if api_secret:
        setup_with_secret(api_secret)
    else:
        print("API Secret requerido para continuar")