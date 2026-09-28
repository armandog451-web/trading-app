import os
import json

base_dir = r"C:\Users\edsel\OneDrive\Documents\PROJET 2"
files_to_push = [
    "config.py",
    "database.py",
    "broker.py",
    "guardian.py",
    "engine.py",
    "server.py",
    "telegram_service.py",
    "start.bat",
    "start.ps1",
    "requirements.txt",
    ".env.example",
    "README.md",
    "INICIAR_24_7_AUTOMATICO.bat",
    "INSTALADOR_OTRA_PC.bat",
    "INSTALAR_ARRANQUE_CON_WINDOWS.bat",
    "create_desktop_shortcut.ps1",
    "templates/dashboard.html"
]

res = []
for rel in files_to_push:
    full = os.path.join(base_dir, rel.replace("/", os.sep))
    if os.path.exists(full):
        with open(full, "r", encoding="utf-8") as f:
            res.append({"path": rel, "content": f.read()})

out_path = os.path.join(base_dir, "github_payload.json")
with open(out_path, "w", encoding="utf-8") as out:
    json.dump(res, out)

print(f"Generated payload with {len(res)} files at {out_path}")
