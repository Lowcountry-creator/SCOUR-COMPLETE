"""Development framework. Legacy outputs are NOT verified design recommendations."""
from basin_exit import basin_exit

import argparse
import json
import math
import sys
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).resolve().parent / "legacy"))
from hec14_outlet_protection import Inputs, analyze, flow_area, format_report

STATUS = "DEVELOPMENT ONLY — independent engineering verification pending"
INFERENCES = [
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
    validate_fields(data)
    data = dict(data)
    dmax = data.pop("trial_dmax_ft", None)
    side_slope = data.pop("basin_side_slope", None)
    for field in ("V_perm", "tau_perm"):
        if field not in data:
            raise ValueError(f"{field} must be explicitly supplied for the receiving lining")
    inp = Inputs.from_dict(data)
    if not data.get("V_LB") or not any(data["V_LB"]):
        raise ValueError("V_LB requires four supplied HY-8 station velocities")
    if inp.barrels != 1:
        raise ValueError("barrels must be one for framework screening; multiple outlets are unverified")
    inp.validate()
    if inp.yo > inp.rise - inp.embedment:
        raise ValueError("yo exceeds hydraulic rise above the outlet bed")
    if abs(inp.Q / flow_area(inp, inp.yo) - inp.Vo) > 0.1:
        raise ValueError("Vo differs from Q/A by more than 0.1 fps")
    if inp.V_LB[0] > inp.Vo:
        raise ValueError("V_LB velocities exceed Vo")
    result = analyze(inp)
    # HEC-14 (2006) 10.1.4 gives alternative thickness bases. Reporting
    # the larger as a conservative screen is engineering judgment.
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
    legacy = asdict(result)
    summary = {key: legacy.pop(key) for key in
               ("option_1", "option_2", "vertical_limits", "banks")}
    thickness_note = "Dmax unavailable: block 5 gives the D50 basis only."
    if thickness:
        thickness_note = "Thickness comparison (larger governs this screen): " + ", ".join(
            f"{name}: D50 basis {v['d50_basis_ft']:.2f} ft, Dmax basis "
            f"{v['dmax_basis_ft']:.2f} ft, use {v['screen_ft']:.2f} ft"
            for name, v in thickness.items())
    report = "\n".join([STATUS, *INFERENCES, thickness_note, format_report(inp, result), STATUS])
    return {"status": STATUS, "inputs": asdict(inp), "legacy": legacy,
            "legacy_unverified_design_text": summary,
            "trial_dmax_ft": dmax, "thickness": thickness, "basin_side_slope": side_slope, "basin_exit": exit_check, "report": report, "recommendations": [],
            "inferences": INFERENCES,
            "blockers": ["Independent equation and applicability verification pending",
                         "Independent jet decay not implemented"]}

def run_batch(cases):
    results = []
    for index, case in enumerate(cases):
        try:
            results.append({"index": index, **run_case(case)})
        except Exception as exc:
            results.append({"index": index, "error": str(exc), "status": STATUS})
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
