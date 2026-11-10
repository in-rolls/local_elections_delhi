"""Extract official Delhi results without combining ward identities across elections."""

import argparse
import itertools
import re
import subprocess
from pathlib import Path

import pandas as pd
import pdfplumber


def clean(value):
    return " ".join(str(value).split()) if value is not None else ""


def results_2017(path):
    records = []
    body = path.name.split("_")[0]
    boundaries = {
        "north": [92, 176.5, 248.8, 320, 359.2, 416.8, 485.1, 511.8, 556],
        "south": [92, 177.1, 248.2, 318.8, 357.2, 418.5, 485.8, 512.2, 556],
        "east": [92, 185.4, 254.6, 312.4, 350.7, 418.8, 486, 512.4, 556],
    }[body]
    with pdfplumber.open(path) as pdf:
        starts = []
        for i, page in enumerate(pdf.pages):
            for word in page.extract_words():
                match = re.fullmatch(r"\((\d+)-([NSE])\)", word["text"])
                if match and 90 < word["x0"] < 96:
                    starts.append((i, word["top"] - 1, f"{int(match[1])}-{match[2]}"))
        for idx, (first, top, ward) in enumerate(starts):
            last, bottom, _ = (
                starts[idx + 1]
                if idx + 1 < len(starts)
                else (len(pdf.pages) - 1, 810, None)
            )
            columns = []
            for left, right in itertools.pairwise(boundaries):
                pieces = []
                for page_no in range(first, last + 1):
                    lo = top if page_no == first else 60
                    hi = bottom if page_no == last else 810
                    chars = [
                        c
                        for c in pdf.pages[page_no].chars
                        if left <= c["x0"] < right and lo <= c["top"] < hi
                    ]
                    pieces.append(
                        pdfplumber.utils.extract_text(chars, x_tolerance=1) or ""
                    )
                columns.append(clean(" ".join(pieces)))
            match = re.fullmatch(r"\(\d+-[NSE]\)\s*(.*)", columns[0])
            if match is None:
                raise ValueError(columns)
            record = {
                "year": 2017,
                "ward": ward,
                "ward_name": match[1],
                "winner_name": columns[1],
                "winner_party": columns[2],
                "winner_votes": int(columns[3]),
                "runner_up_name": columns[4],
                "runner_up_party": columns[5],
                "runner_up_votes": int(columns[6]),
                "margin": int(columns[7]),
                "source_page": ";".join(str(i + 1) for i in range(first, last + 1)),
                "source_file": path.name,
            }
            if record["winner_votes"] - record["runner_up_votes"] != record["margin"]:
                raise ValueError(record)
            records.append(record)
    return pd.DataFrame(records)


def results_2022(path):
    records = []
    with pdfplumber.open(path) as pdf:
        starts = []
        for i, page in enumerate(pdf.pages):
            for word in page.extract_words():
                match = re.fullmatch(r"\((\d+)\)", word["text"])
                if match and 80 < word["x0"] < 87 and word["top"] > 77:
                    starts.append((i, word["top"] - 1, int(match[1])))
        if [s[2] for s in starts] != list(range(1, 251)):
            raise ValueError("2022 report does not enumerate 250 wards in order")
        for idx, (first_page, top, ward) in enumerate(starts):
            last_page, bottom, _ = (
                starts[idx + 1]
                if idx + 1 < len(starts)
                else (len(pdf.pages) - 1, 810, None)
            )
            columns = []
            boundaries = [80, 164, 209, 276, 340, 370, 434, 499, 537, 580]
            for left, right in itertools.pairwise(boundaries):
                pieces = []
                for page_no in range(first_page, last_page + 1):
                    lo = top if page_no == first_page else 77
                    hi = bottom if page_no == last_page else 810
                    if hi > lo:
                        chars = [
                            c
                            for c in pdf.pages[page_no].chars
                            if left <= c["x0"] < right and lo <= c["top"] < hi
                        ]
                        pieces.append(
                            pdfplumber.utils.extract_text(chars, x_tolerance=1) or ""
                        )
                columns.append(clean(" ".join(pieces)))
            label = re.fullmatch(r"\((\d+)\)\s*(.*)", columns[0])
            if label is None or int(label[1]) != ward:
                raise ValueError(columns)
            reservation = {"GEN": "G", "WOMEN": "W", "SC": "SC", "SC-WOMEN": "SCW"}.get(
                columns[1].replace(" ", "")
            )
            if reservation is None:
                raise ValueError(columns)
            record = {
                "year": 2022,
                "ward": str(ward),
                "ward_name": label[2],
                "reservation": reservation,
                "winner_name": columns[2],
                "winner_party": columns[3],
                "winner_votes": int(columns[4]),
                "runner_up_name": columns[5],
                "runner_up_party": columns[6],
                "runner_up_votes": int(columns[7]),
                "margin": int(columns[8]),
                "source_page": ";".join(
                    str(p + 1) for p in range(first_page, last_page + 1)
                ),
                "source_file": path.name,
            }
            if record["winner_votes"] - record["runner_up_votes"] != record["margin"]:
                raise ValueError(record)
            records.append(record)
    return pd.DataFrame(records)


