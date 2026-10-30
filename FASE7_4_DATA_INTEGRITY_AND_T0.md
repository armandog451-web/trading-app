# ORACLEBOT V2 — FASE 7.4
# INTEGRIDAD DE DATOS, PROTOCOLO TEMPORAL Y DEFINICIÓN DE T0 PROSPECTIVO (BLOQUE B)

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Fecha de emisión:** 30 de octubre de 2026  
**Punto de origen prospectivo (T0):** `2026-10-30T16:00:00Z`  
**Primera sesión forward acreditable:** `2026-11-02` (Lunes hábil NYSE)

---

## 1. DEFINICIÓN DEL PUNTO DE ORIGEN PROSPECTIVO ($T_0$)

Para evitar la contaminación epistemológica conocida como *data snooping* o *lookahead retrospective*, el sistema establece un punto de corte temporal inquebrantable:

$$T_0 = \mathbf{2026\text{-}10\text{-}30T16:00:00Z}$$

### 1.1 Exclusión de la Sesión del 30 de Octubre de 2026 como Evidencia Forward
- La sesión del viernes 30 de octubre de 2026 fue utilizada para auditar y verificar el Discovery Engine v2 en la Fase 7.3A.
- Dado que los precios intradía y cierres preliminares de esta fecha ya fueron examinados por el equipo investigador, la directiva del Bloque B prohíbe taxativamente computar dicha sesión como evidencia prospectiva nueva.
- **Regla Operativa:** La acumulación formal de evidencia forward comienza única y exclusivamente a partir de la sesión hábil siguiente: **Lunes 2 de Noviembre de 2026** (`2026-11-02`).

---

## 2. COMPUERTAS DE INTEGRIDAD DE DATOS (`DataIntegrityGate`)

El evaluador `AutonomousShadowEvaluator` somete cada serie temporal a validaciones previas antes de permitir cualquier cómputo de señales:

1. **Rechazo de Barras Incompletas:** Si la hora de evaluación es anterior al cierre oficial (16:00 ET), la barra se clasifica como `UNCLOSED` y se descarta de inmediato sin evaluar señales.
2. **Rechazo de Fines de Semana:** Cualquier barra fechada en sábado o domingo se invalida, registrando una alerta de calidad de datos.
3. **Validación de Calendario Oficial NYSE:**
   - Se cotejan las fechas contra el calendario oficial de feriados (New Year's Day, MLK Day, Washington's Birthday, Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving Day, Christmas Day).
   - En días de cierre anticipado (13:00 ET), el horario de consolidación de datos se ajusta acordemente.
4. **Huella Digital de Barra:** Por cada barra diaria utilizada en la toma de decisiones, se calcula su hash SHA-256 inmutable:
   $$\text{BarHash} = \text{SHA256}(\text{Symbol} : \text{Timestamp} : \text{Open} : \text{High} : \text{Low} : \text{Close} : \text{Volume})$$
   Dicho hash se estampa en el ledger de evidencia, permitiendo auditar en el futuro exactamente qué datos generaron cada señal.

---

## 3. TRATAMIENTO DE GAPS OPERATIVOS Y CAÍDAS DE SERVICIO

Si el sistema sufre una interrupción de energía, red o fallo de API durante una sesión bursátil:

1. **Prohibición de Fabricación Retrospectiva:** Queda terminantemente prohibido reconstruir operaciones que no fueron ejecutadas en su momento y presentarlas retrospectivamente como evidencia prospectiva.
2. **Registro de Evento de Brecha (`GAP_EVENT`):** Si una sesión bursátil transcurre sin que el evaluador la procese en tiempo real, el reloj forward incrementa el contador `runtime_gaps` y la sesión se registra como no evaluada.
3. **Auditoría Transparente:** La presencia de gaps operativos no invalida la campaña, pero queda registrada como un factor de degradación de la madurez operativa en los informes semanales.
