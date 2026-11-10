"""Build election-specific Delhi releases and an explicit education-source audit."""

import argparse
import gzip
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from build_release import EDUCATION

PARTY = {
    "SAMAJWADI PARTY": "SP",
    "INDIAN NATIONAL LOK DAL": "INLD",
    "AAM AADMI PARTY": "AAP",
    "BHARATIYA JANATA PARTY": "BJP",
    "INDIAN NATIONAL CONGRESS": "INC",
    "INDEPENDENT": "IND",
    "BAHUJAN SAMAJ PARTY": "BSP",
    "RASHTRIYA LOK DAL": "RLD",
}
TCPD_GRADUATE = {
    "Graduate": 1,
    "Postgraduate": 1,
    "Inter": 0,
    "Higher": 0,
    "Middle": 0,
    "Primary": 0,
    "Illetrate": 0,
}


def text_value(value):
    return str(value).strip() if pd.notna(value) else None


def verify_sources(root, upstream):
    for line in (root / "data/source_manifest.jsonl").read_text().splitlines():
        row = json.loads(line)
        if (
            hashlib.sha256((root / row["path"]).read_bytes()).hexdigest()
            != row["sha256"]
        ):
            raise ValueError(f"Source changed: {row['path']}")
    for row in json.loads((root / "data/upstream_manifest.json").read_text()):
        if (
            hashlib.sha256((upstream / row["path"]).read_bytes()).hexdigest()
            != row["sha256"]
        ):
            raise ValueError(f"Upstream source changed: {row['path']}")


def official_results(root, year):
    data = pd.read_csv(
        root / f"data/extracted/{year}/winner_runner_up.csv",
        dtype={"ward": str, "source_page": str},
    )
    data["result_verification"] = "sec_report"
    if year == 2017:
        manual = pd.read_csv(
            root / "data/reference/2017_deferred_results.csv",
            dtype={"ward": str, "source_page": str},
        )
        for r in manual.itertuples():
            if (
                hashlib.sha256(
                    (root / f"data/raw/2017/{r.source_file}").read_bytes()
                ).hexdigest()
                != r.source_sha256
            ):
                raise ValueError("Deferred result source changed")
        manual["result_verification"] = "sec_scan_manually_checked"
        data = pd.concat(
            [data, manual.drop(columns="source_sha256")], ignore_index=True
        )
    if year == 2022:
        data["winner_votes_raw_report"] = data.winner_votes
        mask = data.ward.eq("236")
        if data.loc[mask, "winner_votes"].tolist() != [15070]:
            raise ValueError("Unexpected winner-summary value for ward 236")
        data.loc[mask, "winner_votes"] = 15069
        data.loc[mask, "margin"] = 15069 - data.loc[mask, "runner_up_votes"]
        data.loc[mask, "source_file"] = "returns/ward_236.pdf"
        data.loc[mask, "source_page"] = "1"
        data.loc[mask, "result_verification"] = "sec_scan_manually_checked"
    data["result_source"] = data.source_file.map(lambda f: f"data/raw/{year}/{f}")
    return data.drop(columns="source_file")


def read_profiles(upstream):
    data = pd.read_parquet(upstream / "data/delhi/release/winner_source_audit.parquet")
    spec = importlib.util.spec_from_file_location(
        "source_html", upstream / "src/local_elections/states/delhi/html.py"
    )
    html = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(html)
    details = []
    for row in data.itertuples():
        detail = None
        if pd.notna(row.source_path):
            path = upstream / "data/delhi/interim/qualification_audit" / row.source_path
            response = json.loads(gzip.decompress(path.read_bytes()))
            if (
                hashlib.sha256(response["body"].encode()).hexdigest()
                != row.source_sha256
            ):
                raise ValueError("Profile checksum changed")
            parsed = html.profile(response["body"], row.year)
            if (
                parsed["education"] != row.education
                or parsed["ward_number"] != row.ward_number
                or parsed["profile_party"] != row.winner_party
            ):
                raise ValueError("Profile differs from pinned winner record")
            visible = html.text(html.expand_rows(response["body"]))
            match = re.search(
                r"Educational Details\s+Category:\s*[^\n]+\n(.*?)(?:Details of PAN|Details of Criminal|Assets &|Details of Assets|Disclaimer|$)",
                visible,
                re.DOTALL,
            )
            if match:
                detail = match[1].strip() or None
        details.append(detail)
    data["education_details_profile"] = details
    data = data.rename(
        columns={
            "ward_number": "ward",
            "education": "education_raw_profile",
            "source_url": "profile_url",
            "source_path": "profile_cache_path",
            "source_sha256": "profile_sha256",
            "source_capture": "profile_capture",
            "age": "age_profile",
            "occupation": "occupation_profile",
        }
    )
    return data


