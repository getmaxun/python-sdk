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
        robot = await maxun.scrape.create("Example", "https://example.com")
        result = await robot.run()
        print(result.markdown)

asyncio.run(main())
```

Prefer no `async`? Use `MaxunSync`, which has the same methods without `await` (see [Sync usage](#sync-usage)).

## Contents

- [Setup](#setup)
- [What you can build](#what-you-can-build): [Scrape](#scrape) · [Extract with selectors](#extract-with-selectors) · [Extract with a prompt](#extract-with-a-prompt) · [Crawl](#crawl) · [Search](#search) · [Documents](#documents)
- [Running robots and reading results](#running-robots-and-reading-results)
- [Managing robots](#managing-robots): [Schedules](#schedules) · [Webhooks](#webhooks) · [Change monitoring](#change-monitoring)
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

| | Creates | Result is in |
|---|---|---|
| `maxun.scrape` | a robot that turns one page into markdown/html/text/links/summary/screenshots | `result.markdown`, `.html`, `.text`, `.links`, `.summary`, `.screenshots` |
| `maxun.extract` | a robot that captures specific data, by selectors or from a prompt | `result.text_data`, `result.list_data` |
| `maxun.crawl` | a robot that visits many pages of a site | `result.crawl_data` |
| `maxun.search` | a robot that searches the web (DuckDuckGo) | `result.search_data` |
| `maxun.documents` | a robot that reads a PDF, DOCX, XLSX, CSV, JPG or PNG | `result.document_data` or `result.markdown` etc. |
| `maxun.robots` | nothing; lists, finds and deletes robots of any type | |

Every `create` returns a `Robot`. Robots are saved on your account; run them as often as you like.

Robot names are unique. Creating a robot with a name that exists and **the same settings** returns the existing robot; different settings raise `ConflictError`.

## What you can build

### Scrape

```python
robot = await maxun.scrape.create(
    "Pricing page",
    "https://example.com/pricing",
    formats=["markdown", "links", "screenshot-fullpage"],
)
result = await robot.run()
result.markdown     # str
result.links        # list of URLs
result.screenshots  # list
```

Formats: `markdown` (default), `html`, `text`, `links`, `summary`, `screenshot-visible`, `screenshot-fullpage`.

**Smart Queries** ask an LLM a question about the page on every run:

```python
robot = await maxun.scrape.create("HN", "https://news.ycombinator.com",
                                  smart_queries="Which story has the most points?")
result = await robot.run()
result.smart_query_result

