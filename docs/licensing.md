# ShowUp — Third-Party Licensing & Open-Weight Attribution

ShowUp is an open-source software project licensed under the [MIT License](../LICENSE). It incorporates and interfaces with open-weight foundation models and third-party libraries that possess distinct licensing frameworks.

---

## 1. ShowUp Core Pipeline

- **License**: MIT License
- **Copyright**: (c) 2026 ShowUp Contributors
- **Scope**: All original source code located under `src/showup/`, test suites, background workers, and documentation.

---

## 2. TabPFN v2 Foundation Model (Prior Labs)

ShowUp integrates TabPFN v2 as its Tier-3 tabular foundation model for zero-shot in-context probabilistic risk estimation.

- **Developer**: Prior Labs GmbH & Co. KG (Freiburg, Germany)
- **Source Repository**: [github.com/PriorLabs/TabPFN](https://github.com/PriorLabs/TabPFN)
- **Academic Citation**:
  ```bibtex
  @article{hollmann2025tabpfnv2,
    title={Accurate Predictions on Small Data with a Tabular Foundation Model},
    author={Hollmann, Noah and M{\"u}ller, Samuel and Purucker, Lennart and G{\"o}rres, Frank and Franke, J{\"o}rg and Grabocka, Josif and Hutter, Frank},
    journal={Nature},
    year={2025}
  }
  ```
- **License Terms**:
  - The open-source TabPFN software wrapper is distributed under Apache 2.0.
  - The default pre-trained TabPFN v2 weights downloaded via Hugging Face are released by Prior Labs under a **Non-Commercial Research & Educational License**.
  - **Commercial Use Notice**: If you intend to operate ShowUp as a commercial enterprise or hosted service utilizing TabPFN v2 weights, you must acquire a commercial license directly from [Prior Labs](https://priorlabs.ai) or operate ShowUp using its built-in **Tier-2 Calibrated Logistic Regression** engine (which is completely Apache 2.0 / MIT compliant).

---

## 3. Local Open-Weights LLMs via Ollama

ShowUp interfaces with local open-weight language models (e.g. `llama3.2:3b`, `gemma3:4b`) running locally through the Ollama runtime for multilingual WhatsApp reminder synthesis.

- **Distribution Runtime**: Ollama (MIT License)
- **Model Terms**: Respective model licenses (e.g., Llama 3.2 Community License, Gemma Terms of Use)
- **Commercial Permissibility**: Both Llama 3.2 and Gemma grant royalty-free licenses for commercial applications adhering to acceptable use policies.
- **Privacy & Safety**: All inference executes strictly on the local CPU/GPU via `http://localhost:11434`. No prompt text, client names, or booking details are ever transmitted to external cloud endpoints.

---

## 4. Key Python Dependencies

| Package | License | Purpose |
|---|---|---|
| `streamlit` | Apache 2.0 | Reactive desktop web UI |
| `scikit-learn` | BSD-3-Clause | Calibrated logistic regression & metrics |
| `sqlalchemy` | MIT | SQLite database ORM |
| `alembic` | MIT | Relational schema migrations |
| `pydantic` | MIT | Data parsing, validation, & settings |
| `pandas` / `numpy` | BSD-3-Clause | Tabular data manipulation & matrix math |
| `structlog` | Apache 2.0 / MIT | Structured JSON logging with PII scrubbing |
| `httpx` | BSD-3-Clause | Local asynchronous HTTP client for Ollama |
| `scipy` | BSD-3-Clause | Statistical distributions & confidence intervals |

---

## 5. Compliance Checklist for Solo Business Owners

1. **Local Desktop Use**: Running ShowUp locally on your clinic or business laptop for your own appointments falls under legitimate personal / internal operational use.
2. **Offline Integrity**: ShowUp permanently disables telemetry headers (`HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, `TRANSFORMERS_OFFLINE=1`).
3. **Wipe Capabilities**: You retain 100% control over stored data and can execute an irreversible full data wipe at any time via the Privacy page.
