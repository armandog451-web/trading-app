# ORACLEBOT V2 — INFORME DE IMPLEMENTACIÓN
## FASE EXP-MTF01 — Multi-Timeframe Extreme Reversal
### Arquitectura Modular y Certificación de Componentes

**Proyecto:** OracleBot v2 / AI Trading Agent / Strategy Laboratory  
**Workspace canónico:** `C:\Users\edsel\Documents\trading-app-repo`  
**Identificador único:** `MTF_ExtremeReversal_V1`  
**Campaña:** `EXP-MTF01`  
**Fecha de emisión:** 31 de octubre de 2026  
**Clasificación:** `RESEARCH_ONLY / ANALYSIS_ONLY`  

---

## 1. ARQUITECTURA MODULAR DEL SISTEMA

La estrategia `MTF_ExtremeReversal_V1` ha sido diseñada siguiendo una estricta separación de responsabilidades y garantizando cero acoplamiento con la operativa de producción (D21 y campañas Forward Shadow activas):

```text
ai_trading_agent/strategy_lab/experiments/exp_mtf01/
├── daily_context_engine.py          # Extremos D1, aceleración (5d) y desaceleración causal
├── market_structure_engine.py       # Swings H1 causales (L=3, R=3) confirmados en T+3 y BOS
├── fibonacci_confluence_engine.py   # Retrocesos Fib 0.618/0.75 y confluencia métrica con EMA 50
├── m5_entry_engine.py               # Fractales M5 (L=2, R=2), timeout e invalidación
├── causal_mtf_synchronizer.py       # Sincronización multi-temporal cerrada y orquestación
└── mtf_backtester.py                # Simulación de ejecución T+1, costos y colisiones
```

---

## 2. DETALLE DE COMPONENTES Y PROTOCOLOS CAUSALES

### 2.1 DailyContextEngine
- **Métricas:** Calcula $ATR_{14}(D1)$, canales rodantes de 60 días ($Min\_Low_{60}, Max\_High_{60}$) desplazados por 1 barra para no incluir el día en curso.
- **Aceleración:** Desplazamiento direccional a 5 días respecto a $2.50 \times ATR$.
- **Desaceleración:** Detección de contracción del cuerpo real ($\le 45\%$ del rango) combinada con mecha de rechazo ($\ge 35\%$) o formación de *inside bar*.
- **Garantía Causal:** Al evaluar cualquier momento $T$ durante la sesión intradía, el motor consulta exclusivamente días con fecha estrictamente anterior: `df.index.date < T.date()`.

### 2.2 MarketStructureEngine
- **Swings Fractales:** Con $SWING\_LEFT = 3$ y $SWING\_RIGHT = 3$, un pivote en la barra $k$ únicamente se registra como confirmado en el índice $k+3$.
- **Cero Anticipación:** Las barras entre $k$ y $k+2$ no tienen conocimiento del pivote; el precio solo puede romper estructuras causalmente confirmadas.
- **Break of Structure (BOS):** Identifica el cruce del precio de cierre de H1 por encima del último *Swing High* confirmado (para Long) o por debajo del último *Swing Low* confirmado (para Short).

### 2.3 FibonacciConfluenceEngine
- **Cálculo de Impulso:** Delimita el rango entre el pivote origen $P_0$ y el pivote de ruptura $P_1$.
- **Confluencia:** Exige que el nivel 0.618 de Fibonacci se encuentre a una distancia no mayor a $0.25 \times ATR_{14}(H1)$ de la media móvil exponencial de 50 periodos ($EMA_{50}$).
- **Zona de Interacción:** Genera un intervalo de precios causalmente congelado $[Z_{min}, Z_{max}]$.

### 2.4 M5EntryEngine
- **Confirmación Intradía:** Emplea fractales rápidos ($L=2, R=2$) en temporalidad de 5 minutos para registrar la micro-tendencia correctiva.
- **Gatillo:** Se dispara cuando una vela M5 cierra superando el último fractal local en la dirección del setup.
- **Timeout y Expiración:** Si transcurren más de 24 barras M5 (2 horas) sin confirmación, o si el precio perfora el nivel de invalidación (Fib 0.75), el setup se cancela inmediatamente.

### 2.5 CausalMTFSynchronizer
- Orquesta el flujo de información respetando la jerarquía temporal:
  $$\text{D1 (D-1 cerrada)} \implies \text{H1 (T cerrada)} \implies \text{M5 (T cerrada)} \implies \text{Señal en } T$$
- Permite la activación selectiva de componentes para ejecutar los estudios de ablación (Ablaciones B, C, D, E).

### 2.6 MTFBacktester
- **Simulación Causal:** La ejecución ocurre en el precio `Open` de la barra $T+1$.
- **Modelo de Fricción:** Aplica un deslizamiento base de 2.0 puntos básicos (bps) y comisiones de \$0.005 por acción en entrada y salida.
- **Resolución Conservadora de Colisiones:** Si en una misma barra M5 el precio toca tanto el Stop Loss como el Take Profit, el motor asigna automáticamente el Stop Loss, asumiendo el peor escenario para proteger la integridad cuantitativa.
- **Gestión de Capital:** Modela una cuenta ficticia de \$100,000 USD con riesgo fijo del 0.25% (\$250 USD) por trade.

---

## 3. CERTIFICACIÓN DE AISLAMIENTO

Todos los scripts operan en un entorno estrictamente aislado dentro del subdirectorio `experiments/exp_mtf01/`. No se realizan llamadas a brokers externos, no se interactúa con APIs de órdenes y se preservan todos los procesos protegidos del sistema.
