# D21 RUNTIME RECOVERY REPORT — 12 DE NOVIEMBRE DE 2026
**Modalidad:** AUTHORIZED RUNTIME RECOVERY — D21 / TELEGRAM / MOOMOO PAPER  
**Fecha de Emisión:** 12 de noviembre de 2026  
**Workspace Canónico:** `C:\Users\edsel\Documents\trading-app-repo`  
**Entorno Python:** `C:\Users\edsel\Documents\trading-app-repo\.venv\Scripts\python.exe` (Python 3.11)  
**Veredicto Final:** `RUNTIME_RECOVERED_AUTOSTART_NOT_VERIFIED`

---

## 1. RESUMEN EJECUTIVO Y CAUSA RAÍZ (ROOT CAUSE)

* **Causa Raíz:** En la madrugada del 12/11/2026 a las `00:31:29 EST`, el sistema operativo Windows ejecutó un reinicio no programado del host (`LastBootUpTime: 2026-11-12 00:31:29`).
* **Mecanismo de Falla:**
  1. Los procesos previos de producción (FastAPI worker PID `13832` / supervisor PID `3556` y EXP-ST02 PID `10472`) fueron terminados por el apagado del sistema operativo.
  2. La carpeta de inicio (`shell:startup`) contenía únicamente dos accesos directos desalineados (`OracleBotV2_AlwaysOn.vbs` apuntando a un script no canónico en `OneDrive\Documents\OracleBot` y `Sistema_Trading_Dual.lnk` apuntando a `Documents\SuperBot`), los cuales no apuntaban al repositorio canónico `C:\Users\edsel\Documents\trading-app-repo` ni al entorno virtual `.venv`.
  3. No existía ninguna tarea programada en el Programador de Tareas de Windows (*Task Scheduler*) ni servicio de Windows para el agente o Moomoo OpenD.
  4. En consecuencia, el servidor API en el puerto `8090`, el orquestador horario de tareas y el daemon EXP-ST02 permanecieron inactivos durante toda la mañana, impidiendo la emisión del reporte premarket matutino de las 09:20 ET y la evaluación del Ciclo 1 de EXP-ST02 de las 10:31 ET.

---

## 2. TIEMPO DE INACTIVIDAD Y BRECHA DE OBSERVACIÓN (DOWNTIME & OBSERVATION GAP)

* **Etiqueta Oficial:** `PAPER_OBSERVATION_GAP`
* **Inicio de la Brecha:** `2026-11-12 00:31:29 EST` (Reinicio del host Windows)
* **Fin de la Brecha:** `2026-11-12 11:27:34 EST` (Restauración del runtime y confirmación HTTP 200 en `/health`)
* **Duración Total:** `10 horas, 56 minutos, 05 segundos` (656 minutos).
* **Política Causal Anti-Retroactiva:** Se prohibió estrictamente la ejecución retroactiva de evaluaciones o señales perdidas durante la brecha, catalogando formalmente las tareas omitidas en SQLite sin alterar la serie histórica.

---

## 3. TAREAS OMITIDAS (MISSED JOBS)

Registradas formalmente en la tabla `task_logs_audit` de `ai_trading_agent.db`:

| Tarea / Job | Horario Previsto | Estado Registrado | Causa Forense |
| :--- | :---: | :---: | :--- |
| `premarket_scan_2026-11-12` | 09:20:00 EST | `MISSED_DUE_TO_HOST_REBOOT` | Runtime de orquestación detenido durante la ventana premarket. |
| `exp_st02_cycle_1` | 10:31:30 EST | `MISSED_DUE_TO_HOST_REBOOT` | Daemon EXP-ST02 detenido durante el cierre de la barra 09:30–10:30. |

Ambas tareas fueron blindadas en el sistema para que, al reactivarse el scheduler, este reconociera el estado `MISSED_DUE_TO_HOST_REBOOT` y no disparara despachos extemporáneos a destiempo durante la sesión de mercado.

---

## 4. RECUPERACIÓN DE MOOMOO OPEND & PAPER BROKER

* **Ubicación de Moomoo OpenD:** `C:\Users\edsel\AppData\Roaming\moomoo_OpenD\moomoo_OpenD.exe`
* **Configuración:** `OpenD.xml` (`ip: 127.0.0.1`, `api_port: 11111`, `pdt_protection: 1`)
* **Estado de Conectividad:** `DEGRADED` (El Gateway local de OpenD requiere autenticación/código de verificación en la interfaz gráfica tras reinicio de sesión).
* **Protección Institucional:** Conforme a la regla de degradación autorizada (*"Si OpenD no está disponible: AI Trading Agent puede iniciar en DEGRADED pero NO debe enviar órdenes hasta broker PAPER healthy"*), el adaptador `MoomooBrokerAdapter` permanece activo en modo de simulación determinista sin errores, con 0 posiciones abiertas y 0 órdenes pendientes.
* **Bloqueo LIVE:** Totalmente inviolable (`allow_live_trading: False`, `LIVE` bloqueado en settings y registry).

---

## 5. RECUPERACIÓN DEL RUNTIME Y ENDPOINT DE SALUD

