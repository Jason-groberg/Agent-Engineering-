import copy
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from Codex_Harness import codex_harness as harness


REPORT = {
    "status": "completed", "summary": "Implemented and verified.",
    "checks": [
        {"kind": "test", "result": "passed", "evidence": "python -m unittest: 1 passed"},
        {"kind": "page", "result": "passed", "evidence": "desktop.png and mobile.png inspected"},
        {"kind": "browser", "result": "passed", "evidence": "Primary journeys passed at both sizes."},
        {"kind": "accessibility", "result": "passed", "evidence": "axe: zero violations."},
    ],
    "changes": ["index.html"], "findings": [], "questions": [],
}
# A real local child process exercises stdin, event streaming, and the output report file.
FAKE_CLI = """
import json, pathlib, sys
prompt = sys.stdin.read()
pathlib.Path(sys.argv[1]).write_text(sys.argv[2], encoding='utf-8')
print(json.dumps({'type': 'thread.started', 'thread_id': 'test-thread'}))
print(json.dumps({'type': 'item.completed', 'item': {'type': 'command_execution', 'exit_code': 0}}))
print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 20, 'cached_input_tokens': 5, 'output_tokens': 10}}))
"""


class CodexHarnessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=harness.BASE)
        self.addCleanup(self.directory.cleanup)
        role_directory = Path(self.directory.name) / "roles"
        role_directory.mkdir()
        for _, filename in harness.ROLES.values():
            (role_directory / filename).write_text(
                (harness.BASE / "roles" / filename).read_text(encoding="utf-8"), encoding="utf-8")
        self.project = Path(self.directory.name) / "project"
        self.project.mkdir()
        self.run_dir = Path(self.directory.name) / "reports"
        self.run_dir.mkdir()
        self.tracker = Mock()

    def test_project_boundary_and_reserved_directories(self):
        for path in (harness.BASE, harness.BASE.parent, "../Simple_Harness", "runs/project",
                     "REPORTS/project", "roles/project", "sessions/project", ".codex/project", ".env.local",
                     ".game_tools/project"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                harness.project_path(path)
        self.assertEqual(harness.project_path(self.project), self.project.resolve())

    def test_role_sandboxes_and_minimal_tools(self):
        for role, (sandbox, _) in harness.ROLES.items():
            argv = harness.command("codex", self.project, role, "test-model", self.run_dir / "report.json")
            self.assertEqual(argv[argv.index("--sandbox") + 1], sandbox)
            self.assertIn("sandbox_workspace_write.network_access=" +
                          ("true" if role in ("ui", "developer") else "false"), argv)
            self.assertIn("--ignore-user-config", argv)
            self.assertIn("--ephemeral", argv)
            self.assertIn("--strict-config", argv)
            self.assertIn("mcp_servers={}", argv)
            self.assertEqual(argv[argv.index("--enable") + 1], "view_image")
            self.assertIn("features.skip_host_skill_discovery=true", argv)
            self.assertIn('approval_policy="never"', argv)
            expected_search = "live" if role in ("planning", "ui", "developer") else "disabled"
            self.assertIn(f'web_search="{expected_search}"', argv)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)
            disabled = [argv[index + 1] for index, value in enumerate(argv) if value == "--disable"]
            self.assertEqual(disabled, list(harness.DISABLED_FEATURES))
            self.assertEqual(argv[-1], "-")

    def test_real_subprocess_events_report_and_tracker_adapter(self):
        def command(*arguments):
            return [sys.executable, "-B", "-c", FAKE_CLI, str(arguments[-1]), json.dumps(REPORT)]

        with patch.object(harness, "command", side_effect=command), patch("builtins.print"):
            report = harness.run_role("codex", self.project, "developer", "test-model",
                                      "A unicode brief: café", self.run_dir, self.tracker, "task")
        self.assertEqual(report, REPORT)
        self.tracker.track.assert_called_once()
        response, elapsed, task = self.tracker.track.call_args.args
        self.assertEqual(response.id, "test-thread")
        self.assertEqual(response.model, "test-model")
        self.assertEqual(response.usage.total_tokens, 30)
        self.assertEqual(response.usage.input_tokens_details.cached_tokens, 5)
        self.assertGreaterEqual(elapsed, 0)
        self.assertEqual(task, "task")
        self.assertIn("café", (self.run_dir / "developer.prompt.txt").read_text(encoding="utf-8"))
        self.assertEqual(len((self.run_dir / "developer.events.jsonl").read_text().splitlines()), 3)
        self.assertIn(f'"{harness.BASE / "phaser.py"}" --project "{self.project}"',
                      (self.run_dir / "developer.prompt.txt").read_text(encoding="utf-8"))

    def test_failed_cli_stops_even_if_report_exists(self):
        script = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2]); sys.exit(1)"
        with patch.object(harness, "command", side_effect=lambda *args: [
            sys.executable, "-B", "-c", script, str(args[-1]), json.dumps(REPORT)
        ]), patch("builtins.print"):
            with self.assertRaisesRegex(RuntimeError, "did not complete"):
                harness.run_role("codex", self.project, "ui", "test-model", "task",
                                 self.run_dir, self.tracker, "task")
        self.tracker.track.assert_not_called()

    def test_report_validation_and_verification_gate(self):
        self.assertEqual(harness.validate_report(REPORT), REPORT)
        self.assertTrue(harness.verification_complete(REPORT))
        variants = [
            {**REPORT, "checks": []},
            {**REPORT, "status": "blocked"},
            {**REPORT, "findings": [{"owner": "ui", "description": "index.html: broken link"}]},
            {**REPORT, "checks": [REPORT["checks"][0]]},
            {**REPORT, "checks": [{"kind": "build", "result": "passed", "evidence": "build passed"}, REPORT["checks"][1]]},
            {**REPORT, "checks": [check for check in REPORT["checks"] if check["kind"] != "accessibility"]},
            {**REPORT, "checks": [*REPORT["checks"], {"kind": "asset", "result": "not_run", "evidence": "missing"}]},
        ]
        for report in variants:
            with self.subTest(report=report):
                self.assertFalse(harness.verification_complete(report))
        invalid = copy.deepcopy(REPORT)
        invalid["checks"][0]["evidence"] = ""
        for report in ({}, {**REPORT, "status": "PASS"}, {**REPORT, "changes": "file"}, invalid,
                       {**REPORT, "findings": ["missing owner"]},
                       {**REPORT, "status": "needs_input", "questions": ["Question?"] * 4}):
            with self.subTest(report=report), self.assertRaises(ValueError):
                harness.validate_report(report)

    def test_invalid_usage_is_rejected(self):
        for usage in ({"input_tokens": -1, "output_tokens": 1},
                      {"input_tokens": True, "output_tokens": 1},
                      {"input_tokens": 1, "output_tokens": 1, "cached_input_tokens": 2}):
            with self.subTest(usage=usage), self.assertRaises(ValueError):
                harness.usage_response("test-model", "thread", usage)

    def test_order_and_report_handoffs(self):
        calls = []

        def run_role(*arguments):
            calls.append((arguments[2], arguments[4]))
            return copy.deepcopy(REPORT)

        # Keep all generated test run records in the disposable test directory.
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness.shutil, "which", return_value="codex"), \
                patch.object(harness, "run_role", side_effect=run_role), patch("builtins.print"):
            self.assertTrue(harness.run("Build a café site", "test-model", "project", self.tracker))
        self.assertEqual([role for role, _ in calls], list(harness.ROLES))
        self.assertIn('"planning":', calls[1][1])
        self.assertIn('"developer":', calls[3][1])
        self.assertIn("café", calls[0][1])

    def test_role_files_are_loaded_once_per_session_and_reloaded_next_session(self):
        ui_path = Path(self.directory.name) / "roles" / "ui.md"
        ui_path.write_text("Original UI guidance: café.\n", encoding="utf-8")
        ui_prompts = []

        def run_role(*arguments):
            if arguments[2] == "planning":
                ui_path.write_text("Updated UI guidance.\n", encoding="utf-8")
            if arguments[2] == "ui":
                ui_prompts.append(arguments[4])
            return copy.deepcopy(REPORT)

        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness.shutil, "which", return_value="codex"), \
                patch.object(harness, "run_role", side_effect=run_role), patch("builtins.print"):
            self.assertTrue(harness.run("Build a site", "test-model", "project", self.tracker))
            self.assertTrue(harness.run("Build a site", "test-model", "project", self.tracker))
        self.assertIn("Original UI guidance: café.", ui_prompts[0])
        self.assertNotIn("Updated UI guidance.", ui_prompts[0])
        self.assertIn("Updated UI guidance.", ui_prompts[1])

    def test_missing_role_file_stops_before_any_agent_starts(self):
        (Path(self.directory.name) / "roles" / "review.md").unlink()
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness, "run_role") as run_role:
            with self.assertRaises(FileNotFoundError):
                harness.run("Build a site", "test-model", "project", self.tracker)
        run_role.assert_not_called()

    def test_blocked_planning_stops_without_running_next_roles(self):
        blocked = {**REPORT, "status": "blocked", "findings": []}
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness.shutil, "which", return_value="codex"), \
                patch.object(harness, "run_role", return_value=blocked) as run_role, patch("builtins.print"):
            self.assertFalse(harness.run("Accept payments", "test-model", "project", self.tracker))
        run_role.assert_called_once()

    def test_planning_intake_collects_answers_before_implementation(self):
        intake = {**REPORT, "status": "needs_input", "questions": ["Which payment provider?"]}
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness.shutil, "which", return_value="codex"), \
                patch.object(harness, "run_role", side_effect=[intake, REPORT, REPORT, REPORT, REPORT]) as run_role, \
                patch("builtins.input", return_value="Stripe") as input_, patch("builtins.print"):
            self.assertTrue(harness.run("Build a site", "test-model", "project", self.tracker))
        input_.assert_called_once()
        calls = run_role.call_args_list
        self.assertEqual([entry.args[2] for entry in calls], ["planning", "planning", "ui", "developer", "review"])
        self.assertEqual(calls[0].args[-1], "planning-intake")
        self.assertIn("Stripe", calls[1].args[4])
        self.assertIn("Stripe", calls[2].args[4])

    def test_unanswered_intake_does_not_start_ui_or_developer(self):
        intake = {**REPORT, "status": "needs_input", "questions": ["Who is the audience?"]}
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness.shutil, "which", return_value="codex"), \
                patch.object(harness, "run_role", return_value=intake) as run_role, \
                patch("builtins.input", side_effect=EOFError), patch("builtins.print"):
            self.assertFalse(harness.run("Build a site", "test-model", "project", self.tracker))
        run_role.assert_called_once()

    def run_reports(self, reports, answer="n", max_reviews=3, role=None):
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness.shutil, "which", return_value="codex"), \
                patch.object(harness, "run_role", side_effect=reports) as run_role, \
                patch("builtins.input", return_value=answer) as input_, patch("builtins.print") as print_:
            result = harness.run("Build a site", "test-model", "project", self.tracker,
                                 role=role, max_reviews=max_reviews)
        return result, run_role.call_args_list, input_, print_

    def test_unfinished_ui_and_developer_handoffs_reach_review_and_repair(self):
        unfinished = {**REPORT, "status": "needs_changes",
                      "checks": [{"kind": "asset", "result": "failed", "evidence": "Missing garden PNG."}],
                      "findings": [{"owner": "ui", "description": "Garden asset is missing."}]}
        result, calls, input_, _ = self.run_reports(
            [REPORT, unfinished, unfinished, unfinished, unfinished, REPORT, REPORT])
        self.assertTrue(result)
        self.assertEqual([entry.args[2] for entry in calls],
                         ["planning", "ui", "developer", "review", "ui", "developer", "review"])
        self.assertIn("Garden asset is missing.", calls[2].args[4])
        self.assertIn('"result": "failed"', calls[3].args[4])
        self.assertIn("Garden asset is missing.", calls[4].args[4])
        input_.assert_not_called()

    def test_blocked_ui_or_developer_still_stops_the_workflow(self):
        blocked = {**REPORT, "status": "blocked", "summary": "Required tool unavailable."}
        for reports in ([REPORT, blocked], [REPORT, REPORT, blocked]):
            with self.subTest(reports=reports):
                result, calls, input_, _ = self.run_reports(reports)
                self.assertFalse(result)
                self.assertEqual(len(calls), len(reports))
                input_.assert_not_called()

    def test_single_unfinished_ui_or_developer_does_not_start_other_roles(self):
        unfinished = {**REPORT, "status": "needs_changes",
                      "findings": [{"owner": "ui", "description": "Missing asset."}]}
        for role in ("ui", "developer"):
            with self.subTest(role=role):
                result, calls, input_, _ = self.run_reports([unfinished], role=role)
                self.assertFalse(result)
                self.assertEqual([entry.args[2] for entry in calls], [role])
                input_.assert_not_called()

    def test_review_routes_component_findings_through_ui_and_developer(self):
        defect = {**REPORT, "status": "needs_changes",
                  "findings": [{"owner": "ui", "description": "Fix the narrow mobile button."}]}
        result, calls, input_, _ = self.run_reports([REPORT, REPORT, REPORT, defect, REPORT, REPORT, REPORT])
        self.assertTrue(result)
        self.assertEqual([entry.args[2] for entry in calls],
                         ["planning", "ui", "developer", "review", "ui", "developer", "review"])
        self.assertEqual(calls[4].args[-1], "ui-2")
        self.assertIn("Fix the narrow mobile button.", calls[4].args[4])
        input_.assert_not_called()

    def test_review_routes_other_bugs_directly_to_developer(self):
        defect = {**REPORT, "status": "needs_changes",
                  "findings": [{"owner": "developer", "description": "Fix the date parser."}]}
        result, calls, input_, _ = self.run_reports([REPORT, REPORT, REPORT, defect, REPORT, REPORT])
        self.assertTrue(result)
        self.assertEqual([entry.args[2] for entry in calls],
                         ["planning", "ui", "developer", "review", "developer", "review"])
        input_.assert_not_called()

    def test_third_failed_review_presents_findings_and_decline_stops(self):
        defect = {**REPORT, "status": "needs_changes",
                  "findings": [{"owner": "developer", "description": "Remaining parser bug."}]}
        result, calls, input_, print_ = self.run_reports(
            [REPORT, REPORT, REPORT, defect, REPORT, defect, REPORT, defect])
        self.assertFalse(result)
        self.assertEqual(calls[-1].args[-1], "review-3")
        self.assertEqual(len(calls), 8)
        input_.assert_called_once()
        self.assertIn("Remaining parser bug.", " ".join(str(entry) for entry in print_.call_args_list))

    def test_explicit_continue_authorizes_another_batch(self):
        defect = {**REPORT, "status": "needs_changes",
                  "findings": [{"owner": "developer", "description": "Fix the parser."}]}
        result, calls, input_, _ = self.run_reports(
            [REPORT, REPORT, REPORT, defect, REPORT, defect, REPORT, defect, REPORT, REPORT], answer="yes")
        self.assertTrue(result)
        self.assertEqual(calls[-1].args[-1], "review-4")
        input_.assert_called_once()

    def test_single_review_does_not_start_write_roles(self):
        defect = {**REPORT, "status": "needs_changes",
                  "findings": [{"owner": "ui", "description": "Fix the button."}]}
        result, calls, input_, _ = self.run_reports([defect], role="review")
        self.assertFalse(result)
        self.assertEqual([entry.args[2] for entry in calls], ["review"])
        input_.assert_not_called()

    def test_missing_rendering_stops_workflow(self):
        unverified = {**REPORT, "checks": [REPORT["checks"][0]]}
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness.shutil, "which", return_value="codex"), \
                patch.object(harness, "run_role", side_effect=[REPORT, REPORT, unverified]) as run_role, \
                patch("builtins.print"):
            self.assertFalse(harness.run("Build a site", "test-model", "project", self.tracker))
        self.assertEqual(run_role.call_count, 3)

    def test_legacy_asset_helper_rejects_paid_generation(self):
        from Codex_Harness.assets import main
        with patch("Simple_Harness.dev_harness.DevHarness.generate_asset") as generate:
            with self.assertRaisesRegex(SystemExit, "PixelLab generation is disabled"):
                main()
        generate.assert_not_called()

    def test_follow_up_sessions_reuse_decisions_and_preserve_existing_project_files(self):
        (self.project / "index.html").write_text("Existing working website", encoding="utf-8")
        intake = {**REPORT, "status": "needs_input", "questions": ["Which palette?"]}
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness.shutil, "which", return_value="codex"), \
                patch.object(harness, "run_role", side_effect=[intake, REPORT, REPORT, REPORT, REPORT]), \
                patch("builtins.input", return_value="Mint and coral"), patch("builtins.print"):
            self.assertTrue(harness.run("Build the original portfolio", "test-model", "project", self.tracker))
        state_paths = list((Path(self.directory.name) / "sessions").glob("*.json"))
        self.assertEqual(len(state_paths), 1)
        initial = json.loads(state_paths[0].read_text(encoding="utf-8"))["initial_brief"]
        self.assertIn("Mint and coral", initial)
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness.shutil, "which", return_value="codex"), \
                patch.object(harness, "run_role", return_value=REPORT) as run_role, patch("builtins.print"):
            self.assertTrue(harness.run("Add a pond beside the garden", "test-model", "project", self.tracker))
        prompt = run_role.call_args_list[0].args[4]
        self.assertIn("Mint and coral", prompt)
        self.assertIn("Add a pond beside the garden", prompt)
        self.assertIn("Build the original portfolio", prompt)
        self.assertNotIn("PixelLab helper:", prompt)
        self.assertNotIn("--transparent", prompt)
        self.assertEqual((self.project / "index.html").read_text(), "Existing working website")
        state = json.loads(state_paths[0].read_text(encoding="utf-8"))
        self.assertEqual(state["initial_brief"], initial)
        self.assertEqual(state["last_brief"], "Add a pond beside the garden")

    def test_session_context_is_separate_for_each_project(self):
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness.shutil, "which", return_value="codex"), \
                patch.object(harness, "run_role", return_value=REPORT) as run_role, patch("builtins.print"):
            self.assertTrue(harness.run("Private detail for project one", "test-model", "project", self.tracker))
            run_role.reset_mock()
            self.assertTrue(harness.run("Build a different website", "test-model", "other", self.tracker))
        self.assertNotIn("Private detail for project one", run_role.call_args_list[0].args[4])
        self.assertEqual(len(list((Path(self.directory.name) / "sessions").glob("*.json"))), 2)

    def test_invalid_session_context_stops_without_overwriting_it(self):
        self.run_reports([REPORT, REPORT, REPORT, REPORT])
        state_path = next((Path(self.directory.name) / "sessions").glob("*.json"))
        invalid = '{"reports": "corrupt"}'
        state_path.write_text(invalid, encoding="utf-8")
        with patch.object(harness, "BASE", Path(self.directory.name)), \
                patch.object(harness, "run_role") as run_role:
            with self.assertRaisesRegex(ValueError, "Invalid saved session context"):
                harness.run("Follow-up request", "test-model", "project", self.tracker)
        run_role.assert_not_called()
        self.assertEqual(state_path.read_text(encoding="utf-8"), invalid)

    def test_main_accepts_task_text_or_a_utf8_prompt_file(self):
        prompt = Path(self.directory.name) / "start prompt.md"
        text = "Build a café site.\nKeep the layout simple.\n"
        prompt.write_text(text, encoding="utf-8-sig")
        modules = {"usage_tracker": SimpleNamespace(UsageTracker=Mock(return_value=self.tracker)),
                   "dotenv": SimpleNamespace(load_dotenv=Mock())}
        for arguments in ([text], ["--prompt", str(prompt)]):
            with self.subTest(arguments=arguments), patch.dict("sys.modules", modules), \
                    patch("sys.argv", ["codex_harness.py", *arguments, "--model", "test-model",
                                       "--project", "project"]), \
                    patch.object(harness, "run", return_value=True) as run:
                self.assertEqual(harness.main(), 0)
                run.assert_called_once_with(text, "test-model", "project", self.tracker, None, 3)

    def test_bad_prompt_arguments_stop_before_tracker_or_run(self):
        prompt = Path(self.directory.name) / "prompt.md"
        prompt.write_text(" \n", encoding="utf-8")
        invalid_utf8 = Path(self.directory.name) / "invalid.md"
        invalid_utf8.write_bytes(b"\xff\xfe")
        modules = {"usage_tracker": SimpleNamespace(UsageTracker=Mock()),
                   "dotenv": SimpleNamespace(load_dotenv=Mock())}
        for arguments in ([], [""], ["--prompt", str(prompt)], ["--prompt", str(invalid_utf8)],
                          ["--prompt", str(prompt.parent / "missing.md")],
                          ["--prompt", str(prompt.parent)], ["task", "--prompt", str(prompt)]):
            with self.subTest(arguments=arguments), patch.dict("sys.modules", modules), \
                    patch("sys.argv", ["codex_harness.py", *arguments, "--model", "test-model"]), \
                    patch.object(harness, "run") as run, patch("sys.stderr"):
                with self.assertRaises(SystemExit) as error:
                    harness.main()
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()
        modules["usage_tracker"].UsageTracker.assert_not_called()

    def test_direct_script_entrypoint_from_harness_directory(self):
        prompt = Path(self.directory.name) / "start prompt.md"
        prompt.write_text("Build a café site.\n", encoding="utf-8")
        script = """
import runpy, sys
from types import SimpleNamespace
tracker = SimpleNamespace(print_summary=lambda: None, save_to_file=lambda: None)
sys.modules['usage_tracker'] = SimpleNamespace(UsageTracker=lambda: tracker)
sys.modules['dotenv'] = SimpleNamespace(load_dotenv=lambda **kwargs: None)
namespace = runpy.run_path('codex_harness.py')
def run(task, model, project, actual_tracker, role, max_reviews):
    from Codex_Harness.browser_checks import local_browser_worker
    assert task == 'Build a caf\\u00e9 site.\\n'
    assert model == 'test-model' and project == 'project' and actual_tracker is tracker
    return True
namespace['main'].__globals__['run'] = run
sys.argv = ['codex_harness.py', '--prompt', sys.argv[1], '--model', 'test-model', '--project', 'project']
assert namespace['main']() == 0
"""
        completed = subprocess.run([sys.executable, "-B", "-c", script,
                                    str(prompt.relative_to(harness.BASE))],
                                   cwd=harness.BASE, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_main_summarizes_and_saves_tracker_after_error(self):
        modules = {"usage_tracker": SimpleNamespace(UsageTracker=Mock(return_value=self.tracker)),
                   "dotenv": SimpleNamespace(load_dotenv=Mock())}
        with patch.dict("sys.modules", modules), \
                patch("sys.argv", ["codex_harness.py", "task", "--model", "test-model"]), \
                patch.object(harness, "run", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                harness.main()
        self.tracker.print_summary.assert_called_once_with()
        self.tracker.save_to_file.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
