# Maxun Python SDK

The official Python SDK for [Maxun](https://maxun.dev) — turn any website into an API.

Works with both Maxun Cloud and Maxun Open Source.

## What can you do with Maxun SDK?

- Extract structured data from any website
- Scrape entire pages as Markdown or HTML
- Crawl multiple pages automatically to discover and scrape content
- Perform web searches and extract results as metadata or full content
- Use AI to extract data with natural language prompts
- Capture screenshots (visible area or full page)
- Automate workflows with clicks, form fills, and navigation
- Schedule recurring jobs to keep your data fresh
- Get webhooks when extractions complete
- Handle pagination automatically (scroll, click, load more)

## Installation

```bash
pip install maxun
```

With LLM support:

```bash
pip install "maxun[anthropic]"   # Anthropic Claude
pip install "maxun[openai]"      # OpenAI GPT
pip install "maxun[all]"         # All LLM providers
```

## Local Development

Dependencies are declared in `pyproject.toml`.

To install the SDK locally in editable mode:

```bash
cd python-sdk
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .               # core only
pip install -e ".[all]"        # core + all LLM providers
```

## Configuration

```python
from maxun import Config

config = Config(
    api_key="your-api-key",            # Required
    base_url="https://app.maxun.dev/api/sdk/",  # Optional, defaults to localhost
    team_id="your-team-uuid",          # Optional, for team-scoped robots
)
```

Environment variables are supported via a `.env` file (uses `python-dotenv`):

```
MAXUN_API_KEY=your-api-key
MAXUN_BASE_URL=https://app.maxun.dev/api/sdk/
MAXUN_TEAM_ID=your-team-uuid
```

## Core Classes

### Scrape

Scrape full pages as Markdown, HTML, or screenshots.

```python
from maxun import Scrape, Config

scraper = Scrape(Config(api_key="..."))

robot = await scraper.create(
    "Page Scraper",
    "https://example.com",
    formats=["markdown", "html"],
)

result = await robot.run()
print(result["data"]["markdown"])
```

Available formats: `"markdown"`, `"html"`, `"screenshot-visible"`, `"screenshot-fullpage"`

### Crawl

Crawl multiple pages starting from a URL.

```python
from maxun import Crawl, CrawlConfig, Config

crawler = Crawl(Config(api_key="..."))

robot = await crawler.create(
    "Site Crawler",
    "https://example.com",
    CrawlConfig(
        mode="domain",       # "domain" | "subdomain" | "path"
        limit=50,
        max_depth=3,
        use_sitemap=True,
        follow_links=True,
        respect_robots=True,
    ),
)

result = await robot.run()
```

### Search

Search the web and collect results.

```python
from maxun import Search, SearchConfig, Config

searcher = Search(Config(api_key="..."))

robot = await searcher.create(
    "AI News Search",
    SearchConfig(
        query="artificial intelligence 2025",
        mode="discover",     # "discover" | "scrape"
        limit=10,
    ),
)

result = await robot.run()
```

### Extract

Build robots that extract structured data from pages.

```python
from maxun import Extract, Config

extractor = Extract(Config(api_key="..."))

# Capture specific text fields
robot = await (
    extractor
    .create("My Robot")
    .navigate("https://example.com")
    .capture_text({"Title": "h1", "Price": ".price"})
)

# Capture a list of items with optional pagination
robot = await (
    extractor
    .create("Product List")
    .navigate("https://shop.example.com")
    .capture_list({
        "selector": "article.product",
        "pagination": {"type": "clickNext", "selector": "a.next"},
        "maxItems": 100,
    })
)

result = await robot.run()
```

### LLM Extraction

Use a natural language prompt to extract data.

```python
from maxun import Extract, Config

extractor = Extract(Config(api_key="..."))

robot = await extractor.extract(
    prompt="Extract the product name, price, and rating",
    url="https://shop.example.com/product/123",
    llm_provider="anthropic",
    llm_model="claude-3-5-sonnet-20241022",
    llm_api_key="your-anthropic-key",
)

result = await robot.run()
```

## Robot Management

All robot types return a `Robot` instance with a consistent API:

```python
# Run the robot
result = await robot.run()

# Schedule recurring runs
await robot.schedule({
    "runEvery": 1,
    "runEveryUnit": "DAYS",
    "timezone": "UTC",
})

# Add a webhook
await robot.add_webhook({
    "url": "https://your-server.com/webhook",
    "events": ["run.completed", "run.failed"],
})

# Get execution history
runs = await robot.get_runs()
latest = await robot.get_latest_run()
specific = await robot.get_run("run-id")

# Update metadata or workflow
await robot.update({"meta": {"name": "New Name"}})
await robot.refresh()   # reload from server

# Delete
await robot.delete()
```

### Scheduling

```python
from maxun import ScheduleConfig

await robot.schedule({
    "runEvery": 6,
    "runEveryUnit": "HOURS",   # MINUTES | HOURS | DAYS | WEEKS | MONTHS
    "timezone": "America/New_York",
})

# Stop scheduling
await robot.unschedule()

# Read current schedule
schedule = robot.get_schedule()
```

### Webhooks

```python
await robot.add_webhook({
    "url": "https://your-server.com/webhook",
    "events": ["run.completed", "run.failed"],
})

webhooks = robot.get_webhooks()
await robot.remove_webhooks()
```

## Error Handling

```python
from maxun import MaxunError

try:
    result = await robot.run()
except MaxunError as e:
    print(f"Error {e.status_code}: {e}")
    print(f"Details: {e.details}")
```

## Types Reference

| Type | Description |
|------|-------------|
| `Config` | SDK configuration (api_key, base_url, team_id) |
| `CrawlConfig` | Crawl robot configuration |
| `SearchConfig` | Search robot configuration |
| `ScheduleConfig` | Schedule configuration |
| `WebhookConfig` | Webhook configuration |
| `ExtractListConfig` | List capture configuration |
| `PaginationConfig` | Pagination strategy |
| `MaxunError` | SDK exception with status_code and details |

## Examples

See the [examples/](./examples) directory for complete working examples.

## Requirements

- Python 3.8+
- `httpx >= 0.24.0`
- `python-dotenv >= 1.0.0`
- Optional: `anthropic >= 0.18.0`, `openai >= 1.0.0`
