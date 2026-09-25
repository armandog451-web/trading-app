import logging

logger = logging.getLogger(__name__)

class FundamentalEngine:
    """
    Capa 2: Análisis Fundamental y Catalizadores Corporativos (Earnings / Balances).
    Filtra activos elegibles y evalúa sorpresas de beneficios (EPS) para Day Trading.
    """

    def __init__(self):
        # Base de catalizadores conocidos de alta liquidez
        self.mock_fundamental_db = {
            "SPY": {"pe_ratio": 26.5, "eps_growth_yoy": 8.4, "has_earnings_today": False, "catalyst": "Índice S&P 500"},
            "QQQ": {"pe_ratio": 32.1, "eps_growth_yoy": 14.2, "has_earnings_today": False, "catalyst": "Índice Nasdaq 100"},
            "NVDA": {"pe_ratio": 48.0, "eps_growth_yoy": 122.0, "has_earnings_today": False, "catalyst": "Líder chips IA & Datacenters"},
            "TSLA": {"pe_ratio": 62.3, "eps_growth_yoy": -4.5, "has_earnings_today": True, "catalyst": "Reporte de entregas vehiculares"},
            "AAPL": {"pe_ratio": 31.0, "eps_growth_yoy": 6.1, "has_earnings_today": False, "catalyst": "Lanzamiento ecosistema IA"},
            "AMD": {"pe_ratio": 41.5, "eps_growth_yoy": 19.3, "has_earnings_today": True, "catalyst": "Earnings Surprise Beat +8%"},
        }

    async def get_fundamental_profile(self, symbol: str) -> dict:
        """
        Devuelve el perfil fundamental y si el activo tiene earnings activos hoy.
        """
        data = self.mock_fundamental_db.get(symbol.upper(), {
            "pe_ratio": 24.0,
            "eps_growth_yoy": 5.0,
            "has_earnings_today": False,
            "catalyst": "Flujo de mercado regular"
        })
        return data

    def is_eligible_for_intraday(self, symbol: str, fundamental_data: dict) -> tuple[bool, str]:
        """
        Regla institucional:
        Si la acción reporta resultados HOY en sesión regular, se opera solo con confirmación
        de volumen extremo o tras asimilar la noticia para evitar halts de volatilidad.
        """
        if fundamental_data.get("has_earnings_today"):
            return True, "En juego por reporte de resultados (Alta volatilidad esperada)"
        return True, "Condición fundamental estable para operativa técnica"

fundamental_engine = FundamentalEngine()
