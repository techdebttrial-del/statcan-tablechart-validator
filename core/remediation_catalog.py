"""Finite, deterministic remediation choices for StatCan findings.

This catalogue is deliberately conservative: it records reviewer intent and
possible replacement input, but never invents analytical values or edits a
workbook without explicit approval.
"""
from __future__ import annotations

from typing import Dict, List

_COMMON = {
    "T101-NO-EMPTY-CELLS": [
        {"id": "enter_value", "label_en": "Enter the correct value", "label_fr": "Saisir la valeur correcte", "input": "text"},
        {"id": "select_symbol", "label_en": "Use an approved StatCan symbol", "label_fr": "Utiliser un symbole approuvé de StatCan", "input": "select"},
        {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"},
    ],
    "C101-NO-EMPTY-CELLS": [
        {"id": "enter_value", "label_en": "Enter the correct value", "label_fr": "Saisir la valeur correcte", "input": "text"},
        {"id": "select_symbol", "label_en": "Use an approved StatCan symbol", "label_fr": "Utiliser un symbole approuvé de StatCan", "input": "select"},
        {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"},
    ],
}

_CATALOG: Dict[str, List[dict]] = {
    **_COMMON,
    "T101-NO-FORMULAS": [{"id": "replace_with_value", "label_en": "Replace formula with reviewed static value", "label_fr": "Remplacer la formule par une valeur statique vérifiée", "input": "text"}, {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"}],
    "T101-NO-COLOR-FILL": [{"id": "remove_fill", "label_en": "Remove cell background fill", "label_fr": "Supprimer le remplissage de fond", "input": "none"}, {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"}],
    "T101-INDENT-FEATURE": [{"id": "use_indent", "label_en": "Use Excel indent instead of leading spaces", "label_fr": "Utiliser le retrait Excel plutôt que des espaces", "input": "none"}, {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"}],
    "T101-GRIDLINES-ON": [{"id": "turn_on", "label_en": "Turn on worksheet gridlines", "label_fr": "Activer le quadrillage de la feuille", "input": "none"}, {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"}],
    "T101-SOURCE-PRESENT": [{"id": "enter_source", "label_en": "Enter the source citation", "label_fr": "Saisir la citation de source", "input": "text"}, {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"}],
    "C101-NO-EXTRA-CALCULATIONS": [{"id": "remove_calculation", "label_en": "Remove the helper calculation", "label_fr": "Supprimer le calcul auxiliaire", "input": "none"}, {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"}],
    "C101-SIZE-WIDTH": [{"id": "resize_chart", "label_en": "Resize chart to 22.5–30 cm", "label_fr": "Redimensionner le graphique à 22,5–30 cm", "input": "none"}, {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"}],
    "C101-SIZE-HEIGHT-MIN": [{"id": "resize_chart", "label_en": "Resize chart to at least 11 cm high", "label_fr": "Redimensionner le graphique à au moins 11 cm de hauteur", "input": "none"}, {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"}],
    "C101-MAX-SIX-SERIES": [{"id": "remove_series", "label_en": "Remove or combine unnecessary series", "label_fr": "Supprimer ou combiner les séries inutiles", "input": "text"}, {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"}],
    "C101-SOURCE-PRESENT": [{"id": "enter_source", "label_en": "Enter the source citation below the chart", "label_fr": "Saisir la citation de source sous le graphique", "input": "text"}, {"id": "leave_open", "label_en": "Leave open for data owner", "label_fr": "Laisser ouvert pour le propriétaire des données", "input": "none"}],
}


def remediation_options(rule_id: str) -> List[dict]:
    return [dict(option) for option in _CATALOG.get(rule_id, [{"id": "leave_open", "label_en": "Leave open for reviewer decision", "label_fr": "Laisser ouvert pour décision du réviseur", "input": "none"}])]


def registry() -> Dict[str, List[dict]]:
    return {rule_id: remediation_options(rule_id) for rule_id in _CATALOG}

remediation_options.registry = registry  # compatibility with simple catalog tests

APPROVED_SYMBOLS = ["..", "...", "0s", "p", "r", "x", "E", "F"]
SOURCE_OPTIONS = ["Statistics Canada", "Source: Statistics Canada", "Custom source (type below)"]


def approved_symbol_options() -> List[str]:
    return list(APPROVED_SYMBOLS)
