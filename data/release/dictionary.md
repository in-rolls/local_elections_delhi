# Delhi release dictionary

Each year directory has `candidates.parquet` (one actual candidate), `winners.parquet` (one elected ward), a schema with types and row counts, and SHA-256 checksums. Candidate keys are `(year, ward, rank)`; winner keys are `(year, ward)`. NOTA has its own `(year, ward)` file in 2017 and 2022. Null means unavailable or unresolved, never an inferred zero. The 2012-specific dictionary supplies its additional SEC candidate-list fields.

## Election records

| Fields | Meaning and source |
|---|---|
| `year`, `ward` | Election year and election-specific ward identifier. 2017 uses the corporation suffix N/S/E. These are not longitudinal identifiers. |
| `rank` | Source-reported result order; 2017 may have gaps because NOTA is excluded. In 2022 this is candidate order excluding NOTA, with Aya Nagar's erroneous ordering corrected. Ties need not share a rank. The 2007 order is checked to have nonincreasing votes. |
| `candidate_name`, `party` | SEC name and full party name in 2007; Goyal in 2012/2017; OpenCity/TCPD in 2022. Later releases use standard abbreviations for recognized parties and retain other full names. |
| `votes`, `votes_raw_compilation` | Vote count used in the release and, where applicable, the untouched compiled count. Winner values are checked against SEC results; documented source decisions may supersede compiled counts. Losing-candidate votes in 2012/2017 are not all independently verified. |
| `rank_raw_compilation`, `report_order` | Untouched compiled position and SEC detailed-report order, respectively. The report includes NOTA in its ordering; the compilation puts NOTA last. |
| `votes_report`, `vote_source`, `vote_source_page`, `winner_votes_raw_report` | SEC detailed-report count; source and one-based PDF page for the selected count; untouched winner-summary count. The signed ward 236 return supersedes the report. |
| `is_winner` | Reported rank equals 1. |
| `reservation`, `quota` | G, W, SC, or SCW; quota is true for W/SCW. Describes the office, not the winner's sex. 2007/2012 and 2022 have official-source checks; 2017 categories come from Goyal. |
| `sex`, `sex_raw`, `sex_raw_goyal`, `gender_doubt`, `sex_source` | Source-recorded M/F or null, with raw labels and review information where available. Goyal supplies 2007/2012/2017; TCPD supplies 2022. No sex inference from names. Explicit Goyal doubt flags are treated as missing. The 2012 release applies the separately documented corrections. |
| `age`, `age_raw` | Numeric years and verbatim source value. Nonnumeric entries such as Unknown become null in `age`. Source is Goyal in 2017 and TCPD in 2022. |
| `occupation_raw`, `assets_raw`, `liabilities_raw` | Goyal's 2017 profession and declared financial totals (Indian rupees). Retained source fields, not independently verified financial measures. |
| `candidate_source`, `source_sheet`, `source_row`, `goyal_excel_row` | Original source file, worksheet where applicable, and one-based row including headers. |
| `ward_name`, `electors`, `reported_total_votes` | SEC ward label, electorate, and reported ward total in the 2007 spreadsheet. Reported totals are preserved rather than silently reconciled. |
| `winner_name`, `winner_party`, `winner_votes` | SEC result-report values for 2017/2022, subject to documented signed-return checks. |
| `runner_up_name`, `runner_up_party`, `runner_up_votes`, `margin` | SEC runner-up fields and winner-minus-runner-up margin. Deferred 2017 return scans do not supply runner-up party; it remains null. In 2007 runner-up votes come from the second candidate in the SEC spreadsheet. |
| `result_source`, `source_page`, `result_verification` | Source PDF path, one-based page(s), and whether the result came from a machine-readable SEC report or a manually inspected signed return. |
| `age_profile`, `occupation_profile`, `pending_cases`, `convicted_cases` | Cached MyNeta age, profession, and separate pending-case and conviction counts. Retained from the upstream parser; unavailable records stay null. |

## Education records

The separate education file has one record for every 2012/2017/2022 winner, even without a profile. Winner releases include these audit fields where applicable. Candidate education outside the winner sample remains the compilation's transcription and has not undergone the same profile check.

| Fields | Meaning and source |
|---|---|
| `education` | Selected category: MyNeta where available, otherwise Goyal (2012/2017) or TCPD (2022). Unresolved comparable-category conflicts are null. TCPD's coarse category labels are retained without pretending they identify an exact school grade. |
| `education_raw_profile`, `education_raw_goyal`, `education_raw_tcpd` | Untouched source categories. |
| `education_details_profile`, `education_details_goyal` | Verbatim degree/school description from MyNeta's education section or Goyal's school field. These descriptions are evidence for review, not automatically inferred degrees. |
| `graduate`, `graduate_raw_profile`, `graduate_raw_secondary` | Nullable 1/0. MyNeta/Goyal Graduate, Graduate Professional, Post Graduate, and Doctorate are 1; named school grades, Literate, and Illiterate are 0. Others/Unknown/Not Given are null. TCPD Graduate/Postgraduate are 1 and Inter/Higher/Middle/Primary/Illetrate are 0; Other is null. A known disagreement on graduate status makes the selected value null. |
| `category_disagreement` | Goyal and MyNeta have different explicit category labels; these are comparable detailed taxonomies. TCPD's coarser labels are not compared as exact categories. |
| `graduate_conflict` | Both sources classify graduate status and disagree. |
| `education_source` | Transcription used or preferred before unresolved-conflict handling. Does not imply the original affidavit was checked. |
| `education_status` | missing; secondary_source; category_conflict; graduate_conflict; or degree_independently_corroborated. A category conflict can still have agreed graduate status. |
| `affidavit_verified` | Whether the original affidavit was checked. False for the current collection; an independent biography is not an affidavit. |
| `independent_education_source` | Independent source corroborating the degree, when available. Rajni Abbi's university CV is the documented current case. |
| `profile_url`, `profile_cache_path`, `profile_sha256`, `profile_capture` | MyNeta URL, cached response path relative to the upstream qualification_audit directory, UTF-8 body hash, and collection timestamp. |
| `affidavit_filename_tcpd` | Original filename supplied by TCPD. A filename is not a recovered document or verified download URL. |

The quota/non-quota comparison must include all non-quota winners, including women. Published counts and rates should show missingness separately by quota status. No education values are inferred from occupation, age, sex, quota status, or relatives.

## Source-audit tables

`candidate_results_2022.csv` has one row per compiled candidate or NOTA entry (1,599), with original and selected votes, both source orders, the SEC row text, and source page. The join uses ward and candidate order excluding NOTA, with checked exceptions in wards 51 and 157; ward 195 has a documented shortened-name match. Every left-hand record must match once and pass a name check. No unmatched record is dropped. `result_disagreements.csv` records the three count disagreements and decisions.

`ward_totals_2022.csv` has one row per ward (250). `Valid_Votes` and `Total_Votes` preserve the compilation's columns; `valid_votes_report` preserves the detailed SEC report. `candidate_plus_nota_votes` sums the selected records. The five inspected returns supply `valid_votes_signed`, `rejected_votes_signed`, and `tendered_votes_signed`; these are null elsewhere. `report_minus_sum`, `compilation_minus_sum`, and `signed_minus_sum` compare each valid-vote total with the selected sum. Sources, pages, hashes, and review notes accompany the signed values. Rejected and tendered ballots are not added to candidate counts. Ward 27's inconsistent signed valid total is retained explicitly.
