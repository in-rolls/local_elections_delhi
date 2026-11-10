# Delhi same-ward comparison

One row per 2007 ward retained for the 2012 election. All 272 wards remain in the file; restrict `reserved_woman == 0` for the open-election comparison. The comparison is prior quota versus prior nonquota, not male versus female prior winners. Nonquota seats may elect women. Missing winner sex remains null. `ward_links.parquet` contains the geographic key/provenance projection, with the same types.

| Column | Arrow type | Nullable | Meaning |
|---|---|---|---|
| `year` | int16 | False | Outcome election year: 2012. |
| `prior_year` | int16 | False | Prior reservation election year: 2007. |
| `ward_no` | string | False | Outcome-election ward identifier. |
| `prior_ward_no` | string | False | Prior-election ward identifier. |
| `body` | string | False | 2012 municipal corporation, from the SEC candidate-list frame. |
| `prior_body` | string | False | Municipal Corporation of Delhi in 2007. |
| `ward_name` | string | False | 2012 ward name, as printed in the SEC result report. |
| `prior_ward_name` | string | False | 2007 ward name, as printed in the SEC spreadsheet. |
| `link_basis` | string | False | The 2012 order distributes the existing 2007 wards among three corporations. |
| `link_source_path` | string | False | Repository-relative continuity notification. |
| `link_source_page` | int16 | False | One-based physical PDF page establishing continuity. |
| `link_source_sha256` | string | False | SHA-256 of the continuity notification. |
| `reserved_raw` | string | False | 2012 recorded category: G/W/SC/SCW. |
| `prior_reserved_raw` | string | False | 2007 recorded category: G/W/SC/SCW. |
| `reserved_woman` | int8 | True | 2012 women quota: 1=yes, 0=no; independent of winner sex. |
| `prior_reserved_woman` | int8 | True | 2007 women quota: 1=yes, 0=no; independent of winner sex. |
| `reserved_caste` | string | False | 2012 caste quota: NONE or SC. |
| `prior_reserved_caste` | string | False | 2007 caste quota: NONE or SC. |
| `winner` | string | False | 2012 winner name from the SEC result report. |
| `winner_woman_raw` | string | False | Unchanged Goyal winner sex code: F or M. |
| `winner_woman` | int8 | True | Selected 2012 winner sex: 1=female, 0=male, null=unresolved. |
| `winner_woman_source` | string | False | Selected winner sex source recorded by the 2012 release. |
| `winner_woman_decision` | string | False | source_retained, correct, or unresolved; no name/quota inference. |
| `winner_woman_review_url` | string | True | Evidence URL from the pinned sex-review ledger, if reviewed. |
| `winner_woman_review_evidence` | string | True | Verbatim evidence note from the pinned sex-review ledger. |
| `reserved_source_path` | string | False | 2012 official result report supporting reservation and winner identity. |
| `reserved_source_page` | int16 | False | One-based physical 2012 result-report page. |
| `reserved_source_sha256` | string | False | SHA-256 of the official 2012 result report. |
| `prior_reserved_source_path` | string | False | 2007 SEC election spreadsheet. |
| `prior_reserved_source_row` | int32 | False | One-based spreadsheet winner row; Detailed Result sheet. |
| `prior_reserved_source_sha256` | string | False | SHA-256 of the official 2007 spreadsheet. |
