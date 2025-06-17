# Solana Trading Bot - Documentación Consolidada

## 1. Descripción General
Bot de trading algorítmico para Solana (SOL/USDT) con análisis técnico, aprendizaje adaptativo, backtesting y notificaciones. **Actualmente el bot y todo el pipeline usan exclusivamente Binance como exchange de datos y trading.**

## 2. Características Principales
- Múltiples estrategias (clásicas y ML)
- Ponderación adaptativa de indicadores
- Backtesting integrado
- Modos paper y real
- Gestión de riesgos avanzada
- Notificaciones por Telegram
- Interfaz CLI

## 3. Estructura del Proyecto
- api_client/: Cliente para exchanges (actualmente solo Binance)
- indicators/: Indicadores técnicos
- strategies/: Estrategias de trading
- risk_management/: Gestión de riesgos
- backtesting/: Motor de backtesting
- data_management/: Gestión de datos
- adaptive_system/: Sistema adaptativo
- notifications/: Notificaciones
- interface/: CLI
- db/: Base de datos
- core/: Núcleo
- utils/: Utilidades

## 4. Manual de Uso
### Modos de operación
- Paper Trading: Simulación
- Live Trading: Real (con validaciones)

### Menú principal
1. Scalping en tiempo real
2. Backtesting
3. Configuración
4. Monitor

### Seguridad y validaciones
- Circuit breakers, límites de pérdida, requisitos para modo real

### Sistema adaptativo
- Ponderación dinámica, aprendizaje de patrones, export/import de "cerebro"

### Gestión de riesgos
- Tamaño de posición, stop loss, take profit, control de drawdown

### Notificaciones
- Alertas, Telegram, resumen diario

### Interfaz web
- Dashboard, gráficos, métricas

### Comandos rápidos
```bash
python main.py --mode paper
python main.py --mode live
python bot_cli.py
```

### Estados del bot
- RUNNING, MONITORING, TRADING, STOPPED, ERROR

### Archivos principales
- main.py, trading_bot.py, strategies/, config.env

### Requisitos
- Python 3.11.7, requirements.txt, conexión estable, API keys Binance

### Mantenimiento
- Backups, logs, reporte de errores, actualizaciones

## 5. Arquitectura y Estrategias
- Núcleo: Bot Manager, Trading Engine
- Sistema adaptativo: Brain Transfer, Indicator Weighting
- Estrategias: Pattern Analyzer, Scalping, Auto Suggestion
- Gestión de datos: Market Data, Order Book Analyzer
- Gestión de riesgos: Position Sizing, Stop Loss Manager
- Cliente API: Binance Client, WebSocket Client
- Interfaz: CLI Menu, Color Formatter
- Notificaciones: Alert System, Telegram Bot
- Backtesting: Strategy Tester, Performance Analyzer

## 6. Estrategias Implementadas
- Scalping por Ruptura, Momento, Reversión a la Media (ver detalles en estructura original)

## 7. Advertencia
El trading algorítmico conlleva riesgos. Usa este software bajo tu propia responsabilidad.

## 8. Definición y cálculo del target ML

- El cálculo de la variable objetivo (`target`) para el modelo de Machine Learning se realiza en:
  - **Archivo:** `binance_data_processor.py`
  - **Función:** `calculate_future_return_and_target` (o equivalente)

### Parámetros principales:
- `future_window`: horizonte de velas hacia adelante para calcular el retorno futuro (ej. 5 o 10 minutos).
- `threshold_percentage`: porcentaje mínimo de cambio de precio para considerar una señal significativa.

### Lógica de cálculo:
- Se calcula el `future_return` como el cambio porcentual entre el precio de cierre actual y el de la vela futura.
- El `target` se clasifica en tres clases:
  - **1 (compra):** si el retorno futuro es mayor o igual al umbral positivo.
  - **-1 (venta):** si el retorno futuro es menor o igual al umbral negativo.
  - **0 (lateral):** si el retorno está entre los umbrales.

### Problema actual:
- El target suele tener solo una clase (0), lo que impide el entrenamiento ML.
- Se recomienda revisar la lógica y los datos para lograr una distribución más balanceada.

### Referencia:
- Ver archivo `ml_target_definition.md` en esta misma carpeta para la definición formal y ejemplos.

## 9. Extracción de muestra de datos para depuración y compatibilidad

**Última actualización: 17/06/2025 — Extracción de muestra de datos y documentación de extract_sample.py**

- El script `extract_sample.py` permite extraer fácilmente una muestra pequeña (por ejemplo, 50 filas) de cualquier archivo grande de datos CSV.
- Uso principal: generar un archivo `sample_binance_raw_data.csv` para compartir, depurar o analizar la estructura de los datos de entrada.
- Configuración: se debe ajustar la variable `INPUT_BIG_CSV_PATH` al archivo de datos de origen (por ejemplo, `data/SOLUSDT_processed_big_dataset.csv`).
- El archivo de salida se genera en la raíz del proyecto y puede ser usado para análisis rápido o para compartir con otros colaboradores o IA.
- El orden de columnas de la muestra está documentado en `info/sample_binance_raw_data.txt` y debe respetarse para compatibilidad multiplataforma (ej. Gemini, Colab, etc.):

```
open_time, open, high, low, close, volume, close_time, quote_asset_volume, number_of_trades, taker_buy_base_asset_volume, taker_buy_quote_asset_volume, SMA_10, SMA_30, RSI_14, EMA_12, EMA_26, MACD, MACD_Signal, MACD_Hist, BB_SMA, BB_STD, BB_UPPER, BB_LOWER, hour, day_of_week, day_of_month, month, target
```

## 10. Contexto multiplataforma y flujo de trabajo

- El proyecto se desarrolla y mantiene en VS Code, con integración a GitHub, Google Colab y Google Drive para colaboración, entrenamiento y pruebas multiplataforma.
- El flujo de trabajo incluye edición y ejecución de scripts en local (VS Code), entrenamiento de modelos ML en Colab, y almacenamiento/backup de datos y modelos en Drive.
- Toda la información relevante de cambios, rutas y estado se documenta en la carpeta `info/`.

## 11. Estado y pendientes

- El pipeline concatena y procesa correctamente los archivos históricos de Binance.
- El cálculo del target sigue generando una sola clase, lo que impide el entrenamiento ML (SMOTE y RandomForest requieren al menos dos clases).
- Se han implementado logs y archivos de depuración, pero el problema persiste incluso con umbral 0.0.
- Próximos pasos: revisar la lógica de cálculo y la calidad de los datos, probar con otros símbolos, y automatizar la generación de fragmentos de depuración.

---

**Nota:** El archivo motor para activar todo el proceso es `train_model.py`. Ejecuta este archivo para iniciar el pipeline completo de procesamiento y entrenamiento ML.

**Última actualización: 17/06/2025**

_Archivo consolidado por GitHub Copilot el 17/06/2025._
