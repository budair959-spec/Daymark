from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from daymark.web_search import SearchError, search_web


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="daymark-search", description="Perplexity web search")
    p.add_argument("query", nargs="+", help="1-5 queries (quote each)")
    p.add_argument("-n", "--max-results", type=int, default=10)
    p.add_argument("--country", help="ISO 3166-1 alpha-2 code")
    p.add_argument("--domain", action="append", help="allow domain; prefix '-' to exclude")
    p.add_argument("--recency", choices=["hour", "day", "week", "month", "year"])
    args = p.parse_args(argv)
    try:
        results = search_web(
            args.query,
            max_results=args.max_results,
            country=args.country,
            search_domain_filter=args.domain,
            search_recency_filter=args.recency,
        )
    except (SearchError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    json.dump([asdict(r) for r in results], sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
