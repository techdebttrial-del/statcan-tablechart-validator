"""
ModeManager — Dual-flavour architecture for the StatCan Tables/Charts Validator.

Controls and monitors the operating mode:
- OFFLINE: No LLM calls, zero network dependencies, PassthroughTranslator
- LLM_ASSISTED: Cascade 2 via LiteLLM for translations + fix suggestions
- CLOUD_ESCALATION: Auto-escalates to cloud models when local LLM insufficient

Auto-degrades from LLM_ASSISTED → OFFLINE if the LLM gateway is unreachable.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# Default LLM gateway configuration
_DEFAULT_LITELLM_URL = "http://192.168.2.170:4000"
_DEFAULT_CASCADE2_MODEL = "r720-cascade2"
_DEFAULT_CLOUD_MODEL = "cloud-*-free"
_HEALTH_TIMEOUT = 5  # seconds


class OperatingMode(str, Enum):
    OFFLINE = "offline"
    LLM_ASSISTED = "llm_assisted"
    CLOUD_ESCALATION = "cloud_escalation"
    DEGRADED = "degraded"  # LLM gateway unreachable, fell back to offline


@dataclass
class HealthStatus:
    """Current health of the LLM gateway and mode state."""
    mode: OperatingMode
    gateway_ok: bool = False
    cascade2_loaded: bool = False
    litellm_ok: bool = False
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    cloud_escalations_used: int = 0
    max_cloud_escalations: int = 3
    llm_model: str = ""
    auto_downgraded: bool = False

    def emoji(self) -> str:
        if self.mode == OperatingMode.OFFLINE:
            return "🟢"
        elif self.mode == OperatingMode.LLM_ASSISTED:
            return "🟢"
        elif self.mode == OperatingMode.DEGRADED:
            return "🟡"
        elif self.mode == OperatingMode.CLOUD_ESCALATION:
            return "🔵"
        return "⚪"

    def label(self, lang: str = "en") -> str:
        labels = {
            OperatingMode.OFFLINE: ("Offline", "Hors ligne"),
            OperatingMode.LLM_ASSISTED: ("LLM-Assisted", "Assisté par LLM"),
            OperatingMode.CLOUD_ESCALATION: ("Cloud Escalation", "Escalade infonuagique"),
            OperatingMode.DEGRADED: ("Degraded (Offline)", "Dégradé (hors ligne)"),
        }
        idx = 0 if lang == "en" else 1
        return labels.get(self.mode, ("Unknown", "Inconnu"))[idx]

    def summary(self, lang: str = "en") -> str:
        mode_label = self.label(lang)
        if self.mode == OperatingMode.OFFLINE:
            return f"{self.emoji()} {mode_label} — No LLM dependencies"
        elif self.mode == OperatingMode.LLM_ASSISTED:
            model = self.llm_model or "Cascade 2"
            return f"{self.emoji()} {mode_label} — {model} ({self.latency_ms:.0f}ms)" if self.latency_ms else f"{self.emoji()} {mode_label} — {model}"
        elif self.mode == OperatingMode.DEGRADED:
            return f"{self.emoji()} {mode_label} — {self.error or 'Gateway unreachable'}"
        elif self.mode == OperatingMode.CLOUD_ESCALATION:
            return f"{self.emoji()} {mode_label} — {self.cloud_escalations_used}/{self.max_cloud_escalations} used"
        return f"{self.emoji()} {mode_label}"


class ModeManager:
    """
    Manages the operating mode and LLM gateway health for the validator.

    Usage:
        mm = ModeManager()
        health = mm.check_health()  # probes gateway
        mode = mm.get_mode()        # returns current OperatingMode
    """

    def __init__(
        self,
        litellm_url: Optional[str] = None,
        cascade2_model: Optional[str] = None,
        cloud_model: Optional[str] = None,
        max_cloud_escalations: Optional[int] = None,
        use_llm: Optional[bool] = None,
    ):
        self._litellm_url = (litellm_url or os.environ.get("LITELLM_BASE_URL", _DEFAULT_LITELLM_URL)).rstrip("/")
        self._cascade2_model = cascade2_model or os.environ.get("LITELLM_MODEL", _DEFAULT_CASCADE2_MODEL)
        self._cloud_model = cloud_model or os.environ.get("CLOUD_ESCALATION_MODEL", _DEFAULT_CLOUD_MODEL)

        raw_use_llm = use_llm
        if raw_use_llm is None:
            env_val = os.environ.get("USE_LLM", "true")
            raw_use_llm = env_val.lower() in ("true", "1", "yes")
        self._use_llm = bool(raw_use_llm)

        self._max_cloud_escalations = max_cloud_escalations or int(
            os.environ.get("MAX_CLOUD_ESCALATIONS", "3")
        )
        self._cloud_escalations_used = 0
        self._health: Optional[HealthStatus] = None
        self._last_health_check: float = 0
        self._health_check_interval: float = 30.0  # re-check every 30s
        self._mode: OperatingMode = OperatingMode.OFFLINE

        # Try to import litellm
        try:
            import litellm  # noqa: F401
            self._litellm_available = True
        except ImportError:
            self._litellm_available = False
            logger.warning("litellm not installed — offline mode only")

        logger.info(
            "ModeManager: litellm_url=%s cascade2=%s cloud=%s use_llm=%s",
            self._litellm_url, self._cascade2_model, self._cloud_model, self._use_llm,
        )

    # ---- Public API -------------------------------------------------

    def get_mode(self) -> OperatingMode:
        """Return the current operating mode, performing health check if needed."""
        if time.monotonic() - self._last_health_check > self._health_check_interval:
            self.check_health()
        return self._mode

    def check_health(self) -> HealthStatus:
        """Probe LLM gateway and return comprehensive health status."""
        self._last_health_check = time.monotonic()
        t0 = time.monotonic()

        if not self._use_llm or not self._litellm_available:
            self._mode = OperatingMode.OFFLINE
            self._health = HealthStatus(
                mode=OperatingMode.OFFLINE,
                gateway_ok=False,
                error="LLM assistance disabled" if not self._use_llm else "litellm not installed",
            )
            return self._health

        # Probe LiteLLM health — try /v1/models first (more reliable)
        import urllib.request
        import json as json_module

        litellm_ok = False
        cascade2_loaded = False
        error = None

        # Try /v1/models first (returns 200 with model list)
        try:
            req = urllib.request.Request(f"{self._litellm_url}/v1/models", method="GET")
            with urllib.request.urlopen(req, timeout=_HEALTH_TIMEOUT) as resp:
                if resp.status == 200:
                    body = resp.read().decode()
                    models_data = json_module.loads(body)
                    model_ids = []
                    if "data" in models_data:
                        model_ids = [m.get("id", "") for m in models_data["data"]]
                    elif "models" in models_data:
                        model_ids = [m.get("name", "") for m in models_data["models"]]
                    litellm_ok = len(model_ids) > 0
                    cascade2_loaded = self._cascade2_model in model_ids
                    if not litellm_ok:
                        error = "No models returned from LiteLLM"
                    elif not cascade2_loaded:
                        logger.warning("Cascade 2 model '%s' not found in LiteLLM models: %s",
                                       self._cascade2_model, model_ids[:5])
                        error = f"Model '{self._cascade2_model}' not loaded"
        except Exception as e:
            error = f"LiteLLM /v1/models failed: {e}"
            logger.warning(error)

        elapsed_ms = (time.monotonic() - t0) * 1000

        # Determine mode
        if litellm_ok and cascade2_loaded:
            self._mode = OperatingMode.LLM_ASSISTED
        elif litellm_ok:
            self._mode = OperatingMode.DEGRADED
        else:
            self._mode = OperatingMode.OFFLINE
            error = error or "LLM gateway unreachable"

        self._health = HealthStatus(
            mode=self._mode,
            gateway_ok=litellm_ok and cascade2_loaded,
            cascade2_loaded=cascade2_loaded,
            litellm_ok=litellm_ok,
            latency_ms=elapsed_ms,
            error=error,
            cloud_escalations_used=self._cloud_escalations_used,
            max_cloud_escalations=self._max_cloud_escalations,
            llm_model=self._cascade2_model,
        )

        return self._health

    @property
    def health(self) -> Optional[HealthStatus]:
        return self._health

    def escalate_to_cloud(self) -> bool:
        """
        Attempt to escalate to cloud model. Returns True if escalation is possible.
        """
        if self._cloud_escalations_used >= self._max_cloud_escalations:
            logger.warning("Cloud escalation budget exhausted (%d/%d)",
                           self._cloud_escalations_used, self._max_cloud_escalations)
            return False

        if not self._use_llm or not self._litellm_available:
            return False

        self._cloud_escalations_used += 1
        self._mode = OperatingMode.CLOUD_ESCALATION
        logger.info("Cloud escalation %d/%d — using %s",
                     self._cloud_escalations_used, self._max_cloud_escalations,
                     self._cloud_model)
        return True

    def reset_cloud_budget(self) -> None:
        """Reset cloud escalation counter (e.g., on new session)."""
        self._cloud_escalations_used = 0

    def set_use_llm(self, value: bool) -> None:
        """Toggle LLM usage without restart."""
        self._use_llm = bool(value)
        # Force re-check on next get_mode()
        self._last_health_check = 0
        logger.info("LLM assistance set to %s", self._use_llm)

    @property
    def use_llm(self) -> bool:
        return self._use_llm

    @property
    def cloud_escalations_used(self) -> int:
        return self._cloud_escalations_used

    @property
    def litellm_url(self) -> str:
        return self._litellm_url

    @property
    def cascade2_model(self) -> str:
        return self._cascade2_model

    @property
    def cloud_model(self) -> str:
        return self._cloud_model

    def __repr__(self) -> str:
        return (
            f"ModeManager(mode={self._mode.value}, use_llm={self._use_llm}, "
            f"litellm={self._litellm_url}, cascade2={self._cascade2_model}, "
            f"cloud_esc={self._cloud_escalations_used}/{self._max_cloud_escalations})"
        )