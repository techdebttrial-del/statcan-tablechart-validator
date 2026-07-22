import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.translation_manager import TranslationManager


def test_make_bilingual_note_marks_machine_translation():
    tm = TranslationManager()
    note = tm.make_bilingual_note("This is fine.", "en", "Reviewer A")
    assert note.original_language == "en"
    assert note.translation.target_language == "fr"
    assert note.translation.is_machine_translation is True


def test_render_pair_original_language():
    tm = TranslationManager()
    note = tm.make_bilingual_note("Ceci est correct.", "fr", "Reviewer A")
    pair_fr = tm.render_pair(note, "fr")
    assert pair_fr["is_machine_translation"] is False
    pair_en = tm.render_pair(note, "en")
    assert pair_en["is_machine_translation"] is True


def test_human_verified_translation_overrides_display():
    tm = TranslationManager()
    note = tm.make_bilingual_note("Original text.", "en", "Reviewer A")
    tm.attach_human_verified_translation(note, "Texte vérifié par un humain.")
    pair_fr = tm.render_pair(note, "fr")
    assert pair_fr["text"] == "Texte vérifié par un humain."
    assert pair_fr["is_machine_translation"] is False
