# ShowUp — Architecture

## 1. Overview

ShowUp is a **local-first desktop web application** that helps solo service businesses
(physio clinics, tutors, salons, driving instructors) reduce appointment no-shows.

Everything runs on the owner's machine. No client data ever leaves the device.
The only network call is to a **local** Ollama instance at `localhost:11434` for
message drafting.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Owner's Machine                          │
│                                                                 │
│  ┌──────────┐   ┌──────────────────────────────────────────┐    │
│  │ Ollama   │◄──┤            ShowUp Application            │    │
│  │ (Gemma)  │   │                                          │    │
│  │ :11434   │   │  ┌────────┐  ┌──────────┐  ┌─────────┐  │    │
│  └──────────┘   │  │  UI    │──┤ Services │──┤ Storage  │  │    │
│                 │  │Streamlit│  │ (Python) │  │ (SQLite) │  │    │
│                 │  └────────┘  └──────────┘  └─────────┘  │    │
│                 └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## 2. Design Principles

| # | Principle | Consequence |
|---|-----------|-------------|
| 1 | **Privacy by default** | Zero outbound calls; PII never logged; wipe-all supported |
| 2 | **Honest numbers** | All metrics from deterministic code; LLM never computes stats |
| 3 | **Layered architecture** | UI → Services → Domain; no business logic in Streamlit |
| 4 | **Ethical features** | Allowlist-only feature gate; no age/gender/name/neighbourhood |
| 5 | **Graceful degradation** | Rules → LogReg → TabPFN tiers; template fallback for messages |
| 6 | **Reproducibility** | All randomness seeded; deterministic model selection |

## 3. Layer Diagram

```
┌─────────────────────────────────────────┐
│               UI Layer                  │  Streamlit pages
│  (read-only from cache, calls services) │  No business logic
├─────────────────────────────────────────┤
│           Service Layer                 │
│  ┌─────────┬──────────┬──────────────┐  │
│  │ Ingest  │ Scoring  │  Messaging   │  │
│  │ Service │ Service  │  Service     │  │
│  ├─────────┼──────────┼──────────────┤  │
│  │Features │ Insights │  Jobs        │  │
│  │ Builder │ Engine   │  (bg worker) │  │
│  └─────────┴──────────┴──────────────┘  │
├─────────────────────────────────────────┤
│           Domain Layer                  │  Pure dataclasses, enums
│  Booking, Client, RiskBand,            │  No I/O, no DB imports
│  Intervention, FeatureAudit            │
├─────────────────────────────────────────┤
│          Storage Layer                  │  SQLAlchemy 2 models
│  SQLite + Alembic migrations           │  Repositories (CRUD)
│  wipe_all() for privacy                │
└─────────────────────────────────────────┘
```

## 4. Data Flow

### 4.1 Import Pipeline

```
CSV file
  │
  ▼
Encoding/Delimiter Sniffing (chardet, csv.Sniffer)
  │
  ▼
Column Mapper (fuzzy header matching → saved mapping per source)
  │
  ▼
Row-level Validation (Pydantic v2 models)
  │  ├── errors → Validation Report (shown in UI)
  │  └── duplicates → Dedupe (client_id + appointment_datetime)
  │
  ▼
Dry-Run Preview (UI shows sample + stats)
  │
  ▼ (owner confirms)
Commit to SQLite via Repository
  │
  ▼
Trigger Background Scoring Job
```

### 4.2 Scoring Pipeline (runs in background subprocess)

```
Load labeled bookings from DB
  │
  ▼
Count labels → decide tier
  │
  ├── < 100 labeled OR < 10 no-shows → Tier 1 (Rules)
  │     │
  │     ▼
  │   Apply rule engine → risk bands → cache to DB
  │
  └── Enough data → Tier 2 (Model Selection)
        │
        ▼
      Build features (allowlist-only, no leakage)
        │
        ▼
      Expanding-window time-ordered backtest
        │
        ├── Rules engine
        ├── Logistic Regression (sklearn)
        └── TabPFN v2 (local weights, lazy-loaded)
        │
        ▼
      Compare: PR-AUC, ROC-AUC, Brier + bootstrap CIs
        │
        ▼
      Select best model (TabPFN only if significantly better)
        │
        ▼
      Score upcoming bookings → risk bands → cache to DB
        │
        ▼
      Store explanation text + backtest metrics in DB
```

### 4.3 Message Drafting (on-demand, never background)

```
Owner clicks "Draft Message" on a booking
  │
  ▼
Build prompt:
  - language, tone (mapped from risk band)
  - pre-computed facts (time, service, client name)
  - word limit (<40), constraints (no guilt, no invented numbers)
  │
  ▼
Call Ollama (localhost:11434) → Gemma
  - timeout: 30s, retries: 2
  │
  ▼
Guardrails check:
  - length ≤ 40 words?
  - contains only supplied digits?
  - correct language? (heuristic)
  - no blocked phrases?
  │
  ├── PASS → show draft to owner
  └── FAIL → regenerate (max 2 attempts)
        │
        └── still FAIL → fallback to curated template
              (English / Hindi / Marathi)
  │
  ▼
Owner edits → copies or opens wa.me link
(Nothing logged about message content)
```

