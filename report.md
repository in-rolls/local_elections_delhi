# Delhi municipal elections: source audit

The releases cover **four general elections (2007, 2012, 2017, and 2022)**, with 8,880 candidate records and 1,066 winner records. These counts are election-specific records, not unique people or unchanged geographic units. Education is classifiable for 734 of the 794 winners in the three later cycles; original affidavits have not been systematically recovered.

## 2012 source comparison

The 2012 release contains **2,423 candidates and 272 winners**. Original SEC PDFs cover all wards. We also recovered two ward result sheets and old election pages from the Internet Archive. The election records establish results and reservations; they do not supply education or independently establish every candidate's sex.

## What agrees

Tanushree Goyal's [replication deposit](https://doi.org/10.7910/DVN/9XPV4I) contains 2,423 candidates for 2012. After converting three text-valued ward IDs to integers, candidate counts agree with the SEC lists in **every ward**. All **272 winner vote counts and reservation categories** agree with the [official result report](https://sec.delhi.gov.in/sites/default/files/SEC/generic_multiple_files/2012winnerrunnerup.pdf).

Among **226 winners** with classifiable education in both Goyal and the cached individual MyNeta profiles, graduate status agrees in **100%** of cases. Both draw on affidavit/MyNeta information, so this is a consistency check, not independent validation of the underlying affidavits.

## Confirmed discrepancies

