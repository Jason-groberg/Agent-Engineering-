"""Install the requested browser tools privately inside Codex_Harness."""

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from urllib.request import urlopen


BASE = Path(__file__).resolve().parent
AXE_VERSION = "4.14.0"


def install_axe():
    with urlopen(f"https://registry.npmjs.org/axe-core/{AXE_VERSION}", timeout=60) as response:
        metadata = json.load(response)
    expected_url = f"https://registry.npmjs.org/axe-core/-/axe-core-{AXE_VERSION}.tgz"
    if metadata["dist"]["tarball"] != expected_url:
        raise ValueError("Unexpected axe package download URL.")
    with urlopen(expected_url, timeout=60) as response:
        archive = response.read()
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(archive).digest()).decode()
    if integrity != metadata["dist"]["integrity"]:
        raise ValueError("axe package integrity check failed.")
    vendor = BASE / ".browser_tools" / "axe-core"
    vendor.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        # Read only these members; never extract archive-supplied paths onto the filesystem.
        for name in ("axe.min.js", "LICENSE"):
            with package.extractfile(f"package/{name}") as source:
                (vendor / name).write_bytes(source.read())
    (vendor / "version.txt").write_text(AXE_VERSION, encoding="utf-8")


def main():
    tools = BASE / ".browser_tools"
    subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                    "--no-cache-dir", "--upgrade", "--target", str(tools),
                    "-r", str(BASE / "requirements-browser.txt")], check=True)
    install_axe()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(tools) + os.pathsep + environment.get("PYTHONPATH", "")
    environment["PLAYWRIGHT_BROWSERS_PATH"] = str(BASE / ".browsers")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                   env=environment, check=True)
    print("Playwright, Chromium, and axe-core are ready inside Codex_Harness.")


if __name__ == "__main__":
    main()
