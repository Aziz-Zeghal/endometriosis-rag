"""Polite HTTP connector: robots.txt, per-host delay and retries (the disk cache is in the base)."""

import logging
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from endorag_ingestion.core import BaseConnector, ManifestEntry, Settings
from endorag_ingestion.core.settings import RAW_DIR

logger = logging.getLogger(__name__)

TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class FetchError(Exception):
    """The document cannot be fetched (robots.txt, bad content, HTTP error)."""


class HttpConnector(BaseConnector):
    """Downloads a manifest entry over HTTP (`fetch_url`, else `url`).

    Cached files are returned by `BaseConnector.download()` without any network access;
    `refresh=True` forces a new download.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        raw_dir: Path = RAW_DIR,
        client: httpx.Client | None = None,
        refresh: bool = False,
        default_delay_s: float = 2.0,
        retries: int = 3,
        timeout_s: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(raw_dir, refresh)
        self.user_agent = (settings or Settings()).user_agent
        self.default_delay_s = default_delay_s
        self.retries = retries
        self.sleep = sleep
        self.clock = clock
        self._client = client
        self._timeout_s = timeout_s
        self._robots: dict[str, RobotFileParser] = {}
        self._last_request: dict[str, float] = {}

    @property
    def client(self) -> httpx.Client:
        # Created lazily so cache hits never open a connection pool.
        if self._client is None:
            self._client = httpx.Client(follow_redirects=True, timeout=self._timeout_s)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _download_to(self, entry: ManifestEntry, path: Path) -> dict:
        if entry.format not in ("html", "pdf", "xml"):
            raise FetchError(f"{entry.id}: format {entry.format!r} is not served over HTTP")
        url = str(entry.fetch_url or entry.url)
        robots = self._robots_for(url)
        if not robots.can_fetch(self.user_agent, url):
            raise FetchError(f"{entry.id}: disallowed by robots.txt ({url})")
        # robots.txt Crawl-delay is a floor: a manifest entry may only slow down, never speed up.
        delay = entry.crawl_delay_s if entry.crawl_delay_s is not None else self.default_delay_s
        delay = max(delay, float(robots.crawl_delay(self.user_agent) or 0))

        response = self._get(url, delay)
        if response.is_error:
            raise FetchError(f"{entry.id}: HTTP {response.status_code} for {url}")
        final_url = str(response.url)
        # Redirects are followed by httpx; never keep a page the final host's robots.txt disallows.
        if final_url != url and not self._robots_for(final_url).can_fetch(
            self.user_agent, final_url
        ):
            raise FetchError(f"{entry.id}: redirect target disallowed by robots.txt ({final_url})")
        content_type = response.headers.get("content-type")
        self._check_content(entry, response.content, content_type)

        path.write_bytes(response.content)
        logger.info("Fetched %s -> %s", url, path.name)
        return {
            "url": url,
            "final_url": final_url,
            "status": response.status_code,
            "content_type": content_type,
        }

    def _robots_for(self, url: str) -> RobotFileParser:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            robots_url = f"{host}/robots.txt"
            parser = RobotFileParser(robots_url)
            response = self._get(robots_url, self.default_delay_s)
            # Same semantics as RobotFileParser.read(): 401/403 = all disallowed,
            # other 4xx = no robots.txt, so everything is allowed.
            if response.status_code in (401, 403):
                parser.disallow_all = True
            elif response.is_success:
                parser.parse(response.text.splitlines())
            elif response.is_server_error:
                # Cached as "disallow all" (stdlib semantics) so the host is not retried per entry.
                parser.disallow_all = True
                logger.warning(
                    "robots.txt unavailable for %s (HTTP %s)", host, response.status_code
                )
            else:
                parser.allow_all = True
            self._robots[host] = parser
        return self._robots[host]

    def _get(self, url: str, delay_s: float) -> httpx.Response:
        """GET with the per-host delay and retries with exponential backoff on transient errors."""
        host = urlsplit(url).netloc
        for attempt in range(self.retries + 1):
            last = self._last_request.get(host)
            if last is not None:
                wait = last + delay_s - self.clock()
                if wait > 0:
                    self.sleep(wait)
            self._last_request[host] = self.clock()
            try:
                response = self.client.get(url, headers={"User-Agent": self.user_agent})
            except httpx.TransportError:
                if attempt == self.retries:
                    raise
            else:
                if response.status_code not in TRANSIENT_STATUSES or attempt == self.retries:
                    return response
                retry_after = response.headers.get("retry-after", "")
                if retry_after.isdigit():
                    self.sleep(max(2**attempt, int(retry_after)))
                    continue
            self.sleep(2**attempt)
        raise AssertionError("unreachable")

    @staticmethod
    def _check_content(entry: ManifestEntry, body: bytes, content_type: str | None) -> None:
        # PDF readers accept the header anywhere in the first 1024 bytes.
        is_pdf = b"%PDF" in body[:1024]
        if entry.format == "pdf" and not is_pdf:
            raise FetchError(f"{entry.id}: expected a PDF, got {content_type or 'unknown content'}")
        if entry.format == "xml" and (is_pdf or b"<" not in body[:200]):
            raise FetchError(f"{entry.id}: expected XML, got {content_type or 'unknown content'}")
        if entry.format == "html" and (
            is_pdf or (content_type and "html" not in content_type.lower())
        ):
            raise FetchError(f"{entry.id}: expected HTML, got {content_type or 'a PDF'}")
