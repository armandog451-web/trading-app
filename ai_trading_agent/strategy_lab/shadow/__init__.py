"""
ai_trading_agent.strategy_lab.shadow
====================================
Módulo de Validación Prospectiva Autónoma (Frozen Forward Shadow Validation - Fase 7.4).
Proporciona:
- Congelamiento criptográfico de estrategias candidatas (SHA-256 de 64 caracteres).
- Ledgers inmutables de evidencia encadenada (Append-Only Cryptographic Ledger).
- Simulador de ejecución causal realista (Señal en Cierre T -> Fill en Apertura T+1).
- Relojes de validación prospectiva independientes y control de hitos (20, 60, 90 sesiones).
- Aislamiento físico 100% verificado respecto a brokers y respecto a D21.
"""

from .campaign_models import (
    ShadowCampaignStatus,
    CostScenario,
    ShadowValidationClock,
    ShadowPosition,
    ShadowLedgerEntry,
    CampaignFreezeManifest
)
from .crypto_ledger import ShadowEvidenceLedger
from .shadow_simulator import ShadowExecutionSimulator
from .shadow_evaluator import AutonomousShadowEvaluator

__all__ = [
    "ShadowCampaignStatus",
    "CostScenario",
    "ShadowValidationClock",
    "ShadowPosition",
    "ShadowLedgerEntry",
    "CampaignFreezeManifest",
    "ShadowEvidenceLedger",
    "ShadowExecutionSimulator",
    "AutonomousShadowEvaluator"
]
