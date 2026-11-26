# QC Review R01: SCOUR-COMPLETE

| | |
|---|---|
| Review type | Independent, adversarial internal quality control (QC) review |
| Reviewed commit | `4aaab25` (Checkpoint early graphics and reporting scaffold), 2026-11-25 |
| Review date | 2026-11-25 |
| Reviewer | Claude (AI reviewer). Findings need confirmation by the Engineer of Record before they are treated as closed. |
| Scope | `HANDOFF.md`, `README.md`, `docs/`, all source and tests, upstream Mew-Tools baseline |
| Engine changes | None. No file under `legacy/`, and no `.py` file, was modified by this review. |

Units are US customary (ft, cfs, fps, psf) throughout.

Abbreviations: FHWA = Federal Highway Administration. HEC = Hydraulic Engineering Circular. SCDOT = South Carolina Department of Transportation. RHDS = SCDOT Requirements for Hydraulic Design Studies. SWQDM = SCDOT Stormwater Quality Design Manual. TW = tailwater depth. Fr = Froude number at the culvert brink.

---

## 1. Grades

| Category | Grade | Color | One-line basis |
|---|---|---|---|
| **Overall** | **D** | 🔴 Red | Core equations are right. Safeguards fail, published checks are missing or not enforced, and most target features do not exist yet. |
| Engineering accuracy | C | 🟡 Yellow | Eq. 10.1 to 10.6 verified and reproduce four FHWA examples. Applicability gates, the basin exit check, tailwater datum, and multi-barrel handling are not defensible as coded. |
| Software integrity | C | 🟡 Yellow | 41 of 41 tests pass with `python -m pytest`. Bare `pytest` fails collection. Invalid and missing inputs produce design text. |
| Architecture | D | 🔴 Red | The plan in `docs/ARCHITECTURE.md` is sound. The code is a thin wrapper with no result model, method registry, batch manifest, or alternative logic. |
| Verification | D | 🔴 Red | All ten register items were pending and no test had been run. Status reporting was honest, which is the one strength. |
| Usability | D | 🔴 Red | The inherited command line works. The GUI is a JSON text box, was not runnable in the review environment, and shows the ten-block report as escaped text. |

Legacy preservation, graded separately: **A** 🟢. All seven legacy files and the license are byte-identical to upstream.

The grade is against the stated end-state requirements and against any use for design. As an M1/M2 checkpoint the project is recoverable, and the repo already says it is not verified for design.

## 2. Bottom line

1. The inherited HEC-14 Chapter 10 math is correct. I rebuilt Culverts 1, 2 and 4 from the published equations in separate code and matched the engine to 1e-16. The engine also reproduces four published FHWA examples within rounding.
2. The "no recommendations" safeguard does not work. `recommendations` is an empty list, but the same result carries a full block 10 design summary with riprap classes, lengths, key depths and bank slopes, and `legacy_report.txt` carries no development notice (C-01).
3. Two input conditions produce a wrong design summary with no warning: Fr at or above 3 (C-02) and missing HY-8 jet velocities (C-03).
4. The HEC-14 basin exit velocity check (Section 10.1.5, Step 4) is not implemented. In FHWA's own example that check rejects a trial basin (H-01).
5. HY-8 jet velocities appear to be reproducible without manual transcription. The twelve transcribed values from Culverts 1, 2 and 4 fall on one curve of VL/Vo against L/De. Section 7 gives the evidence and the limits on that conclusion.

Further depth on the equations will not change these conclusions. The open work is gating, inputs, and missing checks, not the formulas.

## 3. Basis of review and limits

### 3.1 Sources opened in this review

| Source | Edition | How it was read |
|---|---|---|
| FHWA HEC-14, Hydraulic Design of Energy Dissipators for Culverts and Channels | 3rd ed., FHWA-NHI-06-086, July 2006. FHWA's library listing still shows this as the current edition, with an errata date of 10/01/2012. | FHWA PDF, text extraction. Table 1.1, Chapter 1 example, Sections 10.1 to 10.3. |
| FHWA HEC-15, Design of Roadside Channels with Flexible Linings | 3rd ed., FHWA-NHI-05-114, Sept. 2005 | PDF text extraction, Chapter 6. |
| SCDOT Requirements for Hydraulic Design Studies | May 26, 2009. SCDOT's hydraulic design page lists it as the effective version, supplemented by Hydraulic Design Bulletins. | SCDOT PDF, Sections 1.1.8, 2.2.2, 2.2.11, 2.3. |
| SCDOT Stormwater Quality Design Manual | Main manual cover dated December 2014. Appendix B and Appendix E, which show no date in the text read. | SCDOT PDFs. |
| SCDOT Instructional Bulletin 09-2 and a draft SCDOT gabion standard sheet | As posted | Search excerpts only, for riprap class D50 and thickness. |
| HY-8 help, Riprap Basin and Apron page | Aquaveo XMS wiki | Web page. |
| Upstream `Lowcountry-creator/Mew-Tools` | commit `e0cf993` | Cloned and compared by blob hash. |

### 3.2 Limits on this review. Read before relying on it.

- The reference PDFs were read through a text extraction tool, not as page images. Equations 10.4 and 10.5 were garbled in extraction. I confirmed their form by reproducing both the SI and the customary-unit worked examples (0.131 m against a published 0.13 m, and 0.432 ft against a published 0.43 ft). Page numbers come from the extracted page footers.
- HEC-14 Figure 10.3 was not viewed as an image. Its curve values in this review come from FHWA's own worked-example readings and from the HY-8 values stored in the repo.
- **UNVERIFIED** in this review: SCDOT Standard Specifications Section 804 (riprap class gradations and Dmax), SCDOT Standard Drawing 804-305-00, the HEC-14 errata list, HEC-15 Chapter 3 pages (Eq. 3.1 is cited from a cross-reference in Chapter 6), HEC-22 4th edition content, and the format of a real HY-8 `.hy8` or `.rst` file.
- The GUI was not executed. The review environment has no `tkinter`. `gui.py` was reviewed by reading only.

### 3.3 Missing inputs and the assumption made for each

| Missing input | Assumption used | Could it change a result? |
|---|---|---|
| The source workbook (Outlet Protection Calcs) | Expected values in `legacy/test_hec14_outlet_protection.py` are the Excel cells, as its docstring says. | No. The independent rebuild does not depend on it. |
| HY-8 Energy Dissipation printouts for Culverts 1, 2 and 4 | The `V_LB` and `HS_hy8` values in `EXAMPLES` were transcribed correctly. | Yes, for Section 7 only. |
| A real HY-8 project and result file | None. Parser findings are limited to the synthetic fixtures. | Yes. See M-12. |
| Side slope for the FHWA exit velocity example | z = 2, inferred because it reproduces the printed Ac = 113.9 ft2 and Tc = 74.4 ft. | No. |

## 4. Tests executed

Environment: Linux, Python 3.13.18, pytest 9.1.1, matplotlib 3.11.2, reportlab 5.0.1, plotly installed for the review.

