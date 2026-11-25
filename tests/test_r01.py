from dataclasses import asdict

import pytest

from scour_complete import STATUS, run_case
from legacy.hec14_outlet_protection import EXAMPLES


def base(**changes):
    return {**asdict(EXAMPLES["culv1"]), **changes}


def test_status_on_standalone_report():
    case = run_case(base())
    assert case["report"].startswith(STATUS) and case["report"].endswith(STATUS)
    assert "option_1" not in case["legacy"]
    assert case["legacy_unverified_design_text"]["option_1"]


def test_froude_gate():
    with pytest.raises(ValueError, match="Fr >= 3"):
        run_case(base(Vo=30, Q=30*14*2.8))


@pytest.mark.parametrize("velocities", [None, [0]*4])
def test_missing_jet(velocities):
    data = base()
    data.pop("V_LB")
    if velocities is not None:
        data["V_LB"] = velocities
    with pytest.raises(ValueError, match="V_LB"):
        run_case(data)


def test_step4_published_exit():
    from basin_exit import basin_exit

    check = basin_exit(800, 68, 2, 32.2, 7)
    assert check["depth_ft"] == pytest.approx(1.60, abs=.01)
    assert check["velocity_fps"] == pytest.approx(7.0, abs=.05)
    assert "Incomplete" in run_case(base())["legacy_unverified_design_text"]["option_2"]
    rejected = run_case(base(basin_side_slope=0, V_channel=1))
    assert "rejected" in rejected["legacy_unverified_design_text"]["option_2"]


def test_relief_pipe_datum():
    from pathlib import Path
    from legacy.hy8_io import inputs_from_hy8

    path = Path(__file__).resolve().parents[1] / "legacy/examples/HY8_Demo_Culverts.hy8"
    with pytest.raises(ValueError, match="Confirm the common elevation datum"):
        inputs_from_hy8(path, 0, 1, 3)
    with pytest.warns(UserWarning, match="bed 100.7"):
        assert inputs_from_hy8(path, 0, 1, 3, confirm_tailwater_datum=True).TW == pytest.approx(2.75)


def test_multiple_outlets_withheld():
    with pytest.raises(ValueError, match="barrels"):
        run_case(base(barrels=3))


@pytest.mark.parametrize("change,field", [({"yo": 7}, "yo"), ({"Vo": 8}, "Vo")])
def test_inconsistent_brink(change, field):
    with pytest.raises(ValueError, match=field):
        run_case(base(**change))


@pytest.mark.parametrize("field", ["V_perm", "tau_perm"])
def test_permissible_required(field):
    case = base()
    del case[field]
    with pytest.raises(ValueError, match=field):
        run_case(case)


@pytest.mark.parametrize("change,field", [
    ({"Q": float("nan")}, "Q"), ({"yo": "2.8"}, "yo"),
    ({"barrels": 1.0}, "barrels"), ({"V_channel": -1}, "V_channel"),
    ({"V_LB": [10, 4, 5, 1]}, "V_LB"), ({"V_LB": [20, 5, 4, 1]}, "V_LB"),
])
def test_field_validation(change, field):
    with pytest.raises(ValueError, match=field):
        run_case(base(**change))


def test_option_one_eligibility():
    assert "Withheld" in run_case(base())["legacy_unverified_design_text"]["option_1"]
    sub = run_case(asdict(EXAMPLES["culv2"]))
    assert "Engineering judgment" in sub["legacy_unverified_design_text"]["option_1"]


def test_option_two_uses_trial_class():
    from legacy.hec14_outlet_protection import Inputs, analyze

    r = analyze(Inputs(**base(D50_trial=.5)))
    assert r.largest_valid_class == "B"
    assert r.option_2.startswith("Class A basin: pool 4.0 ft deep")
    assert (r.Ls, r.La, r.Wb) == pytest.approx((42, 19.8, 55.2), abs=.3)
    assert (r.t_approach, r.t_pool) == (1.5, 1)


