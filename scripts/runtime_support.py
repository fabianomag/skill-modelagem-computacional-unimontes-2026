"""Portable, read-only runtime discovery; never installs dependencies."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def runtime_root() -> Path:
    return Path(os.environ.get("MODELAGEM_RUNTIME_DIR", Path.home() / ".cache/modelagem-computacional-grupo")).expanduser().resolve()


def venv_python(root: Path | None = None) -> Path:
    return (root or runtime_root()) / "python" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def codex_enabled() -> bool:
    return os.environ.get("MODELAGEM_DISABLE_CODEX_RUNTIME") != "1"


def python_candidates() -> list[Path]:
    result = [Path(os.environ["MODELAGEM_PYTHON"])] if os.environ.get("MODELAGEM_PYTHON") else []
    result.extend([venv_python(), Path(sys.executable)])
    if codex_enabled():
        result.append(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3")
    # Keep the venv executable path: resolving its symlink would discard the venv.
    return list(dict.fromkeys(candidate.expanduser().absolute() for candidate in result if candidate.is_file()))


def python_with_modules(*modules: str) -> Path | None:
    for candidate in python_candidates():
        code = "import sys; assert sys.version_info >= (3, 10); " + "; ".join(f"import {module}" for module in modules)
        result = subprocess.run([str(candidate), "-c", code], capture_output=True, timeout=30)
        if result.returncode == 0:
            return candidate
    return None


def find_node() -> Path | None:
    configured = os.environ.get("MODELAGEM_NODE")
    if configured:
        candidate = Path(configured).expanduser()
        return candidate.resolve() if candidate.is_file() else None
    found = shutil.which("node")
    if found:
        return Path(found).resolve()
    if codex_enabled():
        candidate = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
        if candidate.is_file():
            return candidate
    return None


def find_libreoffice() -> Path | None:
    configured = os.environ.get("LIBREOFFICE_PATH")
    if configured:
        candidate = Path(configured).expanduser()
        return candidate.resolve() if candidate.is_file() else None
    candidates = [shutil.which("soffice"), shutil.which("libreoffice"), "/Applications/LibreOffice.app/Contents/MacOS/soffice"]
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        if os.environ.get(env_name):
            candidates.append(str(Path(os.environ[env_name]) / "LibreOffice/program/soffice.exe"))
    return next((Path(value).resolve() for value in candidates if value and Path(value).is_file()), None)


def canonical_renderer() -> Path | None:
    configured = os.environ.get("MODELAGEM_DOCX_RENDERER")
    if configured:
        candidate = Path(configured).expanduser()
        return candidate.resolve() if candidate.is_file() else None
    if not codex_enabled():
        return None
    root = Path.home() / ".codex/plugins/cache/openai-primary-runtime/documents"
    candidates = sorted(root.glob("*/skills/documents/render_docx.py"), reverse=True)
    return candidates[0] if candidates else None


def renderer_python() -> Path:
    if os.environ.get("MODELAGEM_RENDERER_PYTHON"):
        return Path(os.environ["MODELAGEM_RENDERER_PYTHON"]).expanduser().absolute()
    if codex_enabled():
        bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
        if bundled.is_file():
            return bundled
    return Path(sys.executable)
