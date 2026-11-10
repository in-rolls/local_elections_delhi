import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from parse_sources import candidate_inventory, pdf_text
from parse_winners import parse

ROOT = Path(__file__).resolve().parents[1]


def test_printed_candidate_counts_and_serial_gap():
    frame = json.loads((ROOT / "data/frame.json").read_text())
    rows = []
    for ward in [1, 141, 240, 272]:
        source = next(row for row in frame if row["ward"] == ward)
        text = pdf_text(ROOT / source["path"])
        row = candidate_inventory(text)
        assert row["ward"] == ward
        rows.append(row)
        with pytest.raises(ValueError):
            candidate_inventory(text.replace("Total for this Ward", "Invalid total"))
    assert rows[2]["candidate_count"] == 10
    assert not rows[2]["serial_numbers_contiguous"]


def test_official_report_and_wrapped_ward_name():
    data = parse(ROOT / "data/raw/2012/winner_runner_up.pdf")
    assert len(data) == 272
    assert (data.winner_votes - data.runner_up_votes).equals(data.margin)
    assert data.set_index("ward").loc[115, "ward_name"] == "Major Bhupinder Singh Nagar"
    assert data.set_index("ward").loc[2, "winner_votes"] == 9076


def test_source_receipts_and_duplicate_alias():
    rows = [
        json.loads(line)
        for line in (ROOT / "data/source_manifest.jsonl").read_text().splitlines()
    ]
    for row in rows:
        data = (ROOT / row["path"]).read_bytes()
        assert len(data) == row["bytes"]
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
    frame = json.loads((ROOT / "data/frame.json").read_text())
    ward = [row for row in frame if row["ward"] == 141]
    assert len(ward) == 2
    assert pdf_text(ROOT / ward[0]["path"]) == pdf_text(ROOT / ward[1]["path"])
    paths = {row["path"] for row in rows if row["kind"] == "pdf"}
    hashes = [hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths]
    assert len(hashes) == len(set(hashes))


def test_release_keys_unknowns_and_review():
    candidates = pd.read_parquet(ROOT / "data/release/2012/candidates.parquet")
    winners = pd.read_parquet(ROOT / "data/release/2012/winners.parquet").set_index(
        "ward"
    )
    assert len(candidates) == 2423
    assert len(winners) == 272
    assert not candidates.duplicated(["year", "ward", "rank"]).any()
    assert set(candidates.ward) == set(range(1, 273))
    assert candidates.sex.isna().sum() == 10
    assert winners.sex.isna().sum() == 1
    assert winners.loc[111, "sex"] == "F"
    assert winners.loc[254, "sex"] == "M"
    assert pd.isna(winners.loc[115, "sex"])
    assert winners.loc[111, "sex_raw_goyal"] == "M"
    assert (winners.winner_votes == winners.votes).all()
    assert candidates.profile_url[candidates.is_winner.eq(False)].isna().all()
    inventory = pd.read_csv(
        ROOT / "data/extracted/2012/candidate_list_inventory.csv"
    ).drop_duplicates("ward")
    assert (
        candidates.groupby("ward")
        .size()
        .sort_index()
        .equals(inventory.set_index("ward").candidate_count.sort_index())
    )
    for path, digest in json.loads(
        (ROOT / "data/release/2012/checksums.json").read_text()
    ).items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_comparison_denominators_and_chance_agreement():
    rows = pd.read_csv(ROOT / "data/extracted/2012/winner_comparison.csv")
    g = rows[["goyal_graduate", "profile_graduate"]].dropna()
    v = rows[["varun_graduate", "profile_graduate"]].dropna().astype(float)
    assert len(g) == 226
    assert (g.goyal_graduate == g.profile_graduate).all()
    assert len(v) == 183
    assert (v.varun_graduate == v.profile_graduate).sum() == 98
    assets = (
        rows[["totalassets", "varun_assets"]]
        .apply(pd.to_numeric, errors="coerce")
        .dropna()
    )
    assert len(assets) == 234
    assert (assets.totalassets == assets.varun_assets).sum() == 227


def test_original_deposit_education_and_independent_case():
    sources = (
        ROOT.parent / "local_elections/data/delhi/interim/qualification_audit/sources"
    )
    receipt = json.loads(
        (sources / "varun_datasetfull_original_receipt.json").read_text()
    )
    original = sources / receipt["path"]
    assert hashlib.sha256(original.read_bytes()).hexdigest() == receipt["sha256"]
    dta = pd.read_stata(original, convert_categoricals=False)
    tab = pd.read_csv(sources / "varun_datasetfull.tab", sep="\t")
    assert dta.shape == tab.shape
    pd.testing.assert_series_equal(dta.year, tab.year, check_dtype=False)
    pd.testing.assert_series_equal(dta.edu_recoded, tab.edu_recoded, check_dtype=False)
    case = dta[
        dta.year.eq(2012)
        & dta.votespolled.eq(12947)
        & dta.party.eq("BHARATIYA JANATA PARTY")
        & dta.electionoutcome.eq("Winner")
    ]
    assert len(case) == 1
    assert case.iloc[0].edu_recoded == 0
    rows = pd.read_csv(ROOT / "data/extracted/2012/winner_comparison.csv")
    case = rows.set_index("ward").loc[11]
    assert case.winner_name == "RAJNI ABBI"
    assert case.profile_education == case.education == "Doctorate"
    assert case.totalassets == case.varun_assets == 21522003


def test_restore_rejects_changed_remote_before_writing(tmp_path, monkeypatch):
    import fetch_sources

    class Response:
        content = b"%PDF changed source"
        url = "https://example.org/source.pdf"
        status_code = 200

        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        fetch_sources.requests.Session, "get", lambda *a, **k: Response()
    )
    with pytest.raises(ValueError, match="differs from pinned snapshot"):
        fetch_sources.fetch(
            tmp_path,
            Response.url,
            "data/raw/source.pdf",
            "pdf",
            expected_sha256=hashlib.sha256(b"original source").hexdigest(),
        )
    assert not (tmp_path / "data/raw/source.pdf").exists()
    assert not (tmp_path / "data/source_manifest.jsonl").exists()
