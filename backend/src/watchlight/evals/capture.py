from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from watchlight.collector.content_guard import ContentKind, classify
from watchlight.collector.fetch import HttpxFetchClient, is_safe_public_url
from watchlight.collector.robots import RobotsCache

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9.-]+")


async def capture(urls: list[str], output_dir: Path) -> list[dict[str, object]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    client = HttpxFetchClient()
    robots = RobotsCache(client)
    captured: list[dict[str, object]] = []
    for url in urls:
        if not is_safe_public_url(url):
            raise ValueError(f"only public HTTP(S) URLs may be captured: {url}")
        if not await robots.is_allowed(url):
            raise PermissionError(f"robots.txt disallows capture: {url}")
        response = await client.fetch(url)
        kind = classify(response.text, response.status_code)
        if kind is not ContentKind.TARGET:
            raise ValueError(f"content guard classified {url} as {kind.value}")
        captured_at = int(datetime.now(tz=UTC).timestamp())
        timestamp = datetime.fromtimestamp(captured_at, tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        host = _SAFE_NAME.sub("-", urlparse(url).hostname or "source").strip("-")
        digest = hashlib.sha256(response.text.encode()).hexdigest()
        snapshot_path = output_dir / f"{host}-{timestamp}-{digest[:10]}.html"
        snapshot_path.write_text(response.text, encoding="utf-8")
        record: dict[str, object] = {
            "url": url,
            "captured_at": captured_at,
            "http_status": response.status_code,
            "content_sha256": digest,
            "snapshot_path": snapshot_path.name,
        }
        captured.append(record)
    manifest = output_dir / "captures.jsonl"
    with manifest.open("a", encoding="utf-8") as handle:
        for record in captured:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return captured


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture reproducible public web snapshots")
    parser.add_argument("--url", action="append", required=True, dest="urls")
    parser.add_argument("--output-dir", type=Path, default=Path("evals/captures"))
    args = parser.parse_args()
    records = asyncio.run(capture(args.urls, args.output_dir))
    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
