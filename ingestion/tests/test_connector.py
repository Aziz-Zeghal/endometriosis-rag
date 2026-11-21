"""HttpConnector tests with httpx.MockTransport: no real network access."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest
from endorag_ingestion.connectors import FetchError, HttpConnector
from endorag_ingestion.settings import Settings
from fakes import make_entry

FIXTURES = Path(__file__).parent / "fixtures" / "connector"
HTML = (FIXTURES / "page.html").read_bytes()
PDF = (FIXTURES / "doc.pdf").read_bytes()
ROBOTS = (FIXTURES / "robots.txt").read_text()


class FakeClock:
    """Monotonic clock that only advances when the connector sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class Server:
    """Routes requests to canned responses and records every request."""

    def __init__(self, routes: dict[str, httpx.Response | list[httpx.Response]]) -> None:
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = self.routes.get(request.url.path)
        if route is None:
            return httpx.Response(404)
        return route.pop(0) if isinstance(route, list) else route

    def paths(self) -> list[str]:
        return [r.url.path for r in self.requests]


def html_response(body: bytes = HTML) -> httpx.Response:
    return httpx.Response(200, content=body, headers={"content-type": "text/html; charset=utf-8"})


def pdf_response(body: bytes = PDF) -> httpx.Response:
    return httpx.Response(200, content=body, headers={"content-type": "application/pdf"})


def make_connector(tmp_path: Path, server: Server, clock: FakeClock | None = None, **kw):
    clock = clock or FakeClock()
    client = httpx.Client(transport=httpx.MockTransport(server), follow_redirects=True)
    return HttpConnector(
        Settings(_env_file=None),
        raw_dir=tmp_path,
        client=client,
        sleep=clock.sleep,
        clock=clock,
        **kw,
    )


def test_fetch_writes_raw_file_and_meta(tmp_path):
    server = Server({"/robots.txt": httpx.Response(200, text=ROBOTS), "/doc-a": html_response()})
    raw = make_connector(tmp_path, server).fetch(make_entry("doc-a"))

    assert raw.path == tmp_path / "doc-a.html"
    assert raw.path.read_bytes() == HTML
    assert raw.content_type == "text/html; charset=utf-8"
    assert raw.retrieved == date.today()
    meta = json.loads((tmp_path / "doc-a.meta.json").read_text())
    assert meta["url"] == meta["final_url"] == "https://example.org/doc-a"
    assert meta["retrieved"] == date.today().isoformat()
    assert len(meta["sha256"]) == 64
    assert server.requests[-1].headers["user-agent"] == Settings(_env_file=None).user_agent


def test_cache_hit_makes_no_network_call(tmp_path):
    (tmp_path / "doc-a.html").write_bytes(HTML)
    (tmp_path / "doc-a.meta.json").write_text(
        json.dumps({"retrieved": "2026-03-01", "content_type": "text/html"})
    )

    server = Server({})
    raw = make_connector(tmp_path, server).fetch(make_entry("doc-a"))

    assert server.requests == []
    assert raw.retrieved == date(2026, 3, 1)
    assert raw.content_type == "text/html"


def test_second_run_is_offline_and_refresh_refetches(tmp_path):
    server = Server({"/robots.txt": httpx.Response(200, text=ROBOTS), "/doc-a": html_response()})
    make_connector(tmp_path, server).fetch(make_entry("doc-a"))
    n = len(server.requests)

    make_connector(tmp_path, server).fetch(make_entry("doc-a"))
    assert len(server.requests) == n

    server.routes["/doc-a"] = html_response(b"<html><p>Mise a jour</p></html>")
    raw = make_connector(tmp_path, server, refresh=True).fetch(make_entry("doc-a"))
    assert raw.path.read_bytes() == b"<html><p>Mise a jour</p></html>"


def test_robots_disallow_raises_without_fetching(tmp_path):
    server = Server({"/robots.txt": httpx.Response(200, text=ROBOTS)})
    entry = make_entry("doc-a", url="https://example.org/prive/page")

    with pytest.raises(FetchError, match=r"robots\.txt"):
        make_connector(tmp_path, server).fetch(entry)
    assert server.paths() == ["/robots.txt"]
    assert not list(tmp_path.iterdir())


def test_robots_is_fetched_once_per_host(tmp_path):
    server = Server(
        {
            "/robots.txt": httpx.Response(200, text=ROBOTS),
            "/doc-a": html_response(),
            "/doc-b": html_response(),
        }
    )
    connector = make_connector(tmp_path, server)
    connector.fetch(make_entry("doc-a"))
    connector.fetch(make_entry("doc-b"))
    assert server.paths().count("/robots.txt") == 1


def test_crawl_delay_is_honoured_between_requests_to_a_host(tmp_path):
    server = Server(
        {
            "/robots.txt": httpx.Response(200, text=ROBOTS),
            "/doc-a": html_response(),
            "/doc-b": html_response(),
        }
    )
    clock = FakeClock()
    connector = make_connector(tmp_path, server, clock)
    connector.fetch(make_entry("doc-a", crawl_delay_s=10))  # robots.txt then doc-a
    connector.fetch(make_entry("doc-b"))  # default delay

    assert clock.sleeps == [10, 2]