| Command (from repo root) | Result |
|---|---|
| `python -m pytest -q` | **41 passed** in 0.78 s. 33 legacy, 8 new. |
| `pytest -q` | **3 collection errors.** `ModuleNotFoundError` for `scour_complete` and `methods_apron` in all three files under `tests/`. See M-08. |
| `python scour_complete.py c1.json --out out.json` | Runs. Output 11,289 bytes. Also runs from another working directory. |
| `python scour_complete.py batch.json --out out.json` with one bad case | Runs. Bad case isolated with its error text. |
| `reporting.export_case` and `export_batch` (no test exists for either) | Run. PDF, PNG, JSON, text and orbit HTML are written. See M-09 and M-10. |
| `visuals.export_orbit` (no test exists) | Runs for Culvert 1. Raises by design for a no-basin case. |
| `gui.py` | Not executed. No `tkinter` in the review environment. |

Timing: `run_batch` on 2,000 copies of Culvert 1 took 0.23 s. `export_batch` on 20 cases without orbit took 2.89 s and 3.9 MB. One orbit HTML file is 4.86 MB.

`HANDOFF.md` and `README.md` both say no tests had been executed. That is now superseded by the table above.

## 5. Independent reproduction

### 5.1 Culverts 1, 2 and 4

I wrote a separate script from the HEC-14 equations (it does not import the engine) and compared 35 values across the three cases. Maximum absolute difference: 1.1e-16.

| Quantity | Equation and inputs | Culvert 1 | Culvert 2 | Culvert 4 |
|---|---|---|---|---|
| D = rise - embedment, ft | | 6 | 5 | 6 |
| yc, ft | ((Q/Wo)^2 / g)^(1/3), g = 32.2 | 4.017 | 2.706 | 3.192 |
| Q/A, fps | Q / (Wo yo) | 16.315 | 5.052 | 8.171 |
| Fr | Vo / (g ye)^0.5, ye = yo | 1.719 | 0.398 | 0.724 |
| TW/ye | | 1.836 | 1.054 | 1.000 |
| C0, envelope | Eq. 10.2 | 2.4 | 2.4 | 2.4 |
| hs, ft at D50 = 0.75 ft | Eq. 10.1: ye (0.86 (D50/ye)^-0.55 Fr - C0) | 1.821 | -7.142 | -3.351 |
| hs/D50 | | 2.43 | no pool | no pool |
| LB, ft | Ls + La for a valid basin, else 4 Wo | 56 | 48 | 56 |
| Ls, La, WB, ft | max(10 hs, 3 Wo), max(5 hs, Wo), Wo + 2 LB / 3 | 42, 14, 51.33 | n/a | n/a |
| Length to target, ft | linear between HY-8 stations | 104.02 | 57.33 | 106.22 |
| Length adopted, ft | max(L, LB) rounded up to 6 ft | 108 | 60 | 108 |
| Required D50 by reach, ft | Eq. 10.6: 0.692 V^2 / (2 g (Ss - 1)), Ss = 2.65 | 1.735, 0.898, 0.253, 0.112 | 0.166, 0.120, 0.051, 0.022 | 0.435, 0.272, 0.090, 0.040 |
| Bed shear, psf | 62.4 TW S | 6.768 | no slope given | 0.741 |

The arithmetic is confirmed. That is not the same as the design being appropriate. Sections 6 and 10 cover that.

### 5.2 Published FHWA examples run through the engine

| HEC-14 (2006) example | Quantity | Published | Engine | Comment |
|---|---|---|---|---|
| Sec. 10.1.5, steep slope, pp. 10-8 to 10-10. 8 ft x 6 ft box, Q = 800 cfs, yo = 4 ft, Vo = 25 fps, TW = 2.8 ft, D50 = 1.83 ft | Fr | 2.2 | 2.203 | |
| | hs, ft | 6.0 | 6.05 | FHWA rounds Fr and D50/ye first. With Fr = 2.2 and D50/ye = 0.46 the result is 6.0. |
| | hs/D50 | 3.3 | 3.31 | |
| | Ls, LB, WB, ft | 60, 90, 68 | 60.5, 90.7, 68.5 | |
| Same example, TW = 4.2 ft | TW/ye, De ft | 1.05, 6.4 | 1.05, 6.38 | De = (4 A / pi)^0.5, A = 32 ft2 |
| | D50 by Eq. 10.6 at VL = 14.75, 10.5, 7.5, 7.0 fps | 1.42, 0.72, 0.37, 0.32 | 1.417, 0.718, 0.366, 0.319 | |
| Sec. 10.1.5, mild slope, pp. 10-14 to 10-15. 6 ft pipe, Q = 135 cfs, yo = 2.7 ft, Vo = 10.9 fps, TW = 2.0 ft, D50 = 0.5 ft | A ft2, ye ft, Fr | 12.35, 2.48, 1.22 | 12.34, 2.48, 1.22 | Circular path |
| | C0, hs ft, hs/D50 | 1.62, 2.3, 4.6 | 1.62, 2.26, 4.52 | |
| | Ls, LB, WB, ft | 23, 34.5, 29 | 22.6, 33.9, 28.6 | |
| Same, D50 = 0.65 ft | hs ft, hs/D50 | 1.4, 2.15 | 1.42, 2.18 | |
| | LB, ft | 24 | 25.1 | See L-04 |
| Chapter 1, pp. 1-11 to 1-13. 5 ft x 5 ft box, Q = 200 cfs, yo = 2.15 ft, TW = 0, D50 = 1.2 ft | hs, ft | 2.7 | 2.69 | With Vo = Q/A = 18.60 fps. With the published rounded Vo = 19 fps the engine gives 2.81 ft and flags a Vo mismatch. |
| | Pool, apron, ft | 27, 13.5 | 26.9, 13.4 | |
| | Thickness, ft | 3.6 approach, 2.4 remainder | 3.6, 2.4 | Confirms the 3 D50 and 2 D50 rule |
| Sec. 10.2 apron, p. 10-19. Q = 85 cfs, D = 5 ft, TW = 1.6 ft | TW used ft, D50 ft | 2.0, 0.43 | 2.0, 0.432 | `methods_apron.apron_d50` |

Reviewer hand check, not in the engine: the Step 4 exit check for the steep-slope example gives yc = 1.60 ft, Ac = 113.9 ft2, Tc = 74.4 ft, Vc = 800 / 113.9 = 7.02 fps against a published 7.0 fps.

One published value did not reproduce. For the mild-slope example with D50 = 0.83 ft, FHWA prints hs/D50 = 0.96 and the engine gives 0.88. Both fail the hs/D50 of 2 test, so the outcome is the same. The printed value could not be confirmed from the extracted text.

## 6. Findings

File references are to commit `4aaab25`. "Legacy" means `legacy/hec14_outlet_protection.py`.

### Critical

#### C-01. The no-recommendation safeguard is nominal. Design text is emitted for every case.

