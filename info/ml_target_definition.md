# Definición de la Variable Objetivo (Target) para el Modelo ML

Este documento describe cómo se define y calcula la variable `target` para el entrenamiento del modelo de Machine Learning en el bot de trading. Esta variable es la que el modelo intenta predecir para generar señales de compra/venta.

## 1. Archivo y Función Principal de Cálculo

* **Archivo:** `binance_data_processor.py`
* **Función:** `calculate_future_return_and_target` (dentro de la clase `BinanceDataProcessor`)

## 2. Parámetros de Configuración del Target

Estos parámetros son cruciales para determinar la granularidad y la sensibilidad del target.

* **`future_window`**: Define el horizonte de tiempo hacia adelante en el que se evalúa el cambio de precio.
    * **Unidad:** Número de velas (actualmente se asume 1 vela, pero debería ser configurable y reflejar un horizonte de scalping, por ejemplo, 5 o 10 minutos).
    * **Uso en el cálculo:** Se utiliza para obtener el `close` de la vela futura (`future_close = df['close'].shift(-self.future_window)`).

* **`threshold_percentage`**: Define el porcentaje mínimo de cambio en el precio que se considera significativo para una subida o bajada.
    * **Unidad:** Porcentaje (ej., 0.05 significa un 0.05%).
    * **Uso en el cálculo:** Se aplica al `future_return` para clasificar el movimiento.

## 3. Lógica de Cálculo del `future_return`

El `future_return` es el rendimiento porcentual futuro calculado como:

$ \text{future_return} = \left( \frac{\text{future_close} - \text{close}}{\text{close}} \right) \times 100 $

## 4. Definición de la Variable `target` (Clasificación)

La variable `target` se binariza (o trinariza) basándose en el `future_return` y el `threshold_percentage`.

* **Clase 1 (Subida / Compra):**
    * Condición: `future_return` >= `threshold_percentage`
    * Significado: Se espera que el precio suba al menos el `threshold_percentage` en el `future_window` siguiente.

* **Clase -1 (Bajada / Venta):**
    * Condición: `future_return` <= `-threshold_percentage`
    * Significado: Se espera que el precio baje al menos el `threshold_percentage` en el `future_window` siguiente.

* **Clase 0 (Lateral / Sin movimiento significativo):**
    * Condición: `(-threshold_percentage < future_return < threshold_percentage)`
    * Significado: El precio se mantiene dentro del rango de `threshold_percentage` (no hay movimiento claro de subida o bajada).

## 5. Problema Actual y Objetivo

Actualmente, el `target` casi siempre resulta en una sola clase (principalmente 0), lo que impide el entrenamiento del modelo de Machine Learning. El objetivo es que la lógica y los datos produzcan una distribución más equitativa de las clases (1, -1, 0) para permitir un entrenamiento efectivo.

---

Este archivo es lo que necesito para tu `ml_target_definition.md`. Una vez que lo haya asimilado, tendremos tu conceptualización del `target` y podremos compararla directamente con los datos cuando me subas el `sample_binance_raw_data.csv`.
