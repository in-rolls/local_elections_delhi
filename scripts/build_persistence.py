"""Build the documented same-ward 2007–2012 comparison; reject other pairs."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from build_cycles import verify_sources
from parse_sources import pdf_text

LINK_SOURCE = "data/raw/2012/reservation_order.pdf"
FIELDS = [
    ("year", pa.int16(), False, "Outcome election year: 2012."),
    ("prior_year", pa.int16(), False, "Prior reservation election year: 2007."),
    ("ward_no", pa.string(), False, "Outcome-election ward identifier."),
    ("prior_ward_no", pa.string(), False, "Prior-election ward identifier."),
    (
        "body",
        pa.string(),
        False,
        "2012 municipal corporation, from the SEC candidate-list frame.",
    ),
    ("prior_body", pa.string(), False, "Municipal Corporation of Delhi in 2007."),
    (
        "ward_name",
        pa.string(),
        False,
        "2012 ward name, as printed in the SEC result report.",
    ),
    (
        "prior_ward_name",
        pa.string(),
        False,
        "2007 ward name, as printed in the SEC spreadsheet.",
    ),
    (
        "link_basis",
        pa.string(),
        False,
        "The 2012 order distributes the existing 2007 wards among three corporations.",
    ),
    (
        "link_source_path",
        pa.string(),
        False,
        "Repository-relative continuity notification.",
    ),
    (
        "link_source_page",
        pa.int16(),
        False,
        "One-based physical PDF page establishing continuity.",
    ),
    (
        "link_source_sha256",
        pa.string(),
        False,
        "SHA-256 of the continuity notification.",
    ),
    ("reserved_raw", pa.string(), False, "2012 recorded category: G/W/SC/SCW."),
    ("prior_reserved_raw", pa.string(), False, "2007 recorded category: G/W/SC/SCW."),
    (
        "reserved_woman",
        pa.int8(),
        True,
        "2012 women quota: 1=yes, 0=no; independent of winner sex.",
    ),
    (
        "prior_reserved_woman",
        pa.int8(),
        True,
        "2007 women quota: 1=yes, 0=no; independent of winner sex.",
    ),
    ("reserved_caste", pa.string(), False, "2012 caste quota: NONE or SC."),
    ("prior_reserved_caste", pa.string(), False, "2007 caste quota: NONE or SC."),
    ("winner", pa.string(), False, "2012 winner name from the SEC result report."),
    (
        "winner_woman_raw",
        pa.string(),
        False,
        "Unchanged Goyal winner sex code: F or M.",
    ),
    (
        "winner_woman",
        pa.int8(),
        True,
        "Selected 2012 winner sex: 1=female, 0=male, null=unresolved.",
    ),
    (
        "winner_woman_source",
        pa.string(),
        False,
        "Selected winner sex source recorded by the 2012 release.",
    ),
    (
        "winner_woman_decision",
        pa.string(),
        False,
        "source_retained, correct, or unresolved; no name/quota inference.",
    ),
    (
        "winner_woman_review_url",
        pa.string(),
        True,
        "Evidence URL from the pinned sex-review ledger, if reviewed.",
    ),
    (
        "winner_woman_review_evidence",
        pa.string(),
        True,
        "Verbatim evidence note from the pinned sex-review ledger.",
    ),
    (
        "reserved_source_path",
        pa.string(),
        False,
        "2012 official result report supporting reservation and winner identity.",
    ),
    (
        "reserved_source_page",
        pa.int16(),
        False,
        "One-based physical 2012 result-report page.",
    ),
    (
        "reserved_source_sha256",
        pa.string(),
        False,
        "SHA-256 of the official 2012 result report.",
    ),
    (
        "prior_reserved_source_path",
        pa.string(),
        False,
        "2007 SEC election spreadsheet.",
    ),
    (
        "prior_reserved_source_row",
        pa.int32(),
        False,
        "One-based spreadsheet winner row; Detailed Result sheet.",
    ),
    (
        "prior_reserved_source_sha256",
        pa.string(),
        False,
        "SHA-256 of the official 2007 spreadsheet.",
    ),
]
SCHEMA = pa.schema([pa.field(n, t, nullable=v) for n, t, v, _ in FIELDS])
LINK_FIELDS = [n for n, _, _, _ in FIELDS[:12]]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_pair(prior_year, year):
    if (prior_year, year) != (2007, 2012):
        raise ValueError("No validated same-ward link for this election pair")


def validate(table):
    if not table.schema.equals(SCHEMA):
        raise ValueError("Incorrect persistence Arrow schema")
    d = table.to_pandas()
    if (
        len(d) != 272
        or d.ward_no.duplicated().any()
        or d.prior_ward_no.duplicated().any()
    ):
        raise ValueError(
            "Persistence join must preserve 272 unique wards on both sides"
        )
    if (
        set(d.ward_no) != {str(i) for i in range(1, 273)}
        or not d.ward_no.eq(d.prior_ward_no).all()
    ):
        raise ValueError("Invalid documented 2007–2012 identity link")
    if not d.year.eq(2012).all() or not d.prior_year.eq(2007).all():
        raise ValueError("Unexpected election pair")
    for prefix in ["", "prior_"]:
        raw = d[prefix + "reserved_raw"]
        if not raw.isin(["G", "W", "SC", "SCW"]).all():
            raise ValueError("Unknown reservation category")
        if (
            not d[prefix + "reserved_woman"]
            .eq(raw.isin(["W", "SCW"]).astype(int))
            .all()
        ):
            raise ValueError("Quota flag does not match source reservation")
        if (
            not d[prefix + "reserved_caste"]
            .eq(raw.map({"G": "NONE", "W": "NONE", "SC": "SC", "SCW": "SC"}))
            .all()
        ):
            raise ValueError("Caste quota does not match source reservation")
    retained = d.winner_woman_decision.eq("source_retained")
    if (
        not d.loc[retained, "winner_woman"]
        .eq(d.loc[retained, "winner_woman_raw"].map({"F": 1, "M": 0}))
        .all()
    ):
        raise ValueError("Unreviewed winner sex changed")
    if set(d.loc[d.winner_woman.isna(), "ward_no"]) != {"115"}:
        raise ValueError("Unresolved winner must remain missing")
    if d.set_index("ward_no").loc[["111", "254"], "winner_woman"].tolist() != [1, 0]:
        raise ValueError("Documented sex corrections lost")


def build(root, upstream, output=None):
    require_pair(2007, 2012)
    verify_sources(root, upstream)
    for year in [2007, 2012]:
        checks = json.loads((root / f"data/release/{year}/checksums.json").read_text())
        for path, expected in checks.items():
            if digest(root / path) != expected:
                raise ValueError(f"Election release changed: {path}")
    text = " ".join(pdf_text(root / LINK_SOURCE).split())
    if not all(
        x in text
        for x in [
            "7(367)/80/2002/UD/2141",
            "7th February, 2007",
            "these 272 Wards have been distributed",
        ]
    ):
        raise ValueError("Continuity notification does not establish the adopted link")
    prior = pd.read_parquet(root / "data/release/2007/winners.parquet")
    current = pd.read_parquet(root / "data/release/2012/winners.parquet")
    prior["ward"] = prior.ward.astype(str)
    current["ward"] = current.ward.astype(str)
    official = pd.read_csv(
        root / "data/extracted/2012/winner_runner_up.csv", dtype={"ward": str}
    ).set_index("ward")
    frame = pd.DataFrame(json.loads((root / "data/frame.json").read_text()))
    frame["ward"] = frame.ward.astype(str)
    frame = frame[["ward", "corporation"]].drop_duplicates()
    if frame.ward.duplicated().any() or frame.corporation.value_counts().to_dict() != {
        "north": 104,
        "south": 104,
        "east": 64,
    }:
        raise ValueError("SEC corporation membership frame is ambiguous")
    review_path = upstream / "data/delhi/interim/sex_review.csv"
    review = pd.read_csv(review_path, dtype={"ward": str}).set_index("ward")
    joined = prior.merge(
        current,
        on="ward",
        validate="one_to_one",
        how="outer",
        suffixes=("_prior", "_current"),
        indicator=True,
    )
    if len(joined) != 272 or not joined._merge.eq("both").all():
        raise ValueError("Election join is incomplete")
    joined = joined.merge(frame, on="ward", validate="one_to_one")
    records = []
    for r in joined.sort_values("ward", key=lambda s: s.astype(int)).itertuples():
        ward = r.ward
        decision = (
            review.loc[ward, "decision"] if ward in review.index else "source_retained"
        )
        if (
            ward in review.index
            and review.loc[ward, "source_gender"] != r.sex_raw_goyal_current
        ):
            raise ValueError("Sex review no longer matches the original winner")
        if (
            official.loc[ward, "reservation"] != r.reservation_current
            or official.loc[ward, "winner_votes"] != r.votes_current
        ):
            raise ValueError("Outcome release does not match official result")
        records.append(
            {
                "year": 2012,
                "prior_year": 2007,
                "ward_no": ward,
                "prior_ward_no": ward,
                "body": r.corporation.title() + " Delhi Municipal Corporation",
                "prior_body": "Municipal Corporation of Delhi",
                "ward_name": official.loc[ward, "ward_name"],
                "prior_ward_name": r.ward_name,
                "link_basis": "2012_notification_retains_2007_wards",
                "link_source_path": LINK_SOURCE,
                "link_source_page": 1,
                "link_source_sha256": digest(root / LINK_SOURCE),
                "reserved_raw": r.reservation_current,
                "prior_reserved_raw": r.reservation_prior,
                "reserved_woman": int(r.reservation_current in ["W", "SCW"]),
                "prior_reserved_woman": int(r.reservation_prior in ["W", "SCW"]),
                "reserved_caste": "SC"
                if r.reservation_current.startswith("SC")
                else "NONE",
                "prior_reserved_caste": "SC"
                if r.reservation_prior.startswith("SC")
                else "NONE",
                "winner": official.loc[ward, "winner_name"],
                "winner_woman_raw": r.sex_raw_goyal_current,
                "winner_woman": {"F": 1, "M": 0}.get(r.sex_current),
                "winner_woman_source": r.sex_source_current,
                "winner_woman_decision": decision,
                "winner_woman_review_url": review.loc[ward, "source_url"]
                if ward in review.index
                else None,
                "winner_woman_review_evidence": review.loc[ward, "evidence"]
                if ward in review.index
                else None,
                "reserved_source_path": "data/raw/2012/winner_runner_up.pdf",
                "reserved_source_page": int(official.loc[ward, "pdf_page"]),
                "reserved_source_sha256": digest(
                    root / "data/raw/2012/winner_runner_up.pdf"
                ),
                "prior_reserved_source_path": "data/raw/2007/election_results.xls",
                "prior_reserved_source_row": r.source_row,
                "prior_reserved_source_sha256": digest(
                    root / "data/raw/2007/election_results.xls"
                ),
            }
        )
    table = pa.Table.from_pylist(records, schema=SCHEMA)
    validate(table)
    output = output or root / "data/release/persistence"
    output.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output / "wards_2007_2012.parquet")
    pq.write_table(table.select(LINK_FIELDS), output / "ward_links.parquet")
    if not table.equals(pq.read_table(output / "wards_2007_2012.parquet")):
        raise ValueError("Persistence Parquet round trip changed values")
    normalized = lambda value: re.sub(r"[^A-Z0-9]", "", value.upper())
    changes = [
        {k: r[k] for k in ["ward_no", "prior_ward_name", "ward_name", "link_basis"]}
        for r in records
        if normalized(r["ward_name"]) != normalized(r["prior_ward_name"])
    ]
    pd.DataFrame(changes).to_csv(output / "ward_name_differences.csv", index=False)
    data = table.to_pandas()
    open_wards = data[data.reserved_woman.eq(0)]
    summary = {
        "linked_wards": len(data),
        "women_reserved_2012": int(data.reserved_woman.sum()),
        "nonquota_2012": len(open_wards),
        "known_nonquota_outcomes": int(open_wards.winner_woman.notna().sum()),
        "unknown_nonquota_wards": open_wards.loc[
            open_wards.winner_woman.isna(), "ward_no"
        ].tolist(),
        "arms": [
            {
                "prior_reserved_woman": int(arm),
                "eligible_wards": len(rows),
                "known_winners": int(rows.winner_woman.notna().sum()),
                "women_winners": int(rows.winner_woman.sum()),
            }
            for arm, rows in open_wards.groupby("prior_reserved_woman")
        ],
        "quota_transitions": [
            {
                "prior_reserved_woman": int(a),
                "reserved_woman": int(b),
                "wards": len(rows),
            }
            for (a, b), rows in data.groupby(["prior_reserved_woman", "reserved_woman"])
        ],
        "ward_name_differences": len(changes),
    }
    (output / "profile.json").write_text(json.dumps(summary, indent=2) + "\n")
    schema = {
        "wards_2007_2012": {
            "primary_key": ["year", "ward_no"],
            "rows": 272,
            "fields": [
                {"name": n, "arrow_type": str(t), "nullable": v, "description": d}
                for n, t, v, d in FIELDS
            ],
        },
        "ward_links": {
            "primary_key": ["prior_year", "year", "prior_ward_no", "ward_no"],
            "rows": 272,
            "fields": LINK_FIELDS,
        },
    }
    (output / "schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    (output / "dictionary.md").write_text(
        "# Delhi same-ward comparison\n\nOne row per 2007 ward retained for the 2012 election. All 272 wards remain in the file; restrict `reserved_woman == 0` for the open-election comparison. The comparison is prior quota versus prior nonquota, not male versus female prior winners. Nonquota seats may elect women. Missing winner sex remains null. `ward_links.parquet` contains the geographic key/provenance projection, with the same types.\n\n| Column | Arrow type | Nullable | Meaning |\n|---|---|---|---|\n"
        + "".join(f"| `{n}` | {t} | {v} | {d} |\n" for n, t, v, d in FIELDS)
    )
    inputs = [
        "data/release/2007/winners.parquet",
        "data/release/2012/winners.parquet",
        "data/extracted/2012/winner_runner_up.csv",
        "data/frame.json",
        LINK_SOURCE,
        "data/raw/2007/election_results.xls",
        "data/raw/2012/winner_runner_up.pdf",
    ]
    sources = [{"path": path, "sha256": digest(root / path)} for path in inputs]
    sources.append(
        {
            "path": "../local_elections/data/delhi/interim/sex_review.csv",
            "sha256": digest(review_path),
        }
    )
    (output / "sources.json").write_text(json.dumps(sources, indent=2) + "\n")
    (output / "checksums.json").write_text(
        json.dumps(
            {
                p.name: digest(p)
                for p in sorted(output.iterdir())
                if p.is_file() and p.name != "checksums.json"
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(summary, indent=2))
    return table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    build(args.root, args.root.parent / "local_elections")
