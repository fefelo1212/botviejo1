#!/usr/bin/env python3
"""
Configurador automático del sistema de trading Binance
Configura credenciales y prepara todo el sistema
"""

import os
import json
import requests
import hmac
import hashlib
import time
from datetime import datetime

def configure_credentials(api_key: str, api_secret: str):
    """Configura credenciales y valida conexión"""
    print("Configurando credenciales de Binance...")
    
    # Validar formato básico
    if not api_key or not api_secret or len(api_key) < 20 or len(api_secret) < 20:
        print("Error: Credenciales inválidas")
        return False
    
    # Crear configuración
    config = {
        "api_key": api_key,
        "api_secret": api_secret,
        "base_url": "https://api.binance.com",
        "testnet_url": "https://testnet.binance.vision",
        "use_testnet": True,  # Iniciar en testnet por seguridad
        "symbol": "SOLUSDT",
        "position_size": 0.05,  # 5% del balance
        "setup_time": datetime.now().isoformat()
    }
    
    # Guardar configuración
    with open('binance_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    # Crear archivo .env
    env_content = f"""BINANCE_API_KEY={api_key}
BINANCE_API_SECRET={api_secret}
SYMBOL=SOLUSDT
USE_TESTNET=true
POSITION_SIZE=0.05
"""
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print(f"Credenciales configuradas: ***{api_key[-8:]}")
    return test_connection(config)

def test_connection(config):
    """Prueba conexión con Binance usando las credenciales"""
    try:
        base_url = config['testnet_url'] if config['use_testnet'] else config['base_url']
        
        # Test básico sin autenticación
        response = requests.get(f"{base_url}/api/v3/ping", timeout=5)
        if response.status_code != 200:
            print("Error: No se puede conectar con Binance")
            return False
        
        # Test con autenticación
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
        
        response = requests.get(f"{base_url}/api/v3/account", headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            account_data = response.json()
            print("Conexión exitosa con Binance")
            print(f"Puede tradear: {account_data.get('canTrade', False)}")
            
            # Mostrar algunos balances
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
        print(f"Error probando conexión: {e}")
        return False

def create_trading_scripts():
    """Crea scripts optimizados para trading con las credenciales configuradas"""
    
    # Script principal de trading
    trading_script = '''#!/usr/bin/env python3
"""
Bot de trading Binance configurado automáticamente
"""

import json
import requests
import hmac
import hashlib
import time
import pandas as pd
from datetime import datetime

# Cargar configuración
with open('binance_config.json', 'r') as f:
    CONFIG = json.load(f)

class BinanceTrader:
    def __init__(self):
        self.api_key = CONFIG['api_key']
        self.api_secret = CONFIG['api_secret']
        self.base_url = CONFIG['testnet_url'] if CONFIG['use_testnet'] else CONFIG['base_url']
        self.symbol = CONFIG['symbol']
        self.position_size = CONFIG['position_size']
    
    def _get_signature(self, params):
        """Genera signature para autenticación"""
        timestamp = int(time.time() * 1000)
        query_string = f"{params}&timestamp={timestamp}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature, timestamp
    
    def get_account_info(self):
        """Obtiene información de la cuenta"""
        try:
            signature, timestamp = self._get_signature("")
            headers = {'X-MBX-APIKEY': self.api_key}
            params = {'timestamp': timestamp, 'signature': signature}
            
            response = requests.get(f"{self.base_url}/api/v3/account", 
                                  headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error obteniendo cuenta: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def get_price(self, symbol=None):
        """Obtiene precio actual"""
        if not symbol:
            symbol = self.symbol
        try:
            response = requests.get(f"{self.base_url}/api/v3/ticker/price", 
                                  params={'symbol': symbol}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return float(data['price'])
            return None
        except Exception as e:
            print(f"Error obteniendo precio: {e}")
            return None
    
    def place_order(self, side, quantity, order_type='MARKET'):
        """Coloca una orden"""
        try:
            params = f"symbol={self.symbol}&side={side}&type={order_type}&quantity={quantity}"
            signature, timestamp = self._get_signature(params)
            
            headers = {'X-MBX-APIKEY': self.api_key}
            data = {
                'symbol': self.symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'timestamp': timestamp,
                'signature': signature
            }
            
            response = requests.post(f"{self.base_url}/api/v3/order", 
                                   headers=headers, data=data, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error en orden: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error colocando orden: {e}")
            return None
    
    def run_trading_cycle(self):
        """Ejecuta un ciclo de trading"""
        print(f"=== Ciclo Trading {datetime.now().strftime('%H:%M:%S')} ===")
        
        # Obtener precio actual
        price = self.get_price()
        if not price:
            print("No se pudo obtener precio")
            return
        
        print(f"Precio {self.symbol}: ${price:.4f}")
        
        # Obtener información de cuenta
        account = self.get_account_info()
        if not account:
            print("No se pudo obtener info de cuenta")
            return
        
        print(f"Puede tradear: {account.get('canTrade', False)}")
        
        # Obtener balance USDT
        balances = account.get('balances', [])
        usdt_balance = next((b for b in balances if b['asset'] == 'USDT'), None)
        
        if usdt_balance:
            free_usdt = float(usdt_balance['free'])
            print(f"Balance disponible: ${free_usdt:.2f}")
            
            if free_usdt > 10:  # Mínimo $10 para operar
                # Calcular cantidad a comprar (5% del balance)
                position_value = free_usdt * self.position_size
                quantity = position_value / price
                quantity = round(quantity, 6)  # Redondear a 6 decimales
                
                print(f"Posición calculada: {quantity} {self.symbol.replace('USDT', '')} (${position_value:.2f})")
                
                # Aquí puedes agregar lógica de señales de trading
                # Por ahora solo muestra la información
            else:
                print("Balance insuficiente para operar")

if __name__ == "__main__":
    trader = BinanceTrader()
    trader.run_trading_cycle()
'''
    
    with open('binance_trader.py', 'w') as f:
        f.write(trading_script)
    
    # Script de descarga de datos
    downloader_script = '''#!/usr/bin/env python3
"""
Descargador de datos Binance configurado
"""

import json
import requests
import pandas as pd
from datetime import datetime

# Cargar configuración
with open('binance_config.json', 'r') as f:
    CONFIG = json.load(f)

def download_market_data():
    """Descarga datos de mercado"""
    base_url = CONFIG['base_url']  # Usar API pública
    symbol = CONFIG['symbol']
    
    print(f"Descargando datos de {symbol}...")
    
    try:
        # Precio actual
        response = requests.get(f"{base_url}/api/v3/ticker/price", 
                              params={'symbol': symbol}, timeout=5)
        if response.status_code == 200:
            price_data = response.json()
            print(f"Precio actual: ${float(price_data['price']):.4f}")
        
        # Datos históricos
        response = requests.get(f"{base_url}/api/v3/klines", 
                              params={'symbol': symbol, 'interval': '1m', 'limit': 100}, 
                              timeout=10)
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
            df.to_csv(f'{symbol}_data.csv', index=False)
            print(f"Datos guardados: {len(df)} velas en {symbol}_data.csv")
            print(f"Último precio: ${df['close'].iloc[-1]:.4f}")
            
    except Exception as e:
        print(f"Error descargando datos: {e}")

if __name__ == "__main__":
    download_market_data()
'''
    
    with open('binance_downloader.py', 'w') as f:
        f.write(downloader_script)
    
    print("Scripts de trading creados:")
    print("- binance_trader.py: Bot principal de trading")
    print("- binance_downloader.py: Descargador de datos")

def setup_complete_system(api_key: str, api_secret: str):
    """Configura sistema completo"""
    print("=== CONFIGURACIÓN COMPLETA SISTEMA BINANCE ===")
    
    # Paso 1: Configurar credenciales
    if not configure_credentials(api_key, api_secret):
        print("Error en configuración de credenciales")
        return False
    
    # Paso 2: Crear scripts
    create_trading_scripts()
    
    # Paso 3: Crear estructura de carpetas
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Paso 4: Crear archivo de instrucciones
    instructions = """# Sistema Binance Configurado

## Archivos Principales:
- binance_trader.py: Bot de trading principal
- binance_downloader.py: Descargador de datos
- binance_config.json: Configuración del sistema

## Uso:

### 1. Descargar datos de mercado:
```bash
python binance_downloader.py
```

### 2. Ejecutar bot de trading:
```bash
python binance_trader.py
```

### 3. Verificar configuración:
```bash
python configure_binance_system.py
```

## Configuración Actual:
- Modo: TESTNET (seguro para pruebas)
- Símbolo: SOLUSDT
- Tamaño posición: 5% del balance
- Credenciales: Configuradas y validadas

## Próximos Pasos:
1. Ejecutar binance_downloader.py para obtener datos
2. Ejecutar binance_trader.py para ver información de cuenta
3. Agregar lógica de señales de trading según necesites

El sistema está listo para usar con tus credenciales reales de Binance.
"""
    
    with open('README_BINANCE.md', 'w') as f:
        f.write(instructions)
    
    print("\n=== SISTEMA CONFIGURADO EXITOSAMENTE ===")
    print("✓ Credenciales validadas")
    print("✓ Scripts de trading creados")
    print("✓ Estructura de carpetas creada")
    print("✓ Documentación generada")
    print("\nPróximos pasos:")
    print("1. python binance_downloader.py - Descargar datos")
    print("2. python binance_trader.py - Probar bot")
    print("3. Revisar README_BINANCE.md para más detalles")
    
    return True

def main():
    """Función principal"""
    print("=== CONFIGURADOR SISTEMA BINANCE ===")
    print("Introduce tus credenciales de Binance:")
    
    api_key = input("API Key: ").strip()
    api_secret = input("API Secret: ").strip()
    
    if api_key and api_secret:
        setup_complete_system(api_key, api_secret)
    else:
        print("Credenciales inválidas")

if __name__ == "__main__":
    main()