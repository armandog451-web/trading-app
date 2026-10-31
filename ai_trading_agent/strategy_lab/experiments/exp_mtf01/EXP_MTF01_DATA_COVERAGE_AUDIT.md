# ORACLEBOT V2 — EXP-MTF01 AUDITORÍA DE COBERTURA DE DATOS
## Verificación Empírica de Profundidad Histórica D1, H1 y M5

| Símbolo | TF | Periodo Consultado | Barras Reales | Fecha Inicio | Fecha Fin | Estado de Cobertura |
|---|---|---|---|---|---|---|
| SPY | D1 | 5y | 1255 | 2021-11-01 | 2026-10-30 | SUFFICIENT (5y) |
| SPY | H1 | 730d | 5076 | 2023-12-04 14:30 | 2026-10-30 19:30 | SUFFICIENT (730d) |
| SPY | M5 | 60d | 4680 | 2026-08-07 13:30 | 2026-10-30 19:55 | REAL_M5_WINDOW_LIMITED (60d) |
| QQQ | D1 | 5y | 1255 | 2021-11-01 | 2026-10-30 | SUFFICIENT (5y) |
| QQQ | H1 | 730d | 5077 | 2023-12-04 14:30 | 2026-10-30 19:30 | SUFFICIENT (730d) |
| QQQ | M5 | 60d | 4680 | 2026-08-07 13:30 | 2026-10-30 19:55 | REAL_M5_WINDOW_LIMITED (60d) |
| DIA | D1 | 5y | 1255 | 2021-11-01 | 2026-10-30 | SUFFICIENT (5y) |
| DIA | H1 | 730d | 5076 | 2023-12-04 14:30 | 2026-10-30 19:30 | SUFFICIENT (730d) |
| DIA | M5 | 60d | 4680 | 2026-08-07 13:30 | 2026-10-30 19:55 | REAL_M5_WINDOW_LIMITED (60d) |
| IWM | D1 | 5y | 1255 | 2021-11-01 | 2026-10-30 | SUFFICIENT (5y) |
| IWM | H1 | 730d | 5076 | 2023-12-04 14:30 | 2026-10-30 19:30 | SUFFICIENT (730d) |
| IWM | M5 | 60d | 4680 | 2026-08-07 13:30 | 2026-10-30 19:55 | REAL_M5_WINDOW_LIMITED (60d) |
| GLD | D1 | 5y | 1255 | 2021-11-01 | 2026-10-30 | SUFFICIENT (5y) |
| GLD | H1 | 730d | 5076 | 2023-12-04 14:30 | 2026-10-30 19:30 | SUFFICIENT (730d) |
| GLD | M5 | 60d | 4680 | 2026-08-07 13:30 | 2026-10-30 19:55 | REAL_M5_WINDOW_LIMITED (60d) |
| TLT | D1 | 5y | 1255 | 2021-11-01 | 2026-10-30 | SUFFICIENT (5y) |
| TLT | H1 | 730d | 5077 | 2023-12-04 14:30 | 2026-10-30 19:30 | SUFFICIENT (730d) |
| TLT | M5 | 60d | 4680 | 2026-08-07 13:30 | 2026-10-30 19:55 | REAL_M5_WINDOW_LIMITED (60d) |

## Hallazgos Críticos de Disponibilidad de Datos

1. **Disponibilidad D1 y H1:** Los datos diarios (D1) y horarios (H1) presentan suficiente profundidad histórica (1,250+ barras diarias y 4,500+ barras horarias para los 6 ETFs).
2. **Limitación Estructural M5 (60 días):** Las APIs gratuitas de Yahoo Finance limitan estrictamente las consultas de datos intradía de 5 minutos a un máximo de 60 días naturales retrospectivos (~4,500 barras por activo).
3. **Ventana de Solapamiento Causal Multitemporal Conjunta (D1 + H1 + M5):**
   - La evaluación conjunta con las tres temporalidades activas simultáneamente abarca un horizonte real de aproximadamente 60 días calendario (unas 8 semanas de negociación bursátil).
   - Conforme a las reglas del Brief Maestro (Secciones 9.3 y 11.1), está estrictamente prohibido generar barras M5 sintéticas o interpoladas para inflar la muestra histórica.
   - Todo trade ejecutado en M5 debe auditarse exclusivamente sobre barras reales de mercado dentro de dicha ventana.
   - Si la frecuencia de señales produce una muestra de trades inferior al umbral de suficiencia estadística (< 30 operaciones), el resultado debe etiquetarse honestamente como `INSUFFICIENT_EVIDENCE` / `INSUFFICIENT_DATA`.
