"""
ai_trading_agent.strategy_lab.experiments.exp_st02.shadow_models
================================================================
Modelos fuertemente tipados para la campaña Frozen Forward Shadow (EXP-ST02).

Campaña: CAMP-SHADOW-EXP-ST02-2026
Máquina de estados estricta y aislamiento forense sin broker.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ShadowExpSt02State(str, Enum):
    PENDING_AUDIT = "PENDING_AUDIT"
    AUDITING_EXP_ST01 = "AUDITING_EXP_ST01"
    AUDIT_PASS = "AUDIT_PASS"
    AUDIT_FAIL = "AUDIT_FAIL"
    AUDIT_INCONCLUSIVE = "AUDIT_INCONCLUSIVE"
    FREEZE_CANDIDATES = "FREEZE_CANDIDATES"
    VALIDATE_H5 = "VALIDATE_H5"
    SHADOW_PREFLIGHT = "SHADOW_PREFLIGHT"
    PREFLIGHT_PASS = "PREFLIGHT_PASS"
    PREFLIGHT_FAIL = "PREFLIGHT_FAIL"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    FORWARD_SHADOW_ACTIVE = "FORWARD_SHADOW_ACTIVE"
    COLLECTING_DATA = "COLLECTING_DATA"
    BLOCKED = "BLOCKED"


class ShadowEventTypeST02(str, Enum):
    GENESIS = "GENESIS"
    HEARTBEAT = "HEARTBEAT"
    NO_SIGNAL = "NO_SIGNAL"
    NO_TRADE = "NO_TRADE"
    SIGNAL_DETECTED = "SIGNAL_DETECTED"
    ORDER_SIMULATED = "ORDER_SIMULATED"
    FILL_SIMULATED = "FILL_SIMULATED"
    POSITION_CLOSED = "POSITION_CLOSED"
    RISK_VIOLATION = "RISK_VIOLATION"
    ERROR = "ERROR"


class ShadowLedgerEntryST02(BaseModel):
    entry_id: str
    campaign_id: str
    candidate_id: str
    timestamp_utc: str
    event_type: ShadowEventTypeST02
    sequence_num: int
    payload: Dict[str, Any]
    prev_hash: str
    entry_hash: str


class ShadowCampaignManifestST02(BaseModel):
    campaign_id: str = "CAMP-SHADOW-EXP-ST02-2026"
    version: str = "1.0.0"
    created_at_utc: str
    t0_activation_utc: Optional[str] = None
    first_eligible_session: Optional[str] = None
    current_state: ShadowExpSt02State = ShadowExpSt02State.AUTHORIZATION_REQUIRED
    activation_authorized: bool = False
    target_sessions: int = 90
    completed_sessions: int = 0
    portfolios: Dict[str, Dict[str, Any]]
    gates: Dict[str, Any]
    isolation_fingerprints: Dict[str, Any]
    manifest_sha256: str = ""
