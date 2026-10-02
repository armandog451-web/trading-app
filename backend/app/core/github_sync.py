import os
import sys
import json
import shutil
import logging
import datetime
import threading
import subprocess
from pathlib import Path

logger = logging.getLogger("github_sync")

def get_git_exe() -> str:
    """Localiza el ejecutable de Git en el sistema o en instalaciones locales de GitHub Desktop."""
    possible_paths = [
        r"C:\Users\edsel\AppData\Local\GitHubDesktop\app-3.6.6\resources\app\git\cmd\git.exe",
        r"C:\Users\edsel\AppData\Local\GitHubDesktop\app-3.6.6\resources\app\git\mingw64\bin\git.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\GitHubDesktop\app-3.6.6\resources\app\git\cmd\git.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
    ]
    for p in possible_paths:
        if os.path.isfile(p):
            return p

    # Búsqueda dinámica en carpetas de GitHub Desktop
    gh_dir = os.path.expandvars(r"%LOCALAPPDATA%\GitHubDesktop")
    if os.path.isdir(gh_dir):
        for root, _, files in os.walk(gh_dir):
            if "git.exe" in files and ("cmd" in root or "bin" in root):
                return os.path.join(root, "git.exe")

    which_git = shutil.which("git")
    if which_git:
        return which_git

    return "git"

def get_github_token() -> str:
    """Recupera el token personal de GitHub para operaciones no interactivas."""
    token_file = Path(r"C:\Users\edsel\OneDrive\Documents\TRADING N8N\Token GitHub.txt")
    if token_file.exists():
        try:
            tok = token_file.read_text(encoding="utf-8").strip()
            if tok:
                return tok
        except Exception as e:
            logger.warning(f"Error leyendo Token GitHub.txt: {e}")

    return os.environ.get("GITHUB_TOKEN", "")

def ensure_remote_authenticated(repo_dir: Path, git_exe: str):
    """Garantiza que la URL de origen incluya el token para evitar prompts interactivos."""
    token = get_github_token()
    if not token:
        return
    try:
        res = subprocess.run([git_exe, "remote", "get-url", "origin"], cwd=repo_dir, capture_output=True, text=True)
        url = res.stdout.strip()
        auth_url = f"https://armandog451-web:{token}@github.com/armandog451-web/trading-app.git"
        if "github.com/armandog451-web/trading-app" in url and token not in url:
            subprocess.run([git_exe, "remote", "set-url", "origin", auth_url], cwd=repo_dir, capture_output=True, text=True)
            logger.info("GitHubSync: Remote origin autenticado exitosamente con token.")
    except Exception as e:
        logger.warning(f"GitHubSync: No se pudo verificar remote origin: {e}")

def save_config_snapshot(repo_dir: Path):
    """Genera y guarda una copia estructurada de la configuración activa en trade_config.json."""
    try:
        from app.config import settings
        from app.engines.risk_engine import risk_engine
        config_data = {
            "updated_at": datetime.datetime.now().isoformat(),
            "app_name": getattr(settings, "APP_NAME", "TradePulse"),
            "risk": {
                "max_daily_loss_pct": getattr(risk_engine, "max_daily_loss_pct", 2.0),
                "risk_per_trade_pct": getattr(risk_engine, "risk_per_trade_pct", 1.0),
                "min_rr_ratio": getattr(risk_engine, "min_rr_ratio", 2.0),
                "auto_square_off_time": getattr(risk_engine, "auto_square_off_time", "15:50"),
                "max_open_positions": getattr(settings, "MAX_OPEN_POSITIONS", 3),
                "max_option_cost_per_contract": getattr(settings, "MAX_OPTION_COST_PER_CONTRACT", 200.0)
            },
            "broker": {
                "active_broker": getattr(settings, "ACTIVE_BROKER", "MOOMOO"),
                "auto_execute_trades": getattr(settings, "AUTO_EXECUTE_TRADES", False),
                "alpaca_paper": getattr(settings, "ALPACA_PAPER", True),
                "moomoo_host": getattr(settings, "MOOMOO_HOST", "127.0.0.1"),
                "moomoo_port": getattr(settings, "MOOMOO_PORT", 11111),
                "moomoo_paper": getattr(settings, "MOOMOO_PAPER", True),
                "moomoo_acc_id": getattr(settings, "MOOMOO_ACC_ID", 0)
            },
            "notifications": {
                "telegram_active": bool(getattr(settings, "TELEGRAM_BOT_TOKEN", "") and getattr(settings, "TELEGRAM_CHAT_ID", "")),
                "telegram_chat_id": getattr(settings, "TELEGRAM_CHAT_ID", ""),
                "notify_market_close": getattr(settings, "NOTIFY_MARKET_CLOSE", False)
            }
        }
        config_path = repo_dir / "trade_config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        logger.info(f"GitHubSync: Snapshot de configuración guardado en {config_path}")
    except Exception as e:
        logger.error(f"GitHubSync: Error guardando snapshot de configuración: {e}")

