"""
Service wiring — v2.0 with dual-flavour architecture.

Wires ModeManager, FixSuggester, and the existing Inspector/Translator/Store
into singleton constructors cached via st.cache_resource.
"""
from __future__ import annotations

import os
import streamlit as st

from core.rule_pack_loader import RulePackLoader
from core.excel_inspector import ExcelInspector
from core.translation_manager import TranslationManager, PassthroughTranslator
from core.llm_translator import LLMTranslator
from core.repository_client import RepositoryClient
from core.project_store import ProjectStore
from core.report_generator import ReportGenerator
from core.mode_manager import ModeManager
from core.fix_suggester import FixSuggester

import logging

logger = logging.getLogger(__name__)

DATA_ROOT = os.environ.get("TVC_DATA_ROOT", os.path.join(os.path.expanduser("~"), ".tvc_data"))


@st.cache_resource
def get_rule_loader() -> RulePackLoader:
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
    return RulePackLoader(config_dir)


@st.cache_resource
def get_inspector() -> ExcelInspector:
    return ExcelInspector(loader=get_rule_loader())


@st.cache_resource
def get_mode_manager() -> ModeManager:
    return ModeManager()


@st.cache_resource
def get_fix_suggester() -> FixSuggester:
    return FixSuggester(mode_manager=get_mode_manager())


@st.cache_resource
def get_translation_manager() -> TranslationManager:
    mm = get_mode_manager()
    if mm.use_llm:
        litellm_url = os.environ.get("LITELLM_BASE_URL", mm.litellm_url)
        if litellm_url:
            model = os.environ.get("LITELLM_MODEL", mm.cascade2_model)
            translator = LLMTranslator(base_url=litellm_url, model=model)
            logger.info("TranslationManager using LLMTranslator (base_url=%s, model=%s)", litellm_url, model)
            return TranslationManager(translator=translator)

    translator = PassthroughTranslator()
    logger.info("TranslationManager using PassthroughTranslator (no LLM)")
    return TranslationManager(translator=translator)


@st.cache_resource
def get_repository() -> RepositoryClient:
    return RepositoryClient(root_path=DATA_ROOT)


@st.cache_resource
def get_project_store() -> ProjectStore:
    return ProjectStore(
        repo=get_repository(),
        inspector=get_inspector(),
        translator=get_translation_manager(),
    )


@st.cache_resource
def get_report_generator() -> ReportGenerator:
    return ReportGenerator(translator=get_translation_manager())