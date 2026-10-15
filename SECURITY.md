# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in ShowUp, please report it
responsibly by emailing the maintainer directly. Do **not** open a public
GitHub issue for security-related bugs.

## Security Design

ShowUp is designed with the following security properties:

### Data Privacy
- **Zero outbound network calls** — the only network connection is to a local
  Ollama instance at `localhost:11434`.
- **No telemetry** — all library telemetry (HuggingFace, etc.) is disabled.
- **PII redaction** — structured logging automatically strips names, phone
  numbers, email addresses, and message content.
- **Data wipe** — users can delete all data (DB, caches, logs, model outputs)
  with a single action.

### Input Validation
- **CSV formula injection** — all exported CSV cells are sanitized to prevent
  formula injection attacks.
- **Path traversal** — uploaded filenames are sanitized; all writes go to a
  fixed data directory.
- **Upload size limits** — configurable maximum upload size (default 50 MB).
- **Parameterized queries** — all database queries use SQLAlchemy's
  parameterized query interface; no raw SQL string interpolation.

### Dependencies
- **Pinned versions** — all dependencies are version-pinned in `pyproject.toml`.
- **Automated auditing** — `pip-audit` runs in CI to catch known vulnerabilities.

### Model Safety
- **Feature allowlist** — only approved features are used for scoring; no age,
  gender, name, phone, or neighbourhood data.
- **LLM guardrails** — generated messages are checked for length, content, and
  language before being shown to the user.
- **No auto-send** — messages are never sent automatically; the owner always
  reviews and sends manually.
