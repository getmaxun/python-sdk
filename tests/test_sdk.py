"""Checks every public method sends the right request to the Maxun SDK API.

The expected endpoints, bodies and response shapes come from the server's
routes (server/src/api/sdk.ts in getmaxun/maxun).
"""

import json
import re
import warnings

import httpx
import pytest
import respx

from maxun import (
    Config, ConflictError, CrawlConfig, Crawl, Extract, Maxun, MaxunSync, NotFoundError,
    RunFailedError, Scrape, ScheduleConfig, SearchConfig, ValidationError, WebhookConfig,
)

BASE = "http://localhost:8080/api/sdk"


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


def test_runresult_export_is_the_class():
    import maxun
    from maxun.robot import RunResult
    assert maxun.RunResult is RunResult


async def test_doc_parse_links(mock, maxun):
    rec = robot_record("p1", type_="doc-parse")
    rec["recording"]["outputFormats"] = ["markdown", "links"]
    mock.get("robots/p1").respond(json={"data": rec})
    mock.post("robots/p1/execute").respond(json={"data": RUN_RESULT})
    mock.get("robots/p1/runs/run1").respond(json={"data": {"serializableOutput": {"links": ["https://x"]}}})
    robot = await maxun.robots.get("p1")
    assert robot.formats == ["markdown", "links"]
    assert (await robot.run()).links == ["https://x"]


async def test_existing_extract_robot_warns(mock, maxun):
    mock.post("robots").respond(200, json={"data": robot_record(type_="extract"), "existing": True})
    with pytest.warns(UserWarning, match="NOT saved"):
        await maxun.extract.create("E").navigate("https://e.com").capture_text({"T": "h1"}).build()


async def test_runs_sorted_by_real_time(mock, maxun):
    mock.get("robots/r1").respond(json={"data": robot_record()})
    mock.get("robots/r1/runs").respond(json={"data": [
        {"runId": "a", "startedAt": "9/30/2026, 9:00:00 AM"},
        {"runId": "b", "startedAt": "10/1/2026, 1:00:00 AM"},
        {"runId": "c", "startedAt": "9/30/2026, 11:00:00 PM"},
    ]})
    robot = await maxun.robots.get("r1")
    assert [r["runId"] for r in await robot.get_runs()] == ["b", "c", "a"]


def test_sync_init_failure_stops_thread(monkeypatch):
    import threading
    monkeypatch.delenv("MAXUN_API_KEY", raising=False)
    before = threading.active_count()
    with pytest.raises(ValueError):
        MaxunSync()
    assert threading.active_count() == before


# ---------- URL-first calls ----------

async def test_scrape_url_first(mock, maxun):
    route = mock.post("robots").respond(201, json={"data": robot_record()})
    robot = await maxun.scrape("https://maxun.dev/pricing/", formats=["markdown", "html"], monitor=True)
    meta = body(route)["meta"]
    assert meta["url"] == "https://maxun.dev/pricing/" and meta["formats"] == ["markdown", "html"]
    assert meta["compareRuns"] is True
    assert re.fullmatch(r"Scrape: maxun\.dev/pricing \[[0-9a-f]{6}\]", meta["name"])
    assert robot.id == "r1"

    # The same call gives the same name; different settings give a different one.
    first = meta["name"]
    await maxun.scrape("https://maxun.dev/pricing/", formats=["markdown", "html"], monitor=True)
    assert body(route)["meta"]["name"] == first
    await maxun.scrape("https://maxun.dev/pricing/", formats=["markdown"])
    assert body(route)["meta"]["name"] != first

    await maxun.scrape("https://maxun.dev", name="Home", smart_queries="Price?")
    assert body(route)["meta"]["name"] == "Home"
    assert body(route)["meta"]["promptInstructions"] == "Price?"


async def test_url_first_catches_old_argument_order(maxun):
    with pytest.raises(TypeError):
        await maxun.scrape("My robot", "https://e.com")
    with pytest.raises(ValueError, match="URL first"):
        await maxun.scrape("My robot")
    with pytest.raises(ValueError, match="URL first"):
        maxun.extract("Products")


async def test_crawl_url_first(mock, maxun):
    route = mock.post("crawl").respond(201, json={"data": robot_record(type_="crawl")})
    await maxun.crawl("https://docs.e.com", limit=5, max_depth=2, include_paths=["/blog/*"], formats=["text"])
    sent = body(route)
    assert sent["url"] == "https://docs.e.com" and sent["formats"] == ["text"]
    assert sent["crawlConfig"] == {
        "mode": "domain", "limit": 5, "maxDepth": 2, "includePaths": ["/blog/*"],
        "respectRobots": True, "useSitemap": True, "followLinks": True,
    }
    assert sent["name"].startswith("Crawl: docs.e.com [")


