# ORACLEBOT V2 — FASE 7.4
# ESPECIFICACIÓN DEL SIMULADOR DE EJECUCIÓN PROSPECTIVA REALISTA (BLOQUE D & BLOQUE H)

**Proyecto:** OracleBot v2 / Strategy Laboratory  
**Módulo:** `ai_trading_agent.strategy_lab.shadow.shadow_simulator`  
**Fecha:** 30 de octubre de 2026

---

## 1. PRINCIPIO DE CAUSALIDAD TEMPORAL ESTRICTA ($T \to T+1$)

El simulador `ShadowExecutionSimulator` implementa una política temporal de ejecución que erradica cualquier vestigio de anticipación temporal (*lookahead bias*):

$$\text{Señal en Cierre de Sesión } T \implies \text{Orden Encolada} \implies \text{Ejecución en Apertura de Sesión } T+1$$

### 1.1 Invalidez Física del Llenado al Cierre de la Misma Barra
En backtesting ingenuo es habitual simular que la orden se llena al precio de cierre de la barra cuya señal depende de dicho cierre. En los mercados bursátiles reales esto es físicamente imposible, pues el precio oficial de cierre del NYSE sólo se determina al finalizar la subasta de cierre (*Closing Auction*, 16:00:00 ET). Cualquier orden posterior debe necesariamente ejecutarse en la sesión siguiente.

### 1.2 Mecánica de Llenado en Apertura
1. **Entrada en Apertura $T+1$:**
   $$\text{Entry Fill} = \text{Open}_{T+1} \times (1.0 + \text{Slippage Rate})$$
2. **Deslizamiento en Efectivo:**
   $$\text{Slippage USD} = (\text{Entry Fill} - \text{Open}_{T+1}) \times \text{Shares}$$
3. **Comisión:**
   $$\text{Commission USD} = \max(\text{Shares} \times \text{Comm Rate}, \text{Min Comm})$$

---

## 2. MODELADO DE GAPS ADVERSOS DE APERTURA (*OPENING GAPS*)

Una debilidad frecuente de los simuladores es asumir que los Stop-Loss siempre se ejecutan exactamente al nivel prefijado, ignorando que el mercado puede abrir con una brecha negativa violenta.

En [`shadow_simulator.py`](file:///C:/Users/edsel/Documents/trading-app-repo/ai_trading_agent/strategy_lab/shadow/shadow_simulator.py), el tratamiento de gaps se modela rigurosamente:

$$\text{Si } \text{Open}_i \le \text{Stop Loss Price} \implies \text{Exit Mid Price} = \text{Open}_i \quad (\text{Evento: STOP\_LOSS\_GAP\_OPEN})$$

$$\text{Exit Fill} = \text{Open}_i \times (1.0 - \text{Slippage Rate})$$

Si la sesión abre por debajo del stop protector, la orden se ejecuta al precio real de apertura con el deslizamiento correspondiente, asumiendo la pérdida completa del gap.

---

## 3. ESPECIFICACIÓN DE LOS TRES ESCENARIOS DE COSTES PARALELOS

Para evaluar la resiliencia económica frente a cambios de liquidez o comisiones, el simulador soporta tres escenarios estandarizados:

| Escenario | Comisión por Acción | Slippage en Entrada | Slippage en Salida | Comisión Mínima por Orden |
| :--- | :---: | :---: | :---: | :---: |
| **1× Base** | $0.005 USD | 5.0 bps (0.05%) | 5.0 bps (0.05%) | $1.00 USD |
| **2× Moderado** | $0.010 USD | 10.0 bps (0.10%) | 10.0 bps (0.10%) | $2.00 USD |
| **3× Severo** | $0.015 USD | 15.0 bps (0.15%) | 15.0 bps (0.15%) | $3.00 USD |

Cada escenario mantiene su propia contabilidad y registro de trades, asegurando que las decisiones de un tier no contaminen las de otro.

---

## 4. GESTIÓN DE CAPITAL, TAMAÑO DE POSICIÓN Y LÍMITES DE CONCURRENCIA

### 4.1 Dimensionamiento por Riesgo Fijo
El número de acciones para cada orden se calcula dinámicamente en función de la distancia al Stop-Loss sobre el precio de apertura:

$$\text{Stop Distance} = \max(\text{Open}_{T+1} \times \text{Stop Loss Pct}, 1.0)$$

$$\text{Shares} = \max\left(10, \left\lfloor \frac{\text{Risk Budget USD}}{\text{Stop Distance}} \right\rfloor \right)$$

Donde $\text{Risk Budget USD} = \$250.00 \text{ USD}$.

### 4.2 Control de Efectivo y Rechazo de Apalancamiento
Antes de autorizar el llenado:
$$\text{Requerimiento de Efectivo} = (\text{Entry Fill} \times \text{Shares}) + \text{Commission USD}$$

Si $\text{Requerimiento de Efectivo} > \text{Current Cash}$, el simulador reduce el número de acciones al máximo permisible con el efectivo restante. Si $\text{Shares} < 10$, la orden se cancela por falta de liquidez.

### 4.3 Control de Concurrencia
- **Candidate A:** Máximo 1 posición simultánea por activo (hasta 6 activos).
- **Candidate B:** Máximo 2 posiciones simultáneas en toda la cartera.

---

## 5. AISLAMIENTO ABSOLUTO RESPECTO A BROKERS

El archivo [`shadow_simulator.py`](file:///C:/Users/edsel/Documents/trading-app-repo/ai_trading_agent/strategy_lab/shadow/shadow_simulator.py) no contiene referencias ni importaciones a Moomoo, Interactive Brokers ni módulos de red. Opera como una máquina de estados pura en memoria.
