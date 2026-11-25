# Verification of QC Review R01, SCOUR-COMPLETE

Verifier: Claude (AI reviewer), independent second read of `docs/QC_REVIEW_R01.md`. Findings need confirmation by the Engineer of Record before they are treated as closed.

Date: 2026-11-25
Repo: this repository. Code reviewed at main `4aaab25`. Review read at branch `qc-review-r01`, commit `4a8b1db` (`docs/QC_REVIEW_R01.md`, plus a HANDOFF.md entry).
Method: I read the code, docs and legacy engine first and formed my own findings. Then I read R01 and checked each finding against the code and against reruns. No code or legacy file was changed.
Units: ft, cfs, fps, psf.

## 1. Verdict on the review

**Grade: B (yellow).**

R01 is careful and mostly right. Every number I re-ran reproduced: Culverts 1, 2 and 4, the four FHWA example runs through the engine, H-03, H-04, M-02, M-03, M-07, C-02, the Section 7 jet decay table and power fit, M-13, H-02, and the legacy byte identity against Mew-Tools `e0cf993`. Its overall D for the repo is fair for a design tool at M1/M2.

Why it isn't an A:
- It missed a real block 10 bug. Option 2 names one riprap class and prints the pool geometry and thickness for a different stone (N-01).
- It missed that `TW` and `V_channel` silently default to 0. A missing TW flips the case to the low tailwater branch (N-02).
- One row in its safeguards table overstates things. Batch isolation fails when a single case has NaN or inf input (N-03).
- I could not independently confirm the HEC-14 Chapter 10 text it cites. The FHWA PDF returned only the front matter through Chapter 2 here (see Section 2). The Chapter 10 page and equation citations in R01 are consistent with the HEC-14 table of contents, but the equation text itself is UNVERIFIED by me.

## 2. Source access and limits

- HEC-14 3rd ed. (FHWA-NHI-06-086, 2006), FHWA PDF. Direct download was blocked in the review environment. The fetch tool returned 78,547 characters covering the front matter, TOC, Chapter 1 and part of Chapter 2. From that I **verified**:
  - Table 1.1: riprap basin Fr < 3; riprap apron footnote 8, "Culvert rise less than or equal to 1500 mm (60 in)"; apron Fr column "na".
  - TOC: 10.1.3 High Tailwater p. 10-4; 10.1.4 Riprap Details p. 10-4; 10.1.5 Design Procedure p. 10-5; 10.2 Riprap Apron p. 10-16; 10.3 Riprap Aprons After Energy Dissipators p. 10-19; Figure 10.3 "Distribution of Centerline Velocity for Flow from Submerged Outlets" p. 10-4; Table 10.1 "Example Riprap Classes and Apron Dimensions" p. 10-18.
- Chapter 10 equation text, Step 2/4/5 wording, and the published worked-example values: **UNVERIFIED** by me. Secondary sources (Purdue JTRP-2019/16 for INDOT; Tennessee EPSC Handbook 4.3.6) restate Eq. 10.4 as D50 = 0.2 D (Q / (g^0.5 D^2.5))^(4/3) (D/TW), the 0.4D to 1.0D tailwater limits, and an effective diameter for supercritical flow. These agree with the code and with R01. They are secondary, not governing.
- HEC-15 (2005), SCDOT RHDS (2009), SCDOT SWQDM, and SCDOT Spec 804: not opened. Every R01 citation to these is UNVERIFIED by me.
- Tests: `python -m pytest` gives 40 passed and 1 failed. The failure is `test_velocity_plot` (matplotlib not installed here). I did not install the requirements.txt packages, since that needs your OK. R01 reports 41/41 with matplotlib present, which is consistent. Bare `pytest` gives 3 collection errors (confirmed).

## 3. R01 findings, one by one

Legend: **Confirmed** = I reproduced it in code or by reading. **Disputed** = evidence says otherwise. **Unverified** = depends on a source I could not open; the code fact behind it is noted where confirmed.

### Critical

| ID | Call | Evidence |
|---|---|---|
| C-01 No-recommendation safeguard is nominal | Confirmed | `scour_complete.py:23-24` returns `recommendations: []` next to full `legacy.option_1/option_2/vertical_limits/banks`. `format_report` (legacy 762-863) has no status line. `reporting.py:14` writes it bare to `legacy_report.txt`. |
| C-02 Fr >= 3 still yields a basin | Confirmed | Probe `Vo=30, Q=30*14*2.8, D50_trial=1.3`: Fr 3.16, block 3 "Not applicable, Fr >= 3", trial gives "Riprap basin (Sec 10.1)", Option 2 "Class C basin: pool 4.9 ft deep, 49 ft pool + 24 ft apron, 63 ft wide". Gate is text only, legacy 523-524 vs 586-600. Fr < 3 limit verified in Table 1.1. |
| C-03 Missing V_LB gives a design from zeros | Confirmed | Culvert 1 without `V_LB`: L adopted 60 ft (true 108 ft), Option 1 "Class D 0 to 56 ft. Class B 56 to 60 ft." No warning. This is **unconservative** (shorter, smaller stone). |

