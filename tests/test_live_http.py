"""List calls over a real HTTP connection (no mocking), for every resource."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from maxun import Maxun, MaxunSync

TYPES = ["scrape", "crawl", "extract", "search", "doc-extract", "doc-parse"]
ROBOTS = [
    {"id": f"db{n}", "recording_meta": {"id": str(n), "name": f"{t} {n}", "type": t}, "recording": {"workflow": []}}
    for n, t in enumerate(TYPES * 5)
]
EXPECTED = {
    "scrape": 5, "crawl": 5, "extract": 5, "search": 5, "documents": 10, "robots": 30,
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"data": ROBOTS}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def base_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/api/sdk"
    server.shutdown()



async def test_async_list_every_resource(base_url):
    async with Maxun(api_key="k", base_url=base_url) as maxun:
        for name, count in EXPECTED.items():
            robots = await getattr(maxun, name).list()
            assert len(robots) == count, name
        for t in TYPES:
            assert len(await maxun.robots.list(type=t)) == 5
            assert [r.type for r in await maxun.robots.list(type=t)] == [t] * 5
        assert len(await maxun.scrape.list(type="scrape")) == 5
        assert len(await maxun.documents.list(type="doc-parse")) == 5
        with pytest.raises(ValueError):
            await maxun.scrape.list(type="crawl")


def test_sync_list_every_resource(base_url):
    with MaxunSync(api_key="k", base_url=base_url) as maxun:
        for name, count in EXPECTED.items():
            assert len(getattr(maxun, name).list()) == count, name
        assert len(maxun.robots.list(type="crawl")) == 5
