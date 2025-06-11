#!/usr/bin/env python3
"""
Configuración de credenciales para Binance
Archivo para credenciales reales de trading
"""

import os
from typing import Dict, Optional

class BinanceConfig:
    """Configuración de credenciales Binance"""
    
    def __init__(self):
        # Credenciales principales
        self.api_key = None
        self.api_secret = None
        
        # URLs de API
        self.base_url = "https://api.binance.com"
        self.testnet_url = "https://testnet.binance.vision"
        
        # Configuración de trading
        self.use_testnet = True  # Cambiar a False para trading real
        self.symbol = "SOLUSDT"
        self.default_quantity = 0.01  # Cantidad mínima
        
    def set_credentials(self, api_key: str, api_secret: str):
        """Configura las credenciales de API"""
        self.api_key = api_key
        self.api_secret = api_secret
        print("✓ Credenciales configuradas")
    
    def load_from_env(self):
        """Carga credenciales desde variables de entorno"""
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        
        if self.api_key and self.api_secret:
            print("✓ Credenciales cargadas desde variables de entorno")
            return True
        else:
            print("✗ No se encontraron credenciales en variables de entorno")
            return False
    
    def get_api_url(self) -> str:
        """Obtiene URL de API según configuración"""
        return self.testnet_url if self.use_testnet else self.base_url
    
    def is_configured(self) -> bool:
        """Verifica si las credenciales están configuradas"""
        return bool(self.api_key and self.api_secret)
    
    def get_headers(self) -> Dict[str, str]:
        """Obtiene headers para requests autenticados"""
        if not self.is_configured():
            raise ValueError("Credenciales no configuradas")
        
        return {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def create_signature(self, params: str, timestamp: int) -> str:
        """Crea signature para requests autenticados"""
        import hmac
        import hashlib
        
        if not self.api_secret:
            raise ValueError("API Secret no configurado")
        
        query_string = f"{params}&timestamp={timestamp}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def print_config(self):
        """Muestra configuración actual (sin mostrar claves)"""
        print("\n=== CONFIGURACIÓN BINANCE ===")
        print(f"API Key: {'***' + self.api_key[-8:] if self.api_key else 'No configurada'}")
        print(f"API Secret: {'***' + self.api_secret[-8:] if self.api_secret else 'No configurado'}")
        print(f"Testnet: {'Sí' if self.use_testnet else 'No'}")
        print(f"URL API: {self.get_api_url()}")
        print(f"Símbolo: {self.symbol}")
        print(f"Estado: {'✓ Configurado' if self.is_configured() else '✗ Incompleto'}")

# Instancia global de configuración
config = BinanceConfig()

def setup_credentials():
    """Función para configurar credenciales interactivamente"""
    print("=== CONFIGURACIÓN DE CREDENCIALES BINANCE ===")
    print("Introduce tus credenciales de Binance:")
    
    api_key = input("API Key: ").strip()
    api_secret = input("API Secret: ").strip()
    
    if api_key and api_secret:
        config.set_credentials(api_key, api_secret)
        
        # Preguntar por testnet
        use_testnet = input("¿Usar testnet? (y/n) [y]: ").strip().lower()
        config.use_testnet = use_testnet != 'n'
        
        config.print_config()
        return True
    else:
        print("✗ Credenciales inválidas")
        return False

if __name__ == "__main__":
    setup_credentials()