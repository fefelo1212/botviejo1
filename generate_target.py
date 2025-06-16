import pandas as pd
import numpy as np

# Parámetros ajustables
N = 5  # Número de velas hacia adelante
up_thresh = 0.002  # 0.2% para compra
down_thresh = 0.002  # 0.2% para venta

# Cargar el dataset original
df = pd.read_csv('SOLUSDT_technical_analysis.csv')

# Lógica lookahead
future_return = (df['close'].shift(-N) - df['close']) / df['close']
df['target'] = np.select(
    [future_return > up_thresh,
     future_return < -down_thresh],
    [1, -1],
    default=0
)

# Guardar el nuevo archivo
df.to_csv('SOLUSDT_ml_dataset.csv', index=False)
print("Archivo generado: SOLUSDT_ml_dataset.csv con columna 'target'")