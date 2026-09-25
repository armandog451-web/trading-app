import os
import shutil
from pathlib import Path

def export_project():
    root = Path(__file__).resolve().parent
    desktop = Path(os.environ.get("USERPROFILE", "")) / "OneDrive" / "Desktop"
    if not desktop.exists():
        desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"

    zip_base = desktop / "TradePulse_Paquete_Completo"
    temp_dir = Path(os.environ.get("TEMP", ".")) / "TradePulseExport"

    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"Preparando exportación desde: {root}")

    # Ignorar carpetas pesadas e innecesarias
    ignore_patterns = shutil.ignore_patterns("node_modules", "__pycache__", ".git", "*.pyc", "watchdog.log", ".pytest_cache")

    # Copiar contenido
    shutil.copytree(root, temp_dir / "trading-app", ignore=ignore_patterns, dirs_exist_ok=True)

    # Crear ZIP
    print(f"Comprimiendo archivo ZIP en: {zip_base}.zip...")
    archive_path = shutil.make_archive(str(zip_base), "zip", temp_dir)

    # Limpiar temp
    shutil.rmtree(temp_dir, ignore_errors=True)

    size_mb = os.path.getsize(archive_path) / (1024 * 1024)
    print(f"\n[EXITO] Paquete exportado correctamente:")
    print(f"Ruta: {archive_path}")
    print(f"Tamaño: {size_mb:.2f} MB")

if __name__ == "__main__":
    export_project()
