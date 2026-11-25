"""Development framework. Legacy outputs are NOT verified design recommendations."""
from basin_exit import basin_exit
from methods_apron import apron_screen
from scdot_stone import GRADATIONS, reach_class

import argparse
import json
import math
from pathlib import Path
from dataclasses import asdict

from legacy.hec14_outlet_protection import Inputs, analyze, flow_area, format_report

STATUS = "DEVELOPMENT ONLY — independent engineering verification pending"
INFERENCES = [
    'Basin length uses separate pool and apron minimum lengths. The mild-slope 0.65 ft trial gives 25.1 ft here versus 24 ft in the FHWA example.',
    'I18: Legacy jet screening uses TW/ye. Step 5 also uses TW/yo; verify applicability where the two classifications differ.',
    'I07-I12: Station interval is 4 Wo without a valid basin. Target is max(channel, permissible); interpolate linearly, apply a one-LB minimum, round up to 6 ft and size each reach at its upstream velocity. These length rules are engineering judgment.',
    'I15: Block 9 uses a fixed Shields coefficient for bed screening only. Reynolds-dependent HEC-15 sizing and bank checks are pending.',
    'I06: The upper D50/ye limit of 0.7 is the HY-8 screening limit.',
    'I13: Option 1 extends basin and apron relationships to a lined channel by engineering judgment.',
    'I14: Confirm the supplied permissible velocity and shear against site cover, soil, slope and applicable table row.',
    'I21: Full-barrel outlet results are screening only. Brink velocity tolerance is 0.1 fps.',
    'I05: Equivalent single-outlet geometry is a screening assumption. Multiple-barrel jet interaction is UNVERIFIED.',
    "I01: Alternative ranking is engineering judgment, not an agency procedure.",
    "I02: Conceptual geometry is illustrative, not predicted scour topography.",
    "I03: Legacy construction details are project-specific, not universal.",
    "I04: Interpolated HY-8 velocities are not independent jet predictions.",
]