def perform_git_sync(reason: str = "Configuración actualizada") -> dict:
    """
    Ejecuta un ciclo completo de sincronización hacia GitHub:
    1. Guarda el snapshot de configuración (trade_config.json).
    2. Agrega los archivos modificados a Git staging.
    3. Si hay cambios, realiza commit descriptivo y push a origin main.
    """
    from app.config import settings
    repo_dir = Path(settings.BASE_DIR)
    git_exe = get_git_exe()
    ensure_remote_authenticated(repo_dir, git_exe)
    save_config_snapshot(repo_dir)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GCM_INTERACTIVE": "never"
    }

    try:
        # 1. git add .
        subprocess.run([git_exe, "add", "."], cwd=repo_dir, capture_output=True, text=True, check=True)

        # 2. Verificar si hay cambios preparados o modificados
        status_res = subprocess.run([git_exe, "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True)
        if not status_res.stdout.strip():
            logger.info("GitHubSync: No hay cambios pendientes por commitear.")
            return {
                "success": True,
                "changed": False,
                "message": f"Repositorio al día. No hay cambios pendientes por subir. [{now_str}]"
            }

        # 3. Commit
        commit_msg = f"Auto-sync TradePulse: {reason} [{now_str}]"
        commit_res = subprocess.run([git_exe, "commit", "-m", commit_msg], cwd=repo_dir, capture_output=True, text=True)
        if commit_res.returncode != 0:
            err = commit_res.stderr or commit_res.stdout
            logger.error(f"GitHubSync: Fallo al crear commit: {err}")
            return {
                "success": False,
                "message": f"Error al registrar cambios localmente: {err}",
                "detail": err
            }

        # 4. Push
        push_res = subprocess.run([git_exe, "push", "origin", "main"], cwd=repo_dir, capture_output=True, text=True, timeout=25, env=env)
        if push_res.returncode == 0:
            logger.info(f"GitHubSync: Push exitoso a GitHub: {commit_msg}")
            return {
                "success": True,
                "changed": True,
                "message": f"¡Sincronización exitosa con GitHub! [{now_str}]",
                "detail": push_res.stdout or commit_res.stdout
            }
        else:
            err_msg = push_res.stderr or push_res.stdout
            logger.error(f"GitHubSync: Error en git push: {err_msg}")
            return {
                "success": False,
                "message": f"Error al subir cambios a GitHub: {err_msg}",
                "detail": err_msg
            }

    except subprocess.TimeoutExpired:
        logger.error("GitHubSync: Tiempo de espera agotado al conectar con GitHub.")
        return {
            "success": False,
            "message": "Tiempo de espera agotado al conectar con GitHub (Timeout 25s).",
            "detail": "Git push timed out"
        }
    except Exception as e:
        logger.error(f"GitHubSync: Error inesperado durante sincronización: {e}")
        return {
            "success": False,
            "message": f"Error inesperado ejecutando sincronización: {str(e)}",
            "detail": str(e)
        }

class GitHubAutoSyncManager:
    """Manejador debounced para ejecutar auto-sincronizaciones en segundo plano."""
    def __init__(self, debounce_seconds: float = 2.0):
        self.debounce_seconds = debounce_seconds
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._reasons: list[str] = []

    def trigger_sync(self, reason: str = "Configuración actualizada"):
        with self._lock:
            if reason not in self._reasons:
                self._reasons.append(reason)
            if self._timer and self._timer.is_alive():
                self._timer.cancel()
            
            self._timer = threading.Timer(self.debounce_seconds, self._run_debounced_sync)
            self._timer.daemon = True
            self._timer.start()

    def _run_debounced_sync(self):
        with self._lock:
            combined_reason = ", ".join(self._reasons) if self._reasons else "Configuración actualizada"
            self._reasons.clear()
            self._timer = None

        logger.info(f"GitHubAutoSyncManager: Ejecutando sync programado: {combined_reason}")
        res = perform_git_sync(reason=combined_reason)
        logger.info(f"GitHubAutoSyncManager: Fin de sincronización -> {res.get('message')}")
        return res

auto_sync_manager = GitHubAutoSyncManager()
