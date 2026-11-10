# Delhi local elections

Delhi municipal elections in **2007, 2012, 2017, and 2022**, with source-linked candidate and winner records. Original State Election Commission (SEC) documents are retained alongside research-deposit and MyNeta evidence. A documented 272-ward link supports 2007–2012 comparisons; later cycles remain separate election cross-sections.

| Election | Actual candidates | Winners | Winners with classifiable graduate status |
|---|---:|---:|---:|
| 2007 | 2,570 | 272 | 0 |
| 2012 | 2,423 | 272 | 226 |
| 2017 | 2,538 | 272 | 263 |
| 2022 | 1,349 | 250 | 245 |

NOTA is stored separately for 2017 and 2022 and is never treated as a candidate. Graduate coverage is based on available transcriptions, with unresolved graduate-status conflicts excluded; it is not the number of independently verified affidavits.

- [2007 release](data/release/2007/), [2012 release](data/release/2012/), [2017 release](data/release/2017/), and [2022 release](data/release/2022/): candidates, winners, schemas, and hashes.
- [Same-ward 2007–2012 handoff](data/release/persistence/wards_2007_2012.parquet): all 272 linked wards, reservation histories, selected winner sex, and legal continuity evidence; [dictionary](data/release/persistence/dictionary.md). Later election pairs are not linked by ward number.
- [Education source audit](data/release/education/winners.parquet): all 794 winners in 2012/2017/2022, with source categories, degree descriptions, disagreements, and verification status. [Unresolved records](data/release/education/unresolved.csv) retain missing and disputed outcomes.
- [Source report](report.md) and [dictionary](data/release/dictionary.md) explain coverage and source decisions.

## Sources and receipts

The [source ledger](data/source_manifest.jsonl) records URLs, download times, byte counts, and SHA-256 hashes. [The ward frame](data/frame.json) enumerates all 272 wards: 104 North, 104 South, and 64 East. The SEC lists two PDFs for ward 141 with identical extracted text but different bytes; both source versions are retained. Byte-identical downloads share a stored file.

[Raw SEC PDFs](data/raw/2012/) include every ward's candidate list, the 18-page winner/runner-up report, and the 2012 reservation notification. [Archive captures](data/raw/archive/) include the old election pages and two surviving ward result sheets. The archive is supplementary; the live SEC collection supplies complete candidate-list coverage. Original nomination affidavits were not recovered in this search.

Research deposits and previously collected MyNeta/directory receipts reside once in sibling `../local_elections/`. [The upstream manifest](data/upstream_manifest.json) pins inputs by hash. Goyal's full 53-file V1.0 deposit is indexed in `../local_elections/data/reference/goyal_9xpv4i/manifest.json`; existing originals are referenced rather than copied. This checkout and its upstream companion must travel together for an offline rebuild.

## Earlier elections

The [coverage assessment](report.md#earlier-elections-and-longitudinal-limits) records the incomplete 1997/2002 holdings. The 1997 scan covers only wards 1–32; those records are not presented as a complete election release.

## Handling

Official SEC records determine reservations and winner results. For 2012, Goyal supplies the candidate roster, ranks, votes, sex, and candidate education. Candidate counts match the SEC separately in every ward, and all 272 winner vote counts and reservations match. This does not independently validate every losing candidate's name, votes, or sex.

The complete 2022 vote comparison corrects two Aya Nagar candidate counts and resolves a one-vote SEC report error using the signed return; [the report](report.md#four-cycle-coverage) documents these decisions and unresolved ward-total arithmetic.

Winner education uses cached individual MyNeta profiles where available, with Goyal's raw education as fallback in 2012/2017 and TCPD in 2022. Unspecified education remains unclassified. The release excludes the problematic Karekurve-Ramachandra–Lee education field. Source-coded sex is retained separately; two previously documented winner-sex errors are corrected and one disputed winner remains unknown. Neither sex nor education is inferred from names, quotas, or another person's record.

Goyal's three text-valued ward IDs are converted to integers. The SEC's ward 240 list skips serial number 8 but contains the printed total of ten candidates; the parser checks record counts and uniqueness rather than assuming consecutive serial numbers. Printed ward numbers are election-specific and are not a cross-election boundary crosswalk.

## Reproduce

Python 3.11+, Poppler (`pdftotext`), and the packages in `requirements.txt` are needed. An existing data environment can be used.

```sh
python -m pip install -r requirements.txt
make build
make test
```

`python scripts/fetch_deposits.py` verifies or restores the pinned Goyal deposit in the upstream collection.

`make fetch` resumes the original 2012 SEC collection. `python scripts/fetch_sources.py --restore` verifies or restores all sources in the saved ledger, including the additional cycles. `python scripts/fetch_archives.py` verifies/resumes the pinned captures; `--discover` searches for additional captures to review. Archive searches and replay use the `wayback` package, following `piedomains`; live requests use Requests with urllib3 retries. Parsing and release construction are offline. The build reuses the pinned upstream MyNeta parser to verify cached winner profiles in all three education cycles. No source updates are silently admitted into the release.
