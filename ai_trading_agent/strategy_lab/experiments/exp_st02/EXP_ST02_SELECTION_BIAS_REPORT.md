# ENTREGABLE 06 — AUDITORÍA FORMAL DE SESGO DE SELECCIÓN
## Hipótesis H5 (Adaptive Trailing Stop) | Protocolo Institucional

**Fecha:** 2026-10-31 10:43:06 UTC  
**Dictamen de Sesgo:** `HISTORICAL_HOLDOUT_NOT_INDEPENDENT`  

---

### 1. DECLARACIÓN OBLIGATORIA DE SNOOPING BIAS

1. **Génesis de H5:** En la fase EXP-ST01 se evaluaron cinco hipótesis cuantitativas (H1: ADX, H2: RVOL, H3: ATR Expansion, H4: Session Timing, H5: Adaptive Trailing Stop).
2. **Selección Post-Hoc:** H5 fue seleccionada porque demostró superioridad sobre el dataset 2018–2026 respecto a las otras cuatro hipótesis rechazadas.
3. **Contaminación de Muestras OOS Históricas:**
   - Debido a que la formulación de H5 se validó sobre los mismos datos históricos donde se observó el fallo de H1-H4, **ninguna partición histórica adicional dentro de este rango puede considerarse estadísticamente no examinada**.
   - Se emite la declaración canónica: `HISTORICAL_HOLDOUT_NOT_INDEPENDENT`.

---

### 2. PROTOCOLO DE REMEDIACIÓN INSTITUCIONAL

- **Prohibición de Declaración `CONFIRMED`:** Queda prohibido declarar a H5 como una ventaja confirmada basándose únicamente en la evidencia retrospectiva de EXP-ST01.
- **Vía Única de Certificación:** H5 sólo podrá ser confirmada mediante observación prospectiva autónoma en la campaña Frozen Forward Shadow (`CAMP-SHADOW-EXP-ST02-2026`), operando sobre barras cerradas estrictamente posteriores a su momento real de activación $T_0$.
