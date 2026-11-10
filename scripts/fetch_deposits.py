"""Verify or restore Goyal's pinned public deposit in the upstream collection."""

import argparse
import hashlib
import json
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def collect(upstream):
    manifest = upstream / "data/reference/goyal_9xpv4i/manifest.json"
    rows = json.loads(manifest.read_text())
    with requests.Session() as session:
        session.mount(
            "https://",
            HTTPAdapter(
                max_retries=Retry(
                    total=4,
                    backoff_factor=2,
                    status_forcelist=[429, 500, 502, 503, 504],
                )
            ),
        )
        for row in rows:
            path = upstream / row["path"]
            if path.exists():
                body = path.read_bytes()
            else:
                response = session.get(row["url"], timeout=(20, 90))
                response.raise_for_status()
                body = response.content
            if (
                len(body) != row["bytes"]
                or hashlib.sha256(body).hexdigest() != row["sha256"]
                or hashlib.md5(body).hexdigest() != row["md5"]
            ):
                raise ValueError(f"Deposit hash mismatch: {row['path']}")
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
    print(len(rows), "deposited originals verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upstream",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "local_elections",
    )
    collect(parser.parse_args().upstream)
