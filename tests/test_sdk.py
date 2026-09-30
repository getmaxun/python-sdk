"""Checks every public method sends the right request to the Maxun SDK API.

The expected endpoints, bodies and response shapes come from the server's
routes (server/src/api/sdk.ts in getmaxun/maxun).
"""

import json
import warnings

import httpx
import pytest
import respx

from maxun import (
    Config, ConflictError, CrawlConfig, Crawl, Extract, Maxun, MaxunSync, NotFoundError,
    RunFailedError, Scrape, ScheduleConfig, SearchConfig, ValidationError, WebhookConfig,
)

BASE = "https://maxun.test/api/sdk/"


def robot_record(robot_id="r1", type_="scrape", **meta):
    return {
        "id": "db-" + robot_id,
        "recording_meta": {"id": robot_id, "name": meta.pop("name", "Robot"), "type": type_, **meta},
        "recording": {"workflow": meta.pop("workflow", [])},
        "webhooks": None,
        "schedule": None,
    }


RUN_RESULT = {
    "runId": "run1", "status": "success", "hasChanges": False, "changedFormats": [],
    "data": {"textData": {"Title": "Hi"}, "listData": [{"a": 1}], "crawlData": [], "searchData": {},
             "markdown": "# Hi", "html": None, "text": None, "summary": None, "promptResult": "42"},
    "screenshots": [],
}


def body(route, i=-1):
    return json.loads(route.calls[i].request.content)


@pytest.fixture
def mock():
    with respx.mock(base_url=BASE, assert_all_called=False) as m:
        yield m


@pytest.fixture
async def maxun():
    async with Maxun(api_key="k", base_url=BASE) as m:
        yield m


# ---------- configuration ----------

def test_config_reads_env(monkeypatch):
    monkeypatch.setenv("MAXUN_API_KEY", "env-key")
    monkeypatch.setenv("MAXUN_BASE_URL", "http://localhost:8080/api/sdk")
    monkeypatch.setenv("MAXUN_TEAM_ID", "team")
    c = Config()
    assert (c.api_key, c.base_url, c.team_id) == ("env-key", "http://localhost:8080/api/sdk/", "team")


def test_config_requires_key(monkeypatch):
    monkeypatch.delenv("MAXUN_API_KEY", raising=False)
    with pytest.raises(ValueError, match="MAXUN_API_KEY"):
        Config()


async def test_headers(mock):
    route = mock.get("status").respond(json={"email": "a@b.c"})
    async with Maxun(api_key="k", base_url=BASE, team_id="t") as m:
        assert (await m.status())["email"] == "a@b.c"
    assert route.calls[0].request.headers["x-api-key"] == "k"
    assert route.calls[0].request.headers["x-team-id"] == "t"


# ---------- scrape / crawl / search / extract creation ----------

async def test_scrape_create(mock, maxun):
    route = mock.post("robots").respond(201, json={"data": robot_record(formats=["markdown", "text"])})
    robot = await maxun.scrape.create(
        "S", "https://e.com", formats=["markdown", "text"], smart_queries=" price? ", monitor=True
    )
    meta = body(route)["meta"]
    assert meta == {"name": "S", "type": "scrape", "url": "https://e.com", "formats": ["markdown", "text"],
                    "promptInstructions": "price?", "compareRuns": True}
    assert body(route)["workflow"] == []
    assert robot.id == "r1" and robot.type == "scrape"


async def test_scrape_rejects_bad_format(maxun):
    with pytest.raises(ValueError, match="Invalid formats"):
        await maxun.scrape.create("S", "https://e.com", formats=["pdf"])


async def test_crawl_defaults(mock, maxun):
    route = mock.post("crawl").respond(201, json={"data": robot_record(type_="crawl")})
    await maxun.crawl.create("C", "https://e.com")
    sent = body(route)
    assert sent["url"] == "https://e.com"
    assert sent["crawlConfig"] == {"mode": "domain", "limit": 50, "maxDepth": 3, "respectRobots": True,
                                   "useSitemap": True, "followLinks": True}


