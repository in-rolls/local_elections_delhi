import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_election_universes_and_nota():
    for year, count, wards in [
        (2007, 2570, 272),
        (2012, 2423, 272),
        (2017, 2538, 272),
        (2022, 1349, 250),
    ]:
        folder = ROOT / f"data/release/{year}"
        candidates = pd.read_parquet(folder / "candidates.parquet")
        winners = pd.read_parquet(folder / "winners.parquet")
        assert len(candidates) == count
        assert len(winners) == wards
        assert not candidates.duplicated(["year", "ward", "rank"]).any()
        assert not winners.duplicated(["year", "ward"]).any()
        assert not candidates.candidate_name.str.upper().eq("NOTA").any()
        assert candidates.is_winner.sum() == wards
        assert winners["rank"].eq(1).all()
        for path, digest in json.loads((folder / "checksums.json").read_text()).items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    for year, wards in [(2017, 272), (2022, 250)]:
        nota = pd.read_parquet(ROOT / f"data/release/{year}/nota.parquet")
        assert len(nota) == wards
        assert not nota.duplicated(["year", "ward"]).any()
    old = pd.read_parquet(ROOT / "data/release/2007/candidates.parquet")
    assert old.education.isna().all()
    assert old.graduate.isna().all()


def test_deferred_wards_against_scanned_control_totals():
    candidates = pd.read_parquet(ROOT / "data/release/2017/candidates.parquet")
    nota = pd.read_parquet(ROOT / "data/release/2017/nota.parquet").set_index("ward")
    winners = pd.read_parquet(ROOT / "data/release/2017/winners.parquet").set_index(
        "ward"
    )
    for ward, total, n in [("16-N", 24820, 12), ("40-E", 26032, 10)]:
        rows = candidates[candidates.ward.eq(ward)]
        assert len(rows) == n
        assert rows.votes.sum() + nota.loc[ward, "votes"] == total
        assert winners.loc[ward, "result_verification"] == "sec_scan_manually_checked"
    assert winners.loc["16-N", "winner_votes"] == 10946
    assert winners.loc["40-E", "winner_votes"] == 9374


def test_page_spanning_rows_and_report_conflict():
    records = pd.read_csv(
        ROOT / "data/extracted/2022/winner_runner_up.csv", dtype={"ward": str}
    ).set_index("ward")
    assert records.loc["43", "winner_name"] == "BOBI"
    assert records.loc["43", "runner_up_party"] == "INDIAN NATIONAL CONGRESS"
    assert records.loc["66", "runner_up_party"] == "BHARATIYA JANATA PARTY"
    assert (records.winner_votes - records.runner_up_votes).equals(records.margin)
    winners = pd.read_parquet(ROOT / "data/release/2022/winners.parquet").set_index(
        "ward"
    )
    assert winners.loc["236", "votes"] == 15069
    assert winners.loc["236", "winner_votes_raw_report"] == 15070
    assert winners.loc["236", "margin"] == 7476
    assert winners.loc["236", "result_verification"] == "sec_scan_manually_checked"
    assert winners.loc["236", "votes_raw_compilation"] == 15069
    disagreements = pd.read_csv(
        ROOT / "data/extracted/source_audit/result_disagreements.csv"
    )
    assert len(disagreements) == 3
    assert set(disagreements.ward) == {157, 236}
    row = disagreements[disagreements.ward.eq(236)].iloc[0]
    assert row.decision == "prefer_signed_return"
    assert row.selected == row.compilation == 15069


def test_education_conflicts_stay_distinct_from_missing_and_corroboration():
    education = pd.read_parquet(
        ROOT / "data/release/education/winners.parquet"
    ).set_index(["year", "ward"])
    assert len(education) == 794
    assert not education.affidavit_verified.any()
    assert (
        education.loc[(2012, "11"), "education_status"]
        == "degree_independently_corroborated"
    )
    assert education.loc[(2012, "17"), "education_status"] == "missing"
    assert education.loc[(2017, "50-N"), "category_disagreement"]
    assert education.loc[(2017, "50-N"), "graduate"] == 0
    assert pd.isna(education.loc[(2017, "50-N"), "education"])
    assert education.loc[(2022, "134"), "graduate_conflict"]
    assert pd.isna(education.loc[(2022, "134"), "graduate"])
    assert education.loc[(2022, "134"), "graduate_raw_profile"] == 0
    assert education.loc[(2022, "134"), "graduate_raw_secondary"] == 1
    assert education.loc[(2022, "162"), "education_source"] == "tcpd_transcription"
    assert education.loc[(2012, "86"), "education_raw_profile"] == "Others"
    assert "BBS" in education.loc[(2012, "86"), "education_details_profile"]
    assert pd.isna(education.loc[(2012, "86"), "graduate"])


def test_detailed_results_and_signed_return_reconciliation():
    candidates = pd.read_parquet(ROOT / "data/release/2022/candidates.parquet")
    nota = pd.read_parquet(ROOT / "data/release/2022/nota.parquet")
    ward = candidates[candidates.ward.eq("157")].copy()
    ward["name"] = ward.candidate_name.str.upper()
    ward = ward.set_index("name")
    assert ward.loc["POOJA", "votes"] == 79
    assert ward.loc["POOJA", "votes_raw_compilation"] == 8683
    assert ward.loc["POOJA", "rank"] == 7
    assert ward.loc["POOJA", "rank_raw_compilation"] == 2
    assert ward.loc["BINEETA SHARMA", "votes"] == 103
    assert ward.loc["BINEETA SHARMA", "votes_raw_compilation"] == 0
    assert ward.loc["HIMANI AMBAWTA", "votes"] == 8683
    assert ward.loc["HIMANI AMBAWTA", "rank"] == 2
    assert ward.votes.sum() + nota.set_index("ward").loc["157", "votes"] == 27518
    assert candidates.votes.sum() + nota.votes.sum() == 7335824
    assert nota.votes.sum() == 57545
    comparison = pd.read_csv(
        ROOT / "data/extracted/source_audit/candidate_results_2022.csv"
    )
    assert len(comparison) == 1599
    assert comparison.row_text.notna().all()
    assert comparison.votes_raw_compilation.ne(comparison.votes_report).sum() == 3
    totals = pd.read_csv(
        ROOT / "data/extracted/source_audit/ward_totals_2022.csv"
    ).set_index("ward")
    assert len(totals) == 250
    assert totals.loc[41, "Valid_Votes"] == 3070
    assert totals.loc[41, "valid_votes_signed"] == 30704
    assert totals.loc[41, "rejected_votes_signed"] == 2
    assert totals.loc[212, "valid_votes_signed"] == 25968
    assert totals.loc[27, "valid_votes_signed"] == 37346
    assert totals.loc[27, "candidate_plus_nota_votes"] == 37338
    assert totals.loc[27, "signed_minus_sum"] == 8
    assert totals.loc[236, "report_minus_sum"] == 1
    assert totals.report_minus_sum.ne(0).sum() == 1
    assert totals.signed_minus_sum.dropna().ne(0).sum() == 1
