from types import SimpleNamespace
from typing import Any

import httpx
import perplexity
import pytest

from daymark import SearchError, search_web


def _r(url: str, title: str = "t") -> SimpleNamespace:
    return SimpleNamespace(title=title, url=url, snippet="s", date=None, last_updated=None)


class FakeClient:
    def __init__(self, results: list[Any] | None = None, exc: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.search = SimpleNamespace(create=self._create)
        self._results, self._exc = results or [], exc

    def _create(self, **kw: Any) -> SimpleNamespace:
        self.calls.append(kw)
        if self._exc:
            raise self._exc
        return SimpleNamespace(results=self._results)


def test_dedupes_by_url_and_omits_unset_params() -> None:
    c = FakeClient([_r("https://a"), _r("https://b"), _r("https://a")])
    out = search_web(["q1", "q2"], client=c, country="US")  # type: ignore[arg-type]
    assert [r.url for r in out] == ["https://a", "https://b"]
    assert c.calls[0] == {"query": ["q1", "q2"], "max_results": 10, "country": "US"}


def test_single_query_sent_as_string() -> None:
    c = FakeClient([_r("https://a")])
    search_web("hello", client=c)  # type: ignore[arg-type]
    assert c.calls[0]["query"] == "hello"


BAD = [{"query": []}, {"query": ["x"] * 6}, {"query": "q", "max_results": 21}]


@pytest.mark.parametrize("kw", BAD)
def test_validation(kw: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        search_web(client=FakeClient(), **kw)  # type: ignore[arg-type]


def test_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    with pytest.raises(SearchError, match="PERPLEXITY_API_KEY"):
        search_web("q")


def test_rate_limit_maps_to_search_error() -> None:
    resp = httpx.Response(429, request=httpx.Request("POST", "https://api.perplexity.ai/search"))
    exc = perplexity.RateLimitError("rl", response=resp, body=None)
    with pytest.raises(SearchError) as ei:
        search_web("q", client=FakeClient(exc=exc))  # type: ignore[arg-type]
    assert ei.value.status == 429
