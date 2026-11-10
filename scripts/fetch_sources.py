"""Collect the SEC's 2012 candidate lists and results, retaining source bytes."""

import argparse
import hashlib
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from wayback import Mode, WaybackClient, WaybackSession

BASE = "https://sec.delhi.gov.in"
LOCK = threading.Lock()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(v for k, v in attrs if k == "href" and v)


def links(body):
    parser = Links()
    parser.feed(body)
    return parser.links


def fetch(root, url, relative, kind, expected_sha256=None):
    path = root / relative
    ledger = root / "data/source_manifest.jsonl"
    with LOCK:
        cached_rows = ledger.read_text().splitlines() if ledger.exists() else []
    if cached_rows:
        for line in cached_rows:
            row = json.loads(line)
            if (
                row["url"] == url
                and row.get("requested_path", row["path"]) == relative
                and (root / row["path"]).exists()
            ):
                if (
                    hashlib.sha256((root / row["path"]).read_bytes()).hexdigest()
                    == row["sha256"]
                ):
                    return root / row["path"]
                raise ValueError(f"Source changed locally: {path}")
    session = requests.Session()
    retry = Retry(total=4, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    if url.startswith("https://web.archive.org/web/"):
        with WaybackClient(
            WaybackSession(retries=3, backoff=2, memento_calls_per_second=1)
        ) as client:
            response = client.get_memento(url, mode=Mode.original, exact=True)
        if response.status_code != 200:
            raise ValueError(f"Archived status {response.status_code}: {url}")
    else:
        response = session.get(url, timeout=(20, 90))
        response.raise_for_status()
    body = response.content
    session.close()
    if (
        expected_sha256 is not None
        and hashlib.sha256(body).hexdigest() != expected_sha256
    ):
        raise ValueError(f"Source differs from pinned snapshot: {url}")
    if kind == "pdf" and not body.startswith(b"%PDF"):
        raise ValueError(f"Not a PDF: {url}")
    if kind == "html" and b"<html" not in body.lower():
        raise ValueError(f"Not HTML: {url}")
    with LOCK:
        requested_path = relative
        if kind == "pdf" and ledger.exists():
            digest = hashlib.sha256(body).hexdigest()
            for line in ledger.read_text().splitlines():
                prior = json.loads(line)
                if prior["sha256"] == digest and (root / prior["path"]).exists():
                    relative = prior["path"]
                    path = root / relative
                    break
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        row = {
            "url": url,
            "response_url": response.url,
            "path": relative,
            "requested_path": requested_path,
            "kind": kind,
            "fetched_at": datetime.now(UTC).isoformat(),
            "status": response.status_code,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
        with ledger.open("a") as output:
            output.write(json.dumps(row) + "\n")
    return path


def collect(root):
    root.mkdir(parents=True, exist_ok=True)
    frame = []
    for corporation in ("north", "south", "east"):
        base = f"{BASE}/doit/tab-content/{corporation}-delhi-ward-list-2012"
        pending, seen = [base + "?page=0"], set()
        pdfs = set()
        while pending:
            url = pending.pop(0)
            if url in seen:
                continue
            seen.add(url)
            page = re.search(r"page=(\d+)", url)
            number = int(page[1]) if page else 0
            path = fetch(
                root, url, f"data/raw/2012/indexes/{corporation}_{number}.html", "html"
            )
            for href in links(path.read_text()):
                full = urljoin(url, href)
                if "/universal-tab/ward-" in full and full.endswith(".pdf"):
                    pdfs.add(full)
                if href.startswith("?page=") and full not in seen:
                    pending.append(full)
        for url in sorted(pdfs):
            match = re.search(r"ward-(\d+)-ward-list-(north|south|east)", url)
            if not match or match[2] != corporation:
                raise ValueError(url)
            ward = int(match[1])
            frame.append(
                {
                    "year": 2012,
                    "corporation": corporation,
                    "ward": ward,
                    "url": url,
                    "path": "data/raw/2012/candidates/" + url.rsplit("/", 1)[1],
                }
            )
        print(corporation, len(pdfs), "candidate-list PDFs", flush=True)
    if {r["ward"] for r in frame} != set(range(1, 273)):
        raise ValueError(f"Expected 272 unique wards, found {len(frame)} records")
    frame.sort(key=lambda r: r["ward"])
    (root / "data/frame.json").write_text(json.dumps(frame, indent=2) + "\n")
    with ThreadPoolExecutor(max_workers=3) as pool:
        for index, downloaded in enumerate(
            pool.map(lambda r: fetch(root, r["url"], r["path"], "pdf"), frame), 1
        ):
            frame[index - 1]["path"] = downloaded.relative_to(root).as_posix()
            if index % 25 == 0:
                print(
                    "Downloaded", index, "of", len(frame), "ward-list files", flush=True
                )
    (root / "data/frame.json").write_text(json.dumps(frame, indent=2) + "\n")
    fetch(
        root,
        BASE
        + "/sites/default/files/SEC/circulars-orders/notification-regarding-reservation-seats-2012_1.pdf",
        "data/raw/2012/reservation_order.pdf",
        "pdf",
    )
    fetch(
        root,
        BASE + "/sites/default/files/SEC/generic_multiple_files/2012winnerrunnerup.pdf",
        "data/raw/2012/winner_runner_up.pdf",
        "pdf",
    )
    fetch(
        root,
        BASE + "/sec/election-result-municipal-corporation-delhi-2012",
        "data/raw/2012/indexes/results.html",
        "html",
    )
    fetch(
        root,
        BASE + "/sec/list-contesting-candidates-2012",
        "data/raw/2012/indexes/candidates.html",
        "html",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Verify or restore every source in the pinned local ledger",
    )
    args = parser.parse_args()
    if args.restore:
        records = [
            json.loads(line)
            for line in (args.root / "data/source_manifest.jsonl")
            .read_text()
            .splitlines()
        ]
        for row in records:
            path = fetch(
                args.root,
                row["url"],
                row.get("requested_path", row["path"]),
                row["kind"],
                expected_sha256=row["sha256"],
            )
            if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                raise ValueError(f"Source differs from pinned snapshot: {row['url']}")
        print(len(records), "source receipts verified")
    else:
        collect(args.root)
