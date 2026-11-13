"""
news_collector.py
=================
Módulo recolector de noticias RSS en tiempo real ("Los Sentidos") para Oracle Bot.
Extrae titulares recientes sin dependencias de pago con timeout estricto de 5s por fuente
y tolerancia total a fallos (Fail-Safe silencioso).
"""

import calendar
import logging
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import feedparser

logger = logging.getLogger(__name__)


class NewsCollector:
    """Recolector ligero de titulares financieros vía RSS (Yahoo Finance, CNBC, MarketWatch)."""

    DEFAULT_TIMEOUT_SECONDS = 5
    DEFAULT_MAX_HEADLINES = 15
    DEFAULT_LOOKBACK_HOURS = 2.0

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_headlines: int = DEFAULT_MAX_HEADLINES,
        lookback_hours: float = DEFAULT_LOOKBACK_HOURS,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_headlines = max_headlines
        self.lookback_hours = lookback_hours

    @staticmethod
    def clean_ticker(moomoo_ticker: str) -> str:
        """
        Recibe el ticker en formato Moomoo (ej. 'US.QQQ', 'US.SPY', 'US.NVDA')
        y devuelve el símbolo limpio ('QQQ').
        """
        if not moomoo_ticker:
            return ""
        cleaned = str(moomoo_ticker).strip().upper()
        if cleaned.startswith("US."):
            cleaned = cleaned[3:]
        elif "." in cleaned:
            cleaned = cleaned.split(".")[-1]
        return cleaned.strip()

    def _build_rss_urls(self, clean_symbol: str) -> List[str]:
        """Construye las 3 fuentes RSS requeridas."""
        return [
            f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={clean_symbol}&region=US&lang=en-US",
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
            "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        ]

    @staticmethod
    def _parse_entry_datetime(entry: dict) -> Optional[datetime]:
        """Extrae la fecha UTC de una entrada de feedparser si está disponible."""
        time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if time_struct:
            try:
                timestamp = calendar.timegm(time_struct)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except Exception:
                return None
        return None

    def _fetch_single_feed(self, url: str) -> List[dict]:
        """Descarga y parsea una fuente RSS con timeout estricto de 5 segundos."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw_bytes = response.read()
            parsed = feedparser.parse(raw_bytes)
            return list(getattr(parsed, "entries", []))
        except Exception as exc:
            logger.debug(f"NewsCollector: fallo silencioso al consultar RSS ({url}): {exc}")
            return []

    def get_recent_headlines(self, moomoo_ticker: str) -> List[str]:
        """
        Consulta las 3 fuentes RSS para el ticker indicado, filtra por las últimas
        2 horas, elimina duplicados y retorna hasta 15 titulares recientes.
        En caso de fallo de red o excepción, devuelve [] silenciosamente.
        """
        try:
            clean_sym = self.clean_ticker(moomoo_ticker)
            if not clean_sym:
                return []

            urls = self._build_rss_urls(clean_sym)
            now_utc = datetime.now(timezone.utc)
            cutoff_utc = now_utc - timedelta(hours=self.lookback_hours)

            recent_items = []
            seen_normalized = set()

            for url in urls:
                entries = self._fetch_single_feed(url)
                for entry in entries:
                    title = str(entry.get("title", "")).strip()
                    if not title:
                        continue

                    pub_dt = self._parse_entry_datetime(entry)
                    if pub_dt is not None and pub_dt < cutoff_utc:
                        continue

                    norm_title = " ".join(title.lower().split())
                    if norm_title in seen_normalized:
                        continue

                    seen_normalized.add(norm_title)
                    sort_ts = pub_dt.timestamp() if pub_dt is not None else now_utc.timestamp()
                    recent_items.append((sort_ts, title))

            # Ordenar de más reciente a más antiguo y limitar a los últimos 15 titulares
            recent_items.sort(key=lambda item: item[0], reverse=True)
            return [title for _, title in recent_items[: self.max_headlines]]
        except Exception as exc:
            logger.debug(f"NewsCollector: excepción global capturada en get_recent_headlines: {exc}")
            return []


def collect_news(moomoo_ticker: str) -> List[str]:
    """Función auxiliar directa para obtener los últimos 15 titulares recientes."""
    return NewsCollector().get_recent_headlines(moomoo_ticker)
