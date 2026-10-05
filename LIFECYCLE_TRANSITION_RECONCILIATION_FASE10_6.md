# FASE 10.6 — LIFECYCLE TRANSITION SEMANTICS RECONCILIATION

**System Core:** `ai_trading_agent v2.2.1-pro`  
**Audit Date:** 2026-10-05  
**Candidate Subject:** `D21_RangeCompress_5d` (Family: `daily_range_compression_breakout`)  
**Frozen Fingerprint:** `f885ec2db2422308`  
**Investigation Focus:** Exact Code Inspection of Lifecycle Transitions, Location of SQS Gate, and Disentangling `PAPER_ELIGIBLE` vs `APPROVED`.

---

## 1. EXACT STATE TRANSITION TRACE IN `LifecycleManager`

An inspection of `ai_trading_agent/strategy_lab/lifecycle/manager.py` reveals the exact programmatic rules governing every transition:

| Transition | Function | File & Lines | Required Previous State | Positive Transition Conditions | Hard Blocking Conditions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`RESEARCH -> BACKTEST`** | `promote_strategy` | `manager.py:33` | `RESEARCH` | State transition membership | None |
| **`BACKTEST -> VALIDATING`** | `promote_strategy` | `manager.py:34` | `BACKTEST` | State transition membership | None |
| **`VALIDATING -> CANDIDATE`** | `promote_strategy` | `manager.py:35, 120-123` | `VALIDATING` | `evaluate_candidate_gating(strat) == True` | `min_trades < 8`, `PF < 1.0`, `EES == NO_EDGE`, `PRS < 50` |
| **`CANDIDATE -> PAPER`** | `promote_strategy` | `manager.py:36, 126-128` | `CANDIDATE` | **`strat.robustness_score >= 60.0`** | **`strat.robustness_score < 60.0`** |
| **`PAPER -> APPROVED`** | `promote_strategy` | `manager.py:37, 131-136` | `PAPER` | **`strat.strategy_score >= 70.0`** AND Candidate Gating | **`strat.strategy_score < 70.0`** |

> [!IMPORTANT]
> **Key Architectural Finding:**  
> The condition `strategy_score >= 70.0` ($SQS \ge 70.0$) appears **ONLY** in line 132 for the transition **`PAPER -> APPROVED`**.  
> The transition **`CANDIDATE -> PAPER`** (lines 126–128) checks **ONLY** `robustness_score >= 60.0`. It **DOES NOT** inspect or require `strategy_score >= 70.0`.

---

## 2. DRY-RUN STATE EVALUATION FOR D21

A dry-run evaluation of `D21_RangeCompress_5d` was executed against `LifecycleManager` without mutating persistent state:

```python
# Parameters of Frozen Lead D21:
metrics = {
    "total_trades": 102,
    "is_trades": 60,
    "oos_trades": 42,
    "profit_factor": 1.17,
    "expectancy": 64.87,
    "sharpe_ratio": 0.47
}
robustness_score = 71.2
strategy_score = 69.17
```

### Dry-Run Step-by-Step Output:
1. **Candidate Gate Evaluation (`evaluate_candidate_gating`):**
   - Trades: $102 \ge 8$ (PASS)
   - In-Sample: $60 \ge 5$ (PASS)
   - Out-of-Sample: $42 \ge 3$ (PASS)
   - Profit Factor: $1.17 \ge 1.0$ (PASS)
   - Robustness: $71.2 \ge 50.0$ (PASS)
   - Economic Edge: `POSITIVE_EDGE` (PASS)
   - $\longrightarrow$ **`CANDIDATE_GATING_PASSED`** (`True`).
2. **Transition `VALIDATING -> CANDIDATE`:**
   - Pre-condition: Current status is `VALIDATING` and candidate gating passed.
   - $\longrightarrow$ **`ALLOWED`** (`True`).
3. **Transition `CANDIDATE -> PAPER`:**
   - Pre-condition: Current status is `CANDIDATE` and `robustness_score >= 60.0`.
   - D21 Robustness Score: $71.2 \ge 60.0$.
   - $\longrightarrow$ **`ALLOWED`** (`True`).
4. **Transition `PAPER -> APPROVED`:**
   - Pre-condition: Current status is `PAPER` and `strategy_score >= 70.0`.
   - D21 Strategy Score: $69.17 < 70.0$.
   - $\longrightarrow$ **`BLOCKED`** (`False: Strategy Score (69.2) es menor al mínimo requerido (70.0)`).

---

## 3. SQS EXACT CODE LOCATION AUDIT

**Where in the code is $SQS \ge 70.0$ applied?**