async def test_search_query_first(mock, maxun):
    route = mock.post("search").respond(201, json={"data": robot_record(type_="search")})
    await maxun.search("AI model releases", mode="discover", time_range="week", limit=5)
    sent = body(route)
    assert sent["searchConfig"] == {"query": "AI model releases", "mode": "discover", "limit": 5,
                                    "filters": {"timeRange": "week"}}
    assert sent["name"].startswith("Search: AI model releases [")


async def test_extract_url_first(mock, maxun):
    route = mock.post("robots").respond(201, json={"data": robot_record(type_="extract")})
    robot = await maxun.extract("https://e.com", monitor=True).capture_text({"T": "h1"}).build()
    sent = body(route)
    assert sent["meta"]["type"] == "extract" and sent["meta"]["compareRuns"] is True
    assert sent["meta"]["name"].startswith("Extract: e.com [")
    assert sent["workflow"][-1]["what"][0] == {"action": "goto", "args": ["https://e.com"]}
    assert robot.type == "extract"

    await maxun.extract("https://e.com", name="Titles").capture_text({"T": "h1"}).build()
    assert body(route)["meta"]["name"] == "Titles"

    llm = mock.post("extract/llm").respond(json={"data": {"robotId": "r1"}})
    mock.get("robots/r1").respond(json={"data": robot_record(type_="extract")})
    await maxun.extract("https://e.com", prompt="prices", llm_provider="ollama")
    sent = body(llm)
    assert sent["prompt"] == "prices" and sent["url"] == "https://e.com" and sent["llmProvider"] == "ollama"
    assert sent["robotName"].startswith("Extract: e.com [")
    await maxun.extract(prompt="YC companies and batches")
    assert "url" not in body(llm) and body(llm)["robotName"].startswith("Extract: YC companies and batches [")

    with pytest.raises(TypeError):
        maxun.extract()
    with pytest.raises(TypeError):
        maxun.extract("https://e.com", llm_provider="ollama")


async def test_documents_reuse_robot_with_generated_name(mock, maxun):
    existing = robot_record("d9", type_="doc-extract")
    route = mock.post("robots/document").respond(409, json={"error": "exists"})
    mock.get("robots").mock(side_effect=lambda r: httpx.Response(200, json={"data": [existing]}))
    with pytest.raises(ConflictError):
        await maxun.documents.extract(b"x", "totals", file_name="a.pdf", name="Mine")

    robot_name = None

    def capture(request):
        nonlocal robot_name
        robot_name = re.search(rb'name="robotName"\r\n\r\n([^\r]*)', request.content).group(1).decode()
        existing["recording_meta"]["name"] = robot_name
        return httpx.Response(409, json={"error": "exists"})

    route.mock(side_effect=capture)
    robot = await maxun.documents.extract(b"x", "totals", file_name="a.pdf")
    assert robot_name.startswith("Document: a.pdf [") and robot.id == "d9"


def test_sync_url_first(mock):
    mock.post("robots").respond(201, json={"data": robot_record()})
    mock.post("extract/llm").respond(json={"data": {"robotId": "r1"}})
    mock.get("robots/r1").respond(json={"data": robot_record(type_="extract")})
    with MaxunSync(api_key="k", base_url=BASE) as m:
        assert m.scrape("https://e.com").id == "r1"
        assert m.extract("https://e.com", prompt="prices").type == "extract"
        assert m.extract("https://e.com").capture_text({"T": "h1"}).build().id == "r1"


# ---------- clean output ----------

def test_robot_and_config_hide_internals():
    from maxun import Robot as RobotClass, Client
    config = Config(api_key="secret-key", base_url=BASE)
    assert "secret-key" not in repr(config)
    client = Client(config)
    assert "secret-key" not in repr(client)
    robot = RobotClass(client, robot_record("f48", type_="extract", name="Quotes"))
    assert repr(robot) == "Robot(id='f48', name='Quotes', type='extract')"
    assert repr([robot]) == "[Robot(id='f48', name='Quotes', type='extract')]"
    assert robot.to_dict() == {"id": "f48", "name": "Quotes", "type": "extract"}
    assert robot.client is client and robot.robot_data["recording_meta"]["id"] == "f48"


from maxun.robot import Run as Run_