### High

| ID | Call | Evidence |
|---|---|---|
| H-01 Step 4 exit velocity check missing | Confirmed (code) / Unverified (HEC-14 text) | No exit depth or velocity is computed anywhere. Legacy 608 says "use the Sec 10.1 basin exit check" and stops. I did not read Step 4 itself. |
| H-02 HY-8 tailwater datum not checked | Confirmed (fixture) | Demo `.hy8` line 190: relief pipe outlet invert 100.70; line 70: channel invert 99.16. Parser passes TW = 4.29 ft. Depth above pipe invert = 103.45 - 100.70 = 2.75 ft. `outlet_invert_ft` is parsed (`hy8_io.py:219`) and never used. Real HY-8 convention is UNVERIFIED, as R01 says. |
| H-03 Multiple barrels as one outlet | Confirmed | 1 x 48 in pipe at 60 cfs: ye 1.772, Fr 1.264, TW/ye 0.56. 3 pipes at 180 cfs: ye 3.070, Fr 0.960, TW/ye 0.33. HEC-14 test geometry ranges cited from 10.1.1: Unverified. |
| H-04 Mismatched brink inputs still drive design | Confirmed | `Vo=8`: "Does not match", then Fr 0.84, No pool, full Option 1. Box `ye` uses raw `yo` (legacy 409) while `A` uses `min(yo, D)` (legacy 500-501). With yo = 7 > D = 6: ye 7.0, A 84, Vo check "OK". |
| H-05 V_perm and tau_perm default silently | Confirmed (code) / Unverified (SWQDM table values) | Defaults at legacy 114-115 apply when keys are omitted; run proceeds. Whether 2.1 psf is the top of Table E.3 is not verified by me. |
| H-06 Validation accepts NaN, strings, non-physical | Confirmed | NaN and inf pass `<= 0` checks. String `yo` raises TypeError. `V_LB=[-5,2,3,4]` accepted (L target 24.4 ft). See N-03 for the batch effect. |
| H-07 Option 1 not a published HEC-14 design | Confirmed as judgment; HEC-14 and RHDS citations Unverified | Code logic matches the description (legacy 560-565, 647-649, 718-731). I agree it should carry an inference ID. |

### Medium

| ID | Call | Evidence |
|---|---|---|
| M-01 D50/ye <= 0.7 cited to wrong source | Unverified | Needs HEC-14 Step 2 text and HY-8 help. Plausible. |
| M-02 Block 9 skips HEC-15 Reynolds step | Confirmed (arithmetic) / Unverified (HEC-15 Table 6.1 values) | tau 6.768 psf, code D50 1.399 ft, u* 1.869 fps, Re* 2.15e5, D50 with F* 0.15 and SF 1.5 = 0.657 ft. Factor about 2.1, conservative. |
| M-03 Thickness ignores Dmax option | Confirmed (arithmetic) / Unverified (10.1.4 text, Dmax values) | 1.5 Dmax > 2 D50 for A (1.125 vs 1.0), B (1.95 vs 1.5), C (2.7 vs 2.6). 2 Dmax > 3 D50 for B only (2.6 vs 2.25). |
| M-04 Length rules are judgment | Confirmed | Rules exist as stated (legacy 468-483, 614-646). None carry an inference ID. |
| M-05 Low tailwater gets no design | Confirmed (code) / Unverified (Step 5 TW/yo wording) | TW = 0.5 on Culvert 1: L adopted "n/a, low tailwater", Option 1 "See block 7." |
| M-06 SCDOT selection logic, README too weak | Unverified | RHDS not opened. |
| M-07 Classes E and F missing, Dmax unconfirmed | Confirmed (code) / Unverified (SCDOT values) | Vo 20 fps: required D50 2.605 ft, code prints "Larger than D". Class B Dmax in code is 1.30. |
| M-08 Tests collect only under `python -m pytest` | Confirmed | Bare `pytest`: 3 collection errors. Upstream `pytest.ini` (blob 1804137) and `.github/workflows/tests.yml` exist at `e0cf993` and were not copied. |
| M-09 Orbit failure marks valid case as error | Confirmed by reading | `reporting.py:29-30` calls `export_orbit` after writing files; `visuals.py:26-27` raises for no basin; `export_batch` records the whole case as error. Not run (no plotly). |
| M-10 QC PDF thin | Confirmed by reading | `reporting.py:18-28`. Raw unrounded floats printed. |
| M-11 Real project ID in public repo | Confirmed | "US176" in `EXAMPLES`, legacy tests, README. Inherited from public upstream. |
| M-12 Parser only run on synthetic fixtures | Confirmed (fixture header) / Unverified (`SLRIPRAP` card meaning) | |
| M-13 `--flow 490` read as index | Confirmed | "flow index 490 out of range (0 to 4)"; `490.0` runs. |
| M-14 GUI gaps | Confirmed by reading | Not run here either. |
| M-15 `methods_apron` is stone size only; D' used in TW test | Confirmed (code) / Unverified ("high tailwater referral matches HEC-14") | D 5, yn 3, TW 4.5 raises "High tailwater: evaluate HEC-14 section 10.3". The TOC title of 10.3 is "Riprap Aprons After Energy Dissipators". Whether HEC-14 10.2 actually points high TW cases there is UNVERIFIED by me, so I would not mark that item "verified" yet. |

