# Maxun Python SDK — Examples

Python equivalents of every Node SDK example.

## Setup

**1. Install the SDK** (from the `python-sdk/` directory):

```bash
pip install -e .
# With LLM support:
pip install -e ".[all]"
```

**2. Set environment variables** (copy `.env.example` to `.env` and fill in your values):

```bash
cp ../.env.example ../.env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `MAXUN_API_KEY` | Your Maxun API key (required) | — |
| `MAXUN_BASE_URL` | Base URL of your Maxun server | `https://app.maxun.dev/` |
| `MAXUN_TEAM_ID` | Team UUID for team-scoped robots (optional) | — |

**3. Run any example:**

```bash
python examples/basic_extraction.py
python examples/simple_scrape.py
python examples/basic_crawl.py
# ... etc.
```

## Examples

| File | Description | Node SDK equivalent |
|------|-------------|---------------------|
| [`basic_extraction.py`](./basic_extraction.py) | Extract specific fields with CSS selectors | [`basic-extraction.ts`](../../../maxun-sdks/examples/basic-extraction.ts) |
| [`simple_scrape.py`](./simple_scrape.py) | Scrape a page as Markdown, HTML, or screenshot | [`simple-scrape.ts`](../../../maxun-sdks/examples/simple-scrape.ts) |
| [`basic_crawl.py`](./basic_crawl.py) | Crawl multiple pages from a starting URL | [`basic-crawl.ts`](../../../maxun-sdks/examples/basic-crawl.ts) |
| [`basic_search.py`](./basic_search.py) | Search the web and collect results | [`basic-search.ts`](../../../maxun-sdks/examples/basic-search.ts) |
| [`chained_extract.py`](./chained_extract.py) | Multi-step: capture_text + capture_list on one page | [`chained-extract.ts`](../../../maxun-sdks/examples/chained-extract.ts) |
| [`list_pagination.py`](./list_pagination.py) | Extract lists with scroll / click pagination | [`list-pagination.ts`](../../../maxun-sdks/examples/list-pagination.ts) |
| [`llm_extraction.py`](./llm_extraction.py) | Use a natural-language prompt to build a robot | [`llm-extraction.ts`](../../../maxun-sdks/examples/llm-extraction.ts) |
| [`scheduling.py`](./scheduling.py) | Schedule robots for periodic execution | [`scheduling.ts`](../../../maxun-sdks/examples/scheduling.ts) |
| [`webhooks.py`](./webhooks.py) | Receive webhook notifications on run events | [`webhooks.ts`](../../../maxun-sdks/examples/webhooks.ts) |
| [`robot_management.py`](./robot_management.py) | List, update, inspect runs, and delete robots | [`robot-management.ts`](../../../maxun-sdks/examples/robot-management.ts) |
| [`complete_workflow.py`](./complete_workflow.py) | Full workflow: extract + webhook + schedule | [`complete-workflow.ts`](../../../maxun-sdks/examples/complete-workflow.ts) |
| [`form_fill_screenshot.py`](./form_fill_screenshot.py) | Fill form inputs and capture screenshots | [`form-fill-screenshot.ts`](../../../maxun-sdks/examples/form-fill-screenshot.ts) |
| [`team_robot.py`](./team_robot.py) | Create and run a robot scoped to a team | [`team-robot.ts`](../../../maxun-sdks/examples/team-robot.ts) |
