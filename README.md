# 🤖 AlgortimTrading Robot v2.0 PRO

Motor de trading algorítmico profesional para cuentas Demo (**Moomoo OpenD** y **Alpaca Paper**) con **estrategia híbrida intradía**, panel de control en **Google Chrome** y notificaciones interactivas de ejecución con 1 toque en **Telegram**.

---

## 🌟 Características Principales

1. **Estrategia Híbrida Cuantitativa (16 Clases de Trading):**
   * **Trend Following:** Cruce y expansión de EMA 20/50/200.
   * **Mean Reversion:** Zonas extremas de agotamiento RSI(14) + Bandas de Bollinger.
   * **Ruptura de Liquidez & Order Blocks:** Detección de barridos intradiarios con expansión de volumen (>1.3x).
   * **Rebote VWAP Institucional:** Rebotes en el precio promedio ponderado por volumen.
2. **Auto-Aprendizaje Continuo (Machine Learning Adaptativo):**
   * El robot calibra y ajusta los pesos de cada estrategia según los aciertos y pérdidas (*Win/Loss*).
3. **Guardián de Posiciones & Riesgo Institucional:**
   * **Auto Break-Even (+1.0R):** Asegura la operación a precio de entrada cuando avanza la mitad del objetivo (riesgo cero).
   * **Auto Square-Off (03:55 PM EST):** Cierre forzoso antes de la campana de Wall Street para eliminar el riesgo de *gaps* nocturnos.
   * **Freno de Emergencia Diario (*Circuit Breaker* -2.5%):** Auto-pausa si la sesión acumula pérdida máxima diaria.
   * **Riesgo / Beneficio Mínimo 1:2 estricto.**
4. **Notificaciones Interactivas en Telegram:**
   * Bot: `@LaraMayaBot` | Chat ID: `8887098910`
   * Desglose completo: **Precio unitario**, **Inversión Total ($)**, Pérdida máxima ($) y Ganancia estimada ($).
   * Botones en vivo: `[✅ Ejecutar Orden]` y `[❌ Descartar]`.
5. **Panel de Control Web Moderno:**
   * Corre localmente en `http://localhost:8050` con gráficos de TradingView en vivo, métricas de cuenta y control en 1 clic.

---

## 🖥️ Instalación y Uso en Esta PC (1 Clic)

1. En tu Escritorio encontrarás el acceso directo **`AlgortimTrading Robot`**.
2. Haz doble clic sobre él.
3. Se iniciará el motor y se abrirá automáticamente tu navegador Google Chrome en `http://localhost:8050`.

---

## 🚀 Cómo Instalarlo en Otra PC para Operar 24/7

Si tienes otra computadora o servidor que permanecerá encendido las 24 horas del día, sigue estos sencillos pasos:

### Paso 1: Clonar o Descargar el Repositorio
En la nueva PC, abre PowerShell o CMD y clona el repositorio privado:
```bash
git clone https://github.com/armandog451-web/AlgortimTrading-robot.git
cd AlgortimTrading-robot
```
*(O simplemente copia toda la carpeta del proyecto mediante una memoria USB o disco en la nueva PC).*

### Paso 2: Ejecutar el Instalador Automático
Haz doble clic en:
👉 **`INSTALADOR_OTRA_PC.bat`**

Este script hará todo por ti:
* Comprueba que tengas Python 3.11 instalado.
* Instala automáticamente todas las dependencias (`requirements.txt`).
* Crea tu archivo de configuración `.env`.
* Genera el acceso directo en el Escritorio de la nueva PC.

### Paso 3: Configurar el Arranque Automático con Windows (Opcional pero Recomendado para 24/7)
Para que no tengas que preocuparte si la PC se reinicia o se corta la luz:
1. Haz doble clic en **`INSTALAR_ARRANQUE_CON_WINDOWS.bat`**.
2. Listo. Cada vez que Windows encienda o se reinicie tras actualizaciones, el robot arrancará solo en segundo plano con el vigilante auto-reinicio (**`INICIAR_24_7_AUTOMATICO.bat`**).

### Paso 4: Asegurar Moomoo OpenD en la Otra PC
* Instala e inicia sesión en **moomoo OpenD** en la otra PC.
* Asegúrate de que el puerto `11111` esté escuchando (puerto predeterminado de OpenD).

---

## ⚙️ Configuración (.env)

```ini
BROKER=moomoo
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111
TELEGRAM_BOT_TOKEN=8885408454:AAHJB3V7lM0foQX65sAzqvn-W6ydKKj6Jbk
TELEGRAM_CHAT_ID=8887098910
DEMO_CAPITAL=100000.0
RISK_MAX_EXPOSURE=0.02
MIN_RR_RATIO=2.0
MAX_DAILY_LOSS_PCT=2.5
```

---

## 📁 Estructura del Proyecto

```
AlgortimTrading-robot/
├── start.bat                         # Lanzador en 1 clic
├── start.ps1                         # Script unificado de inicio + apertura en Chrome
├── INICIAR_24_7_AUTOMATICO.bat       # Vigilante con auto-reinicio continuo 24/7
├── INSTALAR_ARRANQUE_CON_WINDOWS.bat # Registra el bot en el inicio de Windows
├── INSTALADOR_OTRA_PC.bat            # Instalador desatendido para otra máquina
├── create_desktop_shortcut.ps1       # Generador de accesos directos
│
├── server.py                         # Servidor FastAPI del panel de control
├── engine.py                         # Motor cuantitativo de estrategias y escaneo
├── guardian.py                       # Guardián de posiciones, break-even y square-off
├── broker.py                         # Gestor de brokers (Moomoo OpenD & Alpaca)
├── telegram_service.py               # Servicio asíncrono interactivo de Telegram
├── database.py                       # Base de datos SQLite (señales, métricas, logs)
├── config.py                         # Configuración centralizada
│
├── templates/
│   └── dashboard.html                # Terminal visual estilo Bloomberg/TradingView
├── requirements.txt                  # Librerías Python necesarias
├── .env.example                      # Plantilla de variables de entorno
└── README.md                         # Esta documentación
```

---

*Desarrollado para Edsel Armando • AlgortimTrading Robot v2.0 PRO*