def finite_number(field, value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number")


def validate_fields(data):
    for field, value in data.items():
        if field in ("project", "culvert", "description", "design_storm", "hy8_file",
                     "min_class", "shape"):
            if not isinstance(value, str):
                raise ValueError(f"{field} must be text")
        elif field == "V_LB":
            if not isinstance(value, (list, tuple)) or len(value) != 4:
                raise ValueError("V_LB requires four station velocities")
            for station in value:
                finite_number(field, station)
            if min(value) < 0 or any(a < b for a, b in zip(value, value[1:])):
                raise ValueError("V_LB must be nonnegative and nonincreasing")
        elif value is not None or field not in ("slope", "HS_hy8", "basin_side_slope"):
            finite_number(field, value)
            if value < 0:
                raise ValueError(f"{field} must be nonnegative")
    if type(data.get("barrels", 1)) is not int:
        raise ValueError("barrels must be an integer count")
    for field in ("V_perm", "tau_perm"):
        if data.get(field) == 0:
            raise ValueError(f"{field} must be positive")


def run_case(data):
    """Preserve original ten-block output; do not promote unverified methods."""
    if not isinstance(data, dict):
        raise ValueError("Case must be a JSON object")
    data = dict(data)
    lining_basis = data.pop("lining_basis", None)
    if lining_basis is not None:
        if not isinstance(lining_basis, dict):
            raise ValueError("lining_basis requires cover, soil_group and source_row")
        for key in ("cover", "soil_group", "source_row"):
            if not isinstance(lining_basis.get(key), str) or not lining_basis[key].strip():
                raise ValueError(f"lining_basis requires {key}")
        if data.get("slope") is None:
            raise ValueError("slope required with lining_basis")
        lining_basis = {key: lining_basis[key] for key in ("cover", "soil_group", "source_row")}
    validate_fields(data)
    soil_k = data.pop("soil_k", None)
    apron_normal_depth = data.pop("apron_normal_depth_ft", None)
    dmax = data.pop("trial_dmax_ft", None)
    side_slope = data.pop("basin_side_slope", None)
    for field in ("V_perm", "tau_perm", "TW", "V_channel", "shape", "barrels",
                  "embedment", "D50_trial", "Ss", "min_class"):
        if field not in data:
            raise ValueError(f"{field} must be explicitly supplied")
    inp = Inputs.from_dict(data)
    if inp.V_LB is not None and not any(inp.V_LB):
        raise ValueError("V_LB requires four supplied HY-8 station velocities")
    if inp.barrels != 1:
        raise ValueError("barrels must be one for framework screening; multiple outlets are unverified")
    supplied_width = inp.Wo
    inp.validate()
    if inp.yo > inp.rise - inp.embedment:
        raise ValueError("yo exceeds hydraulic rise above the outlet bed")
    if abs(inp.Q / flow_area(inp, inp.yo) - inp.Vo) > 0.1:
        raise ValueError("Vo differs from Q/A by more than 0.1 fps")
    if inp.V_LB and inp.V_LB[0] > inp.Vo:
        raise ValueError("V_LB velocities exceed Vo")
    result = analyze(inp)
    # HEC-14 (2006) 10.1.4 gives alternative thickness bases. Reporting
    # the larger as a conservative screen is engineering judgment.
    if dmax is None:
        dmax = next((upper for _, median, upper in GRADATIONS
                     if median == inp.D50_trial), None)
    thickness = None
    if result.basin_applies == "Yes" and dmax is not None:
        if dmax < inp.D50_trial:
            raise ValueError("trial_dmax_ft must be at least D50_trial")
        thickness = {}
        for name, d50_value, factor in (("approach", result.t_approach, 2),
                                        ("pool", result.t_pool, 1.5)):
            thickness[name] = {"d50_basis_ft": d50_value, "dmax_basis_ft": factor*dmax,
                               "screen_ft": max(d50_value, factor*dmax)}
    exit_check = None
    if result.basin_applies == "Yes":
        if side_slope is None:
            result.option_2 = "Incomplete: supply basin_side_slope (H:V) for exit check."
        else:
            exit_check = basin_exit(inp.Q, result.Wb, side_slope, inp.g,
                                    max(inp.V_channel, inp.V_perm))
            outcome = "passes" if exit_check["passes"] else "fails"
            detail = (f"Trial basin exit {outcome}: {exit_check['velocity_fps']:.2f} fps "
                      f"vs {exit_check['allowable_fps']:.2f} fps allowable.")
            result.option_2 = (result.option_2 + " " + detail if exit_check["passes"]
                               else "Trial basin rejected. " + detail)
    elif result.option_2.startswith("Available"):
        result.option_2 = "Incomplete: rerun candidate stone and check basin exit."
    if result.Fr >= 1:
        result.option_1 = "I13: Withheld for supercritical or critical outlet flow."
    else:
        result.option_1 = "I13: Engineering judgment. " + result.option_1
    if result.TW_ye <= 0.75:
        result.decay_L = []
        result.decay_V = []
        result.decay_ratio = []
        result.reaches = []
        result.headwall_class_lined = "Not evaluated at low tailwater"
        result.option_1 = "Low tailwater: downstream jet sizing withheld."
        if exit_check and exit_check["passes"] and inp.TW / inp.yo <= 0.75:
            result.option_2 = ("Trial basin exit passes. No additional downstream "
                               "riprap indicated by Step 5 for this basin.")
    if result.tie_to_hy8.startswith("Does not tie"):
        raise ValueError("HS_hy8 disagrees with trial pool depth by more than 0.05 ft; "
                         "reconcile HY-8 station spacing before using this case")
    apron = {"status": "Outside single unembedded circular outlet screen (60 in maximum)"}
    if inp.shape == "circular" and inp.embedment == 0 and inp.rise <= 5:
        try:
            apron = apron_screen(inp.Q, inp.rise, inp.TW, inp.Ss,
                                 supercritical=inp.yo < result.yc,
                                 normal_depth=apron_normal_depth)
        except ValueError as exc:
            apron = {"status": str(exc)}
    if soil_k is None:
        soil_screen = "Soil K missing; SCDOT soil screen incomplete."
    elif soil_k > 0.4:
        soil_screen = "Highly erodible; outlet protection required."
    elif soil_k >= 0.25:
        soil_screen = "Moderately erodible; outlet protection may be required."
    else:
        soil_screen = "Below moderate K threshold; review design-storm scour potential."
    legacy = asdict(result)
    summary = {key: legacy.pop(key) for key in
               ("option_1", "option_2", "vertical_limits", "banks")}
    thickness_note = "Dmax unavailable: block 5 gives the D50 basis only."
    if thickness:
        thickness_note = "Thickness comparison (larger governs this screen): " + ", ".join(
            f"{name}: D50 basis {v['d50_basis_ft']:.2f} ft, Dmax basis "
            f"{v['dmax_basis_ft']:.2f} ft, use {v['screen_ft']:.2f} ft"
            for name, v in thickness.items())
    reach_classes = [reach_class(r.D50_required, inp.min_class) for r in result.reaches]
    class_note = "SCDOT 2025 §804.2.1 reach classes (minimum applied): " + (
        ", ".join(reach_classes) or "not evaluated")
    if lining_basis:
        lining_note = "Permissible threshold basis: " + ", ".join(
            f"{key}={value}" for key, value in lining_basis.items())
    else:
        lining_note = ("UNVERIFIED permissible thresholds: supply lining_basis "
                       "(cover, soil_group, source_row) and slope for traceability.")
    exit_note = "Basin exit: no checked geometry."
    if exit_check:
        exit_note = (f"Basin exit critical depth {exit_check['depth_ft']:.2f} ft; "
                     f"velocity {exit_check['velocity_fps']:.2f} fps; allowable "
                     f"{exit_check['allowable_fps']:.2f} fps.")
    # Preserve the ten legacy blocks, identifying the historical A-D table.
    class_note += ". The following workbook blocks retain their A-D class labels."
    report = "\n".join([STATUS, *INFERENCES, exit_note, soil_screen, lining_note, class_note, thickness_note, format_report(inp, result), STATUS])
    return {"status": STATUS, "soil_k": soil_k, "soil_screen": soil_screen, "lining_basis": lining_basis, "inputs": asdict(inp), "supplied_width_ft": supplied_width, "legacy": legacy,
            "legacy_unverified_design_text": summary,
            "reach_classes_2025": reach_classes, "trial_dmax_ft": dmax, "thickness": thickness, "basin_side_slope": side_slope, "apron": apron, "apron_normal_depth_ft": apron_normal_depth, "basin_exit": exit_check, "report": report, "recommendations": [],
            "inferences": INFERENCES,
            "blockers": ["Independent equation and applicability verification pending",
                         "Independent jet decay not implemented"]}

def run_batch(cases, *, strict=False):
    results = []
    for index, case in enumerate(cases):
        try:
            entry = {"index": index, **run_case(case)}
            json.dumps(entry, allow_nan=False)
            results.append(entry)
        except Exception as exc:
            if strict and not isinstance(exc, (ValueError, OverflowError)):
                raise
            results.append({"index": index, "error": str(exc), "error_type": type(exc).__name__,
                            "status": STATUS})
    return results

def main():
    parser = argparse.ArgumentParser(description=STATUS)
    parser.add_argument("input", type=Path, help="JSON object or array of cases")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = run_batch(data) if isinstance(data, list) else run_case(data)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")

if __name__ == "__main__":
    main()
