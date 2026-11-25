"""Development framework. Legacy outputs are NOT verified design recommendations."""
import argparse
import json
import sys
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).resolve().parent / "legacy"))
from hec14_outlet_protection import Inputs, analyze, format_report

STATUS = "DEVELOPMENT ONLY — independent engineering verification pending"
INFERENCES = [
    "I01: Alternative ranking is engineering judgment, not an agency procedure.",
    "I02: Conceptual geometry is illustrative, not predicted scour topography.",
    "I03: Legacy construction details are project-specific, not universal.",
    "I04: Interpolated HY-8 velocities are not independent jet predictions.",
]

def run_case(data):
    """Preserve original ten-block output; do not promote unverified methods."""
    inp = Inputs.from_dict(data)
    if not data.get("V_LB") or not any(data["V_LB"]):
        raise ValueError("V_LB requires four supplied HY-8 station velocities")
    result = analyze(inp)
    legacy = asdict(result)
    summary = {key: legacy.pop(key) for key in
               ("option_1", "option_2", "vertical_limits", "banks")}
    report = "\n".join([STATUS, *INFERENCES, format_report(inp, result), STATUS])
    return {"status": STATUS, "inputs": asdict(inp), "legacy": legacy,
            "legacy_unverified_design_text": summary,
            "report": report, "recommendations": [],
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
