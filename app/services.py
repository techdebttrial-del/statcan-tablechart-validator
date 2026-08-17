"""
Service wiring — deterministic-only architecture.

Wires the Inspector/Translator/Store into singleton constructors cached via
st.cache_resource. No LLM gateways, no mode switching: identification and
changes are fully deterministic.
"""
from __future__ import annotations

import os
import streamlit as st

from core.rule_pack_loader import RulePackLoader
from core.excel_inspector import ExcelInspector
from core.translation_manager import TranslationManager, PassthroughTranslator
from core.repository_client import RepositoryClient
from core.project_store import ProjectStore
from core.report_generator import ReportGenerator

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
def get_translation_manager() -> TranslationManager:
    # Reviewer notes are kept bilingual (EN/FR) deterministically: the
    # original text is preserved and the alternate language is clearly
    # labelled as untranslated, with a human-verified slot available.
    translator = PassthroughTranslator()
    logger.info("TranslationManager using PassthroughTranslator (deterministic, no LLM)")
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