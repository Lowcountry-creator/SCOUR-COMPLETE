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
    with pytest.warns(UserWarning, match="bed 100.7"):
        assert inputs_from_hy8(path, 0, 1, 3).TW == pytest.approx(2.75)


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
