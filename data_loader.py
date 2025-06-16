import pandas as pd
import json

def load_live_data(file_path):
    """
    Carga datos en tiempo real desde un archivo CSV.
    """
    try:
        data = pd.read_csv(file_path)
        print(f"Live data loaded successfully from {file_path}")
        return data
    except Exception as e:
        print(f"Error loading live data: {e}")
        return None

def load_trading_log(file_path):
    """
    Carga el registro de operaciones desde un archivo JSON.
    """
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        print(f"Trading log loaded successfully from {file_path}")
        return data
    except Exception as e:
        print(f"Error loading trading log: {e}")
        return None

def load_technical_analysis(file_path):
    """
    Carga datos de análisis técnico desde un archivo CSV.
    """
    try:
        data = pd.read_csv(file_path)
        print(f"Technical analysis data loaded successfully from {file_path}")
        return data
    except Exception as e:
        print(f"Error loading technical analysis data: {e}")
        return None

def preprocess_data(live_data, trading_log, technical_analysis):
    """
    Preprocesa y combina los datos cargados.
    """
    try:
        # Verificar si las columnas necesarias existen
        if 'timestamp' not in live_data.columns:
            raise KeyError("La columna 'timestamp' no está presente en SOLUSDT_live_data.csv")
        if 'timestamp' not in technical_analysis.columns:
            raise KeyError("La columna 'timestamp' no está presente en SOLUSDT_technical_analysis.csv")

        # Ejemplo de preprocesamiento: combinar datos en un DataFrame
        combined_data = pd.merge(live_data, technical_analysis, on='timestamp', how='inner')

        # Agregar información del registro de operaciones si es necesario
        if trading_log is not None:
            combined_data['trading_log'] = [trading_log] * len(combined_data)

        print("Data preprocessed successfully.")
        return combined_data
    except KeyError as ke:
        print(f"Error preprocessing data: {ke}")
        return None
    except Exception as e:
        print(f"Error preprocessing data: {e}")
        return None

# Ejemplo de uso
if __name__ == "__main__":
    live_data = load_live_data("SOLUSDT_live_data.csv")
    trading_log = load_trading_log("SOLUSDT_trading_log.json")
    technical_analysis = load_technical_analysis("SOLUSDT_technical_analysis.csv")

    combined_data = preprocess_data(live_data, trading_log, technical_analysis)
    if combined_data is not None:
        print(combined_data.head())
