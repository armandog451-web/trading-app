# ORACLEBOT V2 — ESPECIFICACIÓN CIENTÍFICA FORMAL
## FASE EXP-MTF01 — Multi-Timeframe Extreme Reversal
### Estrategia: MTF_ExtremeReversal_V1

**Proyecto:** OracleBot v2 / AI Trading Agent / Strategy Laboratory  
**Workspace canónico:** `C:\Users\edsel\Documents\trading-app-repo`  
**Identificador único:** `MTF_ExtremeReversal_V1`  
**Campaña:** `EXP-MTF01`  
**Fecha de emisión:** 31 de octubre de 2026  
**Estado:** `SPECIFICATION_FROZEN`  
**Clasificación:** `RESEARCH_ONLY / ANALYSIS_ONLY`  
**Autorización:** Investigación aislada. Cero órdenes LIVE/PAPER. Sin conexión a broker.

---

## 1. INTRODUCCIÓN Y OBJETIVO DE LA INVESTIGACIÓN

El objetivo de la fase `EXP-MTF01` es traducir, formalizar matemáticamente, implementar de manera causal y evaluar con rigor cuantitativo la metodología heurística descrita en el material audiovisual del usuario ("Multi-Timeframe Extreme Reversal").

El propósito fundamental **no es replicar con sesgo de confirmación operaciones discrecionales ganadoras seleccionadas a posteriori**, sino someter cada supuesto de la estrategia a pruebas estadísticas refutables, deterministas y libres de sesgo de anticipación (*look-ahead bias*), determinando objetivamente si el sistema posee una ventaja económica neta (*economic edge*) tras considerar fricciones de mercado (comisiones y deslizamiento).

---

## 2. DIFERENCIAS TÉCNICAS: VIDEO HEURÍSTICO VS. FORMALIZACIÓN CIENTÍFICA

| Elemento | Heurística Discrecional del Video | Formalización Científica Determinista (EXP-MTF01) | Justificación Metodológica |
|---|---|---|---|
| **Extremo Diario (D1)** | Soporte/resistencia trazado visualmente a discreción del autor. | Canal de extremo retrospectivo: $Close_t \le \min_{60}(Low) + 0.50 \times ATR_{14}(D1)$. | Elimina subjetividad y previene la selección retroactiva de niveles. |
| **Aceleración (D1)** | "Velas grandes acercándose al nivel". | Desplazamiento neto direccional: $\|Close_t - Close_{t-5}\| \ge 2.5 \times ATR_{14}(D1)$ con persistencia de signo. | Cuantifica objetivamente el impulso extremo que precede al agotamiento. |
| **Desaceleración (D1)** | "Velas pequeñas o mechas que muestran rechazo". | Contracción de cuerpo real ($\frac{\|Close - Open\|}{High - Low} \le 0.45$) con mecha de rechazo $\ge 0.35 \times Range$ o vela interior (*inside bar*). | Regla determinista evaluada únicamente en barras diarias cerradas. |
| **Estructura Horaria (H1)** | Picos y valles visuales identificados en retrospectiva. | Swing High / Swing Low con confirmación simétrica causal ($SWING\_LEFT = 3, SWING\_RIGHT = 3$). Confirmado en $T+3$. | Cero sesgo de anticipación. Un pivot no existe para el algoritmo hasta que transcurren 3 barras a su derecha. |
| **Cambio Estructural (BOS)** | "Ruptura de la estructura bajista previa". | Cierre $H1 > SwingHigh$ confirmado más reciente (para Long), o $Close < SwingLow$ confirmado (para Short). | Definición algorítmica unívoca sin ambigüedad gráfica. |
| **Confluencia EMA 50 + Fib 0.618** | Trazado visual de retroceso de Fibonacci y observación cualitativa de cercanía a la EMA. | Rango de confluencia métrico: $\|Fib_{0.618} - EMA_{50}(H1)\| \le 0.25 \times ATR_{14}(H1)$. Zona activa $[Fib_{0.618} \pm 0.25 ATR]$. | Excluye retrocesos desalineados o que no coinciden geométricamente con el soporte dinámico. |
| **Gatillo de Entrada (M5)** | "Ruptura de la línea de tendencia correctiva en 5 minutos". | Ruptura confirmada de Swing High/Low local ($L=2, R=2$) en M5 en dirección del impulso, evaluada al cierre de la barra M5. | Las líneas de tendencia manuales son inherentemente subjetivas; los fractales locales son 100% reproducibles. |
| **Sincronización Temporal** | Observación simultánea de pantallas sin considerar disponibilidad causal de datos. | Motor de sincronización causal: M5 en tiempo $T$ solo accede a barra D1 cerrada en $D-1$ y barra H1 cerrada estrictamente en o antes de $T$. | Previene contaminación de datos intradía incompletos (*data leakage*). |
| **Ejecución y Costos** | Precios ideales sin comisiones, slippage ni verificación de latencia. | Simulación causal $T \to T+1$ al precio Open de la barra M5 subsiguiente, incorporando comisiones (\$0.005/acción) y slippage (2 a 6 bps). | Refleja la fricción microestructural real en timeframes de alta frecuencia. |
| **Stop Loss** | Colocado visualmente "por debajo del nivel 75% de Fib". | Nivel exacto: $P_1 - 0.75 \times (P_1 - P_0) - 0.10 \times ATR_{14}(H1)$ registrado antes de emitir la orden. | Cálculo causal previo que evita desplazamiento de stop post-fill. |
| **Take Profit** | Salida discrecional cerca de máximos previos. | Dos modelos congelados: MTF_V1A (Estructura = $P_1$) y MTF_V1B (R Fijo = $2.0R$). | Permite medir empíricamente la expectativa matemática de ambas hipótesis de salida. |

