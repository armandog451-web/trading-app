# ENTREGABLE 03 — AUDITORÍA DE COBERTURA HISTÓRICA Y CONCILIACIÓN
## Matriz de 50 Backtests (10 ETFs x 5 Temporalidades)

**Fecha:** 2026-10-31 11:16:08 UTC  
**Total Combinaciones:** 50  
**Total Trades Conciliados:** 1072  
**Estado:** CONCILIADO Y VÁLIDO  

---

### 1. DESGLOSE POR TEMPORALIDAD Y CRITERIO DE SUFICIENCIA

| Temporalidad | Límite API / Fuente | Barras Típicas | Combinaciones Válidas | Combinaciones Insuficientes | Trades Acumulados | Justificación Técnica |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **M15** | Yahoo Finance | 134 trades | 4 | 6 | 134 | Regla: Muestra >= 15 trades y barras suficientes |
| **M30** | Yahoo Finance | 67 trades | 0 | 10 | 67 | Regla: Muestra >= 15 trades y barras suficientes |
| **H1** | Yahoo Finance | 544 trades | 10 | 0 | 544 | Regla: Muestra >= 15 trades y barras suficientes |
| **H4** | Yahoo Finance | 107 trades | 1 | 9 | 107 | Regla: Muestra >= 15 trades y barras suficientes |
| **D1** | Yahoo Finance | 220 trades | 10 | 0 | 220 | Regla: Muestra >= 15 trades y barras suficientes |

---

### 2. RECONCILIACIÓN ESTADÍSTICA

- **Combinaciones con Muestra Suficiente (VALID):** 25 / 50 (D1: 10, H1: 10, H4: 1, M15: 4, M30: 0).
- **Combinaciones Insuficientes (INSUFFICIENT_DATA):** 25 / 50.
- **Transparencia Científica:** Cumplimiento estricto de la Sección 5.3: no se inventaron datos ni se aplicó interpolación ficticia para inflar artificialmente la muestra en M15 o M30.
