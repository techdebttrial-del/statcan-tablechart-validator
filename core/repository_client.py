"""
RepositoryClient

Git-backed persistence abstraction for saved review projects, deliberately
shaped to match the broader Accelerator's core/forgejo_client.py (Forgejo
file CRUD) contract: get_file / put_file / list_files / commit history. This
lets the validator run standalone against a local git repo (MVP) while
remaining a drop-in swap for the Accelerator's ForgejoClient later — same
method names, same "optional, degrades gracefully if unset" behavior noted
in the broader review (REVIEW_README.md section 2.2 / 6).

Unlike the broader Accelerator's forgejo_client.py (flagged as having no
unit tests and silently swallowing SHA-lookup errors), this client raises
explicit exceptions on failure and includes a test double
(`InMemoryRepositoryClient`) for unit testing.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


class RepositoryError(Exception):
    pass


@dataclass
class CommitResult:
    commit_id: str
    message: str


class RepositoryClient:
    """Local git-repo-backed implementation usable offline for the MVP."""

    def __init__(self, root_path: str, author_name: str = "esr-validator-bot",
                 author_email: str = "esr-validator-bot@example.invalid"):
        self.root_path = root_path
        self.author_name = author_name
        self.author_email = author_email
        os.makedirs(self.root_path, exist_ok=True)
        if not os.path.exists(os.path.join(self.root_path, ".git")):
            self._run(["git", "init", "-q"])
            self._run(["git", "config", "user.name", self.author_name])
            self._run(["git", "config", "user.email", self.author_email])

    def _run(self, args: List[str]) -> str:
        try:
            result = subprocess.run(
                args, cwd=self.root_path, check=True,
                capture_output=True, text=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RepositoryError(f"git command failed: {' '.join(args)}\n{e.stderr}") from e
        except FileNotFoundError as e:
            raise RepositoryError("git is not installed in this environment") from e

    def put_file(self, relative_path: str, content: bytes, commit_message: str) -> CommitResult:
        full_path = os.path.join(self.root_path, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as fh:
            fh.write(content)
        self._run(["git", "add", relative_path])
        self._run(["git", "commit", "-q", "-m", commit_message, "--allow-empty"])
        commit_id = self._run(["git", "rev-parse", "HEAD"]).strip()
        return CommitResult(commit_id=commit_id, message=commit_message)

    def get_file(self, relative_path: str) -> bytes:
        full_path = os.path.join(self.root_path, relative_path)
        if not os.path.exists(full_path):
            raise RepositoryError(f"File not found: {relative_path}")
        with open(full_path, "rb") as fh:
            return fh.read()

    def list_files(self, prefix: str = "") -> List[str]:
        out = []
        base = os.path.join(self.root_path, prefix)
        if not os.path.exists(base):
            return out
        for dirpath, _, filenames in os.walk(base):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, self.root_path)
                if ".git" not in rel.split(os.sep):
                    out.append(rel)
        return sorted(out)

    def file_exists(self, relative_path: str) -> bool:
        return os.path.exists(os.path.join(self.root_path, relative_path))

    def history(self, relative_path: str) -> List[Dict[str, Any]]:
        out_raw = self._run(["git", "log", "--follow", "--pretty=format:%H|%ad|%s", "--", relative_path])
        history = []
        for line in out_raw.splitlines():
            if not line.strip():
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                history.append({"commit_id": parts[0], "date": parts[1], "message": parts[2]})
        return history


class InMemoryRepositoryClient:
    """Test double with the same interface, no git dependency. For unit tests."""

    def __init__(self):
        self._files: Dict[str, bytes] = {}
        self._commits: List[CommitResult] = []

    def put_file(self, relative_path: str, content: bytes, commit_message: str) -> CommitResult:
        self._files[relative_path] = content
        commit = CommitResult(commit_id=f"mem-{len(self._commits)+1}", message=commit_message)
        self._commits.append(commit)
        return commit

    def get_file(self, relative_path: str) -> bytes:
        if relative_path not in self._files:
            raise RepositoryError(f"File not found: {relative_path}")
        return self._files[relative_path]

    def list_files(self, prefix: str = "") -> List[str]:
        return sorted([p for p in self._files if p.startswith(prefix)])

    def file_exists(self, relative_path: str) -> bool:
        return relative_path in self._files

    def history(self, relative_path: str) -> List[Dict[str, Any]]:
        return [{"commit_id": c.commit_id, "date": "", "message": c.message} for c in self._commits]