- **Where:** `scour_complete.py:23-24`; `reporting.py:14`; legacy 693-707, 718-746, 855-862.
- **Evidence:** For Culvert 1, `run_case` returns `recommendations: []` and, in the same object, `legacy.option_1` = "Class D 0 to 56 ft. Class C 56 to 108 ft. Bottom and both banks.", `legacy.option_2` with basin dimensions, `vertical_limits` with key depths and freeboard, and `banks` with a 2H:1V slope. `result["report"]` equals the legacy `format_report` text exactly and contains no development notice. `reporting.export_case` writes that text to `legacy_report.txt` as a standalone file.
- **Why it matters:** A reader who opens `legacy_report.txt` sees a complete "Design summary" from methods the repo itself lists as unverified. Requirement 7 (unverified methods cannot generate misleading design recommendations) is not met.
- **Correction (framework layer, no engine change):** Wrap the legacy text with a status header and footer on every output path. Do not write a bare `legacy_report.txt`. In `run_case`, move block 10 fields into a clearly named `legacy_unverified_design_text` group, or withhold them unless a verification status allows release. Keep the unmodified legacy text available only for regression comparison.

#### C-02. Fr at or above 3 does not stop a basin from being reported.

- **Where:** legacy 523-524 (text only), 541, 574-575, 586-600, 734-746. The only Fr check that acts is in `visuals.py:26`.
- **Evidence:** Culvert 1 with Vo = 30 fps and trial D50 = 1.3 ft gives Fr = 3.16. Block 3 prints "Not applicable, Fr >= 3". Block 4 prints "Riprap basin (Sec 10.1)". Block 10 prints "Class C basin: pool 4.9 ft deep, 49 ft pool + 24 ft apron, 63 ft wide".
- **Reference:** HEC-14 (2006) Table 1.1, p. 1-2: riprap basin, Fr < 3. The architecture plan already lists this as open prior QC.
- **Correction:** Make applicability a gate, not a label. When Fr is at or above 3, withhold block 5 geometry and Option 2 and say why.

#### C-03. Missing HY-8 jet velocities produce a protection length and class callout from zeros.

- **Where:** legacy 128 (default `[0, 0, 0, 0]`), 154, 468-483, 620-629, 633-649; `scour_complete.py:19-27`.
- **Evidence:** Culvert 1 JSON with `V_LB` removed returns length adopted = 60 ft and Option 1 = "Class D 0 to 56 ft. Class B 56 to 60 ft. Bottom and both banks." No warning appears in the result. The legacy command line prints a warning to stderr only on the `--hy8` path. The velocity chart labels the zeros as supplied HY-8 velocities.
- **Correction:** In the framework, treat `V_LB` as required for blocks 6, 7, 8 and 10. If absent or all zero, withhold those blocks and add a blocker. Also reject velocities that are negative, exceed Vo, or increase downstream (see H-06).

### High

#### H-01. The HEC-14 basin exit velocity check is not implemented.

- **Where:** legacy 591-602 and 734-746. Nothing computes exit depth or velocity.
- **Reference:** HEC-14 (2006) Section 10.1.5, Step 4, pp. 10-5 to 10-6. Critical depth at the basin exit is found from Q^2 / g = Ac^3 / Tc for a trapezoid of bottom width WB, and Vc = Q / Ac is compared with the allowable velocity. In the steep-slope example the third trial fails this check at 7.5 fps against 7 fps allowable.
- **Evidence:** Option 2 is reported for Culvert 1 with no exit check. Low tailwater cases print "use the Sec 10.1 basin exit check" (legacy 608) and stop.
- **Correction:** Add Step 4 as its own pure function with side slope as a required input. Until it exists, Option 2 should be labeled incomplete.

#### H-02. Tailwater depth from HY-8 is used without checking its datum.

- **Where:** `legacy/hy8_io.py:456` uses the `.rst` Tailwater Depth directly. The culvert outlet invert is parsed at line 219 and never used. The channel invert sits in `CHANNELGEOMETRY` (line 235-236).
- **Evidence:** In the demo project, the 48 in relief pipe has an outlet invert of 100.70 ft and the tailwater channel invert is 99.16 ft. The parser passes TW = 4.29 ft. Depth above the pipe invert is 103.45 - 100.70 = 2.75 ft. TW/ye moves from 2.38 to 1.53. In this case both are above 1.0 so C0 does not change, but any case near TW/ye of 0.75 to 1.0 will change C0, the high or low tailwater branch, or both.
- **Limit:** The fixtures are synthetic. Whether a real HY-8 result reports tailwater depth from the channel invert is **UNVERIFIED** here.
- **Correction:** Compute TW as tailwater elevation minus outlet bed elevation (invert plus embedment), report both values, and refuse to proceed when they disagree by more than a stated tolerance unless the Engineer confirms.

#### H-03. Multiple barrels are treated as one outlet with no published basis.

- **Where:** legacy 361-362 and 406-410 (circular area summed over barrels, then ye = (A/2)^0.5); `legacy/hy8_io.py:458` (Wo = barrels x span); `EXAMPLES` descriptions at legacy 873, 881, 889.
- **Evidence:** One 48 in pipe at 60 cfs gives ye = 1.772 ft and Fr = 1.264. Three identical pipes at 180 cfs give ye = 3.070 ft and Fr = 0.960 with the same flow per barrel. Fr crosses 1.0 and TW/ye drops from 0.56 to 0.33 only because the barrel count changed.
- **Reference:** HEC-14 (2006) Section 10.1 does not address multiple barrels. The tests behind Eq. 10.1 used pipes of 6 to 24 in and boxes about 1 to 2 ft wide (Section 10.1.1). A 14 ft wide twin box is well outside that geometry.
- **Correction:** Record this as an inference with its own ID. For circular outlets compute ye per barrel. State the single-equivalent-outlet assumption on every report. Do not present a result as verified for more than one barrel until a defensible basis is documented.

#### H-04. Inconsistent brink inputs are flagged in text but still drive the design.

- **Where:** legacy 509-514 (Vo check is a string, Fr uses the typed Vo), 500-501 against 408-409 (area uses yo capped at D, box ye uses uncapped yo).
- **Evidence:** Culvert 1 with Vo typed as 8 fps (Q/A is 16.3 fps) prints "Does not match" and then reports Fr = 0.84, no pool, and a full Option 1. Culvert 1 with yo = 6.5 ft above D = 6 ft uses A = 84 ft2 from the capped depth and ye = 6.5 ft from the uncapped depth.
- **Correction:** Fail the case, or require an explicit override with provenance, when |Q/A - Vo| exceeds tolerance. Use one depth for both A and ye. Treat a submerged, full-barrel outlet as a separate condition with its own applicability note.

#### H-05. Permissible velocity and shear default silently to single table values.

