"""
TranslationManager

Lightweight EN/FR machine-translation wrapper for free-text reviewer notes,
aligned with the broader Accelerator's translation_manager.py /
comparative_editor.py bilingual conventions. This module deliberately keeps
translation "draft-quality" and clearly labeled, per project decision: notes
show the original in a labeled section, and a clearly identified machine
translation in the alternate language. No LLM call is required for the MVP;
a pluggable `Translator` protocol allows wiring an LLM client later
(e.g. core/llm_client.py from the broader Accelerator) without touching
callers.
"""
from __future__ import annotations

import hashlib
from typing import Optional, Protocol

from core.models import Translation, BilingualNote, now_iso


class Translator(Protocol):
    def translate(self, text: str, source_language: str, target_language: str) -> str: ...
    @property
    def engine_name(self) -> str: ...


class PassthroughTranslator:
    """
    Fallback translator used when no LLM gateway is configured.
    Clearly marks output as untranslated so it is never mistaken for a
    real translation. Replace with an LLM-backed Translator (e.g. wrapping
    core/llm_client.py's LiteLLM gateway from the broader Accelerator) for
    production use.
    """

    engine_name = "passthrough-no-llm-configured"

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        marker = "[FR translation unavailable]" if target_language == "fr" else "[EN translation unavailable]"
        return f"{marker} {text}"


class TranslationManager:
    def __init__(self, translator: Optional[Translator] = None):
        self.translator = translator or PassthroughTranslator()

    def _other_language(self, lang: str) -> str:
        return "fr" if lang == "en" else "en"

    def make_bilingual_note(self, text: str, source_language: str, author: str) -> BilingualNote:
        target_language = self._other_language(source_language)
        translated_text = self.translator.translate(text, source_language, target_language)
        source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        translation = Translation(
            text=translated_text,
            source_language=source_language,
            target_language=target_language,
            is_machine_translation=True,
            engine=self.translator.engine_name,
            translated_at=now_iso(),
            source_text_hash=source_hash,
            human_verified=False,
        )
        return BilingualNote(
            original_text=text,
            original_language=source_language,
            author=author,
            translation=translation,
        )

    def attach_human_verified_translation(self, note: BilingualNote, verified_text: str) -> BilingualNote:
        note.human_verified_translation = verified_text
        if note.translation:
            note.translation.human_verified = False  # machine translation itself is never "upgraded"
        return note

    def render_pair(self, note: BilingualNote, display_language: str) -> dict:
        """
        Returns a dict with 'primary' (in display_language) and 'secondary'
        keys, each labeled per the "clearly identified as machine
        translation from the source language" requirement.
        """
        if note.original_language == display_language:
            primary = {
                "label_en": "Original reviewer note",
                "label_fr": "Note originale du réviseur",
                "text": note.original_text,
                "is_machine_translation": False,
            }
        else:
            if note.human_verified_translation:
                primary = {
                    "label_en": "Human-verified translation",
                    "label_fr": "Traduction vérifiée par un humain",
                    "text": note.human_verified_translation,
                    "is_machine_translation": False,
                }
            else:
                src_label = "English" if note.original_language == "en" else "French"
                primary = {
                    "label_en": f"Machine translation from {src_label} — original available",
                    "label_fr": f"Traduction automatique depuis l'{('anglais' if note.original_language=='en' else 'français')} — texte original disponible",
                    "text": note.translation.text if note.translation else "",
                    "is_machine_translation": True,
                }
        return primary
