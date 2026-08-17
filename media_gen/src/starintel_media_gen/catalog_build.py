from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path


ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "starintel-social-presence/0.1 fictional-character routing catalog"


def _query(limit: int, offset: int) -> str:
    return f"""
SELECT ?item ?itemLabel ?altLabel ?universeLabel WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q95074 .
  ?item rdfs:label ?itemLabel .
  FILTER(LANG(?itemLabel) = \"en\")
  OPTIONAL {{ ?item skos:altLabel ?altLabel . FILTER(LANG(?altLabel) = \"en\") }}
  OPTIONAL {{
    ?item wdt:P1080 ?universe .
    ?universe rdfs:label ?universeLabel .
    FILTER(LANG(?universeLabel) = \"en\")
  }}
}}
ORDER BY ?item
LIMIT {limit}
OFFSET {offset}
""".strip()


def fetch_page(limit: int, offset: int) -> list[dict[str, str]]:
    params = urllib.parse.urlencode({"query": _query(limit, offset), "format": "json"})
    request = urllib.request.Request(
        f"{ENDPOINT}?{params}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = json.load(response)
    rows: list[dict[str, str]] = []
    for binding in raw["results"]["bindings"]:
        rows.append({key: value["value"] for key, value in binding.items()})
    return rows


def build_catalog(output: Path, *, batch_size: int = 5000, max_rows: int | None = None) -> int:
    grouped: dict[str, dict[str, object]] = defaultdict(lambda: {"aliases": set(), "universes": set()})
    offset = 0
    seen_rows = 0
    while True:
        remaining = None if max_rows is None else max_rows - seen_rows
        if remaining is not None and remaining <= 0:
            break
        limit = batch_size if remaining is None else min(batch_size, remaining)
        rows = fetch_page(limit, offset)
        if not rows:
            break
        for row in rows:
            item = row["item"]
            record = grouped[item]
            record["canonical"] = row["itemLabel"]
            if row.get("altLabel"):
                record["aliases"].add(row["altLabel"])
            if row.get("universeLabel"):
                record["universes"].add(row["universeLabel"])
        seen_rows += len(rows)
        offset += len(rows)
        if len(rows) < limit:
            break

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as handle:
        for item, raw in sorted(grouped.items()):
            universes = sorted(raw["universes"])
            payload = {
                "canonical": raw["canonical"],
                "aliases": sorted(raw["aliases"]),
                "universe": universes[0] if universes else "unknown",
                "source": "show",
                "wikidata": item,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return len(grouped)
