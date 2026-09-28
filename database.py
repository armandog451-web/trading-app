import sqlite3
from datetime import datetime
from config import DB_PATH, DEMO_CAPITAL

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabla de señales y órdenes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        qty INTEGER NOT NULL,
        price REAL NOT NULL,
        stop_loss REAL NOT NULL,
        take_profit REAL NOT NULL,
        rr_ratio REAL NOT NULL,
        strategy TEXT NOT NULL,
        rationale TEXT NOT NULL,
        confidence REAL NOT NULL,
        status TEXT NOT NULL, -- PENDIENTE, EJECUTADA, CANCELADA, RECHAZADA
        broker TEXT NOT NULL,
        telegram_message_id INTEGER,
        pnl REAL DEFAULT 0.0,
        created_at TEXT NOT NULL,
        executed_at TEXT
    )
    """)
    
    # Tabla de aprendizaje y ponderación de estrategias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy_metrics (
        name TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        description TEXT NOT NULL,
        weight REAL NOT NULL DEFAULT 1.0,
        total_trades INTEGER NOT NULL DEFAULT 0,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        win_rate REAL NOT NULL DEFAULT 0.0,
        total_pnl REAL NOT NULL DEFAULT 0.0,
        last_updated TEXT NOT NULL
    )
    """)

    # Tabla de configuración en caliente
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # Tabla de logs del sistema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL
    )
    """)

    # Inicializar métricas base de las estrategias de los videos si no existen
    cursor.execute("SELECT COUNT(*) FROM strategy_metrics")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        initial_strategies = [
            (
                "trend_following",
                "Tendencia & Cruce EMA 20/50/200",
                "Identificación de tendencia institucional y retrocesos a medias dinámicas.",
                1.0, 14, 10, 4, 71.4, 2840.50, now
            ),
            (
                "mean_reversion",
                "Reversión a la Media (RSI + Bollinger)",
                "Detección de agotamiento extremo en zonas de sobrecompra/sobreventa.",
                1.1, 12, 8, 4, 66.7, 1920.00, now
            ),
            (
                "liquidity_breakout",
                "Ruptura de Liquidez & Order Blocks",
                "Barridos de máximos/mínimos intradiarios con expansión de volumen.",
                1.2, 10, 7, 3, 70.0, 3150.20, now
            ),
            (
                "vwap_pullback",
                "Rebote VWAP Institucional",
                "Testeo de nivel institucional VWAP con confirmación de velas.",
                0.9, 8, 5, 3, 62.5, 1100.00, now
            )
        ]
        cursor.executemany("""
            INSERT INTO strategy_metrics 
            (name, display_name, description, weight, total_trades, wins, losses, win_rate, total_pnl, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, initial_strategies)

    conn.commit()
    conn.close()

def log_event(level: str, message: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level, message))
    conn.commit()
    conn.close()
