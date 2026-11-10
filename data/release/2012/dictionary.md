# Release dictionary

The candidate key is `(year, ward, rank)`; the winner key is `(year, ward)`. Both files are Parquet; null is missing, never zero or an inferred value. String fields retain source spellings. No cross-election ward continuity is asserted.

| Fields | Meaning and source |
| --- | --- |
| `year`, `ward`, `rank` | Election year, numeric ward ID, and reported candidate rank from Goyal; ward IDs normalized from mixed numeric/text cells. |
| `candidate_name`, `party`, `votes` | Goyal's candidate name, party abbreviation, and votes. All winner vote counts checked against SEC. |
| `is_winner` | Reported rank equals 1. |
| `reservation`, `quota` | SEC category G, W, SC, or SCW; quota is true for W/SCW. This describes the office, not the candidate's sex. |
| `sex`, `sex_raw_goyal`, `gender_doubt`, `sex_source` | Best available M/F or null; untouched Goyal code and doubt flag; source is goyal, review_correct, or review_unresolved. Goyal's explicit doubt flags produce null outcomes. |
| `education`, `education_raw_goyal`, `education_source` | Selected education category; untouched Goyal category; source is goyal or myneta_profile. Cached individual profiles take priority for winners where available. |
| `graduate` | Nullable integer: 1 for Graduate, Graduate Professional, Post Graduate, or Doctorate; 0 for Illiterate, Literate, 5th/8th/10th/12th Pass; null for missing or other categories. |
| `goyal_excel_row` | One-based spreadsheet row, including the header, in CandidateElectionData_original.xlsx (stored upstream as goyal_candidates.xlsx). |
| `sec_candidate_list`, `sec_candidate_list_url` | Local source PDF path and original URL for the ward. |
| `profile_url` | Cached MyNeta profile URL for winners; null for losing candidates. |
| `winner_name`, `winner_party`, `winner_votes` | Winner-only columns: official SEC spellings, full party name, and votes. |
| `runner_up_votes`, `margin`, `pdf_page` | Winner-only columns: SEC runner-up votes, winner-minus-runner-up margin, and one-based PDF page in the official result report. |

The row-level comparison contains raw Goyal and Varun education fields and the profile education used for validation. Its asset fields are comparison inputs, not release recommendations. No candidate names or sex codes are reconstructed from missing values in Varun's file.
