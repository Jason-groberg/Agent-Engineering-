import base64
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from Simple_Harness.dev_harness import DevHarness, ROLE_INSTRUCTIONS, ROOT


def response(text="Done", calls=(), status="completed"):
    return SimpleNamespace(status=status, output=list(calls), output_text=text)


def call(name, **arguments):
    return SimpleNamespace(type="function_call", name=name, call_id="call-1",
                           arguments=json.dumps(arguments))


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.directory.cleanup)
        self.project = Path(self.directory.name)
        self.client, self.tracker = Mock(), Mock()
        self.harness = DevHarness(self.project, self.client, self.tracker, "test-model")

    def run_quietly(self, task="Build a portfolio", role=None):
        with patch("builtins.print"):
            self.harness.run(task, role)

    def test_file_tools_and_atomic_failure_preserve_existing_content(self):
        self.harness.write_file("src/index.html", "old")
        self.assertEqual(self.harness.read_file("src/index.html"), "old")
        self.assertEqual(self.harness.list_files("."), ["src/"])
        with patch("Simple_Harness.dev_harness.os.replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                self.harness.write_file("src/index.html", "new")
        self.assertEqual(self.harness.read_file("src/index.html"), "old")
        self.assertEqual(list((self.project / "src").iterdir()),
                         [self.project / "src/index.html"])

    def test_path_boundary_and_excluded_files(self):
        for path in ("../escape.txt", str(ROOT / "tool_chat.py"), ".env",
                     ".env.local", "REPORTS/result.txt", ".git/config",
                     "Past_Prompts/prompt.txt", "Codex_Usage_Tracking/log.txt"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.harness.project_path(path)
        for project in (ROOT, ROOT.parent, ROOT / "Reports/project"):
            with self.subTest(project=project), self.assertRaises(ValueError):
                DevHarness(project, self.client, self.tracker, "test-model")

    def test_resolved_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as outside:
            link = self.project / "linked"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("Symlink creation is unavailable on this Windows account.")
            try:
                with self.assertRaises(ValueError):
                    self.harness.project_path("linked/file.txt")
                self.assertEqual(self.harness.list_files("."), [])
            finally:
                link.unlink()

    def test_role_order_context_handoff_and_response_tracking(self):
        snapshots = []

        def create(**kwargs):
            snapshots.append({**kwargs, "input": list(kwargs["input"])})
            name = tuple(ROLE_INSTRUCTIONS)[len(snapshots) - 1]
            item = SimpleNamespace(type="message", role="assistant", phase="final_answer",
                                   content=f"{name} report")
            return SimpleNamespace(status="completed", output=[item], output_text=item.content)

        self.client.responses.create.side_effect = create
        self.run_quietly()
        self.assertEqual(self.tracker.track.call_count, 4)
        self.assertIn("Now perform the planning role.", snapshots[0]["input"][-1]["content"])
        self.assertIn("planning report", [getattr(item, "content", None)
                                          for item in snapshots[1]["input"]])
        self.assertEqual(snapshots[1]["input"][2].phase, "final_answer")
        expected = [
            {"list_files", "read_file"},
            {"list_files", "read_file", "generate_asset"},
            {"list_files", "read_file", "write_file"},
            {"list_files", "read_file"},
        ]
        self.assertEqual([{tool["name"] for tool in entry["tools"]} for entry in snapshots], expected)
        for tracking_call in self.tracker.track.call_args_list:
            self.assertEqual(tracking_call.args[2], "Build a portfolio")

    def test_unauthorized_role_tool_is_rejected_at_dispatch(self):
        self.client.responses.create.side_effect = [
            response(calls=[call("write_file", path="forbidden.txt", content="oops")]),
            response(),
        ]
        self.run_quietly(role="review")
        self.assertFalse((self.project / "forbidden.txt").exists())
        output = self.client.responses.create.call_args.kwargs["input"][-1]
        self.assertIn("unavailable to review", json.loads(output["output"])["error"])
        self.assertEqual(self.tracker.track.call_count, 2)

    def test_incomplete_response_stops_pipeline_and_is_tracked(self):
        self.client.responses.create.return_value = response(status="incomplete")
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            self.run_quietly()
        self.assertEqual(self.client.responses.create.call_count, 1)
        self.assertEqual(self.tracker.track.call_count, 1)

    def test_tool_loop_limit_stops_pipeline(self):
        self.client.responses.create.return_value = response(calls=[call("list_files", path=".")])
        with self.assertRaisesRegex(RuntimeError, "limit of 10"):
            self.run_quietly()
        self.assertEqual(self.client.responses.create.call_count, 10)
        self.assertEqual(self.tracker.track.call_count, 10)

    def test_pixellab_request_and_both_base64_formats(self):
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWuQAAAAASUVORK5CYII="
        )
        for index, prefix in enumerate(("", "data:image/png;base64,")):
            payload = {"image": {"type": "base64", "base64": prefix + base64.b64encode(png).decode()},
                       "usage": {"type": "usd", "usd": 0.01}}
            with patch.dict(os.environ, {"PIXELLAB_API_KEY": "test-secret"}, clear=True), \
                    patch("Simple_Harness.dev_harness.urlopen") as urlopen:
                urlopen.return_value.__enter__.return_value = io.StringIO(json.dumps(payload))
                result = self.harness.generate_asset("mascot", f"assets/{index}.png", 128, 64, True)
            self.assertEqual((self.project / result["path"]).read_bytes(), png)
            self.assertEqual(result["usage"], payload["usage"])
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, "https://api.pixellab.ai/v1/generate-image-pixflux")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
            self.assertEqual(json.loads(request.data), {
                "description": "mascot", "image_size": {"width": 128, "height": 64},
                "no_background": True,
            })

    def test_asset_validation_prevents_requests_and_overwrite(self):
        self.harness.write_file("existing.png", "keep")
        with patch.dict(os.environ, {}, clear=True), patch("Simple_Harness.dev_harness.urlopen") as urlopen:
            for arguments in (("mascot", "existing.png", 128, 128, True),
                              ("mascot", "bad.jpg", 128, 128, True),
                              ("mascot", "bad.png", 401, 128, True),
                              ("mascot", "bad.png", True, 128, True),
                              ("", "bad.png", 128, 128, True),
                              ("mascot", "bad.png", 128, 128, True)):
                with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                    self.harness.generate_asset(*arguments)
            urlopen.assert_not_called()
        self.assertEqual(self.harness.read_file("existing.png"), "keep")

    def test_pixellab_failure_does_not_retry_or_create_an_asset(self):
        for error in (HTTPError("url", 402, "credits", {}, None), URLError("network")):
            with patch.dict(os.environ, {"PIXELLAB_API_KEY": "test-secret"}, clear=True), \
                    patch("Simple_Harness.dev_harness.urlopen", side_effect=error) as urlopen:
                with self.assertRaises(RuntimeError):
                    self.harness.generate_asset("mascot", "asset.png", 128, 128, True)
                urlopen.assert_called_once()
                self.assertFalse((self.project / "asset.png").exists())

    def test_malformed_image_does_not_create_an_asset(self):
        payload = {"image": {"type": "base64", "base64": "not valid base64"}}
        with patch.dict(os.environ, {"PIXELLAB_API_KEY": "test-secret"}, clear=True), \
                patch("Simple_Harness.dev_harness.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = io.StringIO(json.dumps(payload))
            with self.assertRaises(ValueError):
                self.harness.generate_asset("mascot", "asset.png", 128, 128, True)
        self.assertFalse((self.project / "asset.png").exists())

    def test_main_summarizes_and_saves_usage_on_failure(self):
        # Stub imports so this test never opens the existing tracker or dotenv file.
        tracker = Mock()
        modules = {"usage_tracker": SimpleNamespace(UsageTracker=Mock(return_value=tracker)),
                   "openai": SimpleNamespace(OpenAI=Mock()),
                   "dotenv": SimpleNamespace(load_dotenv=Mock())}
        with patch.dict("sys.modules", modules), \
                patch("sys.argv", ["dev_harness.py", "task", "--model", "test-model"]), \
                patch("Simple_Harness.dev_harness.DevHarness", side_effect=RuntimeError("failed")):
            from Simple_Harness.dev_harness import main
            with self.assertRaises(RuntimeError):
                main()
        tracker.print_summary.assert_called_once_with()
        tracker.save_to_file.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
