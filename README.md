# Daymark

Programmatic web search via the [Perplexity Search API](https://docs.perplexity.ai/api-reference/search-post)
(`POST https://api.perplexity.ai/search`) — ranked `title`/`url`/`snippet` results, no LLM answer.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
export PERPLEXITY_API_KEY=...   # create at https://console.perplexity.ai; never commit it
```

```python
from daymark import search_web
for r in search_web(["python 3.13 release notes", "python 3.13 JIT"], max_results=5, country="US"):
    print(r.title, r.url)
```

```bash
daymark-search "latest AI developments" -n 3 --recency week --domain -pinterest.com
```

Accepts up to 5 queries per call; results are deduped by URL. 429s are retried by the SDK
(honoring `Retry-After`) and surface as `SearchError` if retries are exhausted.

Checks: `ruff check . && mypy && pytest`
