# Sistema de Trading Binance - Instrucciones Completas

## Descripción del Sistema

Sistema de trading modular de 3 componentes independientes:
1. **Descargador de datos** - Obtiene datos reales de Binance (sin API keys)
2. **Procesador de análisis** - Calcula indicadores técnicos y señales
3. **Bot de trading** - Ejecuta operaciones en modo paper trading

## Instalación

### 1. Dependencias Requeridas
```bash
pip install pandas requests numpy
```

### 2. Estructura de Archivos
```
proyecto/
├── binance_data_downloader.py    # Módulo descarga datos
├── binance_data_processor.py     # Módulo procesamiento
├── binance_trading_bot.py        # Bot de trading
├── test_binance_system.py        # Script de prueba completo
├── binance_data/                 # Carpeta datos descargados
├── processed_data/               # Carpeta análisis procesados
└── trades_log_SOLUSDT.json      # Log de operaciones
```

## Uso del Sistema

### Opción 1: Prueba Completa Automática
```bash
python test_binance_system.py
```
Ejecuta todo el flujo: descarga → procesamiento → trading

### Opción 2: Módulos Independientes

#### 1. Descargar Datos de Binance
```bash
python binance_data_downloader.py
```
**Qué hace:**
- Conecta a API pública de Binance (sin credenciales)
- Descarga precio actual, ticker 24h, datos históricos
- Guarda archivos CSV y JSON en `binance_data/`
- Datos para SOLUSDT en intervalos 1m, 5m, 15m, 1h

#### 2. Procesar Análisis Técnico
```bash
python binance_data_processor.py
```
**Qué hace:**
- Lee datos de `binance_data/`
- Calcula indicadores: SMA, EMA, RSI, MACD, Bollinger Bands
- Detecta señales de compra/venta
- Guarda análisis en `processed_data/`

#### 3. Ejecutar Bot de Trading
```bash
python binance_trading_bot.py
```
**Qué hace:**
- Lee análisis de `processed_data/`
- Ejecuta operaciones de paper trading
- Balance virtual inicial: $10,000
- Gestión automática de stop loss/take profit
- Guarda log de trades

## Características del Sistema

### Ventajas
- **Sin API keys requeridas** - Usa endpoints públicos de Binance
- **Completamente modular** - Cada componente es independiente
- **Datos reales** - No usa simulaciones, obtiene datos reales de mercado
- **Paper trading seguro** - Sin riesgo financiero real
- **Análisis técnico avanzado** - Múltiples indicadores y señales

### Datos Descargados
- Precio actual en tiempo real
- Estadísticas 24 horas (volumen, cambio %)
- Velas históricas (OHLCV) hasta 1000 períodos
- Order book (profundidad de mercado)
- Trades recientes

### Indicadores Calculados
- **SMA** (5, 20, 50 períodos)
- **EMA** (12, 26 períodos)
- **RSI** (14 períodos)
- **MACD** (12, 26, 9)
- **Bollinger Bands** (20 períodos, 2σ)
- **Soporte/Resistencia** dinámicos

### Señales de Trading
- **Cruce de medias móviles** (SMA 5/20)
- **RSI sobrecomprado/sobrevendido** (<30 />70)
- **MACD bullish/bearish** 
- **Confirmación múltiple** (requiere 60% confianza)

## Configuración Avanzada

### Modificar Símbolo
Editar en cada archivo:
```python
symbol = "BTCUSDT"  # Cambiar de SOLUSDT a otro par
```

### Ajustar Intervalos
En `binance_data_downloader.py`:
```python
intervals = ["1m", "5m", "15m", "1h", "4h"]  # Agregar más intervalos
```

### Cambiar Parámetros de Trading
En `binance_trading_bot.py`:
```python
position_percent = 0.05  # 5% del balance por operación
min_confidence = 0.7     # 70% confianza mínima
```

## Flujo de Operación Recomendado

### Para Trading Automático
1. **Cada 1-2 minutos**: Ejecutar descargador
2. **Después de descarga**: Ejecutar procesador
3. **Modo continuo**: Dejar bot ejecutándose

### Script de Automatización (ejemplo)
```bash
#!/bin/bash
while true; do
    python binance_data_downloader.py
    python binance_data_processor.py
    python binance_trading_bot.py
    sleep 60
done
```

## Archivos Generados

### binance_data/
- `SOLUSDT_1m_klines.csv` - Datos de velas 1 minuto
- `SOLUSDT_24hr_ticker.json` - Estadísticas 24h
- `SOLUSDT_orderbook.json` - Libro de órdenes
- `SOLUSDT_recent_trades.json` - Trades recientes
- `SOLUSDT_summary_report.json` - Reporte resumen

### processed_data/
- `SOLUSDT_1m_analysis.json` - Análisis técnico completo
- `SOLUSDT_1m_processed.csv` - Datos con indicadores

### Logs de Trading
- `trades_log_SOLUSDT.json` - Historial de operaciones
- Performance: balance, win rate, P&L

## Solución de Problemas

### Error de conexión Binance
```
Error: No se pudo conectar con Binance
```
**Solución**: Verificar conexión a internet, Binance puede estar temporalmente indisponible

### Datos antiguos
```
Archivo de análisis muy antiguo: 15.3 minutos
```
**Solución**: Ejecutar primero descargador y procesador para actualizar datos

### Dependencias faltantes
```
ImportError: No module named 'pandas'
```
**Solución**: `pip install pandas requests numpy`

### Sin señales de trading
```
Señal insuficiente para operar
```
**Normal**: El bot es conservador, requiere alta confianza para operar

## Métricas de Rendimiento

El sistema rastrea automáticamente:
- **Total trades**: Número de operaciones
- **Win rate**: Porcentaje de operaciones exitosas
- **P&L total**: Ganancia/pérdida acumulada
- **Retorno**: Porcentaje de ganancia sobre balance inicial
- **Average win/loss**: Promedio de ganancias y pérdidas

## Próximos Pasos Recomendados

1. **Ejecutar prueba inicial**: `python test_binance_system.py`
2. **Revisar archivos generados** en carpetas `binance_data/` y `processed_data/`
3. **Ejecutar bot en modo continuo** para paper trading
4. **Analizar performance** en `trades_log_SOLUSDT.json`
5. **Optimizar parámetros** según resultados

## Notas Importantes

- **Solo paper trading**: No ejecuta operaciones reales con dinero
- **Datos en tiempo real**: Conecta directamente a Binance
- **Sin riesgo financiero**: Balance virtual, operaciones simuladas
- **Sistema educativo**: Para aprender trading algorítmico

**El sistema está listo para usar sin modificaciones adicionales. Todos los módulos son independientes y pueden ejecutarse por separado o en conjunto.**