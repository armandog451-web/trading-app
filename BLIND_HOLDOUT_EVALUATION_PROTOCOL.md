# BLIND HOLDOUT EVALUATION PROTOCOL

**Protocol Status:** PRE-REGISTERED & LOCKED (NOT EXECUTED)  
**System Core:** `ai_trading_agent v2.2.1-pro`  
**Candidate Subject:** `D21_RangeCompress_5d`  
**Family:** `daily_range_compression_breakout`  
**Evaluation Nature:** Single One-Shot Blind Out-of-Sample Holdout Verification  

---

## 1. PURPOSE & SECURITY WARNING

> [!CAUTION]
> This protocol specifies the **EXACT and UNALTERABLE** rules for the blind evaluation of `D21_RangeCompress_5d` on the Final Holdout dataset (`2025-10-05` to `2026-10-05`).  
> **THIS PROTOCOL IS PRE-REGISTERED PRIOR TO UNSEALING THE HOLDOUT.**  
> It must NOT be executed without explicit written human authorization.  
> Once executed, the Final Holdout dataset will be permanently consumed and cannot be reused for this strategy family.

---

## 2. FROZEN SUBJECT SPECIFICATION

The backtester must verify that the strategy code and configuration match this exact cryptographic hash before opening the holdout:

```yaml
Strategy ID: D21_RangeCompress_5d
Family: daily_range_compression_breakout
Frozen Fingerprint: f885ec2db2422308
Timeframe: 1D
Holding Horizon: 5 daily bars
Donchian Length: 20
RVOL Threshold: 1.25
SMA Filter: SMA50
Exit Geometry: time_stop
RR Ratio: 2.0
ATR Mult: 1.5
Trailing Mult: 2.0
Concurrency Policy: ONE_POSITION_PER_SYMBOL
Max Concurrent Positions: 2
Position Sizing: Fixed fractional risk 1.0% equity ($1,000)
Universe: [SPY, QQQ, IWM, DIA]
Execution: Open of day t after signal on close of day t-1
```

If `current_fingerprint != f885ec2db2422308`, execution must abort immediately with a `SecurityViolationError`.

---

## 3. HOLDOUT DATASET DEFINITION

- **Timeframe:** 1D (Daily bars).
- **Holdout Start Timestamp:** `2025-10-05T00:00:00`
- **Holdout End Timestamp:** `2026-10-05T00:00:00` (or latest available dataset bar).
- **Duration:** Exactly 1 calendar year ($365$ days, $\approx 252$ trading bars per symbol).
- **Symbols:** `SPY`, `QQQ`, `IWM`, `DIA`.
- **Integrity Requirement:** No historical indicators inside the holdout window may look forward past the current evaluation bar $t$. Feature warm-up must utilize strictly pre-holdout trailing bars.

---

## 4. EXECUTION FRICTION & COST ASSUMPTIONS

The blind evaluation must use realistic production friction:
- **Brokerage Commission:** Interactive Brokers Tiered rate of $\$0.005$ per share, with minimum $\$1.00$ per order.
- **Baseline Slippage:** Exactly **5.0 bps** ($0.0005 \times \text{fill price}$).
- **Stress Slippage Grid:** $0.0\text{ bps}$, $5.0\text{ bps}$, $10.0\text{ bps}$.

---

## 5. PRE-REGISTERED PASS / FAIL RULES

The holdout test outcome will be judged strictly by the following criteria. **No post-hoc adjustments to thresholds are permitted**:

| Metric | Minimum Required Threshold | Failure Condition |
| :--- | :--- | :--- |
| **Net Profit Factor ($PF_{5\text{bps}}$)** | **$\ge 1.05$** | $PF < 1.05$ |
| **Total Net PnL** | **$> \$0.00$** | Net PnL $\le \$0.00$ |
| **Trade Expectancy** | **$\ge +\$15.00$ / trade** | Expectancy $< +\$15.00$ |
| **Minimum Closed Trades** | **$\ge 12$ trades** across universe | Trades $< 12$ (insufficient holdout activity) |
| **Maximum Realized Drawdown** | **$\le 10.0\%$** of account equity | Drawdown $> 10.0\%$ |
| **Allowed Performance Degradation** | $PF_{\text{holdout}} \ge 0.70 \times PF_{\text{pre-holdout}}$ | Degradation $> 30\%$ |
| **Loss Concentration** | No single symbol loss $> 60\%$ of total loss | Catastrophic single-asset failure |

---

## 6. CANDIDATE OUTCOME CLASSIFICATION

Upon completion of the single blind evaluation, the strategy will be automatically assigned one of three mutually exclusive outcomes:

```
IF ALL PASS CRITERIA MET AND PF >= 1.15:
    OUTCOME = CANDIDATE_CONFIRMED
    ACTION = Promote to PAPER_TRADING_ELIGIBLE

ELIF ALL PASS CRITERIA MET AND 1.05 <= PF < 1.15:
    OUTCOME = MARGINAL_PASS
    ACTION = Maintain in MONITORING / Discretionary Review

ELSE (ANY PASS CRITERIA FAILED):
    OUTCOME = HOLDOUT_FAILED
    ACTION = Strategy permanently ARCHIVED. No parameter mutation allowed.
```

---

## 7. EXECUTION PROTOCOL INVARIANTS

1. **One-Shot Execution:** The holdout evaluation script may be executed exactly **ONE (1)** time.
2. **Zero Iterations:** If the strategy fails or falls short, tuning parameters, adding indicators, or altering exit logic to "fix" the holdout performance is **STRICTLY FORBIDDEN**.
3. **Audit Trail Logging:** Every executed trade, timestamp, fill price, slippage deduction, and equity point must be appended to an immutable JSON audit log.