async def test_crawl_partial_dict_and_monitor(mock, maxun):
    create = mock.post("crawl").respond(201, json={"data": robot_record(type_="crawl")})
    update = mock.put("robots/r1").respond(json={"data": robot_record(type_="crawl", compareRuns=True)})
    robot = await maxun.crawl.create("C", "https://e.com", {"limit": 5, "include_paths": ["/blog"]}, monitor=True)
    cfg = body(create)["crawlConfig"]
    assert cfg["limit"] == 5 and cfg["includePaths"] == ["/blog"] and cfg["maxDepth"] == 3
    assert body(update) == {"meta": {"compareRuns": True}}
    assert robot.is_monitoring


async def test_search_create(mock, maxun):
    route = mock.post("search").respond(201, json={"data": robot_record(type_="search")})
    await maxun.search.create("Q", SearchConfig(query="ai", mode="discover", time_range="week", limit=5))
    assert body(route)["searchConfig"] == {"query": "ai", "mode": "discover", "limit": 5,
                                           "filters": {"timeRange": "week"}}
    await maxun.search.create("Q2", "just a query")
    assert body(route)["searchConfig"]["query"] == "just a query"
    assert body(route)["searchConfig"]["mode"] == "scrape"


async def test_extract_builder(mock, maxun):
    route = mock.post("robots").respond(201, json={"data": robot_record(type_="extract")})
    robot = await (
        maxun.extract.create("E")
        .navigate("https://e.com")
        .capture_text({"Title": "h1"})
        .capture_list({"selector": "li", "max_items": 5, "pagination": {"type": "none"}})
        .scroll(2)
        .build()
    )
    sent = body(route)
    assert sent["meta"] == {"name": "E", "type": "extract"}
    main, blank = sent["workflow"]
    assert blank["where"]["url"] == "about:blank" and blank["what"][0] == {"action": "goto", "args": ["https://e.com"]}
    actions = [a["action"] for a in main["what"]]
    assert actions == ["scrapeSchema", "scrapeList", "scroll"]
    assert main["what"][1]["args"][0] == {"itemSelector": "li", "maxItems": 5,
                                          "pagination": {"type": "none", "selector": None}}
    assert main["what"][2]["args"] == [2]
    assert robot.type == "extract"


async def test_extract_builder_await_still_works(mock, maxun):
    mock.post("robots").respond(201, json={"data": robot_record(type_="extract")})
    robot = await maxun.extract.create("E").navigate("https://e.com").capture_text({"T": "h1"})
    assert robot.id == "r1"


def test_builder_requires_navigate():
    with pytest.raises(ValueError, match="navigate"):
        Extract(Config(api_key="k", base_url=BASE)).create("E").capture_text({"T": "h1"})


async def test_extract_from_prompt(mock, maxun):
    llm = mock.post("extract/llm").respond(json={"success": True, "data": {"robotId": "r9"}})
    mock.get("robots/r9").respond(json={"data": robot_record("r9", type_="extract")})
    robot = await maxun.extract.from_prompt("get prices", url="https://e.com", name="P")
    assert body(llm) == {"prompt": "get prices", "url": "https://e.com", "robotName": "P"}
    assert robot.id == "r9"
    # old name, self-hosted LLM settings
    await maxun.extract.extract("get prices", llm_provider="ollama", robot_name="P")
    assert body(llm) == {"prompt": "get prices", "robotName": "P", "llmProvider": "ollama"}


async def test_llm_settings_validated(maxun):
    with pytest.raises(ValueError, match="llm_api_key"):
        await maxun.extract.from_prompt("x", llm_provider="openai")


# ---------- documents ----------

