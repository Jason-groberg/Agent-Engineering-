"""Run project browser journeys and axe checks at desktop and mobile sizes."""

from argparse import ArgumentParser
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import threading
import time
from uuid import uuid4
from urllib.parse import urljoin, urlsplit


BASE = Path(__file__).resolve().parent
VIEWPORTS = {"desktop": {"width": 1280, "height": 800}, "mobile": {"width": 390, "height": 844}}
VALUE_ACTIONS = {"fill", "expect_text", "expect_url"}
SELECTOR_ACTIONS = {"click", "fill", "expect_visible", "expect_text"}


def request_files(project, token):
    from Codex_Harness.codex_harness import project_path

    project = project_path(project)
    if not re.fullmatch(r"[0-9a-f]{32}", token):
        raise ValueError("Invalid browser request token.")
    output = project / ".harness-verification"
    if not output.resolve().is_relative_to(project):
        raise ValueError("Browser request directory cannot escape the project.")
    output.mkdir(exist_ok=True)
    paths = [output / f"{token}-{name}.json" for name in ("request", "response")]
    if any(path.is_symlink() for path in paths):
        raise ValueError("Browser request files cannot be symlinks.")
    return paths


def request_local_checks(project, url, token):
    request, response = request_files(project, token)
    request_id = uuid4().hex
    request.write_text(json.dumps({"id": request_id, "url": local_url(url)}), encoding="utf-8")
    deadline = time.monotonic() + 190
    while time.monotonic() < deadline:
        try:
            result = json.loads(response.read_text(encoding="utf-8"))
            if result.get("id") == request_id:
                return result["result"]
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(0.1)
    raise TimeoutError("Local wrapper did not finish browser checks within 190 seconds.")


@contextmanager
def local_browser_worker(project, token):
    request, response = request_files(project, token)
    stop = threading.Event()

    def work():
        previous = None
        while not stop.wait(0.1):
            try:
                request_files(project, token)
                job = json.loads(request.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            if (not isinstance(job, dict) or set(job) != {"id", "url"}
                    or not isinstance(job["id"], str) or not re.fullmatch(r"[0-9a-f]{32}", job["id"])
                    or job["id"] == previous):
                continue
            previous = job["id"]
            process = None
            try:
                url = local_url(job["url"])
                print("[browser] Running Playwright and axe on the local PC", flush=True)
                process = subprocess.Popen([sys.executable, "-B", str(BASE / "browser_checks.py"),
                                            "--project", str(project), "--url", url],
                                           cwd=project, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True, encoding="utf-8")
                deadline = time.monotonic() + 180
                while True:
                    if stop.is_set() or time.monotonic() >= deadline:
                        raise TimeoutError("Browser verification stopped or exceeded 180 seconds.")
                    try:
                        stdout, stderr = process.communicate(timeout=0.2)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                if process.returncode not in (0, 1):
                    raise RuntimeError(stderr[-2000:] or "Browser runner failed.")
                result = json.loads(stdout)
            except Exception as error:
                result = {"checks": [{"kind": kind, "result": "failed", "evidence": str(error)}
                                     for kind in ("browser", "accessibility")],
                          "screenshots": [], "errors": [str(error)]}
            finally:
                if process is not None and process.poll() is None:
                    process.kill()
                    process.communicate()
            if not stop.is_set():
                request_files(project, token)
                response.write_text(json.dumps({"id": job["id"], "result": result}), encoding="utf-8")

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=5)


def local_url(url):
    if not isinstance(url, str):
        raise ValueError("Browser URL must be a string.")
    parsed = urlsplit(url)
    if (parsed.scheme not in ("http", "https")
            or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed.username is not None or parsed.password is not None):
        raise ValueError("Browser checks require a local HTTP(S) URL without credentials.")
    parsed.port  # Validate malformed port numbers before starting the browser.
    return url


def validate_spec(spec):
    if not isinstance(spec, dict) or set(spec) != {"cases"} or not isinstance(spec["cases"], list) or not spec["cases"]:
        raise ValueError("browser_checks.json must contain a nonempty cases array.")
    names = set()
    for case in spec["cases"]:
        if (not isinstance(case, dict) or set(case) != {"name", "path", "steps"}
                or not isinstance(case["name"], str) or not re.fullmatch(r"[A-Za-z0-9_-]+", case["name"])
                or case["name"] in names or not isinstance(case["path"], str)
                or not isinstance(case["steps"], list) or not case["steps"]):
            raise ValueError("Each case needs a unique safe name, a path, and steps.")
        names.add(case["name"])
        for step in case["steps"]:
            if not isinstance(step, dict) or not isinstance(step.get("action"), str):
                raise ValueError("Invalid browser step.")
            action = step["action"]
            if action not in SELECTOR_ACTIONS | VALUE_ACTIONS:
                raise ValueError(f"Unsupported browser action: {action}")
            fields = {"action"} | ({"selector"} if action in SELECTOR_ACTIONS else set())
            fields |= {"value"} if action in VALUE_ACTIONS else set()
            if set(step) != fields or any(not isinstance(step[field], str) or not step[field].strip() for field in fields):
                raise ValueError("Browser step fields must be nonempty strings.")
        actions = {step["action"] for step in case["steps"]}
        if not actions & {"click", "fill"} or not actions & {"expect_visible", "expect_text", "expect_url"}:
            raise ValueError("Each browser case needs an interaction and an expected outcome.")
    return spec