### Low

| ID | Call | Note |
|---|---|---|
| L-01 | Confirmed | `scour_complete.py:8`. |
| L-02 | Confirmed | `test_manual_eq106` re-tests the same formula; regression test only checks non-empty report. |
| L-03 | Confirmed | `validate()` sets `Wo` on the caller's object (legacy 139-140). |
| L-04 | Confirmed (engine 25.1 ft) / Unverified (FHWA LB = max(15 hs, 4 Wo)) | |
| L-05 | Confirmed | `e0cf993` is a commit; its tree is `a6d743a`. `examples/example_culv1.json` exists upstream, not copied. |
| L-06 | Confirmed | `visuals.py:10-11` plots zeros with the "Supplied HY-8 velocities" label. |
| L-07 | Confirmed | Surface deepest at mid of Lb, `visuals.py:33-38`. |
| L-08 | Confirmed | No upper bounds; tkinter not in requirements. |
| L-09 | Unverified | Errata date and HEC-11 archive status not checked. |
| L-10 | Confirmed | `except Exception` stores only `str(exc)`. |

### Sections 5, 7, 8 of R01

- 5.1 rebuild of Culverts 1, 2, 4: Confirmed (my values match R01's table).
- 5.2 engine runs on FHWA examples: engine-side numbers Confirmed (steep: Fr 2.203, hs 6.05, hs/D50 3.31, Ls 60.5, LB 90.75, WB 68.5; mild: A 12.34, ye 2.48, Fr 1.22, C0 1.62, hs 2.26, hs/D50 4.52; D50 0.65: hs 1.42, LB 25.1; D50 0.83: hs/D50 0.88; Chapter 1: hs 2.69 at Vo = Q/A, 2.81 at Vo 19; thickness 3.6/2.4; apron 0.432 ft). Published FHWA values: Unverified by me.
- 7 jet decay: Confirmed. L/De and VL/Vo for all 12 points match. Fit VL/Vo = 6.187 (L/De)^-1.0076 on the 9 points with L/De >= 10; max error 0.045 percent (R01 says "within 0.04 percent", a rounding nit). Log-log interpolation at L/De 10, 15, 20, 21 gives 0.597, 0.404, 0.302, 0.288. FHWA's example chart readings: Unverified. I agree with R01: the power law is a regression, not a design equation.
- 8 legacy preservation: Confirmed by blob hash. All seven legacy files and LICENSE match upstream `e0cf993`.

## 4. What R01 missed

### N-01 (High). Option 2 mixes the class label with trial-stone geometry.

- Where: legacy `_option_2`, lines 739-744. It prints `r.largest_valid_class` with `r.hs`, `r.Ls`, `r.La`, `r.Wb`. Those come from the **trial** stone (lines 592-600), and so do `t_approach` and `t_pool`.
- Evidence: Culvert 1 with `D50_trial = 0.5` (Class A): Option 2 says "Class B basin: pool 4.0 ft deep, 42 ft pool + 20 ft apron, 55 ft wide". The Class B pool by Eq. 10.1 is 1.82 ft; 4.0 ft is the Class A pool. Block 5 thickness is 2 x 0.5 = 1.0 ft, against 1.5 ft for Class B. R01's own C-02 probe hid this because it set the trial to 1.3 ft (Class C), the same as the largest valid class. With the default 0.75 ft trial at Fr 3.16, Option 2 prints "Class C basin: pool 9.0 ft deep", which is also the Class B geometry.
- Why it matters: the callout and the dimensions disagree. Built as printed, the lining is thinner than the named class needs. The text only ties out when the trial stone is the largest valid class, as in Culvert 1 as shipped, so the regression tests never see it.
- Fix (framework layer): build Option 2 from a stone check run at the named class, or name the trial class. Add a regression test with `D50_trial = 0.5`.

### N-02 (Medium). TW and V_channel silently default to 0.

- Where: legacy 100-101 (`TW: float = 0.0`, `V_channel: float = 0.0`). `validate()` allows TW = 0.
- Evidence: Culvert 1 JSON with `TW` removed runs as "Low tailwater", length "n/a", Option 1 "See block 7". With `V_channel` removed, the target falls to V_perm and the adopted length moves from 108 to 180 ft, and the "channel faster than permissible" finding disappears.
- R01 lists silent defaults for V_LB, V_perm, tau_perm, Ss, D50_trial and min_class, but not these two. TW is the one that flips the high/low tailwater branch and C0.
- Fix: require TW and V_channel in the framework input layer. Accept TW = 0 only when it is given explicitly.

### N-03 (Medium). One non-finite case kills the whole batch output.

- Where: `scour_complete.py:44-45`; same pattern in `reporting.py:13` and `gui.py:46`.
- Evidence: `run_batch([culv1 with Q=NaN, culv1])` returns both cases. Then `json.dumps(..., allow_nan=False)` raises `ValueError` and nothing is written for either case. Same with `Q=inf`.
- This disputes the R01 Section 10 row "Batch errors are isolated: Yes". It holds for exceptions inside `run_case`, but not for the export step. H-06 notes the single-case symptom but not the batch effect.

### N-04 (Low). Regime text claims the jet is submerged regardless of tailwater.

- Where: legacy 505-506.
- Evidence: Culvert 1 with TW = 0.5 ft (TW/ye 0.18, low tailwater) still prints "Supercritical at brink; tailwater submerges jet".
- Fix: drop the tailwater clause, or tie it to TW > yc.

### N-05 (Low). The HY-8 pool depth tie is text only, yet the decay stations depend on HY-8's basin length.

- Where: legacy 567-572, 609.
- Evidence: the decay stations are `LB x (1..4)` with LB from this code's trial stone, while `V_LB` was read at HY-8's own stations. If the trial D50 or the inputs differ from the HY-8 run, the tie check prints "Does not tie" and every protection-length station is still shifted. R01 7.3 flags the LB fallback, but not the case where the basin is valid and LB doesn't match.
- Fix: when V_LB is supplied and the HS tie fails, withhold blocks 6 to 8 and 10.

### N-06 (Low, docs). Section labels in VERIFICATION.md are equation numbers.

- Where: `docs/VERIFICATION.md` V02 "HEC-14 10.4-10.5 apron" and V05 "HEC-14 10.6 downstream stone".
- Evidence: per the HEC-14 TOC, Chapter 10 has sections 10.1 to 10.3 only. 10.4 to 10.6 are equation numbers. A future check by section will not find them.

## 5. Overall

- Agree with R01's D for the repo against its stated end state, and its A for legacy preservation.
- Agree with R01's fix order, with two additions near the top: N-01 (Option 2 geometry) next to C-02, and N-02 (TW and V_channel required) next to C-03.
- To close the Unverified items, someone needs to open the HEC-14 Chapter 10 pages (10-1 to 10-19) and HEC-15 Chapter 6 as page images. The review environment could not reach them. Further depth on the formulas will not change the verdict.

## 6. Reproduce

Scripts are in `docs/qc_probes/`. From the repo root, run each with `python -I docs/qc_probes/<name>.py .`. They only read the repo.
- `probe_edge_cases.py`: silent defaults, Fr gate, NaN/inf batch, V_LB zero/negative, yo > D, low-TW regime text, apron edge cases.
- `probe_option2_mismatch.py`: N-01.
- `probe_r01_numbers.py`: R01 Sections 5.2, H-03, H-04, M-02, M-03, M-07, C-02, Section 7 table.
- `probe_jet_decay_fit.py`: Section 7 fit and interpolation, M-15.

Sources used for Section 2:
- FHWA HEC-14 PDF (front matter and Chapters 1-2 only): https://www.fhwa.dot.gov/engineering/hydraulics/pubs/06086/hec14.pdf
- Purdue/INDOT JTRP-2019/16 (secondary): https://rosap.ntl.bts.gov/view/dot/55509/dot_55509_DS1.pdf
- Tennessee EPSC Handbook 4.3.6 Riprap Apron (secondary): https://www.tn.gov/content/dam/tn/environment/water/stormwater/epsc-handbook/dwr-npdes-sop-g-16-erosion-prevention-sediment-control-handbook-01092026-4.3.6%20-riprap-apron.pdf
