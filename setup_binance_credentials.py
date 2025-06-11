#!/usr/bin/env python3
"""
Script para configurar credenciales de Binance de forma segura
"""

import os
import json
from datetime import datetime

def setup_credentials(api_key: str, api_secret: str):
    """Configura credenciales de Binance de forma segura"""
    
    # Validar credenciales
    if not api_key or not api_secret:
        print("Error: Credenciales vacías")
        return False
    
    if len(api_key) < 20 or len(api_secret) < 20:
        print("Error: Credenciales parecen incorrectas")
        return False
    
    # Crear archivo .env
    env_content = f"""# Credenciales Binance
BINANCE_API_KEY={api_key}
BINANCE_API_SECRET={api_secret}

# Configuración
SYMBOL=SOLUSDT
USE_TESTNET=True
POSITION_SIZE=0.05
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    # Crear config.json
    config_data = {
        "api_key": api_key,
        "api_secret": api_secret,
        "symbol": "SOLUSDT",
        "use_testnet": True,
        "position_size": 0.05,
        "setup_time": datetime.now().isoformat()
    }
    
    with open('binance_config.json', 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print("✓ Credenciales configuradas exitosamente")
    print("✓ Archivo .env creado")
    print("✓ Archivo binance_config.json creado")
    print(f"✓ API Key: ***{api_key[-8:]}")
    print(f"✓ API Secret: ***{api_secret[-8:]}")
    
    return True

def load_credentials():
    """Carga credenciales desde archivo"""
    try:
        with open('binance_config.json', 'r') as f:
            config = json.load(f)
        
        print("Credenciales cargadas:")
        print(f"API Key: ***{config['api_key'][-8:]}")
        print(f"Testnet: {config['use_testnet']}")
        print(f"Símbolo: {config['symbol']}")
        
        return config
    except FileNotFoundError:
        print("No se encontró archivo de configuración")
        return None
    except Exception as e:
        print(f"Error cargando configuración: {e}")
        return None

def test_credentials():
    """Prueba las credenciales configuradas"""
    config = load_credentials()
    if not config:
        return False
    
    try:
        from binance_real_trading import BinanceRealTrader
        from binance_config import config as global_config
        
        # Configurar credenciales globales
        global_config.set_credentials(config['api_key'], config['api_secret'])
        global_config.use_testnet = config['use_testnet']
        
        # Crear trader y probar
        trader = BinanceRealTrader()
        
        if trader.test_connection():
            print("✓ Credenciales válidas y funcionando")
            return True
        else:
            print("✗ Error con las credenciales")
            return False
            
    except Exception as e:
        print(f"Error probando credenciales: {e}")
        return False

if __name__ == "__main__":
    print("=== CONFIGURACIÓN CREDENCIALES BINANCE ===")
    
    # Verificar si ya hay configuración
    existing_config = load_credentials()
    
    if existing_config:
        print("\n¿Quieres probar las credenciales existentes? (y/n): ", end="")
        test_existing = input().lower()
        
        if test_existing == 'y':
            test_credentials()
        else:
            print("Introduce nuevas credenciales:")
            api_key = input("API Key: ").strip()
            api_secret = input("API Secret: ").strip()
            setup_credentials(api_key, api_secret)
    else:
        print("Introduce tus credenciales de Binance:")
        api_key = input("API Key: ").strip()
        api_secret = input("API Secret: ").strip()
        
        if setup_credentials(api_key, api_secret):
            print("\n¿Probar conexión ahora? (y/n): ", end="")
            test_now = input().lower()
            
            if test_now == 'y':
                test_credentials()