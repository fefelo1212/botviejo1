"""
Cerebro Adaptativo para Trading
- Usa el histórico para elegir la mejor estrategia y parámetros.
- Recibe datos en tiempo real y aplica la estrategia óptima.
- Simula operaciones y reoptimiza si la rentabilidad baja.
- Se conecta a los módulos existentes (backtesting, estrategias, adaptador de datos).
"""

import pandas as pd
from classic_strategies import ClassicStrategy, AdaptiveStrategy
from modulo_intermediador import adaptar_binance_a_backtesting
from backtesting import BacktestEngine

def estrategia_wrapper(fn, params):
    """Adapta una función de estrategia clásica para que retorne (signal, reason)"""
    def wrapped(df, **kwargs):
        signal = fn(df, **params)
        reason = None
        return signal, reason
    return wrapped

class EstrategiaWrapper:
    @staticmethod
    def wrap(fn, params):
        def strategy_fn(df):
            signal = fn(df, **params)
            return signal, None  # El motor espera dos valores
        return strategy_fn

class CerebroAdaptativo:
    def __init__(self, ruta_csv_historico, modo="simulacion"):
        self.ruta_csv_historico = ruta_csv_historico
        self.modo = modo
        self.estrategia_optima = None
        self.parametros_optimos = None
        self.resultados = None
        self._inicializar()

    def _wrap_strategy(self, fn, params):
        # Devuelve una función que retorna (signal escalar, None)
        def wrapped(df_in):
            serie = fn(df_in, **params)
            # Si es Serie, devolver el último valor; si ya es escalar, devolverlo
            if hasattr(serie, 'iloc'):
                return serie.iloc[-1] if not serie.empty else 0, None
            return serie, None
        return wrapped

    def _inicializar(self):
        print("[CEREBRO] Iniciando optimización de estrategias...")
        # Cargar y adaptar histórico
        df = adaptar_binance_a_backtesting(self.ruta_csv_historico)
        print(f"[CEREBRO] DataFrame histórico: filas={len(df)} columnas={list(df.columns) if isinstance(df, pd.DataFrame) else 'N/A'}")
        print(f"[CEREBRO] Primeras filas:\n{df.head(10) if isinstance(df, pd.DataFrame) else df}")
        # Limitar a las primeras 200 filas para debug rápido
        df = df.head(200)
        if not isinstance(df, pd.DataFrame) or df.empty:
            print("[CEREBRO] No se pudo cargar el histórico.")
            raise Exception("No se pudo cargar el histórico.")
        # Probar solo una estrategia y un set de parámetros
        nombre = "moving_average_crossover"
        fn = ClassicStrategy.moving_average_crossover
        params = {"fast_period": 5, "slow_period": 20}
        print(f"[CEREBRO] Probando {nombre} con params {params}")
        engine = BacktestEngine(initial_balance=10000.0)
        engine.data = df.copy()
        strat_fn = self._wrap_strategy(fn, params)
        result = engine.run_backtest(strat_fn)
        print(f"[CEREBRO] Resultado para {nombre} {params}: {result}")
        self.estrategia_optima = nombre
        self.parametros_optimos = params
        self.resultados = result
        print(f"[CEREBRO] Mejor estrategia: {nombre} | Params: {params} | Return: {result.get('return_pct', 0):.2f}%")
        # Probar la estrategia adaptativa
        nombre = "adaptive_strategy"
        fn = AdaptiveStrategy.get_adaptive_strategy
        params = {}
        print(f"[CEREBRO] Probando {nombre}")
        engine = BacktestEngine(initial_balance=10000.0)
        engine.data = df.copy()
        # La función adaptativa devuelve una Serie, hay que adaptarla a (signal, None)
        def strat_fn(dfin):
            serie = fn(dfin)
            # Si es Serie, devolver el último valor; si ya es escalar, devolverlo
            if hasattr(serie, 'iloc'):
                return serie.iloc[-1] if not serie.empty else 0, None
            return serie, None
        result = engine.run_backtest(strat_fn)
        print(f"[CEREBRO] Resultado para {nombre}: {result}")
        self.estrategia_optima = nombre
        self.parametros_optimos = params
        self.resultados = result
        print(f"[CEREBRO] Mejor estrategia: {nombre} | Return: {result.get('return_pct', 0):.2f}%")

    def procesar_dato_tiempo_real(self, df_nuevo):
        # df_nuevo: DataFrame con una o varias filas nuevas (ya adaptado)
        # Aplica la estrategia óptima y simula operación
        if self.estrategia_optima == "adaptive_strategy":
            serie = AdaptiveStrategy.get_adaptive_strategy(df_nuevo)
            signal = serie.iloc[-1] if hasattr(serie, 'iloc') and not serie.empty else 0
        else:
            fn = getattr(ClassicStrategy, self.estrategia_optima)
            signal = fn(df_nuevo, **self.parametros_optimos).iloc[-1]
        print(f"[CEREBRO] Señal generada en tiempo real: {signal}")
        return signal

    def reoptimizar_si_es_necesario(self, df_reciente):
        # Si la rentabilidad baja, reoptimiza usando los datos recientes
        # (Implementar lógica de trigger según métricas)
        pass

    def entrenar_por_bloques(self, bloque_size=1000, ruta_resultados="resultados_bloques.csv"):
        """
        Entrena la estrategia adaptativa por bloques usando todo el histórico disponible.
        Cada bloque se usa para backtesting y se imprime el resultado en español.
        Los resultados se guardan incrementalmente en un archivo CSV.
        """
        import csv
        import os
        df_full = adaptar_binance_a_backtesting(self.ruta_csv_historico)
        total = len(df_full)
        print(f"[CEREBRO] Entrenando por bloques de {bloque_size} filas (total={total})")
        resultados = []
        # Si el archivo existe, cargar los bloques ya procesados
        bloques_procesados = set()
        if os.path.exists(ruta_resultados):
            with open(ruta_resultados, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bloques_procesados.add((int(row['inicio']), int(row['fin'])))
        # Abrir el archivo en modo append
        with open(ruta_resultados, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Escribir cabecera si el archivo está vacío
            if f.tell() == 0:
                writer.writerow(["inicio", "fin", "return_pct", "balance_final"])
            for start in range(0, total, bloque_size):
                end = min(start + bloque_size, total)
                if (start, end) in bloques_procesados:
                    print(f"[CEREBRO][BLOQUE] Bloque {start}-{end} ya procesado. Saltando.")
                    continue
                df_bloque = df_full.iloc[start:end]
                if len(df_bloque) < 50:
                    print(f"[CEREBRO][BLOQUE] Bloque {start}-{end} demasiado pequeño. Saltando.")
                    continue  # Saltar bloques muy pequeños
                engine = BacktestEngine(initial_balance=10000.0)
                engine.data = df_bloque.copy()
                def strat_fn(dfin):
                    serie = AdaptiveStrategy.get_adaptive_strategy(dfin)
                    if hasattr(serie, 'iloc'):
                        return serie.iloc[-1] if not serie.empty else 0, None
                    return serie, None
                result = engine.run_backtest(strat_fn)
                return_pct = result.get('return_pct', 0)
                balance_final = result.get('final_balance', 0)
                print(f"[CEREBRO][BLOQUE] Filas {start}-{end}: Retorno={return_pct:.2f}% | Balance final={balance_final:.2f}")
                writer.writerow([start, end, return_pct, balance_final])
                resultados.append((start, end, return_pct, balance_final))
        print(f"[CEREBRO] Entrenamiento por bloques finalizado. Bloques evaluados: {len(resultados)}")
        print(f"[CEREBRO] Resultados guardados en {ruta_resultados}")
        return resultados

# Ejemplo de uso:
# cerebro = CerebroAdaptativo("processed_data/SOLUSDT_full_concat.csv")
# cerebro.procesar_dato_tiempo_real(df_nuevo)

if __name__ == "__main__":
    cerebro = CerebroAdaptativo("processed_data/SOLUSDT_full_concat.csv")
    # Simulación de dato en tiempo real SOLO con la estrategia óptima seleccionada
    import pandas as pd
    df_hist = adaptar_binance_a_backtesting("processed_data/SOLUSDT_full_concat.csv")
    df_nuevo = df_hist.tail(10)  # Simula 10 velas nuevas
    cerebro.procesar_dato_tiempo_real(df_nuevo)
    # Entrenamiento por bloques
    cerebro.entrenar_por_bloques(bloque_size=1000)
