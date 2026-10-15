# Changelog

All notable changes to ShowUp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-15

### Added
- **Core Architecture & Storage**: SQLite database schema with SQLAlchemy 2 ORM, Alembic migrations, OS-level file permissions (0600 / Owner ACL), and transaction-safe repository layer.
- **Safe CSV Ingestion**: Robust CSV reader with chardet encoding detection, csv.Sniffer delimiter parsing, formula injection sanitization, fuzzy column mapper with saved profiles, and duplicate detection.
- **Ethical Feature Engineering**: Strict 14-behavioral-feature allowlist preventing demographic/PII leakage (banning age, gender, address, phone, name), temporal order enforcement, and human-readable feature audit panel.
- **3-Tier Adaptive Scoring**:
  - Tier 1: Heuristic baseline rules engine for small datasets.
  - Tier 2: Calibrated Logistic Regression with L2 regularization and probability calibration.
  - Tier 3: In-context tabular foundation model (TabPFN v2) with zero-telemetry enforcement and time-ordered expanding-window backtesting.
- **Deterministic Business Insights**:
  - Exact historical no-show cost accounting with sample size disclosures and low-data suppression thresholds.
  - Stratified what-if simulator for upfront deposits and confirmation requests with empirical effect sizes and confounding disclosures.
- **Privacy-Preserving Messaging**:
  - Local LLM client for Google Gemma (`gemma3:4b`) via Ollama (`http://localhost:11434`).
  - Automated output guardrails checking length limits, hallucinated dates/fees, and prohibited phrases.
  - Curated fallback templates in English, Hindi, and Marathi.
  - Manual review interface with one-click `wa.me` WhatsApp links.
- **Desktop UI**: Complete multi-page Streamlit application with custom typography, responsive design, progress indicators, and empty state handlers.
- **Data Privacy & Security**:
  - Irreversible full data destruction (`wipe_all`) covering database, logs, and cache.
  - Enforcement of zero outbound network connections with automated socket blocking test.
- **Synthetic Data Generator & CLI**: Seeded synthetic dataset generator replicating realistic lead time, deposit, and channel dynamics, with `--messy` header testing support.
- **Comprehensive Documentation**: Architectural specification, model card, licensing & attribution disclosures, screen-by-screen user guide, launcher scripts (`run.bat`, `run.sh`, `download_models.py`), and Docker container.