- **Where:** legacy 114-115 (`V_perm = 4.0`, `tau_perm = 2.1`).
- **Reference:** SWQDM Appendix E, p. E-4. Table E.2 permissible velocities run from 3 to 8 fps depending on cover, soil group and slope. Table E.3 lists 2.1 psf for retardance Class B only (12 in Bermuda or 18 in unmowed tall fescue, good stand). Class C is 1.0, Class D is 0.6 and Class E is 0.35 psf. Both tables sit in the grassed channel and swale section of a water quality manual.
- **Why it matters:** 2.1 psf is the highest value in the table, so the default is the least conservative choice. Culvert 4 passes the shear check at 0.741 psf against 2.1 psf and would fail against Class D or E. Applying these tables to a receiving stream at the 50-year event is engineering judgment, not a published SCDOT requirement.
- **Correction:** Remove the defaults in the framework layer. Require cover, soil group and slope, and record the table row used.

#### H-06. Validation accepts non-finite, non-numeric and non-physical inputs.

- **Where:** legacy 133-157.
- **Evidence:** Q = NaN passes validation, the run completes with a full Option 1, and `json.dumps(..., allow_nan=False)` then raises so the command line writes no output. A string for Q or inside `V_LB` raises `TypeError`. A negative channel velocity, `barrels = 2.5`, and jet velocities that increase downstream (`[11.741, 12.5, 4.145, 3.102]`, length adopted 150 ft) are all accepted.
- **Correction:** Add a validation layer in the framework that checks type, finiteness, sign and monotonic decay before the engine is called, and returns field-level messages.

#### H-07. Option 1 (lined channel, no pool) is not a published HEC-14 design and is not labeled as judgment.

- **Where:** legacy 560-565, 576-577, 647-649, 718-731.
- **Basis of concern:** Option 1 picks stone large enough that Eq. 10.1 returns hs at or below zero, then sizes reaches from the brink with Eq. 10.6 and the Figure 10.3 velocities. HEC-14 states Eq. 10.1 for hs/D50 of at least 2 (Step 2, p. 10-5), so hs at or below zero is outside the stated range. Section 10.3 presents Eq. 10.6 for aprons after an energy dissipator, with V as the dissipator exit velocity (p. 10-19). Section 10.1.3 points to Figure 10.3 and Section 10.3 for riprap downstream of a basin under high tailwater.
- **SCDOT context:** RHDS (2009) Section 2.3, Steps 5A.5 and 6D.5, pp. 59 and 62, call for a riprap pad or channel lining when outlet flow is subcritical and an energy dissipator when it is supercritical. Culvert 1 is supercritical at the brink (Fr = 1.72) and still receives Option 1 first.
- **Correction:** Carry Option 1 as an inference with its own ID and rationale. Tie eligibility to the RHDS subcritical or supercritical test. Do not list it ahead of a published method.

### Medium

#### M-01. The D50/ye upper limit of 0.7 is cited to the wrong source.

- **Where:** legacy 61-63 and 457; `legacy/README.md:98`.
- **Reference:** HEC-14 (2006) Step 2, p. 10-5, states only D50/ye of at least 0.1 and hs/D50 of at least 2. No upper limit appears in Section 10.1. The HY-8 help page says the model runs covered D50/ye from 0.1 to 0.7 and that the program rejects values outside that range.
- **Correction:** Keep the limit. Re-cite it as an HY-8 program limit and data range, not HEC-14 Step 2.

#### M-02. The block 9 riprap size is labeled HEC-15 but skips the Reynolds number step.

- **Where:** legacy 658-668.
- **Reference:** HEC-15 (2005) Eq. 6.8, p. 6-4: D50 >= SF d So / (F* (SG - 1)). Table 6.1: F* = 0.047 and SF = 1.0 for particle Reynolds number at or below 4e4; F* = 0.15 and SF = 1.5 at or above 2e5; linear between. Eq. 6.8 applies below 5 percent slope (p. 6-5).
- **Evidence:** Culvert 1: tau = 62.4 x 5.14 x 0.0211 = 6.77 psf. Engine D50 = 6.77 / (0.047 x 1.65 x 62.4) = 1.40 ft. Shear velocity = (32.2 x 5.14 x 0.0211)^0.5 = 1.87 fps and Re = 1.87 x 1.40 / 1.217e-5 = 2.15e5, so Table 6.1 gives F* = 0.15 and SF = 1.5 and D50 = 1.5 x 5.14 x 0.0211 / (0.15 x 1.65) = 0.66 ft.
- **Effect:** The engine is conservative on the bed by a factor of about 2 here. It is not the HEC-15 procedure, and banks are not checked.
- **Correction:** Implement Eq. 6.8 with Table 6.1 and the slope limits, or relabel the result as a conservative screening value.

#### M-03. Riprap thickness ignores the Dmax alternatives.

- **Where:** legacy 599-600.
- **Reference:** HEC-14 (2006) Section 10.1.4, p. 10-4: floor and sides 2 D50 or 1.5 Dmax; the foreslope at the outlet 3 D50 or 2 Dmax. SCDOT's pipe end riprap table (Standard Drawing 804-305-00 as excerpted in Instructional Bulletin 09-2) uses a minimum of 2 x D50.
- **Evidence:** With the class table in the code, 1.5 Dmax exceeds 2 D50 for Class A (1.12 against 1.00 ft), Class B (1.95 against 1.50 ft) and Class C (2.70 against 2.60 ft). 2 Dmax exceeds 3 D50 for Class B (2.60 against 2.25 ft).
- **Correction:** Report both and state which governs. Dmax values need Section 804 confirmation first (M-07).

#### M-04. Protection length rules are judgment and are not labeled as such in the report.

- **Where:** legacy 468-483, 614-629, 633-646.
- **Rules in the code:** target velocity is the larger of permissible and channel velocity; minimum length is 1 LB; length is rounded up to 6 ft; velocity between stations is linear; each LB reach is sized on the velocity at its upstream end.
- **Published support:** HEC-14 Step 4 defines the allowable basin exit velocity as the larger of the channel normal velocity and a stability-based velocity, and Section 10.3 ties the length of protection to the difference between exit and channel velocity without giving a number. The rest is judgment.
- **Effect of linear interpolation:** For Culvert 1 the linear length to 7.02 fps is 104.0 ft. Using the curve in Section 7 it is 99.6 ft. Linear is conservative because the decay curve is convex.
- **Correction:** Add each rule to the inference register and print the IDs in block 7.

#### M-05. Low tailwater cases get no design and no exit check.

- **Where:** legacy 605-608, 622-624, 720-721.
- **Reference:** HEC-14 Step 5, p. 10-6, says no added riprap is needed beyond the basin when TW/yo is at or below 0.75. Step 5 uses TW/yo while Section 10.1.3 uses TW/ye. They match for a box and differ for a pipe. The engine uses TW/ye (legacy 515-516).
- **Correction:** For low tailwater run Step 4 and report the basin exit velocity. Record the TW/ye choice as an inference.

#### M-06. SCDOT's own selection logic is not implemented, and the README understates SCDOT adoption of HEC-14.

