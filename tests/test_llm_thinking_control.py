"""Regression tests for thinking-model request options."""
from types import SimpleNamespace

from core.fix_suggester import FixSuggester
from core.llm_translator import LLMTranslator
from core.models import Finding, Severity
from core.mode_manager import ModeManager


class RecordingLLM:
    def __init__(self):
        self.kwargs = None

    def completion(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='OK'))]
        )


def test_translation_disables_thinking_for_qwen_requests():
    client = LLMTranslator(base_url="http://llm", model="r720-cascade2", max_retries=1)
    recorder = RecordingLLM()
    client._litellm = recorder
    client._available = True

    assert client.translate("Hello", "en", "fr") == "OK"
    assert recorder.kwargs["chat_template_kwargs"] == {"enable_thinking": False}


def test_fix_suggestions_disable_thinking_for_qwen_requests():
    mode = ModeManager(use_llm=True, litellm_url="http://llm", cascade2_model="r720-cascade2")
    mode._mode = mode.get_mode()  # health is not needed for this isolated call
    suggester = FixSuggester(mode_manager=mode)
    recorder = RecordingLLM()
    suggester._litellm = recorder

    finding = Finding(
        finding_id="f1", rule_id="T101-TEST", pack="tables101",
        severity=Severity.ERROR, sheet_name="tbl01", location="A1",
        title_en="Test", title_fr="Test", description_en="Test",
        description_fr="Test",
    )
    suggester._call_llm_for_suggestions(finding, "prompt", "r720-cascade2", "http://llm")
    assert recorder.kwargs["chat_template_kwargs"] == {"enable_thinking": False}
