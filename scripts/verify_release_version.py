"""Verify release versions, wheel contents, and Docker Hub visibility."""

from __future__ import annotations

import argparse
import ast
from contextlib import closing
from email.parser import BytesParser
import http.client
import json
import os
from pathlib import Path
import re
import tomllib
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
_VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
_REPOSITORY = "/v2/namespaces/koalalive/repositories/neurodaily"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _toml(path):
    return tomllib.loads(path.read_text(encoding="utf-8"))


def check_versions(root: Path, tag: str | None) -> str:
    version = _toml(root / "pyproject.toml")["project"]["version"]
    if not _VERSION.fullmatch(version):
        raise ValueError(f"Invalid package version {version}")
    if tag is not None and tag not in (f"v{version}", f"cli-v{version}"):
        raise ValueError(f"Release tag does not match package version {version}")

    module = ast.parse((root / "neurodaily/__init__.py").read_text(encoding="utf-8"))
    runtime = next((ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                    and any(isinstance(item, ast.Name) and item.id == "__version__" for item in node.targets)), None)
    desktop = root / "desktop/tauri"
    package = _toml(desktop / "src-tauri/Cargo.toml")["package"]
    cargo_lock = _toml(desktop / "src-tauri/Cargo.lock")["package"]
    desktop_lock = _json(desktop / "package-lock.json")
    formula = (root / "Formula/neurodaily.rb").read_text(encoding="utf-8")
    versions = {
        "Python runtime": runtime,
        "Cargo.toml": package["version"],
        "Cargo.lock": next((item["version"] for item in cargo_lock if item["name"] == package["name"]), None),
        "tauri.conf.json": _json(desktop / "src-tauri/tauri.conf.json")["version"],
        "package.json": _json(desktop / "package.json")["version"],
        "package-lock.json": desktop_lock["version"],
        "package-lock.json root package": desktop_lock["packages"][""]["version"],
        "Homebrew formula": next(iter(re.findall(r'^  version "([^"]+)"$', formula, re.M)), None),
        "Homebrew source tag": next(iter(re.findall(r'\btag: "(?:cli-)?v([^"\n]+)"', formula)), None),
    }
    for component, declared in versions.items():
        if declared != version:
            raise ValueError(f"{component} declares {declared!r}, expected {version}")
    return version


def verify_wheel(root: Path, directory: Path, version: str) -> Path:
    wheels = list(directory.rglob("*.whl"))
    expected = f"neurodaily-{version}-py3-none-any.whl"
    if len(wheels) != 1 or wheels[0].name != expected:
        raise ValueError(f"Expected exactly one CLI wheel named {expected}")
    project = _toml(root / "pyproject.toml")
    package = root / "neurodaily"
    files = set(package.rglob("*.py"))
    for pattern in project["tool"]["setuptools"]["package-data"]["neurodaily"]:
        files.update(package.glob(pattern))
    expected_files = {file.relative_to(root).as_posix(): file for file in files if file.is_file()}
    info = f"neurodaily-{version}.dist-info/"
    with ZipFile(wheels[0]) as wheel:
        entries = wheel.namelist()
        if len(entries) != len(set(entries)) or wheel.testzip():
            raise ValueError("The CLI wheel contains duplicate or damaged files")
        metadata = BytesParser().parsebytes(wheel.read(info + "METADATA"))
        if metadata["Name"] != "neurodaily" or metadata["Version"] != version:
            raise ValueError("The wheel metadata does not match the release version")
        console = wheel.read(info + "entry_points.txt").decode()
        if "neurodaily = neurodaily.cli:main" not in console.splitlines():
            raise ValueError("The wheel does not install the NeuroDaily CLI")
        wheel_sources = {name for name in entries if not name.startswith(info)}
        if wheel_sources != expected_files.keys():
            raise ValueError("The CLI wheel file list does not match the release checkout")
        for name, source in expected_files.items():
            if wheel.read(name) != source.read_bytes():
                raise ValueError(f"Wheel source differs from the release checkout: {name}")
    return wheels[0]


def should_publish(releases, tag: str) -> bool:
    version = tag.removeprefix("v")
    if not _VERSION.fullmatch(version):
        raise ValueError("Expected a stable version tag")
    published = []
    for release in releases:
        if release["draft"] or release["prerelease"]:
            continue
        other = release["tag_name"].removeprefix("v")
        if _VERSION.fullmatch(other):
            published.append(tuple(map(int, other.split("."))))
    target = tuple(map(int, version.split(".")))
    if target in published:
        return False
    if any(previous > target for previous in published):
        raise ValueError("A newer release is already published. Refusing to move latest backwards.")
    return True


def _hub_request(method, path, body=None, token=None, allow_missing=False):
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with closing(http.client.HTTPSConnection("hub.docker.com", timeout=15)) as connection:
        connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        response = connection.getresponse()
        if response.status == 404 and allow_missing:
            return None
        if response.status != 200:
            raise ValueError(f"Docker Hub could not verify {path} (HTTP {response.status})")
        return json.loads(response.read(256 * 1024))


def verify_docker_destination(tag: str | None, *, source_private: bool) -> bool | None:
    secret = os.environ.get("DOCKERHUB_TOKEN")
    username = os.environ.get("DOCKERHUB_USERNAME", "koalalive")
    if not secret or not username:
        raise ValueError("A Docker Hub token and username are required to verify the repository")
    result = _hub_request("POST", "/v2/auth/token", {"identifier": username, "secret": secret})
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise ValueError("Docker Hub did not return a bearer token")
    repository = _hub_request("GET", _REPOSITORY, token=token)
    visibility = repository.get("is_private")
    if repository.get("namespace") != "koalalive" or repository.get("name") != "neurodaily" \
            or type(visibility) is not bool:
        raise ValueError("Could not verify Docker Hub repository visibility. Publication refused.")
    if visibility is False and source_private is not False:
        raise ValueError("The source repository is private and Docker Hub is public. Publication refused.")
    if tag is None:
        return None
    if tag != "latest" and not _VERSION.fullmatch(tag):
        raise ValueError("Invalid Docker image version")
    tagged = _hub_request("GET", f"{_REPOSITORY}/tags/{tag}", token=token, allow_missing=True)
    if tagged is None:
        return False
    if tagged.get("name") != tag:
        raise ValueError("Docker Hub returned an unexpected image tag")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    package = commands.add_parser("package")
    package.add_argument("--tag")
    package.add_argument("--wheels", type=Path)
    state = commands.add_parser("release-state")
    state.add_argument("tag")
    state.add_argument("releases", type=Path)
    docker = commands.add_parser("docker-destination")
    docker.add_argument("--source-private", choices=("true", "false"), required=True)
    docker.add_argument("--image-tag")
    args = parser.parse_args()
    try:
        if args.command == "package":
            version = check_versions(ROOT, args.tag)
            if args.wheels:
                verify_wheel(ROOT, args.wheels, version)
            print(version)
        elif args.command == "release-state":
            releases = [release for page in _json(args.releases) for release in page]
            print(str(should_publish(releases, args.tag)).lower())
        else:
            exists = verify_docker_destination(args.image_tag, source_private=args.source_private == "true")
            if exists is not None:
                print(str(exists).lower())
    except (AttributeError, http.client.HTTPException, KeyError, OSError, TypeError, ValueError) as error:
        # Credentials exchanged with Docker Hub stay in memory and out of diagnostics.
        message = str(error) if type(error) is ValueError else "Could not verify release metadata"
        parser.exit(1, message + "\n")


if __name__ == "__main__":
    main()