- **Where:** `README.md:4`, `HANDOFF.md:4`, `docs/VERIFICATION.md` (V07).
- **Reference:** RHDS (2009) Section 2.2.11, p. 50, requires every culvert outlet to be checked for scour potential with HEC-14 methods and ties the choice of riprap lining or dissipator to the outlet Froude number and soil. It classes soils with K above 0.4 as highly erodible and 0.25 to 0.4 as moderately erodible. Section 2.3 Step 5A.5, p. 59, sets riprap extent from HEC-14 Figure 10.4 for subcritical outlets and sends the outfall channel to HEC-11 and HEC-15. Section 2.2.2, p. 48, sets the 50-year design storm for primary and interstate routes and 25-year for secondary.
- **Correction:** State that SCDOT requires HEC-14 by reference, citing RHDS Section 2.2.11. Add soil K, the subcritical or supercritical branch, and the Figure 10.4 reference to the M4 decision engine scope. Note that SWQDM Appendix B.1.3 has a separate outlet protection procedure for construction-phase pipe outlets that does not reference HEC-14.

#### M-07. SCDOT riprap Classes E and F are missing and Dmax values are unconfirmed.

- **Where:** legacy 50-55, 288, 300-301.
- **Reference:** SWQDM Appendix B, Table B.1, p. B-5: Class A D50 0.5 ft, Dmax 0.75 ft; Class B 0.75 and 1.33; Class C 1.30 and 1.80. A draft SCDOT standard sheet lists C 1.30, D 1.80, E 2.25 and F 2.85 ft D50 with pay items for Classes B through F.
- **Evidence:** D50 for A through D matches. The code has Class B Dmax as 1.30 ft against 1.33 ft in Table B.1. Class D Dmax of 2.25 ft is **UNVERIFIED**. At Vo = 20 fps, Eq. 10.6 needs 2.60 ft and the engine prints "Larger than D" where Class F (2.85 ft) would cover it.
- **Correction:** Confirm the table against the current SCDOT Standard Specifications Section 804, add E and F in the framework class table, and cite edition and section.

#### M-08. Tests only collect under `python -m pytest`, and upstream test configuration was not migrated.

- **Where:** `scour_complete.py:8`; `tests/test_framework.py:1-2`; no `pytest.ini` or `conftest.py`.
- **Evidence:** Bare `pytest` gives three collection errors. `tests/test_framework.py` imports `hec14_outlet_protection` only because `scour_complete` was imported first and edited `sys.path`. Upstream has `pytest.ini` (with `pythonpath`) and `.github/workflows/tests.yml`. Neither was copied, so `legacy/README.md:120-121` now describes CI that does not exist here.
- **Correction:** Add a root `pytest.ini` with `pythonpath = . legacy` and `testpaths = legacy tests`. Restore the CI workflow. This does not touch the engine.

#### M-09. Batch export reports valid cases as errors and scales poorly with orbit output.

- **Where:** `reporting.py:29-30`, `37-45`; `visuals.py:26-27`, `43`.
- **Evidence:** With `orbit=True`, Culvert 2 (no basin) writes its PDF, PNG, JSON and text, then raises from `export_orbit`, and `summary.csv` records the whole case as an error. Each orbit file is 4.86 MB because Plotly is embedded. `summary.csv` has only index, status and error. It carries no culvert name, event, length, class or governing result.
- **Correction:** Treat "no basin to draw" as a skip with a note. Use a shared Plotly script. Add engineering columns and a governing-event rollup per the M5 plan.

#### M-10. The QC PDF is not the report the architecture describes.

- **Where:** `reporting.py:18-28`.
- **Evidence:** One page with a title, the velocity chart, the inference list and, optionally, seven raw numbers such as "hs: 1.8212789916315084 ft". No project or culvert name, no ten-block report, no inputs, no rounding. The three chart series share one color and differ only by line style.
- **Correction:** Include identifiers, inputs, the ten-block text with the status wrapper from C-01, rounded values with units, and distinct series styling.

#### M-11. A real project identifier is in a public repository.

- **Where:** legacy 872, 880, 888; `legacy/README.md:14`, `114-115`; `legacy/test_hec14_outlet_protection.py:4`; `legacy/examples/HY8_Demo_Culverts.hy8:7` (designer initials); `HANDOFF.md` M6 entry.
- **Note:** `HANDOFF.md` already acknowledges this as inherited from the public upstream.
- **Correction:** Decide whether the baseline can be re-cut with generic labels (Project, Culvert 1). That changes strings only, not numbers, but it does break byte identity with upstream, so it needs the owner's decision.

#### M-12. The HY-8 parser has only been run on synthetic fixtures.

- **Where:** `legacy/hy8_io.py:192` (units flag parsed, never checked), `215-216` (embedment units), `427-431` (unit check covers two rows and passes when the label is blank); `legacy/examples/HY8_Demo_Culverts.hy8:8` states the fixtures are not HY-8 output.
- **Also:** The `.hy8` file stores energy dissipator inputs (`STARTENERGYDISSIPATION` to `ENDENERGYDISS`, including an `SLRIPRAP` card, demo lines 143-164). The parser skips them. If that card holds the riprap basin D50 and Dmax, the trial stone could be read instead of typed. The meaning of its fields is **UNVERIFIED**.
- **Correction:** Test against anonymized real HY-8 files before V08 is closed. Check the units flag. Confirm embedment units.

#### M-13. `--flow 490` is read as a column index, not a discharge.

- **Where:** legacy 907-919, 944; `legacy/README.md:39-41`.
- **Evidence:** `--flow 490` raises "flow index 490 out of range (0 to 4)". `--flow 490.0` works.
- **Correction:** In a framework adapter, treat an integer outside the column range as a discharge, or require an explicit prefix.

#### M-14. GUI gaps (static review only).

- **Where:** `gui.py:25`, `32-40`, `41-46`, `47-48`.
- **Observations:** The result tab shows `json.dumps` output, so the ten-block report appears as one escaped string and cannot be read as a report. Display uses `json.dumps` without `allow_nan=False`, so NaN can be shown and then fail on export. There is no HY-8 import, no chart, no PDF or text export, and no per-case inference list. Buttons are packed after an expanding text box and are the first thing clipped when the window is short. No GUI test exists.

#### M-15. `methods_apron.py` is a stone-size function, not an apron design, and one gate is an inference.

- **Where:** `methods_apron.py:11-12`, `14-22`, `23-26`.
- **Verified:** Eq. 10.4 form, the 0.4 D floor, the 60 in limit and the high tailwater referral match HEC-14 (2006) pp. 10-16 to 10-18.
- **Gaps:** HEC-14 limits tailwater to 0.4 D to 1.0 D and does not say whether the adjusted D' = (D + yn)/2 replaces D in that test. The code uses D' (lines 20 and 22). With D = 5 ft, yn = 3 ft and TW = 4.5 ft the code refuses a case that is inside 1.0 D. The function returns no class, length (Table 10.1), depth or width, has no specific gravity adjustment, and is not connected to `run_case`.

### Low

