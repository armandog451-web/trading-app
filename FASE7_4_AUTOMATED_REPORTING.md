# ORACLEBOT V2 — FASE 7.4
# ESPECIFICACIÓN DEL SISTEMA DE REPORTES AUTOMATIZADOS Y NOTIFICACIONES TELEGRAM (BLOQUE I)

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Módulo:** `ai_trading_agent.strategy_lab.shadow.shadow_scheduler`  
**Fecha:** 30 de octubre de 2026

---

## 1. SISTEMA DE REPORTES LOCALES AUTOMATIZADOS

El generador de informes `ShadowReportGenerator` produce periódicamente documentación auditable en Markdown y JSON estructurado sin requerir intervención manual.

### 1.1 Reporte Diario Post-Sesión (`daily_shadow_report_<date>.md`)
Se compila automáticamente al término de cada evaluación post-cierre (16:30 ET). Contiene:
1. **Encabezado Institucional:** Fecha evaluada, timestamp UTC y confirmación del modo `RESEARCH / ANALYSIS_ONLY`.
2. **Salud del Shadow Engine:** Estado operativo, escenario de costes activo y verificación de aislamiento de broker (100% air-gapped).
3. **Métricas de Candidate A (`MR_VolCond_ZScore_V1`):** Sesiones válidas acumuladas frente a la meta de 90, señales generadas, posiciones abiertas, trades cerrados, capital líquido, PnL neto realizado, Profit Factor neto, Drawdown máximo y hash del último bloque del ledger.
4. **Métricas de Candidate B (`CS_RelMom_VolAdj_V2`):** Métricas análogas de la estrategia de momentum.
5. **Auditoría de D21 Paralelo:** Confirmación de no-interferencia con la estrategia canónica en Moomoo PAPER.

### 1.2 Reporte Semanal de Auditoría Cuantitativa
Compilado durante el fin de semana, incorpora:
- Desglose acumulado de operaciones por activo.
- Comparativa del rendimiento prospectivo real frente a la línea base histórica congelada.
- Arrastre de costes acumulado (*Cost Drag %*).
- Resultado de la verificación completa de integridad del ledger (`verify_chain_integrity`).
- Progreso de los hitos del reloj forward (20, 60 y 90 sesiones).

---

## 2. ESPECIFICACIÓN DEL CANAL TELEGRAM SALIENTE (READ-ONLY)

Para proporcionar visibilidad remota sin comprometer la seguridad ni introducir vectores de riesgo operativo:

### 2.1 Restricciones Innegociables
1. **Prefijo Obligatorio:** Todo mensaje saliente debe iniciar inexcusablemente con:  
   `🔬 [RESEARCH SHADOW — NO BROKER ORDERS]`
2. **Dirección Estrictamente Unidireccional (Outbound Only):** El canal actúa como un publicador pasivo. No se aceptan comandos entrantes (`/buy`, `/sell`, `/stop`, etc.), eliminando cualquier posibilidad de inyección de comandos o ejecución no autorizada.
3. **Diferenciación Absoluta:** Las alertas Shadow no utilizan los mismos identificadores ni canales que las alertas transaccionales de D21 PAPER.
4. **Rate Limiting y Deduplicación:** Se limita a un máximo de un reporte diario condensado tras el cierre bursátil, previniendo inundación de notificaciones.

### 2.2 Formato Canónico del Mensaje

```text
🔬 [RESEARCH SHADOW — NO BROKER ORDERS]
📅 Sesión: 2026-11-02 | Fase 7.4
----------------------------------------
• MR_VolCond (A): 1 sess | Trades: 0 | Net: +$0.00 | PF: 0.00
• CS_RelMom (B): 1 sess | Trades: 0 | Net: +$0.00 | PF: 0.00
----------------------------------------
🔒 Status: AIR-GAPPED | D21 PAPER: Intacto e Inmutable
```
