"""Extract winner and runner-up columns from the official 18-page report."""

import argparse
import re
from pathlib import Path

import pandas as pd
import pdfplumber


def parse(path):
    records = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            words = page.extract_words()
            starts = [
                w
                for w in words
                if w["x0"] < 55 and w["top"] > 95 and w["text"].isdigit()
            ]
            for i, start in enumerate(starts):
                end = starts[i + 1]["top"] - 4 if i + 1 < len(starts) else 560
                row_words = [w for w in words if start["top"] - 4 <= w["top"] < end]
                columns = []
                for left, right in zip(
                    [0, 185, 299, 425, 473, 581, 710, 755],
                    [185, 299, 425, 473, 581, 710, 755, 842],
                ):
                    columns.append(
                        " ".join(
                            w["text"] for w in row_words if left <= w["x0"] < right
                        )
                    )
                ward = re.fullmatch(r"(\d+)\s*-\s*(.*?)\s*\((G|W|SCW|SC)\)", columns[0])
                if ward is None:
                    raise ValueError((number, columns))
                winner_votes, runner_votes, margin = (
                    int(columns[n]) for n in [3, 6, 7]
                )
                if winner_votes - runner_votes != margin:
                    raise ValueError((number, columns))
                records.append(
                    {
                        "year": 2012,
                        "ward": int(ward[1]),
                        "ward_name": ward[2],
                        "reservation": ward[3],
                        "winner_name": columns[1],
                        "winner_party": columns[2],
                        "winner_votes": winner_votes,
                        "runner_up_name": columns[4],
                        "runner_up_party": columns[5],
                        "runner_up_votes": runner_votes,
                        "margin": margin,
                        "pdf_page": number,
                    }
                )
    result = pd.DataFrame(records)
    if len(result) != 272 or set(result.ward) != set(range(1, 273)):
        raise ValueError("Winner coverage incomplete")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    root = parser.parse_args().root
    data = parse(root / "data/raw/2012/winner_runner_up.pdf")
    data.to_csv(root / "data/extracted/2012/winner_runner_up.csv", index=False)
    print(len(data), "wards; all vote margins verified")