def test_ratio_attribution():
    assert "HY-8 screening limit" in run_case(base())["report"]


def test_shields_screen_identified():
    assert "bed screening only" in run_case(base())["report"]


def test_dmax_thickness():
    case = run_case(base(trial_dmax_ft=1.33))
    assert case["thickness"]["pool"]["screen_ft"] == pytest.approx(1.995)
    assert case["thickness"]["approach"]["screen_ft"] == 2.66


def test_length_judgments_reported():
    assert "I07-I12" in run_case(base())["report"]


def test_low_tailwater_exit():
    case = run_case(base(TW=.5, HS_hy8=None, basin_side_slope=2, V_perm=20))
    assert case["basin_exit"]["passes"]
    assert case["legacy"]["reaches"] == []
    assert "Step 5" in case["legacy_unverified_design_text"]["option_2"]


def test_2025_classes():
    case = run_case(base(Vo=20, Q=20*14*2.8, HS_hy8=None))
    assert case["reach_classes_2025"][0] == "F"
    assert case["trial_dmax_ft"] == 1.33


def test_batch_optional_orbit(tmp_path):
    from reporting import export_batch

    cases = [run_case(base()), run_case(asdict(EXAMPLES["culv2"]))]
    summary = export_batch(cases, tmp_path, orbit=True)
    assert [r["orbit"] for r in summary] == ["written", "no basin geometry"]
    assert not summary[1]["error"]
    assert (tmp_path / "plotly.min.js").exists()
    assert "../plotly.min.js" in (tmp_path / "case_0001/orbit.html").read_text()


def test_pdf_includes_report(tmp_path):
    from unittest.mock import patch
    from reporting import export_case

    case = run_case(base())
    with patch("reportlab.platypus.SimpleDocTemplate.build") as build:
        export_case(case, tmp_path, details=True)
    text = "\n".join(getattr(item, "text", "") for item in build.call_args.args[0])
    assert case["inputs"]["culvert"] in text and "10. Design summary" in text
    assert "hs: 1.82 ft" in text


@pytest.mark.parametrize("flag", ["1", "invalid"])
def test_wrong_import_units(tmp_path, flag):
    from pathlib import Path
    from legacy.hy8_io import inputs_from_hy8

    src = Path(__file__).resolve().parents[1] / "legacy/examples/HY8_Demo_Culverts.hy8"
    changed = tmp_path / src.name
    changed.write_text(src.read_text().replace("UNITS                0", f"UNITS                {flag}"))
    with pytest.raises(ValueError, match="units flag"):
        inputs_from_hy8(changed, 0, 0, 3, rst_path=src.with_suffix(".rst"))


def test_integer_discharge():
    from pathlib import Path
    from legacy.hy8_io import inputs_from_hy8

    src = Path(__file__).resolve().parents[1] / "legacy/examples/HY8_Demo_Culverts.hy8"
    assert inputs_from_hy8(src, 0, 0, 490).Q == 410.9


def test_gui_report_text():
    from gui import display_report

    text = display_report([run_case(base()), {"index": 1, "error": "bad inputs"}])
    assert "\n10. Design summary" in text and "Case 2: bad inputs" in text


def test_adjusted_diameter_ambiguity():
    from methods_apron import apron_d50

    with pytest.raises(ValueError, match="D versus"):
        apron_d50(85, 5, 4.5, supercritical=True, normal_depth=3)
    assert "Stone size only" in apron_d50(85, 5, 2)["scope"]


@pytest.mark.parametrize("field", ["TW", "V_channel", "Ss", "embedment", "barrels"])
def test_explicit_hydraulic_inputs(field):
    data = base()
    del data[field]
    with pytest.raises(ValueError, match=field):
        run_case(data)
    assert run_case(base(TW=0, HS_hy8=None))["legacy"]["tailwater_case"] == "Low tailwater"


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_batch_strict_json(bad):
    import json
    from scour_complete import run_batch

    entries = json.loads(json.dumps(run_batch([base(Q=bad), base()]), allow_nan=False))
    assert entries[0]["index"] == 0 and "Q" in entries[0]["error"]
    assert entries[1]["legacy"]["L_adopted"] == 108


