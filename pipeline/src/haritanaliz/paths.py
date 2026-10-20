"""Locating the repository root and the config folder."""

from __future__ import annotations

import os
from pathlib import Path

ROOT_ENV_VAR = "HARITANALIZ_ROOT"
_MARKER = Path("config") / "settings.yaml"


class RepoRootNotFoundError(RuntimeError):
    """The repository root (the folder that contains config/settings.yaml) was not found."""


def find_repo_root(start: Path | None = None) -> Path:
    """Return the repository root.

    Lookup order: the HARITANALIZ_ROOT environment variable, then the first parent of
    ``start`` (default: the current directory) that contains ``config/settings.yaml``,
    then the parents of this package (works for the editable install used by uv).
    """
    env_root = os.environ.get(ROOT_ENV_VAR)
    if env_root:
        root = Path(env_root).expanduser().resolve()
        if not (root / _MARKER).is_file():
            raise RepoRootNotFoundError(
                f"{ROOT_ENV_VAR}={env_root} does not contain {_MARKER.as_posix()}"
            )
        return root

    starts = [(start or Path.cwd()).resolve(), Path(__file__).resolve()]
    for candidate in starts:
        for directory in (candidate, *candidate.parents):
            if (directory / _MARKER).is_file():
                return directory
    raise RepoRootNotFoundError(f"Could not find {_MARKER.as_posix()} above {starts[0]}")


def default_config_dir(root: Path | None = None) -> Path:
    """Return ``<repo root>/config``."""
    return (root if root is not None else find_repo_root()) / "config"
