"""
RulePackLoader

Loads Table 101 / Chart 101 rule packs from YAML, mirroring the
SupportPackLoader pattern in the broader StatCan ESR Accelerator
(core/support_pack_loader.py), which yields SupportPackRule /
SupportPackCheck objects injected into LLM prompts. Here, rules are
deterministic (no LLM) and are injected into the ExcelInspector instead.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

import yaml


@dataclass
class Rule:
    id: str
    pack: str
    severity: str
    title_en: str
    title_fr: str
    description_en: str
    description_fr: str
    check_expression: str


class RulePackLoader:
    """Singleton-style loader for rule packs + standard symbols."""

    _instance = None

    #: Location of the YAML data inside this distribution package.
    #: Works identically from a source checkout and an installed wheel/sdist.
    _CONFIG_PACKAGE = "config"

    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or self._default_config_dir()
        self._rules: Dict[str, List[Rule]] = {}
        self._symbols: Dict[str, Any] = {}
        self.reload()

    @staticmethod
    def _default_config_dir() -> str:
        """Return a filesystem path for the config package's data.

        Prefers the resolved on-disk location of the ``config`` package so the
        loader keeps reading plain YAML files whether running from a checkout
        (config/ at repo root) or an installed wheel (config/ inside the
        site-packages distribution).
        """
        try:
            import importlib.resources as ilr

            ref = ilr.files(RulePackLoader._CONFIG_PACKAGE)
            path = str(ref) if ref is not None else ""
            if path and os.path.isdir(path):
                return path
        except Exception:
            pass
        # Fallback: repo-layout config dir relative to this module.
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
        )

    def _pack_dir(self) -> str:
        return os.path.join(self.config_dir, "rule_packs")

    @classmethod
    def get(cls, config_dir: str = None) -> "RulePackLoader":
        if cls._instance is None:
            cls._instance = cls(config_dir)
        return cls._instance

    def reload(self) -> None:
        self._rules = {}
        pack_dir = self._pack_dir()
        if not os.path.isdir(pack_dir):
            return
        for fname in sorted(os.listdir(pack_dir)):
            if not fname.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(pack_dir, fname)
            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            pack_name = data["pack"]
            rules = []
            for r in data.get("rules", []):
                rules.append(
                    Rule(
                        id=r["id"],
                        pack=pack_name,
                        severity=r["severity"],
                        title_en=r["title_en"],
                        title_fr=r["title_fr"],
                        description_en=r["description_en"],
                        description_fr=r["description_fr"],
                        check_expression=r["check"],
                    )
                )
            self._rules[pack_name] = rules

        symbols_path = os.path.join(self.config_dir, "symbols", "standard_symbols.yaml")
        if os.path.exists(symbols_path):
            with open(symbols_path, "r", encoding="utf-8") as fh:
                self._symbols = yaml.safe_load(fh)

    def rules_for(self, pack: str) -> List[Rule]:
        return self._rules.get(pack, [])

    def all_rules(self) -> List[Rule]:
        out = []
        for pack_rules in self._rules.values():
            out.extend(pack_rules)
        return out

    def rule_by_id(self, rule_id: str) -> Rule:
        for r in self.all_rules():
            if r.id == rule_id:
                return r
        raise KeyError(f"Unknown rule id: {rule_id}")

    def standard_symbols(self) -> Dict[str, Any]:
        return self._symbols