| ID | Where | Finding | Correction |
|---|---|---|---|
| L-01 | `scour_complete.py:8` | `sys.path` is edited at import. Works, but hides import order problems (M-08). | Package the project or use `pythonpath` in test config. |
| L-02 | `tests/test_m2_benchmarks.py:7-11`, `18-19` | `test_manual_eq106` checks the function against the same formula. `test_regression_cases_available` only checks the report is non-empty. | Replace with the FHWA examples in Section 5.2 and their published values. |
| L-03 | legacy 139-140 | `validate()` changes `Wo` on the caller's object for circular inputs. | In the framework, pass a copy and report derived values separately. |
| L-04 | legacy 595-597 | Ls + La gives 25.1 ft where FHWA's example uses LB = max(15 hs, 4 Wo) = 24 ft. The engine is longer by 1.1 ft. | Document as a conservative deviation. |
| L-05 | `HANDOFF.md:3`, `8`, `14` | "main tree e0cf993" is a commit hash; the tree is `a6d743a`. Commits `f0e76fe` and `60e21a3` each add one file; the other files named are in earlier commits. Upstream `examples/example_culv1.json` was not copied. | Correct in the next entry. |
| L-06 | `visuals.py:10-13` | Chart is drawn for low tailwater and zero-velocity cases with the same "Supplied HY-8 velocities" label. | Suppress or relabel. |
| L-07 | `visuals.py:33-38` | The conceptual surface puts the deepest point at mid-length of pool plus apron and curves the apron. HEC-14 Figures 10.1 and 10.2 show a pool followed by an apron. | Keep the I02 label. Draw pool and apron as separate segments when geometry is verified. |
| L-08 | `requirements.txt` | No upper bounds. `tkinter` is needed by `gui.py` and is not present in every Python build. | Note in README. |
| L-09 | `docs/ARCHITECTURE.md:3` | HEC-14 errata (FHWA lists 10/01/2012) are not mentioned. HEC-11, named in HEC-14 Step 5, is listed by FHWA as archived and superseded by HEC-23. | Add both to the M2 source list. |
| L-10 | `scour_complete.py:34-35` | `except Exception` turns programming errors into case errors with no type or traceback. | Record the exception type. Let unexpected types surface in tests. |

## 7. Jet velocity decay

### 7.1 What HEC-14 publishes

- Section 10.1.3 (p. 10-4) and Step 5 (p. 10-6): when tailwater is high (TW/ye above 0.75 in 10.1.3, TW/yo in Step 5), estimate the centerline velocity downstream from Figure 10.3 and size riprap with HEC-11 or Section 10.3.
- Figure 10.3 is a chart of VL/Vo against L/De. The worked example on p. 10-9 computes De = (4 A / pi)^0.5 with A equal to the brink flow area (yo x Wo for the box).
- HEC-14 gives the figure only. I found no equation for the curve in Section 10.1 or 10.3. The repo's statement that the figure must be digitized, not replaced with an arbitrary fit, is correct.

### 7.2 Can HY-8 values be reproduced without manual transcription?

Evidence says yes, subject to the limits in 7.3. For each stored case I computed De from the brink area and L = n x LB, then formed VL/Vo from the transcribed HY-8 velocities.

| L/De | VL/Vo | VL/Vo x L/De | Case |
|---|---|---|---|
| 5.49 | 0.8497 | 4.666 | Culvert 2 |
| 6.67 | 0.7907 | 5.270 | Culvert 4 |
| 7.93 | 0.7194 | 5.703 | Culvert 1 |
| 10.98 | 0.5533 | 6.077 | Culvert 2 |
| 13.33 | 0.4550 | 6.065 | Culvert 4 |
| 15.85 | 0.3820 | 6.057 | Culvert 1 |
| 16.48 | 0.3677 | 6.058 | Culvert 2 |
| 20.00 | 0.3024 | 6.048 | Culvert 4 |
| 21.97 | 0.2752 | 6.046 | Culvert 2 |
| 23.78 | 0.2540 | 6.040 | Culvert 1 |
| 26.66 | 0.2263 | 6.034 | Culvert 4 |
| 31.71 | 0.1901 | 6.027 | Culvert 1 |

Findings from that table:

1. Three different culverts interleave on one smooth curve. Predicting each interior point from its neighbors (log-log interpolation) gives errors of 0.05 percent or less for L/De of 13 and above, and up to 2.9 percent below 11 where the points are sparse and the curve bends.
2. The curve agrees with FHWA's own readings of Figure 10.3 in the p. 10-9 example: at L/De = 10, 15, 20 and 21 FHWA reads 0.59, 0.42, 0.30 and 0.28, and interpolation of the HY-8 points gives 0.597, 0.404, 0.302 and 0.288. The largest difference is 0.016, which is within chart-reading tolerance.
3. For L/De of 10 and above (nine points), VL/Vo = 6.187 (L/De)^-1.0076 fits within 0.04 percent. That is the reviewer's regression on stored values. It is **not** a published equation and must not be used for design.
4. Regenerating Culvert 1 from the Culvert 2 and 4 points alone gives 6.238 and 4.146 fps at 2 LB and 3 LB against HY-8 values of 6.235 and 4.145 fps. At 1 LB it gives 11.40 against 11.741 fps (sparse region). 4 LB is beyond the other two cases' range.

Conclusion: HY-8 appears to evaluate one fixed function of L/De, with De from the brink flow area and stations at multiples of LB. The four typed velocities are therefore derived values, not independent inputs.

### 7.3 Limits on that conclusion

- All twelve points are box culverts under high tailwater from one project. Circular outlets, L/De below 5.5 and above 32, and HY-8 versions other than the one used are untested.
- The values depend on LB, which the engine sets to 4 Wo when no valid basin exists (legacy 589). Whether HY-8 uses the same fallback is **UNVERIFIED**; the fit across Culverts 2 and 4 (no basin) is consistent with it.
- The stored velocities were transcribed by hand. A typo would look like scatter and none is visible, but the printouts are not in the repo.

### 7.4 Recommended path (best) and interim path (quick)

**Best Recommended Solution.** Digitize Figure 10.3 from the FHWA PDF with traceable points, store it as a table with source page and reading uncertainty, and interpolate in log-log space. Check it against the twelve points above plus a designed set of HY-8 runs that fill L/De from 3 to 10 and include a circular outlet. Accept when differences are inside a stated tolerance (the data above support about 1 percent for L/De of 10 and above). Keep typed HY-8 values as an optional cross-check that raises a flag when they disagree.

**Quick Fix Solution.** Keep manual entry, and add a consistency check now: compute L/De for each station and warn when a typed VL/Vo differs from the tabulated HY-8-derived curve by more than a set tolerance. That catches transcription errors and wrong LB without claiming an independent prediction.

Either way, label the result as a reproduction of Figure 10.3, not a jet model, and keep inference I04.

## 8. Legacy preservation