- **A. Candidate gate?** $\longrightarrow$ **`NO`**. `evaluate_candidate_gating` does not inspect `strategy_score`.
- **B. Paper gate?** $\longrightarrow$ **`NO`**. Lines 126–128 check only `robustness_score >= 60.0`.
- **C. Approved gate?** $\longrightarrow$ **`YES`**. Lines 131–134:
  ```python
  if target_status == StrategyStatus.APPROVED:
      if strat.strategy_score < 70.0:
          return False, f"APROBACIÓN DENEGADA: Strategy Score ({strat.strategy_score:.1f}) es menor al mínimo requerido (70.0).", strat
  ```
- **D. Multiple gates?** $\longrightarrow$ **`NO`**. Only for `APPROVED`.

---

## 4. PAPER ELIGIBILITY DEFINITION UNDER SEALED CODE

According to the actual Python source code in `LifecycleManager`:
1. To enter **`StrategyStatus.PAPER`**, a strategy must:
   - Reside in `StrategyStatus.CANDIDATE`.
   - Have `robustness_score >= 60.0`.
2. D21 satisfies:
   - `evaluate_candidate_gating` $\longrightarrow$ **PASS**.
   - `robustness_score` $= 71.2 \ge 60.0$ $\longrightarrow$ **PASS**.
3. Therefore, D21 is **QUANTITATIVELY ELIGIBLE FOR PAPER TRADING** (`CANDIDATE -> PAPER`).
4. SQS ($69.17$) blocks **ONLY** final algorithmic approval (`APPROVED`). It **DOES NOT** block observation in the Paper Sandbox (`PAPER`).

---

## 5. WHY D21 WAS REPORTED AS NOT ELIGIBLE IN FASE 10.5

The apparent contradiction arose from a semantic conflation between:
1. **`APPROVED` (Production Capital / Live Automation Readiness):** Which strictly requires $SQS \ge 70.0$.
2. **`PAPER` (Sandbox Observation / Broker Forward-Testing):** Which requires only `CANDIDATE` status and $PRS \ge 60.0$.
3. **Current Missing Step:** D21 was never formally transitioned from `VALIDATING` into `StrategyStatus.CANDIDATE` in the persistent registry database.
   - Because `promote_strategy` enforces single-step transitions (`VALIDATING -> CANDIDATE -> PAPER`), a strategy currently not in `CANDIDATE` cannot leap directly to `PAPER`.

---

## 6. HOLDOUT STATUS RECONCILIATION

- `BLIND_HOLDOUT_PASS` (1-year OOS: $PF = 1.22$, $MaxDD = 5.70\%$, 7/7 criteria met) reinforces empirical validity.
- The sealed `LifecycleManager` has no rule requiring holdout evaluation prior to `PAPER`, nor does it impose extra barriers after holdout pass.
- Holdout success confirms that D21 is a verified research lead ready for sandbox forward-testing.

---

## 7. FINAL DECISION & ELIGIBILITY MATRIX

| Stage / Transition | Code Requirement | D21 Observed Value | Code Evaluation | Status Classification |
| :--- | :--- | :---: | :---: | :--- |
| **Candidate Gating** | $Trades \ge 8, PF \ge 1.0, EES > 0, PRS \ge 50$ | $102\text{ trades}, 1.17\text{ PF}, EES\ 54.2, PRS\ 71.2$ | **PASS** | Quantitatively Eligible |
| **Transition $\to$ `CANDIDATE`** | Origin: `VALIDATING` + Candidate Gating | Validating + Candidate Gating Passed | **PASS** | State Transition Permitted |
| **Transition $\to$ `PAPER`** | Origin: `CANDIDATE` + $PRS \ge 60.0$ | Candidate + $PRS = 71.2 \ge 60.0$ | **PASS** | **PAPER ELIGIBLE** |
| **Transition $\to$ `APPROVED`** | Origin: `PAPER` + $SQS \ge 70.0$ | Paper + $SQS = 69.17 < 70.0$ | **FAIL** | **BLOCKED BY SQS < 70** |
| **Transition $\to$ `LIVE`** | Does not exist in `StrategyStatus` | N/A | **N/A** | Architectural Boundary |

---

## 8. FORMAL INSTITUTIONAL VERDICT

In accordance with Section 8 of the prompt mandate:

$$\mathbf{FORMAL\ VERDICT:}\quad \mathbf{PAPER\_ELIGIBLE\_BUT\_NOT\_APPROVED}$$

1. **`PAPER_ELIGIBLE_BUT_NOT_APPROVED`:**
   - D21 fulfills all quantitative and robust gating requirements to transition from `VALIDATING` $\to$ `CANDIDATE` $\to$ `PAPER`.
   - D21 is **NOT** eligible for `APPROVED` status because $SQS = 69.17 < 70.00$.
2. **Sequential Prerequisite:**
   - D21 must first be formally transitioned into `StrategyStatus.CANDIDATE` before executing the transition to `StrategyStatus.PAPER`.
3. **Execution Authorization:**
   - TradingMode remains **`ANALYSIS_ONLY`**. Actual broker connection to Paper Trading requires human authorization.
