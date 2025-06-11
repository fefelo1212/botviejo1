#!/usr/bin/env python3
"""
Script de prueba completo del sistema Binance
Ejecuta descarga -> procesamiento -> bot de trading
"""

import os
import time
from datetime import datetime

def test_complete_system():
    """Prueba el sistema completo paso a paso"""
    print("=== SISTEMA BINANCE COMPLETO ===")
    print("Prueba: Descarga -> Procesamiento -> Trading")
    print(f"Timestamp: {datetime.now()}")
    
    try:
        # PASO 1: Descargar datos de Binance
        print("\n1. DESCARGANDO DATOS DE BINANCE...")
        from binance_data_downloader import BinanceDataDownloader
        
        downloader = BinanceDataDownloader()
        
        # Verificar conexión
        server_time = downloader.get_server_time()
        if not server_time:
            print("ERROR: No se pudo conectar con Binance")
            return False
        
        symbol = "SOLUSDT"
        
        # Descargar datos básicos
        print(f"Descargando datos para {symbol}...")
        price = downloader.get_symbol_price(symbol)
        ticker = downloader.get_24hr_ticker(symbol)
        klines = downloader.get_klines_historical(symbol, "1m", 1000)
        
        if klines is None or len(klines) == 0:
            print("ERROR: No se pudieron descargar datos históricos")
            return False
        
        print(f"✓ Datos descargados: {len(klines)} velas")
        
        # PASO 2: Procesar datos
        print("\n2. PROCESANDO DATOS...")
        from binance_data_processor import BinanceDataProcessor
        
        processor = BinanceDataProcessor()
        
        # Procesar análisis completo
        analysis = processor.process_full_analysis(symbol, "1m")
        if not analysis:
            print("ERROR: No se pudo procesar el análisis")
            return False
        
        print("✓ Análisis procesado correctamente")
        
        # Obtener recomendación
        recommendation = processor.get_trading_recommendation(symbol, "1m")
        if recommendation:
            print(f"✓ Recomendación: {recommendation['recommendation']}")
        
        # PASO 3: Ejecutar bot de trading
        print("\n3. EJECUTANDO BOT DE TRADING...")
        from binance_trading_bot import BinanceTradingBot
        
        bot = BinanceTradingBot()
        
        # Ejecutar un ciclo de prueba
        bot.run_single_cycle()
        
        print("✓ Bot ejecutado correctamente")
        
        # PASO 4: Verificar archivos generados
        print("\n4. VERIFICANDO ARCHIVOS GENERADOS...")
        
        expected_files = [
            "binance_data/SOLUSDT_1m_klines.csv",
            "binance_data/SOLUSDT_24hr_ticker.json",
            "processed_data/SOLUSDT_1m_analysis.json",
            "processed_data/SOLUSDT_1m_processed.csv"
        ]
        
        for file in expected_files:
            if os.path.exists(file):
                size = os.path.getsize(file)
                print(f"✓ {file} ({size} bytes)")
            else:
                print(f"✗ {file} (no encontrado)")
        
        print("\n=== PRUEBA COMPLETADA EXITOSAMENTE ===")
        print("El sistema está funcionando correctamente")
        print("Puedes ejecutar los módulos por separado:")
        print("1. python binance_data_downloader.py")
        print("2. python binance_data_processor.py") 
        print("3. python binance_trading_bot.py")
        
        return True
        
    except ImportError as e:
        print(f"ERROR: Falta dependencia - {e}")
        print("Instala con: pip install pandas requests")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def check_dependencies():
    """Verifica dependencias requeridas"""
    print("Verificando dependencias...")
    
    required_packages = [
        "pandas",
        "requests", 
        "numpy"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nFaltan dependencias: {missing_packages}")
        print(f"Instala con: pip install {' '.join(missing_packages)}")
        return False
    
    print("✓ Todas las dependencias están instaladas")
    return True

def show_usage_instructions():
    """Muestra instrucciones de uso"""
    print("\n=== INSTRUCCIONES DE USO ===")
    print()
    print("SISTEMA DE 3 MÓDULOS INDEPENDIENTES:")
    print()
    print("1. DESCARGADOR DE DATOS:")
    print("   python binance_data_downloader.py")
    print("   - Descarga datos de Binance (no requiere API keys)")
    print("   - Guarda en carpeta binance_data/")
    print("   - Datos: precios, velas, ticker, order book")
    print()
    print("2. PROCESADOR DE DATOS:")
    print("   python binance_data_processor.py")
    print("   - Lee datos de binance_data/")
    print("   - Calcula indicadores técnicos")
    print("   - Genera señales de trading")
    print("   - Guarda en carpeta processed_data/")
    print()
    print("3. BOT DE TRADING:")
    print("   python binance_trading_bot.py")
    print("   - Lee datos de processed_data/")
    print("   - Ejecuta operaciones de paper trading")
    print("   - Balance virtual: $10,000")
    print("   - Guarda log de trades")
    print()
    print("FLUJO COMPLETO:")
    print("1. Ejecutar descargador cada 1-5 minutos")
    print("2. Ejecutar procesador después del descargador")
    print("3. Ejecutar bot para trading automático")
    print()
    print("ARCHIVOS GENERADOS:")
    print("- binance_data/: Datos raw de Binance")
    print("- processed_data/: Análisis técnico procesado")
    print("- trades_log_SOLUSDT.json: Log de operaciones")

if __name__ == "__main__":
    print("=== BINANCE TRADING SYSTEM TEST ===")
    
    # Verificar dependencias
    if not check_dependencies():
        exit(1)
    
    # Mostrar instrucciones
    show_usage_instructions()
    
    # Ejecutar prueba
    print(f"\n¿Ejecutar prueba del sistema completo? (y/n): ", end="")
    response = input().lower()
    
    if response == 'y':
        success = test_complete_system()
        if success:
            print("\n🎉 SISTEMA FUNCIONANDO CORRECTAMENTE")
        else:
            print("\n❌ SISTEMA CON ERRORES")
    else:
        print("Prueba cancelada")
        print("Ejecuta los módulos individualmente cuando estés listo")