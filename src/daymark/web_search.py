"""Web search via the Perplexity Search API (``POST https://api.perplexity.ai/search``).

Returns ranked, structured results (no LLM answer). The API key is read from the
``PERPLEXITY_API_KEY`` environment variable by the SDK and is never logged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

import perplexity
from perplexity import Perplexity

MAX_QUERIES = 5
MAX_RESULTS_LIMIT = 20  # web search; values above 20 are people-search only

SearchType = Literal["web", "fast"]
Recency = Literal["hour", "day", "week", "month", "year"]


class SearchError(Exception):
    """Raised for any failed search; ``status`` is the HTTP status when known."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    date: str | None = None
    last_updated: str | None = None


def search_web(
    query: str | list[str],
    *,
    max_results: int = 10,
    country: str | None = None,
    search_type: SearchType | None = None,
    search_context_size: Literal["low", "medium", "high"] | None = None,
    max_tokens: int | None = None,
    max_tokens_per_page: int | None = None,
    search_domain_filter: list[str] | None = None,
    search_language_filter: list[str] | None = None,
    search_recency_filter: Recency | None = None,
    search_after_date_filter: str | None = None,
    search_before_date_filter: str | None = None,
    last_updated_after_filter: str | None = None,
    last_updated_before_filter: str | None = None,
    client: Perplexity | None = None,
) -> list[SearchResult]:
    """Search the web. ``query`` may be one string or up to five; results are deduped by URL.

    Dates use MM/DD/YYYY. ``search_domain_filter`` is an allowlist, or a denylist when every
    entry is prefixed with ``-`` (max 20, not both).
    """
    queries = [query] if isinstance(query, str) else list(query)
    if not 1 <= len(queries) <= MAX_QUERIES or not all(q.strip() for q in queries):
        raise ValueError(f"provide 1-{MAX_QUERIES} non-empty queries")
    if not 1 <= max_results <= MAX_RESULTS_LIMIT:
        raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")
    if client is None and not os.environ.get("PERPLEXITY_API_KEY"):
        raise SearchError(
            "PERPLEXITY_API_KEY is not set. Create a key at https://console.perplexity.ai "
            "and export it in your shell."
        )

    optional: dict[str, Any] = {
        "country": country,
        "search_type": search_type,
        "search_context_size": search_context_size,
        "max_tokens": max_tokens,
        "max_tokens_per_page": max_tokens_per_page,
        "search_domain_filter": search_domain_filter,
        "search_language_filter": search_language_filter,
        "search_recency_filter": search_recency_filter,
        "search_after_date_filter": search_after_date_filter,
        "search_before_date_filter": search_before_date_filter,
        "last_updated_after_filter": last_updated_after_filter,
        "last_updated_before_filter": last_updated_before_filter,
    }
    params = {k: v for k, v in optional.items() if v is not None}

    # The SDK retries 429/5xx with backoff (honoring Retry-After); fall back to it on exhaustion.
    api = client or Perplexity(max_retries=3)
    try:
        response = api.search.create(
            query=queries[0] if len(queries) == 1 else queries,
            max_results=max_results,
            **params,
        )
    except perplexity.AuthenticationError as e:
        raise SearchError("Authentication failed (401): check PERPLEXITY_API_KEY", 401) from e
    except perplexity.RateLimitError as e:
        raise SearchError("Rate limited (429) after retries; try again later", 429) from e
    except perplexity.APIStatusError as e:
        raise SearchError(f"Search API error ({e.status_code})", e.status_code) from e
    except perplexity.APIConnectionError as e:
        raise SearchError("Could not reach the Perplexity API") from e

    return dedupe(_flatten(response.results))


def _flatten(items: list[Any]) -> list[SearchResult]:
    """Normalize results; multi-query responses may nest one list per query."""
    out: list[SearchResult] = []
    for item in items:
        if isinstance(item, list):
            out.extend(_flatten(item))
        else:
            out.append(
                SearchResult(
                    title=item.title,
                    url=item.url,
                    snippet=item.snippet,
                    date=getattr(item, "date", None),
                    last_updated=getattr(item, "last_updated", None),
                )
            )
    return out


def dedupe(results: list[SearchResult]) -> list[SearchResult]:
    """Drop repeated URLs, keeping first (highest-ranked) occurrence."""
    seen: set[str] = set()
    unique: list[SearchResult] = []
    for r in results:
        if r.url not in seen:
            seen.add(r.url)
            unique.append(r)
    return unique