def education_records(root, upstream, goyal, tcpd, profiles):
    records = []
    goyal_w = goyal[goyal.eci_pos.eq(1)].set_index(["election", "ward"])
    tcpd_w = tcpd[tcpd.Position.eq(1)].set_index("ward")
    for r in profiles.itertuples():
        record = {
            "year": r.year,
            "ward": r.ward,
            "winner_name": r.winner_name,
            "education_raw_profile": r.education_raw_profile,
            "education_details_profile": r.education_details_profile,
            "profile_url": r.profile_url,
            "profile_cache_path": r.profile_cache_path,
            "profile_sha256": r.profile_sha256,
            "profile_capture": r.profile_capture,
            "education_raw_goyal": None,
            "education_details_goyal": None,
            "education_raw_tcpd": None,
            "affidavit_filename_tcpd": None,
            "graduate_raw_profile": EDUCATION.get(r.education_raw_profile),
            "graduate_raw_secondary": None,
            "category_disagreement": False,
            "graduate_conflict": False,
            "affidavit_verified": False,
            "independent_education_source": None,
        }
        if r.year in [2012, 2017]:
            g = goyal_w.loc[(r.year, r.ward)]
            record.update(
                education_raw_goyal=text_value(g.education),
                education_details_goyal=text_value(g.schoolname),
                graduate_raw_secondary=EDUCATION.get(g.education),
            )
            if pd.notna(r.education_raw_profile) and pd.notna(g.education):
                record["category_disagreement"] = (
                    r.education_raw_profile.strip() != g.education.strip()
                )
            fallback = text_value(g.education)
            fallback_source = "goyal_transcription"
        else:
            t = tcpd_w.loc[r.ward]
            record.update(
                education_raw_tcpd=text_value(t.Education),
                affidavit_filename_tcpd=text_value(t["Affidavit "]),
                graduate_raw_secondary=TCPD_GRADUATE.get(t.Education),
            )
            fallback = text_value(t.Education)
            fallback_source = "tcpd_transcription"
        a, b = record["graduate_raw_profile"], record["graduate_raw_secondary"]
        conflict = a is not None and b is not None and a != b
        record["graduate_conflict"] = conflict
        has_profile = pd.notna(r.education_raw_profile)
        record["education_source"] = (
            "myneta_transcription"
            if has_profile
            else (fallback_source if fallback is not None else None)
        )
        record["education"] = r.education_raw_profile if has_profile else fallback
        record["graduate"] = None if conflict else (a if has_profile else b)
        record["education_status"] = (
            "graduate_conflict"
            if conflict
            else (
                "category_conflict"
                if record["category_disagreement"]
                else (
                    "secondary_source" if record["education"] is not None else "missing"
                )
            )
        )
        if conflict or record["category_disagreement"]:
            record["education"] = None
        if r.year == 2012 and r.ward == "11":
            record["independent_education_source"] = (
                "data/raw/education_validation/rajni_abbi_du_cv.pdf#page=1"
            )
            record["education_status"] = "degree_independently_corroborated"
        records.append(record)
    result = pd.DataFrame(records)
    for c in ["graduate", "graduate_raw_profile", "graduate_raw_secondary"]:
        result[c] = result[c].astype("Int64")
    if result.duplicated(["year", "ward"]).any() or len(result) != 794:
        raise ValueError("Education universe invalid")
    return result