@pytest.mark.parametrize("name,mime", [
    ("a.pdf", "application/pdf"),
    ("a.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("a.png", "image/png"),
    ("a.JPG", "image/jpeg"),
    ("a.csv", "text/csv"),
])
async def test_document_extract_mime(mock, maxun, name, mime):
    route = mock.post("robots/document").respond(201, json={"success": True, "data": robot_record(type_="doc-extract")})
    robot = await maxun.documents.extract(b"bytes", "totals", file_name=name, name="D")
    content = route.calls[-1].request.content
    assert f"Content-Type: {mime}".encode() in content
    assert b'name="prompt"' in content and b'name="robotName"' in content
    assert robot.type == "doc-extract"


async def test_document_parse_formats(mock, maxun, tmp_path):
    f = tmp_path / "report.xlsx"
    f.write_bytes(b"x")
    route = mock.post("robots/document-parse").respond(201, json={"data": robot_record(type_="doc-parse")})
    await maxun.documents.parse(f, formats=["markdown", "links"])
    content = route.calls[-1].request.content
    assert content.count(b'name="outputFormats[]"') == 2
    await maxun.documents.parse(str(f))  # default: server uses all formats
    assert b"outputFormats" not in route.calls[-1].request.content
    with pytest.raises(ValueError, match="Invalid document formats"):
        await maxun.documents.parse(f, formats=["text"])


async def test_document_unsupported_type(maxun):
    with pytest.raises(ValueError, match="Unsupported document type"):
        await maxun.documents.parse(b"x", file_name="a.txt")


async def test_document_error_is_maxun_error(mock, maxun):
    mock.post("robots/document").respond(409, json={"error": "A robot named \"D\" already exists."})
    with pytest.raises(ConflictError):
        await maxun.documents.extract(b"x", "p", file_name="a.pdf", name="D")


# ---------- robot management ----------

async def test_list_filters_by_type(mock, maxun):
    mock.get("robots").respond(json={"data": [robot_record("a", "scrape"), robot_record("b", "extract"),
                                              robot_record("c", "doc-parse")]})
    assert [r.id for r in await maxun.extract.list()] == ["b"]
    assert [r.id for r in await maxun.extract.get_robots()] == ["b"]
    assert [r.id for r in await maxun.documents.list()] == ["c"]
    assert len(await maxun.robots.list()) == 3
    assert [r.id for r in await maxun.robots.list(type="scrape")] == ["a"]


async def test_find_by_name(mock, maxun):
    mock.get("robots").respond(json={"data": [robot_record("a", name="Alpha")]})
    assert (await maxun.robots.find("Alpha")).id == "a"
    with pytest.raises(NotFoundError):
        await maxun.robots.find("Beta")


async def test_run(mock, maxun):
    mock.get("robots/r1").respond(json={"data": robot_record()})
    route = mock.post("robots/r1/execute").respond(json={"data": RUN_RESULT})
    robot = await maxun.robots.get("r1")
    result = await robot.run(formats=["markdown"], smart_queries="price?")
    assert body(route) == {"formats": ["markdown"], "promptInstructions": "price?"}
    assert result.markdown == "# Hi" and result.text_data == {"Title": "Hi"}
    assert result.list_data == [{"a": 1}] and result.smart_query_result == "42"
    assert result["data"]["listData"] == [{"a": 1}]  # dict access still works
    assert result.run_id == "run1"


async def test_run_legacy_options_warn(mock, maxun):
    mock.get("robots/r1").respond(json={"data": robot_record()})
    route = mock.post("robots/r1/execute").respond(json={"data": RUN_RESULT})
    robot = await maxun.robots.get("r1")
    with pytest.warns(UserWarning, match="ignored"):
        await robot.run({"params": {"a": 1}, "timeout": 60})
    assert body(route) == {}


async def test_run_failure(mock, maxun):
    mock.get("robots/r1").respond(json={"data": robot_record()})
    mock.post("robots/r1/execute").respond(500, json={"error": "Failed to execute robot", "message": "Run failed"})
    robot = await maxun.robots.get("r1")
    with pytest.raises(RunFailedError, match="Run failed"):
        await robot.run()


async def test_runs_diff_abort_duplicate_delete(mock, maxun):
    mock.get("robots/r1").respond(json={"data": robot_record()})
    mock.get("robots/r1/runs").respond(json={"data": [{"runId": "old", "startedAt": "2026-01-01"},
                                                      {"runId": "new", "startedAt": "2026-02-01"}]})
    diff = mock.get("robots/r1/runs/new/diff").respond(json={"data": {"runId": "new", "diffs": []}})
    abort = mock.post("robots/r1/runs/new/abort").respond(json={"data": {}})
    dup = mock.post("robots/r1/duplicate").respond(201, json={"data": robot_record("r2")})
    delete = mock.delete("robots/r1").respond(json={"message": "ok"})

    robot = await maxun.robots.get("r1")
    assert (await robot.get_latest_run())["runId"] == "new"
    await robot.get_run_diff("new", format="markdown")
    assert diff.calls[0].request.url.params["format"] == "markdown"
    await robot.abort("new")
    assert abort.called
    copy = await robot.duplicate("https://other.com")
    assert body(dup) == {"targetUrl": "https://other.com"} and copy.id == "r2"
    await robot.delete()
    assert delete.called


async def test_schedule_forms(mock, maxun):
    mock.get("robots/r1").respond(json={"data": robot_record()})
    saved = {"runEvery": 6, "runEveryUnit": "HOURS", "timezone": "UTC", "cronExpression": "0 */6 * * *"}
    route = mock.put("robots/r1").respond(json={"data": {**robot_record(), "schedule": saved}})
    robot = await maxun.robots.get("r1")

    await robot.schedule(ScheduleConfig(run_every=6, run_every_unit="HOURS", cron_expression="ignored"))
    assert body(route) == {"schedule": {"runEvery": 6, "runEveryUnit": "HOURS", "timezone": "UTC"}}
    await robot.schedule({"runEvery": 1, "runEveryUnit": "days", "timezone": "Asia/Kolkata", "atTimeStart": "09:00"})
    assert body(route)["schedule"] == {"runEvery": 1, "runEveryUnit": "DAYS", "timezone": "Asia/Kolkata",
                                       "atTimeStart": "09:00"}
    result = await robot.schedule(run_every=2, run_every_unit="WEEKS", start_from="monday")
    assert body(route)["schedule"]["startFrom"] == "MONDAY"
    assert result["cronExpression"] == "0 */6 * * *"
    await robot.unschedule()
    assert body(route) == {"schedule": None}


async def test_webhooks(mock, maxun):
    stored = {"webhooks": None}

    def put(request):
        payload = json.loads(request.content)
        stored["webhooks"] = payload.get("webhooks")
        return httpx.Response(200, json={"data": {**robot_record(), "webhooks": stored["webhooks"]}})

    mock.get("robots/r1").mock(side_effect=lambda r: httpx.Response(
        200, json={"data": {**robot_record(), "webhooks": stored["webhooks"]}}))
    mock.put("robots/r1").mock(side_effect=put)
    robot = await maxun.robots.get("r1")

    hook = await robot.add_webhook("https://hooks.test/a", retry_attempts=5)
    assert hook["events"] == ["run_completed", "run_failed"]
    assert hook["retryAttempts"] == 5 and hook["active"] is True

    with pytest.warns(UserWarning, match="run_completed"):
        await robot.add_webhook({"url": "https://hooks.test/b", "events": ["run.completed"]})
    assert stored["webhooks"][1]["events"] == ["run_completed"]

    # same URL again updates instead of duplicating
    await robot.add_webhook(WebhookConfig(url="https://hooks.test/a", events=["run_failed"]))
    assert len(stored["webhooks"]) == 2 and stored["webhooks"][0]["events"] == ["run_failed"]
    assert stored["webhooks"][0]["id"] == hook["id"]

    with pytest.raises(ValueError, match="Unknown webhook event"):
        await robot.add_webhook({"url": "https://hooks.test/c", "events": ["done"]})

    await robot.remove_webhook("https://hooks.test/b")
    assert [w["url"] for w in robot.get_webhooks()] == ["https://hooks.test/a"]
    await robot.remove_webhooks()
    assert robot.get_webhooks() == []


async def test_list_limit_and_rename(mock, maxun):
    workflow = [{"where": {}, "what": [{"action": "scrapeList", "args": [{"limit": 100}]}]}]
    mock.get("robots/r1").respond(json={"data": {**robot_record(), "recording": {"workflow": workflow}}})
    route = mock.put("robots/r1").respond(json={"data": robot_record(name="New")})
    robot = await maxun.robots.get("r1")
    await robot.set_list_limit(25)
    assert body(route) == {"limits": [{"pairIndex": 0, "actionIndex": 0, "argIndex": 0, "limit": 25}]}
    await robot.rename("New")
    assert body(route) == {"meta": {"name": "New"}} and robot.name == "New"


# ---------- errors ----------

@pytest.mark.parametrize("status,cls", [(404, NotFoundError), (409, ConflictError), (400, ValidationError)])
async def test_error_mapping(mock, maxun, status, cls):
    mock.get("robots/x").respond(status, json={"error": "nope", "details": "why"})
    with pytest.raises(cls) as info:
        await maxun.robots.get("x")
    assert info.value.status_code == status and "nope" in str(info.value)


async def test_non_json_error_and_body(mock, maxun):
    mock.get("robots/x").respond(502, text="<html>Bad gateway</html>")
    with pytest.raises(Exception) as info:
        await maxun.robots.get("x")
    assert "Bad gateway" in str(info.value)
    mock.get("robots").respond(200, text="<html>app</html>")
    with pytest.raises(Exception, match="non-JSON"):
        await maxun.robots.list()


# ---------- legacy entry points & sync ----------

async def test_legacy_classes(mock):
    route = mock.post("robots").respond(201, json={"data": robot_record()})
    scraper = Scrape(Config(api_key="k", base_url=BASE))
    robot = await scraper.create("S", "https://e.com")
    assert robot.id == "r1" and body(route)["meta"]["formats"] == ["markdown"]
    await scraper.close()
    crawler = Crawl(Config(api_key="k", base_url=BASE))
    c = mock.post("crawl").respond(201, json={"data": robot_record(type_="crawl")})
    await crawler.create("C", "https://e.com", CrawlConfig(mode="path", limit=3))
    assert body(c)["crawlConfig"]["mode"] == "path"
    await crawler.close()


def test_sync_client(mock):
    mock.post("robots").respond(201, json={"data": robot_record(type_="extract")})
    mock.post("robots/r1/execute").respond(json={"data": RUN_RESULT})
    mock.get("robots").respond(json={"data": [robot_record()]})
    with MaxunSync(api_key="k", base_url=BASE) as m:
        robot = m.extract.create("E").navigate("https://e.com").capture_text({"T": "h1"}).build()
        assert robot.id == "r1"
        assert robot.run().text_data == {"Title": "Hi"}
        assert [r.id for r in m.robots.list()] == ["r1"]


def test_deprecated_builder_calls_warn():
    b = Extract(Config(api_key="k", base_url=BASE)).create("E").navigate("https://e.com")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        b.set_cookies([{"name": "a", "value": "b"}]).mode("bulk").scroll("down", 300)
    assert len(caught) == 3
    assert b.current_step["what"] == [{"action": "scroll", "args": [1]}]
    assert "cookies" not in b.current_step["where"]


async def test_run_fills_links_and_document_data(mock, maxun):
    mock.get("robots/r1").respond(json={"data": robot_record(formats=["markdown", "links"])})
    mock.post("robots/r1/execute").respond(json={"data": RUN_RESULT})
    mock.get("robots/r1/runs/run1").respond(json={"data": {"serializableOutput": {
        "links": [{"url": "https://a"}, {"url": "https://b"}]}}})
    robot = await maxun.robots.get("r1")
    assert (await robot.run()).links == ["https://a", "https://b"]

    mock.get("robots/d1").respond(json={"data": robot_record("d1", type_="doc-extract")})
    mock.post("robots/d1/execute").respond(json={"data": RUN_RESULT})
    mock.get("robots/d1/runs/run1").respond(json={"data": {"serializableOutput": {
        "scrapeDoc": {"data": {"total": 10}}}}})
    doc = await maxun.robots.get("d1")
    assert (await doc.run()).document_data == {"total": 10}
