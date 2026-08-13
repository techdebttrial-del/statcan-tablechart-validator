"""
LLM-backed Translator implementation.

Connects to a LiteLLM gateway (http://192.168.2.170:4000) using the
'r720-35b-moe' model alias (Qwen 3.5 35B MoE on M40 GPU) for EN↔FR
machine translation of reviewer notes.

Implements the Translator protocol from core/translation_manager.py with:
  - Retry logic with exponential backoff (3 attempts)
  - Per-request timeout (configurable, default 30s)
  - Graceful fallback to PassthroughTranslator on persistent failure
  - Structured logging for observability
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

from core.translation_manager import PassthroughTranslator, Translator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults – overridable via environment variables
# ---------------------------------------------------------------------------
_DEFAULT_BASE_URL = "http://192.168.2.170:4000"
_DEFAULT_MODEL = "r720-35b-moe"
_DEFAULT_TIMEOUT = 30        # seconds per request
_DEFAULT_MAX_RETRIES = 3     # total attempts (including first)
_DEFAULT_RETRY_DELAY = 2.0   # base delay in seconds (doubles each retry)

# Language code → human name for prompt construction
_LANG_NAMES = {"en": "English", "fr": "French"}


class LLMTranslator:
    """
    Translator that calls a LiteLLM-hosted LLM for EN↔FR translation.

    On any unrecoverable error after exhausting retries, the ``translate``
    method returns the source text wrapped with an ``[LLM translation
    failed]`` marker so callers always get a non-empty string.

    Implements the ``Translator`` protocol from core/translation_manager.py.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        fallback: Optional[Translator] = None,
    ):
        self._base_url = (base_url or os.environ.get("LITELLM_BASE_URL", _DEFAULT_BASE_URL)).rstrip("/")
        raw_model = model or os.environ.get("LITELLM_MODEL", _DEFAULT_MODEL)
        # LiteLLM requires a provider prefix; the proxy uses openai-compatible API
        self._model = raw_model if "/" in raw_model else f"openai/{raw_model}"
        self._timeout = timeout or int(os.environ.get("LITELLM_TIMEOUT", _DEFAULT_TIMEOUT))
        self._max_retries = max_retries or int(os.environ.get("LITELLM_MAX_RETRIES", _DEFAULT_MAX_RETRIES))
        self._retry_delay = retry_delay or float(os.environ.get("LITELLM_RETRY_DELAY", _DEFAULT_RETRY_DELAY))
        self._fallback = fallback or PassthroughTranslator()
        # Self-hosted LiteLLM proxy may not need a real key, but the client requires one
        self._api_key = os.environ.get("LITELLM_API_KEY", "sk-no-key-needed")

        # Lazy import so the rest of the app can load even without litellm installed
        try:
            import litellm as _litellm  # noqa: F401
            self._litellm = _litellm
            self._available = True
            logger.info(
                "LLMTranslator initialised: model=%s base_url=%s timeout=%ds retries=%d",
                self._model, self._base_url, self._timeout, self._max_retries,
            )
        except ImportError:
            self._litellm = None
            self._available = False
            logger.warning("litellm package not installed – falling back to %s", self._fallback.engine_name)

    # -- Translator protocol ---------------------------------------------------

    @property
    def engine_name(self) -> str:
        return f"litellm:{self._model}@{self._base_url}"

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        """
        Translate *text* from *source_language* to *target_language*.

        Retries up to ``self._max_retries`` times with exponential backoff.
        If all attempts fail (network, timeout, parse error, etc.), returns
        the fallback translator's output so the caller always receives a
        usable string.
        """
        if not self._available:
            logger.debug("litellm unavailable – delegating to fallback")
            return self._fallback.translate(text, source_language, target_language)

        if not text or not text.strip():
            return text

        if source_language == target_language:
            return text

        src_name = _LANG_NAMES.get(source_language, source_language)
        tgt_name = _LANG_NAMES.get(target_language, target_language)

        system_prompt = (
            f"You are a professional translator specialised in Canadian government "
            f"statistical terminology. Translate the following text from {src_name} "
            f"to {tgt_name}. Output ONLY the translated text with no explanations, "
            f"no quotation marks, and no additional commentary."
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                t0 = time.monotonic()
                response = self._litellm.completion(  # type: ignore[union-attr]
                    model=self._model,
                    base_url=self._base_url,
                    api_key=self._api_key,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    timeout=self._timeout,
                    temperature=0.2,
                    max_tokens=max(len(text) * 3, 512),  # generous headroom
                    # Qwen3.6 can spend a short request's entire token budget
                    # in reasoning_content and return empty content.  Notes
                    # require a direct translation, not a chain of thought.
                    chat_template_kwargs={"enable_thinking": False},
                )
                elapsed = time.monotonic() - t0
                result = response.choices[0].message.content.strip()  # type: ignore[union-attr]
                if result:
                    logger.info(
                        "Translation succeeded (attempt %d/%d, %.1fs): %s → %s, %d chars",
                        attempt, self._max_retries, elapsed,
                        source_language, target_language, len(result),
                    )
                    return result
                else:
                    raise ValueError("LLM returned empty response")

            except Exception as exc:
                last_error = exc
                delay = self._retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Translation attempt %d/%d failed (%s: %s) – retrying in %.1fs",
                    attempt, self._max_retries, type(exc).__name__, exc, delay,
                )
                if attempt < self._max_retries:
                    time.sleep(delay)

        # All retries exhausted – fall back gracefully
        logger.error(
            "All %d translation attempts failed for %s→%s. Last error: %s – using fallback",
            self._max_retries, source_language, target_language, last_error,
        )
        return self._fallback.translate(text, source_language, target_language)

    # -- Helpers ---------------------------------------------------------------

    def health_check(self) -> bool:
        """
        Quick connectivity probe. Returns True if the LiteLLM endpoint
        responds to a trivial translation request within the timeout.
        """
        if not self._available:
            return False
        try:
            response = self._litellm.completion(  # type: ignore[union-attr]
                model=self._model,
                base_url=self._base_url,
                api_key=self._api_key,
                messages=[{"role": "user", "content": "Say OK"}],
                timeout=10,
                max_tokens=5,
            )
            return bool(response.choices[0].message.content)  # type: ignore[union-attr]
        except Exception as exc:
            logger.debug("LLMTranslator health check failed: %s", exc)
            return False

    def __repr__(self) -> str:
        return (
            f"LLMTranslator(model={self._model!r}, base_url={self._base_url!r}, "
            f"timeout={self._timeout}, max_retries={self._max_retries}, "
            f"available={self._available})"
        )
