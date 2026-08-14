"""Deterministic workbook iteration lineage helpers."""
from __future__ import annotations

import re
from pathlib import Path


def latest_iteration(workbook_dir: str | Path, original_filename: str) -> Path | None:
    """Return the highest-numbered generated iteration for an original file."""
    directory = Path(workbook_dir)
    pattern = re.compile(r"^iteration_(\d+)_.*_" + re.escape(original_filename) + r"$")
    candidates = []
    for path in directory.glob(f"iteration_*_{original_filename}"):
        match = pattern.match(path.name)
        if match:
            candidates.append((int(match.group(1)), path.name, path))
    return max(candidates, key=lambda item: (item[0], item[1]))[2] if candidates else None


def current_workbook(workbook_dir: str | Path, original_filename: str, revision_filename: str) -> Path:
    """Choose the latest immutable iteration, or the initial revision."""
    return latest_iteration(workbook_dir, original_filename) or Path(workbook_dir) / revision_filename


def next_iteration(workbook_dir: str | Path, original_filename: str, finding_id: str) -> Path:
    """Allocate a fresh, non-overwriting iteration filename."""
    directory = Path(workbook_dir)
    previous = latest_iteration(directory, original_filename)
    number = 1
    if previous:
        match = re.match(r"^iteration_(\d+)_", previous.name)
        number = int(match.group(1)) + 1 if match else 1
    candidate = directory / f"iteration_{number:02d}_{finding_id}_{original_filename}"
    while candidate.exists():
        number += 1
        candidate = directory / f"iteration_{number:02d}_{finding_id}_{original_filename}"
    return candidate