async def test_runs_are_summaries_with_results(mock, maxun):
    raw = {
        "id": "3faa", "runId": "bdae", "robotMetaId": "2c56", "robotId": "db-2c56", "name": "Example",
        "status": "success", "startedAt": "10/1/2026, 12:46:25 AM", "finishedAt": "10/1/2026, 12:47:14 AM",
        "log": "x" * 1000, "interpreterSettings": {"maxConcurrency": 1},
        "serializableOutput": {
            "scrapeSchema": {"Title": "Hi"},
            "scrapeList": {"List 1": [{"a": 1}]},
            "markdown": [{"content": "# Hi"}],
            "_comparison": {"changedFormats": ["markdown"]},
        },
        "binaryOutput": {"Screenshot 1": "https://s/1.png"},
        "hasChanges": True,
    }
    mock.get("robots/r1").respond(json={"data": robot_record()})
    mock.get("robots/r1/runs").respond(json={"data": [raw, {**raw, "runId": "old", "startedAt": "", "finishedAt": ""}]})
    narrow = Run_({**raw, "startedAt": "10/1/2026, 12:46:25\u202fPM"})
    assert narrow.started_at == "2026-10-01T12:46:25Z"
    mock.get("robots/r1/runs/bdae").respond(json={"data": raw})
    robot = await maxun.robots.get("r1")

    runs = await robot.get_runs()
    run = runs[0]
    assert run.to_dict() == {
        "id": "3faa", "run_id": "bdae", "robot_id": "2c56", "name": "Example", "status": "success",
        "started_at": "2026-10-01T00:46:25Z", "finished_at": "2026-10-01T00:47:14Z",
    }
    assert repr(run) == (
        "Run(id='3faa', run_id='bdae', robot_id='2c56', name='Example', status='success', "
        "started_at='2026-10-01T00:46:25Z', finished_at='2026-10-01T00:47:14Z')"
    )
    assert "log" not in repr(runs) and "serializableOutput" not in repr(runs)
    assert runs[1].started_at is None
    assert run["runId"] == "bdae" and run.get("missing", 1) == 1  # dict-style access still works

    result = run.result
    assert result.text_data == {"Title": "Hi"} and result.list_data == [{"a": 1}]
    assert result.markdown == "# Hi" and result.screenshots == ["https://s/1.png"]
    assert result.has_changes and result.changed_formats == ["markdown"]

    assert (await robot.get_run("bdae")).run_id == "bdae"
    assert (await robot.get_latest_run()).run_id in ("bdae", "old")


# ---------- monitoring ----------

def crawl_run(run_id, started, pages, status="success", comparison=None):
    out = {"crawl": {"Crawl": pages}}
    if comparison is not None:
        out["_comparison"] = comparison
    return {"runId": run_id, "status": status, "startedAt": started, "serializableOutput": out}


PAGES_V1 = [{"metadata": {"url": "https://e.com/a"}, "markdown": "A one"},
            {"metadata": {"url": "https://e.com/b"}, "markdown": "B"}]
PAGES_V2 = [{"metadata": {"url": "https://e.com/a"}, "markdown": "A two"},
            {"metadata": {"url": "https://e.com/c"}, "markdown": "C"}]


async def test_crawl_monitoring_in_sdk(mock, maxun):
    mock.get("robots/c1").respond(json={"data": robot_record("c1", type_="crawl", compareRuns=True)})
    mock.post("robots/c1/execute").respond(json={"data": {**RUN_RESULT, "runId": "new",
                                                           "data": {"crawlData": PAGES_V2}}})
    mock.get("robots/c1/runs").respond(json={"data": [
        crawl_run("new", "2026-09-30T10:00:00Z", PAGES_V2),
        crawl_run("broken", "2026-09-30T09:00:00Z", [], status="failed"),
        crawl_run("old", "2026-09-29T10:00:00Z", PAGES_V1),
    ]})
    server_diff = mock.get("robots/c1/runs/new/diff")
    robot = await maxun.robots.get("c1")

    result = await robot.run()
    assert result.has_changes and result.changed_formats == ["markdown"]
    assert result.changed_pages == {"added": ["https://e.com/c"], "removed": ["https://e.com/b"],
                                    "changed": ["https://e.com/a"]}

    diff = await robot.get_run_diff("new")
    assert not server_diff.called
    assert diff["previousRunId"] == "old" and diff["changedFormats"] == ["markdown"]
    added = "".join(c["value"] for c in diff["diffs"][0]["changes"] if c["added"])
    removed = "".join(c["value"] for c in diff["diffs"][0]["changes"] if c["removed"])
    assert "A two" in added and "## https://e.com/c" in added
    assert "A one" in removed and "## https://e.com/b" in removed


async def test_crawl_first_run_and_unchanged(mock, maxun):
    mock.get("robots/c1").respond(json={"data": robot_record("c1", type_="crawl", compareRuns=True)})
    mock.post("robots/c1/execute").respond(json={"data": {**RUN_RESULT, "runId": "new"}})
    runs = mock.get("robots/c1/runs")
    robot = await maxun.robots.get("c1")

    runs.respond(json={"data": [crawl_run("new", "2026-09-30T10:00:00Z", PAGES_V1)]})
    assert not (await robot.run()).has_changes

    runs.respond(json={"data": [crawl_run("new", "2026-09-30T10:00:00Z", PAGES_V1),
                                crawl_run("old", "2026-09-29T10:00:00Z", PAGES_V1)]})
    result = await robot.run()
    assert not result.has_changes and result.changed_pages["changed"] == []


