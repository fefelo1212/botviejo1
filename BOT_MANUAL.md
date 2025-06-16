
# MANUAL DEL BOT DE TRADING SOLANA (BINANCE)

## 1. VISIÓN GENERAL
El bot opera en el par SOLUSDT en Binance, utilizando datos en tiempo real y un sistema de aprendizaje adaptativo. El sistema está diseñado para evolucionar y mejorar sus estrategias basándose en los resultados históricos.

## 2. MODOS DE OPERACIÓN

### Paper Trading (Actual)
- Sin riesgo real
- Conexión directa a Binance (sin API key)
- Datos en tiempo real
- Aprendizaje activo
- Balance virtual: $10,000 USDT

### Live Trading (Futuro)
- Requiere validación de performance
- Necesita API keys de Binance
- Sistema completo de gestión de riesgos
- Monitoreo 24/7

## 3. OPERACIÓN DEL BOT

### Inicio del Bot
```powershell
python trading_bot.py
```

### Monitoreo en Tiempo Real
- Ver `trading_bot.log` para actividad
- Revisar `SOLUSDT_trading_log.json` para operaciones
- Consultar `learning_data.json` para datos de aprendizaje

## 4. ESTRATEGIA ACTUAL

### Indicadores Técnicos
- RSI (Periodo 14)
  * Sobrecompra: 70
  * Sobreventa: 30
  * Peso: 30%

- MACD
  * Línea rápida: 12
  * Línea lenta: 26
  * Señal: 9
  * Peso: 30%

- Medias Móviles
  * Rápida: 5 períodos
  * Lenta: 20 períodos
  * Peso: 40%

### Gestión de Riesgo
- Tamaño posición: 1% del balance
- Take Profit: 1.5%
- Stop Loss: 1%

## 5. SISTEMA DE APRENDIZAJE

### Datos Recolectados
- Precio y volumen
- Profundidad de mercado
- Trades en tiempo real
- Rendimiento de operaciones

### Optimización
- Pesos de indicadores
- Parámetros de entrada/salida
- Detección de condiciones de mercado

## 6. REQUISITOS PARA TRADING REAL

### Performance Mínima
- 100+ operaciones simuladas
- Win rate > 55%
- Drawdown máximo < 15%
- Un mes de operación estable

### Configuración Necesaria
- API Keys de Binance
- Configuración de webhooks
- Sistema de notificaciones
- Monitoreo 24/7

## 7. ARCHIVOS IMPORTANTES

### Configuración
- `config.env`: Configuración principal
- `learning_data.json`: Datos de aprendizaje
- `binance_config.json`: Configuración de Binance

### Logs y Datos
- `trading_bot.log`: Log principal
- `SOLUSDT_trading_log.json`: Historial de trades
- `SOLUSDT_live_data.csv`: Datos en tiempo real
- `SOLUSDT_technical_analysis.csv`: Análisis técnico

## 8. PLAN DE IMPLEMENTACIÓN

### Fase 1: Simulación (Actual)
- Operación 24/7 en paper trading
- Recolección de datos
- Optimización de estrategias

### Fase 2: Aprendizaje
- Entrenamiento del sistema
- Ajuste de parámetros
- Validación de resultados

### Fase 3: Trading Real
- Implementación gradual
- Monitoreo constante
- Gestión de riesgos activa
- Stop loss dinámico
- Take profit escalonado
- Control drawdown
- Límites exposición

## 6. NOTIFICACIONES
- Alertas operaciones
- Telegram integrado
- Alertas riesgo
- Resumen diario

## 7. INTERFAZ WEB
- Dashboard tiempo real
- Gráficos rendimiento
- Estado operaciones
- Métricas trading

## 8. COMANDOS RÁPIDOS
```bash
python main.py --mode paper         # Iniciar simulación
python main.py --mode live         # Iniciar real (con validaciones)
python bot_cli.py                  # Interfaz línea comandos
```

## 9. ESTADOS DEL BOT
- RUNNING: Operando
- MONITORING: Analizando
- TRADING: En posición
- STOPPED: Detenido
- ERROR: Error detectado

## 10. ARCHIVOS PRINCIPALES
- main.py: Entrada principal
- trading_bot.py: Core del bot
- strategies/: Estrategias
- config.env: Configuración

## 11. REQUISITOS
- Python 3.11.7
- Dependencias en requirements.txt
- Conexión estable
- API keys (modo real)

## 12. MANTENIMIENTO
- Backups automáticos
- Logs detallados
- Reporte errores
- Actualizaciones auto
