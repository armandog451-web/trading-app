# RECONCILIACIÓN CONTABLE DE COSTES TRANSACCIONALES (FASE 7.1A)
## DESCOMPOSICIÓN FORENSE: TRUE GROSS PNL, SLIPPAGE, COMISIONES Y NET PNL

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fase:** 7.1A — Auditoría Contable y Forense de Ejecución  
**Estado:** **RECONCILIACIÓN COMPLETA Y VERIFICADA AL CÉNTIMO**  

---

## 1. IDENTIFICACIÓN DEL DEFECTO CONTABLE ORIGINAL

En la auditoría de la Fase 7.1 se identificó una ambigüedad metodológica en la denominación y cómputo de las métricas de beneficio:

### Defecto en el Código (`fase7_1_audit_engine.py`):
```python
fill_price = curr_bar.close * (1.0 + slippage_rate)
exit_fill = curr_bar.close * (1.0 - slippage_rate)
gross = (exit_fill - entry_price) * shares
comm = (commission_per_share * shares) * 2.0
slip = (entry_price * slippage_rate + exit_fill * slippage_rate) * shares
net = gross - comm
```

### Diagnóstico Forense:
1. **El Slippage ya estaba dentro de `gross`:** Dado que `entry_price` y `exit_fill` se calcularon incorporando el deslizamiento (+5 bps en compra, -5 bps en venta), la variable `gross` no representaba la ganancia bruta al precio medio de mercado, sino el **PnL de ejecución post-deslizamiento**.
2. **Error de Etiquetado en el Reporte:** En el reporte de la Fase 7.1 se presentaron:
   - "Ganancia Bruta: +\$984.71 USD"
   - "Pérdida Bruta: -\$563.32 USD"
   Estos números correspondían en realidad a la **suma de los Net PnLs ganadores** y **suma de los Net PnLs perdedores**. Se rotularon erróneamente como "Bruto", provocando una contradicción aparente:
   $$\$984.71 - \$563.32 = \$421.39$$
   Si el PnL neto reportado era exactamente +\$421.39 USD, un auditor externo legítimamente cuestionaba dónde se habían deducido los \$138.16 USD de costes.
3. **Ausencia de Doble Deducción en el Resultado Final:** En la fórmula `net = gross - comm`, el slippage se dedujo **una sola vez** (vía precios de ejecución) y las comisiones se restaron una vez. El número final de Net PnL (+\$421.39 USD) era correcto, pero la descomposición contable y el desglose de costes estaban profundamente distorsionados.

---

## 2. MARCO CONTABLE INSTITUCIONAL CORREGIDO

Para eliminar cualquier ambigüedad, se adopta el estándar contable institucional:

$$\text{True Gross PnL} = (P_{\text{exit}}^{\text{mid}} - P_{\text{entry}}^{\text{mid}}) \times \text{Shares}$$

$$\text{Slippage USD} = \left[(P_{\text{entry}}^{\text{fill}} - P_{\text{entry}}^{\text{mid}}) + (P_{\text{exit}}^{\text{mid}} - P_{\text{exit}}^{\text{fill}})\right] \times \text{Shares}$$

$$\text{Commission USD} = \text{Tasa por Acción} \times \text{Shares} \times 2$$

$$\text{True Net PnL} = \text{True Gross PnL} - \text{Slippage USD} - \text{Commission USD}$$

---

## 3. TABLA DE RECONCILIACIÓN MATEMÁTICA EXACTA

A continuación se presenta la reconciliación matemática auditable al céntimo sobre las operaciones originales:

| Concepto Contable | `MOM_TrendPullback_V1` (Filtrada - 11 Trades) | `MR_RsiBollinger_V1` (Filtrada - 18 Trades) |
| :--- | :---: | :---: |
| **Ganancia Bruta Verdadera ($\sum \text{Gross Wins}$)** | **+\$1,061.64 USD** | **+\$1,173.19 USD** |
| **Pérdida Bruta Verdadera ($\sum |\text{Gross Losses}|$ )** | **-\$502.09 USD** | **-\$908.42 USD** |
| **True Gross PnL Total** | **+\$559.55 USD** | **+\$264.77 USD** |
| **(-) Deslizamiento Total (Slippage)** | **-\$135.14 USD** | **-\$221.21 USD** |
| **(-) Comisiones Totales** | **-\$3.02 USD** | **-\$4.82 USD** |
| **(=) True Net PnL Reconciliado** | **+\$421.39 USD** | **+\$38.74 USD** |
| **Comprobación Contable:** | $\$559.55 - \$135.14 - \$3.02 = \mathbf{\$421.39}$ | $\$264.77 - \$221.21 - \$4.82 = \mathbf{\$38.74}$ |
| **Estado de Cuadre:** | **EXACTO AL CÉNTIMO (0.00 diff)** | **EXACTO AL CÉNTIMO (0.00 diff)** |

---

## 4. DISTINCIÓN ENTRE PROFIT FACTOR BRUTO Y NETO

| Métrica | `MOM_TrendPullback_V1` | `MR_RsiBollinger_V1` | Significado Cuantitativo |
| :--- | :---: | :---: | :--- |
| **Gross Profit Factor** | **2.11** | **1.29** | Eficiencia teórica de la señal antes de interactuar con el mercado. |
| **Net Profit Factor** | **1.74** | **1.04** | Rendimiento económico real tras absorber comisiones y deslizamiento. |
| **Cost Drag (% PnL Bruto)** | **24.69%** | **85.37%** | Proporción de la ganancia bruta consumida por los costes operativos. |

> **Conclusión Forense:** En Mean Reversion, el deslizamiento y las comisiones consumen el **85.37%** de todo el beneficio generado. El margen remanente ($PF = 1.04$) es financieramente inviable para su explotación en el mundo real.