---

## 3. FORMALIZACIÓN MATEMÁTICA DETALLADA

### 3.1 Contexto Diario (D1)

Dado un histórico de barras diarias cerradas $\{D_i\}_{i=1}^T$, sea $t$ el índice del último día cerrado disponible antes de la sesión actual:

1. **Rango Verdadero Promedio (ATR):**
   $$TR_t = \max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|)$$
   $$ATR_{14}(D1)_t = \frac{1}{14} \sum_{i=0}^{13} TR_{t-i}$$

2. **Detección de Extremo Histórico (Lookback = 60 días):**
   - Mínimo de 60 periodos: $L_{60, t} = \min_{k=1}^{60} Low_{t-k}$
   - Máximo de 60 periodos: $H_{60, t} = \max_{k=1}^{60} High_{t-k}$
   - **Condición Extremo Inferior (Candidato Long):**
     $$Close_t \le L_{60, t} + 0.50 \times ATR_{14}(D1)_t$$
   - **Condición Extremo Superior (Candidato Short):**
     $$Close_t \ge H_{60, t} - 0.50 \times ATR_{14}(D1)_t$$

3. **Aceleración hacia el Extremo (Lookback = 5 días):**
   - Para Extremo Inferior (descenso acelerado):
     $$Close_{t-5} - Close_t \ge 2.50 \times ATR_{14}(D1)_t$$
   - Para Extremo Superior (ascenso acelerado):
     $$Close_t - Close_{t-5} \ge 2.50 \times ATR_{14}(D1)_t$$

4. **Desaceleración en el Extremo:**
   Definida en la barra $D_t$ mediante al menos una de las siguientes dos condiciones deterministas:
   - **Contracción de Cuerpo y Mecha de Rechazo:**
     $$\frac{|Close_t - Open_t|}{High_t - Low_t} \le 0.45$$
     - Si es Extremo Inferior, mecha inferior: $\frac{\min(Open_t, Close_t) - Low_t}{High_t - Low_t} \ge 0.35$
     - Si es Extremo Superior, mecha superior: $\frac{High_t - \max(Open_t, Close_t)}{High_t - Low_t} \ge 0.35$
   - **Barra Interior (*Inside Bar*):**
     $$High_t \le High_{t-1} \quad \land \quad Low_t \ge Low_{t-1}$$

