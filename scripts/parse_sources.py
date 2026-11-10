"""Validate source files and extract the printed ward inventories offline."""

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


def pdf_text(path):
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def candidate_inventory(text):
    if "Contesting Candidates" not in text or "2012" not in text:
        raise ValueError("Not a 2012 candidate list")
    wards = re.findall(r"Ward No & Name\s+(\d+)\s*-\s*(.*?)\s*\((G|W|SCW|SC)\)", text)
    if not wards or len(set(wards)) != 1:
        raise ValueError(f"Ambiguous ward header: {wards}")
    totals = re.findall(r"Total for this Ward\s*:[^\d]*(\d+)", text)
    if len(totals) != 1:
        raise ValueError(f"Ambiguous candidate total: {totals}")
    numbers = [int(n) for n in re.findall(r"^[ ]{0,10}(\d+)\s+\S", text, re.MULTILINE)]
    count = int(totals[0])
    if len(numbers) != count or len(set(numbers)) != count:
        raise ValueError(
            f"Candidate serial numbers {numbers} disagree with total {count}"
        )
    ward, name, reservation = wards[0]
    return {
        "ward": int(ward),
        "ward_name": name.strip(),
        "reservation": reservation,
        "candidate_count": count,
        "serial_numbers_contiguous": sorted(numbers) == list(range(1, count + 1)),
    }


def parse(root):
    manifest = [
        json.loads(line)
        for line in (root / "data/source_manifest.jsonl").read_text().splitlines()
    ]
    for row in manifest:
        data = (root / row["path"]).read_bytes()
        if (
            len(data) != row["bytes"]
            or hashlib.sha256(data).hexdigest() != row["sha256"]
        ):
            raise ValueError(f"Invalid source: {row['path']}")
    frame = json.loads((root / "data/frame.json").read_text())
    rows, unique = [], {}
    for source in frame:
        text = pdf_text(root / source["path"])
        row = candidate_inventory(text)
        if row["ward"] != source["ward"]:
            raise ValueError(f"Filename/printed ward mismatch: {source['path']}")
        if row["ward"] in unique and unique[row["ward"]] != row:
            raise ValueError(f"Conflicting files for ward {row['ward']}")
        unique[row["ward"]] = row.copy()
        rows.append(
            dict(
                year=2012,
                corporation=source["corporation"],
                **row,
                source_path=source["path"],
                source_url=source["url"],
            )
        )
    if set(unique) != set(range(1, 273)):
        raise ValueError("Incomplete ward coverage")
    output = root / "data/extracted/2012"
    output.mkdir(parents=True, exist_ok=True)
    with (output / "candidate_list_inventory.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    # The result report supplies an independent reservation check for each ward.
    text = pdf_text(root / "data/raw/2012/winner_runner_up.pdf")
    headers = re.findall(
        r"^\s*(\d+)\s*-\s*(.*?)\s*\((G|W|SCW|SC)\)",
        "\n".join(line[:33] for line in text.splitlines()),
        re.MULTILINE | re.DOTALL,
    )
    if len(headers) != 272 or {int(w) for w, _, _ in headers} != set(unique):
        raise ValueError("Incomplete winner report")
    for ward, _, reservation in headers:
        if unique[int(ward)]["reservation"] != reservation:
            raise ValueError(f"Reservation disagrees in ward {ward}")
    summary = {
        "year": 2012,
        "wards": len(unique),
        "candidate_list_files": len(frame),
        "candidates": sum(row["candidate_count"] for row in unique.values()),
        "reservations": dict(Counter(row["reservation"] for row in unique.values())),
        "winner_report_wards": len(headers),
        "sources_verified": len(manifest),
    }
    (output / "coverage.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parse(parser.parse_args().root)
