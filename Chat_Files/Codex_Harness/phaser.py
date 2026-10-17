"""Cache a pinned Phaser runtime, or copy it into a harness game project."""

from argparse import ArgumentParser
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
from urllib.request import urlopen


BASE = Path(__file__).resolve().parent
VERSION = "4.2.1"
CACHE = BASE / ".game_tools" / f"phaser-{VERSION}"
FILES = {"phaser.min.js": "package/dist/phaser.min.js", "LICENSE.txt": "package/LICENSE.md"}


def provision():
    with urlopen(f"https://registry.npmjs.org/phaser/{VERSION}", timeout=60) as response:
        metadata = json.load(response)
    expected_url = f"https://registry.npmjs.org/phaser/-/phaser-{VERSION}.tgz"
    if metadata["version"] != VERSION or metadata["dist"]["tarball"] != expected_url:
        raise ValueError("Unexpected Phaser package version or download URL.")
    with urlopen(expected_url, timeout=60) as response:
        archive = response.read()
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(archive).digest()).decode()
    if integrity != metadata["dist"]["integrity"]:
        raise ValueError("Phaser package integrity check failed.")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        with package.extractfile("package/package.json") as source:
            if json.load(source)["version"] != VERSION:
                raise ValueError("Phaser archive has an unexpected version.")
        contents = {}
        for name, member in FILES.items():
            with package.extractfile(member) as source:
                contents[name] = source.read()
            if not contents[name]:
                raise ValueError("Phaser archive contains an empty runtime or license.")
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, content in contents.items():
        (CACHE / name).write_bytes(content)
    return CACHE


def install(project):
    sys.path.insert(0, str(BASE.parent))
    from Codex_Harness.codex_harness import project_path

    project = project_path(project)
    destination = project / "vendor" / f"phaser-{VERSION}"
    if not destination.resolve().is_relative_to(project):
        raise ValueError("Phaser installation cannot resolve outside the project.")
    if any(not (CACHE / name).is_file() for name in FILES):
        raise FileNotFoundError("Phaser cache missing. Run python phaser.py from Codex_Harness first.")
    contents = {name: (CACHE / name).read_bytes() for name in FILES}
    for name, content in contents.items():
        target = destination / name
        if target.is_symlink():
            raise ValueError("Phaser destination cannot be a symlink.")
        if target.exists() and target.read_bytes() != content:
            raise FileExistsError(f"Refusing to overwrite a different Phaser file: {target}")
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in contents.items():
        target = destination / name
        if not target.exists():
            with target.open("xb") as output:
                output.write(content)
    return {"version": VERSION, "script": str((destination / "phaser.min.js").relative_to(project)),
            "license": str((destination / "LICENSE.txt").relative_to(project))}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Copy cached Phaser into this project inside Codex_Harness.")
    args = parser.parse_args()
    if args.project:
        print(json.dumps(install(args.project)))
    else:
        print(f"Phaser {VERSION} cached with its MIT license at {provision()}")


if __name__ == "__main__":
    main()
