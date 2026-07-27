"""Create and verify a deterministic inventory of tracked governed files."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from common import PolicyError, repository_root
from load_manifest import load_manifest


def canonical_bytes(data: bytes, *, text: bool = True) -> bytes:
    """Normalize CRLF only for files Git classifies as text."""
    return data.replace(b"\r\n", b"\n") if text else data


def _is_text(root: Path, relative: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--eol", "--", relative], text=True, capture_output=True, check=True
    )
    return bool(result.stdout) and result.stdout.split()[0] not in {"i/-text", "i/none"}


def sha256(root: Path, relative: str, data: bytes) -> str:
    return hashlib.sha256(canonical_bytes(data, text=_is_text(root, relative))).hexdigest()


def _tracked(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], text=False, capture_output=True, check=True
    )
    return sorted(path.decode("utf-8") for path in result.stdout.split(b"\0") if path)


def _within(path: str, roots: list[str]) -> bool:
    return any(path == root or path.startswith(root + "/") for root in roots)


def build_inventory(root: Path) -> dict[str, object]:
    manifest = load_manifest(root)
    excluded = manifest["generated_file_roots"] + [manifest["run_storage"]["run_directory"]]
    files = []
    for relative in _tracked(root):
        if not _within(relative, manifest["governed_roots"]) or _within(relative, excluded):
            continue
        path = root / relative
        if path.is_symlink():
            data = path.readlink().as_posix().encode("utf-8")
            kind = "symlink"
        elif path.is_file():
            data = path.read_bytes()
            kind = "file"
        else:
            raise PolicyError(f"tracked governed path is not a file: {relative}")
        canonical = canonical_bytes(data, text=kind == "file" and _is_text(root, relative))
        files.append({"path": relative, "type": kind, "byte_size": len(canonical), "sha256": hashlib.sha256(canonical).hexdigest()})
    return {"schema_version": "1.0", "files": files}


def render(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def check_inventory(root: Path, path: Path) -> bool:
    try:
        return path.is_file() and path.read_text(encoding="utf-8") == render(build_inventory(root))
    except PolicyError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("INVENTORY.json"))
    args = parser.parse_args()
    try:
        root = repository_root()
        output = (root / args.output).resolve()
        output.relative_to(root)
        expected = render(build_inventory(root))
        if args.check:
            if not check_inventory(root, output):
                raise PolicyError(f"inventory drift: {args.output.as_posix()}")
        else:
            output.write_text(expected, encoding="utf-8", newline="\n")
    except (OSError, subprocess.CalledProcessError, PolicyError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