Si se cumplen el Extremo, la Aceleración y la Desaceleración, el estado de contexto D1 para la sesión siguiente se marca como `D1_BULLISH_EXTREME_ACTIVE` o `D1_BEARISH_EXTREME_ACTIVE`.

---

### 3.2 Estructura y Confirmación Horaria (H1)

Sea $\{H_j\}$ la serie de barras horarias cerradas.

1. **Detección Causal de Fractales / Swings:**
   Con parámetros simétricos $SWING\_LEFT = 3$ y $SWING\_RIGHT = 3$, un Swing High ocurre en el índice $k$ si y solo si:
   $$High_k > \max_{m=1}^3 High_{k-m} \quad \land \quad High_k > \max_{m=1}^3 High_{k+m}$$
   *Regla Causal Crítica:* Este Swing High no es visible ni existe para el modelo hasta el cierre de la barra $k+3$. Su timestamp de disponibilidad es $Timestamp(H_{k+3})$.
   
   Análogamente, un Swing Low en el índice $k$ requiere:
   $$Low_k < \min_{m=1}^3 Low_{k-m} \quad \land \quad Low_k < \min_{m=1}^3 Low_{k+m}$$
   Confirmado al cierre de la barra $k+3$.

2. **Ruptura de Estructura (Break of Structure - BOS):**
   - **BOS Alcista (para Long):** Con contexto `D1_BULLISH_EXTREME_ACTIVE`, el precio H1 en barra $j$ cierra por encima del Swing High confirmado más reciente $P_{swing\_high}$:
     $$Close_j > High(P_{swing\_high})$$
   - Se identifica el impulso: $P_0$ (el Swing Low más bajo del movimiento bajista precedente) y $P_1$ (el nuevo Swing High confirmado que culmina el impulso de ruptura).

3. **Cálculo de Retroceso de Fibonacci y Confluencia EMA 50:**
   Dado el rango de impulso $R_{impulse} = High(P_1) - Low(P_0)$ (para Long):
   - Nivel Fib 0.618:
     $$Fib_{0.618} = High(P_1) - 0.618 \times R_{impulse}$$
   - Nivel de Referencia Stop Fib 0.75:
     $$Fib_{0.75} = High(P_1) - 0.75 \times R_{impulse}$$
   - Media Móvil Exponencial H1 de 50 periodos: $EMA_{50}(H1)_j$.
   - **Condición de Confluencia:**
     $$|Fib_{0.618} - EMA_{50}(H1)_j| \le 0.25 \times ATR_{14}(H1)_j$$
   - **Zona de Confluencia Operativa:**
     $$Z_{confluence} = \left[ Fib_{0.618} - 0.25 \times ATR_{14}(H1)_j, \quad Fib_{0.618} + 0.25 \times ATR_{14}(H1)_j \right]$$

Cuando el precio H1 retrocede e interactúa con $Z_{confluence}$ (es decir, $Low_j \le \max(Z_{confluence})$ y $High_j \ge \min(Z_{confluence})$) sin haber cerrado por debajo de $Fib_{0.75}$, se activa el disparador para monitorear M5: `H1_SETUP_READY`.

---

### 3.3 Confirmación y Ejecución Intradía (M5)

Sea $\{M_n\}$ la serie de barras M5 cerradas:

1. **Estructura Local M5:**
   Se calcula la estructura M5 con fractales rápidos $M5\_SWING\_L = 2, M5\_SWING\_R = 2$.
   Durante el retroceso hacia la zona de confluencia, se genera una micro-tendencia bajista en M5 (para setup Long).