def verify(project, url):
    sys.path.insert(0, str(BASE.parent))
    from Codex_Harness.codex_harness import project_path

    project = project_path(project)
    url = local_url(url)
    spec_path = (project / "browser_checks.json").resolve()
    if not spec_path.is_relative_to(project):
        raise ValueError("Browser specification cannot resolve outside the project.")
    spec = validate_spec(json.loads(spec_path.read_text(encoding="utf-8")))
    targets = {case["name"]: local_url(urljoin(url, case["path"])) for case in spec["cases"]}
    output = project / ".harness-verification"
    if not output.resolve().is_relative_to(project):
        raise ValueError("Verification output cannot resolve outside the project.")
    output.mkdir(parents=True, exist_ok=True)
    result = {"url": url, "checks": [], "screenshots": [], "errors": [], "audits": []}
    browser_passed = True
    accessibility_passed = True
    sys.path.insert(0, str(BASE / ".browser_tools"))
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BASE / ".browsers")
    try:
        from playwright.sync_api import expect, sync_playwright
        axe_source = (BASE / ".browser_tools" / "axe-core" / "axe.min.js").read_text(encoding="utf-8")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for case in spec["cases"]:
                    target = targets[case["name"]]
                    for viewport, dimensions in VIEWPORTS.items():
                        label = f"{case['name']}-{viewport}"
                        errors = []
                        with browser.new_context(viewport=dimensions) as context:
                            page = context.new_page()
                            page.on("pageerror", lambda error: errors.append(str(error)))
                            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                            page.on("response", lambda response: errors.append(f"{response.status}: {response.url}")
                                    if response.status >= 400 and response.request.resource_type in {"image", "stylesheet", "script", "font"} else None)

                            def navigation(route):
                                if route.request.is_navigation_request():
                                    try:
                                        local_url(route.request.url)
                                    except ValueError:
                                        errors.append("Navigation outside the local site was blocked.")
                                        route.abort()
                                        return
                                route.continue_()

                            context.route("**/*", navigation)
                            try:
                                response = page.goto(target, wait_until="load")
                                if response is None or response.status >= 400:
                                    raise RuntimeError("The local page did not load successfully.")
                                expect(page.locator("body")).to_be_visible()
                                for state in ("initial", "after"):
                                    if state == "after":
                                        for step in case["steps"]:
                                            action = step["action"]
                                            if action == "expect_url":
                                                expect(page).to_have_url(local_url(urljoin(target, step["value"])))
                                            else:
                                                locator = page.locator(step["selector"])
                                                if action == "click":
                                                    locator.click()
                                                elif action == "fill":
                                                    locator.fill(step["value"])
                                                elif action == "expect_visible":
                                                    expect(locator).to_be_visible()
                                                elif action == "expect_text":
                                                    expect(locator).to_contain_text(step["value"])
                                    image_path = output / f"{label}-{state}.png"
                                    if image_path.is_symlink():
                                        raise ValueError("Screenshot output cannot be a symlink.")
                                    page.screenshot(path=str(image_path), full_page=True)
                                    result["screenshots"].append(str(image_path.relative_to(project)))
                                    page.evaluate(axe_source)
                                    audit = page.evaluate("""async () => await axe.run(document, {
                                        runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']}
                                    })""")
                                    result["audits"].append({"case": label, "state": state, "result": audit})
                                    if audit["violations"]:
                                        accessibility_passed = False
                            except Exception as error:
                                browser_passed = accessibility_passed = False
                                errors.append(str(error))
                        if errors:
                            browser_passed = False
                            result["errors"].extend(f"{label}: {error}" for error in errors)
            finally:
                browser.close()
    except Exception as error:
        browser_passed = accessibility_passed = False
        result["errors"].append(str(error))
    evidence = ".harness-verification/browser-report.json"
    result["checks"] = [
        {"kind": "browser", "result": "passed" if browser_passed else "failed", "evidence": evidence},
        {"kind": "accessibility", "result": "passed" if accessibility_passed else "failed", "evidence": evidence},
    ]
    report_path = output / "browser-report.json"
    if report_path.is_symlink():
        raise ValueError("Browser report output cannot be a symlink.")
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    sys.path.insert(0, str(BASE.parent))
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project directory inside Codex_Harness.")
    parser.add_argument("--url", required=True, help="URL of the running local website.")
    parser.add_argument("--request-token", help="Ask the running local harness to execute browser checks.")
    args = parser.parse_args()
    result = (request_local_checks(Path(args.project), args.url, args.request_token)
              if args.request_token else verify(Path(args.project), args.url))
    print(json.dumps({"checks": result["checks"], "screenshots": result["screenshots"], "errors": result["errors"]}, indent=2))
    return 0 if all(check["result"] == "passed" for check in result["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
