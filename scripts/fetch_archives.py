"""Search and retrieve SEC captures with the wayback client used by piedomains."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from fetch_sources import fetch
from wayback import WaybackClient, WaybackSession


def discover(root):
    records = {}
    with WaybackClient(
        WaybackSession(retries=3, backoff=2, search_calls_per_second=1)
    ) as client:
        for extra in ["urlkey:.*2012.*", "mimetype:application/pdf"]:
            for row in client.search(
                "sec.delhigovt.nic.in/*",
                filter_field=["statuscode:200", extra],
                collapse="urlkey",
            ):
                record = row._asdict()
                record["timestamp"] = row.timestamp.strftime("%Y%m%d%H%M%S")
                records[row.original] = record
    result = {
        "searched_at": datetime.now(UTC).isoformat(),
        "domain": "sec.delhigovt.nic.in",
        "records": list(records.values()),
    }
    (root / "data/archive_search.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        len(records),
        "distinct archived URLs; review before adding captures to archive_frame.json",
    )


def collect(root):
    frame = json.loads((root / "data/archive_frame.json").read_text())
    for row in frame:
        path = fetch(root, row["url"], row["path"], row["kind"])
        if path.relative_to(root).as_posix() != row["path"]:
            raise ValueError(
                "Update the archive frame with the deduplicated source path"
            )
    print("Archived captures verified:", len(frame))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--discover", action="store_true")
    args = parser.parse_args()
    if args.discover:
        discover(args.root)
    else:
        collect(args.root)