def write_release(root, year, candidates, winners, nota=None):
    target = root / f"data/release/{year}"
    target.mkdir(parents=True, exist_ok=True)
    for name, d in [("candidates", candidates), ("winners", winners), ("nota", nota)]:
        if d is not None:
            d.to_parquet(target / f"{name}.parquet", index=False)
    schema = {}
    hashes = {}
    for p in sorted(target.glob("*.parquet")):
        d = pd.read_parquet(p)
        schema[p.stem] = {
            "rows": len(d),
            "key": ["year", "ward", "rank"]
            if p.stem == "candidates"
            else ["year", "ward"],
            "columns": {f.name: str(f.type) for f in pq.read_schema(p)},
        }
        hashes[p.relative_to(root).as_posix()] = hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
    (target / "schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    (target / "checksums.json").write_text(json.dumps(hashes, indent=2) + "\n")


def reconcile_2022(root, raw):
    """Check every compiled candidate/NOTA row against the complete SEC report."""
    report_path = "data/raw/2022/election_report_volume_2.pdf"
    report = pd.read_csv(
        root / "data/extracted/2022/detailed_results.csv", dtype={"ward": str}
    )
    report["candidate_rank"] = (~report.is_nota).groupby(report.ward).cumsum()
    d = raw.copy()
    d["votes_raw_compilation"] = d.Votes
    d["rank_raw_compilation"] = d.Position
    d["candidate_rank"] = d.Position
    # Aya Nagar's erroneous votes changed the compilation's candidate ordering.
    mask = d.ward.eq("157")
    d.loc[mask, "candidate_rank"] = d.loc[mask, "Position"].map(
        {1: 1, 2: 7, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7}
    )
    # Two Shakur Basti independents both have 83 votes; the sources order the tie differently.
    mask = d.ward.eq("51") & d.Position.isin([5, 6])
    d.loc[mask, "candidate_rank"] = d.loc[mask, "Position"].map({5: 6, 6: 5})
    is_nota = d.Candidate_Name.str.upper().eq("NOTA")
    candidates = d[~is_nota].merge(
        report[~report.is_nota],
        on=["ward", "candidate_rank"],
        validate="one_to_one",
        how="left",
    )
    nota = (
        d[is_nota]
        .drop(columns="candidate_rank")
        .merge(report[report.is_nota], on="ward", validate="one_to_one", how="left")
    )
    d = pd.concat([candidates, nota], ignore_index=True)
    if len(d) != len(raw) or d.row_text.isna().any():
        raise ValueError("Incomplete detailed-result join")
    normalize = lambda value: re.sub(r"[^A-Z]", "", value.upper())
    for r in d.itertuples():
        name = normalize(r.Candidate_Name)
        prefix = normalize(re.split(r"\s{2,}", r.row_text)[0])
        full = normalize(r.row_text)
        # The report omits GAUTAM and runs this name into the party column.
        known_alias = (
            r.ward == "195"
            and r.Position == 1
            and name == "DHIRENDERKUMARBUNTYGAUTAM"
            and full == "DHIRENDERKUMARBUNTYAAMAADMIPARTY"
        )
        if not (full.startswith(name) or name.startswith(prefix) or known_alias):
            raise ValueError(
                f"Candidate identity mismatch: {r.ward} {r.Candidate_Name}"
            )
    signed = pd.read_csv(
        root / "data/reference/2022_signed_returns.csv", dtype={"ward": str}
    )
    for r in signed.itertuples():
        if (
            hashlib.sha256((root / r.source_file).read_bytes()).hexdigest()
            != r.source_sha256
        ):
            raise ValueError("Signed result source changed")
    d["Votes"] = d.votes_report
    d["vote_source"] = report_path
    d["vote_source_page"] = d.report_page
    mask = d.ward.eq("236") & d.Position.eq(1)
    if d.loc[mask, "votes_report"].tolist() != [15070]:
        raise ValueError("Unexpected ward 236 report value")
    d.loc[mask, "Votes"] = 15069
    d.loc[mask, "vote_source"] = "data/raw/2022/returns/ward_236.pdf"
    d.loc[mask, "vote_source_page"] = 1
    mask = d.ward.eq("157") & ~d.is_nota
    d.loc[mask, "Position"] = d.loc[mask, "candidate_rank"]
    auditdir = root / "data/extracted/source_audit"
    auditdir.mkdir(parents=True, exist_ok=True)
    fields = [
        "ward",
        "Candidate_Name",
        "rank_raw_compilation",
        "Position",
        "report_order",
        "row_text",
        "votes_raw_compilation",
        "votes_report",
        "Votes",
        "vote_source",
        "vote_source_page",
        "report_page",
    ]
    d[fields].to_csv(auditdir / "candidate_results_2022.csv", index=False)
    bad = d[d.votes_raw_compilation.ne(d.votes_report)]
    audit = [
        {
            "year": 2022,
            "ward": r.ward,
            "candidate_name": r.Candidate_Name,
            "field": "votes",
            "compilation": r.votes_raw_compilation,
            "official": r.votes_report,
            "selected": r.Votes,
            "decision": "prefer_signed_return"
            if r.ward == "236"
            else "prefer_sec_report_confirmed_by_signed_return",
            "source": r.vote_source,
            "page": r.vote_source_page,
        }
        for r in bad.itertuples()
    ]
    totals = pd.read_csv(
        root / "data/extracted/2022/ward_totals.csv", dtype={"ward": str}
    )
    compiled = raw[["ward", "Valid_Votes", "Total_Votes"]].drop_duplicates()
    totals = totals.merge(compiled, on="ward", validate="one_to_one")
    totals["candidate_plus_nota_votes"] = totals.ward.map(d.groupby("ward").Votes.sum())
    totals = totals.merge(signed, on="ward", how="left", validate="one_to_one")
    totals["report_minus_sum"] = (
        totals.valid_votes_report - totals.candidate_plus_nota_votes
    )
    totals["compilation_minus_sum"] = (
        totals.Valid_Votes - totals.candidate_plus_nota_votes
    )
    totals["signed_minus_sum"] = (
        totals.valid_votes_signed - totals.candidate_plus_nota_votes
    )
    totals.to_csv(auditdir / "ward_totals_2022.csv", index=False)
    return d.drop(columns=["is_nota", "candidate_rank"]), audit


def build(root, upstream):
    verify_sources(root, upstream)
    sources = upstream / "data/delhi/interim/qualification_audit/sources"
    g = pd.read_excel(sources / "goyal_candidates.xlsx")
    g["goyal_excel_row"] = g.index + 2
    g["ward"] = [
        str(v).strip() if y == 2017 else str(int(float(v)))
        for v, y in zip(g.commonname, g.election)
    ]
    t = pd.read_csv(sources / "opencity2022.csv")
    t["tcpd_csv_row"] = t.index + 2
    t["ward"] = t.Ward_No.astype(str)
    profiles = read_profiles(upstream)
    edu = education_records(root, upstream, g, t, profiles)
    edudir = root / "data/release/education"
    edudir.mkdir(parents=True, exist_ok=True)
    edu.to_parquet(edudir / "winners.parquet", index=False)
    edu[
        edu.graduate.isna()
        | edu.education_status.isin(["category_conflict", "graduate_conflict"])
    ].to_csv(edudir / "unresolved.csv", index=False)
    old_candidates = pd.read_parquet(root / "data/release/2012/candidates.parquet")
    old_winners = pd.read_parquet(root / "data/release/2012/winners.parquet")
    extra = edu[edu.year.eq(2012)].copy()
    extra["ward"] = extra.ward.astype(int)
    fields = ["ward"] + [c for c in extra if c not in old_winners and c != "year"]
    old_winners = old_winners.merge(extra[fields], on="ward", validate="one_to_one")
    write_release(root, 2012, old_candidates, old_winners)
    t, audit = reconcile_2022(root, t)
    for year in [2017, 2022]:
        official = official_results(root, year)
        if year == 2017:
            d = g[g.election.eq(year)].copy()
            d["is_nota"] = d.eci_candname.str.strip().eq("NOTA")
            nota = d[d.is_nota][["election", "ward", "votes"]].rename(
                columns={"election": "year"}
            )
            d = d[~d.is_nota].copy()
            d["sex"] = d.gender.where(~d.gender_doubt.eq("yes"))
            d = d.rename(
                columns={
                    "election": "year",
                    "eci_pos": "rank",
                    "eci_candname": "candidate_name",
                    "eci_party": "party",
                    "resstatus": "reservation",
                    "education": "education_raw_goyal",
                    "schoolname": "education_details_goyal",
                    "occupation": "occupation_raw",
                    "totalassets": "assets_raw",
                    "liabilities": "liabilities_raw",
                    "gender": "sex_raw",
                }
            )
            d["education"] = d.education_raw_goyal
            d["graduate"] = d.education.map(EDUCATION).astype("Int64")
            d["candidate_source"] = (
                "../local_elections/data/delhi/interim/qualification_audit/sources/goyal_candidates.xlsx"
            )
            d["source_row"] = d.goyal_excel_row
            inv = pd.read_csv(root / "data/extracted/2017/candidate_inventory.csv")
            counts = d.groupby("ward").size()
            expected = inv.set_index("ward").candidate_count.copy()
            expected.loc["40-E"] = 10
            if not counts.sort_index().equals(expected.sort_index()):
                raise ValueError("2017 candidate counts disagree with SEC")
        else:
            d = t.copy()
            d["is_nota"] = (
                d.Candidate_Name.str.strip()
                .str.upper()
                .isin(["NOTA", "NONE OF THE ABOVE"])
            )
            nota = d[d.is_nota][["Year", "ward", "Votes"]].rename(
                columns={"Year": "year", "Votes": "votes"}
            )
            d = d[~d.is_nota].copy()
            d = d.rename(
                columns={
                    "Year": "year",
                    "Position": "rank",
                    "Candidate_Name": "candidate_name",
                    "Votes": "votes",
                    "Gender": "sex_raw",
                    "Age": "age",
                    "Education": "education_raw_tcpd",
                }
            )
            d["party"] = d.Party_Name.map(PARTY).fillna(d.Party_Name)
            d["sex"] = d.sex_raw.map({"Male": "M", "Female": "F"})
            d["reservation"] = d.Ward_Reservation.map(
                {
                    "Women": "W",
                    "Unreserved": "G",
                    "Scheduled Caste": "SC",
                    "Scheduled Caste (Women)": "SCW",
                }
            )
            d["education"] = d.education_raw_tcpd
            d["graduate"] = d.education.map(TCPD_GRADUATE).astype("Int64")
            d["candidate_source"] = (
                "../local_elections/data/delhi/interim/qualification_audit/sources/opencity2022.csv"
            )
            d["source_row"] = d.tcpd_csv_row
        d["age_raw"] = d.age.astype("string")
        d["age"] = pd.to_numeric(d.age, errors="coerce").astype("Int64")
        d["party"] = d.party.str.strip()
        d["is_winner"] = d["rank"].eq(1)
        d["quota"] = d.reservation.isin(["W", "SCW"])
        if "votes_raw_compilation" not in d:
            d["votes_raw_compilation"] = d.votes
        if d.duplicated(["year", "ward", "rank"]).any() or d.reservation.isna().any():
            raise ValueError("Candidate keys/categories invalid")
        winning = d[d.is_winner].merge(
            official,
            on=["year", "ward"],
            validate="one_to_one",
            suffixes=("", "_official"),
        )
        if len(winning) != (272 if year == 2017 else 250):
            raise ValueError("Incomplete winners")
        if not winning.party.eq(winning.winner_party.map(PARTY)).all():
            raise ValueError("Official winner parties disagree")
        if (
            year == 2022
            and not winning.reservation.eq(winning.reservation_official).all()
        ):
            raise ValueError("Official reservation disagrees")
        for r in winning.itertuples():
            if r.votes != r.winner_votes:
                audit.append(
                    {
                        "year": year,
                        "ward": r.ward,
                        "field": "winner_votes",
                        "compilation": r.votes,
                        "official": r.winner_votes,
                        "decision": "prefer_sec_report",
                        "source": r.result_source,
                        "page": r.source_page,
                    }
                )
        edu_year = edu[edu.year.eq(year)]
        for c in ["education", "graduate"]:
            winning = winning.drop(columns=c)
        winning = winning.merge(
            edu_year.drop(
                columns=[
                    "winner_name",
                    "education_raw_goyal",
                    "education_details_goyal",
                    "education_raw_tcpd",
                ]
            ),
            on=["year", "ward"],
            validate="one_to_one",
        )
        winning = winning.merge(
            profiles[
                [
                    "year",
                    "ward",
                    "age_profile",
                    "pending_cases",
                    "convicted_cases",
                    "occupation_profile",
                ]
            ],
            on=["year", "ward"],
            validate="one_to_one",
        )
        for r in winning.itertuples():
            mask = d.ward.eq(r.ward) & d.is_winner
            d.loc[mask, "votes"] = r.winner_votes
            d.loc[mask, "education"] = r.education
            d.loc[mask, "graduate"] = r.graduate
        winning["votes"] = winning.winner_votes
        keep = [
            "year",
            "ward",
            "rank",
            "candidate_name",
            "party",
            "votes",
            "votes_raw_compilation",
            "rank_raw_compilation",
            "votes_report",
            "report_order",
            "vote_source",
            "vote_source_page",
            "is_winner",
            "reservation",
            "quota",
            "sex",
            "sex_raw",
            "age",
            "age_raw",
            "education",
            "graduate",
            "education_raw_goyal",
            "education_details_goyal",
            "education_raw_tcpd",
            "occupation_raw",
            "assets_raw",
            "liabilities_raw",
            "candidate_source",
            "source_row",
        ]
        d = d[[c for c in keep if c in d]].copy()
        winner_keep = keep + [
            "winner_name",
            "winner_party",
            "winner_votes",
            "winner_votes_raw_report",
            "runner_up_name",
            "runner_up_party",
            "runner_up_votes",
            "margin",
            "result_source",
            "source_page",
            "result_verification",
            "education_source",
            "education_status",
            "education_raw_profile",
            "education_details_profile",
            "profile_url",
            "profile_cache_path",
            "profile_sha256",
            "graduate_conflict",
            "category_disagreement",
            "affidavit_verified",
            "age_profile",
            "pending_cases",
            "convicted_cases",
            "occupation_profile",
            "affidavit_filename_tcpd",
        ]
        winning = winning[[c for c in winner_keep if c in winning]].copy()
        write_release(root, year, d, winning, nota)
    # 2007 education remains absent; its candidate and vote records come directly from SEC.
    d = pd.read_parquet(root / "data/extracted/2007/candidates.parquet")
    d["is_winner"] = d["rank"].eq(1)
    d["quota"] = d.reservation.isin(["W", "SCW"])
    old = g[g.election.eq(2007)]
    check = d.merge(
        old,
        left_on=["ward", "rank"],
        right_on=["ward", "eci_pos"],
        validate="one_to_one",
        suffixes=("", "_goyal"),
    )
    if (
        len(check) != len(d)
        or not check.votes.eq(check.votes_goyal).all()
        or not check.reservation.eq(check.resstatus).all()
    ):
        raise ValueError("2007 SEC/Goyal reconciliation failed")
    official_names = check.candidate_name.str.upper().str.replace(
        r"[^A-Z]", "", regex=True
    )
    compiled_names = check.eci_candname.str.upper().str.replace(
        r"[^A-Z]", "", regex=True
    )
    if not official_names.eq(compiled_names).all():
        raise ValueError("2007 candidate identity disagrees before attaching sex")
    d["candidate_source"] = "data/raw/2007/election_results.xls"
    d["source_sheet"] = "Detailed Result"
    d["education"] = pd.Series(None, index=d.index, dtype="string")
    d["graduate"] = pd.Series(pd.NA, index=d.index, dtype="Int64")
    d["sex_raw_goyal"] = check.gender.to_numpy()
    d["sex"] = check.gender.where(~check.gender_doubt.eq("yes")).to_numpy()
    d["sex_source"] = "goyal"
    winning = d[d.is_winner].copy()
    runner = d[d["rank"].eq(2)].set_index("ward").votes
    winning["runner_up_votes"] = winning.ward.map(runner)
    winning["margin"] = winning.votes - winning.runner_up_votes
    write_release(root, 2007, d, winning)
    auditdir = root / "data/extracted/source_audit"
    auditdir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(audit).to_csv(auditdir / "result_disagreements.csv", index=False)
    summary = []
    for year in [2007, 2012, 2017, 2022]:
        c = pd.read_parquet(root / f"data/release/{year}/candidates.parquet")
        w = pd.read_parquet(root / f"data/release/{year}/winners.parquet")
        e = edu[edu.year.eq(year)]
        summary.append(
            {
                "year": year,
                "candidates": len(c),
                "winners": len(w),
                "profile_education": int(e.education_raw_profile.notna().sum()),
                "classifiable_winner_education": int(e.graduate.notna().sum()),
                "graduate_conflicts": int(e.graduate_conflict.sum()),
            }
        )
    pd.DataFrame(summary).to_csv(root / "data/release/coverage.csv", index=False)
    (edudir / "schema.json").write_text(
        json.dumps(
            {
                "rows": len(edu),
                "key": ["year", "ward"],
                "columns": {
                    f.name: str(f.type)
                    for f in pq.read_schema(edudir / "winners.parquet")
                },
            },
            indent=2,
        )
        + "\n"
    )
    (edudir / "checksums.json").write_text(
        json.dumps(
            {
                p.relative_to(root).as_posix(): hashlib.sha256(
                    p.read_bytes()
                ).hexdigest()
                for p in edudir.glob("*.parquet")
            },
            indent=2,
        )
        + "\n"
    )
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--upstream", type=Path)
    a = p.parse_args()
    build(a.root, a.upstream or a.root.parent / "local_elections")
