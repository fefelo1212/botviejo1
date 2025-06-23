import pandas as pd
import numpy as np
from classic_strategies import ClassicStrategy, AdaptiveStrategy
from modulo_intermediador import adaptar_binance_a_backtesting
from backtesting import BacktestEngine
import csv
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EstrategiaWrapper:
    """
    Clase para adaptar las funciones de estrategia a un formato compatible con BacktestEngine.
    """
    @staticmethod
    def wrap(fn, params):
        """
        Envuelve una función de estrategia clásica para que retorne (signal, reason).
        """
        def strategy_fn(df_block):
            # Asume que la función fn toma el DataFrame y los parámetros directamente
            # y devuelve una Serie de señales (-1, 0, 1)
            signal_series = fn(df_block, **params)
            
            # El BacktestEngine espera un solo valor para la última vela del bloque.
            signal = signal_series.iloc[-1] if not signal_series.empty else 0
            reason = None # En esta fase, la razón es simplificada, podríamos añadirla más tarde
            return signal, reason
        return strategy_fn

class CerebroAdaptativo:
    """
    Cerebro Adaptativo para Trading
    - Usa el histórico para elegir la mejor estrategia y parámetros.
    - Recibe datos en tiempo real y aplica la estrategia óptima.
    - Simula operaciones y reoptimiza si la rentabilidad baja.
    - Se conecta a los módulos existentes (backtesting, estrategias, adaptador de datos).
    """
    def __init__(self, ruta_csv_historico, modo="simulacion"):
        self.ruta_csv_historico = ruta_csv_historico
        self.modo = modo
        self.estrategia_optima = None
        self.parametros_optimos = None
        self.resultados = None
        # La inicialización del df_historico_completo se hace en el main para optimización
        logging.info(f"Cerebro Adaptativo inicializado en modo: {self.modo}")

    def _inicializar(self):
        # Este método no se usará directamente para cargar el DF completo en init
        # ahora que la carga se hace en el main para la optimización.
        # Si se usa para otra cosa, mantenerlo.
        pass
    
    def procesar_dato_tiempo_real(self, df_actual: pd.DataFrame):
        """
        Procesa un nuevo dato en tiempo real usando la estrategia óptima.
        Args:
            df_actual (pd.DataFrame): DataFrame con los últimos datos de mercado (ej. últimas N velas).
        """
        if self.estrategia_optima is None or self.parametros_optimos is None:
            logging.warning("No hay estrategia óptima seleccionada. Ejecute la optimización primero.")
            return 0, "No_Optima_Strategy"

        logging.info(f"Procesando dato en tiempo real con estrategia {self.estrategia_optima} y parámetros {self.parametros_optimos}")

        # Aquí necesitas adaptar cómo tu estrategia usa el df_actual.
        # Por ahora, simularemos la señal usando el último dato del df_actual.
        # Esto es un placeholder; la estrategia real necesitaría un historial para calcular indicadores.
        
        # Necesitamos la función de estrategia envuelta para el uso "en vivo"
        # Esto asume que ClassicStrategy.moving_average_crossover puede tomar un DataFrame
        if self.estrategia_optima == 'moving_average_crossover':
            # Asegúrate de que df_actual tenga suficientes datos para el cálculo de MA
            if len(df_actual) < max(self.parametros_optimos['fast_period'], self.parametros_optimos['slow_period']):
                logging.warning(f"DataFrame demasiado corto ({len(df_actual)} filas) para calcular MA con periodos {self.parametros_optimos['fast_period']}, {self.parametros_optimos['slow_period']}.")
                return 0, "Insufficient_Data"

            # La estrategia MA Crossover espera una Serie de 'close'
            signals = ClassicStrategy.moving_average_crossover(
                df_actual['close'],
                self.parametros_optimos['fast_period'],
                self.parametros_optimos['slow_period']
            )
            signal = signals.iloc[-1] if not signals.empty else 0
            reason = "MAC_Signal" # Puedes refinar esto
        else:
            logging.warning(f"Estrategia {self.estrategia_optima} no implementada para procesamiento en tiempo real.")
            signal = 0
            reason = "Strategy_Not_Implemented"

        logging.info(f"Señal generada: {signal} (Razón: {reason})")
        return signal, reason

    def entrenar_por_bloques(self, df_historico: pd.DataFrame, tamano_bloque: int = 1000, ruta_resultados: str = 'resultados_bloques.csv'):
        """
        Realiza un backtesting por bloques sobre el histórico para evaluar una estrategia fija.
        (Este método se mantiene, pero la optimización usa un flujo diferente para probar múltiples parámetros.)
        """
        logging.info(f"[CEREBRO] Iniciando entrenamiento por bloques con tamaño {tamano_bloque}...")
        
        # Asegurarse de que el directorio para resultados_bloques.csv exista
        output_dir = os.path.dirname(ruta_resultados)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        resultados = []
        with open(ruta_resultados, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['start_row', 'end_row', 'return_pct', 'final_balance'])

            for i in range(0, len(df_historico), tamano_bloque):
                start = i
                end = min(i + tamano_bloque, len(df_historico))
                df_bloque = df_historico.iloc[start:end].copy()

                if df_bloque.empty:
                    continue
                
                logging.debug(f"Tamaño de df_bloque para backtest: {len(df_bloque)} filas")

                # Aquí se usa una estrategia fija para el entrenamiento por bloques
                # Adaptamos la estrategia MACD con parámetros fijos para esta evaluación por bloques
                def mac_fixed_strategy_fn(df_b):
                    # Usamos parámetros de ejemplo para la evaluación por bloques
                    signal_series = ClassicStrategy.moving_average_crossover(df_b['close'], 10, 20)
                    return signal_series.iloc[-1] if not signal_series.empty else 0, None
                
                engine = BacktestEngine(df_bloque)
                try:
                    result = engine.run_backtest(mac_fixed_strategy_fn)
                    logging.debug(f"Resultado de BacktestEngine para bloque {start}-{end}: {result}")
                except Exception as e:
                    logging.error(f"Error en backtest para bloque {start}-{end}: {e}")
                    result = {'net_profit_percent': 0.0, 'final_balance': 0.0} # Valores por defecto en caso de error
                
                return_pct = result.get('net_profit_percent', 0.0) * 100
                balance_final = result.get('final_balance', 0.0)

                logging.info(f"[CEREBRO][BLOQUE] Filas {start}-{end}: Retorno={return_pct:.2f}% | Balance final={balance_final:.2f}")
                writer.writerow([start, end, return_pct, balance_final])
                resultados.append((start, end, return_pct, balance_final))
        logging.info(f"[CEREBRO] Entrenamiento por bloques finalizado. Bloques evaluados: {len(resultados)}")
        logging.info(f"[CEREBRO] Resultados guardados en {ruta_resultados}")
        return resultados

    def reoptimizar_si_es_necesario(self):
        """
        Lógica para reoptimizar si la rentabilidad baja o las condiciones de mercado cambian.
        (Por ahora es un placeholder, pero es donde llamarías a optimizar_estrategia de nuevo).
        """
        logging.info("Reoptimización no implementada en esta versión.")

    def optimizar_estrategia(self, df_historico: pd.DataFrame, ruta_optimizacion: str = 'resultados_optimizacion.csv'):
        """
        Optimiza una estrategia probando diferentes combinaciones de parámetros.
        Guarda los resultados y reporta la mejor combinación.
        """
        logging.info(f"[CEREBRO] Iniciando optimización de estrategia...")

        # Asegurarse de que el directorio para resultados_optimizacion.csv exista
        output_dir = os.path.dirname(ruta_optimizacion)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Encabezados para el archivo CSV de resultados de optimización
        encabezados = ['strategy_name', 'fast_period', 'slow_period', 'return_pct', 'sharpe_ratio', 'final_balance', 'total_trades', 'win_rate']
        
        best_strategy_name = None
        best_params = {}
        best_return_pct = -np.inf # Inicializar con un valor muy bajo
        best_sharpe_ratio = -np.inf # Inicializar con un valor muy bajo
        
        with open(ruta_optimizacion, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(encabezados) # Escribir encabezados
            
            # --- Estrategias y parámetros a optimizar (Fase 1: Simplificado) ---
            # Vamos a empezar con Moving Average Crossover, con rangos pequeños
            
            logging.info("[CEREBRO] Probando estrategia: Moving Average Crossover")
            
            # Puedes ajustar estos rangos para más o menos pruebas
            # Para la fase simplificada, mantenlos pequeños
            fast_periods = [5, 10, 15] # Prueba estos periodos para la MA rápida
            slow_periods = [20, 30, 40] # Prueba estos periodos para la MA lenta

            total_combinations = 0
            for fast_p in fast_periods:
                for slow_p in slow_periods:
                    if fast_p < slow_p:
                        total_combinations += 1
            
            current_combination = 0

            for fast_p in fast_periods:
                for slow_p in slow_periods:
                    
                    if fast_p >= slow_p:
                        # logging.info(f"Saltando combinación (fast={fast_p}, slow={slow_p}) donde fast >= slow.")
                        continue # La media rápida debe ser menor que la lenta
                    
                    current_combination += 1
                    logging.info(f"[CEREBRO][OPTIMIZACION] Probando MACD con fast={fast_p}, slow={slow_p} ({current_combination}/{total_combinations} completado)")

                    # Definir la función de estrategia para el BacktestEngine
                    # Esta función debe tomar un DataFrame y retornar (signal, reason)
                    # Asegúrate de que df_block tiene suficientes datos para el cálculo de MA
                    min_len_needed = max(fast_p, slow_p)
                    if len(df_historico) < min_len_needed:
                        logging.warning(f"DataFrame histórico demasiado corto ({len(df_historico)} filas) para calcular MA con periodos {fast_p}, {slow_p}. Saltando combinación.")
                        # Si no hay suficientes datos para esta combinación de parámetros, se salta
                        return_pct, sharpe_ratio, final_balance, total_trades, win_rate = 0.0, -np.inf, 0.0, 0, 0.0
                        writer.writerow(['moving_average_crossover', fast_p, slow_p, return_pct, sharpe_ratio, final_balance, total_trades, win_rate])
                        continue

                    # La función ClassicStrategy.moving_average_crossover espera solo la serie 'close'
                    def mac_strategy_fn(df_block_for_backtest):
                        # Asegúrate de que tu ClassicStrategy.moving_average_crossover
                        # pueda manejar el DataFrame directamente o solo la columna 'close'.
                        # Asume que devuelve una Serie con -1, 0, 1
                        # Enviamos solo la columna 'close' para el cálculo de indicadores.
                        signal_series = ClassicStrategy.moving_average_crossover(df_block_for_backtest['close'], fast_p, slow_p)
                        # El BacktestEngine espera un solo valor para la última vela del bloque.
                        signal = signal_series.iloc[-1] if not signal_series.empty else 0
                        return signal, None # Retornamos la señal y una razón vacía

                    engine = BacktestEngine(df_historico.copy()) # Usamos una copia para no modificar el original
                    
                    try:
                        result = engine.run_backtest(mac_strategy_fn)
                    except Exception as e:
                        logging.error(f"[CEREBRO] Error en backtest para MACD con fast={fast_p}, slow={slow_p}: {e}")
                        # Si hay un error, registra un mal resultado para esta combinación
                        result = {'net_profit_percent': -100.0, 'sharpe_ratio': -100.0, 'final_balance': 0.0, 'total_trades': 0, 'win_rate': 0.0}
                    
                    return_pct = result.get('net_profit_percent', 0.0) * 100
                    sharpe_ratio = result.get('sharpe_ratio', -np.inf)
                    final_balance = result.get('final_balance', 0.0)
                    total_trades = result.get('total_trades', 0)
                    win_rate = result.get('win_rate', 0.0)

                    logging.info(f"  -> Resultado: Retorno={return_pct:.2f}%, Sharpe={sharpe_ratio:.2f}, Balance={final_balance:.2f}")

                    # Guardar resultados en el CSV
                    writer.writerow(['moving_average_crossover', fast_p, slow_p, return_pct, sharpe_ratio, final_balance, total_trades, win_rate])

                    # Actualizar la mejor combinación si encontramos una mejor
                    # Priorizamos Sharpe Ratio, luego Retorno
                    if sharpe_ratio > best_sharpe_ratio:
                        best_sharpe_ratio = sharpe_ratio
                        best_return_pct = return_pct
                        best_strategy_name = 'moving_average_crossover'
                        best_params = {'fast_period': fast_p, 'slow_period': slow_p}
                    elif sharpe_ratio == best_sharpe_ratio and return_pct > best_return_pct:
                         best_return_pct = return_pct
                         best_strategy_name = 'moving_average_crossover'
                         best_params = {'fast_period': fast_p, 'slow_period': slow_p}


        logging.info("[CEREBRO] Optimización de estrategia finalizada.")
        if best_strategy_name:
            logging.info(f"¡Mejor estrategia encontrada: {best_strategy_name} con parámetros {best_params}!")
            logging.info(f"  Retorno: {best_return_pct:.2f}% | Sharpe Ratio: {best_sharpe_ratio:.2f}")
            self.estrategia_optima = best_strategy_name
            self.parametros_optimos = best_params
        else:
            logging.warning("No se encontró una estrategia óptima (todos los backtests fallaron o no hubo resultados).")


# Modificación en el bloque principal para ejecutar la optimización simplificada
if __name__ == "__main__":
    cerebro = CerebroAdaptativo("processed_data/SOLUSDT_full_concat.csv")
    
    # --- FASE 1: Optimización Simplificada ---
    logging.info("--- Iniciando FASE 1: Optimización Simplificada (con datos limitados) ---")
    
    df_full_historico = adaptar_binance_a_backtesting("processed_data/SOLUSDT_full_concat.csv")
    
    # Limitar las filas para la fase simplificada (ej. las primeras 5000 filas)
    # df_historico_simplificado = df_full_historico.head(5000)  # Línea comentada para usar todo el histórico
    df_historico_simplificado = df_full_historico  # Usar todo el histórico para la optimización
    
    if df_historico_simplificado.empty:
        logging.error("DataFrame histórico simplificado está vacío. Asegúrate de que 'SOLUSDT_full_concat.csv' exista y tenga datos.")
    else:
        cerebro.optimizar_estrategia(df_historico_simplificado, 'resultados_optimizacion_simplificada.csv')
    
    logging.info("--- FASE 1 Completada. Revisa 'resultados_optimizacion_simplificada.csv' ---")

    # --- FASE 2: Optimización a Gran Escala (Descomentar cuando la Fase 1 sea exitosa) ---
    # logging.info("--- Iniciando FASE 2: Optimización a Gran Escala (con todos los datos) ---")
    # if df_full_historico.empty:
    #     logging.error("DataFrame histórico completo está vacío. Asegúrate de que 'SOLUSDT_full_concat.csv' exista y tenga datos.")
    # else:
    #     # Aquí podrías ajustar los rangos de parámetros para ser más amplios
    #     # o añadir más estrategias a la optimización
    #     cerebro.optimizar_estrategia(df_full_historico, 'resultados_optimizacion_completa.csv')
    # logging.info("--- FASE 2 Completada. Revisa 'resultados_optimizacion_completa.csv' ---")

    # Ahora puedes usar cerebro.estrategia_optima y cerebro.parametros_optimos
    # para procesar datos en tiempo real si lo deseas.
    # Por ejemplo:
    # if cerebro.estrategia_optima:
    #     logging.info(f"Usando la estrategia óptima: {cerebro.estrategia_optima} con {cerebro.parametros_optimos} para simulación en tiempo real.")
    #     # Simulación de dato en tiempo real (puedes pasarle los últimos datos del DF)
    #     # df_dato_tiempo_real = df_full_historico.tail(200) # Últimas N velas para calcular indicadores
    #     # cerebro.procesar_dato_tiempo_real(df_dato_tiempo_real)
