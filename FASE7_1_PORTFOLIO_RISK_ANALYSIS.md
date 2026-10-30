# ANÁLISIS DE RIESGO DE CARTERA AISLADA (FASE 7.1)
## COMBINACIÓN TEÓRICA MOMENTUM + MEAN REVERSION Y AISLAMIENTO DE D21

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.1 — Auditoría de Cartera Multiestrategia Aislada  
**Composición de Cartera Teórica:**  
- 50% Asignación Teórica: `MOM_TrendPullback_V1` (Régimen `TRENDING_BULL`)  
- 50% Asignación Teórica: `MR_RsiBollinger_V1` (Régimen `RANGING`)  
**Capital Teórico Aislado:** \$100,000 USD (Virtual de Laboratorio)  
**Libro Contable de D21:** **ESTRICTAMENTE SEPARADO ($1,000,000 USD PAPER INTACTO)**  

---

## 1. DESEMPEÑO DE LA CARTERA TEÓRICA COMBINADA

Al fusionar cronológicamente las 29 operaciones ejecutadas por ambas estrategias sobre el benchmark de 1,200 barras, se obtienen las siguientes métricas agregadas:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   MÉTRICAS DE LA CARTERA TEÓRICA (MOM + MR)                      │
├────────────────────────────────────────┬─────────────────────────────────────────┤
│ Operaciones Totales:        29 trades  │ Profit Factor Agregado:      1.29       │
│ Operaciones Ganadoras:      13 (44.8%) │ Sharpe Ratio Anualizado:     0.67       │
│ Operaciones Perdedoras:     16 (55.2%) │ Sortino Ratio Anualizado:    1.39       │
│ Ganancia Media por Ganador: $157.84    │ Expectativa Neta por Trade:  +$15.87    │
│ Pérdida Media por Perdedor: $99.49     │ Retorno en R Medio:          +0.063 R   │
│ Máximo Drawdown Combinado:  $641.95    │ Máximo Drawdown Relativo:    0.64%      │
│ Exposición Temporal Total:  8.92%      │ Factor de Recuperación:      0.72       │
│ PnL Neto Agregado:         +$460.13    │ Costes Totales Absorbidos:   $364.19    │
└────────────────────────────────────────┴─────────────────────────────────────────┘
```

---

## 2. ANÁLISIS DE CORRELACIÓN Y CONCURRENCIA

1. **Ortogonalidad Operativa Estricta:**
   - La correlación de señales entre Momentum y Mean Reversion es **exactamente 0.00**.
   - **Razón Arquitectónica:** Al estar condicionadas a regímenes mutuamente excluyentes (`TRENDING_BULL` vs `RANGING`), **es físicamente imposible que ambas estrategias emitan órdenes o mantengan posiciones simultáneamente**.
   - Concurrencia Máxima de Posiciones: **1 posición**. Jamás se produjo colisión ni competencia por margen o poder de compra.
2. **Efecto de Diversificación vs Efecto Arrastre (Drag):**
   - Aunque la diversificación temporal es perfecta, la inclusión de `MR_RsiBollinger_V1` actuó como un **freno significativo sobre la rentabilidad**:
     - Momentum por sí sola: Sharpe = **1.38**, Profit Factor = **1.74**.
     - Cartera Combinada: Sharpe cae a **0.67**, Profit Factor cae a **1.29**.
   - Mean Reversion aportó 18 operaciones de alta rotación que absorbieron \$226.03 USD en comisiones y slippage para generar un beneficio neto insignificante de +\$38.74 USD, reduciendo la eficiencia global de la cartera.

---

## 3. AISLAMIENTO ABSOLUTO RESPECTO A D21 Y MOOMOO PAPER

Para garantizar la integridad del sistema operativo consolidado:
1. **Libro Contable Independiente:** Las 29 operaciones de la cartera teórica residen exclusivamente en [`ai_trading_agent/scratch/fase7_1_audit_manifest.json`](file:///C:/Users/edsel/OneDrive/Documents/trading-app-repo/ai_trading_agent/scratch/fase7_1_audit_manifest.json).
2. **Cero Impacto en SQLite de Producción:** Las tablas `signals`, `orders`, `paper_trades` y `strategy_metrics` no fueron tocadas.
3. **Cero Conexión al Broker:** Ni Moomoo Open API ni adaptadores PAPER recibieron paquetes de red provenientes de esta cartera.
4. **Independencia de Capital:** El capital virtual de $1,000,000 USD de D21 permanece 100% preservado para la campaña prospectiva oficial.
