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
