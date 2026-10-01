# Maxun Python SDK

The official Python SDK for [Maxun](https://maxun.dev): turn websites and documents into structured data.

Works with Maxun Cloud and self-hosted Maxun.

```bash
pip install maxun
```

```python
import asyncio
from maxun import Maxun

async def main():
    async with Maxun(api_key="your-api-key") as maxun:
        robot = await maxun.scrape("https://maxun.dev", formats=["markdown", "html"])
        result = await robot.run()
        print(result.markdown)

asyncio.run(main())
```

Prefer no `async`? Use `MaxunSync`, which has the same methods without `await` (see [Sync usage](#sync-usage)).

## Contents

- [Setup](#setup)
- [What you can build](#what-you-can-build): [Scrape](#scrape) · [Extract with selectors](#extract-with-selectors) · [Extract with a prompt](#extract-with-a-prompt) · [Crawl](#crawl) · [Search](#search) · [Documents](#documents)
- [Running robots and reading results](#running-robots-and-reading-results)
- [Managing robots](#managing-robots): [Runs](#runs) · [Schedules](#schedules) · [Webhooks](#webhooks) · [Change monitoring](#change-monitoring)
- [LLM settings: Cloud vs self-hosted](#llm-settings-cloud-vs-self-hosted)
- [Errors](#errors)
- [Sync usage](#sync-usage)
- [Upgrading from 0.0.x](#upgrading-from-00x)

## Setup

Get an API key from your Maxun account, then either pass it in or put it in the environment:

```bash
export MAXUN_API_KEY=your-api-key
export MAXUN_BASE_URL=https://app.maxun.dev/api/sdk/   # optional; this is the default (Maxun Cloud)
export MAXUN_TEAM_ID=your-team-uuid                    # optional; Maxun Cloud teams
```

```python
maxun = Maxun()                                            # everything from the environment
maxun = Maxun(api_key="...", base_url="http://localhost:8080/api/sdk/")   # self-hosted
```

The SDK reads real environment variables. To use a `.env` file, call `load_dotenv()` from `python-dotenv` first (installed with the SDK).

`Maxun` holds one connection. Use `async with Maxun() as maxun:` or call `await maxun.close()` when done.

Everything hangs off it:

| Call | Creates | Result is in |
|---|---|---|
| `maxun.scrape(url, ...)` | a robot that turns one page into markdown/html/text/links/summary/screenshots | `result.markdown`, `.html`, `.text`, `.links`, `.summary`, `.screenshots` |
| `maxun.extract(url, prompt=...)` or `maxun.extract(url)` | a robot that captures specific data, by selectors or from a prompt | `result.text_data`, `result.list_data` |
| `maxun.crawl(url, ...)` | a robot that visits many pages of a site | `result.crawl_data` |
| `maxun.search(query, ...)` | a robot that searches the web (DuckDuckGo) | `result.search_data` |
| `maxun.documents.extract(file, prompt)` / `.parse(file)` | a robot that reads a PDF, DOCX, XLSX, CSV, JPG or PNG | `result.document_data` / `result.markdown` etc. |
| `maxun.robots` | nothing; lists, finds and deletes robots of any type | |

Each call takes what to work on first (a URL, a query or a file), then the settings as keyword arguments. It returns a `Robot`, saved on your account; run it as often as you like.

**Robot names.** Every call accepts `name="..."`. Leave it out and the SDK names the robot after what it does plus a short fingerprint of its settings, e.g. `Scrape: maxun.dev [3f2a1c]`. So:

- Running the same call again reuses the same robot instead of creating a duplicate. This holds even if you've edited that robot since, or a prompt robot found a different page the second time.
- Changing any setting gives a new name, so it never clashes with the old robot.
- The Node SDK generates the same names, so both SDKs share robots.

If you choose your own names, reuse behaves differently per robot type:

- Scrape, crawl and prompt-extract robots: the same name with the same settings returns the existing robot; different settings raise `ConflictError`.
- Selector-extract robots: the same name and URL returns the existing robot **unchanged, even if your steps differ**. The SDK warns when this happens. Use a new name or delete the old robot to save new steps.
- Document robots: an existing name raises `ConflictError`.
- Search robots: names are not checked, so every call makes a new robot.

The older style, `maxun.scrape.create(name, url, ...)` and `Scrape(config).create(...)`, still works.

## What you can build

### Scrape

```python
robot = await maxun.scrape(
    "https://example.com/pricing",
    formats=["markdown", "links", "screenshot-fullpage"],
)
result = await robot.run()
result.markdown     # str
result.links        # list of URLs
result.screenshots  # list
```

| Argument | Default | |
|---|---|---|
| `formats` | `["markdown"]` | any of `markdown`, `html`, `text`, `links`, `summary`, `screenshot-visible`, `screenshot-fullpage` |
| `smart_queries` | none | a question the LLM answers about the page on every run |
| `monitor` | off | compare every run with the previous one |
| `name` | generated | robot name |

**Smart Queries** ask an LLM a question about the page on every run:

```python
robot = await maxun.scrape("https://news.ycombinator.com", smart_queries="Which story has the most points?")
result = await robot.run()
result.smart_query_result

# or for a single run
result = await robot.run(smart_queries="List the three newest stories")
```

`summary` and Smart Queries use an LLM; see [LLM settings](#llm-settings-cloud-vs-self-hosted).

### Extract with selectors

`maxun.extract(url)` starts a robot on that page. Chain the steps and finish with `.build()`:

```python
robot = await (
    maxun.extract("https://shop.example.com")
    .capture_text({"Store name": "h1", "Tagline": ".hero p"})
    .capture_list({"selector": "article.product", "max_items": 50})
    .build()
)
result = await robot.run()
result.text_data   # {"Store name": "...", "Tagline": "..."}
result.list_data   # [{...}, {...}]
```

- `capture_text({field: selector})` captures single values. CSS and XPath selectors both work.
- `capture_list({"selector": ...})` captures every element matching `selector`; the fields inside each item are detected automatically. `max_items` defaults to 100.
- Pagination is auto-detected. To set it yourself, add `"pagination"`:
  - `{"type": "scrollDown"}` for infinite scroll
  - `{"type": "clickNext", "selector": "a.next"}` for a Next button
  - `{"type": "clickLoadMore", "selector": "button.more"}` for a Load more button
  - `{"type": "none"}` to read only the first page
- Pass `name="..."` to any `capture_*` to label that capture.

Other steps, in the order you want them to happen:

```python
.navigate(url)                        # go to another page
.click(selector)
.type(selector, text)                 # stored encrypted; input_type="password" etc. is auto-detected
.wait_for(selector, timeout=30000)    # milliseconds
.wait(1000)                           # milliseconds
.scroll(pages=2)                      # scroll down by screen heights
.capture_screenshot("name", full_page=False)
.monitor_changes()                    # see Change monitoring
```

`maxun.extract(url, name=..., monitor=True)` names the robot and turns on [change monitoring](#change-monitoring). `capture_list` also accepts `ExtractListConfig(selector=..., max_items=..., pagination=PaginationConfig(type="clickNext", selector=...))`.

### Extract with a prompt

Describe the data; Maxun builds the robot:

```python
robot = await maxun.extract(
    "https://www.ycombinator.com/companies",
    prompt="Company names, descriptions and batch for the first 15 companies",
)
result = await robot.run()
result.list_data

# Without a URL, Maxun searches for a suitable page first
robot = await maxun.extract(prompt="Company names and batches from the YC directory")
```

### Crawl

```python
robot = await maxun.crawl(
    "https://docs.example.com",
    limit=100,
    include_paths=["/guides/*"],
    formats=["markdown"],
)
result = await robot.run()
for page in result.crawl_data:
    print(page["metadata"]["url"])
```

| Argument | Default | |
|---|---|---|
| `mode` | `"domain"` | stay on the same `"domain"`, `"subdomain"` or URL `"path"` |
| `limit` | `50` | maximum number of pages |
| `max_depth` | `3` | how many links deep to follow |
| `include_paths` / `exclude_paths` | none | URL patterns to keep or skip, e.g. `["/blog/*"]` |
| `use_sitemap` / `follow_links` / `respect_robots` | `True` | |
| `formats` | `["markdown"]` | what to capture from each page (same choices as scrape) |
| `monitor` | off | compare every run with the previous one |
| `name` | generated | robot name |

### Search

```python
robot = await maxun.search("AI model releases", mode="discover", time_range="week")
result = await robot.run()
result.search_data
```

| Argument | Default | |
|---|---|---|
| `mode` | `"scrape"` | `"discover"` returns titles, URLs and snippets; `"scrape"` also opens each result and scrapes it |
| `limit` | `10` | number of results |
| `time_range` | any time | `"day"`, `"week"`, `"month"` or `"year"` |
| `formats` | `["markdown"]` | what to capture from each result in scrape mode |
| `name` | generated | robot name |

### Documents

PDF, DOCX, XLSX, CSV, JPG and PNG.

```python
# Pull specific data out of a file
robot = await maxun.documents.extract("invoice.pdf", "Invoice number, date and total")
result = await robot.run()
result.document_data

# Convert a file to text formats
robot = await maxun.documents.parse("report.docx", formats=["markdown", "links"])
result = await robot.run()
result.markdown
```

`parse` formats: `markdown`, `html`, `links`, `summary` (default: all four). You can pass bytes instead of a path; then give `file_name="report.docx"` so the type is known.

Sending the same file with the same prompt or formats again returns the robot created the first time.

## Running robots and reading results

```python
result = await robot.run()
```

`run()` waits until the run finishes (long crawls can take a while) and returns a `RunResult`. Optional arguments:

- `formats=[...]` changes the output formats for this run only.
- `smart_queries="..."` asks a question for this run only.
- `timeout=600` stops waiting after that many seconds. The run may still finish on the server; check `await robot.get_latest_run()`.

If the run fails or is aborted, `run()` raises `RunFailedError`.

| Attribute | Filled by |
|---|---|
| `run_id`, `status` | every run |
| `markdown`, `html`, `text`, `summary`, `links` | scrape and document-parse robots, in the formats you chose |
| `smart_query_result` | scrape robots with Smart Queries |
| `text_data` (dict) | `capture_text` |
| `list_data` (list) | `capture_list`, prompt extraction |
| `crawl_data` (list, one item per page) | crawl robots |
| `search_data` (dict) | search robots |
| `document_data` | document-extract robots |
| `screenshots` (list) | screenshot formats and `capture_screenshot` |
| `has_changes`, `changed_formats` | robots with change monitoring |
| `changed_pages` | crawl robots with change monitoring |

`RunResult` is also a regular dict, so `result["data"]["listData"]` works too.

## Managing robots

Robots print as just their id, name and type:

```python
>>> await maxun.robots.list()
[Robot(id='f4880b47-…', name='Extract: quotes.toscrape.com [a1b2c3]', type='extract'),
 Robot(id='b827723a-…', name='Crawl: quotes.toscrape.com [9d8e7f]', type='crawl')]
```

```python
await maxun.robots.list()                  # all robots
await maxun.robots.list(type="crawl")      # one type: extract, scrape, crawl, search, doc-extract, doc-parse
await maxun.scrape.list()                  # only scrape robots (every resource has list/get/delete)
robot = await maxun.robots.get("robot-id")
robot = await maxun.robots.find("Pricing page")   # by exact name
await maxun.robots.delete("robot-id")
```

A `Robot` has `id`, `name`, `type`, `url`, `formats` and `is_monitoring`, plus:

```python
await robot.run()
robot.to_dict()                        # {"id": ..., "name": ..., "type": ...}

await robot.rename("New name")
await robot.set_list_limit(25)         # item limit of the list/crawl/search step
copy = await robot.duplicate("https://other-site.com/page")   # same robot, different URL
await robot.refresh()                  # reload from the server
await robot.delete()

robot.get_data()                       # the raw robot record
```

### Runs

```python
>>> await robot.get_runs()             # newest first
[Run(id='3faaa1cd-…', run_id='bdae3b5a-…', robot_id='2c56ce3b-…', name='Example',
     status='success', started_at='2026-10-01T00:46:25Z', finished_at='2026-10-01T00:47:14Z')]

run = await robot.get_latest_run()
run = await robot.get_run(run_id)
await robot.abort(run_id)              # a queued or running run

run.result                             # the run's output, same as robot.run() returns
run.to_dict()                          # the summary fields above
run.get_data()                         # the raw run record (a run is also still a dict of it)
```

`run.result` works for every run, including scheduled ones, so you can read their data later. Times are ISO 8601 in UTC; status is `queued`, `running`, `success`, `failed`, `aborting` or `aborted`.

### Schedules

```python
await robot.schedule(run_every=6, run_every_unit="HOURS", timezone="Asia/Kolkata")
await robot.schedule(run_every=1, run_every_unit="WEEKS", start_from="MONDAY", at_time_start="09:00")
await robot.schedule(run_every=1, run_every_unit="MONTHS", day_of_month=1, at_time_start="06:30")

robot.get_schedule()      # includes nextRunAt and the generated cronExpression
await robot.unschedule()
```

- `run_every_unit` is `MINUTES`, `HOURS`, `DAYS`, `WEEKS` or `MONTHS`. `timezone` defaults to `"UTC"`.
- `at_time_start` (`"HH:MM"`) is the time of day for DAYS/WEEKS/MONTHS. For HOURS, only its minutes are used.
- `start_from` is the weekday for WEEKS. `day_of_month` is for MONTHS.

A `ScheduleConfig(...)` or a dict works in place of keyword arguments.

### Webhooks

```python
hook = await robot.add_webhook("https://your-server.com/maxun")   # both events
await robot.add_webhook(WebhookConfig(url="https://alerts.example.com", events=["run_failed"], retry_attempts=5))

robot.get_webhooks()
await robot.remove_webhook("https://alerts.example.com")   # by URL or id
await robot.remove_webhooks()                              # all
```

- Events are `run_completed` and `run_failed`.
- Maxun sends a POST with `event_type`, `timestamp`, `webhook_id` and `data`.
- Failed deliveries are retried (`retry_attempts`, default 3) with growing delays (`retry_delay` seconds, default 5).
- Adding a URL that is already registered updates it.

### Change monitoring

Scrape, crawl and extract robots can compare every run with the previous successful run. Turn it on with `monitor=True`:

```python
robot = await maxun.scrape("https://example.com/pricing", formats=["text"], monitor=True)
robot = await maxun.crawl("https://docs.example.com", monitor=True)
robot = await maxun.extract(url, monitor=True).capture_list({...}).build()
robot = await maxun.extract(url, prompt="Product names and prices", monitor=True)

# or on an existing robot
await robot.set_monitoring(True)       # set_monitoring(False) turns it off
```

The first run is the baseline. After that, every run tells you what changed:

```python
result = await robot.run()
if result.has_changes:
    print(result.changed_formats)      # e.g. ["markdown"], or ["captured-list"] for extract robots
    diff = await robot.get_run_diff(result.run_id)          # optionally format="markdown"
    for d in diff["diffs"]:
        for change in d["changes"]:
            if change["added"] or change["removed"]:
                print("+" if change["added"] else "-", change["value"])
```

What gets compared:

| Robot | Compared | `format=` values |
|---|---|---|
| Scrape | the page's `text`, `markdown` and `html` output | `text`, `markdown`, `html` |
| Crawl | every page's `text`, `markdown` and `html`, matched by URL | `text`, `markdown`, `html` |
| Extract | the captured text and lists | `captured-text`, `captured-list` |

For crawl robots, `result.changed_pages` and `diff["pages"]` also list which page URLs were `added`, `removed` or `changed`.

Crawl comparison is done by the SDK, because the Maxun server only compares scrape and extract runs. The result has the same shape either way. For crawl robots:

- `robot.get_run_diff(run_id)` works for any run, including scheduled ones.
- `has_changes` is filled in only for runs started with `robot.run()`.
- Webhook payloads and the Maxun dashboard do not show crawl changes.

## LLM settings: Cloud vs self-hosted

These features use an LLM:
- prompt extraction, `extract(url, prompt=...)`
- `documents.extract`
- the `summary` format
- Smart Queries

**Maxun Cloud** runs the LLM for you. Do not pass any `llm_*` argument; Cloud rejects them.

**Self-hosted Maxun** has no built-in model, so these features need an LLM configuration:

```python
robot = await maxun.extract(
    "https://shop.example.com",
    prompt="Product names and prices",
    llm_provider="anthropic",          # "anthropic", "openai" or "ollama"
    llm_api_key="sk-ant-...",          # required for anthropic and openai
    llm_model="...",                   # optional; the provider's default otherwise
    llm_base_url="...",                # optional; e.g. your Ollama or OpenAI-compatible server
)
```

The same four arguments are accepted by:
- `maxun.scrape(...)`, `maxun.crawl(...)` and `maxun.search(...)` (used for `summary` and Smart Queries)
- `documents.extract` and `documents.parse`

## Errors

Every API error is a `MaxunError` with `.status_code` and `.details`. More specific subclasses:

| Error | When |
|---|---|
| `AuthenticationError` | bad or missing API key (401/403) |
| `NotFoundError` | robot or run doesn't exist (404) |
| `ConflictError` | a robot with that name exists with different settings (409) |
| `ValidationError` | the server rejected the input (400) |
| `RunFailedError` | the run failed or was aborted |

Invalid arguments caught before any request (a bad format name, a missing URL) raise `ValueError`.

```python
from maxun import MaxunError, ConflictError

try:
    robot = await maxun.scrape("https://example.com/pricing", name="Pricing page")
except ConflictError:
    robot = await maxun.robots.find("Pricing page")
except MaxunError as e:
    print(e.status_code, e, e.details)
```

## Sync usage

`MaxunSync` has the same API without `await`. It works in scripts and in Jupyter.

```python
from maxun import MaxunSync

with MaxunSync() as maxun:
    robot = maxun.scrape("https://example.com")
    print(robot.run().markdown)

    robot = (
        maxun.extract("https://news.ycombinator.com")
        .capture_list({"selector": "tr.athing", "max_items": 10})
        .build()
    )
    print(robot.run().list_data)
```

## Upgrading from 0.0.x

Existing code keeps working. `Extract(Config(...))`, `Scrape(...)`, `Crawl(...)`, `Search(...)`, `await builder` and dict results are all still supported. Behaviour that changed:

- **Webhooks now fire.** The server's event names are `run_completed`/`run_failed`, but 0.0.x saved `run.completed`/`run.failed`, which never matched. Old names are translated with a warning. Webhooks you already saved with dotted names need to be added again.
- **Documents:** DOCX, JPG and PNG files were uploaded as PDFs and failed; they now work. Document methods raise `MaxunError` like everything else and are available as `maxun.documents` / `Documents(...)`.
- **`robot.run()`**
  - Waits for the run to finish instead of giving up after 5 minutes.
  - Accepts `formats=` and `smart_queries=`.
  - `params`/`webhook` were never used by the server; passing them now warns.
- **`Extract.get_robots()`** crashed with `KeyError`; it now works, and every resource has `list()`, `get()` and `delete()`.
- **Builder**
  - `scroll()` now takes a number of pages; the old `scroll(direction, distance)` did nothing.
  - `set_cookies()` and `mode()` were never supported by the server; they now warn and do nothing.
  - Steps added before `navigate()` raise an error.
- **`CrawlConfig`/`SearchConfig`** now have working defaults. Before, leaving out `limit` or `max_depth` crawled nothing.
- **`schedule()`, `add_webhook()` and `run()`** accept the `ScheduleConfig`, `WebhookConfig` and `ExecutionOptions` classes, not only camelCase dicts.
- **`Config`** reads `MAXUN_API_KEY`/`MAXUN_BASE_URL`/`MAXUN_TEAM_ID` when arguments are left out.
- **Return values:**
  - `robot.get_webhooks()` returns `[]` instead of `None` when there are none.
  - `robot.schedule()` returns the saved schedule and `robot.add_webhook()` returns the saved webhook; both used to return `None`.
- **Document formats:** `create_document_parse_robot` raises `ValueError` for unknown formats instead of silently dropping them.
- **Runs:** `robot.get_runs()`, `get_run()` and `get_latest_run()` return `Run` objects. A `Run` is still the raw dict underneath, so `run["runId"]`, `"status" in run` and `json.dumps(run)` work as before, but it prints as a short summary and adds `run.result`, `run.status`, `run.started_at` and the other summary attributes.
- **`print(robot)`** shows `Robot(id=..., name=..., type=...)`, and `Config` no longer prints the API key.
- **`from maxun import *`** exports only the public API, not `typing` helpers such as `Optional` or `List`.

## Examples

See [examples/](./examples).

## Requirements

- Python 3.8+
- `httpx >= 0.24.0`
- `python-dotenv >= 1.0.0` (only used by the examples)