def test_import_path_unchanged():
    import subprocess
    import sys
    from pathlib import Path

    subprocess.run([sys.executable, "-c",
                    "import sys; before=list(sys.path); import scour_complete; "
                    "assert sys.path == before"], check=True,
                   cwd=Path(__file__).resolve().parents[1])


@pytest.mark.parametrize("name,length,pool", [
    ("culv1", 108, 1.8213), ("culv2", 60, None), ("culv4", 108, None)])
def test_workbook_regression(name, length, pool):
    r = run_case(asdict(EXAMPLES[name]))["legacy"]
    assert r["L_adopted"] == length
    if pool is None:
        assert r["hs"] is None
    else:
        assert r["hs"] == pytest.approx(pool, abs=.0001)


def test_published_steep_basin():
    r = run_case(base(Q=800, Wo=8, rise=6, embedment=0, yo=4, Vo=25, TW=2.8,
                      D50_trial=1.83, HS_hy8=None, basin_side_slope=2))["legacy"]
    assert r["hs"] == pytest.approx(6.0, abs=.06)
    assert r["Lb"] == pytest.approx(90, abs=1)
    assert r["Wb"] == pytest.approx(68, abs=.6)


def test_width_provenance():
    import math

    d = base(shape="circular", rise=4, Wo=0, embedment=0, Q=60, yo=2,
             Vo=60/(2*math.pi), V_LB=[8, 6, 4, 2], HS_hy8=None)
    case = run_case(d)
    assert d["Wo"] == case["supplied_width_ft"] == 0
    assert case["inputs"]["Wo"] == 4


def test_length_deviation_documented():
    assert "25.1 ft" in run_case(base())["report"]


def test_low_tailwater_velocity_label(tmp_path):
    from unittest.mock import patch
    from matplotlib.axes import Axes
    from visuals import export_velocity_plot

    with patch.object(Axes, "plot", autospec=True) as plot:
        export_velocity_plot(run_case(base(TW=0, HS_hy8=None)), tmp_path / "plot.png")
    assert not plot.called


def test_orbit_flat_apron(tmp_path):
    import plotly.graph_objects as go
    from unittest.mock import patch
    from visuals import export_orbit

    with patch.object(go.Figure, "write_html", autospec=True) as write_html:
        export_orbit(run_case(base()), tmp_path / "orbit.html")
    z = write_html.call_args.args[0].data[0].z
    assert min(z[15]) < 0
    assert all(value == 0 for row in z[30:] for value in row)


def test_unexpected_batch_error(monkeypatch):
    import scour_complete

    def fail(_):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(scour_complete, "run_case", fail)
    assert scour_complete.run_batch([{}])[0]["error_type"] == "RuntimeError"
    with pytest.raises(RuntimeError):
        scour_complete.run_batch([{}], strict=True)


def test_low_tailwater_regime():
    assert run_case(base(TW=.5, HS_hy8=None))["legacy"]["regime"] == "Supercritical at brink"


def test_station_tie_failure():
    with pytest.raises(ValueError, match="station spacing"):
        run_case(base(D50_trial=.5))


def test_lining_provenance():
    basis = {"cover": "surveyed grass", "soil_group": "D", "source_row": "project criterion"}
    case = run_case(base(lining_basis=basis))
    assert case["lining_basis"] == basis and "project criterion" in case["report"]
    with pytest.raises(ValueError, match="slope"):
        run_case(base(lining_basis=basis, slope=None))


def test_published_apron_dimensions():
    from methods_apron import apron_screen

    apron = apron_screen(85, 5, 1.6, 2.65)
    assert apron["example_class"] == 2
    assert (apron["length_ft"], apron["thickness_ft"]) == (20, 1.65)
    assert apron["end_width_ft"] == pytest.approx(28.3, abs=.05)
    assert apron_screen(85, 5, 1.6, 2.7)["d50_ft"] < apron["d50_ft"]


