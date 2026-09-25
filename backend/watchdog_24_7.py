"""
TradePulse & Moomoo 24/7 Watchdog Supervisor
Garantiza que Moomoo OpenD y el motor TradePulse se mantengan siempre
activos, auto-recuperándose de caídas, cortes de red o reinicios sin intervención humana.
"""
import os
import sys
import time
import socket
import logging
import subprocess
from pathlib import Path

# Configurar logging
log_file = Path(__file__).resolve().parent / "watchdog.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [WATCHDOG]: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Watchdog247")

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
PYTHON_EXE = sys.executable

# Rutas estándar de Moomoo OpenD
OPEND_PATHS = [
    Path(os.environ.get("APPDATA", "")) / "moomoo_OpenD" / "moomoo_OpenD.exe",
    Path("C:/Program Files/moomoo/OpenD/moomoo_OpenD.exe"),
    Path("C:/Program Files (x86)/moomoo/OpenD/moomoo_OpenD.exe")
]

def find_opend_exe() -> Path | None:
    for p in OPEND_PATHS:
        if p.exists():
            return p
    return None

def is_port_open(host: str = "127.0.0.1", port: int = 11111, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def is_process_running(proc_name: str) -> bool:
    try:
        res = subprocess.check_output(f'tasklist /FI "IMAGENAME eq {proc_name}" /NH', shell=True, text=True)
        return proc_name.lower() in res.lower()
    except Exception:
        return False

def check_backend_alive() -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=2.0) as resp:
            return resp.status == 200
    except Exception:
        return False

def main_loop():
    logger.info("==========================================================")
    logger.info("TradePulse & Moomoo 24/7 Watchdog Supervisor Iniciado")
    logger.info("Modo: Supervisión Continua Sin Intervención Humana")
    logger.info("==========================================================")

    backend_proc = None

    while True:
        try:
            # 1. Supervisar Moomoo OpenD (Puerto 11111)
            if not is_port_open("127.0.0.1", 11111):
                logger.warning("Moomoo OpenD no responde en el puerto 11111. Reiniciando proceso...")
                if is_process_running("moomoo_OpenD.exe"):
                    subprocess.run("taskkill /F /IM moomoo_OpenD.exe", shell=True, capture_output=True)
                    time.sleep(2)
                opend_exe = find_opend_exe()
                if opend_exe:
                    logger.info(f"Lanzando Moomoo OpenD limpiamente: {opend_exe}")
                    subprocess.Popen(str(opend_exe), cwd=str(opend_exe.parent), shell=False)
                    time.sleep(5)
                else:
                    logger.error("No se encontró el ejecutable moomoo_OpenD.exe en las rutas habituales.")

            # 2. Supervisar TradePulse Backend (Puerto 8000)
            if not check_backend_alive():
                logger.warning("TradePulse Backend no responde en http://127.0.0.1:8000. Re-arrancando motor...")
                # Matar procesos huérfanos que puedan tener el puerto tomado
                try:
                    subprocess.run('taskkill /F /FI "WINDOWTITLE eq TradePulse*" /T', shell=True, capture_output=True)
                except Exception:
                    pass

                run_script = BACKEND_DIR / "run.py"
                backend_proc = subprocess.Popen(
                    [PYTHON_EXE, str(run_script)],
                    cwd=str(BACKEND_DIR),
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
                logger.info(f"TradePulse Backend iniciado con PID: {backend_proc.pid}")
                time.sleep(4)

        except Exception as e:
            logger.error(f"Error en bucle del watchdog: {e}")

        time.sleep(10)

if __name__ == "__main__":
    main_loop()
