# ShowUp

**Local-first no-show reduction for solo service businesses.**

ShowUp helps physio clinics, tutors, salons, and driving instructors understand
and reduce appointment no-shows — entirely on their own machine. No data leaves
your computer.

## What It Does

1. **Import** your past bookings from a CSV (attended / no-show).
2. **See** what no-shows cost you, computed from *your own data* only.
3. **Score** upcoming bookings by no-show risk (Low / Medium / High).
4. **Explore** what-if scenarios for deposits and confirmations.
5. **Draft** a short reminder message (via local AI), review it, and send
   manually through WhatsApp.

## Key Principles

- **Privacy first** — all data stays on your machine. Zero outbound network calls.
- **Honest numbers** — every statistic comes from your data with sample sizes shown.
- **Ethical AI** — no age, gender, name, or neighbourhood used in scoring.
- **Open-weight models** — Gemma (via Ollama) for messages, TabPFN v2 for scoring.

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running (for message drafting)

### Install

```bash
# Clone and install
git clone <repo-url> showup
cd showup
pip install -e ".[dev]"

# Pull the Gemma model
ollama pull gemma3:4b

# Generate demo data (no real client data needed)
python scripts/make_demo_data.py

# Launch
streamlit run src/showup/ui/app.py
```

### Windows

```powershell
scripts\run.bat
```

### Linux / macOS

```bash
./scripts/run.sh
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint & format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy --strict src/

# Pre-commit hooks
pre-commit install
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full design.

## License

MIT — see [LICENSE](LICENSE).

> **Note**: ShowUp uses [TabPFN](https://github.com/PriorLabs/TabPFN) for
> advanced scoring. TabPFN has its own license terms. See
> [docs/licensing.md](docs/licensing.md) and [NOTICE.md](NOTICE.md).
