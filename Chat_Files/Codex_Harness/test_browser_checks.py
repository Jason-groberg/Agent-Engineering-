import functools
import io
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from Codex_Harness import browser_checks, setup_browser_tools, phaser


SPEC = {"cases": [{"name": "contact", "path": "/", "steps": [
    {"action": "click", "selector": "a[href='#contact']"},
    {"action": "expect_url", "value": "#contact"},
    {"action": "fill", "selector": "#email", "value": "dev@example.test"},
    {"action": "click", "selector": "button"},
    {"action": "expect_text", "selector": "#status", "value": "Subscribed."},
]}]}
HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Browser verification fixture</title><link rel="icon" href="data:,">
<style>body{font:18px Arial,sans-serif;color:#111;background:white;margin:24px}
input,button{font:inherit;padding:8px;display:block;margin:12px 0}</style></head>
<body><nav aria-label="Main"><a href="#contact">Contact</a></nav><main>
<h1>Verification fixture</h1><section id="contact"><h2>Contact</h2>
<form><label for="email">Email</label><input id="email" type="email" required>
<button type="submit">Subscribe</button><p id="status" role="status"></p></form>
</section></main><script>document.querySelector('form').addEventListener('submit',event=>{
event.preventDefault();document.querySelector('#status').textContent='Subscribed.';});
</script></body></html>"""


class BrowserBoundaryTests(unittest.TestCase):
    def test_host_requests_reject_unsafe_tokens_and_remote_urls(self):
        with tempfile.TemporaryDirectory(dir=browser_checks.BASE) as directory:
            project = Path(directory)
            with self.assertRaises(ValueError):
                browser_checks.request_files(project, "../escape")
            with self.assertRaises(ValueError):
                browser_checks.request_local_checks(project, "https://example.com", uuid4().hex)

    def test_host_worker_returns_errors_without_executing_remote_targets(self):
        with tempfile.TemporaryDirectory(dir=browser_checks.BASE) as directory:
            project, token = Path(directory), uuid4().hex
            request, response = browser_checks.request_files(project, token)
            with patch.object(browser_checks.subprocess, "Popen") as launch, \
                    browser_checks.local_browser_worker(project, token):
                request.write_text(json.dumps({"id": uuid4().hex, "url": "https://example.com"}))
                import time
                deadline = time.monotonic() + 3
                while not response.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                result = json.loads(response.read_text())["result"]
                self.assertTrue(all(check["result"] == "failed" for check in result["checks"]))
                launch.assert_not_called()

    def test_only_local_urls_without_credentials_are_allowed(self):
        self.assertEqual(browser_checks.local_url("http://127.0.0.1:8123/"), "http://127.0.0.1:8123/")
        for url in ("https://example.com", "file:///secret", "http://localhost.example.com",
                    "http://user:password@localhost", "http://localhost:bad"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                browser_checks.local_url(url)

    def test_specs_require_safe_unique_cases_and_meaningful_checks(self):
        self.assertEqual(browser_checks.validate_spec(SPEC), SPEC)
        case = SPEC["cases"][0]
        for spec in ({"cases": []}, {"cases": [case, case]},
                     {"cases": [{**case, "name": "../escape"}]},
                     {"cases": [{**case, "steps": [{"action": "click", "selector": "body"}]}]},
                     {"cases": [{**case, "steps": [{"action": "eval", "value": "anything"}]}]}):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                browser_checks.validate_spec(spec)

    def test_axe_download_rejects_corrupt_archive_before_writing(self):
        version = setup_browser_tools.AXE_VERSION
        metadata = {"dist": {"tarball": f"https://registry.npmjs.org/axe-core/-/axe-core-{version}.tgz",
                             "integrity": "sha512-invalid"}}
        with tempfile.TemporaryDirectory(dir=browser_checks.BASE) as directory, \
                patch.object(setup_browser_tools, "BASE", Path(directory)), \
                patch.object(setup_browser_tools, "urlopen", side_effect=[
                    io.BytesIO(json.dumps(metadata).encode()), io.BytesIO(b"corrupt archive")]):
            with self.assertRaisesRegex(ValueError, "integrity"):
                setup_browser_tools.install_axe()
            self.assertFalse((Path(directory) / ".browser_tools").exists())


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless((browser_checks.BASE / ".browser_tools/axe-core/axe.min.js").exists(),
                     "Run Codex_Harness.setup_browser_tools first.")
class BrowserIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=browser_checks.BASE)
        self.addCleanup(self.directory.cleanup)
        self.project = Path(self.directory.name)
        (self.project / "browser_checks.json").write_text(json.dumps(SPEC), encoding="utf-8")
        handler = functools.partial(QuietHandler, directory=str(self.project))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.url = f"http://127.0.0.1:{self.server.server_port}/"

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_actual_interactions_axe_and_screenshots_pass(self):
        (self.project / "index.html").write_text(HTML, encoding="utf-8")
        result = browser_checks.verify(self.project, self.url)
        self.assertTrue(all(check["result"] == "passed" for check in result["checks"]), result["errors"])
        self.assertEqual(len(result["screenshots"]), 4)
        self.assertEqual(len(result["audits"]), 4)
        for image in result["screenshots"]:
            self.assertTrue((self.project / image).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
        saved = json.loads((self.project / ".harness-verification/browser-report.json").read_text())
        self.assertEqual(saved["checks"], result["checks"])

    def test_local_wrapper_executes_browser_checks_and_returns_real_results(self):
        (self.project / "index.html").write_text(HTML, encoding="utf-8")
        token = uuid4().hex
        with browser_checks.local_browser_worker(self.project, token):
            result = browser_checks.request_local_checks(self.project, self.url, token)
        self.assertTrue(all(check["result"] == "passed" for check in result["checks"]), result["errors"])
        self.assertEqual(len(result["screenshots"]), 4)

    def test_missing_label_and_console_error_fail_verification(self):
        broken = HTML.replace('<label for="email">Email</label>', "")
        broken = broken.replace("</script>", "console.error('Deliberate fixture error');</script>")
        (self.project / "index.html").write_text(broken, encoding="utf-8")
        result = browser_checks.verify(self.project, self.url)
        self.assertTrue(all(check["result"] == "failed" for check in result["checks"]))
        self.assertTrue(any("Deliberate fixture error" in error for error in result["errors"]))
        self.assertTrue(any(audit["result"]["violations"] for audit in result["audits"]))

    @unittest.skipUnless((phaser.CACHE / "phaser.min.js").exists(), "Run Codex_Harness.phaser first.")
    def test_cached_phaser_boots_from_local_project_and_renders_in_chromium(self):
        copied = phaser.install(self.project)
        script_path = copied["script"].replace("\\", "/")
        html = HTML.replace("</head>", f'<script src="{script_path}"></script></head>')
        html = html.replace("</main>", '<div id="phaser-preview" aria-hidden="true"></div>'
                            '<p id="phaser-ready" role="status">Starting game</p></main>')
        html = html.replace("</body>", """<script>
window.game = new Phaser.Game({type: Phaser.CANVAS, width: 64, height: 64,
parent: 'phaser-preview', audio: {noAudio: true}, scene: {create() {
this.add.rectangle(32, 32, 32, 32, 0x00ccff);
document.querySelector('#phaser-ready').textContent = 'Phaser ' + Phaser.VERSION + ' ready';
}}});</script></body>""")
        (self.project / "index.html").write_text(html, encoding="utf-8")
        spec = {"cases": [{"name": "phaser", "path": "/", "steps": [
            {"action": "click", "selector": "a[href='#contact']"},
            {"action": "expect_text", "selector": "#phaser-ready", "value": f"Phaser {phaser.VERSION} ready"},
            {"action": "expect_visible", "selector": "#phaser-preview canvas"},
        ]}]}
        (self.project / "browser_checks.json").write_text(json.dumps(spec), encoding="utf-8")
        result = browser_checks.verify(self.project, self.url)
        self.assertTrue(all(check["result"] == "passed" for check in result["checks"]), result["errors"])
        self.assertEqual(len(result["screenshots"]), 4)


if __name__ == "__main__":
    unittest.main()
