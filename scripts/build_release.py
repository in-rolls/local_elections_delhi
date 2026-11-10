"""Build a source-prioritized 2012 release and row-level comparison receipts."""

import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd

EDUCATION = {
    "Illiterate": 0,
    "Literate": 0,
    "5th Pass": 0,
    "8th Pass": 0,
    "10th Pass": 0,
    "12th Pass": 0,
    "Graduate": 1,
    "Graduate Professional": 1,
    "Post Graduate": 1,
    "Doctorate": 1,
}


def build(root, upstream):
    pins = json.loads((root / "data/upstream_manifest.json").read_text())
    for row in pins:
        path = upstream / row["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError(f"Upstream source changed: {path}")
    sources = upstream / "data/delhi/interim/qualification_audit/sources"
    goyal = pd.read_excel(sources / "goyal_candidates.xlsx")
    goyal["source_row"] = goyal.index + 2
    goyal = goyal[goyal.election.eq(2012)].copy()
    goyal["ward"] = pd.to_numeric(goyal.commonname, errors="raise").astype(int)
    if goyal.duplicated(["ward", "eci_pos"]).any():
        raise ValueError("Goyal candidate keys are not unique")
    inventory = pd.read_csv(
        root / "data/extracted/2012/candidate_list_inventory.csv"
    ).drop_duplicates("ward")
    counts = goyal.groupby("ward").size()
    if not counts.sort_index().equals(
        inventory.set_index("ward").candidate_count.sort_index()
    ):
        raise ValueError("Goyal candidate counts differ from official lists")
    official = pd.read_csv(root / "data/extracted/2012/winner_runner_up.csv")
    winners = official.merge(
        goyal[goyal.eci_pos.eq(1)],
        on="ward",
        validate="one_to_one",
        suffixes=("", "_goyal"),
    )
    if (
        len(winners) != 272
        or not winners.winner_votes.eq(winners.votes).all()
        or not winners.reservation.eq(winners.resstatus).all()
    ):
        raise ValueError("Winner votes or reservations disagree")
    profiles = pd.read_parquet(upstream / "data/delhi/release/winners.parquet")
    profiles = profiles[profiles.year.eq(2012)].copy()
    spec = importlib.util.spec_from_file_location(
        "delhi_source_html", upstream / "src/local_elections/states/delhi/html.py"
    )
    html_parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(html_parser)
    for row in profiles[profiles.source_path.notna()].itertuples():
        with gzip.open(
            upstream / "data/delhi/interim/qualification_audit" / row.source_path, "rt"
        ) as handle:
            response = json.load(handle)
        if hashlib.sha256(response["body"].encode()).hexdigest() != row.source_sha256:
            raise ValueError("Cached profile body hash disagrees")
        parsed = html_parser.profile(response["body"], 2012)
        if (
            parsed["ward_number"] != str(row.ward_number)
            or parsed["education"] != row.education
        ):
            raise ValueError("Cached profile disagrees with typed winner release")
    profiles["ward"] = pd.to_numeric(profiles.ward_number).astype(int)
    profiles = profiles[
        ["ward", "education", "source_url", "source_path", "source_sha256"]
    ].rename(columns={"education": "profile_education"})
    review = pd.read_csv(upstream / "data/delhi/interim/sex_review.csv")
    candidates = goyal.merge(
        inventory[["ward", "reservation", "source_path", "source_url"]],
        on="ward",
        validate="many_to_one",
        suffixes=("", "_sec"),
    )
    candidates["sex"] = candidates.gender.where(~candidates.gender_doubt.eq("yes"))
    candidates["sex_source"] = "goyal"
    for row in review.itertuples():
        mask = candidates.ward.eq(row.ward) & candidates.eci_pos.eq(1)
        if (
            len(candidates[mask]) != 1
            or candidates.loc[mask, "gender"].iloc[0] != row.source_gender
        ):
            raise ValueError("Sex review does not match source row")
        candidates.loc[mask, "sex"] = row.reviewed_gender
        candidates.loc[mask, "sex_source"] = "review_" + row.decision
    candidates = candidates.merge(
        profiles[["ward", "profile_education", "source_url"]].rename(
            columns={"source_url": "profile_url"}
        ),
        on="ward",
        validate="many_to_one",
    )
    candidates["education_source"] = "goyal"
    candidates["education_raw_goyal"] = candidates.education
    use_profile = candidates.eci_pos.eq(1) & candidates.profile_education.notna()
    candidates.loc[use_profile, "education"] = candidates.loc[
        use_profile, "profile_education"
    ]
    candidates.loc[use_profile, "education_source"] = "myneta_profile"
    candidates.loc[~candidates.eci_pos.eq(1), "profile_url"] = pd.NA
    candidates["graduate"] = candidates.education.map(EDUCATION).astype("Int64")
    candidates["is_winner"] = candidates.eci_pos.eq(1)
    candidates["quota"] = candidates.reservation.isin(["W", "SCW"])
    candidates = candidates.rename(
        columns={
            "election": "year",
            "eci_pos": "rank",
            "eci_candname": "candidate_name",
            "eci_party": "party",
            "gender": "sex_raw_goyal",
            "source_row": "goyal_excel_row",
            "source_path": "sec_candidate_list",
            "source_url": "sec_candidate_list_url",
        }
    )
    columns = [
        "year",
        "ward",
        "rank",
        "candidate_name",
        "party",
        "votes",
        "is_winner",
        "reservation",
        "quota",
        "sex",
        "sex_raw_goyal",
        "gender_doubt",
        "sex_source",
        "education",
        "education_raw_goyal",
        "graduate",
        "education_source",
        "goyal_excel_row",
        "sec_candidate_list",
        "sec_candidate_list_url",
        "profile_url",
    ]
    candidates = candidates[columns].sort_values(["ward", "rank"])
    winners = winners.merge(profiles, on="ward", validate="one_to_one")
    varun = pd.read_csv(sources / "varun_datasetfull.tab", sep="\t")
    varun = varun[varun.year.eq(2012)].copy()
    vw = varun[varun.electionoutcome.eq("Winner")][
        ["votespolled", "party", "edu_recoded", "totalassets"]
    ]
    vw = vw[~vw.duplicated(["votespolled", "party"], keep=False)]
    ow = official[~official.duplicated(["winner_votes", "winner_party"], keep=False)]
    linked = ow.merge(
        vw,
        left_on=["winner_votes", "winner_party"],
        right_on=["votespolled", "party"],
        validate="one_to_one",
    )
    winners = winners.merge(
        linked[["ward", "edu_recoded", "totalassets"]].rename(
            columns={"totalassets": "varun_assets"}
        ),
        on="ward",
        how="left",
        validate="one_to_one",
    )
    winners["goyal_graduate"] = winners.education.map(EDUCATION)
    winners["profile_graduate"] = winners.profile_education.map(EDUCATION)
    winners["varun_graduate"] = winners.edu_recoded.ge(3).where(
        winners.edu_recoded.notna()
    )
    audit_columns = [
        "ward",
        "winner_name",
        "eci_candname",
        "winner_party",
        "winner_votes",
        "votes",
        "reservation",
        "resstatus",
        "education",
        "profile_education",
        "edu_recoded",
        "goyal_graduate",
        "profile_graduate",
        "varun_graduate",
        "totalassets",
        "varun_assets",
        "pdf_page",
        "source_row",
        "source_url",
        "source_path",
        "source_sha256",
    ]
    release = root / "data/release/2012"
    release.mkdir(parents=True, exist_ok=True)
    candidates.to_parquet(release / "candidates.parquet", index=False)
    winning = candidates[candidates.is_winner].merge(
        official[
            [
                "ward",
                "winner_name",
                "winner_party",
                "winner_votes",
                "runner_up_votes",
                "margin",
                "pdf_page",
            ]
        ],
        on="ward",
        validate="one_to_one",
    )
    winning.to_parquet(release / "winners.parquet", index=False)
    winners[audit_columns].to_csv(
        root / "data/extracted/2012/winner_comparison.csv", index=False
    )
    summaries = []
    for source in ["goyal", "varun"]:
        subset = winners[[f"{source}_graduate", "profile_graduate"]].dropna()
        a, b = subset.iloc[:, 0].astype(float), subset.iloc[:, 1].astype(float)
        summaries.append(
            {
                "source": source,
                "jointly_classified": len(subset),
                "agreement": float(a.eq(b).mean()),
                "chance_agreement": float(
                    a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
                ),
            }
        )
    assets = (
        winners[["totalassets", "varun_assets"]]
        .apply(pd.to_numeric, errors="coerce")
        .dropna()
    )
    summary = {
        "assets_jointly_recorded": len(assets),
        "assets_exact_agreement": float(
            assets.totalassets.eq(assets.varun_assets).mean()
        ),
        "goyal_candidates": len(goyal),
        "sec_candidates": int(counts.sum()),
        "varun_candidates": len(varun),
        "varun_2012_ward_missing": int(varun.wardnumber.isna().sum()),
        "varun_winners_matched_to_sec": len(linked),
        "winner_votes_agree": 272,
        "winner_reservations_agree": 272,
        "graduate_comparisons": summaries,
        "missing_sex": int(candidates.sex.isna().sum()),
        "missing_winner_sex": int(winning.sex.isna().sum()),
    }
    (root / "data/extracted/2012/comparison_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    hashes = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in release.glob("*.parquet")
    }
    (release / "checksums.json").write_text(json.dumps(hashes, indent=2) + "\n")
    schema = {
        "candidates": {
            "rows": len(candidates),
            "key": ["year", "ward", "rank"],
            "columns": {
                column: str(dtype) for column, dtype in candidates.dtypes.items()
            },
        },
        "winners": {
            "rows": len(winning),
            "key": ["year", "ward"],
            "columns": {column: str(dtype) for column, dtype in winning.dtypes.items()},
        },
    }
    (release / "schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--upstream", type=Path)
    args = parser.parse_args()
    build(args.root, args.upstream or args.root.parent / "local_elections")