| Check | Result |
|---|---|
| `legacy/hec14_outlet_protection.py` against upstream `tools/hec14_outlet_protection/` at `e0cf993` | Identical. Blob `8192ba23`. |
| `legacy/hy8_io.py` | Identical. Blob `b6384973`. |
| `legacy/test_hec14_outlet_protection.py`, `legacy/test_hy8_io.py` | Identical. Blobs `dac49154`, `609a1b5c`. |
| `legacy/README.md` | Identical. Blob `6f246ea6`. |
| `legacy/examples/HY8_Demo_Culverts.hy8`, `.rst` | Identical. Blobs `9bbd78a2`, `7933e6a2`. |
| `LICENSE` | Identical to upstream. |
| Changes under `legacy/` since baseline commit `fc623f8` | None. |
| Ten-block report through the wrapper | `run_case(...)["report"]` equals `format_report(...)` character for character for Culverts 1, 2 and 4. |
| Legacy tests | 33 of 33 pass. |
| Not migrated from upstream | `pytest.ini`, `.github/workflows/tests.yml`, `examples/example_culv1.json`. |

The Mew calculations, the HY-8 parser and the text report format are preserved. The "HY-8 Exporter" PDF format mentioned in `docs/M2_BENCHMARKS.md` is not in either repository, so parity with it could not be checked.

## 9. Architecture evaluation

| Area | State at `4aaab25` | Assessment |
|---|---|---|
| Structure | Five flat modules, 217 lines of new code, `sys.path` edit to reach `legacy/`. | Fine for a spike. Not a base for M3 to M6. Needs a package, a typed result model with a schema version, and unit-bearing field names. |
| Method separation | The engine is one 220-line `analyze` covering blocks 2 to 10. | New methods cannot be selected, gated or benchmarked one at a time. M3's "separate pure functions" has one instance (`methods_apron.py`), not yet connected. |
| Scalability | 0.11 ms per case to compute. 0.14 s per case to export. | Compute is not a constraint. Export is dominated by chart and PDF generation and by 4.86 MB orbit files. |
| Batch | In-memory list, error isolation by broad `except`. | Works at the trivial level. No manifest (crossing, culvert, event), no source paths, no override provenance, no governing-event rollup, no per-case identifiers in the summary. |
| Alternative selection | None. `recommendations` is always empty. Legacy Option 1 and Option 2 text passes through unfiltered. | The M4 status model (verified, conditional, ineligible) does not exist. See C-01 and H-07. |
| GUI | JSON text box, run button, JSON export. | Does not meet the M6 tab list. Not executed in this review. |
| 3D visualization | Plotly surface for a valid basin only, parabolic shape, labeled conceptual. | Acceptable as a labeled concept. Not connected to the GUI. Nothing for the lined channel option. |
| Calculated detail export | Seven numbers printed in the PDF when `details=True`. | Not a drawing. No plan, profile or section. No dimensions for Option 1. |

Recommended structural order: (1) result model and status wrapper, (2) input validation layer, (3) method registry with per-method applicability and verification status, (4) HY-8 adapter with datum and unit checks, (5) batch manifest, (6) GUI and exports reading the same result model.

## 10. Engineering safeguards

| Safeguard claimed | Holds? | Evidence |
|---|---|---|
| No recommendations are emitted before verification | No | C-01 |
| Development status is visible on outputs | Partly | Present in JSON `status`, PDF title, chart title and GUI header. Absent from `legacy_report.txt` and from the `report` string. |
| Methods outside their domain are withheld | No | C-02 (Fr), H-04 (Vo and depth mismatch) |
| Missing inputs do not default silently | No | C-03 (jet velocities), H-05 (permissible values), legacy 118-124 (Ss, D50 trial, minimum class) |
| Interpolated velocities are not presented as predictions | Yes | I04 label on chart and in inference list |
| Batch errors are isolated | Yes | Bad cases return an error entry and the rest run |
| Apron method refuses out-of-range inputs | Yes | `methods_apron.py` raises for D above 5 ft, TW above D, and non-finite values |

## 11. Inference register: published requirement or engineering judgment

The register in `docs/VERIFICATION.md` has four inferences. The code contains at least twenty more assumptions that are not listed. Proposed additions follow. IDs are suggestions.

### 11.1 Published and verified in this review

| Item | Code | Source |
|---|---|---|
| Eq. 10.1 pool depth | legacy 436-442 | HEC-14 (2006) Eq. 10.1, p. 10-3 |
| Eq. 10.2 and 10.3 C0 | legacy 418-433 | p. 10-3. The source writes strict inequalities at 0.75 and 1.0. The functions are continuous there, so the code's handling of the boundaries has no effect. |
| ye = yo (box), (A/2)^0.5 (pipe), single barrel | legacy 406-410 | Section 10.1, p. 10-3 |
| hs/D50 >= 2 and D50/ye >= 0.1 | legacy 62, 64 | Step 2, p. 10-5 |
| Ls, La and LB minimums | legacy 595-597 | p. 10-3 |
| WB = Wo + 2 LB / 3 (3:1 flare) | legacy 598 | Worked examples, pp. 10-8 and 10-14 |
| 3 D50 on the approach, 2 D50 elsewhere | legacy 599-600 | Section 10.1.4; Chapter 1 example, p. 1-13 |
| High tailwater threshold 0.75 | legacy 67 | Section 10.1.3, p. 10-4 |
| Eq. 10.6 | legacy 445-447 | Section 10.3, p. 10-19 |
| Riprap basin Fr < 3; apron rise <= 60 in (footnote 8); SAF basin Fr 1.7 to 17 | legacy 69-70, 520-526 | Table 1.1, p. 1-2 |
| Eq. 10.4, D' for supercritical flow, 0.4 D floor, Table 10.1 | `methods_apron.py`, `docs/M2_BENCHMARKS.md` | Section 10.2, pp. 10-16 to 10-19 |
| Bed shear tau = gamma d So | legacy 659 | HEC-15 (2005) Eq. 3.1, as cross-referenced in Chapter 6 |
| HEC-14 required for SCDOT culvert outlets | n/a | RHDS (2009) Section 2.2.11, p. 50 |
| 50-year design storm, primary routes | `EXAMPLES` | RHDS (2009) Section 2.2.2, p. 48 |
| SCDOT D50 for Classes A, B, C, D | legacy 50-55 | SWQDM Table B.1 (A to C); SCDOT draft standard sheet (C to F). Section 804 not opened. |

### 11.2 Engineering judgment or program behavior, not a published requirement