# or for a single run
result = await robot.run(smart_queries="List the three newest stories")
```

`summary` and Smart Queries use an LLM; see [LLM settings](#llm-settings-cloud-vs-self-hosted).

### Extract with selectors

Chain the steps and finish with `.build()`:

```python
robot = await (
    maxun.extract.create("Products")
    .navigate("https://shop.example.com")
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
.navigate(url)                        # go to a page (always first)
.click(selector)
.type(selector, text)                 # stored encrypted; input_type="password" etc. is auto-detected
.wait_for(selector, timeout=30000)    # milliseconds
.wait(1000)                           # milliseconds
.scroll(pages=2)                      # scroll down by screen heights
.capture_screenshot("name", full_page=False)
.monitor_changes()                    # see Change monitoring
```

`capture_list` also accepts `ExtractListConfig(selector=..., max_items=..., pagination=PaginationConfig(type="clickNext", selector=...))`.

### Extract with a prompt

Describe the data; Maxun builds the robot:

```python
robot = await maxun.extract.from_prompt(
    "Company names, descriptions and batch for the first 15 companies",
    url="https://www.ycombinator.com/companies",   # optional: without it Maxun searches for a page
    name="YC companies",
)
result = await robot.run()
result.list_data
```

### Crawl

```python
from maxun import CrawlConfig

robot = await maxun.crawl.create(
    "Docs crawler",
    "https://docs.example.com",
    CrawlConfig(mode="domain", limit=100, max_depth=3, include_paths=["/guides/*"]),
    formats=["markdown"],
)
result = await robot.run()
for page in result.crawl_data:
    print(page["metadata"]["url"])
```

`CrawlConfig` defaults: `mode="domain"` (or `"subdomain"`, `"path"`), `limit=50` pages, `max_depth=3`, `use_sitemap=True`, `follow_links=True`, `respect_robots=True`, no include/exclude patterns. `crawl_config` can be left out or given as a dict.

### Search

```python
from maxun import SearchConfig

robot = await maxun.search.create(
    "AI news",
    SearchConfig(query="AI model releases", mode="discover", time_range="week", limit=10),
)
result = await robot.run()
result.search_data
```

- `mode="discover"` returns titles, URLs and snippets.
- `mode="scrape"` (the default) also opens each result and scrapes it in `formats` (default `["markdown"]`).
- `time_range`: `"day"`, `"week"`, `"month"` or `"year"`. `limit` defaults to 10.
- Shorthand: `await maxun.search.create("AI news", "AI model releases")`.

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
| `list_data` (list) | `capture_list`, `from_prompt` |
| `crawl_data` (list, one item per page) | crawl robots |
| `search_data` (dict) | search robots |
| `document_data` | document-extract robots |
| `screenshots` (list) | screenshot formats and `capture_screenshot` |
| `has_changes`, `changed_formats` | robots with change monitoring |

`RunResult` is also a regular dict, so `result["data"]["listData"]` works too.

## Managing robots

```python
await maxun.robots.list()                  # all robots
await maxun.robots.list(type="crawl")      # one type: extract, scrape, crawl, search, doc-extract, doc-parse
await maxun.scrape.list()                  # same thing, from the resource
robot = await maxun.robots.get("robot-id")
robot = await maxun.robots.find("Pricing page")   # by exact name
await maxun.robots.delete("robot-id")
```

A `Robot` has `id`, `name`, `type`, `url`, `formats` and `is_monitoring`, plus:

```python
await robot.run()
await robot.get_runs()                 # newest first
await robot.get_latest_run()
await robot.get_run(run_id)
await robot.abort(run_id)              # a queued or running run

await robot.rename("New name")
await robot.set_list_limit(25)         # item limit of the list/crawl/search step
copy = await robot.duplicate("https://other-site.com/page")   # same robot, different URL
await robot.refresh()                  # reload from the server
await robot.delete()

robot.get_data()                       # the raw robot record
```

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

Compare every run with the previous successful run:

```python
robot = await maxun.scrape.create("Prices", "https://example.com/pricing", formats=["text"], monitor=True)
# or: await robot.set_monitoring(True)   /   builder: .monitor_changes()

result = await robot.run()
if result.has_changes:
    diff = await robot.get_run_diff(result.run_id)          # or format="text"
    for d in diff["diffs"]:
        for change in d["changes"]:
            if change["added"] or change["removed"]:
                print("+" if change["added"] else "-", change["value"])
```

## LLM settings: Cloud vs self-hosted

These features use an LLM:
- `extract.from_prompt`
- `documents.extract`
- the `summary` format
- Smart Queries

**Maxun Cloud** runs the LLM for you. Do not pass any `llm_*` argument; Cloud rejects them.

**Self-hosted Maxun** has no built-in model, so these features need an LLM configuration:

```python
robot = await maxun.extract.from_prompt(
    "Product names and prices",
    url="https://shop.example.com",
    llm_provider="anthropic",          # "anthropic", "openai" or "ollama"
    llm_api_key="sk-ant-...",          # required for anthropic and openai
    llm_model="...",                   # optional; the provider's default otherwise
    llm_base_url="...",                # optional; e.g. your Ollama or OpenAI-compatible server
)
```

The same four arguments are accepted by:
- `scrape.create`, `crawl.create` and `search.create` (used for `summary` and Smart Queries)
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
    robot = await maxun.scrape.create("Pricing page", "https://example.com/pricing")
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
    robot = maxun.scrape.create("Example", "https://example.com")
    print(robot.run().markdown)

    robot = (
        maxun.extract.create("HN")
        .navigate("https://news.ycombinator.com")
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

## Examples

See [examples/](./examples).

## Requirements

- Python 3.8+
- `httpx >= 0.24.0`
- `python-dotenv >= 1.0.0` (only used by the examples)
