# Third-Party Notices

ShowUp includes or depends on the following third-party software:

## TabPFN

- **Project**: [TabPFN](https://github.com/PriorLabs/TabPFN)
- **Authors**: Prior Labs / AutoML Freiburg
- **License**: Apache License 2.0 (for the open-source code); model weights
  may have separate terms — see [docs/licensing.md](docs/licensing.md).
- **Usage**: Advanced tabular classification for no-show risk scoring.

> **Important**: The TabPFN model weights and their license terms must be
> independently verified before any commercial deployment of ShowUp. See
> `docs/licensing.md` for details.

## Gemma

- **Project**: [Gemma](https://ai.google.dev/gemma) by Google DeepMind
- **License**: Gemma Terms of Use
- **Usage**: Message drafting via local Ollama inference.

## Ollama

- **Project**: [Ollama](https://ollama.com)
- **License**: MIT License
- **Usage**: Local LLM inference server.

## Streamlit

- **Project**: [Streamlit](https://streamlit.io)
- **License**: Apache License 2.0
- **Usage**: Web-based UI framework.

---

For a full list of Python dependencies and their licenses, run:

```bash
pip-licenses --from=mixed --format=table
```