2. **Disparador de Ruptura M5:**
   La señal de entrada se genera en la barra $M_n$ si:
   - El setup H1 está activo (`H1_SETUP_READY`).
   - El precio de cierre $Close(M_n)$ supera el último Swing High local confirmado de M5:
     $$Close(M_n) > High(M5\_Local\_SwingHigh)$$
   - El precio $Low(M_n)$ no ha quebrado el nivel de invalidación $Fib_{0.75}$.

3. **Ventana de Validez (Timeout):**
   El setup H1 caduca si transcurren más de $M5\_TIMEOUT\_BARS = 24$ barras M5 (2 horas de mercado) desde la activación sin confirmación de ruptura, o si el precio H1/M5 cierra más allá de $Fib_{0.75}$. Si expira, se registra `NO_TRADE_TIMEOUT`.

4. **Ejecución Causal:**
   - La señal se emite formalmente al cierre de la barra M5: $T_{signal} = CloseTime(M_n)$.
   - La orden de mercado simulada se ejecuta en la barra subsiguiente:
     $$FillPrice = Open(M_{n+1}) + Slippage$$
   - No se permite fill retroactivo al precio de apertura de $M_n$ ni al cierre sin deslizamiento.

---

### 3.4 Modelo de Salida: Stop Loss y Take Profit

1. **Stop Loss (SL):**
   - Para posiciones Long:
     $$SL = Fib_{0.75} - 0.10 \times ATR_{14}(H1)$$
   - Para posiciones Short:
     $$SL = Fib_{0.75} + 0.10 \times ATR_{14}(H1)$$
   - Distancia de riesgo en precio: $R_{dist} = |FillPrice - SL|$.
   - Si $R_{dist} \le 0$ o $R_{dist} < 0.05 \times FillPrice$ (riesgo absurdo o stop al revés), la orden es automáticamente rechazada con motivo `INVALID_STOP_DISTANCE`.

2. **Take Profit (TP) — Variantes de Investigación:**
   - **Variante V1A (Structure Target):**
     $$TP_{V1A} = High(P_1) \quad (\text{para Long}) \quad \lor \quad Low(P_1) \quad (\text{para Short})$$
   - **Variante V1B (Fixed R Target):**
     $$TP_{V1B} = FillPrice + 2.0 \times R_{dist} \quad (\text{para Long}) \quad \lor \quad FillPrice - 2.0 \times R_{dist} \quad (\text{para Short})$$

3. **Resolución de Colisiones Intrabarra:**
   Si dentro de una misma barra M5 se tocan simultáneamente el Stop Loss y el Take Profit ($Low \le SL \land High \ge TP$), se aplica la regla de máxima prudencia institucional: **el Stop Loss se considera ejecutado primero** (pérdida de la operación).

---

### 3.5 Dimensionamiento de Posición y Gestión de Riesgo

- **Capital de Cuenta Virtual:** $\$100,000$ USD (aislado, no vinculado a brokers).
- **Riesgo por Operación:** $0.25\%$ del capital $(\$250 \text{ USD})$.
- **Cálculo de Acciones:**
  $$Shares = \min\left( \left\lfloor \frac{250}{R_{dist}} \right\rfloor, \left\lfloor \frac{100000 \times 0.20}{FillPrice} \right\rfloor \right)$$
  (Con límite de apalancamiento máximo de $20\%$ de la cartera en un solo trade).
- **Concurrencia:** Máximo 1 posición activa por activo.

---

## 4. GOBERNANZA Y CONTROL DE INTEGRIDAD

1. **Estado del Manifiesto:** `SPECIFICATION_FROZEN`.
2. **Hash Criptográfico:** Registrado en `EXP_MTF01_PARAMETER_MANIFEST.json`.
3. **Bloqueo Operativo:** Prohibida cualquier modificación de fórmulas durante la ejecución del experimento.
