# ShowUp

> **Local-first no-show reduction desktop web app for solo service professionals.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/)
[![Coverage: 90%](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://pytest.org)
[![Privacy: Local-First](https://img.shields.io/badge/privacy-100%25%20offline-success.svg)](docs/model-card.md)

ShowUp helps independent service businesses — **physiotherapists, remedial massage therapists, private tutors, hair stylists, and driving instructors** — understand, forecast, and reduce appointment no-shows without sending their clients' private information to any cloud service.

---

## What ShowUp Does

```
┌─────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│   Import CSV    │ ───► │  Deterministic Costs    │ ───► │   3-Tier ML Scoring     │
│ (Any scheduler) │      │ (Owner's records only)  │      │ (Rules / LogReg / TabPFN│
└─────────────────┘      └─────────────────────────┘      └────────────┬────────────┘
                                                                       │
┌─────────────────┐      ┌─────────────────────────┐                   │
│ Manual Dispatch │ ◄─── │ WhatsApp Message Draft  │ ◄─────────────────┘
│  (wa.me link)   │      │ (Local LLM via Ollama)  │
└─────────────────┘      └─────────────────────────┘
```

1. **Deterministic Cost Impact**: Calculates exact lost revenue and no-show rates strictly from your historical data. Never quotes hypothetical "industry averages."
2. **Upcoming Risk Scoring**: Predicts unexcused absence probabilities for upcoming appointments using an adaptive 3-tier hierarchy (Heuristic Rules, Calibrated Logistic Regression, and TabPFN v2).
3. **Data-Grounded What-If Simulator**: Stratifies historical attendance by upfront deposit and confirmation status to measure empirical show-up differences with sample size disclosures.
4. **Local LLM Message Drafting**: Synthesizes culturally nuanced, multilingual WhatsApp reminder drafts (English, Hindi, Marathi) using open-weight local LLMs (e.g., `llama3.2:3b`, `gemma3:4b`) running on localhost via Ollama.
5. **Human-in-the-Loop Dispatch**: Pre-populates `wa.me` links for one-click manual sending. **Nothing is ever auto-sent.**

---

## Core Guarantees

- **100% Offline Inference**: Every model runs on localhost. Zero outbound network sockets. Verified by automated socket-interception test suites (`tests/e2e/test_full_pipeline.py`).
- **Ethical AI (14-Feature Allowlist)**: Demographic variables (age, gender, ethnicity) and socioeconomic proxies (postal codes, street addresses, names, phones) are permanently banned from feature matrices.
- **Irreversible Full Data Wipe**: With a single click on the Privacy page, you can permanently delete all local SQLite records, cached models, and logs.
- **Zero Hallucinated Metrics**: All financial figures and probabilities are computed deterministically in Python.

---

## Quick Start

### Prerequisites
- Python 3.11 or newer
- *(Optional, for AI message drafting)*: [Ollama](https://ollama.com) installed and running

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/vinit-tech-source/ShowUp.git
cd ShowUp

# Install editable package with all dependencies
pip install -e ".[dev]"
```

### 2. Prepare Local AI Models

```bash
# Pull an open-weight model in Ollama (e.g., llama3.2:3b or gemma3:4b)
ollama pull llama3.2:3b

# Verify local models
python scripts/download_models.py
```
*(If Ollama is not installed or running, ShowUp automatically falls back to built-in multilingual message templates.)*

### 3. Generate Realistic Demo Data (Optional)

```bash
# Generate synthetic appointments (200 bookings across 30 clients)
python scripts/make_demo_data.py --output data/demo_bookings.csv --clients 30 --bookings 200
```

### 4. Launch the Application

#### Windows
Double-click `scripts\run.bat` or run:
```powershell
scripts\run.bat
```

#### Linux / macOS
```bash
chmod +x scripts/run.sh
./scripts/run.sh
```

#### Manual / Direct Launch
```bash
streamlit run src/showup/ui/app.py
```
Open your browser at `http://localhost:8501`.

---

## Docker Deployment (Optional)

```bash
# Build the container
docker build -t showup:latest .

# Run container with persistent local data volume
docker run -d -p 8501:8501 -v showup-data:/data showup:latest
```

---

## Documentation

- **[docs/user-guide.md](docs/user-guide.md)**: Screen-by-screen walkthrough, import mappings, and workflows.
- **[docs/architecture.md](docs/architecture.md)**: Detailed system design, schemas, and scoring lifecycle.
- **[docs/model-card.md](docs/model-card.md)**: Model cards, ethical allowlist rationale, metrics, and limitations.
- **[docs/licensing.md](docs/licensing.md)**: TabPFN v2 attribution, Gemma terms, and third-party license review.
- **[SECURITY.md](SECURITY.md)**: Security policy, formula injection defenses, and vulnerability reporting.
- **[PRIVACY.md](PRIVACY.md)**: Data processing boundaries and privacy guarantees.

---

## Development & Verification

ShowUp enforces strict code quality standards:

```bash
# Run full test suite with coverage report (gate >= 85%)
pytest --cov=showup --cov-report=term-missing tests/

# Run End-to-End pipeline & zero-network tests
pytest tests/e2e/

# Run Ruff linter & format checks
ruff check .
ruff format --check .

# Run Mypy strict type checking
mypy --strict src/
```

---

## License & Attributions

ShowUp is open-source software licensed under the **[MIT License](LICENSE)**.

- **TabPFN-2**: Uses TabPFN-2 by [Prior Labs](https://github.com/prior-labs/TabPFN) (Apache 2.0 permissive open-weight license with attribution).
- **Ollama / LLMs**: Local inference models subject to their respective open-weight licenses (e.g. Llama 3.2, Gemma). See [docs/licensing.md](docs/licensing.md) for details.
