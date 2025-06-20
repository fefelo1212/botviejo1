"""
Módulo adaptador para estrategias clásicas.
Permite que cualquier función de estrategia que devuelva solo una Serie de señales sea compatible con motores de backtesting que esperan (signal, reason).
"""

def wrap_estrategia(fn, params):
    """
    Devuelve una función que llama a la estrategia y retorna (signal, None), compatible con motores que esperan dos valores.
    """
    def wrapper(df, **kwargs):
        signal = fn(df, **params)
        return signal, None
    return wrapper
