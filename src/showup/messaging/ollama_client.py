"""HTTP client for local Ollama instance (localhost:11434)."""

from __future__ import annotations

import httpx

from showup.config import ShowUpSettings, get_settings
from showup.logging_setup import get_logger

logger = get_logger(__name__)


class OllamaError(Exception):
    """Base error for Ollama client."""


class OllamaNotRunningError(OllamaError):
    """Raised when Ollama daemon is not reachable on localhost."""


class ModelNotPulledError(OllamaError):
    """Raised when the specified model is not available locally in Ollama."""


class OllamaTimeoutError(OllamaError):
    """Raised when generation times out."""


class OllamaClient:
    """HTTP client communicating strictly with the local Ollama service."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        settings: ShowUpSettings = get_settings()
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.timeout = timeout or settings.ollama_timeout

    def check_health(self) -> bool:
        """Check whether local Ollama is active and listening."""
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Fetch names of all models locally pulled in Ollama."""
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    raise OllamaNotRunningError(f"Ollama returned status {resp.status_code}")
                data = resp.json()
                models: list[str] = [m.get("name", "") for m in data.get("models", [])]
                return [m for m in models if m]
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise OllamaNotRunningError("Cannot connect to local Ollama on localhost:11434.") from e

    def is_model_available(self, model_name: str) -> bool:
        """Check if a specific model tag is present."""
        try:
            models = self.list_models()
            clean_target = model_name.split(":", maxsplit=1)[0]
            return any(m == model_name or m.startswith(clean_target) for m in models)
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        max_retries: int = 2,
    ) -> str:
        """Generate text via Ollama.

        Raises:
            OllamaNotRunningError: If Ollama daemon is offline.
            ModelNotPulledError: If target model is not installed.
            OllamaTimeoutError: If inference times out.
        """
        settings = get_settings()
        target_model = model or settings.ollama_model

        payload: dict[str, object] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=float(self.timeout)) as client:
                    resp = client.post(f"{self.base_url}/api/generate", json=payload)

                    if resp.status_code == 404:
                        raise ModelNotPulledError(
                            f"Model '{target_model}' not found in local Ollama. "
                            f"Run 'ollama pull {target_model}' to download it."
                        )

                    if resp.status_code != 200:
                        raise OllamaError(
                            f"Ollama generation failed with status {resp.status_code}."
                        )

                    data = resp.json()
                    response_text: str = data.get("response", "").strip()
                    logger.info("ollama_generation_success", model=target_model)
                    return response_text

            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                raise OllamaNotRunningError(
                    "Ollama is not running on localhost:11434. Please start Ollama."
                ) from e
            except (httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_exc = e
                logger.warning(
                    "ollama_generation_timeout",
                    attempt=attempt,
                    model=target_model,
                )
            except ModelNotPulledError:
                raise
            except Exception as e:
                last_exc = e
                logger.warning("ollama_attempt_failed", attempt=attempt, error=str(e))

        raise OllamaTimeoutError(
            f"Ollama generation timed out after {max_retries + 1} attempts."
        ) from last_exc
