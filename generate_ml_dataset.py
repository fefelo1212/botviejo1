"""
Script para generar un dataset con columna 'target' para ML a partir de SOLUSDT_technical_analysis.csv.
La columna 'target' será:
- 1 si el precio de cierre sube más de 0.1% en la próxima vela
- -1 si baja más de 0.1%
- 0 si se mantiene
"""
import pandas as pd

# Cargar datos
input_file = 'SOLUSDT_technical_analysis.csv'
df = pd.read_csv(input_file)

# Calcular el cambio porcentual de la siguiente vela
df['future_close'] = df['close'].shift(-1)
df['change_pct'] = (df['future_close'] - df['close']) / df['close']

# Definir target
threshold = 0.001  # 0.1%
def get_target(change):
    if change > threshold:
        return 1
    elif change < -threshold:
        return -1
    else:
        return 0

df['target'] = df['change_pct'].apply(get_target)

# Eliminar la última fila (sin futuro)
df = df.iloc[:-1]

# Guardar nuevo dataset
output_file = 'SOLUSDT_ml_dataset.csv'
df.to_csv(output_file, index=False)
print(f"Dataset ML guardado en {output_file}")