## 5. Key Technology Choices

| Component | Technology | Version | Why |
|-----------|-----------|---------|-----|
| Language | Python | ≥ 3.11 | Type hints, performance, ecosystem |
| UI | Streamlit | pinned | Rapid desktop-quality UI, no frontend build |
| DB | SQLite | built-in | Local-first, zero config, single file |
| ORM | SQLAlchemy 2 | pinned | Async-capable, type-safe, migration support |
| Migrations | Alembic | pinned | Reliable schema evolution |
| Validation | Pydantic v2 | pinned | Fast, type-safe data validation |
| Config | pydantic-settings | pinned | Env-driven config with defaults |
| ML baseline | scikit-learn | pinned | Logistic regression, metrics, calibration |
| ML advanced | TabPFN v2 | pinned | Zero-shot tabular classification, local weights |
| LLM | Gemma via Ollama | pinned | Local inference, multilingual, open-weight |
| Logging | structlog | pinned | Structured JSON logs, PII filtering |
| Linting | ruff | pinned | Fast, comprehensive Python linter + formatter |
| Types | mypy | pinned | Strict static type checking |
| Tests | pytest | pinned | Industry standard, rich plugin ecosystem |

## 6. Database Schema (conceptual)

```
clients
  id: UUID (PK)
  external_id: TEXT (from CSV, unique per source)
  language: TEXT (nullable)
  phone_hash: TEXT (nullable, for wa.me link only)
  created_at: DATETIME

bookings
  id: UUID (PK)
  client_id: UUID (FK → clients)
  appointment_at: DATETIME
  booking_created_at: DATETIME (nullable)
  service_type: TEXT (nullable)
  price: DECIMAL (nullable)
  channel: TEXT (nullable)
  deposit_paid: BOOLEAN (nullable)
  confirmed: BOOLEAN (nullable)
  outcome: ENUM('attended', 'no_show')
  source_file: TEXT
  imported_at: DATETIME

scoring_results
  id: UUID (PK)
  booking_id: UUID (FK → bookings)
  risk_band: ENUM('low', 'medium', 'high')
  probability: FLOAT
  model_used: TEXT
  scored_at: DATETIME
  explanation: TEXT

scoring_runs
  id: UUID (PK)
  started_at: DATETIME
  completed_at: DATETIME (nullable)
  status: ENUM('running', 'completed', 'failed')
  tier: INTEGER
  model_selected: TEXT
  metrics_json: TEXT
  explanation: TEXT
  progress_pct: INTEGER
  error_message: TEXT (nullable)

column_mappings
  id: UUID (PK)
  source_name: TEXT (unique)
  mapping_json: TEXT
  created_at: DATETIME

app_settings
  key: TEXT (PK)
  value: TEXT
```

## 7. Feature Engineering

### 7.1 Allowed Features (allowlist-enforced)

| Feature | Source | Computation |
|---------|--------|-------------|
| `lead_time_hours` | booking_created_at, appointment_at | Diff in hours |
| `lead_time_bucket` | lead_time_hours | Categorical bucket |
| `day_of_week` | appointment_at | 0-6 |
| `hour_of_day` | appointment_at | 0-23 |
| `prior_visits` | historical bookings | Count before this booking |
| `prior_no_shows` | historical bookings | Count before this booking |
| `prior_no_show_rate` | historical bookings | Rate before this booking |
| `is_new_client` | prior_visits | True if prior_visits == 0 |
| `days_since_last_visit` | historical bookings | Days since last booking |
| `booking_channel` | channel column | Categorical |
| `service_type` | service_type column | Categorical |
| `price` | price column | Numeric |
| `deposit_paid` | deposit_paid column | Boolean |
| `confirmation_received` | confirmed column | Boolean |

### 7.2 Leakage Prevention

Client-history features (`prior_visits`, `prior_no_shows`, `prior_no_show_rate`,
`days_since_last_visit`) are computed using **only bookings with `appointment_at`
strictly before the current booking's `appointment_at`**. This is enforced in the
feature builder and verified by a dedicated test.

### 7.3 Excluded Features (with reasons)

| Feature | Reason |
|---------|--------|
| `age` | Ethical: potential age discrimination |
| `gender` | Ethical: potential gender discrimination |
| `name` | Ethical + privacy: potential ethnic bias, PII |
| `phone` | Privacy: PII, no predictive value |
| `neighbourhood` | Ethical: potential socioeconomic/racial bias |

These are enforced by an allowlist — no blocklist. The allowlist is defined once in
`features/` and tested to ensure no other columns pass through.

## 8. Scoring Architecture

### 8.1 Tier Selection

```python
def select_tier(bookings: list[Booking]) -> int:
    labeled = [b for b in bookings if b.outcome is not None]
    no_shows = [b for b in labeled if b.outcome == Outcome.NO_SHOW]
    if len(labeled) < 100 or len(no_shows) < 10:
        return 1
    return 2
```