def candidates_2007(path):
    raw = pd.read_excel(path, sheet_name="Detailed Result", header=None)
    records = []
    context = None
    for index, row in raw.iterrows():
        if pd.notna(row[1]) and pd.notna(row[7]) and isinstance(row[23], (int, float)):
            category = (
                clean(row[3])
                if pd.notna(row[3])
                else re.search(r"\((G|W|SCW|SC)\)", clean(row[2]))[1]
            )
            context = {
                "year": 2007,
                "ward": str(int(re.match(r"\d+", str(row[1]))[0])),
                "ward_name": re.sub(
                    r"^\s*-\s*|\s*\((?:G|W|SCW|SC)\)\s*$", "", clean(row[2])
                ),
                "reservation": category,
                "electors": int(row[9]),
                "reported_total_votes": int(row[21]),
            }
            rank = 0
        if context is None or pd.isna(row[23]) or pd.isna(row[7]) or pd.isna(row[8]):
            continue
        if not isinstance(row[23], (int, float)):
            continue
        rank += 1
        records.append(
            {
                **context,
                "rank": rank,
                "candidate_name": clean(row[7]),
                "party": clean(row[8]),
                "votes": int(row[23]),
                "source_row": index + 1,
            }
        )
    data = pd.DataFrame(records)
    if (
        set(data.ward) != {str(i) for i in range(1, 273)}
        or data.duplicated(["ward", "rank"]).any()
    ):
        raise ValueError("2007 ward coverage or candidate keys invalid")
    if not data.reservation.isin(["G", "W", "SC", "SCW"]).all():
        raise ValueError("Unknown reservation")
    if not data.groupby("ward").votes.apply(lambda x: x.is_monotonic_decreasing).all():
        raise ValueError("2007 results not sorted by votes")
    return data


def inventory_2017(root):
    records = []
    for body in ["north", "south", "east"]:
        path = root / f"data/raw/2017/{body}_candidates.pdf"
        text = subprocess.check_output(
            ["pdftotext", "-layout", str(path), "-"], text=True
        ).replace("\xad", "-")
        chunks = re.split(r"Ward No\.\s*(\d+)\s*-\s*([NSE])\s*\(Name\)", text)
        for i in range(1, len(chunks), 3):
            serials = [
                int(m[1])
                for m in re.finditer(r"^ {0,6}(\d+)\s+\S", chunks[i + 2], re.MULTILINE)
            ]
            if serials != list(range(1, len(serials) + 1)) or not serials:
                raise ValueError("Candidate serials incomplete")
            records.append(
                {
                    "ward": str(int(chunks[i])) + "-" + chunks[i + 1],
                    "candidate_count": len(serials),
                    "source_file": path.name,
                }
            )
    result = pd.DataFrame(records)
    if len(result) != 272 or result.ward.duplicated().any():
        raise ValueError("2017 candidate-list coverage invalid")
    return result


def detailed_2022(path):
    text = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    rows, totals = [], []
    ward = None
    for page, body in enumerate(text.split("\f"), 1):
        if "FORM 18 Report" not in body:
            continue
        for line in body.splitlines():
            heading = re.search(r"Ward No. and Name : (\d+) (.*)", line)
            if heading:
                ward = heading[1]
            row = re.match(r"^\s+(\d+)\s+(.+?)\s{2,}(\d+)\s*$", line)
            if row:
                rows.append(
                    {
                        "ward": ward,
                        "report_order": int(row[1]),
                        "row_text": row[2],
                        "votes_report": int(row[3]),
                        "report_page": page,
                    }
                )
            total = re.search(r"Total number of valid votes.*? (\d+)\s*$", line)
            if total and "Grand" not in line:
                totals.append(
                    {
                        "ward": ward,
                        "valid_votes_report": int(total[1]),
                        "report_page": page,
                    }
                )
    records, totals = pd.DataFrame(rows), pd.DataFrame(totals)
    records["is_nota"] = records.row_text.str.match(r"NOTA\s")
    if (
        len(records) != 1599
        or records.is_nota.sum() != 250
        or records.duplicated(["ward", "report_order"]).any()
        or len(totals) != 250
        or totals.ward.duplicated().any()
    ):
        raise ValueError("Incomplete detailed 2022 results")
    counts = records.groupby("ward").size()
    for ward, group in records.groupby("ward", sort=False):
        if list(group.report_order) != list(range(1, counts.loc[ward] + 1)):
            raise ValueError("Nonconsecutive detailed-result order")
    sums = records.groupby("ward").votes_report.sum()
    if not totals.ward.map(sums).eq(totals.valid_votes_report).all():
        raise ValueError("Detailed result rows do not reproduce printed totals")
    return records, totals


def main(root):
    for year, data in [
        (
            2017,
            pd.concat(
                [
                    results_2017(root / f"data/raw/2017/{body}_winner_runner_up.pdf")
                    for body in ["north", "south", "east"]
                ],
                ignore_index=True,
            ),
        ),
        (2022, results_2022(root / "data/raw/2022/winner_runner_up.pdf")),
    ]:
        target = root / f"data/extracted/{year}"
        target.mkdir(parents=True, exist_ok=True)
        if data.ward.duplicated().any():
            raise ValueError("Duplicate official ward")
        data.to_csv(target / "winner_runner_up.csv", index=False)
        print(year, len(data), "official winner records")
    details, totals = detailed_2022(root / "data/raw/2022/election_report_volume_2.pdf")
    details.to_csv(root / "data/extracted/2022/detailed_results.csv", index=False)
    totals.to_csv(root / "data/extracted/2022/ward_totals.csv", index=False)
    data = candidates_2007(root / "data/raw/2007/election_results.xls")
    target = root / "data/extracted/2007"
    target.mkdir(parents=True, exist_ok=True)
    data.to_parquet(target / "candidates.parquet", index=False)
    print(2007, len(data), "official candidates")
    inventory_2017(root).to_csv(
        root / "data/extracted/2017/candidate_inventory.csv", index=False
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    main(p.parse_args().root)
