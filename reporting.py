"""Optional development PDF and batch export; legacy report text preserved."""
from pathlib import Path
import json
import csv
from visuals import export_velocity_plot, export_orbit

def export_case(case, folder, *, details=False, orbit=False, plotlyjs=True):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Preformatted
    from reportlab.lib.styles import getSampleStyleSheet
    from xml.sax.saxutils import escape
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "result.json").write_text(json.dumps(case, indent=2, allow_nan=False), encoding="utf-8")
    (folder / "legacy_report.txt").write_text(case["report"], encoding="utf-8")
    plot = folder / "velocity.png"
    export_velocity_plot(case, plot)
    styles = getSampleStyleSheet()
    story = [Paragraph("SCOUR-COMPLETE — Development only", styles["Title"]),
             Paragraph("Unverified legacy calculations; no design recommendation.", styles["Normal"]),
             Image(str(plot), width=480, height=240)]
    for item in case["inferences"] + case["blockers"]:
        story.append(Paragraph(escape(item), styles["Normal"]))
    if details:
        story.append(Paragraph("Calculated detail data — conceptual, not agency standard", styles["Heading2"]))
        for key in ("hs", "Ls", "La", "Lb", "Wb", "t_approach", "t_pool"):
            value = case["legacy"].get(key)
            story.append(Paragraph(escape(f"{key}: {value} ft" if isinstance(value,(float,int)) else f"{key}: unavailable"), styles["Normal"]))
    SimpleDocTemplate(str(folder / "qc_report.pdf")).build(story)
    orbit_path = folder / "orbit.html"
    if orbit and case["legacy"]["basin_applies"] == "Yes":
        export_orbit(case, orbit_path, plotlyjs=plotlyjs)
        return "written"
    orbit_path.unlink(missing_ok=True)
    return "no basin geometry" if orbit else "not requested"

def export_batch(results, folder, **options):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    summary = []
    for i, case in enumerate(results):
        row = {"index": i, "status": case.get("status"), "error": case.get("error", "")}
        inputs = case.get("inputs", {})
        row.update(culvert=inputs.get("culvert"), event=inputs.get("design_storm"),
                   length_ft=case.get("legacy", {}).get("L_adopted"),
                   orbit="skipped")
        if not row["error"]:
            try:
                plotlyjs = True
                if options.get("orbit") and case["legacy"]["basin_applies"] == "Yes":
                    from plotly.offline import get_plotlyjs
                    shared = folder / "plotly.min.js"
                    if not shared.exists():
                        shared.write_text(get_plotlyjs(), encoding="utf-8")
                    plotlyjs = "../plotly.min.js"
                row["orbit"] = export_case(case, folder / f"case_{i+1:04d}",
                                           plotlyjs=plotlyjs, **options)
            except Exception as exc:
                row["error"] = str(exc)
        summary.append(row)
    with (folder / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["index", "culvert", "event", "length_ft", "status", "orbit", "error"])
        writer.writeheader()
        writer.writerows(summary)
    return summary