* **Ruta de Ejecución:** `C:\Users\edsel\Documents\trading-app-repo`
* **Intérprete Python:** `C:\Users\edsel\Documents\trading-app-repo\.venv\Scripts\python.exe`
* **Servicio Web:** FastAPI / Uvicorn en `127.0.0.1:8090`
* **Protección de Instancia Única:** Verificada al 100%. Un intento concurrente de lanzar una segunda instancia arrojó `[Errno 10048] Only one usage of each socket address is normally permitted` (`REFUSE_TO_START`).
* **Verificación de Heartbeat (`/health`):**
  * Lectura 1 (`11:27:34 EST`): `HTTP 200` | Timestamp: `2026-11-12T16:27:34.664981`
  * Lectura 2 (`11:27:43 EST`): `HTTP 200` | Timestamp: `2026-11-12T16:27:43.017746`
  * Resultado: `timestamp_2 > timestamp_1` -> **`HEARTBEAT = HEALTHY`**.

---

## 6. RECUPERACIÓN DEL SCHEDULER Y ESTADO D21

* **Scheduler:** `MarketScheduleService` activo y monitoreando ventanas operativas cada 20 segundos.
* **Estado de D21:**
  * Estrategia: `D21_RangeCompress_5d`
  * StrategyStatus: `PAPER`
  * Fingerprint Inmutable: `f885ec2db2422308` (Verificado criptográficamente mediante hash SHA-256 de parámetros serializados).
  * TradingMode: `PAPER_TRADING`
* **Evaluación Post-Cierre de Hoy:**
  * Tarea: `daily_post_close_2026-11-12`
  * Horario Programado: `16:15:00 EST` (Se mantiene en cola natural para el cierre de mercado, sin adelantos ni ejecuciones manuales).

---

## 7. RECUPERACIÓN DE EXP-ST02 (SHADOW FORWARD)

* **Proceso Activo:** PID `10584` iniciado de forma autónoma con lockfile exclusivo `exp_st02_service.pid`.
* **Integridad Criptográfica:** 4 de 4 ledgers (`GLD-BASE`, `GLD-H5`, `DIA-BASE`, `DIA-H5`) auditados con encadenamiento SHA-256 válido (`(True, [])`).
* **Próxima Evaluación:** Ciclo 2 (10:30–11:30 ET) programado y listo para ejecución causal a las **11:31:30 EST**.

---

## 8. RECUPERACIÓN DE TELEGRAM

* **Configuración:** Token y Chat ID verificados, cliente `telegram_notifier` inicializado y conexión API con `@LaraMayaBot` verificada con respuesta HTTP 200.
* **Mensaje Operacional Despachado:**
  * Evento: `SYSTEM_RECOVERED`
  * Hora de Entrega: `2026-11-12 11:28:31 EST`
  * Resultado: `DELIVERED` (confirmado sin señales ni trades ficticios).

---

## 9. CONFIGURACIÓN DE AUTO-ARRANQUE RESILIENTE (AUTO-START IMPLEMENTATION)

Para evitar futuras interrupciones tras reinicios no programados del sistema:
1. **Script de Orquestación Maestro:** Creado en `C:\Users\edsel\Documents\trading-app-repo\scripts\auto_start_trading_agent.ps1` y `.bat`, que implementa la secuencia lógica estricta:
   - Espera de conectividad de red local (hasta 30s).
   - Intento de inicio de Moomoo OpenD.
   - Verificación de puerto 8090 e inicio de `run_superrobot.py` (FastAPI).
   - Verificación e inicio de `run_st02_service.py --daemon` (EXP-ST02).
   - Comprobación de `/health` en puerto 8090.
2. **Registro de Usuario en Windows:**
   - Registrado en `HKCU:\Software\Microsoft\Windows\CurrentVersion\Run` bajo el valor `AITradingAgent`.
   - Creado acceso directo `AITradingAgent_AlwaysOn.lnk` en la carpeta Startup del usuario (`shell:startup`).
3. **Instrucción para Programador de Tareas (Elevado):**
   Debido a que el registro a nivel de máquina (`AtStartup` sin sesión iniciada) requiere elevación UAC de Administrador, el script queda preparado para registrarse mediante una consola de Administrador con el comando:
   ```powershell
   Register-ScheduledTask -TaskName "AITradingAgent_AutoStart" -Action (New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\Users\edsel\Documents\trading-app-repo\scripts\auto_start_trading_agent.ps1" -WorkingDirectory "C:\Users\edsel\Documents\trading-app-repo") -Trigger (New-ScheduledTaskTrigger -AtStartup) -Settings (New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew) -User "SYSTEM" -Force
   ```

---

## 10. VALIDACIÓN DE REINICIO Y VEREDICTO FINAL

* **Prueba de Reinicio:** El entorno fue recuperado en caliente con éxito total, el auto-arranque quedó configurado en el registro de usuario (`HKCU\Run`) y en la carpeta Startup, pero la prueba de reinicio físico del equipo no fue ejecutada para no interrumpir la sesión interactiva del agente ni cortar la supervisión bursátil activa en curso.
* **Veredicto:**

# **RUNTIME_RECOVERED_AUTOSTART_NOT_VERIFIED**

*(Infraestructura de AI Trading Agent, Scheduler, Heartbeat, EXP-ST02 y Telegram plenamente recuperada y operativa; auto-arranque configurado y listo para verificación física en la próxima ventana de mantenimiento).*
