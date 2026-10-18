# ShowUp — Model Card & Algorithmic Disclosure

## Model Details

- **Model Hierarchy**: 3-Tier Adaptive Architecture
  - **Tier 1 (Heuristic Baseline)**: Rule-based risk assigner for new deployments ($N < 30$ historical appointments).
  - **Tier 2 (Parametric Baseline)**: Calibrated Logistic Regression with L2 regularization and isotonic/sigmoid calibration ($30 \le N < 100$).
  - **Tier 3 (Tabular Foundation Model)**: TabPFN v2 (Prior Labs), zero-telemetry in-context transformer ($N \ge 100$, activated only when non-overlapping bootstrap confidence intervals demonstrate statistically significant PR-AUC superiority).
- **Secondary Local Model**: Open-weight local LLMs (e.g., `llama3.2:3b`, `gemma3:4b` via local Ollama instance) for client-language WhatsApp message drafting.
- **License**: MIT (ShowUp core pipeline); Prior Labs Non-Commercial / Research License for default TabPFN v2 weights (see `docs/licensing.md`); respective open-weights model licenses for Ollama LLMs.
- **Inference Location**: 100% on-device (localhost CPU/GPU). Zero outbound network traffic.

---

## Intended Use & Domain Scope

- **Primary Intended Use**: Assisting solo and micro service providers (e.g., physiotherapists, remedial massage therapists, private tutors, hair/nail salons, independent driving instructors) in predicting and mitigating appointment no-shows.
- **Actionable Output**:
  1. Discrete risk classifications (`LOW`, `MEDIUM`, `HIGH`) with calibrated posterior probabilities ($P(\text{no-show}) \in [0.0, 1.0]$).
  2. Grounded historical cost reports and deposit/confirmation what-if analyses.
  3. Pre-drafted WhatsApp reminder messages for manual review and delivery.
- **Non-Autonomous Principle**: ShowUp never automates client communications. The human owner always reviews, edits, and manually clicks the `wa.me` dispatch link.

---

## Data & Feature Governance

### Zero Cross-Tenant Data Pooling
ShowUp models are trained exclusively on the active practitioner's own historical appointment records. No pooled datasets, no external demographic lookups, and no industry-average benchmarks are ever used to generate client risk scores.

### Protected Feature Exclusion (Fairness Allowlist)
To prevent algorithmic discrimination, proxy discrimination, and violation of data protection laws (GDPR, UK GDPR, HIPAA, Indian DPDP Act), ShowUp strictly enforces a **14-feature behavioral allowlist** at the architecture boundary:

```python
ALLOWED_FEATURES = frozenset(
    {
        "lead_time_hours",
        "appointment_day_of_week",
        "appointment_hour",
        "is_weekend",
        "service_type",
        "price",
        "booking_channel",
        "deposit_paid",
        "deposit_amount",
        "confirmed",
        "prior_bookings_count",
        "prior_no_shows",
        "no_show_rate",
        "is_new_client",
    }
)
```

### Prohibited Variables (Permanent Exclusion)
The following fields are strictly quarantined during CSV ingestion and permanently forbidden from feature matrices:
- **Demographic data**: Age, gender, ethnicity, marital status, nationality.
- **Socioeconomic proxies**: Residential street address, postal/ZIP code, neighborhood indices.
- **Personal identifiers**: Client name, phone number, email address, national identity numbers.

*Rationale*: Prior studies demonstrate that zip codes and demographic markers introduce uncalibrated societal bias into booking models while providing negligible predictive gain over behavioral attributes (e.g., lead time, upfront deposits, prior attendance consistency).

---

## Evaluation & Metrics Methodology

### Time-Ordered Expanding-Window Backtesting
Randomized $k$-fold cross-validation is strictly forbidden in ShowUp because shuffling appointment records across time creates temporal leakage (training on future bookings to predict past appointments).

ShowUp implements a rolling time-ordered backtest:
1. Appointments are sorted chronologically by `appointment_datetime`.
2. An initial historical window (minimum 30 bookings) serves as the first training fold.
3. Subsequent chunks are predicted strictly out-of-sample before being appended to the training set.

### Primary Metrics
- **PR-AUC (Precision-Recall Area Under Curve)**: Primary optimization metric due to severe class imbalance (typical no-show rates range between 5% and 25%).
- **ROC-AUC (Receiver Operating Characteristic AUC)**: Secondary discrimination metric.
- **Brier Score**: Measures probability calibration reliability ($0.0 = \text{perfect calibration}$).
- **Bootstrap 95% Confidence Intervals**: Derived via 1,000 resamples to evaluate statistical significance before tier promotion.

---

## Limitations & Failure Modes

1. **Cold Start Regimes**: If a clinic has fewer than 10 total past bookings, machine learning models will not execute. The system falls back to Tier 1 transparent heuristic rules.
2. **Sudden Schedule Restructuring**: If a practitioner drastically changes pricing, relocates their physical premises, or alters operating hours, historical behavioral correlations may temporarily degrade until new bookings accumulate.
3. **Misinterpretation of Risk**: A `HIGH` risk label represents an elevated statistical probability, not an absolute guarantee of absence. Messages generated for high-risk clients must remain warm, respectful, and service-oriented.
4. **Offline Hardware Variations**: TabPFN v2 foundation inference utilizes memory-intensive attention layers. On low-memory systems (<8 GB RAM), TabPFN may take several seconds or fail to load; ShowUp automatically falls back to sub-millisecond logistic regression.
