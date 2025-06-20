# Análisis de Resultados del Entrenamiento por Bloques (20/06/2025)

**Última actualización: 20/06/2025**

## Resumen de resultados (`resultados_bloques.csv`)
- Se procesaron 30 bloques de 1,000 filas (último bloque de 880 filas).
- El balance final por bloque oscila entre ~9,690 y ~10,005 (capital inicial: 10,000).
- El retorno porcentual (`return_pct`) aparece como 0 en todos los bloques (posible bug o falta de cálculo).
- El último bloque muestra balance 0, lo que indica un posible error en la simulación o guardado para ese bloque.

## Observaciones clave
- No se observan bloques con ganancias significativas; la mayoría muestra una leve pérdida.
- El bloque 15,000-16,000 es el único con balance >10,000, pero la diferencia es mínima.
- El balance 0 en el último bloque es anómalo y debe revisarse.

## Recomendaciones y próximos pasos
1. **Corregir el cálculo y guardado de `return_pct`** para reflejar el rendimiento real de cada bloque.
2. **Revisar el flujo del último bloque** para evitar balances nulos o errores de simulación.
3. (Opcional) Graficar los balances finales por bloque para análisis visual y detección de outliers.
4. Analizar si la estrategia adaptativa necesita ajustes, ya que no está generando ganancias en el histórico actual.
5. Seguir documentando avances y experimentos en la carpeta `info`.
6. Hacer commit y push de todos los cambios para dejar el trabajo protegido y versionado.

---

_Este análisis deja trazabilidad clara y recomendaciones para el próximo ciclo de trabajo._
