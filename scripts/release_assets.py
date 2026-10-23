"""Create copy-and-run setup files pinned to the image just published."""

import os
import re
from pathlib import Path


def setup_assets(version, image):
    result = {}
    for name in ("docker-compose.yml", "docker-compose.dreeve.yml"):
        content = Path(name).read_text(encoding="utf-8")
        content, count = re.subn(r"ghcr\.io/[\w./-]+:\$\{CONNECTOR_VERSION:-[^}]+\}",
                                 lambda _: f"{image}:${{CONNECTOR_VERSION:-{version}}}", content)
        if count != 1:
            raise ValueError(f"Expected exactly one release image in {name}")
        result[name] = content
    env = Path(".env.example").read_text(encoding="utf-8")
    env, count = re.subn(r"(?m)^CONNECTOR_VERSION=.*$", f"CONNECTOR_VERSION={version}", env)
    if count != 1:
        raise ValueError("Expected CONNECTOR_VERSION in .env.example")
    result["env.example"] = env
    return result


def main():
    target = Path("release-assets")
    target.mkdir(exist_ok=True)
    for name, content in setup_assets(os.environ["VERSION"], os.environ["IMAGE"]).items():
        (target / name).write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
