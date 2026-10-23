import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Config:
    repository: str
    token_file: Path
    watch_dir: Path = Path("/watch")
    state_dir: Path = Path("/state")
    branch: str | None = None
    interval: int = 300
    since: datetime | None = None
    github_api_url: str = "https://api.github.com"

    @classmethod
    def from_env(cls):
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("GITHUB_REPOSITORY must be owner/repository")
        token_file = os.environ.get("GITHUB_TOKEN_FILE", "")
        if not token_file:
            raise ValueError("GITHUB_TOKEN_FILE is required")
        interval = int(os.environ.get("SYNC_INTERVAL_SECONDS", "300"))
        if interval < 30:
            raise ValueError("SYNC_INTERVAL_SECONDS must be at least 30")
        raw_since = os.environ.get("EXPORT_SINCE", "")
        api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
        parsed_url = urlsplit(api_url)
        if (parsed_url.scheme not in ("http", "https") or not parsed_url.hostname
                or parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment):
            raise ValueError("GITHUB_API_URL must be an HTTP(S) base URL without credentials or query")
        since = None
        if raw_since:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_since):
                raise ValueError("EXPORT_SINCE must be YYYY-MM-DD")
            since = datetime.strptime(raw_since, "%Y-%m-%d").replace(tzinfo=UTC)
        return cls(repository.lower(), Path(token_file),
                   Path(os.environ.get("WATCH_DIR", "/watch")),
                   Path(os.environ.get("STATE_DIR", "/state")),
                   os.environ.get("GITHUB_BRANCH") or None, interval, since, api_url)

    def token(self):
        try:
            token = self.token_file.read_text(encoding="utf-8").strip()
        except OSError:
            raise ValueError("Cannot read GITHUB_TOKEN_FILE") from None
        if not token or any(c.isspace() for c in token):
            raise ValueError("GITHUB_TOKEN_FILE must contain one nonempty token")
        return token
