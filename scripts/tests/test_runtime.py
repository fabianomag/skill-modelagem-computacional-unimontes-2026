"""Portable discovery and safe setup tests; no downloads or global writes."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import runtime_support
import setup_runtime
import ingest_source
import build_report_pdf


class RuntimeTests(unittest.TestCase):
    def test_codex_can_be_disabled(self):
        with patch.dict(os.environ, {"MODELAGEM_DISABLE_CODEX_RUNTIME": "1"}):
            self.assertIsNone(runtime_support.canonical_renderer())
            self.assertFalse(any("codex-runtimes" in str(path) for path in runtime_support.python_candidates() if path != Path(sys.executable).resolve()))

    def test_libreoffice_explicit_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "soffice"
            executable.touch()
            with patch.dict(os.environ, {"LIBREOFFICE_PATH": str(executable), "MODELAGEM_DISABLE_CODEX_RUNTIME": "1"}):
                self.assertEqual(runtime_support.find_libreoffice(), executable.resolve())

    def test_invalid_libreoffice_override_does_not_silently_use_another_install(self):
        with patch.dict(os.environ, {"LIBREOFFICE_PATH": "/nonexistent-modelagem/soffice"}):
            self.assertIsNone(runtime_support.find_libreoffice())

    def test_ingestion_does_not_download_when_markitdown_missing(self):
        with patch.object(ingest_source, "python_with_modules", return_value=None), patch.object(ingest_source.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Não há download implícito"):
                ingest_source.markitdown_command(".pdf")

    def test_ingestion_uses_existing_python(self):
        with patch.object(ingest_source, "python_with_modules", return_value=Path("/portable/python")):
            self.assertEqual(ingest_source.markitdown_command(".pdf"), ["/portable/python", "-m", "markitdown"])

    def test_venv_symlink_is_not_resolved_to_system_python(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            python = root / "python/bin/python"
            python.parent.mkdir(parents=True)
            python.symlink_to(sys.executable)
            with patch.dict(os.environ, {"MODELAGEM_RUNTIME_DIR": str(root), "MODELAGEM_DISABLE_CODEX_RUNTIME": "1"}):
                self.assertIn(python, runtime_support.python_candidates())

    def test_preflight_never_installs(self):
        with patch.object(setup_runtime, "find_node", return_value=None), patch.object(setup_runtime, "python_with_modules", return_value=None), patch.object(setup_runtime, "find_libreoffice", return_value=None), patch.object(setup_runtime, "canonical_renderer", return_value=None), patch.object(setup_runtime, "install") as installation:
            result = setup_runtime.check()
            self.assertFalse(result["ready"])
            self.assertTrue(result["diagnostic_only"])
            installation.assert_not_called()

    def test_libreoffice_conversion_has_isolated_profile_and_pdf_qa(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            docx, out = root / "input.docx", root / "render"
            docx.touch()
            commands = []
            def fake_run(command):
                commands.append(command)
                (out / "input.pdf").write_bytes(b"%PDF-fake")
            with patch.object(build_report_pdf, "find_libreoffice", return_value=Path("/portable/soffice")), patch.object(build_report_pdf, "run_checked", side_effect=fake_run), patch.object(build_report_pdf, "render_pdf_pages") as render:
                build_report_pdf.render_with_libreoffice(docx, out, root)
            self.assertIn(f"-env:UserInstallation={(root / 'libreoffice-profile').as_uri()}", commands[0])
            self.assertIn("pdf:writer_pdf_Export", commands[0])
            render.assert_called_once_with(out / "input.pdf", out)

    @unittest.skipUnless(shutil.which("node"), "Node local não instalado")
    def test_node_isolated_modules_without_codex(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "node/node_modules/test-modelagem-module"
            package.mkdir(parents=True)
            (package / "index.js").write_text("module.exports = {portable: true};\n")
            env = os.environ.copy()
            env.pop("RUNTIME_NODE_MODULES", None)
            env.update({"MODELAGEM_RUNTIME_DIR": str(root), "MODELAGEM_DISABLE_CODEX_RUNTIME": "1"})
            code = "const r = require(process.argv[1]); console.log(JSON.stringify({roots:r.moduleRoots(), value:r.runtimeRequire('test-modelagem-module')}));"
            result = subprocess.run([shutil.which("node"), "-e", code, str(SCRIPTS / "node_runtime.cjs")], capture_output=True, text=True, env=env, check=True)
            data = json.loads(result.stdout)
            self.assertTrue(data["value"]["portable"])
            self.assertFalse(any("codex-runtimes" in value for value in data["roots"]))

    @unittest.skipUnless(shutil.which("node"), "Node local não instalado")
    def test_browser_cache_selected_before_playwright_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            browsers = root / "browsers"
            browsers.mkdir()
            executable = browsers / "chromium"
            executable.touch(); executable.chmod(0o755)
            package = root / "node/node_modules/playwright"
            package.mkdir(parents=True)
            (package / "index.js").write_text("const p=require('path'); const captured=process.env.PLAYWRIGHT_BROWSERS_PATH; module.exports={chromium:{executablePath:()=>p.join(captured,'chromium')}};\n")
            env = os.environ.copy()
            for name in ("RUNTIME_NODE_MODULES", "PLAYWRIGHT_BROWSERS_PATH", "CHROME_PATH"):
                env.pop(name, None)
            env.update({"MODELAGEM_RUNTIME_DIR": str(root), "MODELAGEM_DISABLE_CODEX_RUNTIME": "1"})
            code = "const r=require(process.argv[1]); r.runtimeRequire('playwright'); console.log(r.chromeExecutable());"
            result = subprocess.run([shutil.which("node"), "-e", code, str(SCRIPTS / "node_runtime.cjs")], capture_output=True, text=True, env=env, check=True)
            self.assertEqual(result.stdout.strip(), str(executable))


if __name__ == "__main__":
    unittest.main()
