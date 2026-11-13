"""
Módulo: ai_judge.py (El Criterio en 4 Niveles)
==============================================
Evalúa señales de trading combinando:
  - Filtro 1: Regla Monetaria Mecánica (Stop de Pérdida Diaria).
  - Filtro 2: IA Rápida (Triaje < 1s con gemini-3.8-flash).
  - Filtro 3: IA Profunda (Segunda Opinión con gemini-4-argon sólo en caso de DOUBT).
  - Filtro 4: Fail-Safe Obligatorio (ante cualquier fallo técnico, aprueba la orden técnica original).
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Cargar variables de entorno desde el repositorio canónico si existen
_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH, override=False)
else:
    load_dotenv(override=False)


class TradingAgentJudge:
    """
    Juez Interceptor de Noticias y Riesgo con IA en 4 niveles.
    Prioriza Gemini (google-genai SDK con Interactions API: gemini-3.8-flash / gemini-4-argon),
    con soporte de respaldo para OpenAI o Anthropic si están configurados en .env.
    """

    # Nota de arquitectura: según las directrices actuales del SDK google-genai,
    # gemini-2.5-flash y gemini-2.5-pro están deprecados y han sido sustituidos por
    # gemini-3.8-flash (modelo rápido de triaje) y gemini-4-argon (modelo profundo de razonamiento).
    FAST_GEMINI_MODEL = "gemini-3.8-flash"
    DEEP_GEMINI_MODEL = "gemini-4-argon"

    def __init__(
        self,
        max_daily_loss_usd: Optional[float] = None,
        fast_timeout_seconds: float = 8.0,
        deep_timeout_seconds: float = 12.0,
    ) -> None:
        if max_daily_loss_usd is not None:
            self.max_daily_loss_usd = abs(float(max_daily_loss_usd))
        else:
            env_loss = os.getenv("MAX_DAILY_LOSS", "10000.0")
            try:
                self.max_daily_loss_usd = abs(float(env_loss))
            except (ValueError, TypeError):
                self.max_daily_loss_usd = 10000.0

        self.fast_timeout_seconds = float(fast_timeout_seconds)
        self.deep_timeout_seconds = float(deep_timeout_seconds)

        # Detección de proveedor de IA configurado en entorno (.env)
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

        self.provider: Optional[str] = None
        if self.gemini_api_key:
            self.provider = "gemini"
        elif self.openai_api_key:
            self.provider = "openai"
        elif self.anthropic_api_key:
            self.provider = "anthropic"

    @staticmethod
    def _extract_json(raw_text: str) -> Dict[str, Any]:
        """Extrae y parsea un bloque JSON de la respuesta del modelo de forma segura."""
        if not raw_text:
            raise ValueError("Respuesta vacía del modelo de IA")

        cleaned = raw_text.strip()
        # Eliminar bloques markdown ```json ... ``` si existen
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
        if fence_match:
            cleaned = fence_match.group(1).strip()
        else:
            brace_match = re.search(r"(\{.*\})", cleaned, flags=re.DOTALL)
            if brace_match:
                cleaned = brace_match.group(1).strip()

        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("El JSON devuelto no es un objeto diccionario")
        return parsed

    def _call_llm(self, prompt: str, system_instruction: str, tier: str = "fast") -> Dict[str, Any]:
        """
        Invoca al proveedor de IA configurado con un timeout estricto.
        tier: 'fast' (Filtro 2) o 'deep' (Filtro 3).
        """
        if not self.provider:
            raise RuntimeError(
                "No se encontró GEMINI_API_KEY, OPENAI_API_KEY ni ANTHROPIC_API_KEY en el entorno (.env)"
            )

        timeout = self.fast_timeout_seconds if tier == "fast" else self.deep_timeout_seconds

        def _invoke() -> str:
            if self.provider == "gemini":
                from google import genai

                client = genai.Client(api_key=self.gemini_api_key)
                model_name = (
                    self.FAST_GEMINI_MODEL if tier == "fast" else self.DEEP_GEMINI_MODEL
                )
                interaction = client.interactions.create(
                    model=model_name,
                    system_instruction=system_instruction,
                    input=prompt,
                )
                return interaction.output_text or ""

            if self.provider == "openai":
                import urllib.request

                model_name = "gpt-4o-mini" if tier == "fast" else "gpt-4o"
                payload = json.dumps(
                    {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt},
                        ],
                        "response_format": {"type": "json_object"},
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.openai_api_key}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    return body["choices"][0]["message"]["content"]

            if self.provider == "anthropic":
                import urllib.request

                model_name = (
                    "claude-3-5-haiku-latest"
                    if tier == "fast"
                    else "claude-3-7-sonnet-latest"
                )
                payload = json.dumps(
                    {
                        "model": model_name,
                        "max_tokens": 300,
                        "system": system_instruction,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    return body["content"][0]["text"]

            raise RuntimeError(f"Proveedor desconocido: {self.provider}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_invoke)
            raw_output = future.result(timeout=timeout)

        return self._extract_json(raw_output)

    def evaluate_signal(
        self,
        signal: Dict[str, Any],
        headlines: List[str],
        current_daily_pnl: float,
    ) -> Dict[str, Any]:
        """
        Evalúa una señal técnica aplicando las 4 reglas inquebrantables en orden:
          1. Filtro 1 (Regla Monetaria Mecánica)
          2. Filtro 2 (IA Rápida - Triaje < 1s)
          3. Filtro 3 (IA Profunda - Segunda Opinión si Filtro 2 = DOUBT)
          4. Filtro 4 (Fail-Safe obligatorio ante cualquier excepción técnica)
        """
        # =====================================================================
        # FILTRO 1: Regla Monetaria Mecánica (Sin llamar a la IA)
        # =====================================================================
        try:
            pnl_val = float(current_daily_pnl)
        except (ValueError, TypeError):
            pnl_val = 0.0

        if pnl_val <= -abs(self.max_daily_loss_usd):
            return {
                "allow_trade": False,
                "step_triggered": "STEP_1_RISK_GUARD",
                "reason": "Límite de pérdida diaria alcanzado",
            }

        # =====================================================================
        # FILTROS 2 y 3 envueltos en FILTRO 4 (Fail-Safe Obligatorio)
        # =====================================================================
        try:
            # Si no hay titulares recientes, aprobar inmediatamente sin latencia
            if not headlines:
                return {
                    "allow_trade": True,
                    "step_triggered": "STEP_2_FAST_AI",
                    "reason": "Sin titulares recientes en las últimas 2 horas; orden técnica aprobada.",
                }

            symbol = str(signal.get("symbol") or signal.get("ticker") or "UNKNOWN")
            direction = str(signal.get("direction") or signal.get("side") or "LONG").upper()
            strategy = str(signal.get("strategy") or signal.get("strategy_id") or "ORACLE_STRATEGY")

            numbered_headlines = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(headlines[:15]))

            # -----------------------------------------------------------------
            # FILTRO 2: IA Rápida (Triaje < 1s)
            # -----------------------------------------------------------------
            fast_system = (
                "Eres un Juez de Riesgo Algorítmico institucional en Wall Street. "
                "Debes responder ÚNICAMENTE con un objeto JSON válido sin texto adicional."
            )
            fast_prompt = (
                f"Señal técnica generada por estrategia '{strategy}':\n"
                f"- Activo: {symbol}\n"
                f"- Dirección de la orden: {direction}\n\n"
                f"Titulares recientes (últimas 2 horas):\n{numbered_headlines}\n\n"
                "Reglas de decisión:\n"
                "1. Emite 'BLOCK' ÚNICAMENTE si hay un evento macroeconómico crítico en curso "
                "(CPI, decisión de tasas Fed/FOMC, NFP, guerra/cisne negro) o una noticia "
                f"directamente catastrófica y contraria a la dirección {direction} del activo {symbol}.\n"
                "2. Emite 'ALLOW' si las noticias son neutrales, favorables o irrelevantes para el trade.\n"
                "3. Emite 'DOUBT' si existen titulares mixtos o ambiguos que requieran una segunda opinión profunda.\n\n"
                "Responde ESTRICTAMENTE en este formato JSON (con 'reason' en español):\n"
                '{"verdict": "ALLOW" | "BLOCK" | "DOUBT", "reason": "explicación concisa en español"}'
            )

            fast_result = self._call_llm(fast_prompt, fast_system, tier="fast")
            verdict = str(fast_result.get("verdict", "")).upper().strip()
            reason = str(fast_result.get("reason", "Evaluación rápida completada.")).strip()

            if verdict == "ALLOW":
                return {
                    "allow_trade": True,
                    "step_triggered": "STEP_2_FAST_AI",
                    "reason": reason,
                }

            if verdict == "BLOCK":
                return {
                    "allow_trade": False,
                    "step_triggered": "STEP_2_FAST_AI",
                    "reason": reason,
                }

            if verdict != "DOUBT":
                raise ValueError(f"Veredicto desconocido en Filtro 2: {verdict}")

            # -----------------------------------------------------------------
            # FILTRO 3: IA Profunda (Segunda Opinión sólo si Filtro 2 = DOUBT)
            # -----------------------------------------------------------------
            deep_system = (
                "Eres el Comité Senior de Riesgo Cuantitativo. Analiza titulares ambiguos, "
                "cuenta cuántos son alcistas (bullish_count) versus bajistas (bearish_count) "
                "y toma la decisión final ALLOW o BLOCK. Responde ÚNICAMENTE en JSON válido."
            )
            deep_prompt = (
                f"El triaje rápido reportó DOUBT ({reason}) para la señal:\n"
                f"- Activo: {symbol}\n"
                f"- Dirección: {direction}\n"
                f"- Estrategia: {strategy}\n\n"
                f"Titulares recientes:\n{numbered_headlines}\n\n"
                "Instrucciones:\n"
                "1. Cuenta cuántos titulares son alcistas (bullish_count) y cuántos bajistas (bearish_count).\n"
                f"2. Decide finalmente 'ALLOW' o 'BLOCK' para la operación {direction} en {symbol}.\n\n"
                "Responde ESTRICTAMENTE en este formato JSON (con 'reason' en español):\n"
                '{"bullish_count": 0, "bearish_count": 0, "verdict": "ALLOW" | "BLOCK", "reason": "explicación detallada en español"}'
            )

            deep_result = self._call_llm(deep_prompt, deep_system, tier="deep")
            deep_verdict = str(deep_result.get("verdict", "")).upper().strip()
            bullish_count = int(deep_result.get("bullish_count", 0))
            bearish_count = int(deep_result.get("bearish_count", 0))
            deep_reason = str(
                deep_result.get("reason", "Segunda opinión completada.")
            ).strip()

            if deep_verdict not in ("ALLOW", "BLOCK"):
                raise ValueError(f"Veredicto inválido en Filtro 3: {deep_verdict}")

            return {
                "allow_trade": deep_verdict == "ALLOW",
                "step_triggered": "STEP_3_DEEP_AI",
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
                "reason": (
                    f"[Alcistas: {bullish_count} | Bajistas: {bearish_count}] {deep_reason}"
                ),
            }

        except Exception as exc:
            # =================================================================
            # FILTRO 4: Fail-Safe Obligatorio (Bypass de seguridad)
            # =================================================================
            logger.warning(
                "AI Judge Fail-Safe activado (%s). Se aprueba la orden por defecto.",
                exc,
            )
            return {
                "allow_trade": True,
                "step_triggered": "FAIL_SAFE_BYPASS",
                "reason": f"Fail-Safe activado ({type(exc).__name__}: {exc}). Orden técnica permitida sin bloqueo.",
            }