async def test_crawl_defers_to_server_comparison(mock, maxun):
    mock.get("robots/c1").respond(json={"data": robot_record("c1", type_="crawl", compareRuns=True)})
    mock.post("robots/c1/execute").respond(json={"data": {**RUN_RESULT, "runId": "new", "hasChanges": True,
                                                           "changedFormats": ["text"]}})
    mock.get("robots/c1/runs").respond(json={"data": [
        crawl_run("new", "2026-09-30T10:00:00Z", PAGES_V2, comparison={"changedFormats": ["text"]}),
        crawl_run("old", "2026-09-29T10:00:00Z", PAGES_V1)]})
    server_diff = mock.get("robots/c1/runs/new/diff").respond(json={"data": {"runId": "new", "diffs": []}})
    robot = await maxun.robots.get("c1")
    assert (await robot.run()).changed_formats == ["text"]
    await robot.get_run_diff("new")
    assert server_diff.called


async def test_unmonitored_crawl_skips_comparison(mock, maxun):
    mock.get("robots/c1").respond(json={"data": robot_record("c1", type_="crawl")})
    mock.post("robots/c1/execute").respond(json={"data": RUN_RESULT})
    runs = mock.get("robots/c1/runs")
    robot = await maxun.robots.get("c1")
    await robot.run()
    assert not runs.called


async def test_monitoring_only_for_supported_types(mock, maxun):
    mock.get("robots/s1").respond(json={"data": robot_record("s1", type_="search")})
    robot = await maxun.robots.get("s1")
    with pytest.raises(ValueError, match="scrape, crawl and extract"):
        await robot.set_monitoring(True)
    with pytest.raises(TypeError):
        await maxun.search.create("Q", "query", monitor=True)


# ---------- review follow-ups ----------

async def test_old_argument_order_gets_a_clear_message(maxun):
    for call in (
        lambda: maxun.scrape("Home", "https://e.com"),
        lambda: maxun.crawl("Docs", "https://e.com"),
        lambda: maxun.search("My search", "AI"),
    ):
        with pytest.raises(TypeError, match="name=..."):
            await call()
    with pytest.raises(TypeError, match="name=..."):
        maxun.extract("Products", prompt="prices", url="https://e.com")
    with pytest.raises(TypeError, match="unexpected arguments: robot_name"):
        maxun.extract("https://e.com", robot_name="x")


async def test_keyword_url_still_works(mock, maxun):
    llm = mock.post("extract/llm").respond(json={"data": {"robotId": "r1"}})
    mock.get("robots/r1").respond(json={"data": robot_record(type_="extract")})
    await maxun.extract(url="https://e.com", prompt="prices")
    assert body(llm)["url"] == "https://e.com"


def test_runs_still_behave_like_dicts():
    from maxun.robot import Run as RunClass
    raw = {"id": "1", "runId": "r", "status": "success", "startedAt": "2026-10-01T00:00:00Z"}
    run = RunClass(raw)
    assert "runId" in run and dict(run) == raw and run == raw and sorted(run.keys()) == sorted(raw)
    assert json.loads(json.dumps(run)) == raw
    assert run.get_data() == raw and run.run_id == "r"
    assert repr(run).startswith("Run(id='1', run_id='r'")
    assert str([run]).startswith("[Run(")


async def test_generated_names_reuse_the_robot_on_conflict(mock, maxun):
    created = {}

    def create(request):
        created["name"] = json.loads(request.content)["meta"]["name"]
        return httpx.Response(409, json={"error": "exists with a different configuration"})

    mock.post("robots").mock(side_effect=create)
    mock.get("robots").mock(side_effect=lambda r: httpx.Response(
        200, json={"data": [robot_record("old", name=created.get("name"))]}))
    robot = await maxun.scrape("https://e.com")
    assert robot.id == "old"
    with pytest.raises(ConflictError):
        await maxun.scrape("https://e.com", name="Mine")

    llm = mock.post("extract/llm").respond(409, json={"error": "exists"})
    mock.get("robots").mock(side_effect=lambda r: httpx.Response(
        200, json={"data": [robot_record("p", type_="extract", name=json.loads(llm.calls[-1].request.content)["robotName"])]}))
    assert (await maxun.extract(prompt="YC companies")).id == "p"


async def test_default_formats_do_not_change_generated_names(mock, maxun):
    route = mock.post("crawl").respond(201, json={"data": robot_record(type_="crawl")})
    await maxun.crawl("https://e.com")
    first = body(route)["name"]
    await maxun.crawl("https://e.com", formats=["markdown"])
    assert body(route)["name"] == first
