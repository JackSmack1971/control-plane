"""Shared safe path helpers for control-plane scripts."""

from __future__ import annotations

from pathlib import Path, PurePosixPath


class PolicyError(ValueError):
    """Raised when manifest policy is unsafe or invalid."""

    def __init__(self, message: str):
        super().__init__(message if message.startswith("CP") else rejection("CP000", message))


def rejection(code: str, message: str) -> str:
    """Return a stable, actionable rejection message."""
    return f"{code}: {message}"


def repository_root(start: Path | None = None) -> Path:
    """Find the repository root without trusting the process working directory."""
    current = (start or Path(__file__)).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() and (candidate / ".claude/control-plane/manifest.yaml").is_file():
            return candidate
    raise PolicyError("unable to resolve repository root")


def repo_path(root: Path, value: str, *, glob: bool = False) -> str:
    """Return a validated POSIX repository-relative path."""
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/") or ":" in value:
        raise PolicyError(f"path must be POSIX repository-relative: {value!r}")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise PolicyError(f"path traversal is not allowed: {value!r}")
    path = PurePosixPath(value)
    if not glob and "*" in value:
        raise PolicyError(f"wildcards are not allowed in paths: {value!r}")
    if glob and "*" in value and (not value.endswith("/**") or value.count("**") != 1 or "*" in value.removesuffix("/**")):
        raise PolicyError(f"malformed glob pattern: {value!r}")
    resolved = (root / path).resolve(strict=False)
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise PolicyError(f"path escapes repository: {value!r}") from error
    return path.as_posix()
