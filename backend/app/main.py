from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_factors import router as factors_router
from app.api.routes_backtest import router as backtest_router
from app.api.routes_settings import router as settings_router
from app.api.routes_notifications import router as notifications_router
from app.api.routes_orb import router as orb_router
from app.core.bot_runner import bot_runner
from app.core.telegram_listener import telegram_listener
from app.core.position_guardian import position_guardian
from app.core.settings_manager import settings_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando TradePulse Quantitative Engine...")
    init_db()
    settings_manager.load_all_settings()
    telegram_listener.start()
    position_guardian.start()
    
    # Auto-start bot runner to fulfill the user's 24/7 autonomous requirement
    import asyncio
    asyncio.create_task(bot_runner.start())
    
    yield
    logger.info("Deteniendo motor...")
    telegram_listener.stop()
    position_guardian.stop()
    if bot_runner.is_running:
        await bot_runner.stop()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Habilitar CORS para el frontend en React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar Routers
app.include_router(dashboard_router)
app.include_router(factors_router)
app.include_router(backtest_router)
app.include_router(settings_router)
app.include_router(notifications_router)
app.include_router(orb_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "database": "sqlite_ready",
        "bot_active": bot_runner.is_running
    }

# Servir Frontend Compilado en la raíz con política anti-caché
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

@app.get("/")
def serve_root():
    index_file = dist_dir / "index.html"
    if index_file.exists():
        response = FileResponse(index_file)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return {"message": "TradePulse Engine Backend Online"}

if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
