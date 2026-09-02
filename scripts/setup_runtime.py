#!/usr/bin/env python3
"""Check portability; install only with explicit --install, in a private cache."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from runtime_support import canonical_renderer, find_libreoffice, find_node, python_with_modules, runtime_root, venv_python

SCRIPT_DIR = Path(__file__).resolve().parent
MARKER = "modelagem-computacional-runtime-v1"


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, **kwargs)


def node_diagnostic(node: Path, smoke: bool) -> dict:
    program = r"""
const r = require(process.argv[1]);
(async () => {
  const modules = {};
  for (const name of ['marked', 'playwright', 'pdf-lib']) {
    try { r.runtimeRequire(name); modules[name] = true; }
    catch (error) { modules[name] = error.message; }
  }
  let browser, browserError;
  try {
    browser = r.chromeExecutable();
    if (process.argv[2] === 'smoke') {
      const b = await r.launchChromium();
      try { const p = await b.newPage(); await p.setContent('<title>runtime-ok</title>'); await p.pdf(); }
      finally { await b.close(); }
    }
  } catch (error) { browserError = error.message; }
  console.log(JSON.stringify({version: process.versions.node, modules, browser, browserError}));
})();
"""
    result = subprocess.run([str(node), "-e", program, str(SCRIPT_DIR / "node_runtime.cjs"), "smoke" if smoke else "check"], capture_output=True, text=True, timeout=90)
    if result.returncode:
        return {"error": (result.stderr or result.stdout).strip()}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": result.stdout.strip() or "Node não retornou diagnóstico."}


def check(smoke: bool = False) -> dict:
    node = find_node()
    node_result = node_diagnostic(node, smoke) if node else {"error": "Node.js >=20.19 não encontrado no PATH ou MODELAGEM_NODE."}
    python_tools = {module: python_with_modules(module) for module in ("docx", "markitdown", "pypdf", "pypdfium2", "PIL")}
    python = python_tools["docx"]
    libreoffice = find_libreoffice()
    renderer = canonical_renderer()
    version = tuple(int(part) for part in node_result.get("version", "0.0.0").split(".")[:3])
    node_ok = version >= (20, 19, 0) and all(node_result.get("modules", {}).get(name) is True for name in ("marked", "playwright", "pdf-lib")) and not node_result.get("browserError")
    return {
        "ready": bool(node_ok and all(python_tools.values()) and (libreoffice or renderer)),
        "diagnostic_only": True,
        "runtime_dir": str(runtime_root()),
        "node": str(node) if node else None,
        "node_check": node_result,
        "python": str(python) if python else None,
        "python_modules": {module: str(executable) if executable else None for module, executable in python_tools.items()},
        "missing_python_modules": [module for module, executable in python_tools.items() if not executable],
        "python_requirement": "Python >=3.10; módulos: docx, markitdown, pypdf, pypdfium2, PIL",
        "libreoffice": str(libreoffice) if libreoffice else None,
        "codex_renderer_optional": str(renderer) if renderer else None,
        "next_step": "Se faltarem bibliotecas, autorize setup_runtime.py --install. Node/Python e LibreOffice são pré-requisitos locais; este script não instala aplicativos nem pacotes globais.",
        "visual_qa": "--smoke testa a impressão Chromium; a inspeção visual dos PDFs gerados continua obrigatória.",
    }


def install() -> None:
    if sys.version_info < (3, 10):
        raise RuntimeError("Use Python >=3.10 para criar o ambiente isolado.")
    node = find_node()
    npm = shutil.which("npm")
    if not node or not npm:
        raise RuntimeError("Instale Node.js >=20.19 com npm localmente antes de autorizar este setup.")
    version = run([str(node), "-p", "process.versions.node"], capture_output=True, text=True).stdout.strip()
    if tuple(map(int, version.split('.')[:3])) < (20, 19, 0):
        raise RuntimeError("Node.js >=20.19 é necessário para marked e Playwright.")
    root = runtime_root()
    skill = SCRIPT_DIR.parent
    if root in {Path(root.anchor), Path.home().resolve(), Path.cwd().resolve(), skill} or root in skill.parents:
        raise RuntimeError("Escolha uma pasta privada para o runtime, não uma raiz, HOME, workspace ou pasta da skill.")
    marker_path = root / "runtime.json"
    if root.exists() and any(root.iterdir()):
        try:
            existing = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise RuntimeError("A pasta de runtime já contém arquivos sem identificação deste setup; escolha outra com --runtime-dir.") from None
        if existing.get("kind") != MARKER:
            raise RuntimeError("A pasta de runtime pertence a outro ambiente; escolha outra.")
    root.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(json.dumps({"kind": MARKER}) + "\n", encoding="utf-8")
    python = venv_python()
    if not python.is_file():
        print("Criando virtualenv isolado...", flush=True)
        run([sys.executable, "-m", "venv", str(root / "python")])
    print("Instalando dependências Python somente no virtualenv...", flush=True)
    run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(SCRIPT_DIR / "runtime-requirements.txt")])
    node_root = root / "node"
    node_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPT_DIR / "runtime-package.json", node_root / "package.json")
    print("Instalando dependências Node somente no cache privado...", flush=True)
    run([npm, "install", "--prefix", str(node_root), "--ignore-scripts", "--no-audit", "--no-fund"])
    print("Baixando Chromium somente no cache privado...", flush=True)
    browser_env = os.environ.copy()
    browser_env["PLAYWRIGHT_BROWSERS_PATH"] = str(root / "browsers")
    run([str(node), str(node_root / "node_modules/playwright/cli.js"), "install", "chromium"], env=browser_env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, help="Cache privado alternativo; informe o mesmo caminho nas próximas execuções via MODELAGEM_RUNTIME_DIR.")
    parser.add_argument("--install", action="store_true", help="Autorização explícita para baixar/instalar somente no cache privado; não instala Node/Python/LibreOffice.")
    parser.add_argument("--smoke", action="store_true", help="Abrir Chromium headless e testar impressão em memória.")
    args = parser.parse_args()
    if args.runtime_dir:
        os.environ["MODELAGEM_RUNTIME_DIR"] = str(args.runtime_dir.expanduser().resolve())
    try:
        if args.install:
            install()
        result = check(args.smoke)
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(f"Runtime: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
