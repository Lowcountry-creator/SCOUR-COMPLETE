"""Tests for the HY-8 import path.

Fixtures are the synthetic HY-8_Exporter demo project (Oak Creek Road:
twin 6x4 box plus 48 in RCP; Farm Access Lane: triple 36 in HDPE). The
numbers are not a real design; they exercise the parsers and the mapping
into block 1.
"""

import math
from pathlib import Path

import pytest

import hec14_outlet_protection as h
import hy8_io

HERE = Path(__file__).parent / "examples"
HY8 = HERE / "HY8_Demo_Culverts.hy8"
RST = HERE / "HY8_Demo_Culverts.rst"


def test_read_hy8_geometry():
    proj = hy8_io.read_hy8(HY8)
    names = [c.name for c in proj.crossings]
    assert names == ["Oak Creek Road", "Mill Branch Drive", "Farm Access Lane"]
    oak = proj.crossing("Oak Creek Road")
    assert oak.flow_names == ["2-yr", "10-yr", "25-yr", "50-yr", "100-yr"]
    assert oak.flows_cfs == [180, 320, 410, 490, 580]
    assert oak.tailwater_type == 2
    assert oak.channel_slope == 0.004
    box, rcp = oak.culverts
    assert (box.shape, box.span_ft, box.rise_ft, box.barrels) == (
        "Concrete Box", 6, 4, 2)
    assert (rcp.shape, rcp.span_ft, rcp.barrels) == ("Circular", 4, 1)
    mill = proj.crossing(1)
    assert mill.tailwater_type == 6
    assert mill.channel_slope is None  # constant TW elevation has no slope


def test_read_rst_tables():
    xings = hy8_io.read_rst(RST)
    oak = xings[0]
    assert oak.name == "Oak Creek Road"
    t = oak.culvert_summary("Twin 6x4 Box")
    assert t.culvert_index == 0
    assert t.row("Outlet Velocity")[3] == 14.80
    assert t.unit("Outlet Velocity") == "ft/s"
    assert t.row("Tailwater Depth")[3] == 4.29
    with pytest.raises(ValueError):
        oak.culvert_summary("Nope")


def test_inputs_from_hy8_box():
    inp = hy8_io.inputs_from_hy8(
        HY8, "Oak Creek Road", "Twin 6x4 Box", "50-yr",
        V_LB=[10.0, 7.0, 5.0, 4.0], HS_hy8=None)
    assert inp.shape == "box"
    assert inp.barrels == 2
    assert inp.Wo == 12
    assert inp.rise == 4
    assert inp.embedment == 0
    assert inp.Q == 410.90  # culvert discharge, not crossing total
    assert inp.yo == 2.31
    assert inp.Vo == 14.80
    assert inp.TW == 4.29
    assert inp.V_channel == 4.59
    assert inp.slope == 0.004
    assert inp.design_storm == "50-yr"
    assert inp.hy8_file == "HY8_Demo_Culverts.hy8"
    r = h.analyze(inp)
    # Vo check: 410.9 / (12 x 2.31) = 14.82, within 0.1 of 14.80
    assert r.Vo_check_result == "OK"
    assert r.ye == 2.31


def test_inputs_from_hy8_selectors():
    a = hy8_io.inputs_from_hy8(HY8, 0, 1, 3)  # by index
    b = hy8_io.inputs_from_hy8(HY8, "Oak Creek Road", "48 in RCP Relief",
                               490.0)  # by total discharge
    c = hy8_io.inputs_from_hy8(HY8, 0, 1, -2)  # negative = from the end
    assert a.Q == b.Q == c.Q == 79.10
    assert a.shape == "circular"
    assert a.Wo == 4  # 1 barrel x 4 ft diameter
    with pytest.raises(ValueError):
        hy8_io.inputs_from_hy8(HY8, 0, 0, "500-yr")
    with pytest.raises(ValueError):
        hy8_io.inputs_from_hy8(HY8, "Nowhere", 0, 0)
    with pytest.raises(FileNotFoundError):
        hy8_io.inputs_from_hy8(HY8, 0, 0, 0, rst_path=HERE / "missing.rst")


def test_inputs_from_hy8_circular_multi_barrel():
    inp = hy8_io.inputs_from_hy8(HY8, "Farm Access Lane", 0, "25-yr")
    assert inp.shape == "circular"
    assert inp.barrels == 3
    assert inp.rise == 3
    assert inp.Wo == 9
    assert inp.slope == 0.002  # rectangular channel carries a slope
    r = h.analyze(inp)
    assert r.A > 0
    assert math.isclose(r.ye, math.sqrt(r.A / 2))


def test_cli_hy8(tmp_path, capsys):
    out_json = tmp_path / "in.json"
    rc = h.main(["--hy8", str(HY8), "--crossing", "Oak Creek Road",
                 "--culvert", "Twin 6x4 Box", "--flow", "50-yr",
                 "--v-lb", "10", "7", "5", "4", "--hs", "0",
                 "--inputs-out", str(out_json)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Culvert: Oak Creek Road: Twin 6x4 Box" in captured.out
    assert "WARNING" not in captured.err
    assert out_json.exists()
    # Round trip: the written inputs run again without HY-8.
    rc = h.main([str(out_json)])
    assert rc == 0


def test_cli_hy8_warns_without_vlb(capsys):
    h.main(["--hy8", str(HY8), "--culvert", "1"])
    assert "no --v-lb" in capsys.readouterr().err