### 8.2 Backtest Protocol (Tier 2)

- **Expanding window**: First 60% as minimum train set, expand by 10% per fold
- **Time-ordered**: Train on past, test on future (no shuffling)
- **Metrics**: PR-AUC, ROC-AUC, Brier score
- **Confidence**: Bootstrap 95% CIs on test metrics
- **Selection**: TabPFN chosen only if its lower CI bound for PR-AUC exceeds
  the baseline's upper CI bound (i.e., non-overlapping CIs). Otherwise, simpler
  model wins with an honest explanation.

### 8.3 Background Worker

Scoring runs in a **subprocess** (not a thread) launched by the import flow.
Progress is written to `scoring_runs` table as `progress_pct`. The UI polls
`scoring_runs` to show a progress bar. If the worker crashes, the status is
set to `'failed'` with an error message.

## 9. Security Considerations

| Threat | Mitigation |
|--------|-----------|
| SQL injection | Parameterized queries only (SQLAlchemy) |
| CSV formula injection | Prefix `=`, `+`, `-`, `@`, `\t`, `\r` with `'` on export |
| Path traversal | Sanitize upload filenames; write to fixed data dir |
| File size | Configurable upload size limit (default 50 MB) |
| PII in logs | structlog processor strips names, phones, emails |
| Dependency supply chain | Pinned versions, `pip-audit` in CI |
| Data at rest | DB file permissions set to owner-only (0600 on Unix) |

## 10. Configuration

All configuration via environment variables with sane defaults (via `pydantic-settings`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SHOWUP_DATA_DIR` | `~/.showup/data` | Where DB and model cache live |
| `SHOWUP_LOG_LEVEL` | `INFO` | Logging level |
| `SHOWUP_OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `SHOWUP_OLLAMA_MODEL` | `gemma3:4b` | Model tag for drafting |
| `SHOWUP_OLLAMA_TIMEOUT` | `30` | Timeout in seconds |
| `SHOWUP_MAX_UPLOAD_MB` | `50` | Max CSV upload size |
| `SHOWUP_SEED` | `42` | Global random seed |
| `SHOWUP_MIN_SAMPLE_WHATIF` | `20` | Min N for what-if cards |

## 11. Directory Structure

```
showup/
├── pyproject.toml
├── README.md
├── LICENSE
├── NOTICE.md
├── CHANGELOG.md
├── SECURITY.md
├── PRIVACY.md
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── src/showup/
│   ├── __init__.py
│   ├── config.py
│   ├── logging_setup.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── enums.py
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── reader.py
│   │   ├── mapper.py
│   │   ├── validator.py
│   │   └── dedupe.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── database.py
│   │   ├── repositories.py
│   │   └── alembic/
│   ├── features/
│   │   ├── __init__.py
│   │   ├── builder.py
│   │   ├── allowlist.py
│   │   └── audit.py
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── rules.py
│   │   ├── baseline.py
│   │   ├── tabpfn_scorer.py
│   │   ├── backtest.py
│   │   └── selector.py
│   ├── insights/
│   │   ├── __init__.py
│   │   ├── cost_report.py
│   │   └── whatif.py
│   ├── messaging/
│   │   ├── __init__.py
│   │   ├── prompt.py
│   │   ├── ollama_client.py
│   │   ├── guardrails.py
│   │   ├── templates.py
│   │   └── whatsapp.py
│   ├── jobs/
│   │   ├── __init__.py
│   │   └── worker.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── pages/
│   │   └── components/
│   └── synthetic/
│       ├── __init__.py
│       └── generator.py
├── tests/
├── scripts/
└── docs/
```

## 12. Performance Targets

| Operation | Target | How |
|-----------|--------|-----|
| Import 5,000 rows | < 10s | Bulk insert, minimal per-row overhead |
| Scoring 5,000 rows | Background job | Subprocess, progress in DB |
| UI page render | < 300ms | Read from cache only |
| Message draft | < 30s | Ollama timeout, template fallback |

## 13. Testing Strategy

| Layer | Type | Tools | Coverage |
|-------|------|-------|----------|
| Domain | Unit | pytest | 100% |
| Ingest | Unit + Property | pytest, hypothesis | ≥ 90% |
| Features | Unit + Leakage | pytest | ≥ 90% |
| Scoring | Unit + Integration | pytest | ≥ 85% |
| Storage | Integration | pytest, in-memory SQLite | ≥ 85% |
| Messaging | Unit (mocked Ollama) | pytest | ≥ 85% |
| E2E | Full pipeline | pytest, fake Ollama | Pass/Fail |
| Network | Offline assertion | pytest, socket mock | Pass/Fail |
| Allowlist | Unit | pytest | Pass/Fail |

## 14. Future Work (out of scope)

- Calendar integrations (Google Calendar, Outlook)
- Cloud sync / multi-device
- Authentication server
- Auto-sending messages
- Audio input / voice notes
- SMS gateway integration
- Multi-user / team features
- Real-time dashboard updates via WebSocket