def test_governing_events(tmp_path):
    from reporting import export_batch

    small = run_case(asdict(EXAMPLES["culv2"]))
    small["inputs"]["culvert"] = base()["culvert"]
    rows = export_batch([small, run_case(base())], tmp_path)
    assert [r["governs_length_ft"] for r in rows] == [False, True]
    assert rows[1]["governs_max_reach_d50_ft"]


@pytest.mark.parametrize("field", ["TW", "V_channel"])
def test_legacy_missing_tw_or_velocity(field):
    from legacy.hec14_outlet_protection import Inputs, analyze

    data = base()
    del data[field]
    with pytest.raises(ValueError, match=field):
        analyze(Inputs(**data))


def test_legacy_zero_stations():
    from legacy.hec14_outlet_protection import Inputs, analyze

    with pytest.raises(ValueError, match="V_LB"):
        analyze(Inputs(**base(V_LB=[0]*4)))


@pytest.mark.parametrize("k, expected", [
    (.249, "Below moderate"), (.25, "Moderately"), (.4, "Moderately"), (.401, "Highly")])
def test_rhds_soil_thresholds(k, expected):
    assert run_case(base(soil_k=k))["soil_screen"].startswith(expected)


def test_gui_hy8_draft():
    from pathlib import Path
    from gui import import_draft

    path = Path(__file__).resolve().parents[1] / "legacy/examples/HY8_Demo_Culverts.hy8"
    draft = import_draft(path, 0, 0, 3)
    assert draft["Q"] == 410.9 and draft["TW"] == 4.29
    assert draft["V_perm"] is None and draft["V_LB"] is None


def test_low_tailwater_without_jet_data():
    data = base(TW=.5, HS_hy8=None, basin_side_slope=2, V_perm=20)
    del data["V_LB"]
    case = run_case(data)
    assert case["inputs"]["V_LB"] is None
    assert case["basin_exit"]["passes"] and not case["legacy"]["decay_V"]


def test_unlisted_trial_is_named_by_size():
    from legacy.hec14_outlet_protection import Inputs, analyze

    case = Inputs(**base(Wo=2, rise=2, embedment=0, yo=.5, Vo=7,
                         Q=7, TW=.2, D50_trial=.1, V_LB=[4, 3, 2, 1]))
    result = analyze(case)
    assert result.largest_valid_class.startswith("None")
    assert result.option_2.startswith("Trial D50 0.1 ft basin")


def test_report_exit_numbers_low_tw():
    case = run_case(base(TW=.5, HS_hy8=None, basin_side_slope=2, V_perm=20))
    assert f"velocity {case['basin_exit']['velocity_fps']:.2f} fps" in case["report"]


def test_legacy_cli_standalone_warning(tmp_path):
    import json
    from legacy.hec14_outlet_protection import main

    report, data = tmp_path / "case.txt", tmp_path / "case.json"
    main(["--example", "culv1", "--out", str(report), "--json-out", str(data)])
    status = json.loads(data.read_text())["status"]
    assert report.read_text().splitlines()[0] == report.read_text().splitlines()[-1] == status


def test_legacy_import_discloses_lining_defaults(capsys):
    from pathlib import Path
    from legacy.hec14_outlet_protection import main

    path = Path(__file__).resolve().parents[1] / "legacy/examples/HY8_Demo_Culverts.hy8"
    main(["--hy8", str(path), "--v-lb", "4", "3", "2", "1"])
    assert "tau_perm" in capsys.readouterr().err


def test_migration_reference():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "HANDOFF.md"
    assert "e0cf993 is a commit (tree a6d743a)" in path.read_text(encoding="utf-8")


def test_gui_dependency_note():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "README.md"
    assert "python -m tkinter" in path.read_text(encoding="utf-8")


def test_errata_register():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "docs/ARCHITECTURE.md"
    assert "HEC-14 errata dated 2012-10-01" in path.read_text(encoding="utf-8")