The Karekurve-Ramachandra–Lee [AJPS deposit](https://doi.org/10.7910/DVN/0QOVCH) has a serious problem in its 2012 education field. Among **183 jointly classified winners**, its graduate indicator agrees with the cached individual profiles in **53.6%** of cases. Agreement expected from the two marginal graduate rates is **53.2%**. In contrast, declared assets agree exactly with Goyal for **227 of 234 jointly recorded winners (97.0%)**. The education discrepancy therefore cannot readily be explained by all the rows referring to different people. These comparisons do not establish how the discrepancy arose, nor do they test the papers' caste or public-service findings.

The discrepancy is present in the original Stata deposit, not introduced by Dataverse's tabular export or our import. The original `datasetfull.dta` matches Dataverse's published MD5 and file size, and its `edu_recoded` values agree row for row with the tabular export for all 7,819 records, including all 2,308 records from 2012. The [original-file receipt](../local_elections/data/delhi/interim/qualification_audit/sources/varun_datasetfull_original_receipt.json) preserves the download URL, published checksum, and our SHA-256.

An independent source confirms at least one substantive error. The deposit assigns **Rajni Abbi (ward 11)** education code **0**, defined in its codebook as “Not educated.” Her [University of Delhi faculty CV](data/raw/education_validation/rajni_abbi_du_cv.pdf), page 1, records a **PhD in 2003**, as well as three earlier degrees; page 2 identifies her municipal service. The SEC winner record and deposit match uniquely on BJP and **12,947 votes**; declared assets also match Goyal exactly at **₹21,522,003**. Goyal and the individual MyNeta profile both report a doctorate. This independently supports their coding for this person, while leaving the wider profile collection subject to source verification.

This comparison uses the more complete individual-profile collection and an SEC winner join. Its denominators differ from the earlier audit that compared a MyNeta winner-summary page (160 jointly classified education records); both show approximately chance-level agreement for the deposit's education field.

Goyal's winner sex codes also require two corrections already established in the manuscript audit: ward **111**, Raj Kumari, M → F; ward **254**, Mahak Singh, F → M. The [official directory](../local_elections/data/delhi/raw/sex_validation/official_directory_2016.pdf), printed pages 321 and 334, supplies explicit titles; the cached ADR women-winners list also supports ward 111. Ward **115**, Dimple Chadha, remains unresolved. The release retains the original codes and review decisions, leaves that outcome missing, and does not assign sex from names or reservation status.

## Differences that are not established errors

The AJPS deposit contains **2,308** 2012 rows, compared with **2,423** SEC/Goyal candidates, and its `wardnumber` field is missing on all 2012 rows. A unique winner-votes/party match links **269 of 272 winners** to the SEC report; ambiguous or unmatched keys are not forced. The candidate-count difference is an unresolved coverage difference, not proof that 115 candidates were incorrectly omitted from the published analysis.

## Release choices and receipts

Use SEC winner results and reservations; Goyal's candidate records; cached individual profiles for winner education where available; and the documented sex review. Missing or disputed information stays missing. Ten candidate sex outcomes, including one winner, remain unknown. Candidate education outside the winner sample has not received the same profile-level check. The graduate comparison describes the 226 classifiable winners, not all 272: 47 of 111 quota winners (42.3%) and 47 of 115 non-quota winners (40.9%) are graduates. Non-quota winners include women. Agreement between Goyal and MyNeta does not substitute for inspecting original affidavits; those originals have not yet been recovered for a systematic education audit. Treat the release education as the best-supported available coding, not as fully independently validated truth, and do not use the AJPS deposit’s 2012 education field for this comparison.

[The row-level comparison](data/extracted/2012/winner_comparison.csv) includes source values, SEC PDF pages, Goyal spreadsheet row numbers, and profile URLs and hashes. [The inventory](data/extracted/2012/candidate_list_inventory.csv) links every ward to its original PDF. [Source hashes](data/source_manifest.jsonl), [upstream hashes](data/upstream_manifest.json), and [numerical summaries](data/extracted/2012/comparison_summary.json) make each reported comparison reproducible. The original PDFs, cached HTML, research codebooks, and untouched deposits are retained.

## Four-cycle coverage

Checked November 8, 2026. NOTA is excluded from candidate counts and retained separately.

| Election | Actual candidates | Elected wards | Cached winner profiles | Winners with classifiable graduate status |
|---|---:|---:|---:|---:|
| 2007 | 2,570 | 272 | 0 | 0 |
| 2012 | 2,423 | 272 | 237 | 226 |
| 2017 | 2,538 | 272 | 267 | 263 |
| 2022 | 1,349 | 250 | 248 | 245 |

**2007:** The SEC Excel file supplies all 2,570 candidates. Candidate names (after case/punctuation normalization), ranks, votes, and reservations agree with Goyal for every record. Goyal supplies sex, with explicit doubt flags treated as missing. Neither source supplies education for this cycle.

**2017:** Goyal's 2,810 rows consist of 2,538 candidates and 272 NOTA entries. The three SEC winner reports cover 270 wards; signed returns for the deferred polls in 16-N and 40-E complete the 272-ward cycle. All winner vote counts agree with Goyal. Candidate counts agree with the SEC lists in every ward after using the deferred return for 40-E, which lists ten candidates rather than the earlier list's nine. This checks roster sizes and winner results, not every losing candidate's vote count. The signed returns reconcile candidate-plus-NOTA totals of 24,820 and 26,032 in 16-N and 40-E.

**2022:** The OpenCity/TCPD file contains 1,349 actual candidates and 250 NOTA entries. All 1,599 entries are linked to the SEC's detailed Form 18 report, using election-specific ward and result order, with candidate-name checks. NOTA is matched separately. Reviewed exceptions handle Aya Nagar's erroneous ordering, a tied vote count in Shakur Basti, and the shortened name of Dhirender Kumar Bunty Gautam in the report. [The complete comparison](data/extracted/source_audit/candidate_results_2022.csv) preserves source text, order, counts, and PDF pages.

The 2022 comparison identifies three vote-count disagreements:

| Ward and candidate | Compilation | SEC report | Selected | Evidence |
|---|---:|---:|---:|---|
| 157, Pooja | 8,683 | 79 | 79 | Signed return confirms 79; the compilation repeats Himani Ambawta's count. |
| 157, Bineeta Sharma | 0 | 103 | 103 | Signed return confirms 103. |
| 236, Mukesh Kumar Bansal | 15,069 | 15,070 | 15,069 | Signed return supports the compilation and contradicts the report. |

The release corrects Aya Nagar's votes and candidate order. It keeps ward 236's signed count and resulting margin of 7,476, while preserving the report's alternative. None of these changes alters a winner's identity. After correction, candidate-plus-NOTA votes sum to **7,335,824**, one below the SEC report's total because of its ward 236 error. NOTA votes sum to 57,545.

[Ward-total checks](data/extracted/source_audit/ward_totals_2022.csv) retain reported totals separately from sums. For ward 41, the compilation's valid-vote total of 3,070 is truncated: both the report and signed return show 30,704, with two rejected votes recorded on the signed return. For ward 212, both official sources show 25,968, compared with 25,969 in the compilation. Ward 27 requires a different treatment: its candidate-plus-NOTA sum and the SEC report give 37,338, but the signed return itself prints 37,346 valid votes and eight rejected votes. This internal discrepancy remains flagged; no candidate count is changed to force agreement. The five inspected signed returns and their hashes are indexed in [the reference ledger](data/reference/2022_signed_returns.csv).

## What to trust for education

Use the source-audited winner education file, with its missingness and disagreement flags. It prefers cached individual MyNeta profiles and otherwise uses Goyal (2012/2017) or TCPD (2022). The 2012 comparison above establishes why the Karekurve-Ramachandra–Lee education field is excluded. It does not independently validate every retained transcription.

For 2017, Vinay Rawat (50-N) is listed as 12th Pass by MyNeta and 8th Pass by Goyal. The selected category is missing, but both imply non-graduate status. For 2022, Poonam Bhardwaj (ward 134) is Graduate in TCPD and 8th Pass in MyNeta. Both the selected category and graduate indicator remain missing. The two winners without cached 2022 profiles use TCPD transcriptions; their source status is explicit. Others, Unknown, and Not Given remain unclassified. Verbatim school/degree descriptions are preserved for review rather than converted into guessed qualifications.

The strongest accessible education route is the cached candidate-level MyNeta transcription, cross-checked against Goyal's education category and school/degree text. Her README says municipal affidavit information was manually added, but the public deposit does not contain the original municipal affidavit scans. Its `AE_WomenAffidavits.xls` concerns state assembly candidates and is not municipal evidence. Candidate education outside the winner sample has not undergone the same profile audit.

The [contemporaneous ADR report](data/raw/2012/adr_winners_report.pdf) covers 236 winners and records 93 graduates or higher (pages 16–17). It provides a dated consistency check within the ADR/MyNeta source chain. It gives Rajni Abbi's doctorate year as 2004, whereas her university CV says 2003. Both establish a pre-2012 doctorate; the exact year remains discrepant.

Sampled cached profiles from 2012, 2017, and 2022 contain no original-affidavit links. Goyal's public deposit does not include the municipal scans. The old SEC Wayback search retained 154 distinct URLs without locating an affidavit/nomination URL. The 2022 compilation retains affidavit filenames, but filenames are not verified download URLs. Attempts to reach the former 2022 SEC portal and the current affidavit endpoint timed out. These results do not establish that the originals are unavailable. The remaining direct route is obtaining the underlying municipal scans from Goyal, ADR/Delhi Election Watch, or SEC/returning-officer records. No request has been sent, and no record is labeled affidavit-verified.

## Earlier elections and longitudinal limits

The SEC's 1997 reservation schedule covers 134 wards, but its linked results scan covers only wards 1–32. The 2002 pages provide notifications and aggregates; a complete individual candidate file was not confirmed. Neither cycle is presented as a complete release. By-elections remain separate from general elections.

Ward identifiers are election-specific: the 134-ward system, the later 272-ward councils, and the 250-ward 2022 council cannot be linked by number alone. The 2017 boundary changes also require a crosswalk. The documented exception is 2007–2012, established below.

All new originals are stored once in this repository; existing research deposits and MyNeta caches remain in `../local_elections/` and are pinned by hash. The [source ledger](data/source_manifest.jsonl), [upstream manifest](data/upstream_manifest.json), [release dictionary](data/release/dictionary.md), and per-election schemas and checksums document the build.

## Same-ward quota persistence comparisons

The [2007–2012 handoff](data/release/persistence/wards_2007_2012.parquet) contains **272 geographically linked wards**. The [2012 reservation notification](data/raw/2012/reservation_order.pdf), physical page 1, explicitly identifies the February 7, 2007 delimitation order and distributes those same 272 wards among North, South and East Delhi. Thus the link rests on the legal ward frame, not equal numbers or similar names. The [original 2007 delimitation scan](data/raw/2007/delimitation_order.pdf) is also retained. Sixteen printed ward names differ across the election result sources; [the differences](data/release/persistence/ward_name_differences.csv) remain visible rather than being silently standardized. They do not override the notification's identity link.

There are **134 nonquota wards in 2012**, not 136. The official notification reserves 52 North, 53 South and 33 East wards for women, totaling 138. Among the nonquota wards, 44 were women-reserved in 2007 and 90 were not. The observed outcomes are 3 women among 44 formerly reserved wards and 2 among 89 formerly nonquota wards; ward 115 remains unresolved. These give 133 observed outcomes. The comparison is prior quota assignment versus prior nonquota assignment, including women elected without quotas in the comparison group. The new handoff changes none of the 272 reservation histories or selected winner-sex values in the manuscript's previous Delhi input.

The handoff preserves original Goyal sex codes, the two established corrections, the unresolved decision and their evidence. It does not infer sex from names or quotas. Both sides of the join must contain exactly one winner for every ward. Ward identifiers are strings; women indicators are nullable Int8; unknown outcomes are never zero-filled. The [geographic link table](data/release/persistence/ward_links.parquet), [source pins](data/release/persistence/sources.json), [schema](data/release/persistence/schema.json), [dictionary](data/release/persistence/dictionary.md) and [coverage](data/release/persistence/profile.json) accompany the data. `make persistence` rebuilds this handoff offline, and `make test` checks the contracts, sources, corrections, nulls and round trip.

Geographic continuity does not establish random assignment. The 2012 notification, physical pages 3–4, describes Scheduled Caste selection by population and alternating women/general categories in ward order within each corporation. Any causal interpretation still requires the paper's assignment argument and comparisons; this source audit establishes the units and measurements.

**2012–2017:** The [SEC press note of March 14, 2017](data/raw/2017/election_press_note.pdf), physical page 1, states that the 272 ward boundaries were redrawn, renamed and renumbered. The retained [North](data/raw/2017/delimitation_north.pdf), [East](data/raw/2017/delimitation_east.pdf), and [South](data/raw/2017/delimitation_south_schedule.pdf) schedules describe wards through census-town codes, old census ward numbers, enumeration blocks and localities. These provide a route to reconstructing geographic overlap, but an old census ward appearing inside a new ward is not evidence that the entire elected ward remained intact. No same-ward links for this pair have yet been validated.

**2017–2022:** The [October 17, 2022 final order](data/raw/2022/delimitation_order_english.pdf), physical page 1 (printed page 352), establishes 250 newly delimited wards and describes their basis in 2011 census enumeration-block maps. The following English tables retain block lists and localities. The 2017 schedules use six-digit block/sub-block codes and sometimes partial-block or village entries; the 2022 order uses grouped block numbers and ranges. For example, the 2017 North schedule's first row lists 003601, 003602, 003700 and 013500, while the 2022 order lists 36–37,135 for the corresponding locality. Dropping suffixes without checking split blocks and boundaries could create false identity links. No later same-ward panel is released, and the builder rejects both later pairs. These are limitations of the validated crosswalk, not a claim that every ward necessarily changed or that reconstruction is impossible.

The remaining person-level issues are unchanged: ward 115's sex and the stated education conflicts remain unresolved, and original affidavits have not been systematically recovered. The existing source-prioritized election releases remain unchanged by this geography work.