def test_transient_errors_are_retried_with_backoff(tmp_path):
    server = Server(
        {
            "/robots.txt": httpx.Response(404),
            "/doc-a": [httpx.Response(503), httpx.Response(503), html_response()],
        }
    )
    clock = FakeClock()
    raw = make_connector(tmp_path, server, clock, default_delay_s=0).fetch(make_entry("doc-a"))

    assert raw.path.exists()
    assert server.paths().count("/doc-a") == 3
    assert clock.sleeps == [1, 2]


def test_http_error_raises_and_caches_nothing(tmp_path):
    server = Server({"/robots.txt": httpx.Response(404), "/doc-a": httpx.Response(410)})
    with pytest.raises(FetchError, match="HTTP 410"):
        make_connector(tmp_path, server).fetch(make_entry("doc-a"))
    assert not list(tmp_path.iterdir())


def test_pdf_entry_is_saved_as_pdf(tmp_path):
    server = Server({"/robots.txt": httpx.Response(404), "/guide": pdf_response()})
    entry = make_entry("guide", url="https://example.org/guide", format="pdf")
    raw = make_connector(tmp_path, server).fetch(entry)

    assert raw.path == tmp_path / "guide.pdf"
    assert raw.content_type == "application/pdf"


def test_html_error_page_served_for_a_pdf_is_rejected(tmp_path):
    server = Server({"/robots.txt": httpx.Response(404), "/guide": html_response()})
    entry = make_entry("guide", url="https://example.org/guide", format="pdf")

    with pytest.raises(FetchError, match="expected a PDF"):
        make_connector(tmp_path, server).fetch(entry)
    assert not list(tmp_path.iterdir())


def test_robots_crawl_delay_is_a_floor_for_entry_delay(tmp_path):
    server = Server(
        {
            "/robots.txt": httpx.Response(200, text="User-agent: *\nCrawl-delay: 10\n"),
            "/doc-a": html_response(),
            "/doc-b": html_response(),
        }
    )
    clock = FakeClock()
    connector = make_connector(tmp_path, server, clock)
    connector.fetch(make_entry("doc-a", crawl_delay_s=1))
    connector.fetch(make_entry("doc-b", crawl_delay_s=1))

    assert clock.sleeps == [10, 10]


def test_redirect_to_host_disallowed_by_robots_is_rejected(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "other.test":
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
            return html_response()
        if request.url.path == "/doc-a":
            return httpx.Response(302, headers={"location": "https://other.test/prive/x"})
        return httpx.Response(404)

    with pytest.raises(FetchError, match=r"redirect target disallowed"):
        make_connector(tmp_path, handler).fetch(make_entry("doc-a"))
    assert not list(tmp_path.iterdir())


def test_robots_server_error_is_cached_per_host(tmp_path):
    server = Server({"/robots.txt": httpx.Response(503)})
    connector = make_connector(tmp_path, server, retries=0)
    for doc_id in ("doc-a", "doc-b"):
        with pytest.raises(FetchError, match=r"robots\.txt"):
            connector.fetch(make_entry(doc_id))
    assert server.paths() == ["/robots.txt"]


def test_content_type_is_case_insensitive(tmp_path):
    page = httpx.Response(200, content=HTML, headers={"content-type": "Text/HTML"})
    server = Server({"/robots.txt": httpx.Response(404), "/doc-a": page})
    assert make_connector(tmp_path, server).fetch(make_entry("doc-a")).path.exists()


def test_pdf_with_leading_bytes_is_accepted(tmp_path):
    server = Server({"/robots.txt": httpx.Response(404), "/guide": pdf_response(b"\r\n" + PDF)})
    entry = make_entry("guide", url="https://example.org/guide", format="pdf")
    assert make_connector(tmp_path, server).fetch(entry).path.exists()


def test_retry_after_is_honoured_on_429(tmp_path):
    server = Server(
        {
            "/robots.txt": httpx.Response(404),
            "/doc-a": [httpx.Response(429, headers={"retry-after": "60"}), html_response()],
        }
    )
    clock = FakeClock()
    make_connector(tmp_path, server, clock, default_delay_s=0).fetch(make_entry("doc-a"))
    assert clock.sleeps == [60]


def test_meta_records_http_status(tmp_path):
    server = Server({"/robots.txt": httpx.Response(404), "/doc-a": html_response()})
    make_connector(tmp_path, server).fetch(make_entry("doc-a"))
    assert json.loads((tmp_path / "doc-a.meta.json").read_text())["status"] == 200


def test_xml_entry_is_downloaded_from_fetch_url(tmp_path):
    xml = b'<?xml version="1.0"?><article><front/><body><p>Texte</p></body></article>'
    server = Server(
        {
            "/robots.txt": httpx.Response(200, text=ROBOTS),
            "/api/full.xml": httpx.Response(
                200, content=xml, headers={"content-type": "application/xml"}
            ),
        }
    )
    entry = make_entry("doc-x", format="xml", fetch_url="https://example.org/api/full.xml")
    raw = make_connector(tmp_path, server).fetch(entry)

    assert raw.path == tmp_path / "doc-x.xml"
    assert "/doc-x" not in server.paths()
    meta = json.loads((tmp_path / "doc-x.meta.json").read_text())
    assert meta["url"] == "https://example.org/api/full.xml"


def test_xml_entry_rejects_a_pdf(tmp_path):
    server = Server({"/robots.txt": httpx.Response(200, text=ROBOTS), "/doc-x": pdf_response()})
    with pytest.raises(FetchError, match="expected XML"):
        make_connector(tmp_path, server).fetch(make_entry("doc-x", format="xml"))