| Proposed ID | Assumption | Code | Status |
|---|---|---|---|
| I05 | Multiple barrels act as one outlet: Wo = barrels x span, pipe area summed before ye | legacy 361-362; `hy8_io.py:458` | Judgment. H-03. |
| I06 | D50/ye must not exceed 0.7 | legacy 63 | HY-8 limit and data range. M-01. |
| I07 | LB = 4 Wo when no valid basin, used as station spacing | legacy 589 | Judgment. HY-8 behavior UNVERIFIED. |
| I08 | Target velocity = larger of permissible and channel velocity, applied to downstream extent | legacy 614-618 | Extended from HEC-14 Step 4. M-04. |
| I09 | Minimum protection length = 1 LB | legacy 625 | Judgment |
| I10 | Length rounded up to 6 ft | legacy 627 | Judgment |
| I11 | Linear velocity between stations | legacy 468-483 | Judgment. Conservative. |
| I12 | Each LB reach sized on velocity at its upstream end | legacy 633-646 | Judgment. Conservative. |
| I13 | Option 1 lined channel: stone chosen so Eq. 10.1 gives no pool, Eq. 10.6 applied from the brink | legacy 560-565, 647-649, 718-731 | Judgment. H-07. |
| I14 | Receiving channel shear uses TW as depth and SWQDM Table E.3 limits | legacy 659-660 | Judgment. H-05. |
| I15 | F* = 0.047 and SF = 1.0 at any Reynolds number; bed only | legacy 666-667 | Simplification of HEC-15. M-02. |
| I16 | Default permissible velocity 4 fps and shear 2.1 psf | legacy 114-115 | Judgment. H-05. |
| I17 | HY-8 Tailwater Depth is depth above the outlet bed | `hy8_io.py:456` | UNVERIFIED. H-02. |
| I18 | High tailwater test uses TW/ye, not TW/yo | legacy 515-516 | Choice between two HEC-14 statements. M-05. |
| I19 | Thickness from D50 only | legacy 599-600 | Partial use of Section 10.1.4. M-03. |
| I20 | Basin width for multiple pipes uses barrels x diameter | `legacy/README.md:90-91` | Judgment |
| I21 | Tolerances: 0.1 fps on Vo, 0.05 ft on HY-8 pool depth | legacy 511, 569 | Judgment |
| I22 | Tailwater and depths measured above the embedded bed; D = rise - embedment | legacy 100, 498 | Judgment. Depends on HY-8 output convention, UNVERIFIED. |
| I23 | Critical depth reported as D when still supercritical at 0.94 D, said to match HDS-5 and HY-8 | legacy 376-380, 392-394 | Claim UNVERIFIED |
| I24 | Riprap apron shown as applicable for any shape with rise <= 60 in | legacy 520-522 | Eq. 10.4 is recommended for circular culverts (p. 10-17). Full rise is used, not hydraulic rise. |
| I25 | Apron tailwater limits tested against D', not D | `methods_apron.py:20-22` | Judgment. M-15. |
| I03 (existing) | Key depths, 0.5 ft freeboard, 2H:1V banks, geotextile | legacy 695-701 | Listed, but still printed for every case with no label in the report. |

## 12. Check of statements made in the repo

| Statement | Location | Result |
|---|---|---|
| HEC-14 apron example is in Section 10.2, customary units, p. 10-19 | `docs/M2_BENCHMARKS.md:2` | Confirmed |
| Q = 85 cfs, D = 5 ft, TW = 1.6 ft, use 2 ft, D50 = 0.43 ft, Class 2 (6 in), length 20 ft, thickness 1.65 ft, end width 28.3 ft | `docs/M2_BENCHMARKS.md:3` | Confirmed, all values |
| Eq. 10.6 hand check: 69.2 / (64.4 x 1.65) = 0.6512 ft at 10 fps | `docs/M2_BENCHMARKS.md:4` | Arithmetic confirmed (0.65123) |
| Figure 10.3 is graphical, uses equivalent diameter and velocity ratio | `docs/M2_BENCHMARKS.md:5` | Confirmed |
| Legacy copied from upstream and unchanged | `HANDOFF.md:3` | Confirmed by blob hash. "tree e0cf993" should read "commit e0cf993". |
| Culvert 1 and 2 input values | `HANDOFF.md:14` | Match `EXAMPLES` |
| FHWA methods "not independently confirmed" as SCDOT adoption | `README.md:4` | Too weak. RHDS (2009) Section 2.2.11 requires HEC-14 for culvert outlets. |
| SCDOT limits are in SWQDM Appendix E, Tables E.2 and E.3 | `legacy/README.md:72`, legacy 12 | Tables exist on p. E-4. The defaults are single picks from them (H-05). |
| Valid basin needs 0.1 <= D50/ye <= 0.7 per HEC-14 | `legacy/README.md:98` | Lower bound confirmed. Upper bound is HY-8, not HEC-14 (M-01). |
| Table 1.1 footnote 8 limits the apron to 60 in rise | legacy 69 | Confirmed |
| CI runs on Python 3.11 to 3.13 | `legacy/README.md:120-121` | True upstream. Not true in this repo (M-08). |

## 13. Recommended order of reconciliation

No engine change is proposed until these are discussed. Items 1 to 4 can all be done in the framework layer.

1. C-01: status wrapper on every report path and removal of the bare legacy text export.
2. C-02, C-03, H-04, H-06: validation and applicability gates ahead of the engine call.
3. M-08 and L-02: test configuration, CI, and the FHWA examples from Section 5.2 as real benchmarks.
4. H-05, M-07: required permissible inputs with provenance, and a confirmed SCDOT class table through Class F.
5. H-01: Step 4 exit velocity check as a new verified function.
6. H-02, M-12: HY-8 adapter with datum and unit checks, tested on anonymized real files.
7. H-03, H-07, Section 11: owner decisions on multi-barrel handling and on Option 1, then update `docs/VERIFICATION.md`.
8. Section 7: Figure 10.3 table and HY-8 comparison runs.
9. M-11: confidentiality decision on inherited project labels.

Decisions needed from the Engineer of Record: whether Option 1 stays as a labeled judgment method (H-07), how multiple barrels are to be treated (H-03), which thickness rule governs (M-03), and whether inherited project labels are re-cut (M-11).

## Appendix A. How to reproduce the probes

All probes call `scour_complete.run_case` or the legacy functions with the inputs below. `base` is `asdict(EXAMPLES["culv1"])`.

| Finding | Input change | Field to read |
|---|---|---|
| C-01 | none | `report`, `legacy.option_1`, `legacy.vertical_limits`, `recommendations` |
| C-02 | `Vo=30.0, Q=30.0*14*2.8, D50_trial=1.3` | `legacy.basin_applicable`, `legacy.option_2` |
| C-03 | remove `V_LB` | `legacy.L_adopted`, `legacy.option_1` |
| H-02 | `hy8_io.inputs_from_hy8(HY8, 0, 1, 3, V_LB=[6,4,3,2])` | `TW` against demo `.hy8` lines 70 and 190 |
| H-03 | circular, rise 4, yo 2, Vo = 60/(2 pi), TW 1; barrels 1 with Q 60, then barrels 3 with Q 180 | `ye`, `Fr`, `TW_ye` |
| H-04 | `Vo=8.0`; then `yo=6.5, Vo=639.56/(14*6.0)` | `Vo_check_result`, `Fr`, `A`, `ye` |
| H-06 | `Q=float("nan")`; `V_LB=[11.741, 12.5, 4.145, 3.102]`; `V_channel=-3`; `barrels=2.5` | `legacy.option_1`, `legacy.L_adopted` |
| M-07 | `Vo=20.0, Q=20.0*14*2.8` | `legacy.reaches[0]` |
| M-13 | `python legacy/hec14_outlet_protection.py --hy8 legacy/examples/HY8_Demo_Culverts.hy8 --culvert 1 --flow 490 --v-lb 6 4 3 2` | error text |
| Sec. 5.2 | inputs listed in the table | values listed in the table |
