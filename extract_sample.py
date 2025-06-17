import pandas as pd
import os

# --- CONFIGURACIÓN ---
# Cambia esta línea a la ruta real de tu archivo grande en la carpeta data
INPUT_BIG_CSV_PATH = 'data/SOLUSDT_processed_big_dataset.csv'  # <--- AJUSTADO A TU ARCHIVO ORIGEN

# Nombre del archivo pequeño que se generará
OUTPUT_SAMPLE_CSV_FILENAME = 'sample_binance_raw_data.csv'

# Número de líneas a leer (incluye el encabezado, así que 50 = encabezado + 49 filas de datos)
NUM_LINES_TO_READ = 50
# --- FIN CONFIGURACIÓN ---

def extract_sample_csv(input_path: str, output_filename: str, num_lines: int):
    if not os.path.exists(input_path):
        print(f"ERROR: El archivo de entrada no se encontró en '{input_path}'")
        print("Por favor, verifica la ruta en la variable INPUT_BIG_CSV_PATH.")
        return

    try:
        # Lee solo las primeras 'num_lines' del archivo grande
        # 'nrows' lee el número de filas de datos, el encabezado se incluye automáticamente
        df_sample = pd.read_csv(input_path, nrows=num_lines - 1) # -1 porque nrows cuenta solo filas de datos, no el header

        # Guarda el DataFrame pequeño en un nuevo archivo CSV
        df_sample.to_csv(output_filename, index=False)

        print(f"✅ Se creó '{output_filename}' con las primeras {num_lines} líneas del archivo grande.")
        print(f"Ahora puedes subir '{output_filename}' a nuestra conversación.")

    except Exception as e:
        print(f"❌ Ocurrió un error al procesar el archivo: {e}")
        print("Asegúrate de que el archivo CSV esté bien formado y que la ruta sea correcta.")

if __name__ == "__main__":
    extract_sample_csv(INPUT_BIG_CSV_PATH, OUTPUT_SAMPLE_CSV_FILENAME, NUM_LINES_TO_READ)
