# GITHUB REPOSITORY INTEGRITY REPORT — FASE 6.3

**Fecha de Auditoría:** 2026-10-30T13:30:10Z  
**Repositorio Principal:** `armandog451-web/trading-app` (`trading-app-repo`)  
**Repositorio Secundario:** `armandog451-web/AI-Trading-Agent-1.0` (`SuperBot/AI-Trading-Agent-1.0`)  
**Estado:** `PASS` (Integridad Verificada, Cero Fuga de Secretos)

---

## 1. ESTADO DE LOS REPOSITORIOS GIT

### Repositorio Principal (`trading-app-repo`):
* **Ruta Local:** `C:\Users\edsel\OneDrive\Documents\trading-app-repo`
* **Remote Origin:** `https://github.com/armandog451-web/trading-app.git`
* **Rama Activa:** `main`
* **Commit SHA (HEAD):** `f44f397022cfd186c5e916a008003a21e5f118eb`
* **Git Tree SHA:** `099506ae07e186fb155ddc94dfcbd35095d59bfe`
* **Modificaciones Locales:** Exclusivamente mejoras autorizadas de observabilidad e idempotencia en `scheduler_service.py`, `campaign.py`, `app.py` y archivos de log transitorios en `journal/data/`.
* **Estado Remoto:** Prohibido realizar push sin autorización expresa.

### Repositorio Secundario (`SuperBot/AI-Trading-Agent-1.0`):
* **Ruta Local:** `C:\Users\edsel\OneDrive\Documents\SuperBot\AI-Trading-Agent-1.0`
* **Remote Origin:** `https://github.com/armandog451-web/AI-Trading-Agent-1.0.git`
* **Rama Activa:** `main`
* **Commit SHA (HEAD):** `e77829a48c320be48f2347780b25691fff0ca65e`
* **Git Tree SHA:** `b34f0903276dd5d4e56325879a931e7c272ea9e6`
* **Working Tree:** `clean` (sincronizado).

---

## 2. AUDITORÍA CRIPTOGRÁFICA DE ARCHIVOS CRÍTICOS (SHA-256 COMPLETO DE 64 CARACTERES)

Se computaron los hashes SHA-256 directos (RAW) y normalizados por saltos de línea (NORM - LF) para evaluar la equivalencia exacta de lógica algorítmica:

### 2.1. Configuración de Seguridad y Límites (`settings.py`)
* `trading-app-repo` (NORM): `df17adf13e383b8d6e01da90e25217156cbf17196bd6641a50c5c2283c5896a0`
* `SuperBot` (NORM): `df17adf13e383b8d6e01da90e25217156cbf17196bd6641a50c5c2283c5896a0`
* **Concordancia:** **100% IDÉNTICO**.

### 2.2. Motor de Riesgo Institucional (`risk/engine.py`)
* `trading-app-repo` (NORM): `57a8c687c8f549bab55b029920907c6bac89be4eaff5b56e1de69ef01bc4f613`
* `SuperBot` (NORM): `57a8c687c8f549bab55b029920907c6bac89be4eaff5b56e1de69ef01bc4f613`
* **Concordancia:** **100% IDÉNTICO**.

### 2.3. Registro Canónico de Estrategias (`strategy_lab/registry/registry.py`)
* `trading-app-repo` (NORM): `ab67e82841c960d0be9de17f57e457998dde2f1a8864a696d726efea07794cd5`
* `SuperBot` (NORM): `ab67e82841c960d0be9de17f57e457998dde2f1a8864a696d726efea07794cd5`
* **Concordancia:** **100% IDÉNTICO**.
* **Estado D21:** `PAPER`.
* **Estado Estrategias Experimentales (69):** `RESEARCH`.

### 2.4. Motor de Fidelidad de Ejecución (`fidelity/engine.py`)
* `trading-app-repo` (NORM): `106112ebda1636703ee41e4e6558bed9ac674e111ade435d2b8af69d74992c98`
* `SuperBot` (NORM): `106112ebda1636703ee41e4e6558bed9ac674e111ade435d2b8af69d74992c98`
* **Concordancia:** **100% IDÉNTICO**.

### 2.5. Scoring de Fidelidad (`fidelity/scoring.py`)
* `trading-app-repo` (NORM): `12750087d0cda970a1ebfa6650e6bf1e906245f8712824ab28bfe55814903e4b`
* `SuperBot` (NORM): `12750087d0cda970a1ebfa6650e6bf1e906245f8712824ab28bfe55814903e4b`
* **Concordancia:** **100% IDÉNTICO**.

### 2.6. Diario de Operaciones (`trade_journal.py`)
* `trading-app-repo` (NORM): `d7c582269dd67392a2ac18c0679dfff7950dd98d778f7223c535d7ea3ae2b446`
* `SuperBot` (NORM): `d7c582269dd67392a2ac18c0679dfff7950dd98d778f7223c535d7ea3ae2b446`
* **Concordancia:** **100% IDÉNTICO**.

### 2.7. Módulos con Mejoras Locales de Observabilidad (Fase 6.3)
* `scheduler_service.py` y `campaign.py`: Modificados localmente en `trading-app-repo` bajo autorización para incorporar idempotencia, telemetría y los 4 contadores. Los hashes de estos archivos difieren de `SuperBot` estrictamente por la adición de estas características locales de observabilidad sin alterar la lógica de toma de decisiones.

---

## 3. AUDITORÍA DE SEGURIDAD Y AUSENCIA DE SECRETOS

1. **Tokens y Claves:** No existen tokens de Telegram, API keys de brokers ni contraseñas en los archivos rastreados por Git en ninguno de los repositorios.
2. **Archivos `.env`:** Los archivos de variables de entorno y bases de datos SQLite locales (`trading_agent.db`) se encuentran debidamente protegidos y excluidos por las reglas de `.gitignore`.
3. **Logs Transitorios:** Los archivos `.log` y temporales de depuración se mantienen en directorios excluidos o locales.

---

## 4. CONCLUSIÓN Y VEREDICTO

* **Estado:** `PASS`
* **Veredicto:** Ambos repositorios mantienen estricta equivalencia en sus núcleos de riesgo, linaje de estrategias y motores de fidelidad. Los cambios locales en `trading-app-repo` cumplen con todas las restricciones de gobernanza y no se realizarán pushes externos sin aprobación del usuario.
