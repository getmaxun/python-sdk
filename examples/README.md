# Examples

## Setup

From the repository root:

```bash
pip install -e .
cp .env.example .env    # then fill in MAXUN_API_KEY (and MAXUN_BASE_URL if self-hosted)
python examples/simple_scrape.py
```

| Variable | Description | Default |
|---|---|---|
| `MAXUN_API_KEY` | Your Maxun API key (required) | — |
| `MAXUN_BASE_URL` | SDK API URL | `https://app.maxun.dev/api/sdk/` (Cloud). Self-hosted: `http://localhost:8080/api/sdk/` |
| `MAXUN_TEAM_ID` | Team for team-scoped robots (Cloud) | — |

On self-hosted Maxun, the LLM features (prompt extraction, document extraction, `summary`, Smart Queries) also need an LLM: see `llm_extraction.py`.

## Files

| File | Shows |
|---|---|
| [`simple_scrape.py`](./simple_scrape.py) | One page as Markdown, text and a screenshot |
| [`smart_queries.py`](./smart_queries.py) | Asking an LLM a question about a page on each run |
| [`basic_extraction.py`](./basic_extraction.py) | Capturing fields with CSS selectors |
| [`list_pagination.py`](./list_pagination.py) | Lists across pages; changing the item limit |
| [`chained_extract.py`](./chained_extract.py) | Text and a list from the same page |
| [`form_fill_screenshot.py`](./form_fill_screenshot.py) | Typing into a form and taking screenshots |
| [`llm_extraction.py`](./llm_extraction.py) | Building a robot from a plain-English prompt |
| [`basic_crawl.py`](./basic_crawl.py) | Crawling part of a site |
| [`basic_search.py`](./basic_search.py) | Web search in discover and scrape mode |
| [`documents.py`](./documents.py) | Extracting from and converting PDF/DOCX/XLSX/CSV/images |
| [`monitoring.py`](./monitoring.py) | Detecting changes between runs |
| [`scheduling.py`](./scheduling.py) | Hourly, weekly and monthly schedules |
| [`webhooks.py`](./webhooks.py) | Notifications when runs complete or fail |
| [`robot_management.py`](./robot_management.py) | Listing, finding, renaming, copying and deleting robots |
| [`team_robot.py`](./team_robot.py) | Robots in a team workspace |
| [`complete_workflow.py`](./complete_workflow.py) | A scheduled, monitored list robot with a webhook |
| [`sync_usage.py`](./sync_usage.py) | The SDK without async/await |
